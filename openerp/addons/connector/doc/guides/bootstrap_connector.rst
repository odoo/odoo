.. _bootstrap-connector:


########################
Boostrapping a connector
########################

We'll see the steps to bootstrap a new connector.

Besides that, you may want to use the existing connectors to have some
real implementation examples:

* `Odoo Magento Connector`_
* `Odoo Prestashop Connector`_

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
``connector_coffee/__openerp__.py`` manifest.


.. code-block:: python
   :emphasize-lines: 4,5

    # -*- coding: utf-8 -*-
    {'name': 'Coffee Connector',
     'version': '1.0.0',
     'category': 'Connector',
     'depends': ['connector',
                 ],
     'author': 'Myself',
     'license': 'AGPL-3',
     'description': """
    Coffee Connector
    ================

    Connect Odoo to my coffee machine.

    Features:

    * Poor a coffee when Odoo is busy for too long
    """,
     'data': [],
     'installable': True,
     'application': False,
    }

Nothing special but 2 things to note:

* It depends from ``connector``.
* The module category should be ``Connector``.

Of course, we also need to create the ``__init__.py`` file where we will
put the imports of our python modules.


********************
Declare the backends
********************

Our module is compatible with the coffee machines:

 * Coffee 1900
 * Coffee 2900

So we'll declare a backend `coffee`, the generic entity,
and a backend per version.

Put this in ``connector_coffee/backend.py``::

    import openerp.addons.connector.backend as backend


    coffee = backend.Backend('coffee')
    coffee1900 = backend.Backend(parent=coffee, version='1900')
    coffee2900 = backend.Backend(parent=coffee, version='2900')


*************
Backend Model
*************

We declared the backends, but we need a model to configure them.

We create a model ``coffee.backend`` which is an ``_inherit`` of
``connector.backend``. In ``connector_coffee/coffee_model.py``::

    from openerp import fields, models, api


    class CoffeeBackend(models.Model):
        _name = 'coffee.backend'
        _description = 'Coffee Backend'
        _inherit = 'connector.backend'

        _backend_type = 'coffee'

        @api.model
        def _select_versions(self):
            """ Available versions

            Can be inherited to add custom versions.
            """
            return [('1900', 'Version 1900'),
                    ('2900', 'Version 2900')]

        version = fields.Selection(
            selection='_select_versions',
            string='Version',
            required=True,
        )
        location = fields.Char(string='Location')
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')
        default_lang_id = fields.Many2one(
            comodel_name='res.lang',
            string='Default Language',
        )

Notes:

* The ``_backend_type`` must be the same than the name in the backend in
  `Declare the backends`_.
* the versions should be the same than the ones declared in `Declare the backends`_.
* We may want to add as many fields as we want to configure our
  connection or configuration regarding the backend in that model.


****************
Abstract Binding
****************

If we have many :ref:`binding`,
we may want to create an abstract model for them.

It can be as follows (in ``connector_coffee/connector.py``)::

    from openerp import models, fields


    class CoffeeBinding(models.AbstractModel):
        _name = 'coffee.binding'
        _inherit = 'external.binding'
        _description = 'Coffee Binding (abstract)'

        # 'openerp_id': openerp-side id must be declared in concrete model
        backend_id = fields.Many2one(
            comodel_name='coffee.backend',
            string='Coffee Backend',
            required=True,
            ondelete='restrict',
        )
        # fields.char because 0 is a valid coffee ID
        coffee_id = fields.Char(string='ID in the Coffee Machine',
                                select=True)


***********
Environment
***********

We'll often need to create a new environment to work with.
I propose to create a helper method which build it for us (in
``connector_coffee/connector.py``::

    from openerp.addons.connector.connector import Environment


    def get_environment(session, model_name, backend_id):
        """ Create an environment to work with. """
        backend_record = session.env['coffee.backend'].browse(backend_id)
        env = Environment(backend_record, session, model_name)
        lang = backend_record.default_lang_id
        lang_code = lang.code if lang else 'en_US'
        if lang_code == session.context.get('lang'):
            return env
        else:
            with env.session.change_context(lang=lang_code):
                return env

Note that the part regarding the language definition is totally
optional but I left it as an example.


***********
Checkpoints
***********

When new records are imported and need a review, :ref:`checkpoint` are
created. I propose to create a helper too in
``connector_coffee/connector.py``::

    from openerp.addons.connector.checkpoint import checkpoint


    def add_checkpoint(session, model_name, record_id, backend_id):
        return checkpoint.add_checkpoint(session, model_name, record_id,
                                         'coffee.backend', backend_id)

*********************
ConnectorUnit classes
*********************

We'll probably need to create synchronizers, mappers, backend adapters,
binders and maybe our own types of ConnectorUnit classes.

Their implementation can vary a lot. Have a look on the
`Odoo Magento Connector`_ and `Odoo Prestashop Connector`_ projects.


.. _`Odoo Magento Connector`: https://github.com/OCA/connector-magento
.. _`Odoo Prestashop Connector`: https://github.com/OCA/connector-prestashop
