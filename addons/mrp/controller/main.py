# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import xlsxwriter

from odoo import http
from odoo.http import content_disposition, request


class BomReportController(http.Controller):
    @http.route('/bom_report_xslx/<int:bom_id>', type='http')
    def get_report_xlsx(self, bom_id, quantity, variant, report_name='all', **kw):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('bom_structure_sheet.xlsx'))
            ]
        )
        report_obj = request.env['report.mrp.report_bom_structure']
        data, header, columns, report_name = report_obj._get_report_xslx_values(bom_id, quantity, variant, report_name)
        self.prepare_xlsx_sheet(data, header, columns, report_name, response)
        return response

    def prepare_xlsx_sheet(self, data, header, columns, report_name, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(report_name)

        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666', 'indent': 1})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 3})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 1, 25)
        sheet.set_column(4, 4, 10)
        y_offset = 1
        x = 0

        docs = data['docs'][0]
        lines = docs['lines']

        #header
        for column_x in range(0, len(header)):
            header_label = header[column_x].get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            sheet.write(y_offset, column_x, header_label, title_style)

        y_offset += 1
        for bom_line_x in range(0, len(columns)):
            sheet.write(y_offset, bom_line_x, docs.get(columns[bom_line_x], ''), level_0_style)

        y_offset += 1
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = level_1_col1_style
            elif level == 2:
                style = level_2_style
                col1_style = level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            for x in range(0, len(columns)):
                sheet.write(y+y_offset, x, lines[y].get(columns[x], ''), x > 0 and style or col1_style)

        quantity_index = columns.index('quantity')
        sheet.set_column(y_offset + len(lines), quantity_index, 8)
        sheet.write(y_offset + len(lines), quantity_index, 'Unit Cost', level_1_style)

        if docs.get('report_name') == 'bom_structure':
            price_index = columns.index('prod_cost')
            sheet.write(y_offset + len(lines), price_index, docs.get('prod_cost'), level_1_style)
        elif docs.get('report_name') == 'bom_cost':
            total_index = columns.index('total')
            sheet.write(y_offset + len(lines), total_index, docs.get('total'), level_1_style)
        else:
            price_index = columns.index('prod_cost')
            total_index = columns.index('total')
            sheet.write(y_offset + len(lines), price_index, docs.get('prod_cost'), level_1_style)
            sheet.write(y_offset + len(lines), total_index, docs.get('total'), level_1_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
