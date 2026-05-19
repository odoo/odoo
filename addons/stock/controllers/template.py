import io

import xlsxwriter

from odoo import _
from odoo.fields import Domain
from odoo.http import Controller, request, route
from odoo.http.stream import content_disposition


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
        location = request.env.user.has_group("stock.group_stock_multi_locations")
        owner = request.env.user.has_group("stock.group_tracking_owner")
        packages = request.env.user.has_group("stock.group_tracking_lot")
        lots = request.env.user.has_group("stock.group_production_lot")

        quants_domain = [Domain('on_hand', '=', True)]
        if not owner:
            quants_domain += [Domain("owner_id", "=", False)]
        quants = self.env['stock.quant'].search(Domain.AND(quants_domain))
        products = self.env['product.product'].search(Domain.AND([
            Domain("is_storable", "=", True),
            Domain('id', 'not in', quants.product_id.ids),
        ]))
        external_id_by_id = dict((quants.product_id | products).export_data([".id", "id"]).get('datas', []))

        # Writing the headers
        headers = [_('Product/ID'), _('Product/Display Name'), _('Quantity'), _('Counted'), _('Scheduled'), _('Assigned To')]
        centered_columns = [2, 3]
        if location:
            headers, centered_columns = _insert_header(headers, centered_columns, 0, _("Location"))
        if owner:
            headers, centered_columns = _insert_header(headers, centered_columns, 3, _("Owner"))
        if packages:
            headers, centered_columns = _insert_header(headers, centered_columns, 3, _("Package Name"))
        if lots:
            headers, centered_columns = _insert_header(headers, centered_columns, 3, _("Lot or Serial Number"), centered=True)
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        # Add the quants information to the rows list
        rows = []
        for quant in quants:
            product = quant.product_id
            scheduled = str(quant.inventory_date) if quant.inventory_date else ''
            user_id = quant.user_id.name or ""
            row = [external_id_by_id.get(str(product.id)), product.partner_ref, quant.quantity, quant.inventory_quantity, scheduled, user_id]
            if location:
                location_name = quant.location_id.complete_name
                row.insert(0, location_name)
            if owner:
                owner_id = quant.owner_id.display_name or ""
                row.insert(3, owner_id)
            if packages:
                package_name = quant.package_id.display_name if quant.package_id else ""
                row.insert(3, package_name)
            if lots:
                lot_id = quant.lot_id.name or ""
                row.insert(3, lot_id)
            rows.append(row)

        # Add all storable products without a quant
        default_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        for product in products:
            row = [external_id_by_id.get(str(product.id)), product.partner_ref, 0, 0, '', '']
            if location:
                location_name = default_location.complete_name
                row.insert(0, location_name)
            if owner:
                row.insert(3, '')
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

        return request.make_response(excel_file, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition('stock_quant.xlsx')),
        ])


def _insert_header(headers, centered_columns, position, item, centered=False):
    centered_columns = [x + 1 if x >= position else x for x in centered_columns]
    if centered:
        centered_columns += [position]
    headers.insert(position, item)
    return headers, centered_columns
