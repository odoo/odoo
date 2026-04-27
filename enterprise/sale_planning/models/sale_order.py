# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import format_list

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    planning_hours_planned = fields.Float(compute='_compute_planning_hours', export_string_translation=False)
    planning_hours_to_plan = fields.Float(compute='_compute_planning_hours', export_string_translation=False)
    planning_first_sale_line_id = fields.Many2one('sale.order.line', compute='_compute_planning_first_sale_line_id', export_string_translation=False)
    planning_initial_date = fields.Date(compute='_compute_planning_initial_date', export_string_translation=False)

    @api.depends('order_line.planning_hours_to_plan', 'order_line.planning_hours_planned', 'order_line.product_id.planning_enabled')
    def _compute_planning_hours(self):
        group_data = self.env['sale.order.line']._read_group([
            ('order_id', 'in', self.ids),
            ('product_id.planning_enabled', '=', True),
        ], ['order_id'], ['planning_hours_to_plan:sum', 'planning_hours_planned:sum'])
        data_by_order = {
            order: (to_plan_sum, planned_sum)
            for order, to_plan_sum, planned_sum in group_data
        }
        for order in self:
            to_plan_sum, planned_sum = data_by_order.get(order._origin) or (0, 0)
            order.planning_hours_planned = planned_sum
            order.planning_hours_to_plan = to_plan_sum - planned_sum

    @api.depends('order_line.product_id.planning_enabled', 'order_line.planning_hours_to_plan', 'order_line.planning_hours_planned')
    def _compute_planning_first_sale_line_id(self):
        planning_sol = self.env['sale.order.line'].search([
            ('order_id', 'in', self.ids),
            ('product_id.planning_enabled', '=', True),
            ('planning_hours_to_plan', '>', 0),
        ])
        mapped_data = defaultdict(lambda: self.env['sale.order.line'])
        for sol in planning_sol:
            if not mapped_data[sol.order_id]:
                if sol.planning_hours_to_plan > sol.planning_hours_planned:
                    mapped_data[sol.order_id] = sol
        for order in self:
            order.planning_first_sale_line_id = mapped_data[order]

    @api.depends('order_line.planning_slot_ids.start_datetime')
    def _compute_planning_initial_date(self):
        group_data = self.env['planning.slot']._read_group([
            ('sale_order_id', 'in', self.ids)
        ], ['sale_order_id'], ['start_datetime:min'])
        mapped_data = {sale_order.id: start_datetime_min for sale_order, start_datetime_min in group_data}
        for order in self:
            if mapped_data.get(order.id):
                order.planning_initial_date = mapped_data[order.id].date()
            else:
                order.planning_initial_date = fields.Date.today()

    @api.constrains('company_id')
    def _check_company_id(self):
        for order, slots in self.env['planning.slot']._read_group(
            domain=[('sale_order_id', 'in', self.ids)],
            groupby=['sale_order_id'],
            aggregates=['id:recordset'],
        ):
            if not order.company_id:
                continue
            different_company_slots = slots.filtered(lambda slot: slot.company_id != order.company_id)
            if not different_company_slots:
                continue
            raise UserError(_(
                "You cannot update the company for sales order %(order_name)s as it's linked to shifts in another company.\n"
                "Please transfer shifts %(slots_names)s to the destination company first.",
                order_name=order.name,
                slots_names=format_list(self.env, [slot.display_name for slot in different_company_slots]),
            ))

    # -----------------------------------------------------------------
    # Action methods
    # -----------------------------------------------------------------

    def _action_cancel(self):
        result = super()._action_cancel()
        self.sudo()._unplanned_shift_deletion()
        return result

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a planning slot. """
        result = super()._action_confirm()
        self.order_line.sudo()._planning_slot_generation()
        return result

    def action_view_planning(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("planning.planning_action_schedule_by_resource")
        action.update({
            'name': _('View Planning'),
            'domain': [('role_id', 'in', self.order_line.product_template_id.planning_role_id.ids)],
            'context': {
                'default_sale_line_id': self.planning_first_sale_line_id.id,
                'search_default_group_by_role': 1,
                'search_default_group_by_resource': 2,
                'initialDate': self.planning_initial_date,
                'planning_gantt_active_sale_order_id': self.id}
        })
        return action

    def _unplanned_shift_deletion(self):
        unplanned_shift = self.env['planning.slot'].search([('sale_order_id', 'in', self.ids), '|', ('start_datetime', '=', False), ('resource_id', '=', False)])
        unplanned_shift.unlink()
