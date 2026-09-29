# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime


class SifGeneralLedger(models.AbstractModel):
    _name = 'sif.general.ledger'
    _description = 'General Ledger Service & Engine'

    @api.model
    def _default_date_from(self):
        return fields.Date.context_today(self).replace(day=1)

    @api.model
    def _default_date_to(self):
        return fields.Date.context_today(self)

    def _company_scope_domain(self, field_name):
        """Keep company-tagged journals within the allowed companies.

        Legacy journals without a company remain shared until they can be
        explicitly mapped; new Pendapatan journals always carry a company.
        """
        return ['|', (field_name, '=', False), (field_name, 'in', self.env.companies.ids)]

    @api.model
    def get_general_ledger_data(self, filters=None):
        """
        Engine penghitung General Ledger interaktif.
        Mendukung:
        - Aturan Saldo Normal (Normal Balance: Debet vs Kredit)
        - Filter Unit Kerja (Branch / Department)
        - Filter Partner / Rekanan
        - Filter Rentang Tanggal & Status Jurnal
        - Pencarian Akun & Baris Transaksi
        """
        filters = filters or {}
        today = fields.Date.context_today(self)
        lang = filters.get('lang') or self.env.user.lang or self.env.context.get('lang', 'id_ID')
        is_id = str(lang).lower().startswith('id')
        
        # 1. Rentang tanggal
        date_from = filters.get('date_from')
        if not date_from:
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
        
        date_to = filters.get('date_to')
        if not date_to:
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            date_to = (next_month - datetime.timedelta(days=next_month.day)).strftime('%Y-%m-%d')

        target_move = filters.get('target_move', 'posted') # 'posted' or 'all'
        search_query = (filters.get('search') or '').strip().lower()
        unit_name_filter = (filters.get('unit_name') or '').strip()
        department_id_filter = filters.get('department_id')
        if department_id_filter:
            try:
                department_id_filter = int(department_id_filter)
            except (ValueError, TypeError):
                department_id_filter = None
        if department_id_filter:
            department = self.env['hr.department'].browse(department_id_filter).exists()
            if not department or department.company_id not in self.env.companies:
                department_id_filter = None
        partner_id_filter = filters.get('partner_id')
        if partner_id_filter:
            try:
                partner_id_filter = int(partner_id_filter)
            except (ValueError, TypeError):
                partner_id_filter = None

        # 2. Ambil list unit kerja unik untuk dropdown filter
        distinct_units = self.env['sif.jurnal.entry'].search(self._company_scope_domain('company_id') + [
            ('unit_name', '!=', False),
            ('unit_name', '!=', '')
        ]).mapped('unit_name')
        units_list = sorted(list(set(distinct_units)))

        # 3. Ambil list partner yang relevan untuk dropdown filter
        distinct_partners = self.env['sif.jurnal.line'].search([
            ('partner_id', '!=', False)
        ]).mapped('partner_id')
        partners_list = [{'id': p.id, 'name': p.name} for p in distinct_partners]
        partners_list = sorted(partners_list, key=lambda x: x['name'])

        # 4. Domain unposted banner
        unposted_domain = self._company_scope_domain('company_id') + [
            ('state', '=', 'draft'),
            ('date', '<=', date_to)
        ]
        if unit_name_filter:
            unposted_domain.append(('unit_name', '=', unit_name_filter))
        unposted_count = self.env['sif.jurnal.entry'].search_count(unposted_domain)

        # 5. Base domain untuk baris periode
        period_domain = self._company_scope_domain('company_id') + [
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]
        if target_move == 'posted':
            period_domain.append(('state', '=', 'posted'))
        if unit_name_filter:
            period_domain.append(('entry_id.unit_name', '=', unit_name_filter))
        if department_id_filter:
            period_domain.append(('department_id', '=', department_id_filter))
        if partner_id_filter:
            period_domain.append(('partner_id', '=', partner_id_filter))
        
        all_lines = self.env['sif.jurnal.line'].search(period_domain, order='date asc, id asc')

        # 6. Saldo awal sebelum date_from (Initial Balance)
        init_domain = self._company_scope_domain('company_id') + [('date', '<', date_from)]
        if target_move == 'posted':
            init_domain.append(('state', '=', 'posted'))
        if unit_name_filter:
            init_domain.append(('entry_id.unit_name', '=', unit_name_filter))
        if department_id_filter:
            init_domain.append(('department_id', '=', department_id_filter))
        if partner_id_filter:
            init_domain.append(('partner_id', '=', partner_id_filter))
        
        init_lines = self.env['sif.jurnal.line'].search(init_domain)
        init_raw_debits = {}
        init_raw_credits = {}
        for line in init_lines:
            acc_id = line.account_id.id
            init_raw_debits[acc_id] = init_raw_debits.get(acc_id, 0.0) + (line.debit or 0.0)
            init_raw_credits[acc_id] = init_raw_credits.get(acc_id, 0.0) + (line.credit or 0.0)

        # 7. Kelompokkan baris periode per akun
        lines_by_account = {}
        for line in all_lines:
            acc_id = line.account_id.id
            if acc_id not in lines_by_account:
                lines_by_account[acc_id] = []
            lines_by_account[acc_id].append(line)

        # 8. Kumpulkan semua ID akun yang memiliki saldo awal atau mutasi
        all_account_ids = set(init_raw_debits.keys()) | set(init_raw_credits.keys()) | set(lines_by_account.keys())
        if not all_account_ids:
            coa_records = self.env['sif.coa'].search([('active', '=', True)], order='code asc')
        else:
            coa_records = self.env['sif.coa'].search([('id', 'in', list(all_account_ids))], order='code asc')

        accounts_data = []
        grand_total_debit = 0.0
        grand_total_credit = 0.0

        for account in coa_records:
            acc_type = account.account_type or 'other'
            # Tentukan Saldo Normal Akun:
            # Asset & Expense -> Normal Debet (D - C)
            # Liability, Equity, Income -> Normal Kredit (C - D)
            is_normal_credit = acc_type in ('liability', 'equity', 'income')
            normal_bal_type = 'credit' if is_normal_credit else 'debit'
            if is_id:
                normal_bal_label = 'Kredit' if is_normal_credit else 'Debet'
            else:
                normal_bal_label = 'Credit' if is_normal_credit else 'Debit'

            raw_init_deb = init_raw_debits.get(account.id, 0.0)
            raw_init_crd = init_raw_credits.get(account.id, 0.0)
            
            # Hitung saldo awal sesuai saldo normal
            if is_normal_credit:
                acc_init_bal = raw_init_crd - raw_init_deb
            else:
                acc_init_bal = raw_init_deb - raw_init_crd

            acc_lines = lines_by_account.get(account.id, [])

            # Skip akun jika saldo awal 0 dan tidak ada mutasi di periode ini
            if abs(acc_init_bal) < 0.001 and not acc_lines:
                continue

            acc_total_debit = 0.0
            acc_total_credit = 0.0
            running_bal = acc_init_bal
            lines_data = []

            for line in acc_lines:
                deb = line.debit or 0.0
                crd = line.credit or 0.0
                acc_total_debit += deb
                acc_total_credit += crd

                # Tambahkan mutasi ke running balance sesuai saldo normal
                if is_normal_credit:
                    running_bal += (crd - deb)
                else:
                    running_bal += (deb - crd)

                partner_name = line.partner_id.name or line.entry_id.partner_id.name or '-'
                entry_num = line.entry_id.name or '-'
                ref_src = line.entry_id.ref or line.entry_id.kwitansi_ref or ''
                desc = line.name or '-'

                display_title = entry_num
                if ref_src:
                    display_title = f"{entry_num} ({ref_src})"
                if desc and desc != '-':
                    display_title = f"{display_title} {desc}"

                # Filter pencarian teks
                if search_query:
                    search_matched = (
                        search_query in (account.code or '').lower() or
                        search_query in (account.name or '').lower() or
                        search_query in display_title.lower() or
                        search_query in partner_name.lower()
                    )
                    if not search_matched:
                        continue

                line_dict = {
                    'id': line.id,
                    'entry_id': line.entry_id.id,
                    'date': line.date.strftime('%d/%m/%Y') if line.date else '-',
                    'raw_date': line.date.strftime('%Y-%m-%d') if line.date else '',
                    'title': display_title,
                    'entry_num': entry_num,
                    'ref_src': ref_src,
                    'desc': desc,
                    'partner_name': partner_name,
                    'debit': deb,
                    'debit_formatted': self._format_rupiah(deb),
                    'credit': crd,
                    'credit_formatted': self._format_rupiah(crd),
                    'balance': running_bal,
                    'balance_formatted': self._format_rupiah(running_bal),
                    'is_negative': running_bal < -0.001,
                }
                lines_data.append(line_dict)

            acc_ending_bal = running_bal

            # Cek jika ada search query tapi tidak ada matching lines
            if search_query and not lines_data:
                if search_query not in (account.code or '').lower() and search_query not in (account.name or '').lower():
                    continue

            grand_total_debit += acc_total_debit
            grand_total_credit += acc_total_credit

            accounts_data.append({
                'id': account.id,
                'code': account.code or '',
                'name': account.name or '',
                'full_name': f"{account.code} {account.name}",
                'account_type': acc_type,
                'normal_balance': normal_bal_type,
                'normal_balance_label': normal_bal_label,
                'is_normal_credit': is_normal_credit,
                'initial_balance': acc_init_bal,
                'initial_balance_formatted': self._format_rupiah(acc_init_bal),
                'total_debit': acc_total_debit,
                'total_debit_formatted': self._format_rupiah(acc_total_debit),
                'total_credit': acc_total_credit,
                'total_credit_formatted': self._format_rupiah(acc_total_credit),
                'ending_balance': acc_ending_bal,
                'ending_balance_formatted': self._format_rupiah(acc_ending_bal),
                'is_negative': acc_ending_bal < -0.001,
                'lines_count': len(lines_data),
                'lines': lines_data,
            })

        net_diff = grand_total_debit - grand_total_credit

        try:
            d_from = datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            d_from = str(date_from)
        try:
            d_to = datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            d_to = str(date_to)

        return {
            'company_name': ' / '.join(self.env.companies.mapped('name')) or self.env.company.name,
            'date_from': date_from,
            'date_to': date_to,
            'date_from_display': d_from,
            'date_to_display': d_to,
            'target_move': target_move,
            'search': search_query,
            'unit_name': unit_name_filter,
            'department_id': department_id_filter,
            'units_list': units_list,
            'partner_id': partner_id_filter,
            'partners_list': partners_list,
            'unposted_count': unposted_count,
            'accounts': accounts_data,
            'grand_total': {
                'total_debit': grand_total_debit,
                'total_debit_formatted': self._format_rupiah(grand_total_debit),
                'total_credit': grand_total_credit,
                'total_credit_formatted': self._format_rupiah(grand_total_credit),
                'difference': net_diff,
                'difference_formatted': self._format_rupiah(net_diff),
                'is_balanced': abs(net_diff) < 0.01,
            }
        }

    def _format_rupiah(self, amount):
        if amount is None:
            return "Rp 0,00"
        is_neg = amount < -0.001
        abs_amt = abs(amount)
        formatted = f"{abs_amt:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if is_neg:
            return f"-Rp {formatted}"
        return f"Rp {formatted}"


class SifGeneralLedgerWizard(models.TransientModel):
    _name = 'sif.general.ledger.wizard'
    _description = 'Wizard Cetak General Ledger'

    date_from = fields.Date(
        string='Dari Tanggal',
        required=True,
        default=lambda self: self.env['sif.general.ledger']._default_date_from()
    )
    date_to = fields.Date(
        string='Sampai Tanggal',
        required=True,
        default=lambda self: self.env['sif.general.ledger']._default_date_to()
    )
    target_move = fields.Selection(
        [('posted', 'Hanya Jurnal Disetujui (Posted)'),
         ('all', 'Semua Jurnal (Termasuk Draft)')],
        string='Status Jurnal',
        required=True,
        default='posted'
    )
    unit_name = fields.Char(string='Departemen / Unit Lama')
    partner_id = fields.Many2one('res.partner', string='Partner / Rekanan')
    account_ids = fields.Many2many(
        'sif.coa',
        string='Filter Akun (Opsional)',
        help='Kosongkan untuk menyertakan seluruh akun aktif.'
    )

    def action_print_pdf(self):
        self.ensure_one()
        url = (
            f"/sif_keuangan/export_general_ledger_pdf"
            f"?date_from={self.date_from}"
            f"&date_to={self.date_to}"
            f"&target_move={self.target_move}"
            f"&unit_name={self.unit_name or ''}"
            f"&partner_id={self.partner_id.id if self.partner_id else ''}"
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def action_export_xlsx(self):
        self.ensure_one()
        url = (
            f"/sif_keuangan/export_general_ledger_xlsx"
            f"?date_from={self.date_from}"
            f"&date_to={self.date_to}"
            f"&target_move={self.target_move}"
            f"&unit_name={self.unit_name or ''}"
            f"&partner_id={self.partner_id.id if self.partner_id else ''}"
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }


class ReportSifGeneralLedgerDocument(models.AbstractModel):
    _name = 'report.sif_keuangan.report_general_ledger_document'
    _description = 'Parser Laporan PDF General Ledger'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from_val = data.get('date_from')
        date_to_val = data.get('date_to')
        target_move_val = data.get('target_move', 'posted')
        unit_name_val = data.get('unit_name', '')
        partner_id_val = data.get('partner_id')

        if docids and not data:
            wizard = self.env['sif.general.ledger.wizard'].browse(docids[0])
            if wizard.exists():
                date_from_val = wizard.date_from.strftime('%Y-%m-%d') if wizard.date_from else None
                date_to_val = wizard.date_to.strftime('%Y-%m-%d') if wizard.date_to else None
                target_move_val = wizard.target_move
                unit_name_val = wizard.unit_name or ''
                partner_id_val = wizard.partner_id.id if wizard.partner_id else None

        # Konversi ke date object jika format string
        date_from_obj = date_from_val
        if isinstance(date_from_val, str) and date_from_val:
            try:
                date_from_obj = datetime.datetime.strptime(date_from_val, '%Y-%m-%d').date()
            except ValueError:
                date_from_obj = fields.Date.context_today(self).replace(day=1)

        date_to_obj = date_to_val
        if isinstance(date_to_val, str) and date_to_val:
            try:
                date_to_obj = datetime.datetime.strptime(date_to_val, '%Y-%m-%d').date()
            except ValueError:
                date_to_obj = fields.Date.context_today(self)

        gl_engine = self.env['sif.general.ledger']
        gl_data = gl_engine.get_general_ledger_data({
            'date_from': date_from_val,
            'date_to': date_to_val,
            'target_move': target_move_val,
            'unit_name': unit_name_val,
            'partner_id': partner_id_val,
        })

        return {
            'doc_ids': docids or [1],
            'doc_model': 'sif.general.ledger',
            'docs': [self.env.company],
            'company': self.env.company,
            'date_from': date_from_obj,
            'date_to': date_to_obj,
            'date_from_display': date_from_obj.strftime('%d/%m/%Y') if date_from_obj else '-',
            'date_to_display': date_to_obj.strftime('%d/%m/%Y') if date_to_obj else '-',
            'target_move': target_move_val,
            'unit_name': unit_name_val,
            'gl_data': gl_data,
            'accounts': gl_data.get('accounts', []),
            'grand_total': gl_data.get('grand_total', {}),
        }
