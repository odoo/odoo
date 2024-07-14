# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = 'choose.delivery.package'

    @api.model
    def default_get(self, fields):
        res = super(ChooseDeliveryPackage, self).default_get(fields)
        if 'iot_device_id' in fields and res.get('picking_id'):
            picking_id = self.env['stock.picking'].browse(res['picking_id'])
            iot_scale_ids = picking_id.picking_type_id.iot_scale_ids
            if len(iot_scale_ids) == 1:
                res['iot_device_id'] = iot_scale_ids.id
        return res

    available_scale_ids = fields.Many2many('iot.device', related='picking_id.picking_type_id.iot_scale_ids')
    iot_device_id = fields.Many2one('iot.device', "Scale")
    iot_device_identifier = fields.Char(related='iot_device_id.identifier')
    iot_ip = fields.Char(related='iot_device_id.iot_ip')
    manual_measurement = fields.Boolean(related='iot_device_id.manual_measurement')
