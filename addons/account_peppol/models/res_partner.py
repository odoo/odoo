# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.addons.account.models.company import PEPPOL_LIST

INVOICE_RESPONSE_CUSTOMISATION_ID = "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##urn:fdc:peppol.eu:poacc:trns:invoice_response:3::2.1"
TIMEOUT = 10
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('peppol', 'by Peppol')],
    )
    routing_scheme = fields.Selection(selection_add=[('odemo', "Odoo Demo ID")])  # Not a real EAS; used for demonstration.
    available_peppol_sending_methods = fields.Json(compute='_compute_available_peppol_sending_methods')
    available_peppol_edi_formats = fields.Json(compute='_compute_available_peppol_edi_formats')
    peppol_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Unchecked'),
            ('not_valid', 'Partner is not on Peppol'),  # does not exist on Peppol at all
            ('not_valid_format', 'Partner cannot receive format'),  # registered on Peppol but cannot receive the selected document type
            ('valid', 'Partner is on Peppol'),
        ],
        string='Peppol status',
        company_dependent=True,
    )
    peppol_supported_documents = fields.Json('Supported Peppol Documents')
    peppol_response_support = fields.Boolean('Peppol Response Service', compute='_compute_response_support')

    @api.onchange('invoice_edi_format', 'routing_identifier')
    def _onchange_verify_peppol_status(self):
        if not self.commercial_partner_id:
            # avoid issue when commercial_partner_id is on the view
            self._compute_commercial_partner()
        self.button_account_peppol_check_partner_endpoint()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_available_peppol_sending_methods(self):
        methods = dict(self._fields['invoice_sending_method'].selection)
        if self.env.company.country_code not in PEPPOL_LIST:
            methods.pop('peppol')
        self.available_peppol_sending_methods = list(methods)

    @api.depends_context('company')
    @api.depends('invoice_sending_method')
    def _compute_available_peppol_edi_formats(self):
        for partner in self:
            if partner.invoice_sending_method == 'peppol':
                partner.available_peppol_edi_formats = self._get_peppol_formats()
            else:
                partner.available_peppol_edi_formats = list(dict(self._fields['invoice_edi_format'].selection))

    def _compute_available_routing_schemes(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_available_routing_schemes()
        eas_codes = set(self[:1].available_routing_schemes)
        if self.env.company._get_peppol_edi_mode() != 'demo' and 'odemo' in eas_codes:
            eas_codes.remove('odemo')
            self.available_routing_schemes = list(eas_codes)

    @api.depends('peppol_supported_documents', 'peppol_verification_state')
    def _compute_response_support(self):
        for partner in self:
            partner.peppol_response_support = (
                partner.peppol_verification_state == 'valid'
                and partner.peppol_supported_documents
                and INVOICE_RESPONSE_CUSTOMISATION_ID in partner.peppol_supported_documents
            )

    def _compute_routing_scheme_endpoint(self):
        # Don't recompute on partners corresponding to registered companies
        partners_not_to_recompute = self.filtered_domain(self._domain_peppol_do_not_modify_routing_identifier())
        partners_to_recompute = self.browse([partner.id for partner in self if partner._origin.id not in partners_not_to_recompute.ids])
        super(ResPartner, partners_to_recompute)._compute_routing_scheme_endpoint()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_participant_info(self, edi_identification):
        # DEPRECATED: Peppol moved from CNAME to NAPTR DNS records
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
    @handle_demo
    def _check_peppol_participant_exists(self, participant_info, edi_identification):
        service_href = ''
        if isinstance(participant_info, dict):
            participant_identifier = participant_info.get('identifier', '')
            if services := participant_info.get('services', []):
                service_href = services[0].get('href', '')
        else:
            # DEPRECATED: we now use Odoo peppol API to fetch participant info and get a json response
            # keeping this branch for compatibility
            participant_identifier = participant_info.findtext('{*}ParticipantIdentifier') or ''
            service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
            if service_metadata is not None:
                service_href = service_metadata.attrib.get('href', '')

        # all Belgian companies are pre-registered on hermes-belgium, so they will
        # technically have an existing SMP url but they are not real Peppol participants
        # NOTE: peppol identifier must be case insensitive
        return edi_identification.lower() == participant_identifier.lower() and 'hermes-belgium' not in service_href

    @api.model
    def _peppol_lookup_participant(self, edi_identification):
        """NAPTR DNS peppol participant lookup through Odoo's Peppol proxy"""
        company = self.env.company
        if (edi_mode := company._get_peppol_edi_mode()) == 'demo':
            return

        proxy_type = company._get_peppol_proxy_type()
        origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()[proxy_type][edi_mode]
        query = parse.urlencode({'peppol_identifier': edi_identification.lower()})
        api_endpoint = self.env['account_edi_proxy_client.user']._get_peppol_proxy_endpoint('1/lookup', proxy_type=proxy_type)
        endpoint = f'{origin}{api_endpoint}?{query}'

        try:
            response = requests.get(endpoint, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            _logger.debug("failed to query peppol participant %s: %s", edi_identification, e)
            return

        try:
            decoded_response = response.json()
        except ValueError:
            _logger.error('invalid JSON response %s when querying peppol participant %s', response.status_code, edi_identification)
            return

        if error := decoded_response.get('error'):
            if error.get('code') != 'NOT_FOUND':
                _logger.error('error when querying peppol participant %s: %s', edi_identification, error.get('message', 'unknown error'))
            return

        if not response.ok:
            _logger.error('unsuccessful response %s when querying peppol participant %s', response.status_code, edi_identification)
            return

        return decoded_response.get('result')

    @api.model
    def _check_document_type_support(self, participant_info, ubl_cii_format, process_type='billing', partner=None):
        edi_builder = self._get_edi_builder(ubl_cii_format)
        expected_customization_id = edi_builder._get_customization_id(process_type=process_type)
        if isinstance(participant_info, dict):
            service_document_ids = [service['document_id'] for service in participant_info.get('services', []) if service.get('document_id')]
            if partner:
                partner.peppol_supported_documents = service_document_ids
            return any(expected_customization_id in document for document in service_document_ids)

        # DEPRECATED: participant_info as XML fetched directly from SMP
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        for service in service_references:
            if expected_customization_id in parse.unquote_plus(service.attrib.get('href', '')):
                return True
        return False

    def _update_peppol_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        if vals is None:
            partners = self.filtered(lambda p: all([p.routing_scheme, p.routing_endpoint, p.is_ubl_format, p.country_code in PEPPOL_LIST]))
        elif {'routing_scheme', 'routing_endpoint', 'invoice_edi_format'}.intersection(vals.keys()):
            partners = self.filtered(lambda p: p.country_code in PEPPOL_LIST)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_account_peppol_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                # We only check it for companies that are actually using Peppol.
                can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
                all_companies = self.env['res.company'].sudo().search([
                    ('account_peppol_proxy_state', 'in', can_send),
                ])

            for company in all_companies:
                partner.button_account_peppol_check_partner_endpoint(company=company)

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_peppol_state_per_company()
        return res

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_account_peppol_check_partner_endpoint(self, company=None):
        """ A basic check for whether a participant is reachable at the explicit routing identifier
        (``routing_scheme:routing_endpoint``). The SML (Service Metadata Locator) assigns a DNS name
        to each Peppol participant, which resolves into the participant's SMP (Service Metadata Publisher).
        """
        self.ensure_one()
        if not company:
            company = self.env.company

        self.invalidate_recordset(['routing_identifier'])
        self_partner = self.with_company(company)
        if not self_partner.routing_identifier:
            return False
        old_value = self_partner.peppol_verification_state
        new_value = self_partner._get_peppol_verification_state(
            self_partner.routing_identifier,
            self_partner._get_peppol_edi_format(),
            partner=self_partner,
        )
        if old_value != new_value:
            self_partner.peppol_verification_state = new_value
            self._track_add(
                initial_values={self.id: {'peppol_verification_state': old_value}},
                end_values={self.id: {'peppol_verification_state': new_value}},
            )
        return False

    @api.model
    @handle_demo
    def _get_peppol_verification_state(self, routing_identifier, invoice_edi_format, process_type='billing', partner=None):
        ''' Check the state of the peppol participant (defined by its endpoint and eas) for a specific edi format and process.
            A partner record parameter can be added in order to attach its available services (if its participant on Peppol).
        '''
        if not routing_identifier or invoice_edi_format not in self._get_peppol_formats():
            return 'not_verified'

        edi_identification = routing_identifier.lower()
        participant_info = self._peppol_lookup_participant(edi_identification)
        if participant_info is None:
            return 'not_valid'
        is_participant_on_network = self._check_peppol_participant_exists(participant_info, edi_identification)
        if not is_participant_on_network:
            return 'not_valid'
        if self._check_document_type_support(participant_info, invoice_edi_format, process_type=process_type, partner=partner):
            return 'valid'
        return 'not_valid_format'

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'routing_identifier'})

        return frontend_writable_fields

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)

        sending_method = kwargs.get('invoice_sending_method')
        if sending_method == 'peppol':
            mandatory_fields.update({'routing_scheme', 'routing_endpoint', 'invoice_edi_format'})

        return mandatory_fields

    @api.model
    def _domain_peppol_do_not_modify_routing_identifier(self):
        registered_company_partners = self.env['res.company'].sudo().with_context(active_test=False).search([
            ('account_peppol_proxy_state', 'in', self.env['account_edi_proxy_client.user']._get_can_send_domain()),
        ]).partner_id
        return Domain([
            ('routing_scheme', '!=', False),
            ('routing_endpoint', '!=', False),
            '|',
            ('peppol_verification_state', '=', 'valid'),
            ('id', 'in', registered_company_partners.ids),
        ])
