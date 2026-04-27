# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from math import ceil

from odoo import api, models, fields, _


class L10nBeHrPayrollExportPrisma(models.Model):
    _name = 'l10n.be.hr.payroll.export.prisma'
    _inherit = 'hr.work.entry.export.mixin'
    _description = 'Export Payroll to Prisma'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.prisma.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    def _generate_line(self, employee, date, we_dotdict):
        """Prisma work entry lines are composed of a series of fixed-length fields.
        ```
        filler = ' '
        not currently used = /
        start char - length - type        - name                       (value)
        [0]        - 8      - CHAR        - legal entity number        (res_company.legal_number, format: 99999999)
        [8]        - 10     - ALPHANUMERIC- cost center                (leave blank)
        [18]       - 5      - NUMERIC     - employee number            (employee_id.prisma_code)
        [23]       - 8      - DATE        - date                       (work_entry.start_date in YYYYMMDD format)
        [31]       - 1      - NUMERIC     - work entry type day        (always 0)
        [32]       - 4      - NUMERIC     - work entry type code       (work_entry_type.prisma_code, format: 9999)
        [36]       - 2      - NUMERIC     - sub work entry type code   (always 01)
        [38]       - 2      - NUMERIC     - team code                  (always 01)
        [40]       - 7      - NUMERIC     - duration (hours)           (work_entry.duration in hours, format: 9999,99)
        ```

        eg: '12345678          00001YYYYMMDD0001000101999,99'
        """
        work_entry = we_dotdict.work_entries[0]
        duration = we_dotdict.duration
        return self.company_id.prisma_code + ' ' * 10 + employee.prisma_code.zfill(5) \
            + work_entry.date_start.strftime('%Y%m%d') + '0' \
            + work_entry.work_entry_type_id.prisma_code.zfill(4) \
            + '01' * 2 + str(int(duration // 3600)).zfill(4) + ',' \
            + str(int(ceil(duration % 3600 / 3600 * 100))).zfill(2) + '\n'

    def _generate_export_file(self):
        self.ensure_one()
        file = ''
        for employee_line in self.eligible_employee_line_ids:
            we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
            for date, we_by_code in we_by_day_and_code.items():
                for we_dotdict in we_by_code.values():
                    file += self._generate_line(employee_line.employee_id, date, we_dotdict)
        return file

    def _generate_export_filename(self):
        return 'Prisma_%(prisma_company)s_%(reference_time)s_%(datetime)s.txt' % {
            'prisma_company': self.company_id.prisma_code,
            'reference_time': self.period_start.strftime('%Y%m'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
        }

    def _get_name(self):
        return _('Export to Prisma')


class L10nBeHrPayrollExportPrismaEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.prisma.employee'
    _description = 'Prisma Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.prisma')

    def _relations_to_check(self):
        return super()._relations_to_check() + [
            (self.env._('companies'), 'export_id.company_id.prisma_code'),
            (self.env._('employees'), 'employee_id.prisma_code'),
            (self.env._('work entry types'), 'work_entry_ids.work_entry_type_id.prisma_code'),
        ]
