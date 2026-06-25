from odoo import models, fields


class TourDiscountRule(models.Model):
    _name = "tour.discount.rule"
    _description = "Tour Discount Rule"

    name = fields.Char(required=True)
    discount_type = fields.Selection(
        selection=[("group", "Group Size"), ("family_children", "Family with Children")],
        required=True,
    )
    min_people = fields.Integer(string="Minimum People")
    percentage = fields.Float(string="Discount (%)")
    fixed_amount = fields.Float()
    active = fields.Boolean(default=True)
