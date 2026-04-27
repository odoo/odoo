# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models, fields


class L10nBeHrPayrollExportUCM(models.Model):
    _inherit = 'hr.work.entry.export.mixin'
    _name = 'l10n.be.hr.payroll.export.ucm'
    _description = 'Export Payroll to UCM'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.ucm.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    def _generate_line(self, employee, date, work_entry_collection):
        """
        Generate a line for the export file.
        """
        ucm_code = work_entry_collection.work_entries[0].work_entry_type_id.ucm_code
        hours = f'{int(work_entry_collection.duration // 3600):02d}'
        hundredth_of_hours = f'{int((work_entry_collection.duration % 3600) // 36):02d}'
        return self.company_id.ucm_company_code + f'{employee.ucm_code:0>5}' \
            + date.strftime('%m%Y%d') + ucm_code + hours + hundredth_of_hours \
            + '0000000             ' + '\n'

    def _generate_export_file(self):
        self.ensure_one()
        file = ''
        for employee_line in self.eligible_employee_line_ids:
            we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
            for date, we_by_code in we_by_day_and_code.items():
                for work_entry_collection in we_by_code.values():
                    file += self._generate_line(employee_line.employee_id, date, work_entry_collection)
        return file

    def _generate_export_filename(self):
        return '%(ucm_company)s_RP_%(reference_time)s_%(datetime)s.txt' % {
            'ucm_company': self.env.company.ucm_code,
            'reference_time': self.period_start.strftime('%Y%m'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
        }

    def _get_name(self):
        return self.env._('Export to UCM')


class L10nBeHrPayrollExportUCMEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.ucm.employee'
    _description = 'UCM Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.ucm')

    def _relations_to_check(self):
        return super()._relations_to_check() + [
            (self.env._('companies'), 'export_id.company_id.ucm_code'),
            (self.env._('employees'), 'employee_id.ucm_code'),
            (self.env._('work entry types'), 'work_entry_ids.work_entry_type_id.ucm_code'),
        ]
