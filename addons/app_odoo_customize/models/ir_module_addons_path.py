# -*- coding: utf-8 -*-

import random
from odoo import api, fields, models, modules, tools, _


class IrModuleAddonsPath(models.Model):
    _name = "ir.module.addons.path"
    _description = 'Module Addons Path'

    def _default_bg_color(self):
        colors = ['#F06050', '#F4A45F', '#F7CD2E', '#6CC1ED', '#EB7E7F', '#5CC482',
                  '#2c8297', '#D8485E', '#9365B8', '#804967', '#475576', ]
        res = '#FFFFFF'
        try:
            res = random.choice(colors)
        except:
            pass
        return res

    name = fields.Char(string='Short Name')
    path = fields.Char(string='Path')
    path_temp = fields.Char(string='Path Temp')
    color = fields.Char(default=_default_bg_color)
    module_ids = fields.One2many('ir.module.module', 'addons_path_id')
    module_count = fields.Integer(compute='_compute_module_count')

    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)

    def open_apps_view(self):
        self.ensure_one()

        return {'type': 'ir.actions.act_window',
                'name': 'Apps',
                'view_mode': 'kanban,tree,form',
                'res_model': 'ir.module.module',
                'context': {},
                'domain': [('addons_path_id', '=', self.id)],
                }
