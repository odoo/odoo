# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosPreset(models.Model):
    _inherit = 'pos.preset'

    sms_receipt_template_id = fields.Many2one(
        comodel_name='sms.template',
        string="SMS Receipt Template",
        domain=[('model', '=', 'pos.order')],
        help="SMS template used to send the order confirmation to the customer after a successful self order.",
    )

    @api.model
    def _load_pos_self_data_fields(self, config):
        return super()._load_pos_self_data_fields(config) + ['sms_receipt_template_id']
