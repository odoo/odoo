# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class RestaurantPrinter(models.Model):
    _inherit = 'pos.printer'

    device_id = fields.Many2one('iot.device', 'IoT Device', domain="['&', ('type', '=', 'printer'), ('subtype', '=', 'receipt_printer'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    device_identifier = fields.Char(related="device_id.identifier")
    proxy_ip = fields.Char(size=45, related='device_id.iot_ip', store=True)

    @api.constrains('proxy_ip')
    def _constrains_proxy_ip(self):
        for record in self:
            if record.printer_type == 'iot' and record.device_id and not record.proxy_ip:
                raise ValidationError(_("Proxy IP cannot be empty."))

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ['device_identifier']
        return result
