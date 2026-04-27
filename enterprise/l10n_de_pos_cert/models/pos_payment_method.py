# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if self.env.company.l10n_de_is_germany_and_fiskaly():
            fields += ['journal_id']
        return fields
