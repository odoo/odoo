# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class IotDevice(models.Model):
    _inherit = 'iot.device'

    qcp_test_type = fields.Char(compute='_compute_qcp_test_type')
    quality_point_ids = fields.One2many('quality.point', 'device_id')

    @api.depends('type')
    def _compute_qcp_test_type(self):
        types = {'device': 'measure', 'scale': 'measure', 'camera': 'picture', 'printer': 'print_label'}
        for device in self:
            device.qcp_test_type = types.get(device.type, '')
