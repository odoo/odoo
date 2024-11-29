from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_sms_receipt_template_id = fields.Many2one('sms.template', related='pos_config_id.sms_receipt_template_id', readonly=False)
