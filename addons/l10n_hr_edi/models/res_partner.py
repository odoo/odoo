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
        selection_add=[('eracun', 'By eRacun')],
    )
    invoice_edi_format = fields.Selection(selection_add=[('ubl_hr', "CIUS HR"),],)
    eracun_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not on eRacun'),
            ('valid', 'Valid'),
        ],
        string='eRacun endpoint verification',
        company_dependent=True,
    )

    eracun_identifier_type = fields.Selection(
        string='eRacun Endpoint Type',
        help='Identifier used by eRacun',
        compute="_compute_eracun_identifier_type", store=True, readonly=False,
        tracking=True,
        selection=[
            ('0088', "EAN/GLN"),
            ('9934', "OIN"),
        ],
    )
    eracun_identifier_value = fields.Char(
        string='eRacun Endpoint',
        help='Code used to identify the Endpoint on eRacun',
        compute="_compute_eracun_identifier_value", store=True, readonly=False,
        tracking=True,
    )

    is_using_eracun = fields.Boolean(compute='_compute_is_using_eracun')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('country_code', 'vat', 'company_registry')
    def _compute_eracun_identifier_type(self):
        for partner in self:
            partner.eracun_identifier_type = partner.eracun_identifier_type
            country_code = partner._deduce_country_code()
            if country_code == 'HR' and not partner.eracun_identifier_type:
                partner.eracun_identifier_type = '9934'
            elif country_code != 'HR':
                partner.eracun_identifier_type = ''

    @api.depends('country_code', 'vat', 'company_registry', 'eracun_identifier_type')
    def _compute_eracun_identifier_value(self):
        for partner in self:
            if partner.eracun_identifier_value != partner._origin.eracun_identifier_value:
                # value changed, don't override it
                partner.eracun_identifier_value = partner.eracun_identifier_value
                continue
            country_code = partner._deduce_country_code()
            if country_code == 'HR' and partner.eracun_identifier_type == '9934': # Check this being company registry
                partner.eracun_identifier_value = partner.company_registry
            elif country_code == 'HR':
                partner.eracun_identifier_value = partner.eracun_identifier_value
            else:
                partner.eracun_identifier_value = ''

    @api.depends_context('allowed_company_ids')
    @api.depends('invoice_edi_format')
    def _compute_is_using_eracun(self):
        eracun_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'eracun')
        for partner in self:
            partner.is_using_eracun = eracun_user and partner.invoice_edi_format == 'ubl_hr'

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_eracun_send_ubl_hr(self):
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

    @api.model
    def _get_eracun_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        eracun_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'eracun')
        edi_mode = eracun_user and eracun_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_hr_eracun.edi.mode')
        sml_zone = '.demo' if edi_mode == 'test' else ''
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis{sml_zone}.ams.porezna-uprava.hr/{endpoint_participant}"
        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.info(e)
            return None
        return etree.fromstring(response.content)

    def _l10n_hr_eracun_log_verification_state_update(self, company, old_value, new_value):
        # log the update of the eRacun verification state
        # we do this instead of regular tracking because of the customized message
        # and because we want to log the change for every company in the db
        if old_value == new_value:
            return

        eracun_verification_state_field = self._fields['eracun_verification_state']
        selection_values = dict(eracun_verification_state_field.selection)
        old_label = selection_values[old_value] if old_value else False  # get translated labels
        new_label = selection_values[new_value] if new_value else False

        # Is this the same for HR, just with different values filled?
        body = Markup("""
            <ul>
                <li>
                    <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old}</span>
                    <i class='o-mail-Message-trackingSeparator fa fa-long-arrow-right mx-1 text-600'/>
                    <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new}</span>
                    <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({field})</span>
                    <span class='o-mail-Message-trackingCompany ms-1 fst-italic text-muted'>({company})</span>
                </li>
            </ul>
        """).format(
            old=old_label,
            new=new_label,
            field=eracun_verification_state_field.string,
            company=company.display_name,
        )
        self._message_log(body=body)

    @api.model
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

        return edi_identification == participant_identifier and service_href.startswith(smp_eracun_url)

    # This doesn't really do anything as we're already checking for 'ubl_hr'?
    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        return any(document_type in parse.unquote_plus(service.attrib.get('href', '')) for service in service_references)

    def _update_eracun_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        if vals is None:
            partners = self.filtered(lambda p: all([p.eracun_identifier_type, p.eracun_identifier_value, p.is_using_eracun]))
        elif {'eracun_identifier_type', 'eracun_identifier_value', 'is_using_eracun'}.intersection(vals.keys()):
            partners = self.filtered(lambda p: p.is_using_eracun)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_eracun_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                all_companies = self.env['res.company'].sudo().search([])

            for company in all_companies:
                partner.button_eracun_check_partner_endpoint(company=company)

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        self._update_eracun_state_per_company(vals=vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_eracun_state_per_company()
        return res

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    #@handle_demo
    def button_eracun_check_partner_endpoint(self, company=None):
        """ A basic check for whether a participant is reachable at the given identifier_type and identifier_value
        """
        self.ensure_one()
        if not company:
            company = self.env.company

        self_partner = self.with_company(company)
        old_value = self_partner.eracun_verification_state
        self_partner.eracun_verification_state = self._get_eracun_verification_state(self_partner.invoice_edi_format)
        if self_partner.eracun_verification_state == 'valid' and not self_partner.invoice_sending_method:
            self_partner.invoice_sending_method = 'eracun'

        self._l10n_hr_eracun_log_verification_state_update(company, old_value, self_partner.eracun_verification_state)
        return False

    #@handle_demo
    def _get_eracun_verification_state(self, invoice_edi_format):
        self.ensure_one()
        if not self.eracun_identifier_type or not self.eracun_identifier_value or invoice_edi_format != 'ubl_hr':
            return 'not_verified'

        edi_identification = f"{self.eracun_identifier_type}:{self.eracun_identifier_value}".lower()
        participant_info = self._get_eracun_participant_info(edi_identification)
        if participant_info is None:
            return 'not_valid'

        is_participant_on_network = self._check_eracun_participant_exists(participant_info, edi_identification)
        return 'valid' if is_participant_on_network else 'not_valid'
