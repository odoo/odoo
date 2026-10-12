# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _extract_extra_invoiced_lot_values(self, lot):
        extra_values = super()._extract_extra_invoiced_lot_values(lot)
        extra_values['lot_expiration_date'] = lot.expiration_date
        return extra_values
