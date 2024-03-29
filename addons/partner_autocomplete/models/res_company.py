# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import threading

from odoo.addons.iap.tools import iap_tools
from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)

COMPANY_AC_TIMEOUT = 5


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    partner_gid = fields.Integer('Company database ID', related="partner_id.partner_gid", inverse="_inverse_partner_gid", store=True)
    iap_enrich_auto_done = fields.Boolean('Enrich Done')

    def _inverse_partner_gid(self):
        for company in self:
            company.partner_id.partner_gid = company.partner_gid

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not getattr(threading.current_thread(), 'testing', False):
            res.iap_enrich_auto()
        return res

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if view_type == 'form':
            for node in arch.xpath(
                "//field[@name='name']"
                "|//field[@name='vat']"
            ):
                node.attrib['widget'] = 'field_partner_autocomplete'

        return arch, view

    def iap_enrich_auto(self):
        """ Enrich company. This method should be called by automatic processes
        and a protection is added to avoid doing enrich in a loop. """
        if self.env.user._is_system():
            for company in self.filtered(lambda company: not company.iap_enrich_auto_done):
                company._enrich()
            self.iap_enrich_auto_done = True
        return True

    def _enrich(self):
        """ This method calls the partner autocomplete service from IAP to enrich
        partner related fields of the company.

        :return bool: either done, either failed """
        self.ensure_one()
        _logger.info("Starting enrich of company %s (%s)", self.name, self.id)

        company_domain = self._get_company_domain()
        if not company_domain:
            return False

        company_data = self.env['res.partner'].enrich_company(company_domain, False, self.vat, timeout=COMPANY_AC_TIMEOUT)
        if company_data.get('error'):
            return False
        additional_data = company_data.pop('additional_info', False)

        # Keep only truthy values that are not already set on the target partner
        # Erase image_1920 even if something is in it. Indeed as partner_autocomplete is probably installed as a
        # core app (mail -> iap -> partner_autocomplete auto install chain) it is unlikely that people already
        # updated their company logo.
        self.env['res.partner']._iap_replace_logo(company_data)
        company_data = {field: value for field, value in company_data.items()
                        if field in self.partner_id._fields and value and (field == 'image_1920' or not self.partner_id[field])}

        # for company and childs: from state_id / country_id display_name like to IDs
        company_data.update(self._enrich_extract_m2o_id(company_data, ['state_id', 'country_id']))
        if company_data.get('child_ids'):
            company_data['child_ids'] = [
                dict(child_data, **self._enrich_extract_m2o_id(child_data, ['state_id', 'country_id']))
                for child_data in company_data['child_ids']
            ]

        # handle o2m values, e.g. {'bank_ids': ['acc_number': 'BE012012012', 'acc_holder_name': 'MyWebsite']}
        self._enrich_replace_o2m_creation(company_data)

        self.partner_id.write(company_data)

        if additional_data:
            template_values = json.loads(additional_data)
            template_values['flavor_text'] = _("Company auto-completed by Odoo Partner Autocomplete Service")
            self.partner_id.message_post_with_source(
                'iap_mail.enrich_company',
                render_values=template_values,
                subtype_xmlid='mail.mt_note',
            )
        return True

    def _enrich_extract_m2o_id(self, iap_data, m2o_fields):
        """ Extract m2O ids from data (because of res.partner._format_data_company) """
        extracted_data = {}
        for m2o_field in m2o_fields:
            relation_data = iap_data.get(m2o_field)
            if relation_data and isinstance(relation_data, dict):
                extracted_data[m2o_field] = relation_data.get('id', False)
        return extracted_data

    def _enrich_replace_o2m_creation(self, iap_data):
        for o2m_field, values in iap_data.items():
            if isinstance(values, list):
                commands = [(
                    0, 0, create_value
                ) for create_value in values if isinstance(create_value, dict)]
                if commands:
                    iap_data[o2m_field] = commands
                else:
                    iap_data.pop(o2m_field, None)
        return iap_data

    def _get_company_domain(self):
        """ Extract the company domain to be used by IAP services.
        The domain is extracted from the website or the email information.
        e.g:
            - www.info.proximus.be -> proximus.be
            - info@proximus.be -> proximus.be """
        self.ensure_one()

        company_domain = tools.email_domain_extract(self.email) if self.email else False
        if company_domain and company_domain not in iap_tools._MAIL_DOMAIN_BLACKLIST:
            return company_domain

        company_domain = tools.url_domain_extract(self.website) if self.website else False
        if not company_domain or company_domain in ['localhost', 'example.com']:
            return False

        return company_domain
