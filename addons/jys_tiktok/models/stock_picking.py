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
    
    def print_label(self):
        context = self.env.context
        company = self.env.company
        picking_obj = self.env['stock.picking']
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())
        label_url = []
        alr_print = ''
        for pick in picking_obj.browse(context.get('active_ids')):
            sale_id = pick.sale_id
            access_token = sale_id.tiktok_shop_id.tiktok_token
            tiktok_id = sale_id.tiktok_shop_id.shop_id
            if sale_id.tiktok_package_id:
                package_id = sale_id.tiktok_package_id
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
                    alr_print += (pick.marketplace_number+' pesanan sudah dikirim.\n')
                    pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                    continue
                else:
                    alr_print += (pick.marketplace_number+' '+values.get('message','-')+'\n')
                
                if values.get('data'):
                    if values.get('data').get('doc_url'):
                        label_url.append(values.get('data').get('doc_url'))
                        pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})

            else:
                path_det = '/api/orders/detail/query'
                base_string_det = bytes("%s%sapp_key%sshop_id%stimestamp%s%s"%(key,path_det,app,tiktok_id,timest,key),'utf-8')
                sign_det = hmac.new(bytes(key,'utf-8'),base_string_det, hashlib.sha256).hexdigest()
                url = "https://open-api.tiktokglobalshop.com/api/orders/detail/query?app_key=%s&access_token=%s&timestamp=%s&shop_id=%s&sign=%s"%(app,access_token,timest,tiktok_id,sign_det)

                order_ids = [pick.marketplace_number]
                data_det = {"order_id_list": order_ids}
                res_det = requests.post(url, json=data_det)
                values_det = res_det.json()
                package_id = False
                for order in values_det.get('data').get('order_list'):
                    try:
                        package_id = order.get('package_list')[0].get('package_id',False)
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
                        alr_print += (pick.marketplace_number+' pesanan sudah dikirim.\n')
                        pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                        continue
                    else:
                        alr_print += (pick.marketplace_number+' '+values.get('message','-')+'\n')
                    
                    if values.get('data'):
                        if values.get('data').get('doc_url'):
                            label_url.append(values.get('data').get('doc_url'))
                            pick.write({'is_tiktok_printed': True,'date_print_shipped': fields.Datetime.now()})
                else:
                    continue

        pdf_writer = PyPDF2.PdfFileWriter()
        print(label_url)
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
            module_rec = self.env['sgeede.tiktok.shipping.label.pdf'].create(
                {'name': file_name, 'pdf_file': pdf_base64})
            return {'name': _('PDF File'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'sgeede.tiktok.shipping.label.pdf',
                'type': 'ir.actions.act_window',
                'target': 'new'}
        else:
            raise UserError(alr_print)