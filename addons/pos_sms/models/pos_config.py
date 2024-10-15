from odoo import fields, models
from odoo.addons import point_of_sale


class PosConfig(point_of_sale.PosConfig):

    sms_receipt_template_id = fields.Many2one('sms.template', string="Sms Receipt template", domain=[('model', '=', 'pos.order')], help="SMS will be sent to the customer based on this template")
