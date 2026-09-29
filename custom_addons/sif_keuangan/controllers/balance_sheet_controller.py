# -*- coding: utf-8 -*-
import io
import xlsxwriter
from odoo import http
from odoo.http import request


class BalanceSheetController(http.Controller):

    @http.route('/sif_keuangan/export_balance_sheet_xlsx', type='http', auth='user')
    def export_balance_sheet_xlsx(self, date_from=None, date_to=None, target_move='posted', unit_name=None, comparison_type='none', comparison_date=None, **kw):
        """
        Stream export Balance Sheet ke Excel (.xlsx) dengan dukungan komparasi periode dan filter unit kerja.
        """
        filters = {
            'date_from': date_from,
            'date_to': date_to,
            'target_move': target_move or 'posted',
            'unit_name': unit_name or False,
            'comparison_type': comparison_type or 'none',
            'comparison_date': comparison_date or False,
        }

        bs_engine = request.env['sif.balance.sheet']
        data = bs_engine.get_balance_sheet_data(filters)
        has_comp = data.get('has_comparison', False)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Balance Sheet')

        # Formats
        fmt_title = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#714B67'})
        fmt_subtitle = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#4A5568'})
        fmt_sec_header = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#714B67', 'font_color': '#FFFFFF', 'border': 1})
        fmt_subsec_header = workbook.add_format({'bold': True, 'bg_color': '#E2E8F0', 'font_color': '#1E293B', 'border': 1})
        fmt_cell = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        fmt_cell_bold = workbook.add_format({'bold': True, 'border': 1, 'valign': 'vcenter'})
        fmt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'})
        fmt_num_bold = workbook.add_format({'bold': True, 'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'})
        fmt_num_neg = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'font_color': '#DC2626'})
        fmt_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_center_bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_grand_total = workbook.add_format({'bold': True, 'bg_color': '#1E293B', 'font_color': '#FFFFFF', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        fmt_grand_label = workbook.add_format({'bold': True, 'bg_color': '#1E293B', 'font_color': '#FFFFFF', 'border': 1, 'align': 'left'})

        worksheet.set_column('A:A', 45)
        worksheet.set_column('B:B', 22)
        if has_comp:
            worksheet.set_column('C:C', 22)
            worksheet.set_column('D:D', 22)
            worksheet.set_column('E:E', 15)

        company_name = data.get('company_name', 'PT Konsulta Semen Gresik')
        worksheet.write(0, 0, company_name, fmt_title)
        sub_title = f"BALANCE SHEET (NERACA) — Periode: {data.get('date_from_display')} s/d {data.get('date_to_display')}"
        if has_comp:
            sub_title += f" vs {data.get('comparison_date_display')}"
        if data.get('unit_name'):
            sub_title += f" | Departemen: {data.get('unit_name')}"
        worksheet.write(1, 0, sub_title, fmt_subtitle)
        worksheet.write(2, 0, f"Status: {'Hanya Jurnal Disetujui (Posted)' if data.get('target_move') == 'posted' else 'Semua Jurnal'}", fmt_subtitle)

        # Header Columns
        row = 4
        worksheet.write(row, 0, "Komponen Neraca", fmt_subsec_header)
        worksheet.write(row, 1, f"Posisi {data.get('date_to_display')}", fmt_subsec_header)
        if has_comp:
            worksheet.write(row, 2, f"Posisi {data.get('comparison_date_display')}", fmt_subsec_header)
            worksheet.write(row, 3, "Variansi (Rp)", fmt_subsec_header)
            worksheet.write(row, 4, "% Perubahan", fmt_subsec_header)
        row += 1

        def write_row_data(r, label, cur_val, comp_val=0.0, diff_val=0.0, pct_str="", is_bold=False, is_sub=False):
            c_fmt = fmt_subsec_header if is_sub else (fmt_cell_bold if is_bold else fmt_cell)
            n_fmt = fmt_num_bold if is_bold or is_sub else fmt_num
            worksheet.write(r, 0, label, c_fmt)
            worksheet.write(r, 1, cur_val, n_fmt)
            if has_comp:
                worksheet.write(r, 2, comp_val, n_fmt)
                worksheet.write(r, 3, diff_val, n_fmt)
                worksheet.write(r, 4, pct_str, fmt_center_bold if is_bold else fmt_center)

        # 1. ASSETS
        assets = data['assets']
        worksheet.write(row, 0, assets['title'], fmt_sec_header)
        for c in range(1, 5 if has_comp else 2):
            worksheet.write(row, c, '', fmt_sec_header)
        row += 1

        # Current Assets
        ca = assets['current_assets']
        write_row_data(row, f"  {ca['title']}", ca['total'], ca.get('comp_total', 0.0), ca.get('diff_total', 0.0), ca.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        for sub_key in ['bank_and_cash', 'receivables', 'other_current_assets', 'prepayments']:
            sub = ca[sub_key]
            write_row_data(row, f"    {sub['title']}", sub['total'], sub.get('comp_total', 0.0), sub.get('diff_total', 0.0), sub.get('diff_percentage', ''), is_bold=True)
            row += 1
            for l in sub['lines']:
                write_row_data(row, f"      {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
                row += 1

        write_row_data(row, f"  Total {ca['title']}", ca['total'], ca.get('comp_total', 0.0), ca.get('diff_total', 0.0), ca.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        # Fixed Assets
        fa = assets['fixed_assets']
        write_row_data(row, f"  {fa['title']}", fa['total'], fa.get('comp_total', 0.0), fa.get('diff_total', 0.0), fa.get('diff_percentage', ''), is_bold=True)
        row += 1
        for l in fa['lines']:
            write_row_data(row, f"    {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
            row += 1

        # Non-Current Assets
        nca = assets['non_current_assets']
        write_row_data(row, f"  {nca['title']}", nca['total'], nca.get('comp_total', 0.0), nca.get('diff_total', 0.0), nca.get('diff_percentage', ''), is_bold=True)
        row += 1
        for l in nca['lines']:
            write_row_data(row, f"    {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
            row += 1

        write_row_data(row, f"Total {assets['title']}", assets['total'], assets.get('comp_total', 0.0), assets.get('diff_total', 0.0), assets.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 2

        # 2. LIABILITIES
        liab = data['liabilities']
        worksheet.write(row, 0, liab['title'], fmt_sec_header)
        for c in range(1, 5 if has_comp else 2):
            worksheet.write(row, c, '', fmt_sec_header)
        row += 1

        # Current Liabilities
        cl = liab['current_liabilities']
        write_row_data(row, f"  {cl['title']}", cl['total'], cl.get('comp_total', 0.0), cl.get('diff_total', 0.0), cl.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        for sub_key in ['general_current', 'credit_card', 'payables']:
            sub = cl[sub_key]
            write_row_data(row, f"    {sub['title']}", sub['total'], sub.get('comp_total', 0.0), sub.get('diff_total', 0.0), sub.get('diff_percentage', ''), is_bold=True)
            row += 1
            for l in sub['lines']:
                write_row_data(row, f"      {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
                row += 1

        write_row_data(row, f"  Total {cl['title']}", cl['total'], cl.get('comp_total', 0.0), cl.get('diff_total', 0.0), cl.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        # Non-Current Liabilities
        ncl = liab['non_current_liabilities']
        write_row_data(row, f"  {ncl['title']}", ncl['total'], ncl.get('comp_total', 0.0), ncl.get('diff_total', 0.0), ncl.get('diff_percentage', ''), is_bold=True)
        row += 1
        for l in ncl['lines']:
            write_row_data(row, f"    {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
            row += 1

        write_row_data(row, f"Total {liab['title']}", liab['total'], liab.get('comp_total', 0.0), liab.get('diff_total', 0.0), liab.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 2

        # 3. EQUITY
        eq = data['equity']
        worksheet.write(row, 0, eq['title'], fmt_sec_header)
        for c in range(1, 5 if has_comp else 2):
            worksheet.write(row, c, '', fmt_sec_header)
        row += 1

        # Direct Equity
        de = eq['direct_equity']
        write_row_data(row, f"  {de['title']}", de['total'], de.get('comp_total', 0.0), de.get('diff_total', 0.0), de.get('diff_percentage', ''), is_bold=True)
        row += 1
        for l in de['lines']:
            write_row_data(row, f"    {l['full_name']}", l['amount'], l.get('comp_amount', 0.0), l.get('diff_amount', 0.0), l.get('diff_percentage', ''))
            row += 1

        # Earnings
        earn = eq['earnings']
        write_row_data(row, f"  {earn['title']}", earn['total'], earn.get('comp_total', 0.0), earn.get('diff_total', 0.0), earn.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        cye = earn['current_year_earnings']
        write_row_data(row, f"    {cye['title']}", cye['total'], cye.get('comp_total', 0.0), cye.get('diff_total', 0.0), cye.get('diff_percentage', ''))
        row += 1

        pye = earn['previous_years_earnings']
        write_row_data(row, f"    {pye['title']}", pye['total'], pye.get('comp_total', 0.0), pye.get('diff_total', 0.0), pye.get('diff_percentage', ''))
        row += 1

        write_row_data(row, f"  Total {earn['title']}", earn['total'], earn.get('comp_total', 0.0), earn.get('diff_total', 0.0), earn.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 1

        write_row_data(row, f"Total {eq['title']}", eq['total'], eq.get('comp_total', 0.0), eq.get('diff_total', 0.0), eq.get('diff_percentage', ''), is_bold=True, is_sub=True)
        row += 2

        # SUMMARY
        sm = data['summary']
        worksheet.write(row, 0, "TOTAL LIABILITIES + EQUITY", fmt_grand_label)
        worksheet.write(row, 1, sm['total_liabilities_and_equity'], fmt_grand_total)
        if has_comp:
            worksheet.write(row, 2, sm.get('comp_total_liabilities_and_equity', 0.0), fmt_grand_total)
            worksheet.write(row, 3, sm.get('diff_liab_eq', 0.0), fmt_grand_total)
            worksheet.write(row, 4, '', fmt_grand_total)
        row += 1

        worksheet.write(row, 0, f"STATUS KESEIMBANGAN: {'BALANCE (Rp 0,00)' if sm['is_balanced'] else 'SELISIH: ' + sm['difference_formatted']}", fmt_grand_label)
        worksheet.write(row, 1, sm['difference'], fmt_grand_total)
        if has_comp:
            worksheet.write(row, 2, 0.0, fmt_grand_total)
            worksheet.write(row, 3, 0.0, fmt_grand_total)
            worksheet.write(row, 4, '', fmt_grand_total)

        workbook.close()
        output.seek(0)
        file_data = output.read()

        filename = f"Balance_Sheet_{data.get('date_to')}.xlsx"
        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    @http.route('/sif_keuangan/export_balance_sheet_pdf', type='http', auth='user')
    def export_balance_sheet_pdf(self, date_from=None, date_to=None, target_move='posted', unit_name=None, comparison_type='none', comparison_date=None, **kw):
        """
        Stream export Balance Sheet langsung ke berkas PDF.
        """
        wizard = request.env['sif.balance.sheet.wizard'].create({
            'date_from': date_from or False,
            'date_to': date_to or request.env['sif.balance.sheet']._default_date_to(),
            'target_move': target_move or 'posted',
            'unit_name': unit_name or False,
            'comparison_type': comparison_type or 'none',
            'comparison_date': comparison_date or False,
        })
        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'sif_keuangan.action_report_balance_sheet',
            [wizard.id]
        )
        filename = f"Balance_Sheet_{wizard.date_to}.pdf"
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
