from odoo import fields, models


class SaleSubscriptionCloseReason(models.Model):
    _name = "sale.subscription.close.reason"
    _description = "Subscription Close Reason"
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        ondelete="set null",
    )

