# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def unlink(self):
        if not self:
            return True

        # Retrieve the Tax Adjustment entries to reverse.
        moves_to_reverse = self.env['account.move'].search([('tax_advanced_adjust_rec_id', 'in', self.ids)])

        # Unlink partials before doing anything else to avoid 'Record has already been deleted' due to the recursion.
        res = super().unlink()

        # Reverse Tax Adjustment entries entries.
        if moves_to_reverse:
            default_values_list = [{
                'date': move._get_accounting_date(move.date, True),
                'ref': _('Reversal of: %s') % move.name,
            } for move in moves_to_reverse]
            moves_to_reverse._reverse_moves(default_values_list, cancel=True)

        return res
