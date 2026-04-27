# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IotDevice(models.Model):
    _name = 'iot.device'
    _inherit = ['iot.device', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        return [('id', 'in', config_id.iot_device_ids.ids + [payment.iot_device_id.id for payment in config_id.payment_method_ids if payment.iot_device_id])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['iot_ip', 'iot_id', 'identifier', 'type', 'manual_measurement']
