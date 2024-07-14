# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def validate_taxes_on_invoice(self):
        """ Override of account_taxcloud to prevent sending authorization requests to TaxCloud. """
        self.ensure_one()

        if any(sale_line.amazon_item_ref for sale_line in self.invoice_line_ids.sale_line_ids):
            return True  # The invoice was created from an Amazon sales order, don't sync it
        return super().validate_taxes_on_invoice()
