.. _bootstrap-connector:


########################
Boostrapping a connector
########################

We'll see the steps to bootstrap a new connector.

Besides that, you may want to use the existing connectors to have some
real implementation examples:

* `Odoo Magento Connector`_
* `Odoo Prestashop Connector`_

Be aware that the connector API has changed in Odoo 10.0, so the examples
might be outdated.

Some boilerplate is necessary, so this document will guide you through
some steps. Please also take a look on the :ref:`naming-convention`.

For the sake of the example, we'll imagine we have to synchronize
Odoo with a coffee machine.

*************
Odoo Manifest
*************

As we want to synchronize Odoo with a coffee machine, we'll name
our connector connector_coffee.

First, we need to create the Odoo addons itself, editing the
``connector_coffee/__manifest__.py`` manifest.


.. code-block:: python
   :emphasize-lines: 3,4

    {'name': 'Coffee Connector',
     'version': '1.0.0',
     'category': 'Connector',
     'depends': ['connector',
                 ],
     'author': 'Myself',
     'license': 'LGPL-3',
     'description': """
    Coffee Connector
    ================

    Connect Odoo to my coffee machine.

    Features:

    * Pour a coffee when Odoo is busy for too long
    """,
     'data': [],
     'installable': True,
    }

Nothing special but 2 things to note:

* It depends from ``connector``. ``connector`` itself depends from
  ``queue_job``, ``component`` and ``component_event``. ``queue_job`` is in the
  `OCA/queue`_ repository.
* The module category should be ``Connector``.

Of course, we also need to create the ``__init__.py`` file where we will
put the imports of our python modules.

.. _OCA/queue: https://github.com/OCA/queue


*************
Backend Model
*************

Reference: :ref:`api-backend-model`

We need to create a Backend representing the external service.  Every record we
synchronize will be linked with a record of ``coffee.backend``.  This backend
is our *collection* of Components.

The ``coffee.backend`` model is an ``_inherit`` of ``connector.backend``. In
``connector_coffee/models/coffee_binding.py``::

    from odoo import api, fields, models


    class CoffeeBackend(models.Model):
        _name = 'coffee.backend'
        _description = 'Coffee Backend'
        _inherit = 'connector.backend'

        location = fields.Char(string='Location')
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')

Notes:

* We can other fields for the configuration of the connection or the
  synchronizations.

****************
Abstract Binding
****************

Reference: :ref:`api-binding-model`

In order to share common features between all the bindings (see
:ref:`binding`), create an abstract binding model.

It can be as follows (in ``connector_coffee/models/coffee_binding.py``)::

    from odoo import models, fields


    class CoffeeBinding(models.AbstractModel):
        _name = 'coffee.binding'
        _inherit = 'external.binding'
        _description = 'Coffee Binding (abstract)'

        # odoo_id = odoo-side id must be declared in concrete model
        backend_id = fields.Many2one(
            comodel_name='coffee.backend',
            string='Coffee Backend',
            required=True,
            ondelete='restrict',
        )
        coffee_id = fields.Integer(string='ID in the Coffee Machine',
                                   index=True)

Notes:

* This model inherit from ``external.binding``
* Any number of fields or methods can be added


**********
Components
**********

Reference: :ref:`api-component`

We'll probably need to create synchronizers, mappers, backend adapters,
binders and maybe our own kind of components.

Their implementation can vary from a project to another. Have a look on the
`Odoo Magento Connector`_ and `Odoo Prestashop Connector`_ projects.


.. _`Odoo Magento Connector`: https://github.com/OCA/connector-magento
.. _`Odoo Prestashop Connector`: https://github.com/OCA/connector-prestashop
