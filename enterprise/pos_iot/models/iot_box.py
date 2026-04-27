# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IotBox(models.Model):
    _name = 'iot.box'
    _inherit = ['iot.box', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', [device['iot_id'] for device in data['iot.device']['data'] if device['iot_id']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['ip', 'ip_url', 'name']
