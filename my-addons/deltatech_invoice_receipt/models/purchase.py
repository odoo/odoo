# ©  2015-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    notice = fields.Boolean()


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    from_invoice_id = fields.Many2one("account.move", string="Generated from the invoice")

    def receipt_to_stock(self):
        """
        Matoda aceasta este utilizata si in fast purchase
        """
        for purchase_order in self:
            for picking in purchase_order.picking_ids:
                if picking.state == "confirmed":
                    picking.action_assign()
                    if picking.state != "assigned":
                        raise UserError(_("The stock transfer cannot be validated!"))
                if picking.state == "assigned":
                    picking.write({"notice": False, "origin": purchase_order.partner_ref})
                    for move_line in picking.move_lines:
                        if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                            move_line.write({"quantity_done": move_line.product_uom_qty})
                        else:
                            move_line.unlink()
                    # pentru a se prelua data din comanda de achizitie
                    picking.with_context(force_period_date=purchase_order.date_order)._action_done()
