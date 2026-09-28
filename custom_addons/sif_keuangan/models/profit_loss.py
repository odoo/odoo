# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime


class SifProfitLoss(models.AbstractModel):
    _name = 'sif.profit.loss'
    _description = 'Profit and Loss (Laba Rugi) Service & Engine'

    def _company_scope_domain(self):
        return ['|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)]

    @api.model
    def _default_date_from(self):
        return fields.Date.context_today(self).replace(month=1, day=1)

    @api.model
    def _default_date_to(self):
        return fields.Date.context_today(self)

    @api.model
    def get_profit_loss_data(self, filters=None):
        """
        Engine penghitung Laporan Laba Rugi Multistep (Profit and Loss).
        Struktur:
        1. Revenue (Pendapatan Usaha) - Akun 50xxx
        2. Costs of Revenue (Beban Pokok Pendapatan / HPP) - Akun 60xxx
        => Gross Profit (Laba Kotor) = Revenue - Costs of Revenue
        3. Operating Expenses (Beban Operasional & Umum) - Akun 70xxx - 72xxx
        => Operating Income / Loss (Laba Operasional) = Gross Profit - Operating Expenses
        4. Other Income (Pendapatan Lain-lain) - Akun 80xxx
        5. Other Expenses (Beban Lain-lain) - Akun 90xxx
        => Net Profit (Laba Bersih Sebelum Alokasi) = Operating Income + Other Income - Other Expenses
        6. Allocations and Withdrawals (Prive / Dividen / Alokasi Laba)
        => Net Profit Left After Allocations and Withdrawals (Laba Bersih Akhir)
        """
        filters = filters or {}
        today = fields.Date.context_today(self)
        lang = filters.get('lang') or self.env.user.lang or self.env.context.get('lang', 'id_ID')
        is_id = str(lang).lower().startswith('id')

        # 1. Rentang Tanggal Utama
        date_from = filters.get('date_from')
        if not date_from:
            date_from = today.replace(month=1, day=1).strftime('%Y-%m-%d')

        date_to = filters.get('date_to')
        if not date_to:
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            date_to = (next_month - datetime.timedelta(days=next_month.day)).strftime('%Y-%m-%d')

        target_move = filters.get('target_move', 'posted')
        unit_name_filter = (filters.get('unit_name') or filters.get('unit_id') or '').strip()
        comparison_type = filters.get('comparison_type', 'none') # 'none', 'last_month', 'last_year', 'custom'
        custom_comp_date_from = filters.get('custom_comp_date_from')
        custom_comp_date_to = filters.get('custom_comp_date_to')

        # 2. Dapatkan list unit kerja unik
        distinct_units = self.env['sif.jurnal.entry'].search(self._company_scope_domain() + [
            ('unit_name', '!=', False),
            ('unit_name', '!=', '')
        ]).mapped('unit_name')
        units_list = sorted(list(set(distinct_units)))

        # 3. Hitung tanggal pembanding jika ada
        has_comparison = comparison_type != 'none'
        comp_date_from = None
        comp_date_to = None

        if has_comparison:
            comp_date_from, comp_date_to = self._calculate_comparison_dates(
                date_from, date_to, comparison_type, custom_comp_date_from, custom_comp_date_to
            )

        # 4. Ambil data periode utama
        primary_data = self._calculate_pl_period(date_from, date_to, target_move, unit_name_filter, is_id)

        # 5. Ambil data periode pembanding jika aktif
        comp_data = None
        if has_comparison and comp_date_from and comp_date_to:
            comp_data = self._calculate_pl_period(comp_date_from, comp_date_to, target_move, unit_name_filter, is_id)

        # 6. Gabungkan dan hitung variansi & persentase
        result_sections = self._merge_pl_sections(primary_data, comp_data, has_comparison)

        return {
            'date_from': date_from,
            'date_to': date_to,
            'date_from_display': self._format_date_display(date_from),
            'date_to_display': self._format_date_display(date_to),
            'has_comparison': has_comparison,
            'comparison_type': comparison_type,
            'comp_date_from': comp_date_from,
            'comp_date_to': comp_date_to,
            'comp_date_from_display': self._format_date_display(comp_date_from) if comp_date_from else '',
            'comp_date_to_display': self._format_date_display(comp_date_to) if comp_date_to else '',
            'target_move': target_move,
            'unit_name': unit_name_filter,
            'units_list': units_list,
            'company_name': ' / '.join(self.env.companies.mapped('name')) or self.env.company.name,
            'sections': result_sections,
            'summary': {
                'revenue_total': result_sections['revenue']['total'],
                'revenue_total_formatted': self._format_rupiah(result_sections['revenue']['total']),
                'gross_profit': result_sections['gross_profit']['total'],
                'gross_profit_formatted': self._format_rupiah(result_sections['gross_profit']['total']),
                'operating_income': result_sections['operating_income']['total'],
                'operating_income_formatted': self._format_rupiah(result_sections['operating_income']['total']),
                'net_profit': result_sections['net_profit']['total'],
                'net_profit_formatted': self._format_rupiah(result_sections['net_profit']['total']),
                'is_profit': result_sections['net_profit']['total'] >= 0,
            }
        }

    def _calculate_comparison_dates(self, date_from_str, date_to_str, comp_type, custom_from, custom_to):
        try:
            d_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d").date()
            d_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except Exception:
            return None, None

        if comp_type == 'last_month':
            first_curr = d_from.replace(day=1)
            prev_last = first_curr - datetime.timedelta(days=1)
            prev_first = prev_last.replace(day=1)
            return prev_first.strftime("%Y-%m-%d"), prev_last.strftime("%Y-%m-%d")

        elif comp_type == 'last_year':
            try:
                prev_from = d_from.replace(year=d_from.year - 1)
                prev_to = d_to.replace(year=d_to.year - 1)
            except ValueError:
                prev_from = d_from - datetime.timedelta(days=365)
                prev_to = d_to - datetime.timedelta(days=365)
            return prev_from.strftime("%Y-%m-%d"), prev_to.strftime("%Y-%m-%d")

        elif comp_type == 'custom':
            if custom_from and custom_to:
                return custom_from, custom_to
            return None, None

        return None, None

    def _calculate_pl_period(self, date_from, date_to, target_move, unit_name_filter, is_id=True):
        """
        Hitung seluruh saldo akun nominal (Income & Expense) dalam rentang tanggal.
        Pendapatan (Income) = Credit - Debit
        Beban (Expense) = Debit - Credit
        """
        domain = self._company_scope_domain() + [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        if unit_name_filter:
            domain.append(('entry_id.unit_name', '=', unit_name_filter))

        lines = self.env['sif.jurnal.line'].search(domain)
        
        # Agregasi debit dan kredit per akun
        account_debits = {}
        account_credits = {}
        for line in lines:
            acc_id = line.account_id.id
            account_debits[acc_id] = account_debits.get(acc_id, 0.0) + (line.debit or 0.0)
            account_credits[acc_id] = account_credits.get(acc_id, 0.0) + (line.credit or 0.0)

        # Ambil semua akun COA tipe income & expense
        coa_records = self.env['sif.coa'].search([
            ('active', '=', True),
            ('account_type', 'in', ['income', 'expense'])
        ], order='code asc')

        # Struktur Kategori
        sections = {
            'revenue': {'name': 'Pendapatan Usaha (Revenue)' if is_id else 'Operating Revenue', 'accounts': [], 'total': 0.0},
            'costs_of_revenue': {'name': 'Beban Pokok Pendapatan (Costs of Revenue)' if is_id else 'Cost of Goods Sold (COGS)', 'accounts': [], 'total': 0.0},
            'operating_expenses': {'name': 'Beban Operasional (Operating Expenses)' if is_id else 'Operating Expenses (OPEX)', 'accounts': [], 'total': 0.0},
            'other_income': {'name': 'Pendapatan Lain-lain (Other Income)' if is_id else 'Other Income', 'accounts': [], 'total': 0.0},
            'other_expenses': {'name': 'Beban Lain-lain (Other Expenses)' if is_id else 'Other Expenses', 'accounts': [], 'total': 0.0},
            'allocations': {'name': 'Alokasi & Penarikan (Allocations)' if is_id else 'Allocations and Withdrawals', 'accounts': [], 'total': 0.0},
        }

        for acc in coa_records:
            deb = account_debits.get(acc.id, 0.0)
            crd = account_credits.get(acc.id, 0.0)
            code_int = self._safe_int(acc.code)

            # Tentukan kategori dan hitung saldo bersih
            if acc.account_type == 'income' or (code_int and 50000 <= code_int <= 59999):
                if code_int and code_int >= 80000:
                    # Other Income
                    balance = crd - deb
                    sec_key = 'other_income'
                else:
                    balance = crd - deb
                    sec_key = 'revenue'
            elif acc.account_type == 'expense':
                balance = deb - crd
                if code_int and 60000 <= code_int <= 69999:
                    sec_key = 'costs_of_revenue'
                elif code_int and 70000 <= code_int <= 79999:
                    sec_key = 'operating_expenses'
                elif code_int and 90000 <= code_int <= 99999:
                    sec_key = 'other_expenses'
                else:
                    sec_key = 'operating_expenses'
            else:
                continue

            # Jangan tampilkan akun yang saldonya 0 jika tidak ada mutasi sama sekali
            if abs(balance) < 0.001 and abs(deb) < 0.001 and abs(crd) < 0.001:
                continue

            acc_dict = {
                'id': acc.id,
                'code': acc.code or '',
                'name': acc.name or '',
                'full_name': f"{acc.code} {acc.name}",
                'account_type': acc.account_type,
                'debit': deb,
                'credit': crd,
                'balance': balance,
            }
            sections[sec_key]['accounts'].append(acc_dict)
            sections[sec_key]['total'] += balance

        # Hitung subtotals & profits
        rev = sections['revenue']['total']
        cogs = sections['costs_of_revenue']['total']
        gross_profit = rev - cogs

        opex = sections['operating_expenses']['total']
        operating_income = gross_profit - opex

        oth_inc = sections['other_income']['total']
        oth_exp = sections['other_expenses']['total']
        net_profit = operating_income + oth_inc - oth_exp

        alloc = sections['allocations']['total']
        net_profit_after_alloc = net_profit - alloc

        return {
            'revenue': sections['revenue'],
            'costs_of_revenue': sections['costs_of_revenue'],
            'gross_profit': {'name': 'Laba Kotor (Gross Profit)' if is_id else 'Gross Profit', 'total': gross_profit},
            'operating_expenses': sections['operating_expenses'],
            'operating_income': {'name': 'Laba Operasional (Operating Income)' if is_id else 'Operating Income (or Loss)', 'total': operating_income},
            'other_income': sections['other_income'],
            'other_expenses': sections['other_expenses'],
            'net_profit': {'name': 'Laba Bersih (Net Profit)' if is_id else 'Net Profit', 'total': net_profit},
            'allocations': sections['allocations'],
            'net_profit_after_alloc': {
                'name': 'Laba Bersih Akhir (Net Profit Left)' if is_id else 'Net Profit Left After Allocations and Withdrawals',
                'total': net_profit_after_alloc
            }
        }

    def _merge_pl_sections(self, cur, comp, has_comp):
        """
        Menggabungkan periode aktif dengan pembanding dan menghitung variansi serta persentase.
        """
        def format_section(sec_key, is_calculated=False):
            cur_sec = cur[sec_key]
            cur_tot = cur_sec['total']
            comp_tot = comp[sec_key]['total'] if comp else 0.0
            diff = cur_tot - comp_tot
            diff_pct = ((diff / abs(comp_tot)) * 100.0) if (has_comp and abs(comp_tot) > 0.001) else 0.0

            sec_data = {
                'name': cur_sec['name'],
                'total': cur_tot,
                'total_formatted': self._format_rupiah(cur_tot),
                'comp_total': comp_tot,
                'comp_total_formatted': self._format_rupiah(comp_tot) if has_comp else '',
                'diff': diff,
                'diff_formatted': self._format_rupiah(diff) if has_comp else '',
                'diff_pct': diff_pct,
                'diff_pct_formatted': f"{diff_pct:+.1f}%" if has_comp else '',
                'is_negative': cur_tot < -0.001,
                'is_diff_negative': diff < -0.001,
            }

            if not is_calculated:
                # Merge accounts
                cur_accounts = {a['id']: a for a in cur_sec.get('accounts', [])}
                comp_accounts = {a['id']: a for a in (comp[sec_key].get('accounts', []) if comp else [])}
                all_ids = list(cur_accounts.keys()) + [i for i in comp_accounts.keys() if i not in cur_accounts]

                accounts_list = []
                for a_id in all_ids:
                    c_acc = cur_accounts.get(a_id)
                    p_acc = comp_accounts.get(a_id)

                    code = c_acc['code'] if c_acc else p_acc['code']
                    name = c_acc['name'] if c_acc else p_acc['name']
                    full_name = c_acc['full_name'] if c_acc else p_acc['full_name']
                    bal = c_acc['balance'] if c_acc else 0.0
                    c_bal = p_acc['balance'] if p_acc else 0.0
                    acc_diff = bal - c_bal
                    acc_diff_pct = ((acc_diff / abs(c_bal)) * 100.0) if (has_comp and abs(c_bal) > 0.001) else 0.0

                    accounts_list.append({
                        'id': a_id,
                        'code': code,
                        'name': name,
                        'full_name': full_name,
                        'balance': bal,
                        'balance_formatted': self._format_rupiah(bal),
                        'comp_balance': c_bal,
                        'comp_balance_formatted': self._format_rupiah(c_bal) if has_comp else '',
                        'diff': acc_diff,
                        'diff_formatted': self._format_rupiah(acc_diff) if has_comp else '',
                        'diff_pct': acc_diff_pct,
                        'diff_pct_formatted': f"{acc_diff_pct:+.1f}%" if has_comp else '',
                        'is_negative': bal < -0.001,
                        'is_diff_negative': acc_diff < -0.001,
                    })

                accounts_list.sort(key=lambda x: x['code'])
                sec_data['accounts'] = accounts_list
                sec_data['accounts_count'] = len(accounts_list)

            return sec_data

        return {
            'revenue': format_section('revenue'),
            'costs_of_revenue': format_section('costs_of_revenue'),
            'gross_profit': format_section('gross_profit', is_calculated=True),
            'operating_expenses': format_section('operating_expenses'),
            'operating_income': format_section('operating_income', is_calculated=True),
            'other_income': format_section('other_income'),
            'other_expenses': format_section('other_expenses'),
            'net_profit': format_section('net_profit', is_calculated=True),
            'allocations': format_section('allocations'),
            'net_profit_after_alloc': format_section('net_profit_after_alloc', is_calculated=True),
        }

    def _safe_int(self, val):
        try:
            return int(str(val).strip())
        except (ValueError, TypeError):
            return None

    def _format_rupiah(self, amount):
        if amount is None:
            return "Rp 0,00"
        is_neg = amount < -0.001
        abs_amt = abs(amount)
        formatted = f"{abs_amt:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if is_neg:
            return f"-Rp {formatted}"
        return f"Rp {formatted}"

    def _format_date_display(self, date_str):
        if not date_str:
            return ""
        try:
            dt = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return str(date_str)


class SifProfitLossWizard(models.TransientModel):
    _name = 'sif.profit.loss.wizard'
    _description = 'Wizard Cetak Laporan Profit and Loss'

    date_from = fields.Date(
        string='Dari Tanggal',
        required=True,
        default=lambda self: self.env['sif.profit.loss']._default_date_from()
    )
    date_to = fields.Date(
        string='Sampai Tanggal',
        required=True,
        default=lambda self: self.env['sif.profit.loss']._default_date_to()
    )
    target_move = fields.Selection(
        [('posted', 'Hanya Jurnal Disetujui (Posted)'),
         ('all', 'Semua Jurnal (Termasuk Draft)')],
        string='Status Jurnal',
        required=True,
        default='posted'
    )
    unit_name = fields.Char(string='Departemen / Unit Lama')
    comparison_type = fields.Selection(
        [('none', 'Tanpa Komparasi'),
         ('last_month', 'Bulan Sebelumnya'),
         ('last_year', 'Tahun Lalu (YoY)')],
        string='Komparasi Periode',
        default='none'
    )

    def action_print_pdf(self):
        self.ensure_one()
        url = (
            f"/sif_keuangan/export_profit_loss_pdf"
            f"?date_from={self.date_from}"
            f"&date_to={self.date_to}"
            f"&target_move={self.target_move}"
            f"&unit_name={self.unit_name or ''}"
            f"&comparison_type={self.comparison_type or 'none'}"
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def action_export_xlsx(self):
        self.ensure_one()
        url = (
            f"/sif_keuangan/export_profit_loss_xlsx"
            f"?date_from={self.date_from}"
            f"&date_to={self.date_to}"
            f"&target_move={self.target_move}"
            f"&unit_name={self.unit_name or ''}"
            f"&comparison_type={self.comparison_type or 'none'}"
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }


class ReportSifProfitLossDocument(models.AbstractModel):
    _name = 'report.sif_keuangan.report_profit_loss_document'
    _description = 'Parser Laporan PDF Profit and Loss'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from_val = data.get('date_from')
        date_to_val = data.get('date_to')
        target_move_val = data.get('target_move', 'posted')
        unit_name_val = data.get('unit_name', '')
        comparison_type_val = data.get('comparison_type', 'none')

        if docids and not data:
            wizard = self.env['sif.profit.loss.wizard'].browse(docids[0])
            if wizard.exists():
                date_from_val = wizard.date_from.strftime('%Y-%m-%d') if wizard.date_from else None
                date_to_val = wizard.date_to.strftime('%Y-%m-%d') if wizard.date_to else None
                target_move_val = wizard.target_move
                unit_name_val = wizard.unit_name or ''
                comparison_type_val = wizard.comparison_type or 'none'

        date_from_obj = date_from_val
        if isinstance(date_from_val, str) and date_from_val:
            try:
                date_from_obj = datetime.datetime.strptime(date_from_val, '%Y-%m-%d').date()
            except ValueError:
                date_from_obj = fields.Date.context_today(self).replace(month=1, day=1)

        date_to_obj = date_to_val
        if isinstance(date_to_val, str) and date_to_val:
            try:
                date_to_obj = datetime.datetime.strptime(date_to_val, '%Y-%m-%d').date()
            except ValueError:
                date_to_obj = fields.Date.context_today(self)

        pl_engine = self.env['sif.profit.loss']
        pl_data = pl_engine.get_profit_loss_data({
            'date_from': date_from_val,
            'date_to': date_to_val,
            'target_move': target_move_val,
            'unit_name': unit_name_val,
            'comparison_type': comparison_type_val,
        })

        return {
            'doc_ids': docids or [1],
            'doc_model': 'sif.profit.loss',
            'docs': [self.env.company],
            'company': self.env.company,
            'date_from': date_from_obj,
            'date_to': date_to_obj,
            'date_from_display': date_from_obj.strftime('%d/%m/%Y') if date_from_obj else '-',
            'date_to_display': date_to_obj.strftime('%d/%m/%Y') if date_to_obj else '-',
            'target_move': target_move_val,
            'unit_name': unit_name_val,
            'pl_data': pl_data,
            'sections': pl_data.get('sections', {}),
            'summary': pl_data.get('summary', {}),
        }
