from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    so_reference_type = fields.Selection(
        selection=[
            ("so_name", "Based on Document Reference"),
            ("partner", "Based on Customer ID"),
        ],
        string="Communication",
        default="so_name",
        help="You can set here the communication type that will appear on sales orders."
        "The communication will be given to the customer when they choose the payment method.",
    )
