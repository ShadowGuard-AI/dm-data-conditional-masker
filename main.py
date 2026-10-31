import argparse
import ast
import json
import logging
import sys
from pathlib import Path
from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConditionError(ValueError):
    """Raised when a rule condition uses anything outside the allowed grammar."""


def evaluate_condition(condition, record):
    """
    Evaluates a rule condition against one record with a narrow AST
    walker. Allowed: field lookups (a bare field name, or
    record['field']), comparisons including chained comparisons and
    in / not in, the boolean operators and / or, unary not, constants,
    and lists or tuples of constants on the right side of in / not in.
    Everything else, including calls, imports, attribute access,
    subscripts on anything but record, arithmetic, and comprehensions,
    raises ConditionError. An unknown field name also raises
    ConditionError, so a mistyped field cannot pass silently.
    """
    try:
        tree = ast.parse(condition, mode='eval')
    except SyntaxError as e:
        raise ConditionError(f"Condition does not parse: {e}")

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value in node.values:
                    if not eval_node(value):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for value in node.values:
                    if eval_node(value):
                        return True
                return False
            raise ConditionError("Boolean operator not allowed in condition.")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not eval_node(node.operand)
            if isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant) \
                    and isinstance(node.operand.value, (int, float)):
                return -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
            raise ConditionError("Unary operator not allowed in condition.")
        if isinstance(node, ast.Compare):
            left = eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = eval_node(comparator)
                try:
                    if isinstance(op, ast.Eq):
                        ok = left == right
                    elif isinstance(op, ast.NotEq):
                        ok = left != right
                    elif isinstance(op, ast.Lt):
                        ok = left < right
                    elif isinstance(op, ast.LtE):
                        ok = left <= right
                    elif isinstance(op, ast.Gt):
                        ok = left > right
                    elif isinstance(op, ast.GtE):
                        ok = left >= right
                    elif isinstance(op, ast.In):
                        ok = left in right
                    elif isinstance(op, ast.NotIn):
                        ok = left not in right
                    else:
                        raise ConditionError("Comparison operator not allowed in condition.")
                except TypeError as e:
                    raise ConditionError(f"Comparison failed: {e}")
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id == 'record':
                return record
            if node.id in record:
                return record[node.id]
            raise ConditionError(f"Unknown field name in condition: {node.id}")
        if isinstance(node, ast.Subscript):
            if not (isinstance(node.value, ast.Name) and node.value.id == 'record'):
                raise ConditionError("Only record['field'] lookups are allowed in conditions.")
            if not (isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                raise ConditionError("record lookups need a constant field name, as in record['field'].")
            field = node.slice.value
            if field not in record:
                raise ConditionError(f"Unknown field name in condition: {field}")
            return record[field]
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool)) or node.value is None:
                return node.value
            raise ConditionError("Constant not allowed in condition.")
        if isinstance(node, (ast.List, ast.Tuple)):
            values = []
            for element in node.elts:
                if not isinstance(element, ast.Constant):
                    raise ConditionError("Lists in conditions may hold constants only.")
                values.append(eval_node(element))
            return values
        raise ConditionError(f"Condition element not allowed: {type(node).__name__}")

    return eval_node(tree)


class ConditionalMasker:
    """
    Masks data based on conditions specified in a configuration file.
    """

    def __init__(self, config_file, input_file, output_file):
        """
        Initializes the ConditionalMasker.

        Args:
            config_file (str): Path to the configuration file.
            input_file (str): Path to the input data file.
            output_file (str): Path to the output masked data file.
        """
        self.config_file = config_file
        self.input_file = input_file
        self.output_file = output_file
        self.config = self.load_config()
        self.fake = Faker()
        self.evaluation_failures = 0

    def load_config(self):
        """
        Loads the configuration from the specified JSON file.

        Returns:
            dict: The configuration as a dictionary.  Returns None on error and logs it.
        """
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            # Validate config (basic structure check)
            if not isinstance(config, list):  # Config should be a list of rules
                raise ValueError("Configuration file must contain a list of rules.")
            for rule in config:
                if not isinstance(rule, dict) or 'condition' not in rule or 'field' not in rule or 'masking_type' not in rule:
                    raise ValueError("Each rule must be a dictionary with 'condition', 'field', and 'masking_type' keys.")

            return config
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {self.config_file}")
            return None  # Return None to indicate failure
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in configuration file: {self.config_file}")
            return None
        except ValueError as e:
            logging.error(f"Invalid configuration: {e}")
            return None
        except Exception as e:
            logging.exception(f"Error loading configuration: {e}")  # Log exception with traceback.
            return None

    def mask_data(self, data):
        """
        Masks the input data based on the loaded configuration.

        Args:
            data (list): A list of dictionaries representing the data to mask.

        Returns:
            list: The masked data.
        """

        self.evaluation_failures = 0
        masked_data = []
        for record in data:
            masked_record = record.copy()  # Create a copy to avoid modifying the original
            for rule in self.config:
                try:
                    # Conditions are read by the narrow evaluator in
                    # evaluate_condition, never by eval. A field can be
                    # named bare, as in age > 60, or through record, as
                    # in record['department'] == 'HR'.
                    if evaluate_condition(rule['condition'], masked_record):
                        field_to_mask = rule['field']
                        masking_type = rule['masking_type']

                        if field_to_mask in masked_record:
                            masked_record[field_to_mask] = self.apply_masking(masking_type)
                        else:
                            logging.warning(f"Field '{field_to_mask}' not found in record. Skipping masking.")

                except Exception as e:
                    # A failed rule is counted, not silently skipped:
                    # process_data refuses to write output or report
                    # completion when the count is not zero.
                    self.evaluation_failures += 1
                    logging.error(f"Error evaluating condition or masking: {e}")
                    continue

            masked_data.append(masked_record)
        return masked_data


    def apply_masking(self, masking_type):
        """
        Applies the specified masking technique.

        Args:
            masking_type (str): The type of masking to apply (e.g., 'name', 'email', 'address').

        Returns:
            str: The masked value.
        """
        try:
            if masking_type == 'name':
                return self.fake.name()
            elif masking_type == 'email':
                return self.fake.email()
            elif masking_type == 'address':
                return self.fake.address()
            elif masking_type == 'phone_number':
                return self.fake.phone_number()
            elif masking_type == 'company':
                return self.fake.company()
            elif masking_type == 'ssn':
                return self.fake.ssn()
            elif masking_type == 'date':
                return self.fake.date()
            elif masking_type == 'city':
                return self.fake.city()
            elif masking_type == 'country':
                return self.fake.country()
            elif masking_type == 'text':
                return self.fake.text()
            elif masking_type == 'password':
                return self.fake.password() # Generates a random password
            else:
                logging.warning(f"Unknown masking type: {masking_type}.  Returning 'MASKED'.")
                return 'MASKED'
        except Exception as e:
            logging.error(f"Error applying masking: {e}")
            return 'MASKED_ERROR'



    def process_data(self):
        """
        Reads data from the input file, masks it, and writes it to the output file.

        Returns True only when the output file was written. Every failure
        path used to return None and let main exit 0, so a missing config
        file looked like a successful masking run from the shell.
        """
        if self.config is None:
            logging.error("Configuration loading failed.  Exiting.")
            return False

        try:
            with open(self.input_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON in input file: {self.input_file}")
                    return False

            if not isinstance(data, list):
                logging.error("Input file must contain a list of records (JSON array).")
                return False

            masked_data = self.mask_data(data)

            if self.evaluation_failures:
                logging.error(
                    f"{self.evaluation_failures} rule evaluation(s) failed. "
                    "No output was written and the run is not complete."
                )
                return False

            with open(self.output_file, 'w') as f:
                json.dump(masked_data, f, indent=4)

            logging.info(f"Data masking complete.  Output written to: {self.output_file}")
            return True

        except FileNotFoundError:
            logging.error(f"Input file not found: {self.input_file}")
            return False
        except Exception as e:
            logging.exception(f"Error processing data: {e}")  # Log exception with traceback
            return False



def setup_argparse():
    """
    Sets up the argument parser.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    parser = argparse.ArgumentParser(description='Masks data based on conditions specified in a configuration file.')
    parser.add_argument('-c', '--config', dest='config_file', required=True, help='Path to the configuration file.')
    parser.add_argument('-i', '--input', dest='input_file', required=True, help='Path to the input data file.')
    parser.add_argument('-o', '--output', dest='output_file', required=True, help='Path to the output masked data file. It must not resolve to the input file.')
    return parser


def main():
    """
    Main function.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Input validation (file extensions)
    if not args.config_file.lower().endswith('.json'):
        logging.error("Config file must be a JSON file.")
        sys.exit(1)
    if not args.input_file.lower().endswith('.json'):
        logging.error("Input file must be a JSON file.")
        sys.exit(1)
    if not args.output_file.lower().endswith('.json'):
        logging.error("Output file must be a JSON file.")
        sys.exit(1)
    if Path(args.input_file).resolve() == Path(args.output_file).resolve():
        logging.error("Error: Output file cannot be the same file as the input file.")
        sys.exit(1)

    masker = ConditionalMasker(args.config_file, args.input_file, args.output_file)
    if not masker.process_data():
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
Example Usage:

1.  Create a configuration file (e.g., config.json):

    ```json
    [
      {
        "condition": "record['department'] == 'HR'",
        "field": "email",
        "masking_type": "email"
      },
      {
        "condition": "record['country'] == 'USA'",
        "field": "phone_number",
        "masking_type": "phone_number"
      },
       {
        "condition": "record['age'] > 60",
        "field": "address",
        "masking_type": "address"
      }
    ]
    ```

2.  Create an input data file (e.g., input.json):

    ```json
    [
      {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "department": "HR",
        "country": "USA",
        "age": 65,
        "address": "123 Main St"
      },
      {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "department": "Sales",
        "country": "Canada",
        "age": 30,
        "address": "456 Oak Ave"
      },
      {
        "name": "Peter Jones",
        "email": "peter.jones@example.com",
        "department": "HR",
        "country": "UK",
        "age": 45,
        "address": "789 Pine Ln"
      },
      {
        "name": "Alice Brown",
        "email": "alice.brown@example.com",
        "department": "Marketing",
        "country": "USA",
        "age": 70,
        "address": "10 Downing St"
      }
    ]
    ```

3.  Run the script:

    ```bash
    python main.py -c config.json -i input.json -o output.json
    ```

4.  The output file (output.json) will contain the masked data:

    ```json
    [
      {
        "name": "John Doe",
        "email": "carter55@gmail.com",
        "department": "HR",
        "country": "USA",
        "age": 65,
        "address": "6449 Daniel Village\nWest Jeffrey, TN 99223"
        "phone_number": "277-482-8277 x823"
      },
      {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "department": "Sales",
        "country": "Canada",
        "age": 30,
        "address": "456 Oak Ave"
      },
      {
        "name": "Peter Jones",
        "email": "kaylaharrison@yahoo.com",
        "department": "HR",
        "country": "UK",
        "age": 45,
        "address": "789 Pine Ln"
      },
      {
        "name": "Alice Brown",
        "email": "alice.brown@example.com",
        "department": "Marketing",
        "country": "USA",
        "age": 70,
        "address": "16045 Ashley Drive Suite 908\nDavidshire, LA 07566"
        "phone_number": "805-577-8436"
      }
    ]
    ```

    Note: The masked values will be different each time the script is run due to the Faker library generating random data.
"""