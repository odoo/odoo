# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.tools.sql import column_exists, create_column

TIMEOUT = 10
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_peppol_is_endpoint_valid = fields.Boolean(
        string="PEPPOL endpoint validity",
        help="The partner's EAS code and PEPPOL endpoint are valid",
        compute="_compute_account_peppol_is_endpoint_valid", store=True,
        copy=False,
    )
    account_peppol_validity_last_check = fields.Date(
        string="Checked on",
        help="Last Peppol endpoint verification",
        compute="_compute_account_peppol_is_endpoint_valid", store=True,
        copy=False,
    )
    account_peppol_verification_label = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not valid'),  # does not exist on Peppol at all
            ('not_valid_format', 'Cannot receive this format'),  # registered on Peppol but cannot receive the selected document type
            ('valid', 'Valid'),
        ],
        string='Peppol endpoint validity',
        compute='_compute_account_peppol_verification_label',
        copy=False,
    )  # field to compute the label to show for partner endpoint
    is_peppol_edi_format = fields.Boolean(compute='_compute_is_peppol_edi_format')

    def _auto_init(self):
        """Create columns `account_peppol_is_endpoint_valid` and `account_peppol_validity_last_check`
        to avoid having them computed by the ORM on installation.
        """
        if not column_exists(self.env.cr, 'res_partner', 'account_peppol_is_endpoint_valid'):
            create_column(self.env.cr, 'res_partner', 'account_peppol_is_endpoint_valid', 'boolean')
        if not column_exists(self.env.cr, 'res_partner', 'account_peppol_validity_last_check'):
            create_column(self.env.cr, 'res_partner', 'account_peppol_validity_last_check', 'timestamp')
        return super()._auto_init()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # TODO: remove in master
        res = super().fields_get(allfields, attributes)

        # the orm_cache does not contain the new selections added in stable: clear the cache once
        existing_selection = res.get('account_peppol_verification_label', {}).get('selection')
        if existing_selection is None:
            return res

        not_valid_format_label = next(x for x in self._fields['account_peppol_verification_label'].selection if x[0] == 'not_valid_format')
        need_update = not_valid_format_label not in existing_selection

        if need_update:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection']._update_selection(
                'res.partner',
                'account_peppol_verification_label',
                self._fields['account_peppol_verification_label'].selection,
            )
            self.env.registry.clear_cache()
            return super().fields_get(allfields, attributes)
        return res

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        edi_mode = self.env.company._get_peppol_edi_mode()
        sml_zone = 'acc.edelivery' if edi_mode == 'test' else 'edelivery'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.tech.ec.europa.eu/{endpoint_participant}"

        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.debug(e)
            return None
        return etree.fromstring(response.content)

    @api.model
    def _check_peppol_participant_exists(self, edi_identification, check_company=False, ubl_cii_format=False):
        participant_info = self._get_participant_info(edi_identification)
        if participant_info is None:
            return False

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

        return self._check_document_type_support(participant_info, ubl_cii_format)

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_metadata = participant_info.find('.//{*}ServiceMetadataReferenceCollection')
        if service_metadata is None:
            return False

        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        for service in service_metadata.iterfind('{*}ServiceMetadataReference'):
            if document_type in parse.unquote_plus(service.attrib.get('href', '')):
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
    def _compute_account_peppol_is_endpoint_valid(self):
        for partner in self:
            partner.button_account_peppol_check_partner_endpoint()

    @api.depends('account_peppol_is_endpoint_valid', 'account_peppol_validity_last_check')
    def _compute_account_peppol_verification_label(self):
        for partner in self:
            if not partner.account_peppol_validity_last_check:
                partner.account_peppol_verification_label = 'not_verified'
            elif (
                partner.is_peppol_edi_format
                and (participant_info := self._get_participant_info(f'{partner.peppol_eas}:{partner.peppol_endpoint}'.lower())) is not None
                and not partner._check_document_type_support(participant_info, partner.ubl_cii_format)
            ):
                # the partner might exist on the network, but not be able to receive that specific format
                partner.account_peppol_verification_label = 'not_valid_format'
            elif partner.account_peppol_is_endpoint_valid:
                partner.account_peppol_verification_label = 'valid'
            else:
                partner.account_peppol_verification_label = 'not_valid'

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

        if not (self.peppol_eas and self.peppol_endpoint) or not self.is_peppol_edi_format:
            self.account_peppol_is_endpoint_valid = False
        else:
            edi_identification = f'{self.peppol_eas}:{self.peppol_endpoint}'.lower()
            self.account_peppol_validity_last_check = fields.Date.context_today(self)
            self.account_peppol_is_endpoint_valid = bool(self._check_peppol_participant_exists(edi_identification, ubl_cii_format=self.ubl_cii_format))
        return False
