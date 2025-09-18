from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    security_lead = fields.Float(
        related="company_id.security_lead",
        string="Security Lead Time",
        readonly=False,
    )
    use_security_lead = fields.Boolean(
        string="Security Lead Time for Sales",
        help="Margin of error for dates promised to customers. Products will be scheduled for delivery that many days earlier than the actual promised date, to cope with unexpected delays in the supply chain.",
        config_parameter="sale_stock.use_security_lead",
    )
    default_picking_policy = fields.Selection(
        selection=[
            ("direct", "Ship products as soon as available, with back orders"),
            ("one", "Ship all products at once"),
        ],
        string="Picking Policy",
        required=True,
        default="direct",
        default_model="sale.order",
    )

    @api.onchange("use_security_lead")
    def _onchange_use_security_lead(self):
        if not self.use_security_lead:
            self.security_lead = 0.0
