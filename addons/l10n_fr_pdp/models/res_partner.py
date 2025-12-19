import logging
import requests

from markupsafe import Markup
from urllib import parse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

TIMEOUT = 10
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_21_fr', "France E-Invoicing (UBL 2.1)")])
    invoice_sending_method = fields.Selection(
        selection_add=[('pdp', 'By PDP')],
    )
    pdp_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Partner is not on the network'),
            ('not_valid_format', 'Partner cannot receive format'),
            ('valid', 'Partner is on the network'),
        ],
        string='PDP Verification State',
        company_dependent=True,
    )
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
        string='PDP State',
        company_dependent=True,
        compute="_compute_pdp_verification_display_state",
    )
    pdp_identifier = fields.Char(
        string='PDP Identifier',
        help='The Identifier should have one of the following forms: SIREN, SIRET, SIREN_SIRET_CodeRoutage, SIREN_SuffixeAdressage',
        compute="_compute_pdp_identifier", store=True, readonly=False,
        tracking=True,
    )
    is_using_pdp = fields.Boolean(compute='_compute_is_using_pdp')

    @api.onchange('invoice_edi_format', 'peppol_endpoint', 'peppol_eas', 'pdp_identifier')
    def _onchange_verify_pdp_status(self):
        self.button_pdp_check_partner_endpoint()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends_context('allowed_company_ids')
    @api.depends('country_code', 'vat')
    def _compute_is_using_pdp(self):
        pdp_user = self.env.company.sudo().pdp_edi_user
        for partner in self:
            partner.is_using_pdp = pdp_user and (partner.siret or partner._deduce_country_code() == 'FR')

    @api.depends('country_code', 'vat', 'company_registry')
    def _compute_pdp_identifier(self):
        """Initialize the PDP identifier with a default value"""
        for partner in self:
            if partner.pdp_identifier or partner._deduce_country_code() != 'FR':
                continue
            partner.pdp_identifier = partner.siret

    @api.depends('pdp_verification_state', 'pdp_identifier', 'peppol_endpoint', 'peppol_eas')
    def _compute_pdp_verification_display_state(self):
        for partner in self:
            state = partner.pdp_verification_state
            if not state or state == 'not_verified':
                display_state = state
            elif partner.pdp_identifier:
                display_state = f'pdp_{state}'
            else:
                display_state = f'peppol_{state}'
            partner.pdp_verification_display_state = display_state

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_pdp_send_ubl_21_fr(self):
        if self.filtered(
            lambda partner: (
                partner.invoice_sending_method == "pdp"
                and partner._get_pdp_receiver_identification_info()[0] == 'pdp'
                and partner.invoice_edi_format != "ubl_21_fr"
            )
        ):
            ubl_21_fr_string = dict(self._fields['invoice_edi_format']._description_selection(self.env))['ubl_21_fr']
            raise ValidationError(_('For French regulated invoices, only %(format_name)s is supported.', format_name=ubl_21_fr_string))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        self._update_pdp_state_per_company(vals=vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_pdp_state_per_company()
        return res

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_21_fr':
            return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_21_fr'] = {'countries': ['FR'], 'on_peppol': False}  # TODO: it is on peppol but only used with PDP
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'FR':
            return 'ubl_21_fr'
        return super()._get_suggested_invoice_edi_format()

    def _l10n_fr_pdp_log_verification_state_update(self, company, old_value, new_value):
        # log the update of the pdp verification state
        # we do this instead of regular tracking because of the customized message
        # and because we want to log the change for every company in the db
        if old_value == new_value:
            return

        state_field = self._fields['pdp_verification_display_state']
        selection_values = dict(state_field.selection)
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
            field=state_field.string,
            company=company.display_name,
        )
        self._message_log(body=body)

    @api.model
    @handle_demo
    def _pdp_annuaire_lookup_participant(self, edi_identification):
        edi_mode = self.env.company._get_pdp_edi_mode()
        origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp'][edi_mode]
        pdp_identifier = edi_identification.partition(":")[2]
        query = parse.urlencode({'pdp_identifier': pdp_identifier.lower()})
        endpoint = f'{origin}/api/pdp/1/annuaire_lookup?{query}'

        try:
            response = requests.get(endpoint, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            _logger.debug("failed to query annuaire for identifier %s: %s", edi_identification, e)
            return

        try:
            decoded_response = response.json()
        except ValueError:
            _logger.error('invalid JSON response %s when querying annuaire for identifier %s', response.status_code, edi_identification)
            return

        if error := decoded_response.get('error'):
            _logger.error('error when querying annuaire for identifier %s: %s', edi_identification, error.get('message', 'unknown error'))
            return

        if not response.ok:
            _logger.error('unsuccessful response %s when querying annuaire for identifier %s', response.status_code, edi_identification)
            return

        return decoded_response.get('result')

    def _get_pdp_annuaire_verification_state(self, edi_identification, invoice_edi_format):
        if not edi_identification or not self.env.company.pdp_edi_user:
            return 'not_verified'
        if invoice_edi_format != 'ubl_21_fr':
            return 'not_valid_format'
        participant_info = self._pdp_annuaire_lookup_participant(edi_identification)
        if (participant_info or {}).get('in_annuaire'):
            return 'valid'
        return 'not_valid'

    @api.model
    def _pdp_peppol_lookup_participant(self, edi_identification):
        """NAPTR DNS peppol participant lookup through Odoo's Peppol proxy"""
        edi_mode = self.env.company._get_pdp_edi_mode()
        origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp'][edi_mode]
        query = parse.urlencode({'peppol_identifier': edi_identification.lower()})
        endpoint = f'{origin}/api/pdp/1/peppol_lookup?{query}'

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

    @handle_demo
    def _get_pdp_peppol_verification_state(self, edi_identification, invoice_edi_format):
        if not edi_identification or not self.env.company.pdp_edi_user:
            return 'not_verified'
        if invoice_edi_format not in self._get_peppol_formats():
            return 'not_valid_format'
        participant_info = self._pdp_peppol_lookup_participant(edi_identification)
        return self._check_peppol_verification_state(edi_identification, invoice_edi_format, participant_info)

    def _get_pdp_verification_state(self, invoice_edi_format):
        self.ensure_one()
        proxy_type, edi_identification = self._get_pdp_receiver_identification_info()
        if proxy_type == 'pdp':
            return self._get_pdp_annuaire_verification_state(edi_identification, invoice_edi_format)
        elif proxy_type == 'peppol':
            return self._get_pdp_peppol_verification_state(edi_identification, invoice_edi_format)
        else:
            return 'not_verified'

    def _update_pdp_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        if vals is None:
            partners = self.filtered(
                lambda p: all([p.peppol_eas, p.peppol_endpoint, p.is_ubl_format, p.country_code in PEPPOL_LIST]) or p.pdp_identifier
            )
        elif {'peppol_eas', 'peppol_endpoint', 'pdp_identifier', 'invoice_edi_format'}.intersection(vals.keys()):
            partners = self.filtered(lambda p: p.country_code in PEPPOL_LIST)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_pdp_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                all_companies = self.env['res.company'].sudo().search([])

            for company in all_companies:
                partner.button_pdp_check_partner_endpoint(company=company)

    def _get_pdp_receiver_identification_info(self):
        # Return tuple `('pdp', pdp_identifier)` where pdp_identifier is in form "{scheme}:{identifier}"
        # Falls back to return `('peppol', peppol_identifier)` in case there is no PDP identifier.
        self.ensure_one()
        if self.pdp_identifier:
            return 'pdp', f"0225:{self.pdp_identifier}"
        if self.peppol_eas and self.peppol_endpoint:
            return 'peppol', f"{self.peppol_eas}:{self.peppol_endpoint}"
        return None, ""

    # -------------------------------------------------------------------------
    # BUTTONS
    # -------------------------------------------------------------------------

    def button_pdp_check_partner_endpoint(self, company=None):
        """ A basic check for whether a participant is reachable at the given identifier"""
        self.ensure_one()
        if not company:
            company = self.env.company

        self_partner = self.with_company(company)
        old_value = self_partner.pdp_verification_display_state
        self_partner.pdp_verification_state = self._get_pdp_verification_state(self_partner.invoice_edi_format)
        if self_partner.pdp_verification_state == 'valid' and not self_partner.invoice_sending_method:
            self_partner.invoice_sending_method = 'pdp'

        self._l10n_fr_pdp_log_verification_state_update(company, old_value, self_partner.pdp_verification_display_state)
        return False
