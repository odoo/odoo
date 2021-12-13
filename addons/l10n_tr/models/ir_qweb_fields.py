from odoo import api, models, _


class Contact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def get_available_options(self):
        options = super(Contact, self).get_available_options()
        contact_fields = [
            {'field_name': 'l10n_tr_tax_office_id', 'label': _('Tax Office'), 'default': True},
        ]
        options['fields']['params']['params'] += contact_fields

        return options
