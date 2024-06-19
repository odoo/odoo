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
import base64
from requests.models import PreparedRequest
req = PreparedRequest()

class TiktokShop(models.Model):
    _name = 'tiktok.shop'
    _description = 'Tiktok Shop'

    def default_company_id(self):
        return self.env.company.id

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', 'Company', default=default_company_id, store=True)
    shop_id = fields.Char('Shop ID')
    employee_id = fields.Many2one('hr.employee','Customer Service')
    partner_id = fields.Many2one('res.partner','Seller')
    partner_invoice_id = fields.Many2one('res.partner','Pengirim')
    payment_journal_id = fields.Many2one('account.journal', 'Payment Journal')
    payment_method_id = fields.Many2one('account.payment.method', 'Payment Method')
    setting_shop_id = fields.Many2one('stock.warehouse','Warehouse')
    tiktok_token = fields.Char('Access Token')
    tiktok_refresh = fields.Char('Refresh Token')
    tiktok_code = fields.Char('Code')
    tiktok_chiper = fields.Char('Chiper')
    time_code = fields.Integer('Time Code')
    sales_fee = fields.Float('Sales Fee')
    flat_fee = fields.Float('Flat Fee')
    tiktok_commission_product_id = fields.Many2one('product.product','Tiktok Commission Product')
    fulfillment = fields.Selection([('pickup','Pick-up'),('dropoff','Drop-off')])
    start_date = fields.Datetime('Start Get Order')
    def action_authorize_shop_tiktok(self):
        print('action_authorize_shop_tiktok = = = =')
        # company = self.env.user.company_id
        company = self.env.company

        for config in company:
            if not company.tiktok_url:
                raise UserError(_('Please fill your Redirect URL to authorize shop!'))
            if not company.tiktok_client_id:
                raise UserError(_('Please fill your Apps ID to authorize shop!'))
            if not company.tiktok_client_secret:
                raise UserError(_('Please fill your Client Secret to authorize shop!'))
            if not company.tiktok_state:
                raise UserError(_('Please fill your State to authorize shop!'))

            state = str(company.tiktok_state)
            state = base64.b64encode(state.encode('utf-8',errors = 'strict'))
            # url = "https://auth.tiktok-shops.com/oauth/authorize?app_key=%s&state=%s"%(company.tiktok_client_id,state)
            url = "https://auth.tiktok-shops.com/oauth/authorize?app_key=%s&state=%s"%(company.tiktok_client_id,state)
            
            params = {}
            req.prepare_url(url, params)
            return {
                'type': 'ir.actions.act_url', 
                'url': req.url, 
                'target': 'new'
            }

    def action_get_token_tiktok(self):
        token_obj = self.env['tiktok.token']
        company = self.env.user.company_id

        for config in self:
            url = "https://auth.tiktok-shops.com/api/v2/token/get?app_key=%s&auth_code=%s&app_secret=%s&grant_type=authorized_code"%(company.tiktok_client_id,config.tiktok_code,company.tiktok_client_secret)

            res = requests.get(url)
            values = res.json()
            print(values,'VALUES TOKEN---->')

            if values.get('data',False):
                config.write({
                    'tiktok_token': values['data']['access_token'],
                    'tiktok_refresh': values['data']['refresh_token']
                })

                expires_in = values['data']['access_token_expire_in']
                token_obj.create({
                    'access_token' : values['data']['access_token'],
                    'expires_in' : datetime.fromtimestamp(expires_in),
                    'valid' : (datetime.fromtimestamp(expires_in) - datetime.now()).days,
                    'token_type' : 'Auto'
                })

    def action_get_access_token_tiktok(self):
        token_obj = self.env['tiktok.token']
        company = self.env.user.company_id

        for config in self:
            url = "https://auth.tiktok-shops.com/api/v2/token/refresh?app_key=%s&refresh_token=%s&app_secret=%s&grant_type=refresh_token"%(company.tiktok_client_id,config.tiktok_refresh,company.tiktok_client_secret)

            res = requests.get(url)
            values = res.json()

            if values.get('data',False):
                config.write({
                    'tiktok_token': values['data']['access_token'],
                    'tiktok_refresh': values['data']['refresh_token']
                })

                expires_in = values['data']['access_token_expire_in']
                token_obj.create({
                    'access_token' : values['data']['access_token'],
                    'expires_in' : datetime.fromtimestamp(expires_in),
                    'valid' : (datetime.fromtimestamp(expires_in) - datetime.now()).days,
                    'token_type' : 'Auto'
                })