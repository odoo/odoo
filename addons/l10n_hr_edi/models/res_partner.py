import logging
import requests
from markupsafe import Markup
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

TIMEOUT = 10
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('mojeracun', 'By MojEracun')],
    )
    invoice_edi_format = fields.Selection(selection_add=[('ubl_hr', "CIUS HR"),],)
    is_using_mer = fields.Boolean(compute='_compute_is_using_mer')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends_context('allowed_company_ids')
    @api.depends('invoice_edi_format')
    def _compute_is_using_mer(self):
        mojeracun_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'mojeracun')
        for partner in self:
            partner.is_using_mer = mojeracun_user and partner.invoice_edi_format == 'ubl_hr'
            # This should work because we are only finding users for companies
            partner.company_id.l10n_hr_mojeracun_user = mojeracun_user

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_mojeracun_send_ubl_hr(self):
        if self.filtered(lambda partner: partner.invoice_edi_format != 'ubl_hr' and partner.invoice_sending_method == 'eracun'):
            raise ValidationError(_('On eRacun, only the Croatian UBL format is supported.'))

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_hr':
            return self.env['account.edi.xml.ubl_hr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_hr'] = {'countries': ['HR'], 'on_peppol': False}
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'HR':
            return 'ubl_hr'
        return super()._get_suggested_invoice_edi_format()

    # Unsupported for MojEracun?
    """@api.model
    def _check_eracun_participant_exists(self, participant_info, edi_identification):
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        if service_metadata is None:
            return False
        service_href = service_metadata.attrib.get('href', '')
        eracun_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'eracun')
        edi_mode = eracun_user and eracun_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_hr_eracun.edi.mode')
        # I can't find this value for eRacun
        # Is this the one referred to with dig +short?
        smp_eracun_url = 'http://smp-demo.nemhandel.dk' if edi_mode == 'test' else 'http://smp.nemhandel.dk'

        return edi_identification == participant_identifier and service_href.startswith(smp_eracun_url)"""

    # This doesn't really do anything as we're already checking for 'ubl_hr'?
    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        return any(document_type in parse.unquote_plus(service.attrib.get('href', '')) for service in service_references)

    def _update_mer_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        # Since the auth values aren't stored on res.partner and we don't use validation, just check this
        #if vals is None:
        #    partners = self.filtered(lambda p: all([p.mer_username, p.mer_password, p.is_using_mer]))
        #elif {'mer_username', 'mer_password', 'is_using_mer'}.intersection(vals.keys()):
        #    partners = self.filtered(lambda p: p.is_using_mer)
        partners = self.filtered(lambda p: p.is_using_mer)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_mojeracun_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                all_companies = self.env['res.company'].sudo().search([])

            for company in all_companies:
                partner.button_mojeracun_check_partner_endpoint(company=company)

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        self._update_mer_state_per_company(vals=vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_mer_state_per_company()
        return res

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    # Currently unsupported?
    """#@handle_demo
    def button_eracun_check_partner_endpoint(self, company=None):
        # A basic check for whether a participant is reachable at the given identifier_type and identifier_value
        self.ensure_one()
        if not company:
            company = self.env.company

        self_partner = self.with_company(company)
        old_value = self_partner.eracun_verification_state
        self_partner.eracun_verification_state = self._get_eracun_verification_state(self_partner.invoice_edi_format)
        if self_partner.eracun_verification_state == 'valid' and not self_partner.invoice_sending_method:
            self_partner.invoice_sending_method = 'eracun'

        self._l10n_hr_eracun_log_verification_state_update(company, old_value, self_partner.eracun_verification_state)
        return False"""
