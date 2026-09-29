# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime


class SifBalanceSheet(models.AbstractModel):
    _name = 'sif.balance.sheet'
    _description = 'Balance Sheet (Neraca) Service & Engine'

    def _company_scope_domain(self):
        return ['|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)]

    @api.model
    def _default_date_to(self):
        return fields.Date.context_today(self)

    @api.model
    def _format_rupiah(self, amount):
        if amount is None:
            return "Rp 0,00"
        val = float(amount)
        prefix = "-Rp " if val < -0.001 else "Rp "
        abs_val = abs(val)
        parts = f"{abs_val:,.2f}".split(".")
        int_part = parts[0].replace(",", ".")
        dec_part = parts[1]
        return f"{prefix}{int_part},{dec_part}"

    @api.model
    def _format_percentage(self, diff, base):
        if abs(base) < 0.001:
            if abs(diff) < 0.001:
                return "0,0%"
            return "+100,0%" if diff > 0 else "-100,0%"
        pct = (diff / abs(base)) * 100.0
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:,.1f}%".replace(".", ",")

    def _get_comparison_date(self, date_to_str, comp_type, custom_date_str=None):
        if comp_type == 'none' or not comp_type:
            return None
        dt = datetime.datetime.strptime(date_to_str, '%Y-%m-%d').date() if isinstance(date_to_str, str) else date_to_str
        if comp_type == 'last_month':
            first_this_month = dt.replace(day=1)
            last_prev_month = first_this_month - datetime.timedelta(days=1)
            return last_prev_month.strftime('%Y-%m-%d')
        elif comp_type == 'last_year':
            try:
                return dt.replace(year=dt.year - 1).strftime('%Y-%m-%d')
            except ValueError:
                return dt.replace(year=dt.year - 1, day=28).strftime('%Y-%m-%d')
        elif comp_type == 'custom' and custom_date_str:
            return custom_date_str
        return None

    def _calculate_snapshot(self, date_to_str, target_move, unit_name=None):
        """
        Hitung kalkulasi mentah saldo akun dan laba/rugi posisi per date_to_str.
        """
        today = fields.Date.context_today(self)
        date_to = date_to_str or today.strftime('%Y-%m-%d')
        date_to_dt = datetime.datetime.strptime(date_to, '%Y-%m-%d').date() if isinstance(date_to, str) else date_to
        fiscal_year_start = date_to_dt.replace(month=1, day=1).strftime('%Y-%m-%d')
        fy_start_dt = datetime.datetime.strptime(fiscal_year_start, '%Y-%m-%d').date()

        base_domain = self._company_scope_domain() + [('date', '<=', date_to)]
        if target_move == 'posted':
            base_domain.append(('state', '=', 'posted'))
        if unit_name:
            base_domain.append(('unit_name', '=', unit_name))

        lines = self.env['sif.jurnal.line'].search(base_domain)

        account_debit_balance = {}
        account_credit_balance = {}
        cy_income_total = 0.0
        cy_expense_total = 0.0
        py_income_total = 0.0
        py_expense_total = 0.0

        for line in lines:
            acc = line.account_id
            acc_id = acc.id
            deb = line.debit or 0.0
            crd = line.credit or 0.0
            line_date = line.date

            account_debit_balance[acc_id] = account_debit_balance.get(acc_id, 0.0) + (deb - crd)
            account_credit_balance[acc_id] = account_credit_balance.get(acc_id, 0.0) + (crd - deb)

            if acc.account_type == 'income':
                if line_date >= fy_start_dt:
                    cy_income_total += (crd - deb)
                else:
                    py_income_total += (crd - deb)
            elif acc.account_type == 'expense':
                if line_date >= fy_start_dt:
                    cy_expense_total += (deb - crd)
                else:
                    py_expense_total += (deb - crd)

        current_year_earnings = cy_income_total - cy_expense_total
        previous_years_earnings = py_income_total - py_expense_total

        all_accounts = self.env['sif.coa'].search([('active', '=', True)], order='code asc')

        account_amounts = {}
        for acc in all_accounts:
            bal_deb = account_debit_balance.get(acc.id, 0.0)
            bal_crd = account_credit_balance.get(acc.id, 0.0)
            account_amounts[acc.id] = bal_deb if acc.account_type == 'asset' else bal_crd

        return {
            'date_to': date_to,
            'date_to_dt': date_to_dt,
            'account_amounts': account_amounts,
            'current_year_earnings': current_year_earnings,
            'previous_years_earnings': previous_years_earnings,
        }

    @api.model
    def get_balance_sheet_data(self, filters=None):
        """
        Kalkulasi Neraca (Balance Sheet) lengkap dengan opsi Multi-period Comparison dan Filter Unit Kerja.
        """
        filters = filters or {}
        today = fields.Date.context_today(self)
        lang = filters.get('lang') or self.env.user.lang or self.env.context.get('lang', 'id_ID')
        is_id = str(lang).lower().startswith('id')
        
        date_to = filters.get('date_to') or today.strftime('%Y-%m-%d')
        date_from = filters.get('date_from') or today.replace(month=1, day=1).strftime('%Y-%m-%d')
        target_move = filters.get('target_move', 'posted')
        unit_name = filters.get('unit_name') or False
        comparison_type = filters.get('comparison_type', 'none')
        custom_comp_date = filters.get('comparison_date')

        # Ambil daftar Unit Kerja yang tersedia di jurnal
        self.env.cr.execute("""
            SELECT DISTINCT unit_name 
            FROM sif_jurnal_entry 
            WHERE unit_name IS NOT NULL AND unit_name != ''
              AND (company_id IS NULL OR company_id = ANY(%s))
            ORDER BY unit_name
        """, (self.env.companies.ids,))
        units_list = [r[0] for r in self.env.cr.fetchall()]

        # Hitung snapshot periode utama
        snap_cur = self._calculate_snapshot(date_to, target_move, unit_name)

        # Hitung snapshot komparasi jika aktif
        comp_date = self._get_comparison_date(date_to, comparison_type, custom_comp_date)
        has_comparison = bool(comp_date)
        snap_comp = self._calculate_snapshot(comp_date, target_move, unit_name) if has_comparison else None

        all_accounts = self.env['sif.coa'].search([('active', '=', True)], order='code asc')

        def build_line(acc):
            amt_cur = snap_cur['account_amounts'].get(acc.id, 0.0)
            amt_comp = snap_comp['account_amounts'].get(acc.id, 0.0) if has_comparison else 0.0
            diff = amt_cur - amt_comp
            return {
                'id': acc.id,
                'code': acc.code,
                'name': acc.name,
                'full_name': f"[{acc.code}] {acc.name}",
                'amount': amt_cur,
                'amount_formatted': self._format_rupiah(amt_cur),
                'is_negative': amt_cur < -0.001,
                'comp_amount': amt_comp,
                'comp_amount_formatted': self._format_rupiah(amt_comp),
                'comp_is_negative': amt_comp < -0.001,
                'diff_amount': diff,
                'diff_amount_formatted': self._format_rupiah(diff),
                'diff_is_positive': diff > 0.001,
                'diff_is_negative': diff < -0.001,
                'diff_percentage': self._format_percentage(diff, amt_comp),
            }

        def build_section(title, lines_list, sub_total_cur, sub_total_comp):
            diff = sub_total_cur - sub_total_comp
            return {
                'title': title,
                'lines': lines_list,
                'total': sub_total_cur,
                'total_formatted': self._format_rupiah(sub_total_cur),
                'is_negative': sub_total_cur < -0.001,
                'comp_total': sub_total_comp,
                'comp_total_formatted': self._format_rupiah(sub_total_comp),
                'comp_is_negative': sub_total_comp < -0.001,
                'diff_total': diff,
                'diff_total_formatted': self._format_rupiah(diff),
                'diff_is_positive': diff > 0.001,
                'diff_is_negative': diff < -0.001,
                'diff_percentage': self._format_percentage(diff, sub_total_comp),
            }

        # 1. ASSETS
        bank_cash_lines = []
        receivables_lines = []
        other_current_assets_lines = []
        prepayments_lines = []
        fixed_assets_lines = []
        non_current_assets_lines = []

        tot_cur_bank_cash = tot_comp_bank_cash = 0.0
        tot_cur_receivables = tot_comp_receivables = 0.0
        tot_cur_other_ca = tot_comp_other_ca = 0.0
        tot_cur_prepayments = tot_comp_prepayments = 0.0
        tot_cur_fixed_assets = tot_comp_fixed_assets = 0.0
        tot_cur_non_current_assets = tot_comp_non_current_assets = 0.0

        # 2. LIABILITIES
        current_liabilities_lines = []
        payables_lines = []
        credit_card_lines = []
        non_current_liabilities_lines = []

        tot_cur_curr_liab = tot_comp_curr_liab = 0.0
        tot_cur_payables = tot_comp_payables = 0.0
        tot_cur_credit_card = tot_comp_credit_card = 0.0
        tot_cur_non_curr_liab = tot_comp_non_curr_liab = 0.0

        # 3. EQUITY
        equity_lines = []
        tot_cur_equity_direct = tot_comp_equity_direct = 0.0

        for acc in all_accounts:
            code = acc.code or ''
            amt_cur = snap_cur['account_amounts'].get(acc.id, 0.0)
            amt_comp = snap_comp['account_amounts'].get(acc.id, 0.0) if has_comparison else 0.0

            # Filter hanya akun yang memiliki saldo di salah satu periode
            if abs(amt_cur) < 0.001 and abs(amt_comp) < 0.001:
                continue

            line_obj = build_line(acc)

            if acc.account_type == 'asset':
                if code.startswith('110') or code.startswith('111') or code.startswith('112'):
                    bank_cash_lines.append(line_obj)
                    tot_cur_bank_cash += amt_cur
                    tot_comp_bank_cash += amt_comp
                elif code.startswith('120') or code.startswith('121') or code.startswith('122'):
                    receivables_lines.append(line_obj)
                    tot_cur_receivables += amt_cur
                    tot_comp_receivables += amt_comp
                elif code.startswith('160') or code.startswith('130'):
                    prepayments_lines.append(line_obj)
                    tot_cur_prepayments += amt_cur
                    tot_comp_prepayments += amt_comp
                elif code.startswith('13') or code.startswith('14') or code.startswith('15') or code.startswith('17'):
                    other_current_assets_lines.append(line_obj)
                    tot_cur_other_ca += amt_cur
                    tot_comp_other_ca += amt_comp
                elif code.startswith('21') or code.startswith('22') or code.startswith('23') or code.startswith('24'):
                    fixed_assets_lines.append(line_obj)
                    tot_cur_fixed_assets += amt_cur
                    tot_comp_fixed_assets += amt_comp
                else:
                    non_current_assets_lines.append(line_obj)
                    tot_cur_non_current_assets += amt_cur
                    tot_comp_non_current_assets += amt_comp

            elif acc.account_type == 'liability':
                if code.startswith('30') or code.startswith('31'):
                    payables_lines.append(line_obj)
                    tot_cur_payables += amt_cur
                    tot_comp_payables += amt_comp
                elif 'credit' in acc.name.lower() or 'kartu kredit' in acc.name.lower():
                    credit_card_lines.append(line_obj)
                    tot_cur_credit_card += amt_cur
                    tot_comp_credit_card += amt_comp
                elif code.startswith('32') or code.startswith('33') or code.startswith('34'):
                    current_liabilities_lines.append(line_obj)
                    tot_cur_curr_liab += amt_cur
                    tot_comp_curr_liab += amt_comp
                else:
                    non_current_liabilities_lines.append(line_obj)
                    tot_cur_non_curr_liab += amt_cur
                    tot_comp_non_curr_liab += amt_comp

            elif acc.account_type == 'equity':
                equity_lines.append(line_obj)
                tot_cur_equity_direct += amt_cur
                tot_comp_equity_direct += amt_comp

        # Subtotals ASSETS
        tot_cur_curr_assets = tot_cur_bank_cash + tot_cur_receivables + tot_cur_other_ca + tot_cur_prepayments
        tot_comp_curr_assets = tot_comp_bank_cash + tot_comp_receivables + tot_comp_other_ca + tot_comp_prepayments
        tot_cur_assets = tot_cur_curr_assets + tot_cur_fixed_assets + tot_cur_non_current_assets
        tot_comp_assets = tot_comp_curr_assets + tot_comp_fixed_assets + tot_comp_non_current_assets

        # Subtotals LIABILITIES
        tot_cur_curr_liab_all = tot_cur_curr_liab + tot_cur_payables + tot_cur_credit_card
        tot_comp_curr_liab_all = tot_comp_curr_liab + tot_comp_payables + tot_comp_credit_card
        tot_cur_liabilities = tot_cur_curr_liab_all + tot_cur_non_curr_liab
        tot_comp_liabilities = tot_comp_curr_liab_all + tot_comp_non_curr_liab

        # Subtotals EQUITY & EARNINGS
        cur_cy_earn = snap_cur['current_year_earnings']
        comp_cy_earn = snap_comp['current_year_earnings'] if has_comparison else 0.0
        cur_py_earn = snap_cur['previous_years_earnings']
        comp_py_earn = snap_comp['previous_years_earnings'] if has_comparison else 0.0

        tot_cur_earnings = cur_cy_earn + cur_py_earn
        tot_comp_earnings = comp_cy_earn + comp_py_earn

        tot_cur_eq_all = tot_cur_equity_direct + tot_cur_earnings
        tot_comp_eq_all = tot_comp_equity_direct + tot_comp_earnings

        # Grand Summary
        tot_cur_liab_eq = tot_cur_liabilities + tot_cur_eq_all
        tot_comp_liab_eq = tot_comp_liabilities + tot_comp_eq_all

        net_diff_cur = tot_cur_assets - tot_cur_liab_eq
        is_balanced_cur = abs(net_diff_cur) < 0.01

        # Format display dates
        try:
            d_from_display = datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            d_from_display = str(date_from)
        try:
            d_to_display = snap_cur['date_to_dt'].strftime('%d/%m/%Y')
        except Exception:
            d_to_display = str(date_to)

        comp_date_display = snap_comp['date_to_dt'].strftime('%d/%m/%Y') if has_comparison else ''

        diff_assets = tot_cur_assets - tot_comp_assets
        diff_liab_eq = tot_cur_liab_eq - tot_comp_liab_eq

        return {
            'company_name': ' / '.join(self.env.companies.mapped('name')) or self.env.company.name,
            'date_from': date_from,
            'date_to': date_to,
            'date_from_display': d_from_display,
            'date_to_display': d_to_display,
            'has_comparison': has_comparison,
            'comparison_type': comparison_type,
            'comparison_date': comp_date or '',
            'comparison_date_display': comp_date_display,
            'target_move': target_move,
            'unit_name': unit_name or '',
            'units_list': units_list,

            'assets': {
                'title': 'ASET (AKTIVA)' if is_id else 'ASSETS',
                'total': tot_cur_assets,
                'total_formatted': self._format_rupiah(tot_cur_assets),
                'is_negative': tot_cur_assets < -0.001,
                'comp_total': tot_comp_assets,
                'comp_total_formatted': self._format_rupiah(tot_comp_assets),
                'comp_is_negative': tot_comp_assets < -0.001,
                'diff_total': diff_assets,
                'diff_total_formatted': self._format_rupiah(diff_assets),
                'diff_is_positive': diff_assets > 0.001,
                'diff_is_negative': diff_assets < -0.001,
                'diff_percentage': self._format_percentage(diff_assets, tot_comp_assets),

                'current_assets': {
                    'title': 'Aset Lancar' if is_id else 'Current Assets',
                    'total': tot_cur_curr_assets,
                    'total_formatted': self._format_rupiah(tot_cur_curr_assets),
                    'is_negative': tot_cur_curr_assets < -0.001,
                    'comp_total': tot_comp_curr_assets,
                    'comp_total_formatted': self._format_rupiah(tot_comp_curr_assets),
                    'diff_total': tot_cur_curr_assets - tot_comp_curr_assets,
                    'diff_total_formatted': self._format_rupiah(tot_cur_curr_assets - tot_comp_curr_assets),
                    'diff_percentage': self._format_percentage(tot_cur_curr_assets - tot_comp_curr_assets, tot_comp_curr_assets),

                    'bank_and_cash': build_section('Bank dan Kas' if is_id else 'Bank and Cash Accounts', bank_cash_lines, tot_cur_bank_cash, tot_comp_bank_cash),
                    'receivables': build_section('Piutang Usaha' if is_id else 'Receivables', receivables_lines, tot_cur_receivables, tot_comp_receivables),
                    'other_current_assets': build_section('Aset Lancar Lainnya' if is_id else 'Other Current Assets', other_current_assets_lines, tot_cur_other_ca, tot_comp_other_ca),
                    'prepayments': build_section('Biaya Dibayar Dimuka' if is_id else 'Prepayments', prepayments_lines, tot_cur_prepayments, tot_comp_prepayments),
                },
                'fixed_assets': build_section('Aset Tetap' if is_id else 'Fixed Assets', fixed_assets_lines, tot_cur_fixed_assets, tot_comp_fixed_assets),
                'non_current_assets': build_section('Aset Tidak Lancar Lainnya' if is_id else 'Other Non-Current Assets', non_current_assets_lines, tot_cur_non_current_assets, tot_comp_non_current_assets),
            },

            'liabilities': {
                'title': 'KEWAJIBAN (LIABILITAS)' if is_id else 'LIABILITIES',
                'total': tot_cur_liabilities,
                'total_formatted': self._format_rupiah(tot_cur_liabilities),
                'is_negative': tot_cur_liabilities < -0.001,
                'comp_total': tot_comp_liabilities,
                'comp_total_formatted': self._format_rupiah(tot_comp_liabilities),
                'comp_is_negative': tot_comp_liabilities < -0.001,
                'diff_total': tot_cur_liabilities - tot_comp_liabilities,
                'diff_total_formatted': self._format_rupiah(tot_cur_liabilities - tot_comp_liabilities),
                'diff_percentage': self._format_percentage(tot_cur_liabilities - tot_comp_liabilities, tot_comp_liabilities),

                'current_liabilities': {
                    'title': 'Kewajiban Lancar' if is_id else 'Current Liabilities',
                    'total': tot_cur_curr_liab_all,
                    'total_formatted': self._format_rupiah(tot_cur_curr_liab_all),
                    'is_negative': tot_cur_curr_liab_all < -0.001,
                    'comp_total': tot_comp_curr_liab_all,
                    'comp_total_formatted': self._format_rupiah(tot_comp_curr_liab_all),
                    'diff_total': tot_cur_curr_liab_all - tot_comp_curr_liab_all,
                    'diff_total_formatted': self._format_rupiah(tot_cur_curr_liab_all - tot_comp_curr_liab_all),
                    'diff_percentage': self._format_percentage(tot_cur_curr_liab_all - tot_comp_curr_liab_all, tot_comp_curr_liab_all),

                    'general_current': build_section('Kewajiban Lancar Lainnya' if is_id else 'Other Current Liabilities', current_liabilities_lines, tot_cur_curr_liab, tot_comp_curr_liab),
                    'credit_card': build_section('Hutang Kartu Kredit' if is_id else 'Credit Card Payables', credit_card_lines, tot_cur_credit_card, tot_comp_credit_card),
                    'payables': build_section('Hutang Usaha' if is_id else 'Payables', payables_lines, tot_cur_payables, tot_comp_payables),
                },
                'non_current_liabilities': build_section('Kewajiban Jangka Panjang' if is_id else 'Non-Current Liabilities', non_current_liabilities_lines, tot_cur_non_curr_liab, tot_comp_non_curr_liab),
            },

            'equity': {
                'title': 'EKUITAS & MODAL' if is_id else 'EQUITY & CAPITAL',
                'total': tot_cur_eq_all,
                'total_formatted': self._format_rupiah(tot_cur_eq_all),
                'is_negative': tot_cur_eq_all < -0.001,
                'comp_total': tot_comp_eq_all,
                'comp_total_formatted': self._format_rupiah(tot_comp_eq_all),
                'comp_is_negative': tot_comp_eq_all < -0.001,
                'diff_total': tot_cur_eq_all - tot_comp_eq_all,
                'diff_total_formatted': self._format_rupiah(tot_cur_eq_all - tot_comp_eq_all),
                'diff_percentage': self._format_percentage(tot_cur_eq_all - tot_comp_eq_all, tot_comp_eq_all),

                'direct_equity': build_section('Modal Langsung' if is_id else 'Direct Equity', equity_lines, tot_cur_equity_direct, tot_comp_equity_direct),
                'earnings': {
                    'title': 'Laba' if is_id else 'Earnings',
                    'total': tot_cur_earnings,
                    'total_formatted': self._format_rupiah(tot_cur_earnings),
                    'is_negative': tot_cur_earnings < -0.001,
                    'comp_total': tot_comp_earnings,
                    'comp_total_formatted': self._format_rupiah(tot_comp_earnings),
                    'diff_total': tot_cur_earnings - tot_comp_earnings,
                    'diff_total_formatted': self._format_rupiah(tot_cur_earnings - tot_comp_earnings),
                    'diff_percentage': self._format_percentage(tot_cur_earnings - tot_comp_earnings, tot_comp_earnings),

                    'current_year_earnings': {
                        'title': 'Laba Tahun Berjalan' if is_id else 'Current Year Earnings',
                        'total': cur_cy_earn,
                        'total_formatted': self._format_rupiah(cur_cy_earn),
                        'is_negative': cur_cy_earn < -0.001,
                        'comp_total': comp_cy_earn,
                        'comp_total_formatted': self._format_rupiah(comp_cy_earn),
                        'diff_total': cur_cy_earn - comp_cy_earn,
                        'diff_total_formatted': self._format_rupiah(cur_cy_earn - comp_cy_earn),
                        'diff_percentage': self._format_percentage(cur_cy_earn - comp_cy_earn, comp_cy_earn),
                    },
                    'previous_years_earnings': {
                        'title': 'Laba Ditahan (Tahun Lalu)' if is_id else 'Retained Earnings (Previous Years)',
                        'total': cur_py_earn,
                        'total_formatted': self._format_rupiah(cur_py_earn),
                        'is_negative': cur_py_earn < -0.001,
                        'comp_total': comp_py_earn,
                        'comp_total_formatted': self._format_rupiah(comp_py_earn),
                        'diff_total': cur_py_earn - comp_py_earn,
                        'diff_total_formatted': self._format_rupiah(cur_py_earn - comp_py_earn),
                        'diff_percentage': self._format_percentage(cur_py_earn - comp_py_earn, comp_py_earn),
                    },
                },
            },

            'summary': {
                'total_assets': tot_cur_assets,
                'total_assets_formatted': self._format_rupiah(tot_cur_assets),
                'comp_total_assets': tot_comp_assets,
                'comp_total_assets_formatted': self._format_rupiah(tot_comp_assets),
                'diff_assets': diff_assets,
                'diff_assets_formatted': self._format_rupiah(diff_assets),

                'total_liabilities_and_equity': tot_cur_liab_eq,
                'total_liabilities_and_equity_formatted': self._format_rupiah(tot_cur_liab_eq),
                'comp_total_liabilities_and_equity': tot_comp_liab_eq,
                'comp_total_liabilities_and_equity_formatted': self._format_rupiah(tot_comp_liab_eq),
                'diff_liab_eq': diff_liab_eq,
                'diff_liab_eq_formatted': self._format_rupiah(diff_liab_eq),

                'difference': net_diff_cur,
                'difference_formatted': self._format_rupiah(net_diff_cur),
                'is_balanced': is_balanced_cur,
            }
        }


class SifBalanceSheetWizard(models.TransientModel):
    _name = 'sif.balance.sheet.wizard'
    _description = 'Wizard Filter Laporan Balance Sheet'

    date_from = fields.Date(
        string='Dari Tanggal',
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1)
    )
    date_to = fields.Date(
        string='Sampai Tanggal',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )
    target_move = fields.Selection([
        ('posted', 'Hanya Jurnal Disetujui (Posted)'),
        ('all', 'Semua Jurnal (Termasuk Draft)'),
    ], string='Status Entri', default='posted', required=True)
    unit_name = fields.Char(string='Departemen / Unit Lama')
    comparison_type = fields.Selection([
        ('none', 'Tanpa Komparasi'),
        ('last_month', 'Bulan Sebelumnya'),
        ('last_year', 'Tahun Sebelumnya (YoY)'),
        ('custom', 'Tanggal Kustom'),
    ], string='Komparasi Periode', default='none')
    comparison_date = fields.Date(string='Tanggal Komparasi')

    def action_print_pdf(self):
        query = f"date_from={self.date_from or ''}&date_to={self.date_to}&target_move={self.target_move}"
        if self.unit_name:
            query += f"&unit_name={self.unit_name}"
        if self.comparison_type and self.comparison_type != 'none':
            query += f"&comparison_type={self.comparison_type}"
        if self.comparison_date:
            query += f"&comparison_date={self.comparison_date}"
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sif_keuangan/export_balance_sheet_pdf?{query}',
            'target': 'self',
        }

    def action_export_xlsx(self):
        query = f"date_from={self.date_from or ''}&date_to={self.date_to}&target_move={self.target_move}"
        if self.unit_name:
            query += f"&unit_name={self.unit_name}"
        if self.comparison_type and self.comparison_type != 'none':
            query += f"&comparison_type={self.comparison_type}"
        if self.comparison_date:
            query += f"&comparison_date={self.comparison_date}"
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sif_keuangan/export_balance_sheet_xlsx?{query}',
            'target': 'self',
        }


class ReportBalanceSheetDocument(models.AbstractModel):
    _name = 'report.sif_keuangan.report_balance_sheet_document'
    _description = 'Parser Dokumen Cetak Balance Sheet QWeb'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sif.balance.sheet.wizard'].browse(docids)
        doc = docs[0] if docs else None

        date_from = doc.date_from.strftime('%Y-%m-%d') if doc and doc.date_from else None
        date_to = doc.date_to.strftime('%Y-%m-%d') if doc and doc.date_to else fields.Date.today().strftime('%Y-%m-%d')
        target_move = doc.target_move if doc else 'posted'
        unit_name = doc.unit_name if doc and doc.unit_name else False
        comparison_type = doc.comparison_type if doc and doc.comparison_type else 'none'
        comparison_date = doc.comparison_date.strftime('%Y-%m-%d') if doc and doc.comparison_date else None

        bs_engine = self.env['sif.balance.sheet']
        bs_data = bs_engine.get_balance_sheet_data({
            'date_from': date_from,
            'date_to': date_to,
            'target_move': target_move,
            'unit_name': unit_name,
            'comparison_type': comparison_type,
            'comparison_date': comparison_date,
        })

        return {
            'doc_ids': docids,
            'doc_model': 'sif.balance.sheet.wizard',
            'docs': docs,
            'data': bs_data,
            'company': self.env.company,
            'date_to': date_to,
            'date_to_display': bs_data.get('date_to_display', '-'),
            'target_move': target_move,
            'format_rupiah': bs_engine._format_rupiah,
        }
