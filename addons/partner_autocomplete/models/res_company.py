import logging

from odoo import api, fields, models, modules
from odoo.tools.mail import email_domain_extract, url_domain_extract

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)
COMPANY_AC_TIMEOUT = 5
ENRICH_ALLOWED_FIELDS = {
    "name",
    "website",
    "email",
    "phone",
    "street",
    "street2",
    "city",
    "zip",
    "state_id",
    "country_id",
    "primary_industry_id",
    "lang",
    "image_1920",
}


class ResCompany(models.Model):
    _inherit = "res.company"

    partner_autocomplete_config_id = fields.Many2one(
        comodel_name="partner_autocomplete.config",
        compute="_compute_partner_autocomplete_config_id",
        search="_search_partner_autocomplete_config_id",
    )
    iap_enrich_auto_done = fields.Boolean(
        related="partner_autocomplete_config_id.iap_enrich_auto_done",
    )

    def _search_partner_autocomplete_config_id(self, operator, value):
        return self._search_config_link("partner_autocomplete.config", operator, value)

    def _compute_partner_autocomplete_config_id(self):
        configs = self.env["partner_autocomplete.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.partner_autocomplete_config_id = by_company.get(company.id, False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if modules.module.current_test:
            # Skip enrichment in tests so no IAP request is ever issued.
            res.sudo().partner_autocomplete_config_id.iap_enrich_auto_done = True
        else:
            res.iap_enrich_auto()
        return res

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if view_type == "form":
            for node in arch.xpath(
                "//field[@name='name' or @name='vat' or @name='duns']"
            ):
                node.set("widget", "field_partner_autocomplete")

        return arch, view

    def iap_enrich_auto(self):
        """Enrich company. This method should be called by automatic processes
        and a protection is added to avoid doing enrich in a loop."""
        if self.env.user._is_system() and self.env.registry.ready:
            for company in self.filtered(
                lambda company: (
                    not company.partner_autocomplete_config_id.iap_enrich_auto_done
                )
            ):
                if company._enrich():
                    company.partner_autocomplete_config_id.iap_enrich_auto_done = True
        return True

    def _enrich(self):
        """This method calls the partner autocomplete service from IAP to enrich
        partner related fields of the company."""
        self.check_singleton()
        _logger.info("Starting enrich of company %s (%s)", self.name, self.id)

        company_domain = self._get_company_domain_name()
        if not company_domain:
            return False

        company_data = self.env["res.partner"].enrich_by_domain(
            company_domain, timeout=COMPANY_AC_TIMEOUT
        )
        if not company_data or company_data.get("error"):
            return False

        company_data = {
            field: value
            for field, value in company_data.items()
            if field in ENRICH_ALLOWED_FIELDS
            and field in self.partner_id._fields
            and value
            and not self.partner_id[field]
        }

        # for company: from state_id / country_id display_name like to IDs
        company_data.update(
            self._enrich_extract_m2o_id(company_data, ["state_id", "country_id"])
        )

        self.partner_id.write(company_data)
        return True

    def _enrich_extract_m2o_id(self, iap_data, m2o_fields):
        """Extract m2O ids from data (because of res.partner._format_data_company)"""
        extracted_data = {}
        for m2o_field in m2o_fields:
            relation_data = iap_data.get(m2o_field)
            if relation_data and isinstance(relation_data, dict):
                extracted_data[m2o_field] = relation_data.get("id", False)
        return extracted_data

    def _get_company_domain_name(self):
        """Extract the company domain to be used by IAP services.

        The domain is extracted from the website or the email information.

        >>> company.email, company._get_company_domain_name()
        ("info@proximus.be", "proximus.be")
        >>> company.website, company._get_company_domain_name()
        ("https://www.info.proximus.be", "proximus.be")
        """
        self.check_singleton()

        company_domain = email_domain_extract(self.email) if self.email else False
        if company_domain and company_domain not in iap_tools._MAIL_PROVIDERS:
            return company_domain

        company_domain = url_domain_extract(self.website) if self.website else False
        if not company_domain or company_domain in ["localhost", "example.com"]:
            return False

        return company_domain
