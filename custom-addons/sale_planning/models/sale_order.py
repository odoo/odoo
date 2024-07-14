# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, fields, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    planning_hours_planned = fields.Float(compute='_compute_planning_hours')
    planning_hours_to_plan = fields.Float(compute='_compute_planning_hours')
    planning_first_sale_line_id = fields.Many2one('sale.order.line', compute='_compute_planning_first_sale_line_id')
    planning_initial_date = fields.Date(compute='_compute_planning_initial_date')

    @api.depends('order_line.planning_hours_to_plan', 'order_line.planning_hours_planned')
    def _compute_planning_hours(self):
        group_data = self.env['sale.order.line']._read_group([
            ('order_id', 'in', self.ids),
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

    # -----------------------------------------------------------------
    # Action methods
    # -----------------------------------------------------------------

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
            'context': {
                'default_sale_line_id': self.planning_first_sale_line_id.id,
                'search_default_group_by_role': 1,
                'search_default_group_by_resource': 2,
                'search_default_role_id': self.order_line.product_template_id.planning_role_id.ids,
                'initialDate': self.planning_initial_date,
                'planning_gantt_active_sale_order_id': self.id}
        })
        return action
