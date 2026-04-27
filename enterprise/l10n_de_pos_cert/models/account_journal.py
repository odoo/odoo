# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = ['pos.load.mixin', 'account.journal']

    @api.model
    def _load_pos_data_domain(self, data):
        if self.env.company.l10n_de_is_germany_and_fiskaly():
            return [('pos_payment_method_ids.config_ids', 'in', [data['pos.config']['data'][0]['id']])]
        return super()._load_pos_data_domain(data)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if self.env.company.l10n_de_is_germany_and_fiskaly():
            fields.append('id')
        return fields
