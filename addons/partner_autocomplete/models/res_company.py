# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.iap.tools import iap_tools
from odoo import api, fields, models, modules, _
from odoo.tools import config
from odoo.tools.mail import email_domain_extract, url_domain_extract

_logger = logging.getLogger(__name__)

COMPANY_AC_TIMEOUT = 5


class ResCompany(models.Model):
    _inherit = 'res.company'

    iap_enrich_auto_done = fields.Boolean('Enrich Done')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if modules.module.current_test:
            # while running the test, mark enrichment as done
            res.sudo().iap_enrich_auto_done = True
        else:
            res.iap_enrich_auto()
        return res

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if view_type == 'form':
            for i, node in enumerate(arch.xpath("//field[@name='name' or @name='vat' or @name='duns']")):
                node.set('widget', 'field_partner_autocomplete')

        return arch, view

    def iap_enrich_auto(self):
        """ Enrich company. This method should be called by automatic processes
        and a protection is added to avoid doing enrich in a loop. """
        if self.env.user._is_system() and self.env.registry.ready:
            for company in self.filtered(lambda company: not company.iap_enrich_auto_done):
                company._enrich()
            self.iap_enrich_auto_done = True
        return True

    def _enrich(self):
        """ This method calls the partner autocomplete service from IAP to enrich
        partner related fields of the company. """
        self.ensure_one()
        _logger.info("Starting enrich of company %s (%s)", self.name, self.id)

        company_domain = self._get_company_domain()
        if not company_domain:
            return False

        company_data = self.env['res.partner'].enrich_by_domain(company_domain, timeout=COMPANY_AC_TIMEOUT)
        if not company_data or company_data.get("error"):
            return False

        company_data = {field: value for field, value in company_data.items()
                        if field in self.partner_id._fields and value and (field == 'image_1920' or not self.partner_id[field])}

        # for company: from state_id / country_id display_name like to IDs
        company_data.update(self._enrich_extract_m2o_id(company_data, ['state_id', 'country_id']))

        self.partner_id.write(company_data)
        return True

    def _enrich_extract_m2o_id(self, iap_data, m2o_fields):
        """ Extract m2O ids from data (because of res.partner._format_data_company) """
        extracted_data = {}
        for m2o_field in m2o_fields:
            relation_data = iap_data.get(m2o_field)
            if relation_data and isinstance(relation_data, dict):
                extracted_data[m2o_field] = relation_data.get('id', False)
        return extracted_data

    def _get_company_domain(self):
        """ Extract the company domain to be used by IAP services.

        The domain is extracted from the website or the email information.

        >>> company.email, company._get_company_domain()
        ("info@proximus.be", "proximus.be")
        >>> company.website, company._get_company_domain()
        ("www.info.proximus.be", "proximus.be")
        """
        self.ensure_one()

        company_domain = email_domain_extract(self.email) if self.email else False
        if company_domain and company_domain not in iap_tools._MAIL_PROVIDERS:
            return company_domain

        company_domain = url_domain_extract(self.website) if self.website else False
        if not company_domain or company_domain in ['localhost', 'example.com']:
            return False

        return company_domain
