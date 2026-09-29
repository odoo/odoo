# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime
from dateutil.relativedelta import relativedelta


class SifAgingPiutang(models.AbstractModel):
    _name = 'sif.aging.piutang'
    _description = 'Engine Laporan Aging Piutang (Accounts Receivable Aging)'

    @api.model
    def _default_as_of_date(self):
        return fields.Date.context_today(self)

    @api.model
    def get_aging_piutang_data(self, filters=None):
        """
        Engine penghitung Laporan Aging Piutang (Umur Piutang).
        Mendukung:
        - Cut-off / As-of Date dinamis (untuk rekonsiliasi & restatement saldo lampau)
        - Breakdown mendalam piutang kritis >90 hari (91-120, 121-180, 181-365, >365 hari)
        - Dual-Source Sync: Tagihan Pendidikan (education.bill) & Buku Besar Keuangan (sif.jurnal.line 113xxx/12xxx/21xxx)
        - Deduplikasi transaksi ganda & rekonsiliasi saldo FIFO per debitur
        - Filter Unit Kerja / Sekolah / Kampus
        - Filter Klasifikasi Mitra (Siswa/Wali, Customer, Distributor, Vendor/Ekspeditur, Lainnya)
        - Filter Status Bucket & Pencarian Realtime
        - Komparasi periode sebelumnya (MoM / YoY / Kustom)
        """
        filters = filters or {}
        today = fields.Date.context_today(self)
        lang = filters.get('lang') or self.env.user.lang or self.env.context.get('lang', 'id_ID')
        is_id = str(lang).lower().startswith('id')

        # 1. Parameter Cut-off Date (As-of Date)
        as_of_date_str = filters.get('as_of_date') or filters.get('date_to')
        if not as_of_date_str:
            as_of_date_dt = today
            as_of_date_str = today.strftime('%Y-%m-%d')
        else:
            if isinstance(as_of_date_str, str):
                as_of_date_dt = datetime.datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
            else:
                as_of_date_dt = as_of_date_str
                as_of_date_str = as_of_date_dt.strftime('%Y-%m-%d')

        target_move = filters.get('target_move', 'posted')
        unit_name_filter = (filters.get('unit_name') or '').strip()
        partner_type_filter = (filters.get('partner_type') or 'all').strip()
        bucket_filter = (filters.get('bucket') or 'all').strip()
        search_query = (filters.get('search') or '').strip().lower()
        comparison_type = filters.get('comparison_type', 'none')

        # Hitung data snapshot utama
        snap_main = self._calculate_aging_snapshot(as_of_date_dt, target_move, unit_name_filter, partner_type_filter)

        # Hitung data snapshot komparasi (jika aktif)
        comp_date_dt = self._get_comparison_date(as_of_date_dt, comparison_type, filters.get('comparison_date'))
        has_comparison = bool(comp_date_dt)
        snap_comp = self._calculate_aging_snapshot(comp_date_dt, target_move, unit_name_filter, partner_type_filter) if has_comparison else False

        # Filter lines & partners berdasarkan search_query dan bucket_filter
        filtered_partners = []
        filtered_details = []

        for p in snap_main['partners']:
            # Search match di level partner
            match_search = not search_query or (
                search_query in p['partner_name'].lower() or
                search_query in (p.get('unit_name') or '').lower() or
                search_query in (p.get('phone') or '').lower() or
                search_query in (p.get('student_id_number') or '').lower() or
                search_query in (p.get('parent_name') or '').lower()
            )

            # Match bucket filter
            match_bucket = True
            if bucket_filter == 'current' and p['current'] <= 0:
                match_bucket = False
            elif bucket_filter == '1_30' and p['b_1_30'] <= 0:
                match_bucket = False
            elif bucket_filter == '31_60' and p['b_31_60'] <= 0:
                match_bucket = False
            elif bucket_filter == '61_90' and p['b_61_90'] <= 0:
                match_bucket = False
            elif bucket_filter == 'over_90' and p['b_over_90'] <= 0:
                match_bucket = False
            elif bucket_filter == '91_120' and p['b_91_120'] <= 0:
                match_bucket = False
            elif bucket_filter == '121_180' and p['b_121_180'] <= 0:
                match_bucket = False
            elif bucket_filter == '181_365' and p['b_181_365'] <= 0:
                match_bucket = False
            elif bucket_filter == 'over_365' and p['b_over_365'] <= 0:
                match_bucket = False

            if match_search and match_bucket and p['total'] > 0:
                filtered_partners.append(p)

        for d in snap_main['details']:
            match_search = not search_query or (
                search_query in d['doc_name'].lower() or
                search_query in d['partner_name'].lower() or
                search_query in (d.get('unit_name') or '').lower() or
                search_query in (d.get('description') or '').lower() or
                search_query in (d.get('student_id_number') or '').lower() or
                search_query in (d.get('parent_name') or '').lower()
            )
            match_bucket = True
            if bucket_filter != 'all':
                if bucket_filter == 'over_90':
                    match_bucket = d['bucket_code'] in ('91_120', '121_180', '181_365', 'over_365')
                else:
                    match_bucket = d['bucket_code'] == bucket_filter

            if match_search and match_bucket and d['amount'] > 0:
                filtered_details.append(d)

        # Hitung Ringkasan & Komparasi
        totals = snap_main['totals']
        comp_totals = snap_comp['totals'] if snap_comp else False

        comparison_summary = False
        if has_comparison and comp_totals:
            diff_total = totals['total_receivables'] - comp_totals['total_receivables']
            growth_total = (diff_total / comp_totals['total_receivables'] * 100) if comp_totals['total_receivables'] else 0.0
            diff_overdue = totals['total_overdue'] - comp_totals['total_overdue']
            growth_overdue = (diff_overdue / comp_totals['total_overdue'] * 100) if comp_totals['total_overdue'] else 0.0
            diff_over_90 = totals['total_b_over_90'] - comp_totals['total_b_over_90']
            growth_over_90 = (diff_over_90 / comp_totals['total_b_over_90'] * 100) if comp_totals['total_b_over_90'] else 0.0

            comparison_summary = {
                'comp_date': comp_date_dt.strftime('%Y-%m-%d'),
                'comp_date_display': comp_date_dt.strftime('%d/%m/%Y'),
                'comp_total_receivables': comp_totals['total_receivables'],
                'diff_total': diff_total,
                'growth_total': round(growth_total, 2),
                'comp_total_overdue': comp_totals['total_overdue'],
                'diff_overdue': diff_overdue,
                'growth_overdue': round(growth_overdue, 2),
                'comp_total_over_90': comp_totals['total_over_90'],
                'diff_over_90': diff_over_90,
                'growth_over_90': round(growth_over_90, 2),
            }

        # Ambil list unit kerja unik untuk dropdown filter
        units_list = snap_main['available_units']

        return {
            'as_of_date': as_of_date_str,
            'as_of_date_display': as_of_date_dt.strftime('%d/%m/%Y'),
            'company_name': self.env.company.name,
            'currency_symbol': 'Rp',
            'totals': totals,
            'comparison': comparison_summary,
            'has_comparison': has_comparison,
            'partners': filtered_partners,
            'details': filtered_details,
            'available_units': units_list,
            'partner_counts': len(filtered_partners),
            'detail_counts': len(filtered_details),
        }

    def _get_comparison_date(self, as_of_date, comparison_type, custom_date):
        if comparison_type == 'previous_month':
            return as_of_date - relativedelta(months=1)
        elif comparison_type == 'previous_year':
            return as_of_date - relativedelta(years=1)
        elif comparison_type == 'custom' and custom_date:
            try:
                if isinstance(custom_date, str):
                    return datetime.datetime.strptime(custom_date, '%Y-%m-%d').date()
                return custom_date
            except Exception:
                return False
        return False

    def _calculate_aging_snapshot(self, as_of_date, target_move, unit_name_filter, partner_type_filter):
        """
        Mengalkulasi data snapshot piutang pada tanggal tertentu (as_of_date).
        Dual-Source Sync:
        1. education.bill (unpaid / waiting)
        2. sif.jurnal.line (reconciled FIFO debits vs credits per partner/account)
        Deduplikasi jika jurnal mencatat bill yang sama.
        """
        all_details = []
        available_units_set = set()
        recorded_doc_keys = set()

        # -------------------------------------------------------------
        # 1. AMBIL DATA DARI MODUL TAGIHAN PENDIDIKAN (education.bill)
        # -------------------------------------------------------------
        if 'education.bill' in self.env:
            bill_domain = [
                ('bill_date', '<=', as_of_date),
                ('state', 'not in', ('verified', 'paid', 'cancelled', 'cancel')),
            ]
            if unit_name_filter:
                bill_domain.append(('school_id.name', '=', unit_name_filter))

            bills = self.env['education.bill'].search(bill_domain, order='due_date asc, id asc')

            for b in bills:
                sch_name = b.school_id.name if hasattr(b, 'school_id') and b.school_id else 'Sekolah / Kampus'
                available_units_set.add(sch_name)

                if partner_type_filter not in ('all', 'student'):
                    continue

                due_date = b.due_date or b.bill_date or as_of_date
                overdue_days = (as_of_date - due_date).days
                
                # Sisa tagihan
                amount = getattr(b, 'residual', None) or getattr(b, 'amount_unpaid', None) or b.amount or 0.0
                if amount <= 0:
                    continue

                bucket_code, bucket_label, risk_level = self._classify_bucket(overdue_days)

                parent_name = b.parent_id.name if hasattr(b, 'parent_id') and b.parent_id else '-'
                parent_phone = '-'
                if hasattr(b, 'parent_id') and b.parent_id:
                    parent_phone = b.parent_id.phone or getattr(b.parent_id, 'whatsapp', None) or getattr(b.parent_id, 'mobile', None) or '-'

                student_id = b.student_id.id if hasattr(b, 'student_id') and b.student_id else False
                student_name = b.student_id.name if hasattr(b, 'student_id') and b.student_id else 'Siswa Tanpa Nama'
                student_nisn = getattr(b.student_id, 'student_id_number', None) or getattr(b.student_id, 'nisn', None) or '-'

                class_name = b.class_id.name if hasattr(b, 'class_id') and b.class_id else '-'
                period_lbl = getattr(b, 'period_label', None) or '-'

                # Catat key untuk mencegah double-count di jurnal
                if b.name:
                    recorded_doc_keys.add(b.name.strip().upper())

                all_details.append({
                    'id': f"bill_{b.id}",
                    'source': 'education_bill',
                    'doc_id': b.id,
                    'doc_name': b.name or f"BILL-{b.id}",
                    'partner_id': student_id,
                    'partner_name': student_name,
                    'student_id_number': student_nisn,
                    'parent_name': parent_name,
                    'phone': parent_phone,
                    'partner_type': 'student',
                    'partner_type_label': 'Siswa / Mahasiswa',
                    'unit_name': sch_name,
                    'class_name': class_name,
                    'period_label': period_lbl,
                    'bill_date': b.bill_date.strftime('%Y-%m-%d') if b.bill_date else '-',
                    'bill_date_display': b.bill_date.strftime('%d/%m/%Y') if b.bill_date else '-',
                    'due_date': due_date.strftime('%Y-%m-%d'),
                    'due_date_display': due_date.strftime('%d/%m/%Y'),
                    'overdue_days': overdue_days,
                    'bucket_code': bucket_code,
                    'bucket_label': bucket_label,
                    'risk_level': risk_level,
                    'amount': amount,
                    'state': b.state,
                    'state_label': dict(b._fields['state'].selection).get(b.state, b.state) if 'state' in b._fields and hasattr(b._fields['state'], 'selection') else b.state,
                    'description': f"{period_lbl} - {class_name}" if class_name != '-' else period_lbl,
                })

        # -------------------------------------------------------------
        # 2. AMBIL DATA DARI BUKU BESAR KEUANGAN (sif.jurnal.line)
        # -------------------------------------------------------------
        if 'sif.jurnal.line' in self.env:
            # Cari akun-akun piutang: kode 113xxx, 12xxx, 21xxx atau bertipe asset dengan nama piutang
            piutang_accounts = self.env['sif.coa'].search([
                ('account_type', '=', 'asset'),
                ('name', 'not ilike', 'penyisihan'),
                '|', '|', '|',
                ('code', '=like', '113%'),
                ('code', '=like', '12%'),
                ('code', '=like', '21%'),
                ('name', 'ilike', 'piutang')
            ])
            piutang_acc_ids = piutang_accounts.ids

            if piutang_acc_ids:
                jl_domain = [
                    ('account_id', 'in', piutang_acc_ids),
                    ('date', '<=', as_of_date),
                ]
                if target_move == 'posted':
                    jl_domain.append(('state', '=', 'posted'))
                if unit_name_filter:
                    jl_domain.append(('entry_id.unit_name', '=', unit_name_filter))

                lines = self.env['sif.jurnal.line'].search(jl_domain, order='date asc, id asc')

                # Kelompokkan mutasi per partner + unit kerja untuk rekonsiliasi FIFO
                partner_unit_lines = {}
                for line in lines:
                    u_name = line.entry_id.unit_name or 'KANTOR'
                    available_units_set.add(u_name)

                    p_id = line.partner_id.id if line.partner_id else 0
                    p_name = line.partner_id.name if line.partner_id else (line.name or 'Pelanggan Umum / Non-Partner')
                    pu_key = (p_id, p_name, u_name)

                    if pu_key not in partner_unit_lines:
                        partner_unit_lines[pu_key] = {
                            'partner': line.partner_id,
                            'partner_name': p_name,
                            'unit_name': u_name,
                            'debit_lines': [],
                            'total_credit': 0.0,
                        }

                    d_val = line.debit or 0.0
                    c_val = line.credit or 0.0

                    if d_val > 0:
                        partner_unit_lines[pu_key]['debit_lines'].append(line)
                    if c_val > 0:
                        partner_unit_lines[pu_key]['total_credit'] += c_val

                # Alokasi FIFO: Kredit melunasi Debet tertua
                for pu_key, pu_data in partner_unit_lines.items():
                    partner = pu_data['partner']
                    p_name = pu_data['partner_name']
                    u_name = pu_data['unit_name']
                    remaining_credit = pu_data['total_credit']

                    p_type = 'other'
                    p_type_label = 'Lainnya'

                    if partner:
                        p_name_lower = (partner.name or '').lower()
                        cat_names = [c.name.lower() for c in partner.category_id] if hasattr(partner, 'category_id') and partner.category_id else []
                        if 'distributor' in p_name_lower or any('distributor' in c for c in cat_names):
                            p_type = 'distributor'
                            p_type_label = 'Distributor'
                        elif 'vendor' in p_name_lower or 'supplier' in p_name_lower or 'ekspedisi' in p_name_lower or any('vendor' in c or 'ekspedisi' in c for c in cat_names):
                            p_type = 'vendor'
                            p_type_label = 'Vendor / Ekspedisi'
                        elif getattr(partner, 'customer_rank', 0) > 0 or not getattr(partner, 'supplier_rank', 0):
                            p_type = 'customer'
                            p_type_label = 'Pelanggan Umum'

                    if partner_type_filter != 'all' and partner_type_filter != p_type:
                        continue

                    # Proses baris debet secara urut waktu (FIFO)
                    for d_line in pu_data['debit_lines']:
                        # Cegah duplikasi jika dokumen jurnal ini berasal dari education.bill yang sudah tercatat
                        doc_ref_upper = (d_line.entry_id.ref or '').strip().upper()
                        doc_kwit_upper = (d_line.entry_id.kwitansi_ref or '').strip().upper()
                        doc_line_upper = (d_line.name or '').strip().upper()

                        if recorded_doc_keys and (
                            doc_ref_upper in recorded_doc_keys or
                            doc_kwit_upper in recorded_doc_keys or
                            doc_line_upper in recorded_doc_keys
                        ):
                            continue

                        line_debit = d_line.debit or 0.0
                        if remaining_credit >= line_debit:
                            remaining_credit -= line_debit
                            continue
                        elif remaining_credit > 0:
                            open_amount = line_debit - remaining_credit
                            remaining_credit = 0.0
                        else:
                            open_amount = line_debit

                        if open_amount <= 0:
                            continue

                        doc_date = d_line.date
                        due_date = doc_date + datetime.timedelta(days=30)
                        overdue_days = (as_of_date - due_date).days

                        bucket_code, bucket_label, risk_level = self._classify_bucket(overdue_days)

                        phone_val = '-'
                        if partner:
                            phone_val = partner.phone or getattr(partner, 'mobile', None) or getattr(partner, 'whatsapp', None) or '-'

                        all_details.append({
                            'id': f"jl_{d_line.id}",
                            'source': 'sif_jurnal',
                            'doc_id': d_line.entry_id.id,
                            'doc_name': d_line.entry_id.name or 'JRNL',
                            'partner_id': partner.id if partner else False,
                            'partner_name': p_name,
                            'student_id_number': '-',
                            'parent_name': '-',
                            'phone': phone_val,
                            'partner_type': p_type,
                            'partner_type_label': p_type_label,
                            'unit_name': u_name,
                            'class_name': '-',
                            'period_label': d_line.account_id.display_name or d_line.account_id.name or '-',
                            'bill_date': doc_date.strftime('%Y-%m-%d'),
                            'bill_date_display': doc_date.strftime('%d/%m/%Y'),
                            'due_date': due_date.strftime('%Y-%m-%d'),
                            'due_date_display': due_date.strftime('%d/%m/%Y'),
                            'overdue_days': overdue_days,
                            'bucket_code': bucket_code,
                            'bucket_label': bucket_label,
                            'risk_level': risk_level,
                            'amount': open_amount,
                            'state': d_line.state,
                            'state_label': 'Posted' if d_line.state == 'posted' else 'Draft',
                            'description': d_line.name or d_line.entry_id.ref or 'Piutang Usaha',
                        })

        # -------------------------------------------------------------
        # 3. AGREGASI DATA PER PARTNER (PIVOT MATRIX)
        # -------------------------------------------------------------
        partners_map = {}
        totals = {
            'total_receivables': 0.0,
            'total_current': 0.0,
            'total_overdue': 0.0,
            'total_b_1_30': 0.0,
            'total_b_31_60': 0.0,
            'total_b_61_90': 0.0,
            'total_b_over_90': 0.0,
            'total_b_91_120': 0.0,
            'total_b_121_180': 0.0,
            'total_b_181_365': 0.0,
            'total_b_over_365': 0.0,
            'doc_count': len(all_details),
            'partner_count': 0,
        }

        for item in all_details:
            amt = item['amount']
            b_code = item['bucket_code']
            p_key = f"{item['partner_type']}_{item['partner_name']}_{item['unit_name']}"

            if p_key not in partners_map:
                partners_map[p_key] = {
                    'partner_key': p_key,
                    'partner_id': item['partner_id'],
                    'partner_name': item['partner_name'],
                    'partner_type': item['partner_type'],
                    'partner_type_label': item['partner_type_label'],
                    'unit_name': item['unit_name'],
                    'phone': item['phone'],
                    'student_id_number': item['student_id_number'],
                    'parent_name': item['parent_name'],
                    'current': 0.0,
                    'b_1_30': 0.0,
                    'b_31_60': 0.0,
                    'b_61_90': 0.0,
                    'b_over_90': 0.0,
                    'b_91_120': 0.0,
                    'b_121_180': 0.0,
                    'b_181_365': 0.0,
                    'b_over_365': 0.0,
                    'total': 0.0,
                    'doc_count': 0,
                    'max_overdue_days': 0,
                }

            p_entry = partners_map[p_key]
            p_entry['doc_count'] += 1
            p_entry['total'] += amt
            if item['overdue_days'] > p_entry['max_overdue_days']:
                p_entry['max_overdue_days'] = item['overdue_days']

            # Tambahkan ke bucket partner & totals
            if b_code == 'current':
                p_entry['current'] += amt
                totals['total_current'] += amt
            else:
                totals['total_overdue'] += amt
                if b_code == '1_30':
                    p_entry['b_1_30'] += amt
                    totals['total_b_1_30'] += amt
                elif b_code == '31_60':
                    p_entry['b_31_60'] += amt
                    totals['total_b_31_60'] += amt
                elif b_code == '61_90':
                    p_entry['b_61_90'] += amt
                    totals['total_b_61_90'] += amt
                elif b_code == '91_120':
                    p_entry['b_over_90'] += amt
                    p_entry['b_91_120'] += amt
                    totals['total_b_over_90'] += amt
                    totals['total_b_91_120'] += amt
                elif b_code == '121_180':
                    p_entry['b_over_90'] += amt
                    p_entry['b_121_180'] += amt
                    totals['total_b_over_90'] += amt
                    totals['total_b_121_180'] += amt
                elif b_code == '181_365':
                    p_entry['b_over_90'] += amt
                    p_entry['b_181_365'] += amt
                    totals['total_b_over_90'] += amt
                    totals['total_b_181_365'] += amt
                elif b_code == 'over_365':
                    p_entry['b_over_90'] += amt
                    p_entry['b_over_365'] += amt
                    totals['total_b_over_90'] += amt
                    totals['total_b_over_365'] += amt

            totals['total_receivables'] += amt

        partner_list = list(partners_map.values())
        partner_list = sorted(partner_list, key=lambda x: x['total'], reverse=True)
        totals['partner_count'] = len(partner_list)

        # Hitung rasio
        tot_rec = totals['total_receivables']
        totals['current_ratio'] = round((totals['total_current'] / tot_rec * 100), 1) if tot_rec > 0 else 0.0
        totals['overdue_ratio'] = round((totals['total_overdue'] / tot_rec * 100), 1) if tot_rec > 0 else 0.0
        totals['critical_ratio'] = round((totals['total_b_over_90'] / tot_rec * 100), 1) if tot_rec > 0 else 0.0

        sorted_units = sorted(list(available_units_set))

        return {
            'as_of_date': as_of_date,
            'totals': totals,
            'partners': partner_list,
            'details': all_details,
            'available_units': sorted_units,
        }

    def _classify_bucket(self, overdue_days):
        """
        Klasifikasi umur piutang ke dalam bucket standar & breakdown kritis.
        """
        if overdue_days <= 0:
            return 'current', 'Belum Jatuh Tempo (Lancar)', 'success'
        elif 1 <= overdue_days <= 30:
            return '1_30', '1 - 30 Hari (Pengingat Awal)', 'info'
        elif 31 <= overdue_days <= 60:
            return '31_60', '31 - 60 Hari (Penagihan Reguler)', 'warning'
        elif 61 <= overdue_days <= 90:
            return '61_90', '61 - 90 Hari (Surat Peringatan 1)', 'danger-light'
        elif 91 <= overdue_days <= 120:
            return '91_120', '91 - 120 Hari (SP-2 / Panggilan)', 'danger'
        elif 121 <= overdue_days <= 180:
            return '121_180', '121 - 180 Hari (SP-3 / Blokir Layanan)', 'danger'
        elif 181 <= overdue_days <= 365:
            return '181_365', '181 - 365 Hari (Piutang Diragukan)', 'danger-dark'
        else:
            return 'over_365', '> 365 Hari / > 1 Thn (Piutang Macet / Write-off)', 'danger-dark'


class SifAgingPiutangWizard(models.TransientModel):
    _name = 'sif.aging.piutang.wizard'
    _description = 'Wizard Filter & Ekspor Aging Piutang'

    as_of_date = fields.Date(
        string='Per Tanggal (As-of Date)',
        default=fields.Date.context_today,
        required=True,
        help='Tanggal cut-off analisis umur piutang.'
    )
    unit_name = fields.Char(
        string='Unit Kerja / Sekolah'
    )
    partner_type = fields.Selection([
        ('all', 'Semua Mitra & Siswa'),
        ('student', 'Siswa / Mahasiswa (Tagihan Pendidikan)'),
        ('customer', 'Pelanggan Umum'),
        ('distributor', 'Distributor'),
        ('vendor', 'Vendor / Ekspedisi'),
        ('other', 'Lainnya'),
    ], string='Klasifikasi Mitra', default='all', required=True)

    bucket = fields.Selection([
        ('all', 'Semua Umur Piutang'),
        ('current', 'Hanya Lancar (Belum Jatuh Tempo)'),
        ('over_90', 'Hanya Kritis (> 90 Hari)'),
    ], string='Filter Umur', default='all', required=True)

    def action_open_client_action(self):
        """Buka full-page client action Aging Piutang"""
        return {
            'type': 'ir.actions.client',
            'tag': 'sif_keuangan.aging_piutang',
            'name': _('Aging Piutang (Umur Piutang)'),
            'target': 'current',
            'params': {
                'as_of_date': self.as_of_date.strftime('%Y-%m-%d') if self.as_of_date else False,
                'unit_name': self.unit_name or '',
                'partner_type': self.partner_type or 'all',
                'bucket': self.bucket or 'all',
            }
        }


class ReportSifAgingPiutangDocument(models.AbstractModel):
    _name = 'report.sif_keuangan.report_aging_piutang_document'
    _description = 'Parser Laporan PDF Aging Piutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        as_of_date_val = data.get('as_of_date')
        unit_name_val = data.get('unit_name', '')
        partner_type_val = data.get('partner_type', 'all')
        bucket_val = data.get('bucket', 'all')
        search_val = data.get('search', '')
        comparison_type_val = data.get('comparison_type', 'none')

        if docids and not data:
            wizard = self.env['sif.aging.piutang.wizard'].browse(docids[0])
            if wizard.exists():
                as_of_date_val = wizard.as_of_date.strftime('%Y-%m-%d') if wizard.as_of_date else None
                unit_name_val = wizard.unit_name or ''
                partner_type_val = wizard.partner_type or 'all'
                bucket_val = wizard.bucket or 'all'

        if not as_of_date_val:
            as_of_date_val = fields.Date.context_today(self).strftime('%Y-%m-%d')

        aging_engine = self.env['sif.aging.piutang']
        report_data = aging_engine.get_aging_piutang_data({
            'as_of_date': as_of_date_val,
            'unit_name': unit_name_val,
            'partner_type': partner_type_val,
            'bucket': bucket_val,
            'search': search_val,
            'comparison_type': comparison_type_val,
        })

        def format_rp(val):
            if val is None:
                return "0,00"
            num = float(val)
            is_neg = num < 0
            formatted = f"{abs(num):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"-{formatted}" if is_neg else formatted

        return {
            'doc_ids': docids or [1],
            'doc_model': 'sif.aging.piutang',
            'docs': [self.env.company],
            'company': self.env.company,
            'data': report_data,
            'as_of_date_display': report_data.get('as_of_date_display'),
            'totals': report_data.get('totals', {}),
            'partners': report_data.get('partners', []),
            'details': report_data.get('details', []),
            'format_rp': format_rp,
            'datetime': datetime,
        }
