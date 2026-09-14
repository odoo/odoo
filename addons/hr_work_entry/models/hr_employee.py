from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    has_work_entries = fields.Boolean(
        compute="_compute_has_work_entries",
        groups="base.group_system,hr.group_hr_user",
    )

    def _compute_has_work_entries(self):
        with_entries = set()
        if self.ids:
            with_entries = {
                row[0]
                for row in self.env.execute_query(
                    SQL(
                        "SELECT DISTINCT employee_id FROM hr_work_entry"
                        " WHERE employee_id IN %s",
                        tuple(self.ids),
                    )
                )
            }
        _debug.perf.count(
            "has_work_entries_probed", employees=self, found=len(with_entries)
        )
        for employee in self:
            employee.has_work_entries = employee._origin.id in with_entries

    def action_view_work_entries(self, initial_date=False):
        self.check_singleton()
        ctx = {"default_employee_id": self.id}
        if initial_date:
            ctx["initial_date"] = initial_date
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("%s work entries", self.display_name),
            "view_mode": "calendar,list,form",
            "res_model": "hr.work.entry",
            "path": "work-entries",
            "context": ctx,
            "domain": [("employee_id", "=", self.id)],
        }

    def generate_work_entries(self, date_start, date_stop, force=False):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)
        if self:
            versions = self._get_versions_with_contract_overlap_with_period(
                date_start, date_stop
            )
            scope = "employees"  # debuglog
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(
                date_start, date_stop
            )
            scope = "all"  # debuglog
        _debug.pipeline(
            "generate_from_employees",
            by=scope,
            employees=self,
            versions=versions,
        )
        return versions.generate_work_entries(date_start, date_stop, force=force)
