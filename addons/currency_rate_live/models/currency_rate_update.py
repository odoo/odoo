# -*- coding: utf-8 -*-
from lxml import etree
import requests

from openerp.addons.web.controllers.main import xml2json_from_elementtree
from openerp import api, fields, models


class CurrencyRateProvider(models.Model):
    _name = "currency.rate.provider"
    _description = "Currency Rate Provider"

    currency_ids = fields.Many2many('res.currency', string="Currencies to Update", required=True)
    company_id = fields.Many2one('res.company', string="Company")
    base_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, string="Base Currency", required=True, readonly=True, default=1)
    server_action_id = fields.Many2one('ir.actions.server', string='Name', domain=[('model_id', '=', 'currency.rate.provider')], required=True)

    @api.multi
    def process_currency_rate_data(self, request_url, response_type, preprocess):
        self.ensure_one()
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']
        parse_url = requests.request('GET', request_url)
        data = []
        if response_type == 'json':
            data = parse_url.json()
        elif response_type == 'xml':
            xml = parse_url.content
            xmlstr = etree.fromstring(xml)
            data = xml2json_from_elementtree(xmlstr)
        for vals in preprocess(data):
            currency = Currency.search([('name', '=', vals.get('currency_code'))], limit=1)
            date = vals.get('date', fields.date.today())
            if currency:
                CurrencyRate.create({'currency_id': currency.id, 'rate': vals.get('rate'), 'name': date, 'company_id': self.company_id.id})

    def find_base_currency_rate(self, currency_code):
        currency = self.env['res.currency.rate'].search([('currency_id.name','=',currency_code)], limit=1)
        return currency.rate
