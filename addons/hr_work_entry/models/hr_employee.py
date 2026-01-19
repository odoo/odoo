# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    work_entry_source = fields.Selection(readonly=False, related="version_id.work_entry_source", inherited=True, groups="base.group_system,hr.group_hr_manager")
    work_entry_source_calendar_invalid = fields.Boolean(related="version_id.work_entry_source_calendar_invalid", inherited=True, groups="hr.group_hr_manager")
    external_code = fields.Char("External Code", copy=False, help="Use this code to export your data to a third party", groups="hr.group_hr_user")

    # YTI TODO: Rename private method into _get_work_entries_vals()
    # Public method probably to drop
    def generate_work_entries(self, date_start, date_stop):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            versions = self._get_versions_with_contract_overlap_with_period(date_start, date_stop)
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(date_start, date_stop)
        return versions.generate_work_entries(date_start, date_stop)
