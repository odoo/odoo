import time
import json
import requests
import hashlib
import hmac
import PyPDF2 # type: ignore
import io
import base64
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse # type: ignore

class StockPicking(models.Model):
    _inherit = "stock.picking"

    carrier_tracking_ref = fields.Char('Tracking')
    is_tiktok_printed = fields.Boolean('Tiktok')
    date_print_shipped = fields.Datetime('Print Shipped')
    tiktok_ordersn = fields.Char('Number', compute='_get_tiktok_ordersn', store=True)

    @api.depends('sale_id')
    def _get_tiktok_ordersn(self):
        for stock in self:
            marketplace_number = ''
            if stock.sale_id:
                if stock.sale_id.tiktok_shop_id:
                    marketplace_number = stock.sale_id.tiktok_ordersn

            stock.tiktok_ordersn = marketplace_number

    def print_label(self):
        context = self.env.context
        company = self.env.company
        picking_obj = self.env['stock.picking']
        company_obj = self.env['res.company']
        app = company.tiktok_client_id
        domain = company.tiktok_api_domain
        key = company.tiktok_client_secret
        data = self
        
        if not data.sale_id.tiktok_shop_id:
            raise UserError(_('Please select your shop!'))
        shop = data.sale_id.tiktok_shop_id
        chiper = str(shop.tiktok_chiper)
        timest = int(time.time())
        label_url = [] 
               
        alr_print = ''
        sign = ''
        for pick in picking_obj.browse(context.get('active_ids')):
            sale_id = pick.sale_id
            access_token = sale_id.tiktok_shop_id.tiktok_token
            headers = {
                'x-tts-access-token': str(access_token), 
                "Content-type": "application/json"
            }
            tiktok_id = sale_id.tiktok_shop_id.shop_id
            if sale_id.tiktok_package_id:
                package_id = sale_id.tiktok_package_id
                doc_type = 'SHIPPING_LABEL'
                url =  domain+f"/fulfillment/202309/packages/{package_id}/shipping_documents"+"?app_key=%s&access_token=%s&sign=%s&shop_cipher=%s&timestamp=%s&document_type=%s"%(app,access_token,sign,chiper,timest,doc_type)
                sign = company_obj.cal_sign(url, key, headers)
                url =  domain+f"/fulfillment/202309/packages/{package_id}/shipping_documents"+"?app_key=%s&access_token=%s&sign=%s&shop_cipher=%s&timestamp=%s&document_type=%s"%(app,access_token,sign,chiper,timest,doc_type)
                res = requests.get(url, headers=headers)
                values = res.json()
                if values.get('message',False) == 'Package shipped, no need to print.':
                    alr_print += (sale_id.tiktok_ordersn+' pesanan sudah dikirim.\n')
                    pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                    continue
                else:
                    alr_print += (sale_id.tiktok_ordersn+' '+values.get('message','-')+'\n')
                
                if values.get('data'):
                    if values.get('data').get('doc_url'):
                        label_url.append(values.get('data').get('doc_url'))
                        pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})

            else:
                order_ids = [sale_id.tiktok_ordersn]
                url = domain+"/order/202309/orders?app_key=%s&access_token=%s&timestamp=%s&sign=%s&shop_cipher=%s&ids=%s"%(app,access_token,timest,sign,chiper,','.join(order_ids))
                sign = company_obj.cal_sign(url, key, headers)
                url = domain+"/order/202309/orders?app_key=%s&access_token=%s&timestamp=%s&sign=%s&shop_cipher=%s&ids=%s"%(app,access_token,timest,sign,chiper,','.join(order_ids))
        
                res = requests.get(url, headers=headers)
                values_det = res.json()
                package_id = False
                for order in values_det.get('data').get('orders'):
                    try:
                        package_id = order.get('packages')[0].get('id',False)
                    except:
                        package_id = False

                if package_id:
                    doc_type = 3
                    doc_size = 0

                    path = '/api/fulfillment/shipping_document'
                    strings = f'{key}{path}app_key{app}document_size{doc_size}document_type{doc_type}package_id{package_id}shop_id{tiktok_id}timestamp{timest}{key}'
                    #base_string = bytes("%s%sapp_key%stimestamp%s%s"%(key,path,app,timest,key),'utf-8')
                    base_string = bytes(strings,'utf-8')
                    sign = hmac.new(bytes(key,'utf-8'),base_string, hashlib.sha256).hexdigest()
                    url = "https://open-api.tiktokglobalshop.com/api/fulfillment/shipping_document?app_key=%s&access_token=%s&sign=%s&timestamp=%s"%(app,access_token,sign,timest)
                    url2 = f'&shop_id={tiktok_id}&package_id={package_id}&document_type={doc_type}&document_size={doc_size}'

                    url = url + url2
                    data = {'shop_id': tiktok_id,
                            'package_id': package_id,
                            'document_type': 3,
                            'document_size': 0}
                    res = requests.get(url)
                    values = res.json()
                    if values.get('message',False) == 'Package shipped, no need to print.':
                        alr_print += (str(pick.tiktok_ordersn)+' pesanan sudah dikirim.\n')
                        pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                        continue
                    else:
                        alr_print += (str(pick.tiktok_ordersn)+' '+values.get('message','-')+'\n')
                    
                    if values.get('data'):
                        if values.get('data').get('doc_url'):
                            label_url.append(values.get('data').get('doc_url'))
                            pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                else:
                    continue

        pdf_writer = PyPDF2.PdfFileWriter()
        if label_url:
            for url in label_url:
              response = requests.get(url)
              pdf = PyPDF2.PdfFileReader(io.BytesIO(response.content))
              for page_num in range(pdf.getNumPages()):
                page = pdf.getPage(page_num)
                pdf_writer.addPage(page)

            pdf_bytes = io.BytesIO()
            pdf_writer.write(pdf_bytes)
            pdf_bytes.seek(0)

            pdf_binary = pdf_bytes.getvalue()
            pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
            file_name = 'TikTok-'+(datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H_%M_%S')+'.pdf'
            module_rec = self.env['tiktok.shipping.label.pdf'].create(
                {'name': file_name, 'pdf_file': pdf_base64})
            return {'name': _('PDF File'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'tiktok.shipping.label.pdf',
                'type': 'ir.actions.act_window',
                'target': 'new'}
        else:
            raise UserError(alr_print)