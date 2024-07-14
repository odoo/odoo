# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools import float_round, format_duration, float_compare, float_is_zero


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    planning_slot_ids = fields.One2many('planning.slot', 'sale_line_id')
    planning_hours_planned = fields.Float(compute='_compute_planning_hours_planned', store=True, compute_sudo=True)
    planning_hours_to_plan = fields.Float(compute='_compute_planning_hours_to_plan', store=True, compute_sudo=True)

    @api.depends('product_uom', 'product_uom_qty', 'product_id.planning_enabled', 'state')
    def _compute_planning_hours_to_plan(self):
        sol_planning = self.filtered_domain([('product_id.planning_enabled', '=', True), ('state', 'not in', ['draft', 'sent'])])
        if sol_planning:
            # For every confirmed SO service lines with slot generation, the qty are transformed into hours
            uom_hour = self.env.ref('uom.product_uom_hour')
            uom_unit = self.env.ref('uom.product_uom_unit')
            for sol in sol_planning:
                if sol.product_uom == uom_hour or sol.product_uom == uom_unit:
                    sol.planning_hours_to_plan = sol.product_uom_qty
                else:
                    sol.planning_hours_to_plan = float_round(
                        sol.product_uom._compute_quantity(sol.product_uom_qty, uom_hour, raise_if_failure=False),
                        precision_digits=2
                    )
        for line in self - sol_planning:
            line.planning_hours_to_plan = 0.0

    @api.depends('planning_slot_ids.allocated_hours', 'state')
    def _compute_planning_hours_planned(self):
        PlanningSlot = self.env['planning.slot']
        sol_planning = self.filtered_domain([('product_id.planning_enabled', '=', True), ('state', 'not in', ['draft', 'sent'])])

        # For every confirmed SO service lines with slot generation, the allocated hours on planned slots are summed
        group_data = PlanningSlot.with_context(sale_planning_prevent_recompute=True)._read_group([
            ('sale_line_id', 'in', sol_planning.ids),
            ('start_datetime', '!=', False),
            '|',
                ('resource_id', '=', False),
                ('resource_type', '!=', 'material'),
        ], ['sale_line_id'], ['allocated_hours:sum'])
        mapped_data = {sale_line.id: allocated_hours_sum for sale_line, allocated_hours_sum in group_data}
        for line in self:
            line.planning_hours_planned = mapped_data.get(line.id, 0.0)

        slots = PlanningSlot.search([
            ('start_datetime', '=', False),
            ('sale_line_id', 'in', self.ids),
        ])
        self.env.add_to_compute(PlanningSlot._fields['allocated_hours'], slots)
        slots._recompute_recordset(['allocated_hours'])


    # -----------------------------------------------------------------
    # ORM Override
    # -----------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.state == 'sale' and not line.is_expense:
                line.sudo()._planning_slot_generation()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self.filtered(lambda sol: not sol.is_expense)._post_process_planning_sale_line()
        return res

    @api.depends('product_id', 'planning_hours_to_plan', 'planning_hours_planned')
    @api.depends_context('with_planning_remaining_hours')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get('with_planning_remaining_hours'):
            return
        remaining = _("remaining")
        for line in self:
            name = line.display_name
            if line.product_id.planning_enabled:
                remaining_hours = line.planning_hours_to_plan - line.planning_hours_planned
                name = f'{name} ({format_duration(remaining_hours)} {remaining})'
            line.display_name = name

    # -----------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------

    def _post_process_planning_sale_line(self, ids_to_exclude=None):
        """
            This method ensures unscheduled slot attached to a sale order line
            has the right allocated_hours and is unique

            This method is mandatory due to cyclic dependencies between planning.slot
            and sale.order.line models.

            :param ids_to_exclude: the ids of the slots already being recomputed/written.
        """
        sol_planning = self.filtered('product_id.planning_enabled')
        if sol_planning:
            unscheduled_slots = self.env['planning.slot'].sudo().search([
                ('sale_line_id', 'in', sol_planning.ids),
                ('start_datetime', '=', False),
            ])
            sol_with_unscheduled_slot = set()
            slots_to_unlink = self.env['planning.slot']
            for slot in unscheduled_slots:
                if slot.sale_line_id.id in sol_with_unscheduled_slot:
                    # This slot has to be unlinked as an other exists for the
                    # same sale order line
                    # This 'unlink' will also avoid infinite loop
                    # => if there are 2 unscheduled slots for a sol,
                    # ==> then the first is written and triggers a recompute on the second
                    # ==> then the second is written and triggers a recompute on the first
                    slots_to_unlink |= slot
                else:
                    sol_with_unscheduled_slot.add(slot.sale_line_id.id)
                    if float_is_zero(slot.allocated_hours, precision_digits=2):
                        slots_to_unlink |= slot
            slots_to_unlink.unlink()

    def _planning_slot_generation(self):
        """
            For SO service lines with slot generation, create the planning slot.
        """
        vals_list = []
        for so_line in self:
            if (so_line.product_id.type == 'service'
               and so_line.product_id.planning_enabled
               and not so_line.planning_slot_ids
               and float_compare(
                    so_line.planning_hours_to_plan,
                    so_line.planning_hours_planned,
                    precision_digits=2) == 1):
                vals_list.append(so_line._planning_slot_values())
        self.env['planning.slot'].create(vals_list)

    def _planning_slot_values(self):
        return {
            'start_datetime': False,
            'end_datetime': False,
            'role_id': self.product_id.planning_role_id.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'allocated_hours': self.planning_hours_to_plan - self.planning_hours_planned,
            'allocated_percentage': 100,
            'company_id': self.company_id.id,
        }
