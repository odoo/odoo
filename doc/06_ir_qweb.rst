.. _qweb:

====
QWeb
====

``t-field``
===========

The server version of qweb includes a directive dedicated specifically to
formatting and rendering field values from
:class:`~openerp.osv.orm.browse_record` objects.

The directive is implemented through
:meth:`~base.ir.ir_qweb.QWeb.render_tag_field` on the ``ir.qweb`` openerp
object, and generally delegates to converters for rendering. These converters
are obtained through :meth:`~base.ir.ir_qweb.QWeb.get_converter_for`.

By default, the key for obtaining a converter is the type of the field's
column, but this can be overridden by providing a ``widget`` as field option.

Field options are specified through ``t-field-options``, which must be a JSON
object (map). Custom widgets may define their own (possibly mandatory) options.

Global options
--------------

A global option ``html-escape`` is provided. It defaults to ``True``, and for
many (not all) fields it determines whether the field's output will be
html-escaped before being output.

Date and datetime converters
----------------------------

The default rendering for ``date`` and ``datetime`` fields. They render the
field's value according to the current user's ``lang.date_format`` and
``lang.time_format``. The ``datetime`` converter will also localize the value
to the user's timezone (as defined by the ``tz`` context key, or the timezone
in the user's profile if there is no ``tz`` key in the context).

A custom format can be provided to use a non-default rendering. The custom
format uses the ``format`` options key, and uses the
`ldml date format patterns`_ [#ldml]_.

For instance if one wanted a date field to be rendered as
"(month) (day of month)" rather than whatever the default is, one could use:

.. code-block:: xml

    <span t-field="object.datefield" t-field-options='{"format": "MMMM d"}'/>

Monetary converter (widget: ``monetary``)
-----------------------------------------

Used to format and render monetary value, requires a ``display_currency``
options value which is a path from the rendering context to a ``res.currency``
object. This object is used to set the right currency symbol, and set it at the
right position relative to the formatted value.

The field itself should be a float field.

Relative Datetime (widget: ``relative``)
----------------------------------------

Used on a ``datetime`` field, formats it relatively to the current time
(``datetime.now()``), e.g. if the field's value is 3 hours before now and the
user's lang is english, it will render to *3 hours ago*.

.. note:: this field uses babel's ``format_timedelta`` more or less directly
          and will only display the biggest unit and round up at 85% e.g.
          1 hour 15 minutes will be rendered as *1 hour*, and 55 minutes will
          also be rendered as *1 hour*.

.. warning:: this converter *requires* babel 1.0 or more recent.

Duration (widget: ``duration``)
-------------------------------

Renders a duration defined as a ``float`` to a human-readable localized string,
e.g. ``1.5`` as hours in an english locale will be rendered to
*1 hour 30 minutes*.

Requires a ``unit`` option which may be one of ``second``, ``minute``,
``hour``, ``day``, ``week``, ``month`` or ``year``. This specifies the unit in
which the value should be interpreted before formatting.

The duration must be a positive number, and no rounding is applied.

.. [#ldml] in part because `babel`_ is used for rendering, as ``strftime``
           would require altering the process's locale on the fly in order to
           get correctly localized date and time output. Babel uses the CLDR
           as its core and thus uses LDML date format patterns.

.. _babel: http://babel.pocoo.org

.. _ldml date format patterns:
    http://www.unicode.org/reports/tr35/tr35-dates.html#Date_Format_Patterns

