# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

TIMEOUT = 10

class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_peppol_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not valid'),  # does not exist on Peppol at all
            ('not_valid_format', 'Cannot receive this format'),  # registered on Peppol but cannot receive the selected document type
            ('valid', 'Valid'),
        ],
        string='Peppol endpoint validity',
        compute='_compute_account_peppol_verification_state',
    )
    is_peppol_edi_format = fields.Boolean(compute='_compute_is_peppol_edi_format')

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _get_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        peppol_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'peppol')
        edi_mode = peppol_user and peppol_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('account_peppol.edi.mode')
        sml_zone = 'acc.edelivery' if edi_mode == 'test' else 'edelivery'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.tech.ec.europa.eu/{endpoint_participant}"

        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
        except requests.exceptions.ConnectionError:
            return None
        if response.status_code != 200:
            return None
        return etree.fromstring(response.content)

    @api.model
    def _check_peppol_participant_exists(self, participant_info, edi_identification, check_company=False):
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        service_href = ''
        if service_metadata is not None:
            service_href = service_metadata.attrib.get('href', '')

        if edi_identification != participant_identifier or 'hermes-belgium' in service_href:
            # all Belgian companies are pre-registered on hermes-belgium, so they will
            # technically have an existing SMP url but they are not real Peppol participants
            return False

        if check_company:
            # if we are only checking company's existence on the network, we don't care about what documents they can receive
            if not service_href:
                return True

            access_point_contact = True
            with contextlib.suppress(requests.exceptions.RequestException, etree.XMLSyntaxError):
                response = requests.get(service_href, timeout=TIMEOUT)
                if response.status_code == 200:
                    access_point_info = etree.fromstring(response.content)
                    access_point_contact = access_point_info.findtext('.//{*}TechnicalContactUrl') or access_point_info.findtext('.//{*}TechnicalInformationUrl')
            return access_point_contact

        return True

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        for service in service_references:
            if document_type in parse.unquote_plus(service.get('href', '')):
                return True
        return False

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('ubl_cii_format')
    def _compute_is_peppol_edi_format(self):
        for partner in self:
            partner.is_peppol_edi_format = partner.ubl_cii_format not in (False, 'facturx', 'oioubl_201', 'ciusro')

    @api.depends('peppol_eas', 'peppol_endpoint', 'ubl_cii_format')
    def _compute_account_peppol_verification_state(self):
        for partner in self:
            partner.button_account_peppol_check_partner_endpoint()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @handle_demo
    def button_account_peppol_check_partner_endpoint(self):
        """ A basic check for whether a participant is reachable at the given
        Peppol participant ID - peppol_eas:peppol_endpoint (ex: '9999:test')
        The SML (Service Metadata Locator) assigns a DNS name to each peppol participant.
        This DNS name resolves into the SMP (Service Metadata Publisher) of the participant.
        The DNS address is of the following form:
        - "http://B-" + hexstring(md5(lowercase(ID-VALUE))) + "." + ID-SCHEME + "." + SML-ZONE-NAME + "/" + url_encoded(ID-SCHEME + "::" + ID-VALUE)
        (ref:https://peppol.helger.com/public/locale-en_US/menuitem-docs-doc-exchange)
        """
        self.ensure_one()

        if (
            not (self.peppol_eas and self.peppol_endpoint)
            or not self.is_peppol_edi_format
        ):
            self.account_peppol_verification_state = 'not_verified'
            return False

        edi_identification = f'{self.peppol_eas}:{self.peppol_endpoint}'.lower()
        participant_info = self._get_participant_info(edi_identification)
        if participant_info is None:
            self.account_peppol_verification_state = 'not_valid'
        else:
            is_participant_on_network = self._check_peppol_participant_exists(participant_info, edi_identification)
            if is_participant_on_network:
                is_valid_format = self._check_document_type_support(participant_info, self.ubl_cii_format)
                self.account_peppol_verification_state = 'valid' if is_valid_format else 'not_valid_format'
            else:
                self.account_peppol_verification_state = 'not_valid'

        return False
