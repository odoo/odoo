import json

from odoo import http
from odoo.http import request
from odoo.tools.misc import xlwt


class WebExportXLSX(http.Controller):

    @http.route('/web/export_xlsx/export', type='http', auth='user')
    def export_xlsx(self, data, token):
        result = json.loads(data)
        columns = result.get('columns')
        fields = result.get('fields')
        aggregates = result.get('aggregates')

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet(result['title'])
        xlwt.add_palette_colour('gray_lighter', 0x21)
        workbook.set_colour_RGB(0x21, 224, 224, 224)
        style_highlight = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour gray_lighter;')
        style_normal_bold = xlwt.easyxf('font: bold on;')
        rowIndex = 0

        # Header Columns field
        for idx, column in enumerate(columns):
            worksheet.write(rowIndex, idx, fields[column]['string'], style_normal_bold)

        # Rows recursive
        # Prints group and records
        def write_rows(rowIndex, rows):
            for idx, row in enumerate(rows):
                for columnIndex, column in enumerate(columns):
                    if row['type'] == "list":
                        columnValue = ""
                        if columnIndex == 0:
                            columnValue = row['value']
                        elif row.get('aggregateValues').get(column):
                            columnValue = row['aggregateValues'][column]
                        worksheet.write(rowIndex, columnIndex, columnValue, style_highlight)
                    if row['type'] == "record":
                        record = row['record']
                        columnValue = record[column]
                        worksheet.write(rowIndex, columnIndex, columnValue)
                rowIndex += 1
                if row.get('data') and len(row.get('data')) > 0:
                    rowIndex = write_rows(rowIndex, row.get('data'))
            return rowIndex

        rowIndex = write_rows(rowIndex + 1, result['rows'])

        # Footer aggregates Columns field with aggregate values
        for idx, column in enumerate(columns):
            value = aggregates[column]['value'] if aggregates.get(column) else ""
            worksheet.write(rowIndex, idx, value, style_normal_bold)
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', 'attachment; filename=%s.xls' % result['title'].replace(" ", "-"))
            ],
            cookies={'fileToken': token}
        )
        workbook.save(response.stream)
        return response
