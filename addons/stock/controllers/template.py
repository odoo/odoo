import io

import xlsxwriter

from odoo import _
from odoo.http import Controller, request, route
from odoo.fields import Domain


class StockTemplateController(Controller):

    @route('/stock/xlsx/import_template', type='http', auth='user')
    def import_template(self):
        # Creating the workbook in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Physical Inventory")

        # Styling + Conditional row: lots
        header_format = workbook.add_format({'bold': True, 'align': 'center'})
        center_aligned_cell = workbook.add_format({'align': 'center'})
        lots = request.env.user.has_group("stock.group_production_lot")
        packages = request.env.user.has_group("stock.group_tracking_lot")

        # Writing the headers
        headers = [_('Location'), _('Product/ID'), _('Product/Display Name'), _('Inventoried Quantity'), _('Scheduled'), _('Assigned To')]
        centered_columns = [3]
        if packages:
            centered_columns = [3, 4]
            headers.insert(3, _('Package'))
        if lots:
            centered_columns = [x + 1 for x in centered_columns if x >= 3] + [3]
            headers.insert(3, _('Lot or Serial Number'))
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        # Adding the quants information to the rows list
        rows = []
        quants = self.env['stock.quant'].search([Domain('on_hand', '=', True)])
        for quant in quants:
            location = quant.location_id.complete_name
            product = quant.product_id
            scheduled = str(quant.inventory_date) if quant.inventory_date else ''
            user_id = quant.user_id.name or ""
            internal_product_id = product.export_data(["id"]).get('datas', [[""]])[0][0]
            row = [location, internal_product_id, product.partner_ref, quant.quantity, scheduled, user_id]
            if packages:
                package_name = quant.package_id.display_name if quant.package_id else ""
                row.insert(3, package_name)
            if lots:
                lot_id = quant.lot_id.name or ""
                row.insert(3, lot_id)
            rows.append(row)

        # Adding all storable products without a quant
        products = self.env['product.product'].search(Domain.AND([
            Domain("is_storable", "=", True),
            Domain('id', 'not in', quants.product_id.ids),
        ]))
        for product in products:
            internal_product_id = product.export_data(["id"]).get('datas', [[""]])[0][0]
            row = ['WH/Stock', internal_product_id, product.partner_ref, 0, '', '']
            if packages:
                row.insert(3, '')
            if lots:
                row.insert(3, '')
            rows.append(row)

        # Writing the rows to the file
        for row_index, row in enumerate(rows, start=1):
            for cell_index, cell in enumerate(row):
                if cell_index in centered_columns:
                    worksheet.write(row_index, cell_index, cell, center_aligned_cell)
                else:
                    worksheet.write(row_index, cell_index, cell)

        # Closing and saving the file
        worksheet.autofit()
        workbook.close()
        output.seek(0)
        excel_file = output.read()
        output.close()

        headers = [
            ('Content-Type', 'application/xlsx'),
            ('Content-Disposition', 'attachment; filename=stock_quant.xlsx;'),
            ('Content-Length', len(excel_file)),
        ]

        return request.make_response(excel_file, headers=headers)
