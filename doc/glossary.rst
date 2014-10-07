:orphan: true

.. glossary::

    external id
    external identifier
    external identifiers
        string identifier stored in ``ir.model.data``, can be used to refer
        to a record regardless of its database identifier during data imports
        or export/import roundtrips.

        External identifiers are in the form :samp:`{module}.{id}` (e.g.
        ``account.invoice_graph``). From within a module, the
        :samp:`{module}.` prefix can be left out.

    format string
        inspired by `jinja variables`_, format strings allow more easily
        mixing literal content and computed content (expressions): content
        between ``{{`` and ``}}`` is interpreted as an expression and
        evaluated, other content is interpreted as literal strings and
        displayed as-is

.. _jinja variables: http://jinja.pocoo.org/docs/dev/templates/#variables
