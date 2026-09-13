from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_stock_sms_confirmation_template_id(self):
        try:
            return self.env.ref("stock_sms.sms_template_data_stock_delivery").id
        except ValueError:
            return False

    stock_sms_confirmation_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        default=_default_stock_sms_confirmation_template_id,
        domain="[('model', '=', 'stock.picking')]",
        help="SMS sent to the customer once the order is delivered.",
    )
    has_received_warning_stock_sms = fields.Boolean()
