# -*- coding: utf-8 -*-

from odoo import models

class SaleOrder(models.Model):
    """Ensure a correct invoice by validating taxcloud taxes in the subscription before invoice generation."""
    _inherit = "sale.order"

    def _do_payment(self, payment_token, invoice, auto_commit=False):
        if invoice.fiscal_position_id.is_taxcloud and invoice.move_type in ["out_invoice", "out_refund"]:
            invoice.with_context(taxcloud_authorize_transaction=True).validate_taxes_on_invoice()
        return super()._do_payment(payment_token, invoice, auto_commit=auto_commit)
