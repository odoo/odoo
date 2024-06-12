import time
import json
import requests
import hashlib
import hmac
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from requests.models import PreparedRequest
req = PreparedRequest()

class ResCompany(models.Model):
    _inherit = "res.company"

    tiktok_redirect_url = fields.Char('Tiktok Redirect URL')
    tiktok_partner_id = fields.Integer('Tiktok Partner ID')
    tiktok_partner_key = fields.Char('Tiktok Partner Key')

    tiktok_shop_ids = fields.One2many('tiktok.shop', 'company_id', 'Tiktok Shops')
    tiktok_logistic_product_id = fields.Many2one('product.product', 'Tiktok Delivery Product')
    tiktok_commission_product_id = fields.Many2one('product.product', 'Tiktok Commission Product')
    tiktok_rebate_product_id = fields.Many2one('product.product', 'Tiktok Rebate Product')
    tiktok_tax_product_id = fields.Many2one('product.product', 'Tiktok Tax Product')

    def refresh_tiktok_shop_token(self):
        company_ids = self.search([])
        for company in company_ids:
            for shop in company.tiktok_shop_ids:
                shop.tiktok_generate_refresh_token()

    def action_call_tiktok_api(self, url=None, params={}, shop=None, path=None, method='get', sign=True):
        for company in self:
            if not company.tiktok_partner_id:
                raise UserError(_('Please set your Tiktok Partner ID!'))
            if not company.tiktok_partner_key:
                raise UserError(_('Please set your Tiktok Partner Key!'))
            if not company.tiktok_shop_ids:
                raise UserError(_('No shop found! Please configure at least 1 shop to start the integration.'))
            if not path:
                raise UserError(_('Please declare your Path URL!'))

            if shop:
                tiktok_shop_id = shop.shop_id
            else:
                tiktok_shop_id = company.tiktok_shop_ids[0].shop_id

            host = "https://partner.tiktokmobile.com"
            partner_id = int(company.tiktok_partner_id)
            partner_key = company.tiktok_partner_key

            timest = int(time.time())
            access_token = shop.tiktok_access_token

            base_string = f'{partner_id}{path}{timest}'.encode()
            signature = hmac.new(partner_key.encode(), base_string, hashlib.sha256).hexdigest()

            if sign:
                base_string = f'{partner_id}{path}{timest}{access_token}{tiktok_shop_id}'.encode()
                signature = hmac.new(partner_key.encode(), base_string, hashlib.sha256).hexdigest()

            data = {
                'partner_id': partner_id,
                'shop_id': tiktok_shop_id, 
                'timestamp': int(timest),
            }

            if params:
                data.update(params)

            url = host + path

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }

            if method == 'get':
                parameters = {
                    'partner_id': partner_id,
                    'timestamp': timest,
                    'sign': signature,
                    'shop_id': tiktok_shop_id,
                    'access_token': access_token,
                }
                data.update(parameters)
                res = requests.get(url, params=data, headers=headers, verify=True)

            elif method == 'post':
                if sign:
                    url = url+'?partner_id=%s&timestamp=%s&shop_id=%s&access_token=%s&sign=%s'%(partner_id,timest,tiktok_shop_id,access_token,signature)
                res = requests.post(url, json=data, headers=headers, verify=True)

            else:
                response = {
                    'error': 'wrong method'
                }
                res = response.json()

            return res

    def action_authorize_shop_v2(self):
        for config in self:
            if not config.tiktok_redirect_url:
                raise UserError(_('Please fill your Redirect URL to authorize shop!'))
            if not config.tiktok_partner_id:
                raise UserError(_('Please fill your Partner ID to authorize shop!'))
            if not config.tiktok_partner_key:
                raise UserError(_('Please fill your Partner Key to authorize shop!'))

            host = "https://partner.tiktokmobile.com"
            path = "/api/v2/shop/auth_partner"

            timest = int(time.time())
            redirect_url = config.tiktok_redirect_url

            partner_id = int(config.tiktok_partner_id)
            partner_key = config.tiktok_partner_key

            base_string = f'{partner_id}{path}{timest}'.encode()
            sign = hmac.new(partner_key.encode(), base_string, hashlib.sha256).hexdigest()
            url = host + path + f'?partner_id={partner_id}&timestamp={timest}&sign={sign}' + f'&redirect={redirect_url}'
            params = {}

            req.prepare_url(url, params)
            
            return {
                'type': 'ir.actions.act_url', 
                'url': req.url, 
                'target': 'new'
            }