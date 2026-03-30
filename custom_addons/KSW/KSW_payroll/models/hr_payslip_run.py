import io
import base64

from odoo import fields, models, _
from odoo.exceptions import UserError

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
except ImportError:
    openpyxl = None


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    x_salary_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Salary Paying Bank Account',
        help='Default company bank account for WPS export. '
             'Employees with their own Salary Paying Bank Account '
             'will override this.',
    )


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_line_total(self, slip, code):
        """Return the total of a salary rule line by code, or 0."""
        line = slip.line_ids.filtered(lambda l: l.code == code)
        return line[:1].total if line else 0.0

    def _get_wd_amount(self, slip, code):
        """Return the amount of a worked-day line by code, or 0."""
        wd = slip.worked_days_line_ids.filtered(lambda w: w.code == code)
        return wd[:1].amount if wd else 0.0

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def action_open_wps_wizard(self):
        """Open the WPS text-file generator wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create WPS File'),
            'res_model': 'ksw.wps.file.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_run_id': self.id,
            },
        }

    def _group_slips_by_bank_account(self):
        """Group payslips by the paying bank account.

        Resolution order for each slip:
        1. Employee's ``x_salary_bank_account_id``
        2. Batch-level ``x_salary_bank_account_id`` (fallback)

        Returns a dict ``{res.partner.bank recordset: slip recordsets}``.
        Slips with **no** resolved bank account are collected under an
        empty recordset key so callers can report them.
        """
        groups = {}
        bank_model = self.env['res.partner.bank']
        for slip in self.slip_ids:
            bank = (
                slip.employee_id.sudo().x_salary_bank_account_id
                or self.x_salary_bank_account_id
                or bank_model
            )
            groups.setdefault(bank, self.env['hr.payslip'])
            groups[bank] |= slip
        return groups

    def action_export_bank_file(self):
        """Generate the WPS payroll Excel file from this batch."""
        self.ensure_one()
        if not openpyxl:
            raise UserError(_('The openpyxl library is required.'))
        if not self.slip_ids:
            raise UserError(_('No payslips in this batch to export.'))

        groups = self._group_slips_by_bank_account()

        # Validate: every slip must resolve to a bank account
        no_bank_slips = groups.pop(self.env['res.partner.bank'], None)
        if no_bank_slips:
            names = ', '.join(no_bank_slips.mapped('employee_id.name'))
            raise UserError(_(
                'The following employees have no Salary Paying Bank Account '
                'set (and no fallback is configured on the batch):\n%s\n\n'
                'Please set it on each employee or on the batch.', names,
            ))

        wb = openpyxl.Workbook()
        self._fill_payroll_summary_sheet(wb)

        # One WPS sheet per bank account
        for bank_account, slips in groups.items():
            suffix = ''
            if len(groups) > 1:
                suffix = ' - %s' % (
                    bank_account.bank_id.name
                    or bank_account.acc_number
                    or str(bank_account.id)
                )
            self._fill_wps_sheet(wb, bank_account, slips, suffix)

        # Remove default empty sheet created by openpyxl
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']

        output = io.BytesIO()
        wb.save(output)
        file_data = base64.b64encode(output.getvalue())

        filename = 'WPS_Payroll_%s.xlsx' % (
            self.name.replace(' ', '_').replace('/', '-'),
        )
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument'
                        '.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # Sheet 1 — Internal payroll summary
    # ------------------------------------------------------------------

    def _fill_payroll_summary_sheet(self, wb):
        ws = wb.active
        ws.title = 'Payroll Summary'

        headers = [
            'Employee', 'SSN No', 'Date From', 'Date To', 'Department',
            'Basic Salary', 'House Rent Allowance', 'Other Allowance',
            'Gross', 'Absence Deduction', 'Attendance Deductions',
            'Missed Days (ATT SHEET)', 'Social Insurance', 'Loan',
            'Net Salary', 'Bank Account Number', 'Bank Name',
        ]

        hdr_font = Font(bold=True, size=11)
        hdr_fill = PatternFill('solid', fgColor='D9E1F2')
        hdr_align = Alignment(horizontal='center', wrap_text=True)
        thin = Border(
            left=Side('thin'), right=Side('thin'),
            top=Side('thin'), bottom=Side('thin'),
        )

        for ci, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=ci, value=h)
            c.font = hdr_font
            c.fill = hdr_fill
            c.alignment = hdr_align
            c.border = thin

        for ri, slip in enumerate(
                self.slip_ids.sorted(lambda s: s.employee_id.name or ''), 2):
            emp = slip.employee_id
            bank = emp.sudo().primary_bank_account_id
            is_sheet = emp.sudo().x_is_attendance_sheet

            basic = self._get_line_total(slip, 'BASIC')
            hra = self._get_line_total(slip, 'HRA')
            gross = self._get_line_total(slip, 'GROSS')
            gosi = self._get_line_total(slip, 'GOSI')
            net = self._get_line_total(slip, 'NET')
            attded = self._get_line_total(slip, 'ATTDED')

            # Other allowance = GROSS - BASIC - HRA
            other_alw = gross - basic - hra if gross else 0.0

            # Deductions breakdown
            abs_ded = 0.0
            att_ded = 0.0
            sheet_ded = 0.0
            if is_sheet:
                # Sheet employee: deduction goes to column L
                sheet_ded = -self._get_wd_amount(slip, 'ATT_DED')
            else:
                # Biometric: absence (J) and late/early (K)
                abs_ded = -self._get_wd_amount(slip, 'ATT_ABS')
                att_ded = -(
                    self._get_wd_amount(slip, 'ATT_LATE')
                    + self._get_wd_amount(slip, 'ATT_EARLY')
                )

            # Loan = total DED minus ATTDED and GOSI
            total_ded_cat = sum(
                l.total for l in slip.line_ids
                if l.category_id.code == 'DED'
            )
            loan = total_ded_cat - attded - gosi

            row = [
                emp.name or '',
                emp.identification_id or '',
                slip.date_from,
                slip.date_to,
                emp.department_id.name if emp.department_id else '',
                basic or None,
                hra or None,
                other_alw or None,
                gross or None,
                abs_ded or None,
                att_ded or None,
                sheet_ded or None,
                gosi or None,
                loan or None,
                net,
                bank.acc_number if bank else '',
                bank.bank_id.name if bank and bank.bank_id else '',
            ]
            for ci, v in enumerate(row, 1):
                c = ws.cell(row=ri, column=ci, value=v)
                c.border = thin

        # Auto-width columns
        for ci in range(1, len(headers) + 1):
            letter = openpyxl.utils.get_column_letter(ci)
            mx = max(
                len(str(ws.cell(row=r, column=ci).value or ''))
                for r in range(1, ws.max_row + 1)
            )
            ws.column_dimensions[letter].width = min(mx + 3, 35)

    # ------------------------------------------------------------------
    # Sheet 2 — WPS bank upload (Al Rajhi format)
    # ------------------------------------------------------------------

    def _fill_wps_sheet(self, wb, bank_account, slips=None, suffix=''):
        if slips is None:
            slips = self.slip_ids
        sheet_name = ('WPS Bank File%s' % suffix)[:31]  # Excel 31-char limit
        ws = wb.create_sheet(sheet_name)

        bold = Font(bold=True, size=11)
        title_font = Font(bold=True, size=12, color='003366')
        thin = Border(
            left=Side('thin'), right=Side('thin'),
            top=Side('thin'), bottom=Side('thin'),
        )
        hdr_fill = PatternFill('solid', fgColor='C6EFCE')
        ar_fill = PatternFill('solid', fgColor='E2EFDA')

        # Read WPS header values from the selected bank account
        cic = bank_account.x_wps_cic_number or ''
        debit = bank_account.x_wps_debit_account or ''
        mol = bank_account.x_wps_mol_id or ''

        # ── Row 1 ──
        ws.cell(1, 1, 'CIC - رقم العميل').font = bold
        ws.cell(1, 2, cic)
        ws.merge_cells('C1:D1')
        ws.cell(1, 3,
                'Alrajhi Bank WPS Payroll Payments Upload File'
                ).font = title_font

        # ── Row 2 ──
        ws.cell(2, 1, 'Debit Account:').font = bold
        ws.cell(2, 2, debit)
        ws.merge_cells('C2:D2')
        ws.cell(2, 3,
                'Notes: Template used for upload of WPS Payroll data'
                ).font = Font(bold=True, size=10)
        ws.cell(2, 8, 'Type of Payroll')
        ws.cell(2, 9, 'WPS')

        # ── Row 3 ──
        ws.cell(3, 1, 'MOL ID').font = bold
        ws.cell(3, 2, mol)

        # ── Row 4 ──
        ws.cell(4, 1, 'Payment Purpose').font = bold
        ws.cell(4, 2, 'Payroll')

        # ── Row 5 ──
        ws.cell(5, 1, 'Company Remarks').font = bold
        ws.cell(5, 2, 'Payroll')

        # ── Row 6–7: English / Arabic headers ──
        en_headers = [
            'Bank Name', 'Account Number(34N)', 'Employee Name',
            'Employee Number', 'National ID Number', 'Salary (15N)',
            'Basic Salary', 'Housing Allowance', 'Other Earnings',
            'Deductions', 'Branch Code', 'Branch Name',
            'Employee Remarks', 'Employee Department',
        ]
        ar_headers = [
            'بنك الموظف', 'رقم أيبان الموظف', 'إسم الموظف',
            'الرقم الوظيفي', 'رقم الهوية للموظف', 'إجمالي الراتب',
            'الراتب الأساسي', 'بدل السكن', 'بدل أخرى',
            'الخصومات', 'رمز الفرع', 'اسم الفرع',
            'ملاحظات الموظف', 'قسم الموظف',
        ]

        for ci, (e, a) in enumerate(zip(en_headers, ar_headers), 1):
            c6 = ws.cell(6, ci, e)
            c6.font = bold
            c6.fill = hdr_fill
            c6.border = thin
            c6.alignment = Alignment(horizontal='center')

            c7 = ws.cell(7, ci, a)
            c7.font = Font(bold=True, size=10)
            c7.fill = ar_fill
            c7.border = thin
            c7.alignment = Alignment(horizontal='center')

        # ── Data rows (row 8+), skip employees with net == 0 ──
        ri = 8
        for slip in slips.sorted(
                lambda s: s.employee_id.name or ''):
            net = self._get_line_total(slip, 'NET')
            if not net:
                continue

            emp = slip.employee_id
            bank = emp.sudo().primary_bank_account_id

            basic = self._get_line_total(slip, 'BASIC')
            hra = self._get_line_total(slip, 'HRA')
            gross = self._get_line_total(slip, 'GROSS')
            other_e = gross - basic - hra if gross else 0.0

            total_ded = abs(sum(
                l.total for l in slip.line_ids
                if l.category_id.code == 'DED'
            )) or 0.0

            data = [
                bank.bank_id.name if bank and bank.bank_id else '',
                bank.acc_number if bank else '',
                emp.name or '',
                emp.barcode or '',
                emp.identification_id or '',
                net,              # F: Salary (net)
                basic,            # G: Basic
                hra,              # H: Housing
                other_e,          # I: Other earnings
                total_ded,        # J: Deductions
                '',               # K: Branch Code
                '',               # L: Branch Name
                '',               # M: Employee Remarks
                emp.department_id.name if emp.department_id else '',
            ]
            for ci, v in enumerate(data, 1):
                c = ws.cell(ri, ci, v)
                c.border = thin
            ri += 1

        # Auto-width columns
        for ci in range(1, len(en_headers) + 1):
            letter = openpyxl.utils.get_column_letter(ci)
            mx = max(
                len(str(ws.cell(row=r, column=ci).value or ''))
                for r in range(1, max(ws.max_row + 1, 2))
            )
            ws.column_dimensions[letter].width = min(mx + 3, 40)







