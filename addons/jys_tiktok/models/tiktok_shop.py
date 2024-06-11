import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp
import hmac
import hashlib
import json
import requests
from requests.models import PreparedRequest
req = PreparedRequest()

class TiktokShop(models.Model):
    _name = 'tiktok.shop'
    _description = 'Tiktok Shop'

    name = fields.Char('Name')
    shop_id = fields.Integer('Shop ID')

    def default_company_id(self):
        return self.env.company.id

    company_id = fields.Many2one('res.company', 'Company', default=default_company_id, store=True)
    payment_journal_id = fields.Many2one('account.journal', 'Payment Journal')
    payment_method_id = fields.Many2one('account.payment.method', 'Payment Method')
    boost_product_ids = fields.Many2many('product.template', string='Boost Products')

    commission = fields.Float('Commission (%)')
    max_commission = fields.Float('Max Commission/Qty')
    star_seller_commission = fields.Float('Star Seller Commission (%)')
    duty_import = fields.Float('Duty Import')
    ppn = fields.Float('PPN')

    is_include_tax = fields.Boolean('Include Tax')
    is_star_seller = fields.Boolean('Star Seller')

    tiktok_code = fields.Char(string='Code')
    tiktok_access_token = fields.Char(string='Access Token')
    tiktok_refresh_token = fields.Char(string='Refresh Token')
    
    # def create(self, vals):
    #     if vals[0]['boost_product_ids']:
    #         if vals[0]['boost_product_ids'][0][2]:
    #             if len(vals['boost_product_ids'][0][2]) > 5:
    #                 raise UserError(_('You can only have up to 5 boost products per shop!'))
    #     res = super(TiktokShop, self).create(vals)
    #     return res

    # def write(self, vals):
    #     res = super(TiktokShop, self).write(vals)
    #     for shop in self:
    #         if len(shop.boost_product_ids) > 5:
    #             raise UserError(_('You can only have up to 5 boost products per shop!'))
    #     return res

    def tiktok_generate_new_token(self):
        company = self.env.user.company_id

        for shop in self:
            timest = int(time.time())
            host = "https://partner.tiktokmobile.com"
            path = "/api/v2/auth/token/get"

            code  = shop.tiktok_code

            partner_id = int(company.tiktok_partner_id)
            partner_key = company.tiktok_partner_key

            base_string = f'{partner_id}{path}{timest}'.encode()
            sign = hmac.new(partner_key.encode(), base_string, hashlib.sha256).hexdigest()
            url = host + path + f'?partner_id={partner_id}&timestamp={timest}&sign={sign}'
          
            params = {}
            data = {
                'partner_id': partner_id,
                'code': code,
                'shop_id': shop.shop_id
            }
            data = json.dumps(data)
            headers = {}
            res = requests.post(url, data=data, headers=headers)
            values = res.json()
            
            if 'access_token' in values:
                shop.write({'tiktok_access_token': values['access_token']})
            if 'refresh_token' in values:
                shop.write({'tiktok_refresh_token': values['refresh_token']})

    def tiktok_generate_refresh_token(self):
        company = self.env.user.company_id

        for shop in self:
            timest = int(time.time())
            host = "https://partner.tiktokmobile.com"
            path = "/api/v2/auth/access_token/get"

            refresh_token = shop.tiktok_refresh_token

            partner_id = int(company.tiktok_partner_id)
            partner_key = company.tiktok_partner_key

            base_string = f'{partner_id}{path}{timest}'.encode()
            sign = hmac.new(partner_key.encode(), base_string, hashlib.sha256).hexdigest()
            url = host + path + f'?partner_id={partner_id}&timestamp={timest}&sign={sign}'
          
            params = {}
            data = {
                'partner_id': partner_id,
                'refresh_token': refresh_token,
                'shop_id': shop.shop_id
            }

            data = json.dumps(data)

            headers = {}
            res = requests.post(url, data=data, headers=headers)
            values = res.json()

            if 'access_token' in values:
                shop.write({'tiktok_access_token': values['access_token']})
            if 'refresh_token' in values:
                shop.write({'tiktok_refresh_token': values['refresh_token']})

    def action_authorize_shop_v2(self):
        company = self.env.company
        for config in company:
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