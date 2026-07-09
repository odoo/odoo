# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiView(models.Model):
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
            if type_ != 'qweb' and type_ in _view_info
        }

    def _get_view_info(self):
        return {
            'list': {'icon': 'reorder'},
            'form': {'icon': 'contact_mail', 'multi_record': False},
            'graph': {'icon': 'area_chart'},
            'pivot': {'icon': 'oi_view-pivot'},
            'kanban': {'icon': 'oi_view-kanban'},
            'calendar': {'icon': 'calendar_today'},
            'search': {'icon': 'search'},
        }
