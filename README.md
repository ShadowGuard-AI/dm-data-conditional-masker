![Introduction banner: a dark timber church door with a heavy iron ring at rest on its plate, amber light pooling on stone inside, no name anywhere](intro-banner.png)

# dm-data-conditional-masker

Title block: the name above is set in Buenard in ming blue on a porcelain white plate, dressed as a chronicle entry with a seasonal marker for the hour before a gathering, with the door ring drawn small beside this first heading only.

![Logo](logo.png)

![Banner](banner.png)

![Animated scene](scene.svg)

![Major separator](sep-heavy.svg)

# dm-data-conditional-masker
Masks data based on conditions specified in a configuration file. Allows selective masking of data based on rules defined using the condition grammar described below (e.g., mask email addresses only for users in a specific department). Conditions are read by a narrow expression evaluator, never by Python eval, so a configuration file is data, not code. - Focused on Tools designed to generate or mask sensitive data with realistic-looking but meaningless values

> Register entry, pine rule, a permission: Configuration is data, never code. Conditions are read by a narrow expression evaluator, never by Python eval.

![Major separator](sep-heavy.svg)

## Condition grammar
A condition may use only:
- Field lookups: a bare field name such as `age`, or `record['department']` with a constant field name.
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, and `not in`, including chained comparisons such as `18 <= age < 70`. The right side of `in` or `not in` may be a list or tuple of constants.
- Boolean operators: `and`, `or`, and unary `not`.
- Constants: strings, numbers, booleans, and null, including a negative number written with a leading minus.

Anything else is rejected with an error: calls, imports, attribute access, subscripts on anything other than `record`, arithmetic, comprehensions, and unknown field names.

> Register entry, pine rule, a permission: The grammar list is closed, and anything outside it errors. What is written above is all that a condition may use.

![Minor separator](sep-light.svg)

## Install
`git clone https://github.com/ShadowGuard-AI/dm-data-conditional-masker`

![Minor separator](sep-light.svg)

## Usage
`python3 main.py [options]`

![Minor separator](sep-light.svg)

## Parameters
- `-h`: Show help message and exit
- `-c`: Path to the configuration file.
- `-i`: Path to the input data file.
- `-o`: Path to the output masked data file. It must not be the input file: if the output path resolves to the input file, the run refuses and exits 1 before any write.

> Register entry, cinnabar rule, a refusal: Output may never resolve to input. If the output path resolves to the input file, the run refuses and exits 1 before any write.

![Minor separator](sep-light.svg)

## Failure rules
- If any rule fails to evaluate for any record, the failures are counted, the run exits 1, and no output is written. A condition naming a misspelled or unknown field fails in this way, so its data is never passed through unmasked under a success message.

> Register entry, cinnabar rule, a refusal: One failed rule anywhere means no output at all. The failures are counted, the run exits 1, and nothing is written.

![Minor separator](sep-light.svg)

## License
This project is released under the MIT License. See the [LICENSE](LICENSE) file for details.

![Major separator](sep-heavy.svg)

## Register entries gathered at the door

The main button of this re-skin reads Mask Where the Rules Say So. Its configuration field label reads Configuration File. Its failure heading reads One Failed Rule, No Output. Further headings read A Closed Grammar, Data, Never Code, and Output Never Equals Input. A marginal note in the keeper hand: the install line and the licence line above name ShadowStrikeHQ; that naming is faulty, it is counted openly in the generation record, and the entries themselves stand as they were entered, not struck through and not rewritten. The door closes on a finished register: the ring rests against its plate, what was allowed is written, and what was refused is written.
