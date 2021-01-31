# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    def _default_sms_sale_order_confirm_template(self):
        try:
            return self.env.ref("deltatech_sms_sale.sms_template_data_sale_order_confirm").id
        except ValueError:
            return False

    def _default_sms_sale_order_post_template(self):
        try:
            return self.env.ref("deltatech_sms_sale.sms_template_data_sale_order_post").id
        except ValueError:
            return False

    sale_order_sms_post = fields.Boolean("SMS Post", default=True)
    sale_order_sms_post_template_id = fields.Many2one(
        "sms.template",
        string="SMS Template Order Post",
        domain="[('model', '=', 'sale.order')]",
        default=_default_sms_sale_order_post_template,
        help="SMS sent to the customer once the sale order is posted from website.",
    )

    sale_order_sms_confirm = fields.Boolean("SMS Confirm", default=True)
    sale_order_sms_confirm_template_id = fields.Many2one(
        "sms.template",
        string="SMS Template Order Confirmed",
        domain="[('model', '=', 'sale.order')]",
        default=_default_sms_sale_order_confirm_template,
        help="SMS sent to the customer once the sale order is confirmed.",
    )
