# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_order_sms_post = fields.Boolean(
        related="company_id.sale_order_sms_post", string="SMS Sale Order Post", readonly=False
    )
    sale_order_sms_post_template_id = fields.Many2one(
        related="company_id.sale_order_sms_post_template_id", readonly=False
    )

    sale_order_sms_confirm = fields.Boolean(
        related="company_id.sale_order_sms_confirm", string="SMS Sale Order Confirm", readonly=False
    )
    sale_order_sms_confirm_template_id = fields.Many2one(
        related="company_id.sale_order_sms_confirm_template_id", readonly=False
    )
