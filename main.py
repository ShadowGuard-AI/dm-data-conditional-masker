import argparse
import json
import logging
import sys
from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

        masked_data = []
        for record in data:
            masked_record = record.copy()  # Create a copy to avoid modifying the original
            for rule in self.config:
                try:
                    if eval(rule['condition'], {}, masked_record): # Evaluate condition using record data
                        field_to_mask = rule['field']
                        masking_type = rule['masking_type']

                        if field_to_mask in masked_record:
                            masked_record[field_to_mask] = self.apply_masking(masking_type)
                        else:
                            logging.warning(f"Field '{field_to_mask}' not found in record. Skipping masking.")


                except NameError as e:
                    logging.error(f"Error in condition evaluation.  Invalid variable used: {e}")
                    continue # Skip to the next rule
                except Exception as e:
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
        """
        if self.config is None:
            logging.error("Configuration loading failed.  Exiting.")
            return

        try:
            with open(self.input_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON in input file: {self.input_file}")
                    return

            if not isinstance(data, list):
                logging.error("Input file must contain a list of records (JSON array).")
                return

            masked_data = self.mask_data(data)

            with open(self.output_file, 'w') as f:
                json.dump(masked_data, f, indent=4)

            logging.info(f"Data masking complete.  Output written to: {self.output_file}")


        except FileNotFoundError:
            logging.error(f"Input file not found: {self.input_file}")
        except Exception as e:
            logging.exception(f"Error processing data: {e}")  # Log exception with traceback



def setup_argparse():
    """
    Sets up the argument parser.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    parser = argparse.ArgumentParser(description='Masks data based on conditions specified in a configuration file.')
    parser.add_argument('-c', '--config', dest='config_file', required=True, help='Path to the configuration file.')
    parser.add_argument('-i', '--input', dest='input_file', required=True, help='Path to the input data file.')
    parser.add_argument('-o', '--output', dest='output_file', required=True, help='Path to the output masked data file.')
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

    masker = ConditionalMasker(args.config_file, args.input_file, args.output_file)
    masker.process_data()


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