# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api, _
from datetime import datetime, date
from io import BytesIO
from dateutil.relativedelta import relativedelta
import xlwt
import base64
from odoo.exceptions import UserError


class WizardSlowMovingInv(models.TransientModel):
    _name = "wizard.slow.moving.inventory"
    _description = "Slow Moving Inventory"

    from_date = fields.Date(string="Start Date", default=datetime.today(), required=True)
    categ_ids = fields.Many2many('product.category', string="Product Category")
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
    avg_month = fields.Integer('Number of Months for Average', required=True)
    avg_on_hand_month = fields.Integer('On Hand Months', required=True)
    file_data = fields.Binary(string='File')
    file_name = fields.Char(string='File Name', readonly=True)
    view_by = fields.Selection([('pdf', 'PDF'), ('excel', 'Excel')], string='View by', required=True, default='pdf')
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')

    def print_report(self):
        if self.view_by == 'pdf':
            return self.env.ref('flexipharmacy.pdf_slow_moving_inventory_report').report_action(self)
        else:
            self.generate_xls_report()
            return {
                'name': 'Slow Moving Inventory',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
            }

    def generate_xls_report(self):
        self.ensure_one()
        slow_move_inv_dict = self.env['report.flexipharmacy.slow_moving_inv_report_pdf'].summary_data(
            self)
        curr_symbol = self.env.user.company_id.currency_id.symbol
        report_header = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        header_format = xlwt.easyxf(
            'font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        style_filter_data = xlwt.easyxf(
            'font:bold True; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        data_format = xlwt.easyxf(
            'align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        amt_format = xlwt.easyxf(
            'align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        if slow_move_inv_dict:
            workbook = xlwt.Workbook(encoding="utf-8")
            worksheet = workbook.add_sheet("Slow Moving Inventory Report")
            worksheet.write_merge(0, 1, 0, 4, "Slow Moving Inventory Report", style=report_header)
            worksheet.write_merge(2, 2, 1, 1, "Categories", style=header_format)
            worksheet.write_merge(2, 2, 2, 3, "Warehouse", style=header_format)
            if self.categ_ids:
                catg_name = ', '.join(map(lambda x: (x.name), self.categ_ids))
                worksheet.write_merge(3, 3, 1, 1, catg_name, style=style_filter_data)
            else:
                worksheet.write_merge(3, 3, 1, 1, "All", style=style_filter_data)
            if self.warehouse_ids:
                warehouse_name = ', '.join(map(lambda x: (x.name), self.warehouse_ids))
                worksheet.write_merge(3, 3, 2, 3, warehouse_name, style=style_filter_data)
            else:
                worksheet.write_merge(3, 3, 2, 3, "All", style=style_filter_data)
            worksheet.write_merge(4, 4, 1, 1, "No. of Months for Average", style=header_format)
            worksheet.write_merge(4, 4, 2, 3, "On Hand Months", style=header_format)
            worksheet.write_merge(5, 5, 1, 1, self.avg_month, style=style_filter_data)
            worksheet.write_merge(5, 5, 2, 3, self.avg_on_hand_month, style=style_filter_data)
            row_header = 5
            worksheet.write_merge(row_header + 2, row_header + 2, 0, 0, 'Part #', style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 1, 1, 'Items', style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 2, 2, 'On Hand', style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 3, 3, 'Cost Price', style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 4, 4, 'Value', style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 5, 5, 'Months of Stock Available',
                                  style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 6, 6, 'Average Monthly Transactions',
                                  style=header_format)
            worksheet.write_merge(row_header + 2, row_header + 2, 7, 7, 'UOM', style=header_format)
            row = row_header + 3
            for val in slow_move_inv_dict:
                cost_price = [val][0].get('final_cost_price') + "" + curr_symbol
                value = [val][0].get('value') + "" + curr_symbol
                worksheet.write_merge(row, row, 0, 0, [val][0].get('default_code'), style=data_format)
                worksheet.write_merge(row, row, 1, 1, [val][0].get('p_name'), style=data_format)
                worksheet.write_merge(row, row, 2, 2, [val][0].get('on_hand'), style=amt_format)
                worksheet.write_merge(row, row, 3, 3, cost_price, style=amt_format)
                worksheet.write_merge(row, row, 4, 4, value, style=amt_format)
                worksheet.write_merge(row, row, 5, 5, [val][0].get('compare_qty'), style=amt_format)
                worksheet.write_merge(row, row, 6, 6, [val][0].get('avg_qty'), style=amt_format)
                worksheet.write_merge(row, row, 7, 7, [val][0].get('uom_id'), style=data_format)
                row += 1
            worksheet.col(0).width = 4200
            worksheet.col(1).width = 10000
            worksheet.col(2).width = 6000
            worksheet.col(3).width = 6000
            worksheet.col(4).width = 6000
            worksheet.col(5).width = 6000
            file_data = BytesIO()
            workbook.save(file_data)
            self.write({
                'state': 'get',
                'file_data': base64.encodebytes(file_data.getvalue()),
                'file_name': 'Slow Moving Inventory.xlsx'
            })
        else:
            raise UserError(_('No Record Found.'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
