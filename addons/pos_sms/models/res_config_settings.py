from odoo import fields, models
from odoo.addons import base


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    pos_sms_receipt_template_id = fields.Many2one('sms.template', related='pos_config_id.sms_receipt_template_id', readonly=False)
