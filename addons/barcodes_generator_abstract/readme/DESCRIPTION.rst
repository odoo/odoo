This module extends Odoo functionality, allowing user to generate barcode
depending on a given barcode rule for any Model.

For example, if the barcode pattern is "20.....{NNNDD}":

* the EAN13 code will begin with '20',
* followed by 5 digits (named *Barcode Base* in this module),
* followed by 5 others digits to define the variable price with 2 decimals,
* the last digit (the 13rd digit) is the control digit (i.e. the checksum).

With this module, it is possible to:

* Affect a pattern (barcode.rule) to a model

* Define a Barcode base:
    * manually, if the base of the barcode must be set by a user (typically an
      internal code defined in your company).
    * automatically by a sequence, if you want to let Odoo increment a
      sequence (typical case of a customer number incrementation).

* Generate a barcode, based on the defined pattern and the barcode base
