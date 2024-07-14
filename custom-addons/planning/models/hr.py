# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid

from datetime import datetime, time, timedelta
from odoo import fields, models, _, api

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = "hr.employee"

    def _default_employee_token(self):
        return str(uuid.uuid4())

    default_planning_role_id = fields.Many2one(related='resource_id.default_role_id', readonly=False, groups='hr.group_hr_user',
        help="Role that will be selected by default when creating a shift for this employee.\n"
             "This role will also have precedence over the other roles of the employee when planning orders.")
    planning_role_ids = fields.Many2many(related='resource_id.role_ids', readonly=False, groups='hr.group_hr_user',
        help="Roles that the employee can fill in. When creating a shift for this employee, only the shift templates for these roles will be displayed.\n"
             "Similarly, only the open shifts available for these roles will be sent to the employee when the schedule is published.\n"
             "Additionally, the employee will only be assigned orders for these roles (with the default planning role having precedence over the other ones).\n"
             "Leave empty for the employee to be assigned shifts regardless of the role.")
    employee_token = fields.Char('Security Token', default=_default_employee_token, groups='hr.group_hr_user',
                                 copy=False, readonly=True)

    _sql_constraints = [
        ('employee_token_unique', 'unique(employee_token)', 'Error: each employee token must be unique')
    ]

    @api.depends('job_title')
    @api.depends_context('show_job_title')
    def _compute_display_name(self):
        if not self.env.context.get('show_job_title'):
            return super()._compute_display_name()
        for employee in self:
            employee.display_name = f"{employee.name} ({employee.job_title})" if employee.job_title else employee.name

    def _init_column(self, column_name):
        # to avoid generating a single default employee_token when installing the module,
        # we need to set the default row by row for this column
        if column_name == "employee_token":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row", self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE employee_token IS NULL" % self._table)
            acc_ids = self.env.cr.dictfetchall()
            values_args = [(acc_id['id'], self._default_employee_token()) for acc_id in acc_ids]
            query = """
                UPDATE {table}
                SET employee_token = vals.token
                FROM (VALUES %s) AS vals(id, token)
                WHERE {table}.id = vals.id
            """.format(table=self._table)
            self.env.cr.execute_values(query, values_args)
        else:
            super(Employee, self)._init_column(column_name)

    def _planning_get_url(self, planning):
        result = {}
        for employee in self:
            if employee.user_id and employee.user_id.has_group('planning.group_planning_user'):
                result[employee.id] = '/web?date_start=%s&date_end=%s#action=planning.planning_action_open_shift&menu_id=' % (planning.date_start, planning.date_end)
            else:
                result[employee.id] = '/planning/%s/%s' % (planning.access_token, employee.employee_token)
        return result

    def _slot_get_url(self, slot):
        action_id = self.env.ref('planning.planning_action_open_shift').id
        menu_id = self.env.ref('planning.planning_menu_root').id
        dbname = self.env.cr.dbname or [''],
        start_date = slot.start_datetime.date() if slot else ''
        end_date = slot.end_datetime.date() if slot else ''
        link = "/web?date_start=%s&date_end=%s#action=%s&model=planning.slot&menu_id=%s&db=%s" % (start_date, end_date, action_id, menu_id, dbname[0])
        return {employee.id: link for employee in self}

    @api.onchange('default_planning_role_id')
    def _onchange_default_planning_role_id(self):
        self.planning_role_ids |= self.default_planning_role_id

    @api.onchange('planning_role_ids')
    def _onchange_planning_role_ids(self):
        if self.default_planning_role_id.id not in self.planning_role_ids.ids:
            self.default_planning_role_id = self.planning_role_ids[:1]

    def action_archive(self):
        res = super().action_archive()
        departure_date = datetime.combine(fields.Date.context_today(self) + timedelta(days=1), time.min)
        planning_slots = self.env['planning.slot'].sudo().search([
            ('resource_id', 'in', self.resource_id.ids),
            ('end_datetime', '>=', departure_date),
        ])
        planning_slots._manage_archived_resources(departure_date)
        return res

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    has_slots = fields.Boolean(compute='_compute_has_slots')

    def _compute_has_slots(self):
        self.env.cr.execute("""
        SELECT id, EXISTS(SELECT 1 FROM planning_slot WHERE employee_id = e.id limit 1)
          FROM hr_employee e
         WHERE id in %s
        """, (tuple(self.ids), ))

        result = {eid[0]: eid[1] for eid in self.env.cr.fetchall()}

        for employee in self:
            employee.has_slots = result.get(employee.id, False)

    def action_view_planning(self):
        action = self.env["ir.actions.actions"]._for_xml_id("planning.planning_action_schedule_by_resource")
        action.update({
            'name': _('View Planning'),
            'domain': [('resource_id', 'in', self.resource_id.ids)],
            'context': {
                'search_default_group_by_resource': True,
                'filter_resource_ids': self.resource_id.ids,
                'hide_open_shift': True,
                'default_resource_id': self.resource_id.id if len(self) == 1 else False,
            }
        })
        return action
