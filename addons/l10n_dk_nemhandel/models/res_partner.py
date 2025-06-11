import logging
import requests
from markupsafe import Markup
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

TIMEOUT = 10
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('nemhandel', 'By Nemhandel')],
    )
    invoice_edi_format = fields.Selection(selection_add=[('oioubl_21', "OIOUBL 2.1")])
    nemhandel_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not on Nemhandel'),  # Is not on Nemhandel
            ('valid', 'Valid'),
        ],
        string='Nemhandel endpoint verification',
        company_dependent=True,
    )

    nemhandel_identifier_type = fields.Selection(
        string='Nemhandel Endpoint Type',
        help='Unique identifier used by OIOUBL and Nemhandel',
        compute="_compute_nemhandel_identifier_type", store=True, readonly=False,
        tracking=True,
        selection=[
            ('0088', "EAN/GLN"),
            ('0184', "CVR"),
            ('9918', "IBAN"),
            ('0198', "SE"),
        ],
    )
    nemhandel_identifier_value = fields.Char(
        string='Nemhandel Endpoint',
        help='Code used to identify the Endpoint on Nemhandel',
        compute="_compute_nemhandel_identifier_value", store=True, readonly=False,
        tracking=True,
    )

    is_using_nemhandel = fields.Boolean(compute='_compute_is_using_nemhandel')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('country_code', 'vat', 'company_registry')
    def _compute_nemhandel_identifier_type(self):
        for partner in self:
            partner.nemhandel_identifier_type = partner.nemhandel_identifier_type
            country_code = partner._deduce_country_code()
            if country_code == 'DK' and not partner.nemhandel_identifier_type:
                partner.nemhandel_identifier_type = '0184'
            elif country_code != 'DK':
                partner.nemhandel_identifier_type = ''

    @api.depends('country_code', 'vat', 'company_registry', 'nemhandel_identifier_type')
    def _compute_nemhandel_identifier_value(self):
        for partner in self:
            if partner.nemhandel_identifier_value != partner._origin.nemhandel_identifier_value:
                # value changed, don't override it
                partner.nemhandel_identifier_value = partner.nemhandel_identifier_value
                continue
            country_code = partner._deduce_country_code()
            if country_code == 'DK' and partner.nemhandel_identifier_type == '0184':
                partner.nemhandel_identifier_value = partner.company_registry
            elif country_code == 'DK':
                partner.nemhandel_identifier_value = partner.nemhandel_identifier_value
            else:
                partner.nemhandel_identifier_value = ''

    @api.depends_context('allowed_company_ids')
    @api.depends('invoice_edi_format')
    def _compute_is_using_nemhandel(self):
        nemhandel_user = self.env.company.sudo().nemhandel_edi_user
        for partner in self:
            partner.is_using_nemhandel = nemhandel_user and partner.invoice_edi_format == 'oioubl_21'

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_nemhandel_send_oioubl(self):
        if self.filtered(lambda partner: partner.invoice_edi_format != 'oioubl_21' and partner.invoice_sending_method == 'nemhandel'):
            raise ValidationError(_('On Nemhandel, only OIOUBL 2.1 is supported.'))

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'oioubl_21':
            return self.env['account.edi.xml.oioubl_21']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['oioubl_21'] = {'countries': ['DK'], 'on_peppol': False}
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'DK':
            return 'oioubl_21'
        return super()._get_suggested_invoice_edi_format()

    @api.model
    def _get_nemhandel_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        nemhandel_user = self.env.company.sudo().nemhandel_edi_user
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        sml_zone = 'edel.sml-demo' if edi_mode == 'test' else 'edel.sml'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.dataudveksling.dk/{endpoint_participant}"
        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.info(e)
            return None
        return response.content

    def _l10n_dk_nemhandel_log_verification_state_update(self, company, old_value, new_value):
        # log the update of the nemhandel verification state
        # we do this instead of regular tracking because of the customized message
        # and because we want to log the change for every company in the db
        if old_value == new_value:
            return

        nemhandel_verification_state_field = self._fields['nemhandel_verification_state']
        selection_values = dict(nemhandel_verification_state_field.selection)
        old_label = selection_values[old_value] if old_value else False  # get translated labels
        new_label = selection_values[new_value] if new_value else False

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
            field=nemhandel_verification_state_field.string,
            company=company.display_name,
        )
        self._message_log(body=body)

    @api.model
    def _check_nemhandel_participant_exists(self, participant_info, edi_identification):
        participant_info = etree.fromstring(participant_info)
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        if service_metadata is None:
            return False
        service_href = service_metadata.attrib.get('href', '')
        nemhandel_user = self.env.company.sudo().nemhandel_edi_user
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        smp_nemhandel_url = 'http://smp-demo.nemhandel.dk' if edi_mode == 'test' else 'http://smp.nemhandel.dk'

        return edi_identification == participant_identifier and service_href.startswith(smp_nemhandel_url)

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        return any(document_type in parse.unquote_plus(service.attrib.get('href', '')) for service in service_references)

    def _update_nemhandel_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        if vals is None:
            partners = self.filtered(lambda p: all([p.nemhandel_identifier_type, p.nemhandel_identifier_value, p.is_using_nemhandel]))
        elif {'nemhandel_identifier_type', 'nemhandel_identifier_value', 'is_using_nemhandel'}.intersection(vals.keys()):
            partners = self.filtered(lambda p: p.is_using_nemhandel)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_nemhandel_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                all_companies = self.env['res.company'].sudo().search([])

            for company in all_companies:
                partner.button_nemhandel_check_partner_endpoint(company=company)

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        self._update_nemhandel_state_per_company(vals=vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_nemhandel_state_per_company()
        return res

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    @handle_demo
    def button_nemhandel_check_partner_endpoint(self, company=None):
        """ A basic check for whether a participant is reachable at the given identifier_type and identifier_value
        """
        self.ensure_one()
        if not company:
            company = self.env.company

        self_partner = self.with_company(company)
        old_value = self_partner.nemhandel_verification_state
        self_partner.nemhandel_verification_state = self._get_nemhandel_verification_state(self_partner.invoice_edi_format)
        if self_partner.nemhandel_verification_state == 'valid' and not self_partner.invoice_sending_method:
            self_partner.invoice_sending_method = 'nemhandel'

        self._l10n_dk_nemhandel_log_verification_state_update(company, old_value, self_partner.nemhandel_verification_state)
        return False

    @handle_demo
    def _get_nemhandel_verification_state(self, invoice_edi_format):
        self.ensure_one()
        if not self.nemhandel_identifier_type or not self.nemhandel_identifier_value or invoice_edi_format != 'oioubl_21':
            return 'not_verified'

        edi_identification = f"{self.nemhandel_identifier_type}:{self.nemhandel_identifier_value}".lower()
        participant_info = self._get_nemhandel_participant_info(edi_identification)
        if participant_info is None:
            return 'not_valid'

        is_participant_on_network = self._check_nemhandel_participant_exists(participant_info, edi_identification)
        return 'valid' if is_participant_on_network else 'not_valid'
