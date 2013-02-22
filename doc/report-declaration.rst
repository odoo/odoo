.. _report-declaration:

Report declaration
==================

.. versionadded:: 7.1

Before version 7.1, report declaration could be done in two different ways:
either via a ``<report>`` tag in XML, or via such a tag and a class
instanciation in a Python module. Instanciating a class in a Python module was
necessary when a custom parser was used.

In version 7.1, the recommended way to register a report is to use only the
``<report>`` XML tag. The tag can now support an additional ``parser``
attribute. The value for that attibute must be a fully-qualified class name,
without the leading ``openerp.addons.`` namespace.

.. note::
  The rational to deprecate the manual class instanciation is to make all
  reports visible in the database, have a unique way to declare reports
  instead of two, and remove the need to maintain a registry of reports in
  memory.

