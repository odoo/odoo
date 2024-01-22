Odoo by default support:

::

   <tree delete="false" create="false">

with this module you can:

::

   <tree delete="state=='draft'" create="state!='sent'">

It works in any tree view, so you can use it in One2many.
