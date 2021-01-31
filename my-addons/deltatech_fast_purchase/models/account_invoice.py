# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    # in 13 nu mai exista aceasta metoda - functionalitatea a fost mutata i
    # n modeulul puchase.line in metoda _prepare_account_move_line
    # def _prepare_invoice_line_from_po_line(self, line):
    #     res = super(AccountMove, self)._prepare_invoice_line_from_po_line(line)
    #     if self.type == 'in_refund':
    #         if line.product_id.purchase_method == 'purchase':
    #             qty = line.qty_invoiced - line.product_qty
    #         else:
    #             qty = line.qty_invoiced - line.qty_received
    #         if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
    #             qty = 0.0
    #         res['quantity'] = qty
    #     return res
