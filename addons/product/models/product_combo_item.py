# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductComboItem(models.Model):
    _name = "product.combo.item"
    _description = "Product Combo Item"
    _check_company_auto = True

    company_id = fields.Many2one(
        related="combo_id.company_id",
        store=True,
        precompute=True,
    )
    combo_id = fields.Many2one(
        comodel_name="product.combo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Options",
        required=True,
        check_company=True,
        domain=[("type", "!=", "combo")],
        ondelete="restrict",
    )
    currency_id = fields.Many2one(
        related="product_id.currency_id",
        comodel_name="res.currency",
    )
    lst_price = fields.Float(
        related="product_id.lst_price",
        string="Original Price",
        digits="Product Price",
    )
    extra_price = fields.Float(
        string="Extra Price",
        digits="Product Price",
        default=0.0,
    )

    @api.constrains("product_id")
    def _check_product_id_no_combo(self):
        if any(combo_item.product_id.type == "combo" for combo_item in self):
            raise ValidationError(
                _('A combo choice can\'t contain products of type "combo".')
            )
