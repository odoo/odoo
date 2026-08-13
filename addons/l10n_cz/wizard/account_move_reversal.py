# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if self.country_code == 'CZ':
            res['taxable_supply_date'] = self.date
        return res
