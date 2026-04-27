# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licens

from odoo import _
from odoo.addons.planning.controllers.main import ShiftController
from odoo.http import request
from odoo.tools import format_duration, format_amount


class ShiftControllerProject(ShiftController):

    def _planning_get(self, planning_token, employee_token, message=False):
        result = super()._planning_get(planning_token, employee_token, message)
        if not result:
            # one of the token does not match an employee/planning
            return
        result['open_slot_has_sale_line'] = any(s.sale_line_id for s in result['open_slots_ids'])
        result['unwanted_slot_has_sale_line'] = any(s.sale_line_id for s in result['unwanted_slots_ids'])
        return result

    def _get_slot_sale_line(self, slot):
        if not slot.sale_line_id:
            return None

        remaining_hours = slot.sale_line_id.planning_hours_to_plan - slot.sale_line_id.planning_hours_planned
        remaining_str = ''
        if remaining_hours:
            remaining_str = _('(%(remaining_hours)s remaining)', remaining_hours=format_duration(remaining_hours))
        sols_list = slot.sale_line_id.order_id.order_line
        price_unit = f'({format_amount(request.env, slot.sale_line_id.price_unit, slot.sale_line_id.currency_id)})' if len(sols_list) > 1 and len(sols_list.product_id) == 1 else ''
        return f'{slot.sale_line_id.display_name} {price_unit} {remaining_str}'

    def _get_slot_title(self, slot):
        return " - ".join(x for x in (super()._get_slot_title(slot), self._get_slot_sale_line(slot)) if x)

    def _get_slot_vals(self, slot):
        vals = super()._get_slot_vals(slot)
        vals['sale_line'] = self._get_slot_sale_line(slot)
        return vals
