import logging
import re
import requests

from markupsafe import Markup
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
        # TODO: `ubl_cii_format` is not company_dependent
        if self.env.company._get_peppol_proxy_type() != 'pdp':
            return
        for partner in self:
            if partner.country_code == 'FR':
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

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_21_fr'] = {'countries': ['FR'], 'on_peppol': False}
        return formats_info

    def _get_suggested_ubl_cii_format(self):
        # EXTENDS 'account'
        if self.country_code == 'FR' and not self._l10n_fr_pdp_is_b2c():
            return 'ubl_21_fr'
        return super()._get_suggested_ubl_cii_format()

    def _get_pdp_display_verification_state(self, state=None):
        self.ensure_one()
        state = state if state is not None else self.account_peppol_verification_label
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

    def _log_verification_state_update(self, company, old_value, new_value):
        # log the update of the pdp verification state
        # we do this instead of regular tracking because of the customized message
        # and because we want to log the change for every company in the db
        if self._get_pdp_receiver_identification_info()[0] != 'pdp':
            return super()._log_verification_state_update(company, old_value, new_value)
        if old_value == new_value:
            return None

        state_field = self._fields['pdp_verification_display_state']
        selection_values = dict(state_field.selection)
        old_display_state = self._get_pdp_display_verification_state(state=old_value)
        new_display_state = self._get_pdp_display_verification_state(state=new_value)
        old_label = selection_values[old_display_state] if old_value else False  # get translated labels
        new_label = selection_values[new_display_state] if new_value else False

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
            field=state_field.string,
            company=company.display_name,
        )
        self._message_log(body=body)

    # TODO: function does not exist
    @api.model
    @handle_demo
    def _get_peppol_verification_state(self, peppol_endpoint, peppol_eas, ubl_cii_format):
        proxy_type, edi_identification = self._get_peppol_proxy_identification_info(peppol_eas, peppol_endpoint)
        if proxy_type != 'pdp' or self.env.company._get_peppol_proxy_type() != 'pdp':
            return super()._get_peppol_verification_state(peppol_endpoint, peppol_eas, ubl_cii_format)
        return self._get_pdp_annuaire_verification_state(edi_identification, ubl_cii_format)

    @api.model
    def _get_pdp_annuaire_verification_state(self, edi_identification, ubl_cii_format):
        if not edi_identification:
            return 'not_verified'
        if ubl_cii_format != 'ubl_21_fr':
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
        return self._get_peppol_proxy_identification_info(self.peppol_eas, self.peppol_endpoint)

    @api.model
    def _get_peppol_proxy_identification_info(self, peppol_eas, peppol_endpoint):
        # Extend `account_peppol`
        proxy_type, identifier = super()._get_peppol_proxy_identification_info(peppol_eas, peppol_endpoint)
        if peppol_eas == '0225':
            proxy_type = 'pdp'
        return proxy_type, identifier
