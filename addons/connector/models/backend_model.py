# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)


from odoo import fields, models


class ConnectorBackend(models.AbstractModel):
    """An instance of an external backend to synchronize with.

    The backends have to ``_inherit`` this model in the connectors
    modules.

    The components articulates around a collection, which in the context of the
    connectors is called a Backend.

    It must be defined as a Model that inherits from ``'connector.backend'``.

    Example with the Magento Connector::

        # in connector_magento/models/magento_backend.py

        class MagentoBackend(models.Model):
            _name = 'magento.backend'
            _inherit = 'connector.backend'
            _description = 'Magento Backend'

            # the version in not mandatory
            @api.model
            def _select_versions(self):
                \"\"\" Available versions

                Can be inherited to add custom versions.
                \"\"\"
                return [('1.7', 'Magento 1.7')]

            location = fields.Char(string='Location', required=True)
            username = fields.Char(string='Username')
            password = fields.Char(string='Password')
            versions = fields.Selection(
                selection='_select_versions', required=True
            )


    """

    _name = "connector.backend"
    _inherit = ["collection.base"]
    _description = "Connector Backend"


class ExternalBinding(models.AbstractModel):
    """An abstract model for bindings to external records.

    An external binding is a binding between a backend and Odoo.  For
    example, for a partner, it could be ``magento.res.partner`` or for a
    product, ``magento.product``.

    The final model, will be an ``_inherits`` of the Odoo model and
    will ``_inherit`` this model.

    It will have a relation to the record (via ``_inherits``) and to the
    concrete backend model (``magento.backend`` for instance).

    It will also contains all the data relative to the backend for the
    record.

    It needs to implements at least these fields:

    odoo_id
        The many2one to the record it links (used by ``_inherits``).

    backend_id
        The many2one to the backend (for instance ``magento.backend``).

    external_id
        The ID on the backend.

    sync_date
        Last date of synchronization


    The definition of the field relations is to be done in the
    concrete classes because the relations themselves do not exist in
    this addon.

    For example, for a ``res.partner.category`` from Magento, I would have
    (this is a consolidation of all the columns from the abstract models,
    in ``magentoerpconnect`` you would not find that)::

        class MagentoResPartnerCategory(models.Model):
            _name = 'magento.res.partner.category'

            _inherits = {'res.partner.category': 'odoo_id'}

            odoo_id = fields.Many2one(comodel_name='res.partner.category',
                                      string='Partner Category',
                                      required=True,
                                      ondelete='cascade')
            backend_id = fields.Many2one(
                comodel_name='magento.backend',
                string='Magento Backend',
                required=True,
                ondelete='restrict')
            external_id = fields.Char(string='ID on Magento')
            tax_class_id = fields.Integer(string='Tax Class ID')

            _sql_constraints = [
                ('magento_uniq', 'unique(backend_id, magento_id)',
                 'Partner Tag with same ID on Magento already exists.'),
            ]


    """

    _name = "external.binding"
    _description = "External Binding (abstract)"

    sync_date = fields.Datetime(string="Last synchronization date")
    # add other fields in concrete models
    # XXX we could add a default 'external_id'
