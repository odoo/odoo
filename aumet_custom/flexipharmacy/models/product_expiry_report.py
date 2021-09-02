# -*- coding: utf-8 -*-
#################################################################################
# Author : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
import base64
from io import BytesIO
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import xlwt
from odoo.exceptions import Warning, UserError
from odoo import models, fields, api, _


class ProductExpiryReport(models.Model):
    _name = "product.expiry.report"
    _description = "Product Expiry Report"

    num_expiry_days = fields.Integer(string="Product Expiry In Next")
    location_ids = fields.Many2many('stock.location', string="Location",
                                    domain=[('usage', '=', 'internal')])
    category_ids = fields.Many2many('product.category', string="Category")
    group_by = fields.Selection([('product', 'Product'), ('category', 'Category'),
                                ('warehouse', 'Warehouse'), ('location', 'Location')], string="Group By",
                                default="location")

    def print_pdf_report(self):
        module_installed = self.env['ir.module.module'].search([('name', '=', 'product_expiry'),
                                                                ('state', '=', 'installed')])
        if module_installed:
            return self.print_product_expiry_report('pdf')
        else:
            raise UserError(_('Please enable "Expiration Dates" from Inventory-->Settings-->Traceability'))

    def print_xls_report(self):
        module_installed = self.env['ir.module.module'].search([('name', '=', 'product_expiry'),
                                                                ('state', '=', 'installed')])
        if not module_installed:
            raise UserError(_('Please enable "Expiration Dates" from Inventory-->Settings-->Traceability'))
        else:
            return self.print_product_expiry_report('xls')

    def print_product_expiry_report(self, report_type):
        # if self.num_expiry_days <= 0:
        #     raise UserError('Number Of Expiry Days should be greater then 0')
        expiry_days_where = " AND spl.expiration_date <= '%s'"%(date.today())
        if self.num_expiry_days:
            expiry_days_where = " AND spl.expiration_date >= '%s' AND spl.expiration_date <= '%s' "%(date.today() , date.today() + timedelta(days=self.num_expiry_days))

        location_ids = self.location_ids.ids or self.env['stock.location'].search([('usage', '=', 'internal')]).ids
        category_ids = self.category_ids.ids or self.env['product.category'].search([]).ids
        query = '''SELECT sq.location_id,sl.usage,spl.product_id,spl.id,spl.expiration_date,spl.name,
                        pc.name as product_category,
                                pp.default_code,pt.name as product_name,pp.barcode  
                        FROM stock_production_lot spl
                                LEFT JOIN stock_quant sq on sq.lot_id = spl.id
                                LEFT JOIN stock_location sl on sq.location_id = sl.id
                                LEFT JOIN product_product pp on spl.product_id = pp.id
                                LEFT JOIN product_template pt on pp.product_tmpl_id  = pt.id
                                LEFT JOIN product_category pc on pt.categ_id = pc.id
                        WHERE pc.id IN %s''' % (
            "(%s)" % ','.join(map(str, category_ids)))
        query += expiry_days_where
        query += 'order by pp.default_code'
        self.env.cr.execute(query)
        res1 = self.env.cr.dictfetchall()

        temp_res = []
        for each in res1:
            if each.get('usage') in ['internal', None]:
                temp_res.append(each)
        query = '''SELECT sq.location_id,sl.usage,spl.product_id,spl.id,spl.expiration_date,spl.name,
                          pc.name as product_category,
                          pp.default_code,pt.name as product_name,pp.barcode FROM stock_quant sq
                          LEFT JOIN stock_location sl on sq.location_id = sl.id
                          LEFT JOIN stock_production_lot spl on sq.lot_id = spl.id
                          LEFT JOIN product_product pp on spl.product_id = pp.id
                          LEFT JOIN product_template pt on pp.product_tmpl_id  = pt.id
                          LEFT JOIN product_category pc on pt.categ_id = pc.id
                          WHERE spl.expiration_date <= '%s' AND
                          spl.expiration_date >= '%s' AND
                        pc.id IN %s AND
                        sq.location_id IN %s order by pp.default_code''' % (
            (date.today() + timedelta(days=self.num_expiry_days)),
            date.today(),
            "(%s)" % ','.join(map(str, category_ids)),
            "(%s)" % ','.join(map(str, location_ids)))
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        if not self.location_ids:
            res = res + temp_res
            res = [dict(item) for item in {tuple(each.items()) for each in res}]
        if len(res) == 0:
            raise UserError(_('No such record found for product expiry.'))
        else:
            if self.group_by == 'category':
                vals = {}
                for each in res:
                    if not each.get('location_id'):
                        location_name = "--"
                    else:
                        location_name = self.env['stock.location'].browse(
                            each.get('location_id')).display_name
                    if each['product_category'] not in vals:
                        vals[each.get('product_category')] = [
                            {'barcode': each.get('barcode'),
                             'name': each.get('name'),
                             'product_id': each.get('product_name'),
                             'location_name': location_name,
                             'default_code': each.get('default_code') or '--------',
                             'expiration_date': each.get('expiration_date').strftime('%Y-%m-%d'),
                             'remaining_days': relativedelta(each.get('expiration_date'), date.today()).days,
                             'available_qty': self.env['stock.production.lot'].browse(
                                 each.get('id')).product_qty if each.get('id') else False, }]
                    else:
                        vals[each.get('product_category')].append(
                            {'barcode': each.get('barcode'),
                             'name': each.get('name'),
                             'product_id': each.get('product_name'),
                             'barcode': each.get('barcode'),
                             'location_name': location_name,
                             'default_code': each.get('default_code') or '--------',
                             'expiration_date': each.get('expiration_date').strftime('%Y-%m-%d'),
                             'remaining_days': relativedelta(each.get('expiration_date'), date.today()).days,
                             'available_qty': self.env['stock.production.lot'].browse(
                                 each.get('id')).product_qty if each.get('id') else False, })
            else:
                vals = {}
                for each in res:
                    if not each.get('location_id'):
                        location_name = "--"
                    else:
                        location_name = self.env['stock.location'].browse(
                            each.get('location_id')).display_name
                    if location_name not in vals:
                        vals[location_name] = [
                            {'barcode': each.get('barcode'),
                             'name': each.get('name'),
                             'product_id': each.get('product_name'),
                             'barcode': each.get('barcode'),
                             'product_category': each.get('product_category'),
                             'default_code': each.get('default_code') or '--------',
                             'expiration_date': each.get('expiration_date').strftime('%Y-%m-%d'),
                             'remaining_days': relativedelta(each.get('expiration_date'), date.today()).days,
                             'available_qty': self.env['stock.production.lot'].browse(
                                 each.get('id')).product_qty if each.get('id') else False, }]
                    else:
                        vals[location_name].append(
                            {
                             'barcode': each.get('barcode'),
                             'name': each.get('name'),
                             'product_id': each.get('product_name'),
                             'barcode': each.get('barcode'),
                             'product_category': each.get('product_category'),
                             'default_code': each.get('default_code') or '--------',
                             'expiration_date': each.get('expiration_date').strftime('%Y-%m-%d'),
                             'remaining_days': relativedelta(each.get('expiration_date'), date.today()).days,
                             'available_qty': self.env['stock.production.lot'].browse(
                                 each.get('id')).product_qty if each.get('id') else False, })
        vals.update(
            {'group_by': self.group_by, 'num_days': self.num_expiry_days, 'today_date': date.today()})
        vals_new = {}
        vals_new.update({'stock': vals})
        if report_type == 'pdf':
            return self.env.ref('flexipharmacy.product_expiry_report').report_action(self, data=vals_new)
        elif report_type == 'xls':
            return self.print_xls_product_report(vals)

    def print_xls_product_report(self, vals):
        style_pc = xlwt.XFStyle()
        bold = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        style_pc.alignment = alignment
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        font = xlwt.Font()
        borders = xlwt.Borders()
        borders.bottom = xlwt.Borders.THIN
        font.bold = True
        font.height = 500
        style_pc.font = font
        style_pc.alignment = alignment
        pattern = xlwt.Pattern()
        pattern.pattern = xlwt.Pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = xlwt.Style.colour_map['gray25']
        style_pc.pattern = pattern
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Stock Expiry Report')
        for num in range(0, 7):
            worksheet.col(num).width = 5600
        worksheet.write_merge(1, 2, 0, 6, 'Product Expiry Report', style=style_pc)
        worksheet.write(4, 0, "Product Expiry In Next", bold)
        worksheet.write(4, 1, str(vals.get('num_days')) + ' Days')
        worksheet.write(4, 4, "Date", bold)
        worksheet.write(4, 5, str(vals.get('today_date')))
        row_index = 6
        for key, value in vals.items():
            if vals.get('group_by') and key not in ['group_by', 'num_days', 'today_date']:
                if vals.get('group_by') == 'location':
                    worksheet.write(row_index, 0, "Location", bold)
                elif vals.get('group_by') == 'category':
                    worksheet.write(row_index, 0, "Category", bold)
                worksheet.write(row_index, 1, key)
                row_index += 2
                if value not in [vals.get('num_day'), vals.get('today_date')]:
                    worksheet.write(row_index, 0, "Barcode", bold)
                    worksheet.write(row_index, 1, "Lot/Serial number", bold)
                    worksheet.write(row_index, 2, "Product", bold)
                    if vals.get('group_by') == 'location':
                        worksheet.write(row_index, 3, "Category", bold)
                    elif vals.get('group_by') == 'category':
                        worksheet.write(row_index, 3, "Location", bold)
                    worksheet.write(row_index, 4, "Internal Ref", bold)
                    worksheet.write(row_index, 5, "Expiry Date", bold)
                    worksheet.write(row_index, 6, "Remaining Days", bold)
                    worksheet.write(row_index, 7, "Available Quantity", bold)
                    row_index += 1
                    for each in value:
                        count = 0
                        for each_key, each_val in each.items():
                            worksheet.write(row_index, count, each_val)
                            count += 1
                        row_index += 1
                    row_index += 1
                    file_data = BytesIO()
                    workbook.save(file_data)
                    report_id = self.env['report.download.wizard'].create({
                        'data': base64.encodestring(file_data.getvalue()),
                        'name': 'Product Expiry Report.xls'
                    })
        return {
            'name': 'Download Excel Report',
            'view_mode': 'form',
            'res_model': 'report.download.wizard',
            'target': 'new',
            'res_id': report_id.id,
            'type': 'ir.actions.act_window'
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
