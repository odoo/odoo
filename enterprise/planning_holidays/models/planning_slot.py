# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Slot(models.Model):
    _inherit = 'planning.slot'

    leave_warning = fields.Char(compute='_compute_leave_warning', compute_sudo=True, export_string_translation=False)
    is_absent = fields.Boolean(
        compute='_compute_leave_warning', search='_search_is_absent',
        compute_sudo=True, readonly=True, export_string_translation=False)

    @api.depends_context('lang')
    @api.depends('start_datetime', 'end_datetime', 'employee_id')
    def _compute_leave_warning(self):

        assigned_slots = self.filtered(lambda s: s.employee_id and s.start_datetime)
        (self - assigned_slots).leave_warning = False
        (self - assigned_slots).is_absent = False

        if not assigned_slots:
            return

        min_date = min(assigned_slots.mapped('start_datetime'))
        date_from = min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(assigned_slots.mapped('end_datetime')),
            employee_ids=assigned_slots.mapped('employee_id')
        )

        for slot in assigned_slots:
            warning = False
            slot_leaves = leaves.get(slot.employee_id.id)
            if slot_leaves:
                warning = self.env['hr.leave']._get_leave_warning(
                    leaves=slot_leaves,
                    employee=slot.employee_id,
                    date_from=slot.start_datetime,
                    date_to=slot.end_datetime
                )
            slot.leave_warning = warning
            slot.is_absent = bool(warning)

    @api.model
    def _search_is_absent(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        today = fields.Datetime.today()
        slots = self.search([
            ('employee_id', '!=', False),
            ('end_datetime', '>', today),  # only fetch the slots containing today in their period or shifts in the future
        ])
        if not slots:
            return []

        min_date = min(slots.mapped('start_datetime'))
        date_from = max(min_date, today)
        mapped_leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(slots.mapped('end_datetime')),
            employee_ids=slots.mapped('employee_id'),
        )

        slot_ids = []
        for slot in slots.filtered(lambda s: s.employee_id.id in mapped_leaves):
            leaves = mapped_leaves[slot.employee_id.id]
            period = self.env['hr.leave']._group_leaves(leaves, slot.employee_id, slot.start_datetime, slot.end_datetime)
            if period:
                slot_ids.append(slot.id)
        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', slot_ids)]
