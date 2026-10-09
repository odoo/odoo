#-*- coding: utf-8 -*-

import logging
import os
import csv
import tempfile
from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime, timedelta, date
import xlrd, mmap, xlwt

_logger = logging.getLogger(__name__)

class ImportSaleOrder(models.TransientModel):
    _name = "wizard.import.sale.order"

    file_data = fields.Binary('Archive', required=True,)
    file_name = fields.Char('File Name')
    partner_id = fields.Many2one('res.partner', string='Client', required=True)


    def import_button(self):
        if not self.csv_validator(self.file_name):
            raise UserError(_("The file must be an .xls/.xlsx extension"))
        file_path = tempfile.gettempdir()+'/file.xlsx'
        data = self.file_data
        f = open(file_path,'wb')
        f.write(data.decode('base64'))
        f.close() 


        workbook = xlrd.open_workbook(file_path, on_demand = True)
        worksheet = workbook.sheet_by_index(0)
        first_row = [] # The row where we stock the name of the column
        for col in range(worksheet.ncols):
            first_row.append( worksheet.cell_value(0,col) )
        # transform the workbook to a list of dictionaries
        archive_lines = []
        for row in range(1, worksheet.nrows):
            elm = {}
            for col in range(worksheet.ncols):
                elm[first_row[col]]=worksheet.cell_value(row,col)

            archive_lines.append(elm)

        sale_order_obj = self.env['sale.order']
        product_obj = self.env['product.product']
        product_template_obj = self.env['product.template']
        sale_order_line_obj = self.env['sale.order.line']
        

            
        self.valid_columns_keys(archive_lines)
        self.valid_product_code(archive_lines, product_obj)
        self.valid_prices(archive_lines)
            
        vals = {
            'partner_id': self.partner_id.id,
            'apply_odc': False,
        }
        sale_order_id = sale_order_obj.create(vals)
        cont = 0
        for line in archive_lines:
            cont += 1
            code = str(line.get('code',"")).strip()
            product_id = product_obj.search([('default_code','=',code)])
            quantity = line.get(u'quantity',0)
            price_unit = self.get_valid_price(line.get('price',""),cont)
            product_uom = product_template_obj.search([('default_code','=',code)])
            taxes = product_id.taxes_id.filtered(lambda r: not product_id.company_id or r.company_id == product_id.company_id)
            tax_ids = taxes.ids
            if sale_order_id and product_id:
                vals = {
                    'order_id': sale_order_id.id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(quantity),
                    'price_unit': price_unit,
                    'product_uom': product_id.product_tmpl_id.uom_po_id.id,
                    'name': product_id.name,
                    'tax_id' : [(6,0,tax_ids)],
                }
                sale_order_line_obj.create(vals)
        if self._context.get('open_order', False):
            return sale_order_id.action_view_order(sale_order_id.id)
        return {'type': 'ir.actions.act_window_close'}

   

    @api.model
    def valid_prices(self, archive_lines):
        cont = 0
        for line in archive_lines:
            cont += 1
            price = line.get('price',"")
            if price != "":
                price = str(price).replace("$","").replace(",",".")
            try:
                price_float = float(price)
            except:
                raise UserError("The price of the line item %s does not have an appropriate format, for example: '100.00' - '100'"%cont)
        return True

    @api.model
    def get_valid_price(self, price, cont):
        if price != "":
            price = str(price).replace("$","").replace(",",".")
        try:
            price_float = float(price)
            return price_float
        except:
            raise UserError("The price of the line item %s does not have an appropriate format, for example: '100.00' - '100"%cont)
        return False
    
    @api.model
    def valid_product_code(self, archive_lines, product_obj):
        cont=0
        for line in archive_lines:
            cont += 1
            code = str(line.get('code',"")).strip()
            product_id = product_obj.search([('default_code','=',code)])
            if len(product_id)>1:
                raise UserError("The product code of line %s is duplicated in the system."%cont)
            if not product_id:
                raise UserError("The product code of line %s can't be found in the system."%cont)
            
    @api.model
    def valid_columns_keys(self, archive_lines):
        columns = archive_lines[0].keys()
        print "columns>>",columns
        text = "The file must contain the following columns: code, quantity, and price. \n The following columns are not in the file:"; text2 = text
        if not 'code' in columns:
            text +="\n[ code ]"
        if not u'quantity' in columns:
            text +="\n[ quantity ]"
        if not 'price' in columns:
            text +="\n[ price ]"
        if text !=text2:
            raise UserError(text)
        return True
            
    @api.model
    def csv_validator(self, xml_name):
        name, extension = os.path.splitext(xml_name)
        return True if extension == '.xls' or extension == '.xlsx' else False



class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_view_order(self,sale_order_id):
        action = self.env.ref('sale.action_quotations').read()[0]
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = sale_order_id

        return action 

