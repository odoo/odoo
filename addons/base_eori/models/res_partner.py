# -*- coding: utf-8 -*-
# Copyright 2019-2021 XCLUDE AB (http://www.xclude.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# @author Daniel Stenlöv <info@xclude.se>

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
import requests
import json
from lxml import etree


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
        try:
            if country_code.upper() == 'GB':
                return self._validate_eori_gb(country_code.upper() + eori_number)
            else:
                return self._validate_eori_eu(country_code.upper() + eori_number)
        except Exception:
            # IDEA: Could add fallback method if error from service is returned.
            return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_eu(self, eori):
        # EU Validation
        url = 'https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl'
        body = '<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><ev:validateEORI xmlns:ev="http://eori.ws.eos.dds.s/"><ev:eori>{}</ev:eori></ev:validateEORI></soap:Body></soap:Envelope>'.format(eori)

        resp = requests.post(url, data=body)

        if resp.status_code != 200: 
            raise ValidationError('POST /taxation_customs/dds2/eos/validation/services/validation?wsdl {}'.format(resp.status_code))

        tree = etree.fromstring((resp.text).replace("<?xml version='1.0' encoding='UTF-8'?>", ""))
        if tree.findtext('.//statusDescr') == 'Valid':
            return True

        return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_gb(self, eori):
        # GB Validation
        url = 'https://api.service.hmrc.gov.uk/customs/eori/lookup/check-multiple-eori'        
        task = "{{'eoris': [{}]}}".format(eori)

        resp = requests.post(url, json=task)
        if resp.status_code != 200: 
            raise ValidationError('POST /customs/eori/lookup/check-multiple-eori {}'.format(resp.status_code))

        answer = json.loads(resp.text)
        if anser[0]['valid'] == True:
            return True

        return False
