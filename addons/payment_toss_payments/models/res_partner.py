from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # This unique identifier is to be registered on Toss Payment. It is useful for identifying
    # payments on customer request and analytics feature of Toss Payment for shop owners.
    tosspayments_customer_key = fields.Char(
        "Toss Payments SDK Customer Key",
        readonly=True,
        size=50,
        company_dependent=True,
    )
