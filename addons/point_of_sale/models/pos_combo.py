from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosCombo(models.Model):
    """
    This model is used to allow the pos user to create menus.
    This means that products can be grouped together and sold as a combo.
    """
    _name = "pos.combo"
    _description = "Product combo choices"

    name = fields.Char(string="Name", required=True)
    combo_line_ids = fields.One2many("pos.combo.line", "combo_id", string="Products in Combo")
    num_of_products = fields.Integer("No of Products", compute="_compute_num_of_products")

    @api.depends("combo_line_ids")
    def _compute_num_of_products(self):
        # optimization trick to count the number of products in each combo
        for rec, num_of_products in self.env["pos.combo.line"]._read_group([("combo_id", "in", self.ids)], groupby=["combo_id"], aggregates=["__count"]):
            rec.num_of_products = num_of_products

    @api.constrains("combo_line_ids")
    def _check_combo_line_ids_is_not_null(self):
        if any(not rec.combo_line_ids for rec in self):
            raise ValidationError(_("Please add products in combo."))
