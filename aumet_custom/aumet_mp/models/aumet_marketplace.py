# -*- coding: utf-8 -*-
import json
import requests
import posixpath
from odoo import models, fields


class AumetMarketPlace(models.Model):
    _name = 'aumet.marketplace'
    _description = 'Aumet Market Place'

    name = fields.Char(string='Name', required=True)
    base_url = fields.Char(string='URL', required=True)
    api_key = fields.Char(string='Api Key', required=True)
    description = fields.Text()

    def get_profile_info(self, company_id, token):
        headers = self.get_header(company_id)
        headers.update({"x-access-token": token})
        response = requests.get(f"{self.base_url}/v1/users/profile", headers=headers)
        return response.json()

    def get_header(self, company_id):
        return {
            'Content-Type': 'application/json',
            'x-user-lang': 'en',
            'x-api-key': self.api_key,
            'x-session-id': str(company_id),
        }

    def login(self, email, password, company_id):
        header = self.get_header(company_id)
        data = {
            'email': email,
            'password': password
        }
        url = posixpath.join(self.base_url, "v1/users/signin-password")
        response = requests.post(url, headers=header, data=json.dumps(data))
        if not response.ok:
            return False, response.json()
        cookie = 'PHPSESSID=%s' % response.cookies.get('PHPSESSID')
        json_res = response.json()
        data = json_res["data"]
        profile_info = self.get_profile_info(json_res["data"]["id"], json_res["data"]["accessToken"])
        data.update({"id": list(profile_info["data"]["entityList"].keys())[0]})
        json_res.update({"data": data})
        json_res['cookie'] = cookie
        return True, json_res

    def pull_products(self, company_id):
        header = self.get_header(company_id.id)
        header['Cookie'] = company_id.mp_cookie
        header['x-access-token'] = company_id.mp_access_token
        params = {
            'limit': 9518446744073709551615,
        }
        url = posixpath.join(self.base_url, "v1/pharmacy/products")
        response = requests.get(url, headers=header, params=params)
        response_json = response.json()
        if not response.ok:
            return False, response_json
        elif response_json.get('statusCode', 200) != 200:
            return False, response_json
        return True, response.json()

    def add_product_to_cart(self, company_id, pol):
        header = self.get_header(company_id.id)
        header['Cookie'] = company_id.mp_cookie
        header['x-access-token'] = company_id.mp_access_token
        entity_id = company_id.pharmacy_id
        supplierinfo_id = \
            pol.product_id.seller_ids.filtered(lambda seller: seller.name.id == pol.order_id.partner_id.id)[0]
        data = {
            'entityId': entity_id,
            'entityProductId': pol.mp_product_id.product_id,
            'quantity': pol.product_qty,
            'paymentMethodId': supplierinfo_id.payment_method_id.payment_method_id,
        }
        url = posixpath.join(self.base_url, "v1/pharmacy/cart/product")
        response = requests.post(url, headers=header, data=json.dumps(data))
        response_json = response.json()
        if not response.ok:
            return False, response_json
        elif response_json.get('statusCode', 200) != 200:
            return False, response_json
        return True, response.json()
