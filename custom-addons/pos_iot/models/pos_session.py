# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if len(loaded_data['iot.device']) > 0:
            loaded_data['pos.config']['use_proxy'] = True

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        new_models_to_load = [model for model in ['iot.device', 'iot.box'] if model not in result]
        result.extend(new_models_to_load)
        return result

    def _loader_params_iot_device(self):
        device_ids = self.config_id.iot_device_ids.ids
        for payment in self.config_id.payment_method_ids:
            if payment.iot_device_id:
                device_ids.append(payment.iot_device_id.id)

        return {
            'search_params': {
                'domain': [('id', 'in', device_ids)],
                'fields': ['iot_ip', 'iot_id', 'identifier', 'type', 'manual_measurement'],
            },
        }

    def _get_pos_ui_iot_device(self, params):
        return self.env['iot.device'].search_read(**params['search_params'])

    def _loader_params_iot_box(self):
        devices = self._context.get('loaded_data')['iot.device']
        iot_box_ids = set()
        for device in devices:
            iot_box = device['iot_id']
            if iot_box:
                iot_box_ids.add(iot_box[0])

        return {'search_params': {'domain': [('id', 'in', [*iot_box_ids])], 'fields': ['ip', 'ip_url', 'name']}}

    def _get_pos_ui_iot_box(self, params):
        return self.env['iot.box'].search_read(**params['search_params'])

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].append('iot_device_id')
        return result

    def _loader_params_pos_printer(self):
        result = super()._loader_params_pos_printer()
        result['search_params']['fields'].append('device_identifier')
        return result
