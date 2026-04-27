# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licens

from odoo import _
from odoo.addons.planning.controllers.main import ShiftController
from odoo.http import request


class ShiftControllerProject(ShiftController):

    def _planning_get(self, planning_token, employee_token, message=False):
        result = super()._planning_get(planning_token, employee_token, message)
        if not result:
            # one of the token does not match an employee/planning
            return
        result['open_slot_has_project'] = any(s.project_id for s in result['open_slots_ids'])
        result['unwanted_slot_has_project'] = any(s.project_id for s in result['unwanted_slots_ids'])
        return result

    def _get_slot_title(self, slot):
        return " - ".join(x for x in (super()._get_slot_title(slot), slot.project_id.name) if x)

    def _get_slot_vals(self, slot):
        vals = super()._get_slot_vals(slot)
        vals['project'] = slot.project_id.name
        return vals
