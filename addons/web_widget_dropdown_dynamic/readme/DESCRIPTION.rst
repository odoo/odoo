Dynamic dropdown widget that supports resolving options from backend of:

 * ``fields.Char``
 * ``fields.Integer``
 * ``fields.Selection``

**NOTE:** This widget is not intended to *extend* ``fields.Selection``, but to
filter selection values. For fully-dynamic set of options, use ``fields.Char``
instead.
