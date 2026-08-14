# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        # No account.payments loaded by default.
        # at a time of importing SOs it will manually load the linked payments.
        return fields.Domain.FALSE

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'move_id']
