.. _howto/rdtraining/firstui:

=============================
Finally, Some UI To Play With
=============================

Data Files (XML)
================

Actions
=======

Menus
=====

Field Attributes And View
=========================

Default values
--------------

Any field can be given a default value. In the field definition, add the option
``default=X`` where ``X`` is either a Python literal value (boolean, integer,
float, string), or a function taking a recordset and returning a value::

    name = fields.Char(default="Unknown")
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)

.. exercise:: Active objects – Default values

    * Define the start_date default value as today (see
      :class:`~odoo.fields.Date`).
    * Add a field ``active`` in the class Session, and set sessions as active by
      default.

    .. only:: solutions


Special Fields
--------------

active and state
