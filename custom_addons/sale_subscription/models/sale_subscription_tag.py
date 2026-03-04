from odoo import fields, models


class SaleSubscriptionTag(models.Model):
    _name = "sale.subscription.tag"
    _description = "Subscription Tag"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="set null",
    )

