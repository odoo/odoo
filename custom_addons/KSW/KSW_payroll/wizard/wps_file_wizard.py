import base64
from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError
class WpsFileWizard(models.TransientModel):
    _name = 'ksw.wps.file.wizard'
    _description = 'WPS Text File Generator'
    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Payslip Batch',
        required=True, readonly=True,
    )
    value_date = fields.Date(
        string='Value Date',
        required=True,
        default=fields.Date.context_today,
        help='Payment value date (the date the bank processes the transfer).',
    )
    _LINE_LEN = 300
    def action_generate(self):
        self.ensure_one()
        batch = self.payslip_run_id
        if not batch.slip_ids:
            raise UserError(_('No payslips in this batch to export.'))
        groups = batch._group_slips_by_bank_account()
        no_bank = groups.pop(self.env['res.partner.bank'], None)
        if no_bank:
            names = ', '.join(no_bank.mapped('employee_id.name'))
            raise UserError(_(
                'The following employees have no Salary Paying Bank Account '
                'set (and no fallback on the batch):\n%s', names,
            ))
        attachments = []
        for bank_account, slips in groups.items():
            content = self._build_wps_text(bank_account, slips)
            suffix = ''
            if len(groups) > 1:
                suffix = '_%s' % (
                    bank_account.bank_id.bic
                    or bank_account.bank_id.name
                    or str(bank_account.id)
                ).replace(' ', '_')
            filename = 'WPS_%s%s_%s.txt' % (
                batch.name.replace(' ', '_').replace('/', '-'),
                suffix,
                self.value_date.strftime('%Y%m%d'),
            )
            att = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(content.encode('utf-8')),
                'mimetype': 'text/plain',
                'res_model': batch._name,
                'res_id': batch.id,
            })
            attachments.append(att)
        if len(attachments) == 1:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % attachments[0].id,
                'target': 'new',
            }
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachments[-1].id,
            'target': 'new',
        }
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _sar_to_halalas(self, amount):
        return int(round(amount * 100))
    def _pr(self, text, length):
        """Left-justify text, pad/truncate to length with spaces."""
        return str(text or '')[:length].ljust(length)
    def _pz(self, number, length):
        """Zero-pad integer number to length digits."""
        return str(int(number)).zfill(length)[:length]
    def _swift4(self, bank_account):
        bic = (bank_account.bank_id.bic or '') if bank_account.bank_id else ''
        return bic[:4].ljust(4) if bic else '    '
    def _get_line_total(self, slip, code):
        line = slip.line_ids.filtered(lambda l: l.code == code)
        return line[:1].total if line else 0.0
    # ------------------------------------------------------------------
    # Text-file builders
    # ------------------------------------------------------------------
    def _build_wps_text(self, bank_account, slips):
        valid = slips.filtered(
            lambda s: self._get_line_total(s, 'NET') > 0
        ).sorted(lambda s: s.employee_id.name or '')
        if not valid:
            raise UserError(_('No payslips with a positive NET salary.'))
        total_sar = sum(
            int(round(self._get_line_total(s, 'NET')))
            for s in valid
        )
        lines = [self._header(bank_account, total_sar, len(valid))]
        for slip in valid:
            lines.append(self._detail(slip))
        return '\n'.join(lines) + '\n'
    def _header(self, bank_account, total_sar, count):
        now = datetime.now()
        cic = bank_account.x_wps_cic_number or ''
        debit = (bank_account.x_wps_debit_account or '').replace(' ', '')
        mol = bank_account.x_wps_mol_id or ''
        vdate = self.value_date.strftime('%Y%m%d')
        h = ''.join([
            '0' * 12,                                          # filler       12
            'G',                                               # record type   1
            vdate,                                             # value date    8
            vdate,                                             # value date    8 (repeated)
            self._pz(total_sar, 13),                           # total (SAR)  13
            self._pz(count, 10),                               # record count 10
            self._pr(debit, 24),                               # debit IBAN   24
            'SAR',                                             # currency      3
            'E01',                                             # file ref      3
            now.strftime('%Y%m%d'),                            # creation date 8
            now.strftime('%H%M%S'),                            # creation time 6
            '01',                                              # batch number  2
            self._pz(int(cic) if cic.isdigit() else 0, 15),   # CIC          15
            self._pr(mol, 10),                                 # MOL ID       10
            ' ' * 9,                                           # filler        9
            self._pr('PAYR', 4),                               # payment type  4
            ' ' * 6,                                           # filler        6
            self._pr('Payroll', 7),                            # description   7
        ])
        h = h.ljust(self._LINE_LEN - 1) + 'N'
        return h[:self._LINE_LEN]
    def _detail(self, slip):
        emp = slip.employee_id
        bank = emp.sudo().primary_bank_account_id
        net = self._get_line_total(slip, 'NET')
        basic = self._get_line_total(slip, 'BASIC')
        hra = self._get_line_total(slip, 'HRA')
        gross = self._get_line_total(slip, 'GROSS')
        other = max(gross - basic - hra, 0.0) if gross else 0.0
        total_ded = abs(sum(
            l.total for l in slip.line_ids
            if l.category_id.code == 'DED'
        )) or 0.0
        emp_ref = emp.barcode or '0'
        emp_iban = (bank.acc_number or '').replace(' ', '') if bank else ''
        emp_name = (emp.name or '').upper()
        emp_id = emp.identification_id or '0'
        d = ''.join([
            self._pz(int(emp_ref) if emp_ref.isdigit() else 0, 12),
            self._swift4(bank) if bank else '    ',
            ' ' * 8,
            self._pr(emp_iban, 24),
            ' ' * 11,
            self._pr(emp_name, 50),
            self._pz(self._sar_to_halalas(net), 15),
            self._pz(int(emp_id) if emp_id.isdigit() else 0, 10),
            ' ' * 5,
            self._pz(self._sar_to_halalas(basic), 13),
            self._pz(self._sar_to_halalas(hra), 12),
            self._pz(self._sar_to_halalas(other), 12),
            self._pz(self._sar_to_halalas(total_ded), 12),
            'SAR',
            '0' * 5,
        ])
        used = len(d)
        remain = self._LINE_LEN - used
        if remain > 51:
            trail = ' ' * 50 + '0' + ' ' * (remain - 51)
        elif remain > 0:
            trail = ' ' * (remain - 1) + '0'
        else:
            trail = ''
        d = d + trail
        return d[:self._LINE_LEN]
