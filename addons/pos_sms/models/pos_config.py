from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    sms_receipt_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="Sms Receipt template",
        domain=[("model", "=", "pos.order")],
        help="SMS will be sent to the customer based on this template",
    )
