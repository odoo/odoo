Having this module installed allows a developer to render a float or integer field
without a thousands separator using

.. code-block:: xml

   <field name="id" options="{'enable_formatting': false}" />

Setting this option is supported for list and form views. In kanban views you
can simply use

.. code-block:: xml

    <t t-esc="record.id.raw_value" />

The code in this module is a backport of
https://github.com/odoo/odoo/commit/592794b397ba7f6468e45a5cc3e93681b1ed8578
from Odoo 17, so this module should not be ported beyond version 16.

The new `enable_formatting` option in Odoo 17 replaces the `format` option in
Odoo 15.
