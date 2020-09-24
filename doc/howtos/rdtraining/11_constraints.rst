.. _howto/rdtraining/11_constraints:

====================
Part 11: Constraints
====================

The :ref:`previous chapter <howto/rdtraining/10_actions>` introduced the possibility to add some
business logic to our model. We can now link buttons to business code. But how can we prevent
users from encoding incorrect data? For example, in our real estate module, nothing prevents the
user to set a negative expected price.

Odoo provides two ways to set up automatically verified invariants:
:func:`Python constraints <odoo.api.constrains>` and
:attr:`SQL constraints <odoo.models.Model._sql_constraints>`.

SQL
===

**Reference**: the documentation related to this topic can be found in
:ref:`reference/orm/models` and in the `PostgreSQL's documentation`_.

.. note::

    **Goal**: at the end of this section:

    - Amounts should be (strictly) positive

    .. image:: 11_constraints/media/sql_01.gif
        :align: center
        :alt: Constraints on amounts

    - Property types and tags have a unique name

    .. image:: 11_constraints/media/sql_02.gif
        :align: center
        :alt: Constraints on names

SQL constraints are defined through the model attribute
:attr:`~odoo.models.Model._sql_constraints`. The latter is assigned to a list
of triples of strings ``(name, sql_definition, message)``, where ``name`` is a
valid SQL constraint name, ``sql_definition`` is a table_constraint_ expression,
and ``message`` is the error message.

You can find a simple example
`here <https://github.com/odoo/odoo/blob/24b0b6f07f65b6151d1d06150e376320a44fd20a/addons/analytic/models/analytic_account.py#L20-L23>`__.

.. exercise:: Add SQL constraints

    Add the following constraints in the corresponding models:

    - A property expected price must be strictly positive
    - A property selling price must be positive
    - An offer price must be strictly positive
    - A property tag name and property type name must be unique

    Tip: search for the ``unique`` keyword in the Odoo codebase for the name uniqueness.

Restart the server with the ``-u estate`` option to see the result. Note that you might have data
preventing an SQL constraint to be set. such error message might pop up.

.. code-block:: text

    ERROR rd-demo odoo.schema: Table 'estate_property_offer': unable to add constraint 'estate_property_offer_check_price' as CHECK(price > 0)

For example, if some offers have a price of zero, the constraint can't be applied. You can delete
the problematic data in order to apply the new constraints.

Python
======

**Reference**: the documentation related to this topic can be found in
:func:`~odoo.api.constrains`.

.. note::

    **Goal**: at the end of this section, it is not possible to accept an offer with a price
    lower than 90% of the expected price.

    .. image:: 11_constraints/media/python.gif
        :align: center
        :alt: Python constraint

SQL constraints are an efficient way of ensuring data consistency. However, it may be necessary
to make more complex checks requiring Python code. In this case, we need a Python constraint.

A Python constraint is defined as a method decorated with
:func:`~odoo.api.constrains`, and invoked on a recordset. The decorator
specifies which fields are involved in the constraint, so that the constraint is
automatically evaluated when one of them is modified. The method is expected to
raise an exception if its invariant is not satisfied::

    from odoo.exceptions import ValidationError

    ...

    @api.constrains('date_end')
    def _check_date_end(self):
        for record in self:
            if record.date_end < fields.Date.today():
                raise ValidationError("The end date cannot be set in the past")
        # all records passed the test, don't return anything

A simple example can be found
`here <https://github.com/odoo/odoo/blob/3783654b87851bdeb11e32da78bb5b62865b869a/addons/account/models/account_payment_term.py#L104-L108>`__.

.. exercise:: Add Python constraints

    Add a constraint so that the selling price cannot be lower than 90% of the expected price.

    Tip: the selling price is zero until an offer is validated. You will need to fine tune your
    check to take this into account.

    .. warning::

        Always use the :meth:`~odoo.tools.float_utils.float_compare` and
        :meth:`~odoo.tools.float_utils.float_is_zero` methods when comparing floats!

    Be sure the constraint is triggered every time the selling price or the expected price is changed!

SQL constrains are usually more efficient than Python constrains. When performance matters, always
prefer SQL over Python constrains.

Our real estate module is starting to look good: we added some business logic, and now we make sure
the data is consistent. However, the user interface is still a bit rough. Let's see how we can
improve it in the :ref:`next chapter <howto/rdtraining/12_sprinkles>`.

.. _PostgreSQL's documentation:
.. _table_constraint:
    https://www.postgresql.org/docs/current/ddl-constraints.html
