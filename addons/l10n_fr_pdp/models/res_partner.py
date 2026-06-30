import logging
import re
import requests

from urllib import parse

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)

siren_siret_re = re.compile(r'^(\d{9}|\d{14})$')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_21_fr', "France E-Invoicing (UBL 2.1)")])
    pdp_verification_display_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('pdp_not_valid', 'Partner is not in the annuaire'),
            ('pdp_not_valid_format', 'Partner cannot receive format'),
            ('pdp_valid', 'Partner is in the annuaire'),
            ('peppol_not_valid', 'Partner is not on Peppol'),  # does not exist on Peppol at all
            ('peppol_not_valid_format', 'Partner cannot receive format'),  # registered on Peppol but cannot receive the selected document type
            ('peppol_valid', 'Partner is on Peppol'),
        ],
        string='E-Invoicing State',
        compute="_compute_pdp_verification_display_state",
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # Extend to rename the `peppol` option in the `invoice_sending_method` selection
        fields = super().fields_get(allfields, attributes)
        company = self.env.company
        if not self.env.context.get("studio") and (company.country_code == 'FR' or company.sudo().pdp_identifier) and 'invoice_sending_method' in fields:
            field = fields['invoice_sending_method']
            if 'selection' in field:
                field['selection'] = [('peppol', self.env._('by Approved Platform')) if option[0] == 'peppol' else option for option in field['selection']]
        return fields

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('peppol_verification_state', 'routing_scheme', 'routing_endpoint')
    @api.depends_context('company')
    def _compute_pdp_verification_display_state(self):
        for partner in self:
            partner.pdp_verification_display_state = partner._get_pdp_display_verification_state(partner.peppol_verification_state)

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_pdp_send_ubl_21_fr(self):
        if self.filtered(
            lambda partner: (
                partner.invoice_sending_method == "peppol"
                and partner._get_pdp_receiver_identification_info()[0] == 'pdp'
                and partner.invoice_edi_format != "ubl_21_fr"
            )
        ):
            ubl_21_fr_string = self.env._("France E-Invoicing (UBL 2.1)")
            raise ValidationError(self.env._("For French regulated invoices, only %(format_name)s is supported.", format_name=ubl_21_fr_string))

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------

    def _l10n_fr_pdp_is_b2c(self):
        self.ensure_one()
        return self.vat == '/' or not self.vat

    def _l10n_fr_pdp_get_siren(self):
        self.ensure_one()
        id_type, id_value = self._l10n_fr_pdp_get_base_identifier()
        if id_type in ('siren', 'siret'):
            return id_value[:9]
        return False

    def _l10n_fr_pdp_get_base_identifier(self):
        self.ensure_one()
        candidates = [
            self.additional_identifiers['FR_SIRET'] if self.additional_identifiers and siren_siret_re.match(self.additional_identifiers.get('FR_SIRET', '')) else '',
            self.additional_identifiers['FR_SIREN'] if self.additional_identifiers and siren_siret_re.match(self.additional_identifiers.get('FR_SIREN', '')) else '',
        ]
        for identifier in candidates:
            if not identifier:
                continue
            if len(identifier) == 9:
                return 'siren', identifier
            elif len(identifier) == 14:
                return 'siret', identifier

        return None, None

    def _get_suggested_pdp_identifier(self):
        self.ensure_one()
        # We suggest the SIREN (even if the SIRET is filled in).
        # "Everyone" will probably have registered the SIREN on annuaire. (Even if they have a SIRET.)
        return self._l10n_fr_pdp_get_siren()

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_21_fr':
            return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_21_fr'] = {'countries': ['FR'], 'on_peppol': False}
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'FR' and not self._l10n_fr_pdp_is_b2c():
            return 'ubl_21_fr'
        return super()._get_suggested_invoice_edi_format()

    def _get_pdp_display_verification_state(self, state=None):
        self.ensure_one()
        state = state if state is not None else self.peppol_verification_state
        if not state or state == 'not_verified':
            return state
        elif self.env.company._get_peppol_proxy_type() == 'pdp' and self._get_pdp_receiver_identification_info()[0] == 'pdp':
            return f'pdp_{state}'
        else:
            return f'peppol_{state}'

    def _get_suggested_peppol_edi_format(self):
        # EXTENDS 'account_edi_ubl_cidd`
        self.ensure_one()
        if self.env.company._get_peppol_proxy_type() == 'pdp' and self.commercial_partner_id._get_pdp_receiver_identification_info()[0] == 'pdp':
            return 'ubl_21_fr'
        return super()._get_suggested_peppol_edi_format()

    @api.model
    @handle_demo
    def _get_peppol_verification_state(self, routing_identifier, invoice_edi_format, process_type='billing', partner=None):
        # EXTENDS 'account_peppol': French PDP participants (EAS 0225) are verified against the
        # PDP annuaire (the official French directory) instead of the Peppol SML.
        scheme, _sep, _endpoint = routing_identifier.lower().partition(":")
        if scheme != '0225':
            return super()._get_peppol_verification_state(routing_identifier, invoice_edi_format, process_type=process_type, partner=partner)
        return self._get_pdp_annuaire_verification_state(routing_identifier, invoice_edi_format)

    @api.model
    def _get_pdp_annuaire_verification_state(self, edi_identification, invoice_edi_format):
        if not edi_identification:
            return 'not_verified'
        if invoice_edi_format != 'ubl_21_fr':
            return 'not_valid_format'
        participant_info = self._pdp_annuaire_lookup_participant(edi_identification)
        if (participant_info or {}).get('in_annuaire'):
            return 'valid'
        return 'not_valid'

    @api.model
    @handle_demo
    def _pdp_annuaire_lookup_participant(self, edi_identification):
        edi_mode = self.env.company._get_peppol_edi_mode()
        origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp'][edi_mode]
        pdp_identifier = edi_identification.partition(":")[2]
        query = parse.urlencode({'pdp_identifier': pdp_identifier})  # Note: the annuaire lookup is case-sensitive
        endpoint = f'{origin}/api/pdp/1/annuaire_lookup?{query}'

        try:
            response = requests.get(endpoint, timeout=10)
        except requests.exceptions.RequestException as e:
            _logger.debug("failed to query annuaire for identifier %s: %s", edi_identification, e)
            return None

        try:
            decoded_response = response.json()
        except ValueError:
            _logger.error('invalid JSON response %s when querying annuaire for identifier %s', response.status_code, edi_identification)
            return None

        if error := decoded_response.get('error'):
            _logger.error('error when querying annuaire for identifier %s: %s', edi_identification, error.get('message', 'unknown error'))
            return None

        if not response.ok:
            _logger.error('unsuccessful response %s when querying annuaire for identifier %s', response.status_code, edi_identification)
            return None

        return decoded_response.get('result')

    def _get_pdp_receiver_identification_info(self):
        eas, _sep, endpoint = (self.routing_identifier or '').partition(':')
        return self._get_peppol_proxy_identification_info(eas, endpoint)

    @api.model
    def _get_peppol_proxy_identification_info(self, routing_scheme, routing_endpoint):
        # Extend `account_peppol`
        proxy_type, identifier = super()._get_peppol_proxy_identification_info(routing_scheme, routing_endpoint)
        if routing_scheme == '0225':
            proxy_type = 'pdp'
        return proxy_type, identifier

    def action_pdp_annuaire_lookup(self):
        self.ensure_one()
        if not self.routing_endpoint:
            raise UserError(self.env._("Set up your peppol endpoint to enable the lookup"))

        if not re.match(r"^\d{9}", self.routing_endpoint):
            raise UserError(self.env._("endpoint must be at least 9 characters long and they must be numbers to enable the lookup (ie: siren)"))

        edi_mode = self.env.company._get_peppol_edi_mode()
        origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp'][edi_mode]
        endpoint = f'{origin}/api/pdp/1/pdp_annuaire_lookup'

        response = requests.get(
            url=endpoint,
            params={
                'pdp_endpoint': self.routing_endpoint[:9],  # We only want to take the first 9 char (for the siren)
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('annuaire_lines'):
            raise UserError(self.env._("No annuaire lines found for that identifier"))

        wizard = self.env['l10n_fr_pdp.partner.lookup'].create({
            'available_annuaire_line_ids': [
                Command.create(line)
                for line in data['annuaire_lines']
            ],
            'partner_id': self.id,
        })
        return wizard._get_records_action(target='new')
