from datetime import UTC

from odoo import api, models
from odoo.fields import Domain


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _get_time_rule_affected(self):
        """Return [(employee, date_from_utc, date_to_utc)] for public-holiday leaves in self."""
        ph_leaves = self.filtered(lambda l: not l.resource_id and l.date_from and l.date_to)
        if not ph_leaves:
            return []

        global_leaves = ph_leaves.filtered(lambda l: not l.calendar_id)
        calendar_leaves = ph_leaves.filtered('calendar_id')

        domains = []
        if global_leaves:
            company_ids = global_leaves.company_id.ids
            domains.append(Domain('company_id', 'in', company_ids) if company_ids else Domain.TRUE)
        if calendar_leaves:
            domains.append(Domain('resource_calendar_id', 'in', calendar_leaves.calendar_id.ids))
        if not domains:
            return []

        all_employees = self.env['hr.employee'].sudo().search(Domain.OR(domains))
        if not all_employees:
            return []

        affected = []
        for leave in ph_leaves:
            df = leave.date_from.replace(tzinfo=UTC)
            dt = leave.date_to.replace(tzinfo=UTC)
            if leave.calendar_id:
                emps = all_employees.filtered(lambda e, c=leave.calendar_id: e.resource_calendar_id == c)
            elif leave.company_id:
                emps = all_employees.filtered(lambda e, cid=leave.company_id.id: e.company_id.id == cid)
            else:
                emps = all_employees
            affected.extend((emp, df, dt) for emp in emps)
        return affected

    def _retrigger_time_rules(self):
        affected = self._get_time_rule_affected()
        if affected:
            self.env['hr.attendance']._process_time_rules_for(affected)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._retrigger_time_rules()
        return res

    def write(self, vals):
        affects_time_rules = bool({'date_from', 'date_to', 'resource_id', 'calendar_id'} & set(vals.keys()))
        old_affected = self._get_time_rule_affected() if affects_time_rules else []
        res = super().write(vals)
        if affects_time_rules:
            if old_affected:
                self.env['hr.attendance']._process_time_rules_for(old_affected)
            self._retrigger_time_rules()
        return res

    def unlink(self):
        affected = self._get_time_rule_affected()
        res = super().unlink()
        if affected:
            self.env['hr.attendance']._process_time_rules_for(affected)
        return res
