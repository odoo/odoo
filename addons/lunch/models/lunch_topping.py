from odoo import api, fields, models
from odoo.tools import formatLang


class LunchTopping(models.Model):
    _name = "lunch.topping"
    _description = "Lunch Extras"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    price = fields.Monetary(required=True)
    supplier_id = fields.Many2one(
        comodel_name="lunch.supplier",
        index="btree_not_null",
        ondelete="cascade",
    )
    topping_category = fields.Integer(
        default=1,
        required=True,
    )

    @api.depends("price")
    @api.depends_context("company")
    def _compute_display_name(self):
        currency_id = self.env.company.currency_id
        for topping in self:
            price = formatLang(self.env, topping.price, currency_obj=currency_id)
            topping.display_name = f"{topping.name} {price}"
