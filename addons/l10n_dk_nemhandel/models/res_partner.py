import logging
import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models, _

from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

TIMEOUT = 10
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('oioubl_21', "OIOUBL 2.1")])
    nemhandel_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not valid'),  # does not exist on Nemhandel
            ('valid', 'Valid'),
        ],
        default='not_verified',
        string='Nemhandel endpoint verification',
        copy=False,
        tracking=True,
    )

    nemhandel_identifier_type = fields.Selection(
        string="Nemhandel Endpoint Type",
        help="Unique identifier used by OIOUBL and Nemhandel",
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
        string="Nemhandel Endpoint",
        help="Code used to identify the Endpoint on Nemhandel",
        compute="_compute_nemhandel_identifier_value", store=True, readonly=False,
        tracking=True,
    )

    is_using_nemhandel = fields.Boolean(compute='_compute_is_using_nemhandel')

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'oioubl_21':
            return self.env['account.edi.xml.oioubl_21']
        return super()._get_edi_builder()

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'DK':
                partner.ubl_cii_format = 'oioubl_21'

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
            else:
                partner.nemhandel_identifier_value = ''

    @api.depends_context('allowed_company_ids')
    @api.depends('ubl_cii_format')
    def _compute_is_using_nemhandel(self):
        nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
        for partner in self:
            partner.is_using_nemhandel = nemhandel_user and partner.ubl_cii_format == 'oioubl_21'

    @api.model
    def _get_nemhandel_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        sml_zone = 'edel.sml-demo' if edi_mode == 'test' else 'edel.sml'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.dataudveksling.dk/{endpoint_participant}"
        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.debug(e)
            return None
        return etree.fromstring(response.content)

    @api.model
    def _check_nemhandel_participant_exists(self, participant_info, edi_identification):
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        if service_metadata is None:
            return False
        service_href = service_metadata.attrib.get('href', '')
        nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        smp_nemhandel_url = 'http://smp-demo.nemhandel.dk' if edi_mode == 'test' else 'http://smp.nemhandel.dk'

        return edi_identification == participant_identifier and service_href.startswith(smp_nemhandel_url)

    @handle_demo
    def button_nemhandel_check_partner_endpoint(self):
        """ A basic check for whether a participant is reachable at the given identifier_type and identifier_value
        """
        self.ensure_one()

        if not self.nemhandel_identifier_type or not self.nemhandel_identifier_value:
            self.nemhandel_verification_state = 'not_verified'
        else:
            nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
            edi_identification = f'{self.nemhandel_identifier_type}:{self.nemhandel_identifier_value}'
            resp = nemhandel_user._call_nemhandel_proxy(
                endpoint='/api/nemhandel/1/participant_exists',
                params={'edi_identification': edi_identification},
            )
            if 'code' in resp:
                # NHR PORS returned an error on this participant
                self.nemhandel_verification_state = 'not_valid'
                return False
            participant_info = self._get_nemhandel_participant_info(edi_identification)
            self.nemhandel_verification_state = 'valid' if participant_info is None or self._check_nemhandel_participant_exists(participant_info, edi_identification) else 'not_valid'
        return False
