# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from datetime import datetime
from time import strftime


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_hr_employee(self):
        if len(self.config_id.employee_ids) > 0:
            domain = ['&', ('company_id', '=', self.config_id.company_id.id), '|', ('user_id', '=', self.user_id.id), ('id', 'in', self.config_id.employee_ids.ids)]
        else:
            domain = [('company_id', '=', self.config_id.company_id.id)]
        return {'search_params': {'domain': domain, 'fields': ['name', 'id', 'user_id'], 'load': False}}

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('detailed_type')
        return result

    def _get_pos_ui_pos_category(self, params):
        result = super()._get_pos_ui_pos_category(params)
        if not self.config_id.module_pos_restaurant:
            #Category is created on the fly and is given -1 as arbitrary id to prevent collision
            result.append({'id': -1, 'name': 'Events', 'parent_id': False, 'child_id': [], 'write_date': datetime.now(), 'has_image': False})
        return result

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if not self.config_id.module_pos_restaurant:
            result.extend(['event.event', 'event.event.ticket'])
        return result

    def _get_pos_ui_event_event(self, params):
        event_ids = self.env['event.event'].search(params['search_params']['domain'])
        event_ids = event_ids.filtered(lambda l: l.event_registrations_started)   # computed field not searchable
        event = event_ids.read(params['search_params']['fields'])
        for elem in event:
            elem['image_128'] = bool(elem['image'])
            del elem['image']
        return event

    def _loader_params_event_event(self):
        domain = [('available_in_pos', '=', True), ('date_end', '>=', strftime('%Y-%m-%d 00:00:00'))]
        fields = ['name', 'event_registrations_open', 'date_begin', 'date_end', 'write_date', 'image']
        return {'search_params': {'domain': domain, 'fields': fields}}

    def _get_pos_ui_event_event_ticket(self, params):
        return self.env['event.event.ticket'].search_read(**params['search_params'])

    def get_domain_event_event_ticket(self):
        event_ids = list(map(lambda event: event['id'], self._get_pos_ui_event_event(self._loader_params_event_event())))
        return [('event_id', 'in', event_ids)]

    def _loader_params_event_event_ticket(self):
        fields = ['name', 'description', 'sale_available', 'event_id', 'product_id', 'seats_available', 'write_date', 'price']
        return {'search_params': {'domain': self.get_domain_event_event_ticket(), 'fields': fields}}
