from odoo import fields, models


class LoyaltyMail(models.Model):
    _inherit = "loyalty.mail"

    pos_report_print_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Print Report",
        help="The report action to be executed when creating a coupon/gift card/loyalty card in the PoS.",
        domain=[("model", "=", "loyalty.card")],
    )
