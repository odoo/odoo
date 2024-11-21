# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_action_per_item(self):
        action = self.env.ref('account.action_move_out_invoice_type').id
        return {invoice.id: action for invoice in self}
