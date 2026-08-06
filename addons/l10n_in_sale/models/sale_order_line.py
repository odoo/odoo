# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _affects_qty_invoiced(self, invoice_line):
        """Price adjustment credit / debit notes are to adjust total amounts
        and should not affect quantity invoiced"""
        return (
            super()._affects_qty_invoiced(invoice_line)
            and invoice_line.move_id.l10n_in_adjustment_type != 'price_adjustment'
        )
