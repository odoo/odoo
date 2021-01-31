# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import safe_eval


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def receipt_to_stock(self):
        for purchase_order in self:
            for picking in purchase_order.picking_ids:
                if picking.state == "confirmed":
                    picking.action_assign()
                    if picking.state != "assigned":
                        raise UserError(_("The stock transfer cannot be validated!"))
                if picking.state == "assigned":
                    picking.write({"notice": False, "origin": purchase_order.partner_ref or self.name})
                    for move_line in picking.move_lines:
                        if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                            move_line.write({"quantity_done": move_line.product_uom_qty})
                        else:
                            move_line.unlink()
                    # pentru a se prelua data din comanda de achizitie
                    picking.with_context(force_period_date=purchase_order.date_order)._action_done()

    def action_button_confirm_to_invoice(self):
        if self.state == "draft":
            self.button_confirm()  # confirma comanda

        params = self.env["ir.config_parameter"].sudo()

        validate_invoice = params.get_param("fast_purchase.validate_invoice", default="True")
        validate_invoice = safe_eval(validate_invoice)

        self.receipt_to_stock()

        action = self.action_create_invoice()

        return action

    def action_button_confirm_notice(self):
        picking_ids = self.env["stock.picking"]
        for picking in self.picking_ids:
            if picking.state == "assigned":
                picking.write({"notice": True})
                picking_ids |= picking

        if not picking_ids:
            return

        result = self.action_create_invoice()

        return result
