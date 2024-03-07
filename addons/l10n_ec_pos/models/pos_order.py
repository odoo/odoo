# -*- coding: utf-8 -*-
from odoo import models

class PosOrder(models.Model):
    _inherit = "pos.order"

    def _create_invoice(self, move_vals):
        invoice = super(PosOrder, self)._create_invoice(move_vals)
        if self.payment_ids:
            sri_payment_methods = self.payment_ids.sudo().mapped('payment_method_id.l10n_ec_sri_payment_id')
            if len(sri_payment_methods) == 1:
                invoice.l10n_ec_sri_payment_id = sri_payment_methods
        return invoice
