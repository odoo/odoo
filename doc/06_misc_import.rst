.. _bulk-import:

Bulk Import
===========

OpenERP has included a bulk import facility for CSV-ish files for a
long time. With 7.0, both the interface and internal implementation
have been redone, resulting in
:meth:`~openerp.osv.orm.BaseModel.load`.

.. note::

    the previous bulk-loading method,
    :meth:`~openerp.osv.orm.BaseModel.import_data`, remains for
    backwards compatibility but was re-implemented on top of
    :meth:`~openerp.osv.orm.BaseModel.load`, while its interface is
    unchanged its precise behavior has likely been altered for some
    cases (it shouldn't throw exceptions anymore in many cases where
    it previously did)

This document attempts to explain the behavior and limitations of
:meth:`~openerp.osv.orm.BaseModel.load`.

Data
----

The input ``data`` is a regular row-major matrix of strings (in Python
datatype terms, a ``list`` of rows, each row being a ``list`` of
``str``, all rows must be of equal length). Each row must be the same
length as the ``fields`` list preceding it in the argslist.

Each field of ``fields`` maps to a (potentially relational and nested)
field of the model under import, and the corresponding column of the
``data`` matrix provides a value for the field for each record.

Generally speaking each row of the input yields a record of output,
and each cell of a row yields a value for the corresponding field of
the row's record. There is currently one exception for this rule:

One to Many fields
++++++++++++++++++

Because O2M fields contain multiple records "embedded" in the main
one, and these sub-records are fully dependent on the main record (are
no other references to the sub-records in the system), they have to be
spliced into the matrix somehow. This is done by adding lines composed
*only* of o2m record fields below the main record:

.. literalinclude:: 06_misc_import_o2m.txt

the sections in double-lines represent the span of two o2m
fields. During parsing, they are extracted into their own ``data``
matrix for the o2m field they correspond to.

Import process
--------------

Here are the phases of import. Note that the concept of "phases" is
fuzzy as it's currently more of a pipeline, each record moves through
the entire pipeline before the next one is processed.

Extraction
++++++++++

The first phase of the import is the extraction of the current row
(and potentially a section of rows following it if it has One to Many
fields) into a record dictionary. The keys are the ``fields``
originally passed to :meth:`~openerp.osv.orm.BaseModel.load`, and the
values are either the string value at the corresponding cell (for
non-relational fields) or a list of sub-records (for all relational
fields).

This phase also generates the ``rows`` indexes for any
:ref:`import-message` produced thereafter.

Conversion
++++++++++

This second phase takes the record dicts, extracts the :term:`database
ID` and :term:`external ID` if present and attempts to convert each
field to a type matching what OpenERP expects to write.

* Empty fields (empty strings) are replaced with the ``False`` value

* Non-empty fields are converted through
  :class:`~openerp.addons.base.ir.ir_fields.ir_fields_converter`

.. note:: if a field is specified in the import, its default will *never* be
          used. If some records need to have a value and others need to use
          the model's default, either specify that default explicitly or do
          the import in two phases.

Char, text and binary fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Are returned as-is, without any alteration.

Boolean fields
~~~~~~~~~~~~~~

The string value is compared (in a case-insensitive manner) to ``0``,
``false`` and ``no`` as well of any translation thereof loaded in the
database. If the value matches one of these, the field is set to
``False``.

Otherwise the field is compared to ``1``, ``true`` and ``yes`` (and
any translation of these in the database). The field is always set to
``True``, but if the value does not match one of these a warning will
also be output.

Integers and float fields
~~~~~~~~~~~~~~~~~~~~~~~~~

The field is parsed with Python's built-in conversion routines
(``int`` and ``float`` respectively), if the conversion fails an error
is generated.

Selection fields
~~~~~~~~~~~~~~~~

The field is compared to 1. the values of the selection (first part of
each selection tuple) and 2. all translations of the selection label
found in the database.

If one of these is matched, the corresponding value is set on the
field.

Otherwise an error is generated.

The same process applies to both list-type and function-type selection
fields.

Many to One field
~~~~~~~~~~~~~~~~~

If the specified field is the relational field itself (``m2o``), the
value is used in a ``name_search``. The first record returned by
``name_search`` is used as the field's value.

If ``name_search`` finds no value, an error is generated. If
``name_search`` finds multiple value, a warning is generated to warn
the user of ``name_search`` collisions.

If the specified field is a :term:`external ID` (``m2o/id``), the
corresponding record it looked up in the database and used as the
field's value. If no record is found matching the provided external
ID, an error is generated.

If the specified field is a :term:`database ID` (``m2o/.id``), the
process is the same as for external ids (on database identifiers
instead of external ones).

Many to Many field
~~~~~~~~~~~~~~~~~~

The field's value is interpreted as a comma-separated list of names,
external ids or database ids. For each one, the process previously
used for the many to one field is applied.

One to Many field
~~~~~~~~~~~~~~~~~

For each o2m record extracted, if the record has a ``name``,
:term:`external ID` or :term:`database ID` the :term:`database ID` is
looked up and checked through the same process as for m2o fields.

If a :term:`database ID` was found, a LINK_TO command is emmitted,
followed by an UPDATE with the non-db values for the relational field.

Otherwise a CREATE command is emmitted.

Date fields
~~~~~~~~~~~

The value's format is checked against
:data:`~openerp.tools.misc.DEFAULT_SERVER_DATE_FORMAT`, an error is
generated if it does not match the specified format.

Datetime fields
~~~~~~~~~~~~~~~

The value's format is checked against
:data:`~openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`, an error
is generated if it does not match.

The value is then interpreted as a datetime in the user's
timezone. The timezone is specified thus:

* If the import ``context`` contains a ``tz`` key with a valid
  timezone name, this is the timezone of the datetime.

* Otherwise if the user performing the import has a ``tz`` attribute
  set to a valid timezone name, this is the timezone of the datetime.

* Otherwise interpret the datetime as being in the ``UTC`` timezone.

Create/Write
++++++++++++

If the conversion was successful, the converted record is then saved
to the database via ``(ir.model.data)._update``.

Error handling
++++++++++++++

The import process will only catch 2 types of exceptions to convert
them to error messages: ``ValueError`` during the conversion process,
and sub-exceptions of ``psycopg2.Error`` during the create/write
process.

The import process uses savepoint to:

* protect the overall transaction from the failure of each ``_update``
  call, if an ``_update`` call fails the savepoint is rolled back and
  the import process keeps going in order to obtain as many error
  messages as possible during each run.

* protect the import as a whole, a savepoint is created before
  starting and if any error is generated that savepoint is rolled
  back. The rest of the transaction (anything not within the import
  process) will be left untouched.

.. _import-message:
.. _import-messages:

Messages
--------

A message is a dictionary with 5 mandatory keys and one optional key:

``type``
    the type of message, either ``warning`` or ``error``. Any
    ``error`` message indicates the import failed and was rolled back.

``message``
    the message's actual text, which should be translated and can be
    shown to the user directly

``rows``
    a dict with 2 keys ``from`` and ``to``, indicates the range of
    rows in ``data`` which generated the message

``record``
    a single integer, for warnings the index of the record which
    generated the message (can be obtained from a non-false ``ids``
    result)

``field``
    the name of the (logical) OpenERP field for which the error or
    warning was generated

``moreinfo`` (optional)
    A string, a list or a dict, leading to more information about the
    warning.

    * If ``moreinfo`` is a string, it is a supplementary warnings
      message which should be hidden by default
    * If ``moreinfo`` is a list, it provides a number of possible or
      alternative values for the string
    * If ``moreinfo`` is a dict, it is an OpenERP action descriptor
      which can be executed to get more information about the issues
      with the field. If present, the ``help`` key serves as a label
      for the action (e.g. the text of the link).
