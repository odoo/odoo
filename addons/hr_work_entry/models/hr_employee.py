# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    external_code = fields.Char("External Code", copy=False, help="Use this code to export your data to a third party", groups="hr.group_hr_user")

    # YTI TODO: Rename private method into _get_work_entries_vals()
    # Public method probably to drop
    def generate_work_entries(self, date_start, date_stop):
        """Return the work entry values of the employees of ``self`` between two dates.

        Selects the versions with contract days in the period, then calls
        ``hr.version.generate_work_entries``. Called on an empty recordset, it processes all
        the employees with contract days in the period.

        :param date_start: first day, included (``date``, ``datetime`` or string, converted to
            a date)
        :param date_stop: last day, included
        :return: final work entry values, see ``hr.version.generate_work_entries``
        :rtype: list[dict]
        """
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            versions = self._get_versions_with_contract_overlap_with_period(date_start, date_stop)
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(date_start, date_stop)
        return versions.generate_work_entries(date_start, date_stop)
