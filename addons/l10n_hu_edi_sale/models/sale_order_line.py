# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """

        res = super()._prepare_invoice_line(**optional_values)

        if self.is_downpayment:
            advanced_invoices = (
                self.invoice_lines.filtered(lambda line: line.move_id._is_downpayment())
                .mapped("move_id")
                .filtered(lambda i: i.state == "posted")
            )

            if advanced_invoices:
                res["name"] = res["name"] + " - " + ", ".join([move.name for move in advanced_invoices])

        return res
