# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _anglo_saxon_sale_move_lines(self, i_line):
        for sale_line in i_line.sale_line_ids:
            for proc in sale_line.procurement_ids:
                if proc.purchase_line_id:
                    # if the invoice line is related to sale order lines having one of its
                    # procurement_ids with a purchase_line_id set, it means that it is a
                    # confirmed dropship and in that case we mustn't create the cost of
                    # sale line (because the product won't enter the stock)
                    return []
        return super(AccountInvoice, self)._anglo_saxon_sale_move_lines(i_line)
