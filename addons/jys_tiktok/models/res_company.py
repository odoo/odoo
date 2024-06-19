# -*- encoding: utf-8 -*-
import time
import json
import requests
import hashlib
import hmac
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta # type: ignore
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from requests.models import PreparedRequest
from urllib.parse import urlparse, parse_qs
req = PreparedRequest()


class ResCompany(models.Model):
    _inherit = 'res.company'

    def cal_sign(self, url, secret, headers=None, body=None):
        # Parse the URL and query parameters
        parsed_url = urlparse(url)
        queries = parse_qs(parsed_url.query)
        
        # Extract all query parameters excluding 'sign' and 'access_token'
        keys = [k for k in queries if k != "sign" and k != "access_token"]
        
        # Reorder the parameters' keys in alphabetical order
        keys.sort()
        
        # Concatenate all the parameters in the format of {key}{value}
        input_str = ""
        for key in keys:
            input_str += key + ''.join(queries[key])
        
        # Append the request path
        input_str = parsed_url.path + input_str
        
        # If the request header Content-type is not multipart/form-data, append body to the end
        if headers:
            content_type = headers.get("Content-type", "")
            if content_type != "multipart/form-data" and body:
                if isinstance(body, dict):
                    body = json.dumps(body)
                input_str += body
        
        # Wrap the string generated in step 5 with the App secret
        input_str = secret + input_str + secret
        
        # Generate the HMAC-SHA256 signature
        sign = self.generate_sha256(input_str, secret)
        
        return sign

    def generate_sha256(self, input_str, secret):
        h = hmac.new(secret.encode('utf-8'), input_str.encode('utf-8'), hashlib.sha256)
        return h.hexdigest()
    
    def _get_tiktok_token(self):
        token = False
        token_obj = self.env['tiktok.token']
        for company in self:
            self.env.cr.execute("""SELECT access_token FROM tiktok_token ORDER BY id DESC LIMIT 1""")
            results = self.env.cr.fetchone()
            token = results and results[0] or False
            
        return token
    
    tiktok_api_domain = fields.Char('TikTok API Domain')
    tiktok_client_id = fields.Char('TikTok Apps Id')
    tiktok_client_secret = fields.Char('TikTok Client Secret')
    tiktok_access_token = fields.Char(compute='_get_tiktok_token', string='Access Token',store=True)
    tiktok_logistic_product_id = fields.Many2one('product.product', 'TikTok Delivery Product')
    tiktok_commission_product_id = fields.Many2one('product.product', 'Commission Product')
    tiktok_url = fields.Char('Redirect URL')
    tiktok_state = fields.Char('State', default='Indonesia')
    tiktok_shop_ids = fields.One2many('tiktok.shop', 'company_id', 'Tiktok Shops')

    def cron_generate_token_tiktok(self):
        context = {}
        company = self.env.user.company_id
        company_obj = self.env["res.company"]
        token_obj = self.env["tiktok.token"]
        log_obj = self.env['tiktok.history.api']
        # log_line_obj = self.env['tiktok.history.api.line']
        view_id = self.env.ref('jys_tiktok.view_tiktok_history_api_popup')
        current_date = datetime.today()
        
        url = "https://accounts.tiktok.com/token?grant_type=client_credentials"
        
        params = {}
        response = requests.post(url, headers=params)
        data_respon = response.json()
        
        if 'error_description' in data_respon:
            log_id = log_obj.create({
                'name': 'Get Token Access',
                'additional_info': data_respon.get('error_description'),
                
            })
            # log_line_obj.create({
            #     'name': 'Get Token Access',
            #     'log_id': log_id,
            #     'base_url': url,
            #     'params': params,
            #     'error_responses': str(data_respon),
            #     'state': 'failed'
            # })
            return {
                'name': 'API Logs',
                'type': 'ir.actions.act_window',
                'res_model': 'tiktok.history.api',
                'res_id': log_id,
                'view_mode': 'form',
                'view_id': view_id.id,
                'target': 'new'
            }
        else:
            
            expires_in = data_respon['expires_in']
            valid_on = expires_in // (24 * 3600)
            expires = current_date + relativedelta(days=valid_on)
            token_obj.create({'access_token' : data_respon['access_token'],
                             'expires_in' : expires,
                             'valid' : valid_on,
                             'token_type' : data_respon['token_type']})
            log_id = log_obj.create({
                'name': 'Get Token Access',
                'total_inserted': 1,
                'total_affected': 1,
                'total_skipped': 0,
                'affected_list': 1,
                'skipped_list': 0
            })
            log_line_obj.create({
                'name': 'Get Token Access',
                'log_id': log_id,
                'base_url': url,
                'params': params,
                'state': 'success'
            })
        
        return True
            