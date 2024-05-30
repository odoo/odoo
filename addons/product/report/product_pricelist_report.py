# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import base64
import csv
import io
import xlsxwriter


class ProductPricelistReport(models.AbstractModel):
    _name = 'report.product.report_pricelist'
    _description = 'Pricelist Report'

    def _get_report_values(self, docids, data):
        return self._get_report_data(data, 'pdf')

    @api.model
    def get_html(self, data):
        render_values = self._get_report_data(data, 'html')
        return self.env['ir.qweb']._render('product.report_pricelist_page', render_values)

    @api.model
    def export_csv(self, data):
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Define headers dynamically based on the quantities
        headers = ['Product', 'UOM'] + [f'Quantity ({qty} UOM)' for qty in data['quantities']]
        writer.writerow(headers)

        # Get the report data
        report_data = self._get_report_data(data)
        products = report_data['products']
        quantities = report_data['quantities']

        # Write data rows
        for product in products:
            product_name = product['name']
            product_uom = product['uom']
            product_prices = product['price']

            row = [product_name, product_uom]
            for qty in quantities:
                price = product_prices.get(qty, 0.0)
                row.append(price)

            writer.writerow(row)

        # Get the CSV data from the buffer
        csv_data = buffer.getvalue()
        buffer.close()

        return csv_data

    @api.model
    def export_xls(self, data):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        headers = ['Product', 'UOM'] + [f'Quantity ({qty} UOM)' for qty in data['quantities']]
        worksheet.write_row(0, 0, headers)

        # Initialize column widths based on header length
        column_widths = [len(header) for header in headers]

        # Gather data for setting dynamic widths
        report_data = self._get_report_data(data)
        products = report_data['products']
        quantities = report_data['quantities']

        # Collect all rows of data
        rows = []
        for product in products:
            data_row = [product['name'], product['uom']]
            for qty in quantities:
                price_str = str(product['price'].get(qty, 0.0))
                data_row.append(price_str)
            rows.append(data_row)

            # Update column widths based on data length
            for col_idx, cell_value in enumerate(data_row):
                column_widths[col_idx] = max(column_widths[col_idx], len(cell_value))

        # Write the data rows to the worksheet
        for row_idx, row_data in enumerate(rows, start=1):
            worksheet.write_row(row_idx, 0, row_data)

        # Set the column widths dynamically
        for col_idx, width in enumerate(column_widths):
            worksheet.set_column(col_idx, col_idx, width)

        workbook.close()
        xls_data = buffer.getvalue()
        buffer.close()

        return base64.b64encode(xls_data).decode('utf-8')

    def _get_report_data(self, data, report_type='html'):
        quantities = data.get('quantities', [1])

        data_pricelist_id = data.get('pricelist_id')
        pricelist_id = data_pricelist_id and int(data_pricelist_id)
        pricelist = self.env['product.pricelist'].browse(pricelist_id).exists()
        if not pricelist:
            pricelist = self.env['product.pricelist'].search([], limit=1)

        active_model = data.get('active_model', 'product.template')
        active_ids = data.get('active_ids') or []
        is_product_tmpl = active_model == 'product.template'
        ProductClass = self.env[active_model]

        products = ProductClass.browse(active_ids) if active_ids else ProductClass.search([('sale_ok', '=', True)])
        products_data = [
            self._get_product_data(is_product_tmpl, product, pricelist, quantities)
            for product in products
        ]

        return {
            'is_html_type': report_type == 'html',
            'is_product_tmpl': is_product_tmpl,
            'display_pricelist_title': data.get('display_pricelist_title', False) and bool(data['display_pricelist_title']),
            'pricelist': pricelist,
            'products': products_data,
            'quantities': quantities,
        }

    def _get_product_data(self, is_product_tmpl, product, pricelist, quantities):
        data = {
            'id': product.id,
            'name': is_product_tmpl and product.name or product.display_name,
            'price': dict.fromkeys(quantities, 0.0),
            'uom': product.uom_id.name,
        }
        for qty in quantities:
            data['price'][qty] = pricelist._get_product_price(product, qty)

        if is_product_tmpl and product.product_variant_count > 1:
            data['variants'] = [
                self._get_product_data(False, variant, pricelist, quantities)
                for variant in product.product_variant_ids
            ]

        return data
