# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from zeep import Client
import requests
import json
    

class ResPartner(models.Model):
    _inherit = "res.partner"

    eori_number = fields.Char(string="EORI Number", help="Economic Operator Registration and Identification Number used for customs identification in EU and GB.")
        
    def _split_eori(self, eori):
        eori_country, eori_number = eori[:2].lower(), eori[2:].replace(' ', '')
        return eori_country, eori_number

    @api.constrains('eori_number')
    def validate_eori_number(self):
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company

        if company.eori_validation:
            for partner in self:
                if not partner.eori_number:
                    continue
                eori_country, eori_number = self._split_eori(partner.eori_number)

                if not self._validate_eori(eori_country, eori_number):
                    raise ValidationError(_('Please verify EORI Number.'))

    @api.model
    def _validate_eori(self, country_code, eori_number):
        #TODO: Make a format validation of eori_number.
        try:
            if country_code.upper() == 'GB' or country_code.upper() == 'XI':
                return self._validate_eori_gb(country_code.upper() + eori_number)
            else: #TODO: Check if country in EU.
                return self._validate_eori_eu(country_code.upper() + eori_number)
        except Exception:
            return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_eu(self, eori):
        # EU Validation
        client = Client('https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl')
        result = client.service.validateEORI(eori)

        if result['result'][0]['statusDescr'] == 'Valid':
            return True

        return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_gb(self, eori):
        # GB Validation     
        resp = requests.post('https://api.service.hmrc.gov.uk/customs/eori/lookup/check-multiple-eori', data=json.dumps({'eoris': [eori]}))

        if resp.status_code != 200: 
            raise ValidationError('POST /customs/eori/lookup/check-multiple-eori {}'.format(resp.status_code))

        answer = json.loads(resp.text)
        if answer[0]['valid'] == True:
            return True

        return False
