# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from math import ceil

from odoo import api, models, fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.osv.expression import AND


class L10nBeHrPayrollExportGroupS(models.Model):
    _inherit = 'hr.work.entry.export.mixin'
    _name = 'l10n.be.hr.payroll.export.group.s'
    _description = 'Export Payroll to Group S'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.group.s.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not (companies := self.env.companies.filtered(
            lambda company: company.group_s_code and company.country_id.code == self._country_restriction())
        ):
            raise RedirectWarning(
                self.env._('The companies must have an affiliation number to export to Group S.'),
                action=self.env.ref('hr_payroll.action_hr_payroll_configuration').id,
                button_text=self.env._('Go to Settings')
            )
        if 'company_id' in fields:
            res['company_id'] = self.env.company.id \
                if self.env.company in companies else companies[0].id
        return res

    def _get_company_domain(self):
        return AND([
            super()._get_company_domain(),
            [('group_s_code', '!=', False)]
        ])

    def _compose_group_s_starter(self):
        """Group S requires a start line composed of a series of fixed-length fields.
        The type is only indicative of what is expected.
        ```
        filler = ' '
        not currently used = /
        start char - length - type      - name                  (value)
        [0]        - 3      - ASCII     - code                  (000)
        [3]        - 3      - ASCII     - Name                  (PTG)
        [6]        - 3      - ASCII     - mode                  (002)            - write or create
        [9]        - 14     - INT       - create date           (AAAAmmDDHHMMSS)
        [23]       - 10     - INT       - affiliation number    (res.company field)
        [33]       - 4      - ASCII     - currency              (EUR )
        [37]       - 1      - filler
        [38]       - 6      - ASCII     - database version opt. /
        [44]       - 1      - filler
        [45]       - 20     - ASCII     - maker name            (ODOO)           - no need to use filler
        ```
        eg: 000PTG001202405171618120000654321EUR  000001 ODOO
        """
        affiliation_number = self.env.company.group_s_code and '0000' + self.env.company.group_s_code
        if not affiliation_number:
            raise UserError(self.env._('The company must have an affiliation number to export to Group S.'))
        create_date = datetime.now().strftime('%Y%m%d%H%M%S')
        return '000' + 'PTG' + '002' + create_date + affiliation_number + 'EUR ' + ' ' * 8 + 'ODOO' + '\n'

    def _compose_group_s_info(self, reference_contract, employee_type):
        """ Group S info line are starting line composed of a series of fixed-length fields.
        ```
        filler = ' '
        not currently used = /
        start char - length - type      - name                  (value)
        [0]        - 3      - ASCII     - code                  (003)
        [3]        - 6      - INT       - pay month             (AAAAmm)
        [9]        - 1      - INT       - order number          (1)
        [10]       - 1      - INT       - employee type         (1/3)            - 1 = employé, 3 = ouvrier
        [11]       - 2      - INT       - remuneration type     (02)
        [13]       - 1      - INT       - remuneration interval (1/2/3/4/5)
            |- 1 = By month
            |- 2 = By semi-week
            |- 3 = by 2 weeks
            |- 4 = by 4 weeks
            |- 5 = by week
        [14]       - 6      - INT       - fiscal month          (AAAAmm)
        [20]       - 8      - INT       - period start          (AAAAmmJJ)
        [28]       - 8      - INT       - period end            (AAAAmmJJ)
        [36]       - 1      - INT       - communication mode    (1)
        [37]       - 4      - INT       - reference year        (AAAA)
        [41]       - 8      - INT       - reference code        (00000000)
        [49]       - 8      - INT       - date of payroll run   /
        [57]       - 8      - INT       - date of payroll exec  /
        ```
        eg: 00320240411021202404202404012024043032024000010002024051700000000
        """
        remuneration_interval_to_group_s_code = {
            'monthly': '1',
            'bi-weekly': '3',
            'weekly': '5',
            'semi-weekly': '2',
            'four-weekly': '4',
        }
        employee_type_to_group_s_code = {
            'employee': '1',
            'worker': '3',
        }

        if not reference_contract.schedule_pay:
            raise UserError(self.env._('The pay schedule of the contracts must be set to export to Group S.'))
        if reference_contract.schedule_pay not in remuneration_interval_to_group_s_code:
            raise UserError(self.env._('The pay schedule of the contracts is not supported by Group S.'))

        return '003' + self.period_stop.strftime('%Y%m') + '1' \
            + employee_type_to_group_s_code[employee_type] + '02' \
            + remuneration_interval_to_group_s_code[reference_contract.schedule_pay] \
            + datetime.now().strftime('%Y%m') + self.period_start.strftime('%Y%m%d') \
            + self.period_stop.strftime('%Y%m%d') + '1' + self.period_start.strftime('%Y') \
            + '00000000' + '\n'

    def _compose_group_s_contract(self, contract):
        """Group S contract composed of a series of fixed-length fields.
        ```
        filler = ' '
        not currently used = /
        start char - length - type      - name                  (value)
        [0]        - 3      - ASCII     - code                  (006)
        [3]        - 5      - INT       - Reserved              (00000)
        [8]        - 6      - INT       - employer number       (hr_contract.group_s_code)
        [14]       - 8      - INT       - start date            (AAAAmmJJ)
        [22]       - 8      - INT       - end date              /
        ```
        eg: 0060000000012320240401
        """
        start_date = contract.date_start.strftime('%Y%m%d') if contract.date_start > self.period_start \
            else self.period_start.strftime('%Y%m%d')
        return '006' + '00000' + contract.group_s_code + start_date + '\n'

    def _compose_group_s_work_entry(self, work_entry_dict):
        """Group S work entry composed of a series of fixed-length fields.
        ```
        filler = ' '
        not currently used = /
        start char - length - type      - name                          (value)
        [0]        - 3      - ASCII     - code                          (009)
        [3]        - 8      - INT       - start date                    (AAAAmmJJ)
        [11]       - 3      - ASCII     - work entry type               (code)
            |- see data/hr_work_entry_type_data.xml
        [14]       - 1      - filler
        [15]       - 1      - '+'/'-'   - work entry sign               (+)
        [16]       - 4      - INT       - duration                      (HHMM)
        [20]       - 5      - INT       - LEVEL1                        (00000)
        [25]       - 5      - INT       - LEVEL2                        (00000)
        [30]       - 5      - INT       - LEVEL3                        (00000)
        [35]       - 11     - INT       - Work entry unit value         (00000000000)
        [46]       - 5      - INT       - Work entry percentage         (00000)
        [51]       - 3      - ASCII     - Work entry code 2             (   )
        [54]       - 3      - ASCII     - Work entry code 3             (   )
        [57]       - 3      - ASCII     - Work entry code 4             (   )
        [60]       - 4      - INT       - start hour                    (   )
        [64]       - 1      - ASCII     - reason of absence             (1/2/3/4)
            |- 1 = pas rechute
            |- 2 = remise tardive
            |- 3 = pas rechute et remise tardive
            |- 4 = apte au travail depuis maladie précédente
        [65]       - 4      - INT       - standard day duration         /
        [69]       - 9      - ASCII     - Function Code                 /
        [78]       - 9      - ASCII     - Bonus Code 1                  /
        [87]       - 9      - ASCII     - Bonus Code 2                  /
        [96]       - 9      - ASCII     - Bonus Code 3                  /
        [105]      - 11     - ASCII     - Unit value of bonus 1         /
        [116]      - 11     - ASCII     - Unit value of bonus 2         /
        [127]      - 11     - ASCII     - Unit value of bonus 3         /
        [138]      - 20     - ASCII     - Allocation 1                  /
        [158]      - 20     - ASCII     - Allocation 2                  /
        [178]      - 20     - ASCII     - Allocation 3                  /
        [198]      - 2      - ASCII     - Mobility code                 /
        [200]      - 2      - ASCII     - Travel code                   /
        [202]      - 20     - ASCII     - Loading location              /
        [222]      - 5      - INT       - Number of km mobility         /
        [227]      - 5      - INT       - Number of km travel           /
        [232]      - 1      - ASCII     - Social Charges Category       /
        [233]      - 1      - ASCII     - Application of Social Charges /
        ```
        eg: 00920240403CSS +05000000100002000000000000000000000
        """
        duration = work_entry_dict.duration
        work_entry = work_entry_dict.work_entries[0]
        return '009' + work_entry.date_start.strftime('%Y%m%d') + work_entry.work_entry_type_id.group_s_code + ' ' \
            + '+' + str(int(duration // 3600)).zfill(2) + str(ceil((duration % 3600) / 60)).zfill(2) + '00000' * 3 \
            + '00000000000' + '00000' + '\n'

    def _compose_group_s_eof(self):
        """Group S end of file line composed of a code field  with a value of '999'."""
        return '999'

    def _generate_employee_entries(self, reference_contract, employee_line):
        we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
        employee_entries = ''
        for contract in employee_line.contract_ids:
            if not contract.schedule_pay == reference_contract.schedule_pay:
                raise UserError(self.env._('The pay schedule of the contracts must be the same to export to Group S.'))
            if len(employee_line.contract_ids) > 1:
                we_by_day_and_code_in_contract = {
                    date: we_by_code for date, we_by_code in we_by_day_and_code.items()
                    if date >= contract.date_start and (not contract.date_end or date <= contract.date_end)
                }
            else:
                we_by_day_and_code_in_contract = we_by_day_and_code
            employee_entries += self._compose_group_s_contract(contract)
            for work_entries_by_code in we_by_day_and_code_in_contract.values():
                for work_entries_dict in work_entries_by_code.values():
                    employee_entries += self._compose_group_s_work_entry(work_entries_dict)
        return employee_entries

    def _generate_export_file(self):
        """Generate the export file for Group S. with the following structure:
        - Start line
        - Info line
        - Contract line x N contracts
            - Work entry line x M work entries per contract
        - End of file line
        """

        self.ensure_one()
        file = self._compose_group_s_starter()
        employee_lines_by_employee_type = self.eligible_employee_line_ids.grouped(
            lambda el: el.employee_id.employee_type)
        for employee_type, employee_lines in employee_lines_by_employee_type.items():
            if not employee_lines:
                continue
            reference_contract = employee_lines[0].contract_ids[0]
            file += self._compose_group_s_info(reference_contract, employee_type)
            for employee_line in employee_lines:
                file += self._generate_employee_entries(reference_contract, employee_line)
        file += self._compose_group_s_eof()
        return file

    def _generate_export_filename(self):
        """Group S filename composed of a series of fixed-length fields.
        ```
        Seprator = '_' (each field is separated by a '_' except for the file extension)
        start char - length - type      - name                          (value)
        [0]        - 2      - ASCII     - code                          (FI)                        - Fichier
        [2]        - 3      - ASCII     - code                          (PAI)                       - Paiement
        [5]        - 6      - INT       - employer number               (hr_employee.group_s_code)
        [11]       - 6      - INT       - employer own reference        (what we want)
        [17]       - 5      - INT       - sequence number               (unique)
        [22]       - 8      - INT       - date                          (AAAAmmJJ)
        [30]       - 6      - INT       - Reserved                      (000000)
        [36]       - 4      - ASCII     - file extension                (.dat)
        ```
        """
        self.company_id.group_s_sequence_number += 1
        if len(str(self.company_id.group_s_sequence_number)) > 5:
            self.company_id.group_s_sequence_number = 0
        return '_'.join([
            'FIPAI', 'PTG',
            f'{int(self.company_id.group_s_code):06d}',
            f'{self.company_id.id:06d}',
            f'{self.company_id.group_s_sequence_number:05d}',
            datetime.now().strftime('%Y%m%d'), '000000.dat'
        ])

    def _get_name(self):
        return self.env._('Export to Group S')


class L10nBeHrPayrollExportGroupSEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.group.s.employee'
    _description = 'Group S Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.group.s')

    def _relations_to_check(self):
        return super()._relations_to_check() + [
            (self.env._('companies'), 'export_id.company_id.group_s_code'),
            (self.env._('contracts'), 'contract_ids.group_s_code'),
            (self.env._('work entry types'), 'work_entry_ids.work_entry_type_id.group_s_code'),
        ]
