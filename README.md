![Banner](banner.png)

# dm-data-conditional-masker
Masks data based on conditions specified in a configuration file. Allows selective masking of data based on rules defined using the condition grammar described below (e.g., mask email addresses only for users in a specific department). Conditions are read by a narrow expression evaluator, never by Python eval, so a configuration file is data, not code. - Focused on Tools designed to generate or mask sensitive data with realistic-looking but meaningless values

## Condition grammar
A condition may use only:
- Field lookups: a bare field name such as `age`, or `record['department']` with a constant field name.
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, and `not in`, including chained comparisons such as `18 <= age < 70`. The right side of `in` or `not in` may be a list or tuple of constants.
- Boolean operators: `and`, `or`, and unary `not`.
- Constants: strings, numbers, booleans, and null, including a negative number written with a leading minus.

Anything else is rejected with an error: calls, imports, attribute access, subscripts on anything other than `record`, arithmetic, comprehensions, and unknown field names.

## Install
`git clone https://github.com/ShadowStrikeHQ/dm-data-conditional-masker`

## Usage
`./dm-data-conditional-masker [params]`

## Parameters
- `-h`: Show help message and exit
- `-c`: Path to the configuration file.
- `-i`: Path to the input data file.
- `-o`: Path to the output masked data file. It must not be the input file: if the output path resolves to the input file, the run refuses and exits 1 before any write.

## Failure rules
- If any rule fails to evaluate for any record, the failures are counted, the run exits 1, and no output is written. A condition naming a misspelled or unknown field fails in this way, so its data is never passed through unmasked under a success message.

## License
Copyright (c) ShadowStrikeHQ
