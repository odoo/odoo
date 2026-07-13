# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_refund_reason_list(self):
        return self.env['account.move']._fields['l10n_es_tbai_refund_reason']._description_selection(self.env)
