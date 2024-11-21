# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class View(models.Model):
    _inherit = 'ir.ui.view'

    def get_view_info(self):
        _view_info = self._get_view_info()
        return {
            type_: {
                'display_name': display_name,
                'icon': _view_info[type_]['icon'],
                'multi_record': _view_info[type_].get('multi_record', True),
            }
            for (type_, display_name)
            in self.fields_get(['type'], ['selection'])['type']['selection']
            if type_ != 'qweb'
        }

    def _get_view_info(self):
        return {
            'list': {'icon': 'oi oi-view-list'},
            'form': {'icon': 'fa fa-address-card', 'multi_record': False},
            'graph': {'icon': 'fa fa-area-chart'},
            'pivot': {'icon': 'oi oi-view-pivot'},
            'kanban': {'icon': 'oi oi-view-kanban'},
            'calendar': {'icon': 'fa fa-calendar'},
            'search': {'icon': 'oi oi-search'},
        }
