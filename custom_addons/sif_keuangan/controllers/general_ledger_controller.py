# -*- coding: utf-8 -*-
import io
import xlsxwriter
from odoo import http
from odoo.http import request


class GeneralLedgerController(http.Controller):

    @http.route('/sif_keuangan/export_general_ledger_xlsx', type='http', auth='user')
    def export_general_ledger_xlsx(self, date_from=None, date_to=None, target_move='posted', search=None, unit_name=None, partner_id=None, **kw):
        """
        Stream export General Ledger ke berkas Excel (.xlsx).
        """
        filters = {
            'date_from': date_from,
            'date_to': date_to,
            'target_move': target_move or 'posted',
            'search': search or '',
            'unit_name': unit_name or '',
            'partner_id': partner_id or None,
        }

        gl_engine = request.env['sif.general.ledger']
        data = gl_engine.get_general_ledger_data(filters)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('General Ledger')

        # Formats
        fmt_title = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#714B67'})
        fmt_subtitle = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#4A5568'})
        fmt_header = workbook.add_format({
            'bold': True,
            'bg_color': '#714B67',
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        fmt_acc_header = workbook.add_format({
            'bold': True,
            'bg_color': '#EDF2F7',
            'font_color': '#2D3748',
            'border': 1
        })
        fmt_acc_amount = workbook.add_format({
            'bold': True,
            'bg_color': '#EDF2F7',
            'font_color': '#2D3748',
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right'
        })
        fmt_cell = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        fmt_cell_date = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        fmt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'})
        fmt_num_neg = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'font_color': '#E53E3E'})
        fmt_grand_total = workbook.add_format({
            'bold': True,
            'bg_color': '#2D3748',
            'font_color': '#FFFFFF',
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right'
        })
        fmt_grand_label = workbook.add_format({
            'bold': True,
            'bg_color': '#2D3748',
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'left'
        })

        # Columns width
        worksheet.set_column('A:A', 38)  # Ref / Keterangan
        worksheet.set_column('B:B', 14)  # Date
        worksheet.set_column('C:C', 25)  # Partner
        worksheet.set_column('D:D', 18)  # Debit
        worksheet.set_column('E:E', 18)  # Credit
        worksheet.set_column('F:F', 20)  # Balance

        # Title
        company_name = data.get('company_name', 'PT Konsulta Semen Gresik')
        worksheet.write(0, 0, company_name, fmt_title)
        worksheet.write(1, 0, f"GENERAL LEDGER (BUKU BESAR) — Periode: {data.get('date_from')} s/d {data.get('date_to')}", fmt_subtitle)
        unit_info = f" | Departemen: {data.get('unit_name')}" if data.get('unit_name') else ""
        worksheet.write(2, 0, f"Status: {'Hanya Jurnal Disetujui (Posted)' if data.get('target_move') == 'posted' else 'Semua Jurnal'}{unit_info}", fmt_subtitle)

        # Header Table
        row = 4
        headers = ['No. Bukti / Keterangan Transaksi', 'Tanggal', 'Partner / Rekanan', 'Debet (Rp)', 'Kredit (Rp)', 'Saldo Berjalan (Rp)']
        for col_idx, h in enumerate(headers):
            worksheet.write(row, col_idx, h, fmt_header)
        worksheet.set_row(row, 25)
        row += 1

        for acc in data.get('accounts', []):
            # Account Header (with Normal Balance Info)
            acc_title = f"{acc['full_name']} (Saldo Normal: {acc.get('normal_balance_label', 'Debet')})"
            worksheet.write(row, 0, acc_title, fmt_acc_header)
            worksheet.write(row, 1, '', fmt_acc_header)
            worksheet.write(row, 2, '', fmt_acc_header)
            worksheet.write(row, 3, acc['total_debit'], fmt_acc_amount)
            worksheet.write(row, 4, acc['total_credit'], fmt_acc_amount)
            worksheet.write(row, 5, acc['ending_balance'], fmt_acc_amount)
            row += 1

            # Saldo Awal row
            worksheet.write(row, 0, '  Saldo Awal (Initial Balance)', fmt_cell)
            worksheet.write(row, 1, data.get('date_from'), fmt_cell_date)
            worksheet.write(row, 2, '-', fmt_cell)
            worksheet.write(row, 3, 0.0, fmt_num)
            worksheet.write(row, 4, 0.0, fmt_num)
            worksheet.write(row, 5, acc['initial_balance'], fmt_num_neg if acc['initial_balance'] < 0 else fmt_num)
            row += 1

            # Transaction Lines
            for line in acc.get('lines', []):
                worksheet.write(row, 0, f"  {line['title']}", fmt_cell)
                worksheet.write(row, 1, line['date'], fmt_cell_date)
                worksheet.write(row, 2, line['partner_name'], fmt_cell)
                worksheet.write(row, 3, line['debit'], fmt_num)
                worksheet.write(row, 4, line['credit'], fmt_num)
                worksheet.write(row, 5, line['balance'], fmt_num_neg if line['is_negative'] else fmt_num)
                row += 1

            # Total Account Row
            worksheet.write(row, 0, f"Total {acc['full_name']}", fmt_acc_header)
            worksheet.write(row, 1, '', fmt_acc_header)
            worksheet.write(row, 2, '', fmt_acc_header)
            worksheet.write(row, 3, acc['total_debit'], fmt_acc_amount)
            worksheet.write(row, 4, acc['total_credit'], fmt_acc_amount)
            worksheet.write(row, 5, acc['ending_balance'], fmt_acc_amount)
            row += 1

        # Grand Total Row
        gt = data.get('grand_total', {})
        worksheet.write(row, 0, 'TOTAL GENERAL LEDGER', fmt_grand_label)
        worksheet.write(row, 1, '', fmt_grand_label)
        worksheet.write(row, 2, f"Selisih: Rp {gt.get('difference', 0.0):,.2f}", fmt_grand_label)
        worksheet.write(row, 3, gt.get('total_debit', 0.0), fmt_grand_total)
        worksheet.write(row, 4, gt.get('total_credit', 0.0), fmt_grand_total)
        worksheet.write(row, 5, gt.get('difference', 0.0), fmt_grand_total)
        worksheet.set_row(row, 22)

        workbook.close()
        output.seek(0)
        file_data = output.read()

        filename = f"General_Ledger_{data.get('date_from')}_{data.get('date_to')}.xlsx"
        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    @http.route('/sif_keuangan/export_general_ledger_pdf', type='http', auth='user')
    def export_general_ledger_pdf(self, date_from=None, date_to=None, target_move='posted', unit_name=None, partner_id=None, **kw):
        """
        Stream export General Ledger langsung ke berkas PDF.
        """
        wizard_vals = {
            'date_from': date_from or request.env['sif.general.ledger']._default_date_from(),
            'date_to': date_to or request.env['sif.general.ledger']._default_date_to(),
            'target_move': target_move or 'posted',
            'unit_name': unit_name or False,
        }
        if partner_id:
            try:
                wizard_vals['partner_id'] = int(partner_id)
            except (ValueError, TypeError):
                pass

        wizard = request.env['sif.general.ledger.wizard'].create(wizard_vals)
        pdf_content, _ = request.env['ir.actions.report']._render_qweb_pdf(
            'sif_keuangan.action_report_general_ledger',
            [wizard.id]
        )
        filename = f"General_Ledger_{wizard.date_from}_{wizard.date_to}.pdf"
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
