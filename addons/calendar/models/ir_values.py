# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools
from odoo.addons.calendar.models.calendar import calendar_id2real_id

class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    @api.returns('self', lambda value: value.id)
    def set_action(self, name, action_slot, model, action, res_id=False):
        if res_id:
            res_id = calendar_id2real_id(res_id)
        return super(IrValues, self).set_action(name, action_slot, model, action, res_id=res_id)

    @api.model
    @tools.ormcache_context('self._uid', 'action_slot', 'model', 'res_id', keys=('lang',))
    def get_actions(self, action_slot, model, res_id=False):
        if res_id:
            res_id = calendar_id2real_id(res_id)
        return super(IrValues, self).get_actions(action_slot, model, res_id=res_id)
