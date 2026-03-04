from odoo import api, fields, models


class SaleSubscriptionTemplate(models.Model):
    _name = "sale.subscription.template"
    _description = "Subscription Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    recurring_rule_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("yearly", "Year(s)"),
        ],
        required=True,
        default="monthly",
        string="Recurrence",
    )
    recurring_interval = fields.Integer(required=True, default=1)
    description = fields.Text()
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
    )
    subscription_ids = fields.One2many(
        comodel_name="sale.subscription",
        inverse_name="template_id",
        string="Subscriptions",
    )
    subscription_count = fields.Integer(compute="_compute_subscription_count")

    @api.depends("subscription_ids")
    def _compute_subscription_count(self):
        for template in self:
            template.subscription_count = len(template.subscription_ids)

    def action_view_subscription_ids(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Subscriptions",
            "res_model": "sale.subscription",
            "view_mode": "list,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }

