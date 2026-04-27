# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import json

from werkzeug.datastructures import FileStorage

from odoo import http, _
from odoo.http import content_disposition, request
from odoo.tools import osutil
from odoo.tools.misc import xlsxwriter


class WebCohort(http.Controller):

    @http.route('/web/cohort/export', type='http', auth='user')
    def export_xls(self, data, **kw):
        result = json.load(data) if isinstance(data, FileStorage) else json.loads(data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(result['title'])
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        row = 0

        def write_data(report, row, col):
            # Headers
            columns_length = len(result[report]['rows'][0]['columns'])
            if result['timeline'] == 'backward':
                header_sign = ''
                col_range = range(-(columns_length - 1), 1)
            else:
                header_sign = '+'
                col_range = range(columns_length)

            worksheet.merge_range(row, col + 2, row, columns_length + 1,
                _('%(date_stop)s - By %(interval)s', date_stop=result['date_stop_string'], interval=result['interval_string']), style_highlight)
            row += 1
            worksheet.write(row, col, result['date_start_string'], style_highlight)
            # set minimum width to date_start_string cell to 15 which is around 83px
            worksheet.set_column(col, col, 15)
            col += 1
            worksheet.write(col, col, result['measure_string'], style_highlight)
            # set minimum width to measure_string cell to 15 which is around 83px
            worksheet.set_column(col, col, 15)
            col += 1
            for n in col_range:
                worksheet.write(row, col, '%s%s' % (header_sign, n), style_highlight)
                col += 1

            # Rows
            row += 1
            for res in result[report]['rows']:
                col = 0
                worksheet.write(row, col, res['date'], style_normal)
                col += 1
                worksheet.write(row, col, res['value'], style_normal)
                col += 1
                for i in res['columns']:
                    worksheet.write(row, col, i['percentage'] == '-' and i['percentage'] or str(i['percentage']) + '%', style_normal)
                    col += 1
                row += 1

            # Total
            col = 0
            worksheet.write(row, col, _('Average'), style_highlight)
            col += 1
            worksheet.write(row, col, '%.1f' % result[report]['avg']['avg_value'], style_highlight)
            col += 1
            total = result[report]['avg']['columns_avg']
            for n in range(columns_length):
                if total[str(n)]['count']:
                    worksheet.write(row, col, '%.1f' % float(total[str(n)]['percentage'] / total[str(n)]['count']) + '%', style_highlight)
                else:
                    worksheet.write(row, col, '-', style_highlight)
                col += 1

            return row

        report_length = len(result['report']['rows'])
        comparison_report = result.get('comparisonReport', False)
        if comparison_report:
            comparison_report_length = len(comparison_report['rows'])

        if comparison_report:
            if report_length:
                row = write_data('report', row, 0)
                if comparison_report_length:
                    write_data('comparisonReport', row + 2, 0)
            elif comparison_report_length:
                write_data('comparisonReport', row, 0)
        else:
            row = write_data('report', row, 0)

        workbook.close()
        xlsx_data = output.getvalue()
        filename = osutil.clean_filename(_("Cohort %(title)s (%(model_name)s)", title=result['title'], model_name=result['model']))
        response = request.make_response(
            xlsx_data,
            headers=[('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename + '.xlsx'))],
        )
        return response
