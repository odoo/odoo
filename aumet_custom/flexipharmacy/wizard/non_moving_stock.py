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

import ast
import base64
from datetime import *
from io import BytesIO

import xlwt
from lxml import etree
from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.tools.misc import xlwt
from collections import OrderedDict


class NonMovingStock(models.TransientModel):
    _name = "non.moving.stock"
    _description = "Non Moving Stock Report"

    non_moving_product_days = fields.Integer(string="Non Moving Product in Last", required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouses")
    group_by_category = fields.Boolean(string="Group By Category")
    sale_category_ids = fields.Many2many('product.category', string="Categories")
    report_type = fields.Selection([('pdf', 'PDF Report'), ('xls', 'Excel Report')], string="Report Type",
                                   required=True, default="pdf")
    state = fields.Selection([('new', 'New'), ('done', 'done'), ('sent', 'Sent')], string="State", default='new')
    data = fields.Binary(string="File")
    file_name = fields.Char(string="File Name")
    send_mail_message = fields.Char(string="Message")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(NonMovingStock, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if not self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.groups_ids'):
            if view_type == 'form':
                doc = etree.XML(res['arch'])
                nodes = doc.xpath("//button[@name='send_mail']")
                for node in nodes:
                    node.set('invisible', '1')
                res['arch'] = etree.tostring(doc)
        return res

    def print_report(self):
        vals = {}
        warehouse_name = ''
        if self.non_moving_product_days <= 0:
            raise Warning(_("Please Enter Days To Proceed."))
        final_non_moving_data = {'days': self.non_moving_product_days}
        warehouse_ids_list = self.warehouse_ids or self.env['stock.warehouse'].search([])
        sale_category_ids_list = self.sale_category_ids or self.env['product.category'].search([])
        if self.warehouse_ids:
            warehouse_name = ", ".join([each.name for each in self.warehouse_ids])
            final_non_moving_data.update({'warehouse': warehouse_name})
        location_obj = self.env['stock.location'].sudo()
        customer_location_ids = location_obj.search([('usage', '=', 'customer')]).ids
        for each in warehouse_ids_list:
            location_ids = location_obj.search([('usage', '=', 'internal'), ('location_id', 'child_of',
                                                                             each.lot_stock_id.id)])
            query = """
                select product_id,location_id from stock_move 
                where location_id in %s and 
                state = 'done'
                and date >= '%s 00:00:00' and date <= '%s 23:59:59'
                and location_dest_id in %s
            """ % (
                "(%s)" % ",".join(map(str, location_ids.ids)),
                (date.today() - timedelta(days=self.non_moving_product_days)),
                date.today(), "(%s)" % ",".join(map(str, customer_location_ids)))
            self._cr.execute(query)
            stock_move_data = self._cr.dictfetchall()
            product_list = [each.get('product_id') for each in stock_move_data]
            stock_quant_query = '''
                select sq.product_id,pt.default_code,sl.id,pt.name,pc.name as category,sq.quantity,
                        sl.complete_name from stock_quant sq
                LEFT JOIN stock_location sl on sl.id = sq.location_id
                LEFT JOIN product_product pp on pp.id = sq.product_id
                LEFT JOIN product_template pt on pt.id = pp.product_tmpl_id
                LEFT JOIN product_category pc on pc.id = pt.categ_id
                where pt.categ_id in %s                
                      and sq.location_id in %s
                      and sq.product_id %s
                 ''' % ("(%s)" % ",".join(map(str, sale_category_ids_list.ids)),
                        "(%s)" % ",".join(map(str, location_ids.ids)),
                        "not in (%s)" % ",".join(map(str, product_list)) if product_list else "is not null"
                        )
            self._cr.execute(stock_quant_query)
            stock_quant_data = self._cr.dictfetchall()
            productobj = self.env['product.product']
            if self.group_by_category:
                for data in stock_quant_data:
                    product = productobj.browse(data.get('product_id'))
                    data.update({'sell_price': product.list_price, 'unit_price': product.standard_price})
                    if data.get('category') not in vals:
                        vals[data.get('category')] = [data]
                    else:
                        vals[data.get('category')].append(data)
            else:
                for data in stock_quant_data:
                    product = productobj.browse(data.get('product_id'))
                    data.update({'sell_price': product.list_price, 'unit_price': product.standard_price})
                    if each.id not in vals:
                        vals[each.id] = [data]
                    else:
                        vals[each.id].append(data)
        vals = OrderedDict(sorted(vals.items(), key=lambda item: item[0]))
        final_non_moving_data.update({'data': vals,
                                      'group_by': self.group_by_category,
                                      'currency': self.env.user.company_id.currency_id.symbol,
                                      'current_date': date.today().strftime('%d/%m/%Y')
                                      })

        if not vals:
            raise Warning(_('NO Stock Found'))
        if self.report_type == 'pdf':
            if self.env.context.get('send_mail'):
                final_non_moving_data.update({'break': False})
                vals_new = {'products': final_non_moving_data}
                template_id = self.env.ref('flexipharmacy.non_moving_stock_report')
                pdf = template_id._render_qweb_pdf(self, data=vals_new)
                values = base64.b64encode(pdf[0])
                attachment_id = self.env['ir.attachment'].sudo().create(
                    {'datas': values, 'name': 'Non Moving Stock Report',
                     'store_fname': 'Non Moving Stock.pdf'})
                return attachment_id
            else:
                final_non_moving_data.update({'break': True})
                vals_new = {'products': final_non_moving_data}
                return self.env.ref('flexipharmacy.non_moving_stock_report').report_action(self,
                                                                                           data=vals_new)

        elif self.report_type == 'xls':
            workbook = xlwt.Workbook()
            style_pc = xlwt.XFStyle()
            worksheet = workbook.add_sheet('Non Moving Stock Report')
            bold = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
            alignment = xlwt.Alignment()
            alignment.horz = xlwt.Alignment.HORZ_CENTER
            style_pc.alignment = alignment
            alignment = xlwt.Alignment()
            alignment.horz = xlwt.Alignment.HORZ_CENTER
            alignment_num = xlwt.Alignment()
            alignment_num.horz = xlwt.Alignment.HORZ_RIGHT
            horz_style = xlwt.XFStyle()
            horz_style.alignment = alignment_num
            align_num = xlwt.Alignment()
            align_num.horz = xlwt.Alignment.HORZ_RIGHT
            horz_style_pc = xlwt.XFStyle()
            horz_style_pc.alignment = alignment_num
            style1 = horz_style
            font = xlwt.Font()
            font1 = xlwt.Font()
            borders = xlwt.Borders()
            borders.bottom = xlwt.Borders.THIN
            font.bold = True
            font1.bold = True
            font.height = 500
            style_pc.font = font
            style1.font = font1
            style_pc.alignment = alignment
            pattern = xlwt.Pattern()
            pattern1 = xlwt.Pattern()
            pattern.pattern = xlwt.Pattern.SOLID_PATTERN
            pattern1.pattern = xlwt.Pattern.SOLID_PATTERN
            pattern.pattern_fore_colour = xlwt.Style.colour_map['gray25']
            pattern1.pattern_fore_colour = xlwt.Style.colour_map['gray25']
            style_pc.pattern = pattern
            style1.pattern = pattern
            worksheet.write_merge(0, 1, 0, 5, 'Non Moving Stock Report', style=style_pc)
            worksheet.col(2).width = 5600
            worksheet.write_merge(3, 3, 0, 2,
                                  'Non Moving Product in Last ' + str(self.non_moving_product_days) + ' Days',
                                  bold)
            row = 5
            if self.warehouse_ids:
                worksheet.write(row, 0, 'Warehouses', bold)
                worksheet.write_merge(row, row, 1, 2, warehouse_name)
                row = row + 2
            list1 = ['Default Code', 'Product', 'Location', 'Quantity', 'Cost Price', 'Sale Price']
            if self.group_by_category:
                for each_val in vals:
                    worksheet.write(row, 0, 'Category', bold)
                    worksheet.write(row, 1, each_val)
                    row = row + 1
                    for each_num in range(len(list1)):
                        if list1[each_num] in ['Cost Price', 'Sale Price']:
                            worksheet.write(row, each_num, list1[each_num] + "(" +
                                            self.env.user.company_id.currency_id.symbol + ")",
                                            style1)

                        elif list1[each_num] == 'Quantity':
                            worksheet.write(row, each_num, list1[each_num], style1)
                        else:
                            worksheet.write(row, each_num, list1[each_num], bold)
                    row = row + 1
                    for product_dict in vals.get(each_val):
                        worksheet.col(0).width = 4000
                        worksheet.write(row, 0, product_dict.get('default_code'))
                        worksheet.col(1).width = 6000
                        worksheet.write(row, 1, product_dict.get('name'))
                        worksheet.col(2).width = 8000
                        worksheet.write(row, 2, product_dict.get('complete_name'))
                        worksheet.write(row, 3, product_dict.get('quantity'), horz_style_pc)
                        worksheet.col(4).width = 4500
                        worksheet.write(row, 4, str('%.2f' % (product_dict.get('unit_price'))) + str(
                            self.env.user.company_id.currency_id.symbol), horz_style_pc)
                        worksheet.col(5).width = 4500
                        worksheet.write(row, 5, str('%.2f' % (product_dict.get('sell_price'))) + str(
                            self.env.user.company_id.currency_id.symbol),
                                        horz_style_pc)
                        row = row + 1
                    row = row + 1
            else:
                for each_num in range(len(list1)):
                    if list1[each_num] in ['Cost Price', 'Sale Price']:
                        worksheet.write(row, each_num, list1[each_num] + "(" +
                                        self.env.user.company_id.currency_id.symbol + ")",
                                        style1)

                    elif list1[each_num] == 'Quantity':
                        worksheet.write(row, each_num, list1[each_num], style1)
                    else:
                        worksheet.write(row, each_num, list1[each_num], bold)
                row = row + 1
                for each in vals:
                    for each_product in vals.get(each):
                        worksheet.col(0).width = 4000
                        worksheet.write(row, 0, each_product.get('default_code'))
                        worksheet.col(1).width = 6000
                        worksheet.write(row, 1, each_product.get('name'))
                        worksheet.col(2).width = 8000
                        worksheet.write(row, 2, each_product.get('complete_name'))
                        worksheet.write(row, 3, each_product.get('quantity'), horz_style_pc)
                        worksheet.col(4).width = 4500
                        worksheet.write(row, 4, str('%.2f' % (each_product.get('unit_price'))) + str(
                            self.env.user.company_id.currency_id.symbol), horz_style_pc)
                        worksheet.col(5).width = 4500
                        worksheet.write(row, 5, str('%.2f' % (each_product.get('sell_price'))) + str(
                            self.env.user.company_id.currency_id.symbol),
                                        horz_style_pc)
                        row = row + 1
            file_data = BytesIO()
            workbook.save(file_data)
            self.write({
                'data': base64.encodestring(file_data.getvalue()),
                'file_name': 'Report - %s.xls' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'state': 'done'
            })
            attachment_id = self.env['ir.attachment'].sudo().create(
                {'datas': self.data, 'name': self.file_name, 'store_fname': 'Non Moving Stock.xls'})
            if self.env.context.get('send_mail'):
                return attachment_id
            else:
                return {
                    'name': ('Non Moving Stock'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'non.moving.stock',
                    'res_id': self.id,
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                }

    def send_mail(self):
        user_ids_email_list = []
        groupobj = self.env['res.groups']
        groups_ids = ast.literal_eval(
            self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.groups_ids'))
        for each in groups_ids:
            user_ids_list = groupobj.browse(each)
            for user_line in user_ids_list.users:
                if user_line.email not in user_ids_email_list:
                    user_ids_email_list.append(user_line.email)
            attachment_id = self.print_report()
            try:
                template_id = self.env.ref('flexipharmacy.send_mail_non_moving_stock_report')
            except Exception:
                raise Warning(_("Template Not Found!!! Error"))
            template_id.email_to = ",".join(map(str, user_ids_email_list))
            template_id.attachment_ids = attachment_id
            send_mail_id = template_id.send_mail(self.id, force_send=True)
            mail_id = self.env['mail.mail'].browse(send_mail_id)
            if mail_id.state == 'sent':
                self.write({'send_mail_message': "Mail has been sent successfully!", 'state': 'sent'})
            else:
                self.write({'send_mail_message': "Error in sending mail, Please try again!", 'state': 'sent'})
            return {
                'name': ('Non Moving Stock'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'non.moving.stock',
                'res_id': self.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
            }


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    groups_ids = fields.Many2many("res.groups", string="Groups")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if get_param('flexipharmacy.groups_ids'):
            res.update(
                groups_ids=ast.literal_eval(get_param('flexipharmacy.groups_ids'))
            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('flexipharmacy.groups_ids', self.groups_ids.ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
