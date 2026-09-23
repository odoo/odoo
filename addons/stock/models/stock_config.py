from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockConfig(models.Model):
    _name = "stock.config"
    _description = "A company's stock configuration"
    _inherit = ["mixin.company.config"]

    internal_transit_location_id = fields.Many2one(
        comodel_name="stock.location",
        ondelete="restrict",
        check_company=True,
        help="Used for resupply routes between warehouses that belong to this company",
    )
    stock_move_email_validation = fields.Boolean(string="Email Confirmation picking")
    stock_mail_confirmation_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template confirmation picking",
        default=lambda self: self._default_stock_mail_confirmation_template_id(),
        domain="[('model', '=', 'stock.picking')]",
        help="Email sent to the customer once the order is done.",
    )
    annual_inventory_month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        default="12",
        help="Annual inventory month for products not in a location with a cyclic inventory date. Set to no month if no automatic annual inventory.",
    )
    annual_inventory_day = fields.Integer(
        string="Day of the month",
        default=31,
        help="""Day of the month when the annual inventory should occur. If zero or negative, then the first day of the month will be selected instead.
        If greater than the last day of a month, then the last day of the month will be selected instead.""",
    )
    horizon_days = fields.Integer(
        string="Replenishment Horizon",
        default=365,
        required=True,
        help="""Configure your horizon to trigger reordering rules earlier to get
         a head start on replenishment and avoid delays, or trigger it just-in-time
         ('0 days') to avoid overstocking.""",
    )
    stock_text_confirmation = fields.Boolean()
    stock_confirmation_type = fields.Selection(
        selection=[("sms", "SMS")],
        string="Confirmation Channel",
        default="sms",
        help="Channel used to send the delivery text confirmation to the customer.",
    )

    @api.constrains("horizon_days")
    def _check_horizon_days(self):
        for company in self:
            if company.horizon_days < 0:
                raise ValidationError(
                    self.env._("The replenishment horizon cannot be negative.")
                )

    def _default_stock_mail_confirmation_template_id(self):
        template = self.env.ref(
            "stock.mail_template_data_delivery_confirmation", raise_if_not_found=False
        )
        return template.id if template else False
