# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_mp = fields.Boolean(string="Aumet Marketplace")
    market_place_id = fields.Many2one('aumet.marketplace', string='Market Place')
    mp_email = fields.Char(string='MP Email')
    mp_password = fields.Char(string='MP Password')

    pharmacy_id = fields.Integer(string='Pharmacy ID', readonly=True)
    pharmacy_name = fields.Char(string='Pharmacy Name', readonly=True)

    mp_access_token = fields.Text(string='Access Token', readonly=True)
    mp_cookie = fields.Char(string='Cookie', readonly=True)

    def write(self, vals):
        for company in self:
            if 'market_place_id' in vals or 'mp_email' in vals or 'mp_password' in vals:
                result, response = company.mp_login(vals['mp_email'], vals['mp_password'], vals['market_place_id'])
                if not result:
                    raise api.UserError(response.get('message', 'Invalid user credentials'))
            super(ResCompany, company).write(vals)

    def mp_login(self, email=None, password=None, market_place_id=None):
        if not market_place_id:
            if not self.market_place_id:
                raise api.UserError("Marketplace should be provided to login!")
            market_place_id = self.market_place_id
        else:
            market_place_id = self.env['aumet.marketplace'].browse(market_place_id)

        if not email:
            email = self.mp_email
        if not password:
            password = self.mp_password
        result, response = market_place_id.login(email, password, self.id)
        if not result:
            return False, response
        self.mp_cookie = response['cookie']
        self.mp_access_token = response['data']['accessToken']
        self.pharmacy_id = response['data']['id']
        self.pharmacy_name = response['data']['fullName']
        return True, response

    def _mp_pull_products(self):
        companies = self.search([('is_mp', '=', True)])
        for company in companies:
            result, login_response = company.mp_login()
            if not result:
                raise api.UserError(login_response.get('message', 'Login Error'))
            result, response = company.market_place_id.pull_products(company)
            if not result:
                raise api.UserError(response.get('message', 'Error while updating products!'))
            company.env['marketplace.product'].create_from_marketplace(response['data']['data'])

    def add_product_to_cart(self, pol):
        result, login_response = self.mp_login()
        if not result:
            raise api.UserError(login_response.get('message', 'Login Error'))
        result, response = self.market_place_id.add_product_to_cart(self, pol)
        if not result:
            return False, response
        return True, response
