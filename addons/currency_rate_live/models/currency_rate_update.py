# -*- coding: utf-8 -*-
import json
import urllib
import xml.etree.ElementTree as ET

from openerp.addons.web.controllers.main import xml2json_from_elementtree
from openerp import api, fields, models


class CurrencyRateProvider(models.Model):
    _name = "currency.rate.provider"
    _description = "Currency Rate Provider"

    currency_ids = fields.Many2many('res.currency', string="Currencies to Update", required=True)
    company_id = fields.Many2one('res.company', string="Company")
    base_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Base Currency", required=True, readonly=True, default=1)
    server_action_id = fields.Many2one('ir.actions.server', string='Name', domain=[('model_id', '=', 'currency.rate.provider')])

    @api.multi
    def process_currency_rate_data(self, request_url, response_type, preprocess):
        self.ensure_one()
        Currency = self.env['res.currency']
        CompanyId = self.env['res.company'].search([('currency_provider_ids', '=', self.id)])
        CurrencyRate = self.env['res.currency.rate']
        parse_url = urllib.urlopen(request_url).read()
        data = []
        if response_type == 'json':
            data = json.loads(parse_url)
        elif response_type == 'xml':
            xmlstr = ET.fromstring(parse_url)
            data = xml2json_from_elementtree(xmlstr)
        for vals in preprocess(data):
            currency = Currency.search([('name', '=', vals.get('currency_code'))], limit=1)
            date = vals.get('date', fields.date.today())
            if currency:
                CurrencyRate.create({'currency_id': currency.id, 'rate': vals.get('rate'), 'name': date, 'company_id': CompanyId.id})

    def find_base_currency_rate(self, currency_code):
        currency = self.env['res.currency.rate'].search([('currency_id.name','=',currency_code)], limit=1)
        return currency.rate
