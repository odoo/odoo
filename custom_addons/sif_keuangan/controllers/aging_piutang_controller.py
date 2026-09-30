# -*- coding: utf-8 -*-
import io
import datetime
import xlsxwriter
from odoo import http
from odoo.http import request


class AgingPiutangController(http.Controller):

    @http.route('/sif_keuangan/export_aging_piutang_xlsx', type='http', auth='user')
    def export_aging_piutang_xlsx(self, as_of_date=None, unit_name=None, partner_type='all', bucket='all', search=None, comparison_type='none', **kw):
        """
        Stream export Laporan Aging Piutang ke berkas Excel (.xlsx).
        Memuat 2 Sheet:
        1. Ringkasan Aging Mitra (14 Kolom Matriks Penuaan + Breakdown Kritis >90 Hari)
        2. Daftar Rincian Tagihan Nominatif (Daftar Seluruh Dokumen, NISN, Orang Tua, Kontak WA)
        """
        filters = {
            'as_of_date': as_of_date,
            'unit_name': unit_name or '',
            'partner_type': partner_type or 'all',
            'bucket': bucket or 'all',
            'search': search or '',
            'comparison_type': comparison_type or 'none',
        }

        aging_engine = request.env['sif.aging.piutang']
        data = aging_engine.get_aging_piutang_data(filters)
        totals = data.get('totals', {})
        partners = data.get('partners', [])
        details = data.get('details', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Formats
        fmt_title = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#714B67'})
        fmt_subtitle = workbook.add_format({'bold': True, 'font_size': 9.5, 'font_color': '#475569'})
        fmt_header = workbook.add_format({
            'bold': True, 'font_size': 9, 'bg_color': '#714B67', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        fmt_sub_header = workbook.add_format({
            'bold': True, 'font_size': 9, 'bg_color': '#991B1B', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        fmt_kpi_label = workbook.add_format({
            'bold': True, 'bg_color': '#F1F5F9', 'border': 1, 'font_size': 9, 'align': 'left'
        })
        fmt_kpi_val = workbook.add_format({
            'bold': True, 'bg_color': '#F8FAFC', 'border': 1, 'font_size': 9.5,
            'num_format': '#,##0.00', 'align': 'right'
        })
        fmt_cell = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 9})
        fmt_cell_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9})
        fmt_num = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'font_size': 9
        })
        fmt_num_bold = workbook.add_format({
            'bold': True, 'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'font_size': 9
        })
        fmt_num_danger = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter',
            'font_color': '#DC2626', 'font_size': 9
        })
        fmt_grand_total = workbook.add_format({
            'bold': True, 'bg_color': '#0F172A', 'font_color': '#FFFFFF',
            'num_format': '#,##0.00', 'border': 1, 'align': 'right', 'font_size': 9.5
        })
        fmt_grand_label = workbook.add_format({
            'bold': True, 'bg_color': '#0F172A', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'left', 'font_size': 9.5
        })

        # =========================================================================
        # SHEET 1: RINGKASAN AGING MITRA (13 KOLOM PIVOT)
        # =========================================================================
        ws1 = workbook.add_worksheet('Ringkasan Aging Mitra')
        ws1.set_column('A:A', 5)   # 1. No
        ws1.set_column('B:B', 32)  # 2. Nama Debitur
        ws1.set_column('C:C', 18)  # 3. Klasifikasi
        ws1.set_column('D:D', 24)  # 4. Unit Kerja
        ws1.set_column('E:E', 16)  # 5. Lancar
        ws1.set_column('F:F', 15)  # 6. 1-30 Hari
        ws1.set_column('G:G', 15)  # 7. 31-60 Hari
        ws1.set_column('H:H', 15)  # 8. 61-90 Hari
        ws1.set_column('I:I', 15)  # 9. 91-120 Hari
        ws1.set_column('J:J', 15)  # 10. 121-180 Hari
        ws1.set_column('K:K', 15)  # 11. 181-365 Hari
        ws1.set_column('L:L', 16)  # 12. > 365 Hari
        ws1.set_column('M:M', 18)  # 13. Total Piutang

        company_name = data.get('company_name', 'PT Konsulta Semen Gresik')
        ws1.write(0, 1, company_name, fmt_title)
        ws1.write(1, 1, f"LAPORAN AGING PIUTANG (ANALISIS UMUR PIUTANG) — Posisi Cut-off: {data.get('as_of_date_display')}", fmt_subtitle)
        
        info_sub = f"Unit: {unit_name or 'Semua Unit'} | Klasifikasi: {partner_type.upper()} | Filter: {bucket.upper()}"
        ws1.write(2, 1, info_sub, fmt_subtitle)

        # KPI Summary Boxes
        ws1.write(4, 1, "Total Piutang Aktif", fmt_kpi_label)
        ws1.write(4, 2, totals.get('total_receivables', 0.0), fmt_kpi_val)
        ws1.write(4, 4, "Piutang Lancar", fmt_kpi_label)
        ws1.write(4, 5, totals.get('total_current', 0.0), fmt_kpi_val)
        ws1.write(4, 7, "Total Menunggak", fmt_kpi_label)
        ws1.write(4, 8, totals.get('total_overdue', 0.0), fmt_kpi_val)
        ws1.write(4, 10, "Kritis (>90 Hari)", fmt_kpi_label)
        ws1.write(4, 11, totals.get('total_b_over_90', 0.0), fmt_kpi_val)

        # Table Header Row 1 (Categories)
        ws1.merge_range(6, 0, 7, 0, "NO", fmt_header)
        ws1.merge_range(6, 1, 7, 1, "NAMA DEBITUR / MITRA / SISWA", fmt_header)
        ws1.merge_range(6, 2, 7, 2, "KLASIFIKASI", fmt_header)
        ws1.merge_range(6, 3, 7, 3, "UNIT KERJA / SEKOLAH", fmt_header)
        ws1.merge_range(6, 4, 7, 4, "LANCAR (RP)", fmt_header)
        ws1.merge_range(6, 5, 6, 7, "MENUNGGAK REGULER (1 - 90 HARI)", fmt_header)
        ws1.write(7, 5, "1 - 30 HARI", fmt_header)
        ws1.write(7, 6, "31 - 60 HARI", fmt_header)
        ws1.write(7, 7, "61 - 90 HARI", fmt_header)
        ws1.merge_range(6, 8, 6, 11, "BREAKDOWN MENUNGGAK KRITIS (> 90 HARI)", fmt_sub_header)
        ws1.write(7, 8, "91 - 120 HARI", fmt_sub_header)
        ws1.write(7, 9, "121 - 180 HARI", fmt_sub_header)
        ws1.write(7, 10, "181 - 365 HARI", fmt_sub_header)
        ws1.write(7, 11, "> 365 HARI", fmt_sub_header)
        ws1.merge_range(6, 12, 7, 12, "TOTAL PIUTANG (RP)", fmt_header)

        row = 8
        no = 1
        for p in partners:
            ws1.write(row, 0, no, fmt_cell_center)
            ws1.write(row, 1, p['partner_name'], fmt_cell)
            ws1.write(row, 2, p['partner_type_label'], fmt_cell)
            ws1.write(row, 3, p['unit_name'], fmt_cell)
            ws1.write(row, 4, p['current'], fmt_num)
            ws1.write(row, 5, p['b_1_30'], fmt_num)
            ws1.write(row, 6, p['b_31_60'], fmt_num)
            ws1.write(row, 7, p['b_61_90'], fmt_num)
            ws1.write(row, 8, p['b_91_120'], fmt_num_danger if p['b_91_120'] > 0 else fmt_num)
            ws1.write(row, 9, p['b_121_180'], fmt_num_danger if p['b_121_180'] > 0 else fmt_num)
            ws1.write(row, 10, p['b_181_365'], fmt_num_danger if p['b_181_365'] > 0 else fmt_num)
            ws1.write(row, 11, p['b_over_365'], fmt_num_danger if p['b_over_365'] > 0 else fmt_num)
            ws1.write(row, 12, p['total'], fmt_num_bold)
            row += 1
            no += 1

        # Grand Total Row
        ws1.merge_range(row, 0, row, 3, "TOTAL KESELURUHAN", fmt_grand_label)
        ws1.write(row, 4, totals.get('total_current', 0.0), fmt_grand_total)
        ws1.write(row, 5, totals.get('total_b_1_30', 0.0), fmt_grand_total)
        ws1.write(row, 6, totals.get('total_b_31_60', 0.0), fmt_grand_total)
        ws1.write(row, 7, totals.get('total_b_61_90', 0.0), fmt_grand_total)
        ws1.write(row, 8, totals.get('total_b_91_120', 0.0), fmt_grand_total)
        ws1.write(row, 9, totals.get('total_b_121_180', 0.0), fmt_grand_total)
        ws1.write(row, 10, totals.get('total_b_181_365', 0.0), fmt_grand_total)
        ws1.write(row, 11, totals.get('total_b_over_365', 0.0), fmt_grand_total)
        ws1.write(row, 12, totals.get('total_receivables', 0.0), fmt_grand_total)

        # =========================================================================
        # SHEET 2: DAFTAR NOMINATIF RINCIAN DOKUMEN
        # =========================================================================
        ws2 = workbook.add_worksheet('Daftar Rincian Tagihan')
        ws2.set_column('A:A', 5)   # No
        ws2.set_column('B:B', 18)  # No Dokumen
        ws2.set_column('C:C', 28)  # Debitur
        ws2.set_column('D:D', 15)  # NISN/ID
        ws2.set_column('E:E', 22)  # Orang Tua / Wali
        ws2.set_column('F:F', 24)  # Unit Kerja
        ws2.set_column('G:G', 20)  # Keterangan / Periode
        ws2.set_column('H:H', 13)  # Tgl Terbit
        ws2.set_column('I:I', 13)  # Jatuh Tempo
        ws2.set_column('J:J', 14)  # Hari Terlambat
        ws2.set_column('K:K', 24)  # Kategori Umur
        ws2.set_column('L:L', 18)  # Nominal (Rp)

        ws2.write(0, 1, company_name, fmt_title)
        ws2.write(1, 1, f"DAFTAR NOMINATIF TAGIHAN PIUTANG — Posisi Cut-off: {data.get('as_of_date_display')}", fmt_subtitle)

        r2 = 3
        headers_ws2 = [
            "NO", "NO. DOKUMEN", "NAMA DEBITUR / SISWA", "NISN / ID", "ORANG TUA / WALI",
            "UNIT KERJA / SEKOLAH", "KETERANGAN", "TGL TERBIT",
            "JATUH TEMPO", "HARI TERLAMBAT", "KATEGORI UMUR", "NOMINAL (RP)"
        ]
        for col_idx, h_text in enumerate(headers_ws2):
            ws2.write(r2, col_idx, h_text, fmt_header)
        r2 += 1

        no2 = 1
        for d in details:
            ws2.write(r2, 0, no2, fmt_cell_center)
            ws2.write(r2, 1, d['doc_name'], fmt_cell)
            ws2.write(r2, 2, d['partner_name'], fmt_cell)
            ws2.write(r2, 3, d['student_id_number'] or '-', fmt_cell_center)
            ws2.write(r2, 4, d['parent_name'] or '-', fmt_cell)
            ws2.write(r2, 5, d['unit_name'], fmt_cell)
            ws2.write(r2, 6, d['description'] or '-', fmt_cell)
            ws2.write(r2, 7, d['bill_date_display'], fmt_cell_center)
            ws2.write(r2, 8, d['due_date_display'], fmt_cell_center)
            ws2.write(r2, 9, f"{d['overdue_days']} Hari" if d['overdue_days'] > 0 else "Lancar", fmt_cell_center)
            ws2.write(r2, 10, d['bucket_label'], fmt_cell)
            ws2.write(r2, 11, d['amount'], fmt_num_bold)
            r2 += 1
            no2 += 1

        ws2.merge_range(r2, 0, r2, 10, "TOTAL NOMINATIF", fmt_grand_label)
        ws2.write(r2, 11, totals.get('total_receivables', 0.0), fmt_grand_total)

        workbook.close()
        output.seek(0)

        filename = f"Aging_Piutang_{data.get('as_of_date')}.xlsx"
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )

    @http.route('/sif_keuangan/export_aging_piutang_pdf', type='http', auth='user')
    def export_aging_piutang_pdf(self, as_of_date=None, unit_name=None, partner_type='all', bucket='all', search=None, comparison_type='none', **kw):
        """
        Stream export Laporan Aging Piutang langsung ke berkas PDF (14 Kolom Landscape).
        """
        wizard_vals = {
            'as_of_date': as_of_date or request.env['sif.aging.piutang']._default_as_of_date(),
            'unit_name': unit_name or '',
            'partner_type': partner_type or 'all',
            'bucket': bucket or 'all',
        }

        wizard = request.env['sif.aging.piutang.wizard'].create(wizard_vals)
        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'sif_keuangan.action_report_aging_piutang',
            [wizard.id],
            data={
                'as_of_date': as_of_date,
                'unit_name': unit_name,
                'partner_type': partner_type,
                'bucket': bucket,
                'search': search,
                'comparison_type': comparison_type,
            }
        )
        filename = f"Aging_Piutang_{wizard.as_of_date}.pdf"
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
