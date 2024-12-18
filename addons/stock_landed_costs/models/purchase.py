from odoo import api,models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'is_landed_costs_line': self.product_id.landed_cost_ok})
        return res

    def _get_po_line_invoice_lines_su(self):
        po_line_invoices_lines = super()._get_po_line_invoice_lines_su()
        move = self.sudo().invoice_lines.move_id
        if move.landed_costs_ids.filtered(lambda lc: lc.state == 'done'):
            return po_line_invoices_lines | move.line_ids.filtered('is_landed_costs_line')
        return po_line_invoices_lines
