.. _howto/rdtraining/14_other_module:

====================================
Part 14: Interact With Other Modules
====================================

In the :ref:`previous chapter <howto/rdtraining/13_inheritance>`, we used inheritance to modify
the behavior of a module. In our real estate scenario, we would like to go a step further
and be able to generate invoices for our customers. Odoo provides an Invoicing module, so it
would be neat to create an invoice directly from our real estate module: once a property
is set to 'Sold', an invoice is created in the Invoicing application.

Concrete Example: Account Move
==============================

.. note::

    **Goal**: at the end of this section:

    - A new module ``estate_account`` is created
    - When a property is sold, an invoice is issued for the buyer

    .. image:: 14_other_module/media/create_inv.gif
        :align: center
        :alt: Invoice creation

Any time we interact with another module, we need to keep in mind the modularity. If we intend
to sell our application to real estate agencies, some of them may want the invoicing feature but
others may not want it.

Link Module
-----------

The common approach for such use cases is to create a 'link' module. In our case, the module
would depend on ``estate`` and ``account`` and would include the logic of the invoice creation
from the estate property. This way, the real estate and the accounting modules can be installed
independently. When both are installed, the link module provides the new feature.

.. exercise:: Create a link module

    Create the ``estate_account`` module, which depends on the ``estate`` and ``account`` modules.
    For now, it will be an empty shell.

    Tip: you already did this at the
    :ref:`beginning of the tutorial <howto/rdtraining/03_newapp>`. The process is very similar.

When the ``estate_account`` module appears in the list, go on and install it! You'll notice that
the Invoicing application is installed as well. This is expected since your module depends on it.
If you uninstall the Invoicing application, your module will be uninstalled as well.

Invoice Creation
----------------

It's now time to generate the invoice. We want to add a functionality to the
``estate.property`` model: when a property is sold, we need to add some logic. Does that sound
familiar? If not, it's a good idea to go back to the
:ref:`previous chapter <howto/rdtraining/13_inheritance>` since you might have missed something ;-)

As a first step, we need to extend the action called when pressing the
:ref:`'Sold' button <howto/rdtraining/10_actions>` on a property. To do so, we need to create a
:ref:`model inheritance <howto/rdtraining/13_inheritance>` in the ``estate_account`` module
for the ``estate.property`` model. For now, the action overridden will simply return the ``super``
call. Maybe an example will make things clearer::

    from odoo import models

    class InheritedModel(models.Model):
        _inherit = "inherited.model"

        def inherited_action(self):
            return super().inherited_action()

A practical example can be found
`here <https://github.com/odoo/odoo/blob/f1f48cdaab3dd7847e8546ad9887f24a9e2ed4c1/addons/event_sale/models/account_move.py#L7-L16>`__.

.. exercise:: First step of invoice creation

    - Create a ``estate_property.py`` file in the right folder of the ``estate_account`` module.
    - ``_inherit`` the ``estate.property`` model
    - Override ``action_sold`` method (you might have named it differently) to return the ``super``
      call.

    Tip: to make sure it works, add a ``print`` or a debugger breakpoint in the overridden method.

Is it working? If not, maybe check all Python files are correctly imported.

When the override is working, we can move forward and create the invoice. Unfortunately, there
is no easy way to know how to create any given object in Odoo. Most of the time, it is necessary
to have a look at its model to find the required fields and provide appropriate values.

A good way to learn is to look at how other modules do what you want to do. For example, one of
the basic flows of Sales is the creation of an invoice from a sales order. That looks like a good
starting point since it does exactly what we want to do. Take some time to read and understand the
`_create_invoices <https://github.com/odoo/odoo/blob/f1f48cdaab3dd7847e8546ad9887f24a9e2ed4c1/addons/sale/models/sale.py#L610-L717>`__
method. When you are done crying because this simple task looks awfully complex, we can move
forward on the tutorial.

To create an invoice, we need the following information:

- a ``partner_id``: the customer
- a ``move_type``: it has several `possible values <https://github.com/odoo/odoo/blob/f1f48cdaab3dd7847e8546ad9887f24a9e2ed4c1/addons/account/models/account_move.py#L138-L147>`__
- a ``journal_id``: the accounting journal

This is enough to create an empty invoice.

.. exercise:: Second step of invoice creation

    Create an empty ``account.move`` in the override of the ``action_sold`` method:

    - the ``partner_id`` is taken from the current ``estate.property``
    - the ``move_type`` should correspond to a 'Customer Invoice'
    - the ``journal_id`` must be a ``sale`` journal (in doubt, have a look
      `here <https://github.com/odoo/odoo/blob/f1f48cdaab3dd7847e8546ad9887f24a9e2ed4c1/addons/sale/models/sale.py#L534>`__)

    Tips:

    - to create an object, use ``self.env[model_name].create(values)``, where ``values``
      is a ``dict``.
    - the ``create`` method doesn't take recordsets as field values.

When a property is set to 'Sold', you should now have a new customer invoice created in
Invoicing / Customers / Invoices.

Obviously we don't have any invoice line so far. To create an invoice line, we need the following
information:

- ``name``: a description of the line
- ``quantity``
- ``price_unit``

Moreover, an invoice line needs to be linked to an invoice. The easiest and most efficient way
to link a line to an invoice is to include all lines at invoice creation. To do so, the
``invoice_line_ids`` field is included in the ``account.move`` creation, which is a
:class:`~odoo.fields.One2many`. One2many and Many2many use special 'commands' described in
:ref:`reference/orm/models/crud`. This format is a list of triplets executed sequentially, where
each triplet is a command to execute on the set of records. Here is a simple example to include
a One2many field ``line_ids`` at creation of a ``test.model``:: 

    def inherited_action(self):
        self.env["test.model"].create(
            {
                "name": "Test",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "field_1": "value_1",
                            "field_2": "value_2",
                        },
                    )
                ],
            }
        )
        return super().inherited_action()

.. exercise:: Third step of invoice creation

    Add two invoice lines during the creation of the ``account.move``. Each property sold will
    be invoiced following these conditions:

    - 6% of the selling price
    - an additional 100.0 of administrative fees

    Tip: Add the ``invoice_line_ids`` at creation following the example above.
    For each line, we need a ``name``, ``quantity`` and ``price_unit``.

This chapter might be one of the most difficult that was covered up to now, but it is the closest
to what Odoo development will be in practice. In the :ref:`next one <howto/rdtraining/15_qwebintro>`,
we will introduce the templating mechanism used in Odoo.
