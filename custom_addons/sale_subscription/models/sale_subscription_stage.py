from odoo import fields, models


class SaleSubscriptionStage(models.Model):
    _name = "sale.subscription.stage"
    _description = "Subscription Stage"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ("draft", "New"),
            ("progress", "In Progress"),
            ("renew", "To Renew"),
            ("closed", "Closed"),
        ],
        required=True,
        default="draft",
        index=True,
    )
    description = fields.Text()
    fold = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="set null",
    )

