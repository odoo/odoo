# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from math import ceil

from odoo import api, models, fields, _


class L10nBeHrPayrollExportAcerta(models.Model):
    _inherit = 'hr.work.entry.export.mixin'
    _name = 'l10n.be.hr.payroll.export.acerta'
    _description = 'Export Payroll to Acerta'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.acerta.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    def _generate_line(self, contract, we_dotdict):
        """Acerta work entry lines are composed of a series of fixed-length fields.

        filler = ' '
        not currently used = /
        start char - length - type      - name                  (value)
        [0]        - 3      - CHAR      - code                  ('KLX')
        [3]        - 1      - CHAR      - identifier            ('1')
        [4]        - 7      - NUMERIC   - legal entity number   (res.company.legal_number)
        [11]       - 20     - CHAR      - contract number       (hr.contract.acerta_number) (padded with 0)
        [31]       - 10     - CHAR      - date                  (work_entry.start_date in DD/MM/YYYY format)
        [41]       - 2      - NUMERIC   - sequence number       /
        [43]       - 6      - CHAR      - work entry code       (work_entry_type.acerta_code)
        [49]       - 4      - NUMERIC   - hours worked          (work_entry.duration in hours, minutes in hundredths)

        eg: 'KLX176543210000000000000000001714/10/2024  100   0800'
        """

        work_entry = we_dotdict.work_entries[0]
        duration = we_dotdict.duration
        return 'KLX1' + self.company_id.acerta_code + contract.acerta_code.zfill(20) \
            + work_entry.date_start.strftime('%d/%m/%Y') + '  '  \
            + work_entry.work_entry_type_id.acerta_code.ljust(6) \
            + str(int(duration // 3600)).zfill(2) \
            + str(int(ceil(duration % 3600 // 100))).zfill(2) + '\n'

    def _generate_employee_entries(self, employee_line):
        we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
        employee_entries = ''
        for contract in employee_line.contract_ids:
            if len(employee_line.contract_ids) > 1:
                we_by_day_and_code_in_contract = {
                    date: we_by_code for date, we_by_code in we_by_day_and_code.items()
                    if date >= contract.date_start and (not contract.date_end or date <= contract.date_end)
                }
            else:
                we_by_day_and_code_in_contract = we_by_day_and_code
            for work_entries_by_code in we_by_day_and_code_in_contract.values():
                for work_entries_dotdict in work_entries_by_code.values():
                    employee_entries += self._generate_line(contract, work_entries_dotdict)
        return employee_entries

    def _generate_export_file(self):
        self.ensure_one()
        file = ''
        for employee_line in self.eligible_employee_line_ids:
            file += self._generate_employee_entries(employee_line)
        return file

    def _generate_export_filename(self):
        return 'ACERTA_%(acerta_company)s_%(reference_time)s_%(datetime)s_KLX.txt' % {
            'acerta_company': self.company_id.acerta_code,
            'reference_time': self.period_start.strftime('%Y%m'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
        }

    def _get_name(self):
        return _('Export to Acerta')


class L10nBeHrPayrollExportAcertaEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.acerta.employee'
    _description = 'Acerta Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.acerta')

    def _relations_to_check(self):
        return super()._relations_to_check() + [
            (self.env._('companies'), 'export_id.company_id.acerta_code'),
            (self.env._('contracts'), 'contract_ids.acerta_code'),
            (self.env._('work entry types'), 'work_entry_ids.work_entry_type_id.acerta_code'),
        ]
