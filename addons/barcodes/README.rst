==============================
Barcodes module documentation
==============================

This module brings barcode encoding logic and client-side barcode scanning utilities.


Barcodes encoding
==============================

The Barcodes module defines barcode nomenclatures whose rules identify specific type 
of items e.g. products, locations. It contains the following features:

- Patterns to identify barcodes containing a numerical value (e.g. weight, price)
- Definitin of barcode aliases that allow to identify the same product with different barcodes
- Unlimited barcode patterns and definitions,
- Support for encodings EAN-13, EAN-8 and UPC-A

Barcode encodings
-----------------

A barcode is an arbitrary long sequence of ASCII characters. An EAN-13 barcode is a 13 digit
barcode, whose 13th digit is the checksum. 

Simple barcodes and rules
-------------------------

The default nomenclature assumes an EAN-13 encoding for product barcodes. It defines a rule 
for Unit Products whose encoding is EAN-13, and whose pattern is '.', i.e. any barcode 
matches this pattern. Scanning the barcode of a product, say '5410013101703', matches this rule. 
The scanned item is thus identified as a Unit Product, and is retrieved from the product table.

Note: the special character '.' in patterns is matched by any character. To explicitely specify 
the '.' character in a pattern, escape it with '\'. The '\' character has to be escaped as well
('\\') to be explicitely specified.

Let us now suppose that we identify other items with barcodes, say stock locations. We define a
new rule in the nomenclature with the corresponding type (in our example, the type is 'Location'),
and whose pattern is e.g. '414.', that is, any location barcode starts with '414'. Scanning a barcode
location, say '41401', matches this Location rule, and the corresponding location is retrieved from
the location table.

Note: Rules have a sequence field which indicates the order the rules are evaluated (ASC). In our 
previous examples, the Unit Product rule should have a larger sequence that then Location rule, 
because we want the latter one to be evaluated first.

Barcodes with numerical content
--------------------------------

Barcodes may encode numerical content, which is decoded by the barcodes module. To that purpose,
one have to define a new rule for barcodes with numerical content (e.g. barcodes for Weighted 
Products). The numerical content in a pattern is specified between braces (special characters '{' and 
'}'). The content of the braces must be a sequence of 'N's (representing the whole part of the numerical 
content) followed by a sequence of 'D's (representing the decimal part of the numerical content). 
For instance, let us define a new rule for Weighted Products whose pattern is '21.....{NNDDD}.'. Since
we assume EAN-13 encoding for product barcodes, the encoding of this rule should be EAN-13 as well.

Let us now assume that we want to write a barcode for a given Weighted Product, say oranges. We first 
have to define in product oranges a barcode that will match the Weighted Product rule. This barcode 
must start with '21' and be a correct EAN-13 barcode (i.e. the 13th digit must be a correct checksum). 
Moreover, all the numerical content must be set to a '0'. For instance, let us set the barcode to 
'2100001000004'. 

We now want to write a barcode for 2.75kg of oranges. This barcode should be '2100001027506' (the 
numerical content of this barcode is '02750', and the correct checksum is '6'). When scanned, this 
barcode matches the Weighted Product rule (since is starts with '21'). The numerical content is extracted, 
and replaced by a sequence of '0's. The correct checksum is then computed for the obtained barcode 
('2100001000004') and the corresponding product (oranges) is retrieved from product table.

Note: the special characters '{' and '}' in patterns are used to identify numerical content. To 
explicitely specify '{' or '}' in a pattern, they must be escaped.


Strict EAN-13 field of barcode nomenclatures
--------------------------------------------

Many barcode scanners strip the leading zero when scanning EAN-13 barcodes. Barcode nomenclatures
have a boolean field "Use strict EAN13". If False, when trying to match a scanned barcode with
a rule whose encoding is EAN-13, if the barcode is of length 12 and, by prepending it by a 0,
the last digit is the correct checksum, we automatically prepend the barcode by 0 and try to
find a match with this new barcode. If "Use strict EAN13" is set to True, we look for a pattern
matching the original, 12-digit long, barcode.



Barcodes scanning
==============================

Scanning
--------

Use a USB scanner (that mimics keyboard inputs) in order to work with barcodes in Odoo.
The scanner must be configured to use no prefix and a carriage return or tab as suffix.
The delay between each character input must be less than or equal to 50 milliseconds.
Most barcode scanners will work out of the box.
However, make sure the scanner uses the same keyboard layout as the device it's plugged in.
Either by setting the device's keyboard layout to US QWERTY (default value for most readers)
or by changing the scanner's keyboard layout (check the manual).


Barcode events
------------------------------

When the module barcodes is installed, it instanciate a singleton of the javascript class BarcodeEvents.
The purpose of this component is to listen to keypresses to detect barcodes, then dispatch those barcodes
on core.bus inside a 'barcode_event'.
All keypress events are buffered until there is no more keypress during 50ms or a carriage return / tab is
inputted (because most barcode scanners use this as a suffix).
If the buffered keys looks like a barcode, an event is triggered :
core.bus.trigger('barcode_scanned', barcode);
Otherwise, the keypresses are 'resent'. However, for security reasons, a keypress event programmatically
crafted doesn't trigger native browser behaviors. For this reason, BarcodeEvents doesn't intercept keypresses
whose target is an editable element (eg. input) or when ctrl/cmd/alt is pushed.
To catch keypresses targetting an editable element, it must have the attribute barcode_events="true".


Barcode handlers
------------------------------

To keep the web client consistent, components that want to listen to barcode events should include BarcodeHandlerMixin.
It requires method on_barcode_scanned(barcode) to be implemented and exposes methods start_listening and stop_listening
As long as it is the descendant of a View managed by a ViewManager is only listens while the view is attached.


Form view barcode handler
------------------------------

It is possible for a form view to listen to barcode events, handle them client side and/or server-side.
When the barcode is handled server-side, it works like an onchange. The relevant model must include the
BarcodeEventsMixin and redefine method on_barcode_scanned. This method receives the barcode scanned and
the `self` is a pseudo-record representing the content of the form view, just like in @api.onchange methods.
Barcodes prefixed with 'O-CMD' or 'O-BTN' are reserved for special features and are never passed to on_barcode_scanned.
The form view barcode handler can be extended to add client-side handling. Please refer to the (hopefully
well enough) documented file for more informations.


Button barcode handler
------------------------------

Add an attribute 'barcode_trigger' to a button to be able to trigger it by scanning a barcode. Example :
<button name="validate" type="object" barcode_trigger="validate"/> will be triggered when a barcode containing
"O-BTN.validate" is scanned.
