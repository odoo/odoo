# -*- coding: utf-8 -*-
import io
import xlsxwriter
from odoo import http
from odoo.http import request


class ProfitLossController(http.Controller):

    @http.route('/sif_keuangan/export_profit_loss_xlsx', type='http', auth='user')
    def export_profit_loss_xlsx(self, date_from=None, date_to=None, target_move='posted', unit_name=None, comparison_type='none', custom_comp_date_from=None, custom_comp_date_to=None, **kw):
        """
        Stream export Profit and Loss (Laba Rugi) ke Excel (.xlsx).
        """
        filters = {
            'date_from': date_from,
            'date_to': date_to,
            'target_move': target_move or 'posted',
            'unit_name': unit_name or False,
            'comparison_type': comparison_type or 'none',
            'custom_comp_date_from': custom_comp_date_from or False,
            'custom_comp_date_to': custom_comp_date_to or False,
        }

        pl_engine = request.env['sif.profit.loss']
        data = pl_engine.get_profit_loss_data(filters)
        has_comp = data.get('has_comparison', False)
        sections = data.get('sections', {})

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Profit and Loss')

        # Formats
        fmt_title = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#714B67'})
        fmt_subtitle = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#4A5568'})
        fmt_sec_header = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#714B67', 'font_color': '#FFFFFF', 'border': 1})
        fmt_subsec_header = workbook.add_format({'bold': True, 'bg_color': '#E2E8F0', 'font_color': '#1E293B', 'border': 1})
        fmt_band_highlight = workbook.add_format({'bold': True, 'bg_color': '#CBD5E1', 'font_color': '#0F172A', 'border': 1})
        fmt_band_amount = workbook.add_format({'bold': True, 'bg_color': '#CBD5E1', 'font_color': '#0F172A', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        fmt_band_amount_neg = workbook.add_format({'bold': True, 'bg_color': '#CBD5E1', 'font_color': '#DC2626', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        
        fmt_cell = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        fmt_cell_bold = workbook.add_format({'bold': True, 'border': 1, 'valign': 'vcenter'})
        fmt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'})
        fmt_num_bold = workbook.add_format({'bold': True, 'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'})
        fmt_num_neg = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'font_color': '#DC2626'})
        fmt_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_center_bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_grand_total = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': '#FFFFFF', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        fmt_grand_label = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': '#FFFFFF', 'border': 1, 'align': 'left'})

        worksheet.set_column('A:A', 48)
        worksheet.set_column('B:B', 22)
        if has_comp:
            worksheet.set_column('C:C', 22)
            worksheet.set_column('D:D', 22)
            worksheet.set_column('E:E', 16)

        company_name = data.get('company_name', 'PT Konsulta Semen Gresik')
        worksheet.write(0, 0, company_name, fmt_title)
        sub_title = f"PROFIT AND LOSS (LAPORAN LABA RUGI) — Periode: {data.get('date_from_display')} s/d {data.get('date_to_display')}"
        if has_comp:
            sub_title += f" vs {data.get('comp_date_from_display')} s/d {data.get('comp_date_to_display')}"
        if data.get('unit_name'):
            sub_title += f" | Departemen: {data.get('unit_name')}"
        worksheet.write(1, 0, sub_title, fmt_subtitle)
        worksheet.write(2, 0, f"Status: {'Hanya Jurnal Disetujui (Posted)' if data.get('target_move') == 'posted' else 'Semua Jurnal'}", fmt_subtitle)

        # Header Columns
        row = 4
        worksheet.write(row, 0, "Komponen Laba Rugi", fmt_subsec_header)
        worksheet.write(row, 1, f"Periode Aktif", fmt_subsec_header)
        if has_comp:
            worksheet.write(row, 2, f"Periode Pembanding", fmt_subsec_header)
            worksheet.write(row, 3, "Variansi (Rp)", fmt_subsec_header)
            worksheet.write(row, 4, "% Perubahan", fmt_subsec_header)
        worksheet.set_row(row, 24)
        row += 1

        def write_account_section(sec_data, is_collapsible=True):
            nonlocal row
            # Section Header Row
            worksheet.write(row, 0, f"▶ {sec_data['name']}", fmt_cell_bold)
            worksheet.write(row, 1, sec_data['total'], fmt_num_bold)
            if has_comp:
                worksheet.write(row, 2, sec_data['comp_total'], fmt_num_bold)
                worksheet.write(row, 3, sec_data['diff'], fmt_num_bold)
                worksheet.write(row, 4, sec_data['diff_pct_formatted'], fmt_center_bold)
            row += 1

            # Accounts
            for acc in sec_data.get('accounts', []):
                worksheet.write(row, 0, f"    {acc['full_name']}", fmt_cell)
                worksheet.write(row, 1, acc['balance'], fmt_num_neg if acc['is_negative'] else fmt_num)
                if has_comp:
                    worksheet.write(row, 2, acc['comp_balance'], fmt_num)
                    worksheet.write(row, 3, acc['diff'], fmt_num_neg if acc['is_diff_negative'] else fmt_num)
                    worksheet.write(row, 4, acc['diff_pct_formatted'], fmt_center)
                row += 1

        def write_highlight_band(sec_data):
            nonlocal row
            worksheet.write(row, 0, sec_data['name'], fmt_band_highlight)
            worksheet.write(row, 1, sec_data['total'], fmt_band_amount_neg if sec_data['is_negative'] else fmt_band_amount)
            if has_comp:
                worksheet.write(row, 2, sec_data['comp_total'], fmt_band_amount)
                worksheet.write(row, 3, sec_data['diff'], fmt_band_amount_neg if sec_data['is_diff_negative'] else fmt_band_amount)
                worksheet.write(row, 4, sec_data['diff_pct_formatted'], fmt_band_highlight)
            worksheet.set_row(row, 22)
            row += 1

        # 1. Revenue
        write_account_section(sections['revenue'])
        # 2. Costs of Revenue
        write_account_section(sections['costs_of_revenue'])
        # 3. Gross Profit (Band)
        write_highlight_band(sections['gross_profit'])
        # 4. Operating Expenses
        write_account_section(sections['operating_expenses'])
        # 5. Operating Income (Band)
        write_highlight_band(sections['operating_income'])
        # 6. Other Income
        write_account_section(sections['other_income'])
        # 7. Other Expenses
        write_account_section(sections['other_expenses'])
        # 8. Net Profit (Band)
        write_highlight_band(sections['net_profit'])
        # 9. Allocations
        write_account_section(sections['allocations'])
        # 10. Net Profit Left After Allocations (Final Band)
        net_final = sections['net_profit_after_alloc']
        worksheet.write(row, 0, net_final['name'], fmt_grand_label)
        worksheet.write(row, 1, net_final['total'], fmt_grand_total)
        if has_comp:
            worksheet.write(row, 2, net_final['comp_total'], fmt_grand_total)
            worksheet.write(row, 3, net_final['diff'], fmt_grand_total)
            worksheet.write(row, 4, net_final['diff_pct_formatted'], fmt_grand_label)
        worksheet.set_row(row, 25)

        workbook.close()
        output.seek(0)
        file_data = output.read()

        filename = f"Profit_and_Loss_{data.get('date_from')}_{data.get('date_to')}.xlsx"
        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    @http.route('/sif_keuangan/export_profit_loss_pdf', type='http', auth='user')
    def export_profit_loss_pdf(self, date_from=None, date_to=None, target_move='posted', unit_name=None, comparison_type='none', **kw):
        """
        Stream export Profit and Loss (Laba Rugi) langsung ke berkas PDF.
        """
        wizard = request.env['sif.profit.loss.wizard'].create({
            'date_from': date_from or request.env['sif.profit.loss']._default_date_from(),
            'date_to': date_to or request.env['sif.profit.loss']._default_date_to(),
            'target_move': target_move or 'posted',
            'unit_name': unit_name or False,
            'comparison_type': comparison_type or 'none',
        })
        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'sif_keuangan.action_report_profit_loss',
            [wizard.id]
        )
        filename = f"Profit_and_Loss_{wizard.date_from}_{wizard.date_to}.pdf"
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
