from odoo import _, api, fields, models
from odoo.tools import float_round


class LunchCashmove(models.Model):
    """Two types of cashmoves: payment (credit) or order (debit)"""

    _name = "lunch.cashmove"
    _description = "Lunch Cashmove"
    _order = "date desc"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.uid,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    amount = fields.Float(required=True)
    description = fields.Text()

    def _compute_display_name(self):
        for cashmove in self:
            cashmove.display_name = "{} {}".format(
                _("Lunch Cashmove"), "#%s" % (cashmove.id or "_")
            )

    @api.model
    def get_wallet_balance(self, user, include_config=True):
        result = float_round(
            sum(
                move["amount"]
                for move in self.env["lunch.cashmove.report"].search_read(
                    [("user_id", "=", user.id)], ["amount"]
                )
            ),
            precision_digits=2,
        )
        if include_config:
            result += user.company_id.lunch_minimum_threshold
        return result
