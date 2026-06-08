from odoo import fields, models


class L10nSaEdiDocument(models.Model):
    _inherit = 'l10n_sa_edi.document'
    pos_order_id = fields.Many2one('pos.order', compute='_compute_resource')

    def _l10n_sa_get_resource_field_mapping(self):
        return {
            **super()._l10n_sa_get_resource_field_mapping(),
            'pos.order': 'pos_order_id',
        }
