# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import io
import json

from odoo import _
from odoo.http import Controller, request, route, content_disposition


class ProductPricelistExportController(Controller):

    @route('/product/export/pricelist/', type='http', auth='user', readonly=True)
    def export_pricelist(self, report_data, export_format):
        json_data = json.loads(report_data)
        report_data = request.env['report.product.report_pricelist']._get_report_data(json_data)
        pricelist_name = report_data['pricelist']['name']
        quantities = report_data['quantities']
        products = report_data['products']
        headers = [
            _("Product"),
            _("UOM"),
        ] + [_("Quantity (%s UoM)", qty) for qty in quantities]
        if export_format == 'csv':
            return self._generate_csv(pricelist_name, quantities, products, headers)
        else:
            return self._generate_xlsx(pricelist_name, quantities, products, headers)

    def _generate_rows(self, products, quantities):
        rows = []
        for product in products:
            variants = product.get('variants', [product])
            for variant in variants:
                row = [
                    variant['name'],
                    variant['uom']
                ] + [variant['price'].get(qty, 0.0) for qty in quantities]
                rows.append(row)
        return rows

    def _generate_csv(self, pricelist_name, quantities, products, headers):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        rows = self._generate_rows(products, quantities)
        writer.writerows(rows)
        content = buffer.getvalue()
        buffer.close()
        headers = [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', content_disposition(f'Pricelist - {pricelist_name}.csv'))
        ]
        return request.make_response(content, headers)

    def _generate_xlsx(self, pricelist_name, quantities, products, headers):
        buffer = io.BytesIO()
        import xlsxwriter  # noqa: PLC0415
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        worksheet.write_row(0, 0, headers)
        rows = self._generate_rows(products, quantities)
        column_widths = [len(header) for header in headers]
        for row_idx, row in enumerate(rows, start=1):
            worksheet.write_row(row_idx, 0, row)
            for col_idx, cell_value in enumerate(row):
                column_widths[col_idx] = max(column_widths[col_idx], len(str(cell_value)))

        for col_idx, width in enumerate(column_widths):
            worksheet.set_column(col_idx, col_idx, width)
        workbook.close()
        content = buffer.getvalue()
        buffer.close()
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(f'Pricelist - {pricelist_name}.xlsx'))
        ]
        return request.make_response(content, headers)
