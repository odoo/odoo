import logging
import re
import requests

from urllib import parse

from odoo import _, api, fields, models

from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)

siren_siret_re = re.compile(r'^(\d{9}|\d{14})$')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('ubl_21_fr', "France E-Invoicing (UBL 2.1)")])
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

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('account_peppol_verification_label', 'peppol_endpoint', 'peppol_eas')
    @api.depends_context('company')
    def _compute_pdp_verification_display_state(self):
        for partner in self:
            partner.pdp_verification_display_state = partner._get_pdp_display_verification_state(partner.account_peppol_verification_label)

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        super()._compute_ubl_cii_format()
        # Note: The `ubl_cii_format` is not a `company_dependent` field.
        #       But we only want to use 'ubl_21_fr' when sending from "PDP" to "PDP".
        for partner in self:
            if (
                (partner.company_id.partner_id.peppol_eas == '0225'
                 or (not partner.company_id and self.env.company.partner_id.peppol_eas == '0225'))
                and partner.country_code == 'FR'
                and partner._get_pdp_receiver_identification_info()[0] == 'pdp'
            ):
                partner.ubl_cii_format = 'ubl_21_fr'

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
        siret = self.siret or (self.company_registry if self.company_registry and siren_siret_re.match(self.company_registry) else '')
        siren = siret[:9]
        if len(siret) == 9:
            return 'siren', siren
        elif len(siret) == 14:
            return 'siret', siret
        return None, None

    def _get_suggested_pdp_identifier(self):
        self.ensure_one()
        # We suggest the SIREN (even if the SIRET is filled in).
        # "Everyone" will probably have registered the SIREN on annuaire. (Even if they have a SIRET.)
        return self._l10n_fr_pdp_get_siren()

    def _get_peppol_endpoint_value(self, country_code, field):
        self.ensure_one()
        if country_code == 'FR' and field == 'peppol_endpoint':
            return self._get_suggested_pdp_identifier()
        return super()._get_peppol_endpoint_value(country_code, field)

    def _build_error_peppol_endpoint(self, eas, endpoint):
        # Extend 'account_edi_ubl_cii' for '0225' endpoint
        if eas != '0225':
            return super()._build_error_peppol_endpoint(eas, endpoint)
        if not self.env["res.company"]._check_pdp_identifier(endpoint):
            return _("The Peppol endpoint is not valid. The expected format is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or SIREN_SuffixeAdressage")

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'ubl_21_fr':
            return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_edi_builder()

    def _get_pdp_display_verification_state(self, state=None):
        self.ensure_one()
        state = state if state is not None else self.account_peppol_verification_label
        if not state or state == 'not_verified':
            return state
        elif self.env.company._get_peppol_proxy_type() == 'pdp' and self._get_pdp_receiver_identification_info()[0] == 'pdp':
            return f'pdp_{state}'
        else:
            return f'peppol_{state}'

    def _compute_account_peppol_verification_label(self):
        pdp_partners = self.filtered(
            lambda p: (p._get_pdp_receiver_identification_info()[0] == 'pdp')
        ) if self.env.company._get_peppol_proxy_type() == 'pdp' else self.env[self._name]
        for partner in pdp_partners:
            if not partner.account_peppol_validity_last_check:
                partner.account_peppol_verification_label = 'not_verified'
            elif partner.ubl_cii_format != 'ubl_21_fr':
                partner.account_peppol_verification_label = 'not_valid_format'
            elif partner.account_peppol_is_endpoint_valid:
                partner.account_peppol_verification_label = 'valid'
            else:
                partner.account_peppol_verification_label = 'not_valid'
        super(ResPartner, self - pdp_partners)._compute_account_peppol_verification_label()

    def button_account_peppol_check_partner_endpoint(self):
        self.ensure_one()
        partner_type, edi_identification = self._get_pdp_receiver_identification_info()
        if self.env.company._get_peppol_proxy_type() != 'pdp' or partner_type != 'pdp':
            return super().button_account_peppol_check_partner_endpoint()

        if not edi_identification:
            self.account_peppol_is_endpoint_valid = False
        else:
            participant_info = self._pdp_annuaire_lookup_participant(edi_identification)
            self.write({
                'account_peppol_validity_last_check': fields.Date.context_today(self),
                'account_peppol_is_endpoint_valid': (participant_info or {}).get('in_annuaire') or False,
            })
        return False

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
        return self._get_peppol_proxy_identification_info(self.peppol_eas, self.peppol_endpoint)

    @api.model
    def _get_peppol_proxy_identification_info(self, peppol_eas, peppol_endpoint):
        # Extend `account_peppol`
        proxy_type, identifier = super()._get_peppol_proxy_identification_info(peppol_eas, peppol_endpoint)
        if peppol_eas == '0225':
            proxy_type = 'pdp'
        return proxy_type, identifier
