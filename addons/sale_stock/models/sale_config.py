from odoo import fields, models


class SaleConfig(models.Model):
    _inherit = "sale.config"

    security_lead = fields.Float(
        string="Sales Safety Days",
        default=0.0,
        required=True,
        help="Margin of error for dates promised to customers. "
        "Products will be scheduled for procurement and delivery "
        "that many days earlier than the actual promised date, to "
        "cope with unexpected delays in the supply chain.",
    )
