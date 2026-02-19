# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class StockBarcodesAction(models.Model):
    _name = "stock.barcodes.action"
    _description = "Actions for barcode interface"
    _order = "sequence, id"

    name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=100)
    action_window_id = fields.Many2one(
        comodel_name="ir.actions.act_window", string="Action window"
    )
    context = fields.Char()
    key_shortcut = fields.Integer()
    key_char_shortcut = fields.Char()
    icon_class = fields.Char()

    def open_action(self):
        action = self.action_window_id.sudo().read()[0]
        action_context = safe_eval(action["context"])
        ctx = self.env.context.copy()
        if action_context:
            ctx.update(action_context)
        if self.context:
            ctx.update(safe_eval(self.context))
        if action_context.get("inventory_mode", False):
            return self.open_inventory_action(ctx)
        action["context"] = ctx
        return action

    def open_inventory_action(self, ctx):
        option_group = self.env.ref(
            "stock_barcodes.stock_barcodes_option_group_inventory"
        )
        vals = {
            "option_group_id": option_group.id,
            "manual_entry": option_group.manual_entry,
            "display_read_quant": option_group.display_read_quant,
        }
        if option_group.get_option_value("location_id", "filled_default"):
            vals["location_id"] = (
                self.env["stock.warehouse"].search([], limit=1).lot_stock_id.id
            )
        wiz = self.env["wiz.stock.barcodes.read.inventory"].create(vals)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_barcodes.action_stock_barcodes_read_inventory"
        )
        action["res_id"] = wiz.id
        action["context"] = ctx
        return action
