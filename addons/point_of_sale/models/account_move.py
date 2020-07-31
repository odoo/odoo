# -*- coding: utf-8 -*-

from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_refund_tax_audit_condition(self, aml):
        # Overridden so that the returns can be detected as credit notes by the tax audit computation
        rslt = super()._get_refund_tax_audit_condition(aml)

        if aml.invoice_id:
            # We don't need to check the pos orders for this move lines if an invoice
            # is linked to it ; we know that the invoice type tells us whether it's a refund
            return rslt

        pos_orders_count = self.env['pos.order'].search_count([('account_move', '=', aml.move_id.id)])
        return rslt or (pos_orders_count and aml.debit > 0)