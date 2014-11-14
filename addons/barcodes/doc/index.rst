Barcodes module documentation
==============================

The Barcodes module defines barcode nomenclatures whose rules identify specific type 
of items e.g. products, locations. It contains the following features:

- Barcode patterns to identify barcodes containing a numerical value (e.g. weight, price)
- Definitin of barcode aliases that allow to identify the same product with different barcodes
- Unlimited barcode patterns and definitions,
- Barcode EAN13 encoding supported.

Barcode nomenclatures and rules
-------------------------------

A barcode nomenclature contains a set of rules. Each rule identifies a barcode pattern. 
A rule has a type specifying the model of the object whose barcode matches the pattern.
A rule has an encoding as well, which can be either EAN-13, or Any. The encoding of a rule
must be set to EAN-13 if the rule identifies a pattern matched by objects whose barcode is
encoding in EAN-13. Rules have a sequence field indicated the order the rules are evaluated (ASC).

Many barcode scanners strip the leading zero when scanning EAN-13 barcodes. Barcode nomenclatures
have a boolean field "Use strict EAN13". If False, when trying to match a scanned barcode with
a rule whose encoding is EAN-13, if the barcode is of length 12 and, by prepending it by a 0,
the last digit is the correct checksum, we automatically prepend the barcode by 0 and try to
find a match with this new barcode. If "Use strict EAN13" is set to True, we look for a pattern
matching the original, 12-digit long, barcode.

Barcodes and patterns syntax
-----------------------------

Barcodes and patterns may contain any character. Characters \ . { and } in patterns have a special
meaning and thus have to be unspecialized (using \) to match their corresponding in barcodes. 
For example, barcode "a1.b2{c3\d4" matches the pattern "a1\.b2\{c3\\d4". 

Special character . in a pattern identifies any character (like in classical regular expressions).
Patterns are automatically completed by ".*". For instance, the barcode "abcde" matches the 
pattern ".bc". 

Special characters { and } are used to identify numerical content. A pattern can contain at 
most one set of { } and they must contain only N's and D's (N's represent the integer part of 
the numerical content, while D's represent the decimal part). For instance, the barcode 
"210025751" matches the pattern "21..{NNDD}." and encodes a value of 25.75.