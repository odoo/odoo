# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models

class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.ondelete(at_uninstall=False)
    def _unlink_sdd_mandate_and_invoice(self):
        for partial in self:
            for move in {partial.debit_move_id.move_id, partial.credit_move_id.move_id}:
                if (move.is_invoice(include_receipts=True) and move.sdd_mandate_id):
                    payments_with_mandate = move._get_reconciled_payments().filtered(lambda p: p.sdd_mandate_id and p.move_id not in {partial.debit_move_id.move_id, partial.credit_move_id.move_id})
                    if not payments_with_mandate:
                        move.sdd_mandate_id = False
