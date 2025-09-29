# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import re
import requests
from lxml import etree
from stdnum.fr import siret
from urllib import parse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

TIMEOUT = 10
_logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# ELECTRONIC ADDRESS SCHEME (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
# -------------------------------------------------------------------------
EAS_MAPPING = {
    'AD': {'9922': 'vat'},
    'AE': {'0235': 'vat'},
    'AL': {'9923': 'vat'},
    'AT': {'9915': 'vat'},
    'AU': {'0151': 'vat'},
    'BA': {'9924': 'vat'},
    'BE': {'0208': 'company_registry'},
    'BG': {'9926': 'vat'},
    'CH': {'9927': 'vat'},
    'CY': {'9928': 'vat'},
    'CZ': {'9929': 'vat'},
    'DE': {'9930': 'vat'},
    'DK': {'0184': 'company_registry', '0198': 'vat'},
    'EE': {'9931': 'vat'},
    'ES': {'9920': 'vat'},
    'FI': {'0216': None},
    'FR': {'0009': 'siret', '9957': 'vat'},
    'SG': {'0195': 'l10n_sg_unique_entity_number'},
    'GB': {'9932': 'vat'},
    'GR': {'9933': 'vat'},
    'HR': {'9934': 'vat'},
    'HU': {'9910': 'l10n_hu_eu_vat'},
    'IE': {'9935': 'vat'},
    'IS': {'0196': 'vat'},
    'IT': {'0211': 'vat', '0210': 'l10n_it_codice_fiscale'},
    'JP': {'0221': 'vat'},
    'LI': {'9936': 'vat'},
    'LT': {'9937': 'vat'},
    'LU': {'9938': 'vat'},
    'LV': {'0218': 'company_registry', '9939': 'vat'},
    'MC': {'9940': 'vat'},
    'ME': {'9941': 'vat'},
    'MK': {'9942': 'vat'},
    'MT': {'9943': 'vat'},
    # Do not add the vat for NL, since: "[NL-R-003] For suppliers in the Netherlands, the legal entity identifier
    # MUST be either a KVK or OIN number (schemeID 0106 or 0190)" in the Bis 3 rules (in PartyLegalEntity/CompanyID).
    'NL': {'0106': None, '0190': None},
    'NO': {'0192': 'l10n_no_bronnoysund_number'},
    'NZ': {'0088': 'company_registry'},
    'PL': {'9945': 'vat'},
    'PT': {'9946': 'vat'},
    'RO': {'9947': 'vat'},
    'RS': {'9948': 'vat'},
    'SE': {'0007': 'company_registry'},
    'SI': {'9949': 'vat'},
    'SK': {'9950': 'vat'},
    'SM': {'9951': 'vat'},
    'TR': {'9952': 'vat'},
    'VA': {'9953': 'vat'},
}


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
    ubl_cii_format = fields.Selection(  # from 17.0 module `account_edi_ubl_cii`
        string="Format",
        selection=[
            ('ubl_bis3', "BIS Billing 3.0"),
            ('xrechnung', "XRechnung CIUS"),
            ('nlcius', "NLCIUS"),
        ],
        compute='_compute_ubl_cii_format',
        store=True,
        readonly=False,
    )
    peppol_endpoint = fields.Char(  # from 17.0 module `account_edi_ubl_cii`
        string="Peppol Endpoint",
        help="Unique identifier used by the BIS Billing 3.0 and its derivatives, also known as 'Endpoint ID'.",
        compute="_compute_peppol_endpoint",
        store=True,
        readonly=False,
        tracking=True,
    )
    peppol_eas = fields.Selection(  # from 17.0 module `account_edi_ubl_cii`
        string="Peppol e-address (EAS)",
        help="""Code used to identify the Endpoint for BIS Billing 3.0 and its derivatives.
             List available at https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/""",
        compute="_compute_peppol_eas",
        store=True,
        readonly=False,
        tracking=True,
        selection=[
            ('0002', "0002 - System Information et Repertoire des Entreprise et des Etablissements: SIRENE"),
            ('0007', "0007 - Organisationsnummer (Swedish legal entities)"),
            ('0009', "0009 - SIRET-CODE"),
            ('0037', "0037 - LY-tunnus"),
            ('0060', "0060 - Data Universal Numbering System (D-U-N-S Number)"),
            ('0088', "0088 - EAN Location Code"),
            ('0096', "0096 - DANISH CHAMBER OF COMMERCE Scheme (EDIRA compliant)"),
            ('0097', "0097 - FTI - Ediforum Italia, (EDIRA compliant)"),
            ('0106', "0106 - Association of Chambers of Commerce and Industry in the Netherlands, (EDIRA compliant)"),
            ('0130', "0130 - Directorates of the European Commission"),
            ('0135', "0135 - SIA Object Identifiers"),
            ('0142', "0142 - SECETI Object Identifiers"),
            ('0151', "0151 - Australian Business Number (ABN) Scheme"),
            ('0183', "0183 - Swiss Unique Business Identification Number (UIDB)"),
            ('0184', "0184 - DIGSTORG"),
            ('0188', "0188 - Corporate Number of The Social Security and Tax Number System"),
            ('0190', "0190 - Dutch Originator's Identification Number"),
            ('0191', "0191 - Centre of Registers and Information Systems of the Ministry of Justice"),
            ('0192', "0192 - Enhetsregisteret ved Bronnoysundregisterne"),
            ('0193', "0193 - UBL.BE party identifier"),
            ('0195', "0195 - Singapore UEN identifier"),
            ('0196', "0196 - Kennitala - Iceland legal id for individuals and legal entities"),
            ('0198', "0198 - ERSTORG"),
            ('0199', "0199 - Legal Entity Identifier (LEI)"),
            ('0200', "0200 - Legal entity code (Lithuania)"),
            ('0201', "0201 - Codice Univoco Unità Organizzativa iPA"),
            ('0202', "0202 - Indirizzo di Posta Elettronica Certificata"),
            ('0204', "0204 - Leitweg-ID"),
            ('0208', "0208 - Numero d'entreprise / ondernemingsnummer / Unternehmensnummer"),
            ('0209', "0209 - GS1 identification keys"),
            ('0210', "0210 - CODICE FISCALE"),
            ('0211', "0211 - PARTITA IVA"),
            ('0212', "0212 - Finnish Organization Identifier"),
            ('0213', "0213 - Finnish Organization Value Add Tax Identifier"),
            ('0215', "0215 - Net service ID"),
            ('0216', "0216 - OVTcode"),
            ('0218', "0218 - Unified registration number (Latvia)"),
            ('0221', "0221 - The registered number of the qualified invoice issuer (Japan)"),
            ('0225', "0225 - FRCTC Electronic Address (France)"),
            ('0230', "0230 - National e-Invoicing Framework (Malaysia)"),
            ('0235', "0235 - UAE Tax Identification Number (TIN)"),
            ('0240', "0240 - Register of legal persons (France)"),
            ('9901', "9901 - Danish Ministry of the Interior and Health"),
            ('9910', "9910 - Hungary VAT number"),
            ('9913', "9913 - Business Registers Network"),
            ('9914', "9914 - Österreichische Umsatzsteuer-Identifikationsnummer"),
            ('9915', "9915 - Österreichisches Verwaltungs bzw. Organisationskennzeichen"),
            ('9918', "9918 - SOCIETY FOR WORLDWIDE INTERBANK FINANCIAL, TELECOMMUNICATION S.W.I.F.T"),
            ('9919', "9919 - Kennziffer des Unternehmensregisters"),
            ('9920', "9920 - Agencia Española de Administración Tributaria"),
            ('9922', "9922 - Andorra VAT number"),
            ('9923', "9923 - Albania VAT number"),
            ('9924', "9924 - Bosnia and Herzegovina VAT number"),
            ('9925', "9925 - Belgium VAT number"),
            ('9926', "9926 - Bulgaria VAT number"),
            ('9927', "9927 - Switzerland VAT number"),
            ('9928', "9928 - Cyprus VAT number"),
            ('9929', "9929 - Czech Republic VAT number"),
            ('9930', "9930 - Germany VAT number"),
            ('9931', "9931 - Estonia VAT number"),
            ('9932', "9932 - United Kingdom VAT number"),
            ('9933', "9933 - Greece VAT number"),
            ('9934', "9934 - Croatia VAT number"),
            ('9935', "9935 - Ireland VAT number"),
            ('9936', "9936 - Liechtenstein VAT number"),
            ('9937', "9937 - Lithuania VAT number"),
            ('9938', "9938 - Luxemburg VAT number"),
            ('9939', "9939 - Latvia VAT number"),
            ('9940', "9940 - Monaco VAT number"),
            ('9941', "9941 - Montenegro VAT number"),
            ('9942', "9942 - Macedonia, the former Yugoslav Republic of VAT number"),
            ('9943', "9943 - Malta VAT number"),
            ('9944', "9944 - Netherlands VAT number"),
            ('9945', "9945 - Poland VAT number"),
            ('9946', "9946 - Portugal VAT number"),
            ('9947', "9947 - Romania VAT number"),
            ('9948', "9948 - Serbia VAT number"),
            ('9949', "9949 - Slovenia VAT number"),
            ('9950', "9950 - Slovakia VAT number"),
            ('9951', "9951 - San Marino VAT number"),
            ('9952', "9952 - Türkiye VAT number"),
            ('9953', "9953 - Holy See (Vatican City State) VAT number"),
            ('9955', "9955 - Swedish VAT number"),
            ('9957', "9957 - French VAT number"),
            ('9959', "9959 - Employer Identification Number (EIN, USA)"),
            ('AN', "AN - O.F.T.P. (ODETTE File Transfer Protocol)"),
            ('AQ', "AQ - X.400 address for mail text"),
            ('AS', "AS - AS2 exchange"),
            ('AU', "AU - File Transfer Protocol"),
            ('EM', "EM - Electronic mail"),
        ]
    )

    @api.constrains('peppol_eas')
    def _check_peppol_eas(self):
        for partner in self:
            if partner.peppol_eas in ('0037', '0212', '0213', '0215'):
                raise ValidationError(_("Peppol EAS codes 0037, 0212, 0213, 0215 are deprecated. Please use 0216 instead."))
            elif partner.peppol_eas == '9955':
                raise ValidationError(_("Peppol EAS code 9955 is deprecated. Please use 0007 instead."))
            elif partner.peppol_eas == '9901':
                raise ValidationError(_("Peppol EAS code 9901 is deprecated. Please use a different Danish EAS code instead."))

    @api.constrains('peppol_endpoint')
    def _check_peppol_fields(self):
        for partner in self:
            if partner.peppol_endpoint and partner.peppol_eas:
                error = self._build_error_peppol_endpoint(partner.peppol_eas, partner.peppol_endpoint)
                if error:
                    raise ValidationError(error)

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _peppol_lookup_participant(self, edi_identification):
        """NAPTR DNS peppol participant lookup through Odoo's Peppol proxy"""
        edi_mode = self.env.company._get_peppol_edi_mode()
        if edi_mode == 'demo':
            return

        peppol_edi_format = self.env.ref('account_peppol.edi_peppol', raise_if_not_found=False)
        if not peppol_edi_format:
            raise UserError(_("Missing record 'account_peppol.edi_peppol' (Peppol Account EDI Format)"))

        origin = self.env['account_edi_proxy_client.user']._get_server_url_new(edi_format=peppol_edi_format)
        query = parse.urlencode({'peppol_identifier': edi_identification.lower()})
        endpoint = f'{origin}/api/peppol/1/lookup?{query}'

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

        error = decoded_response.get('error')
        if error:
            if error.get('code') != 'NOT_FOUND':
                _logger.error('error when querying peppol participant %s: %s', edi_identification, error.get('message', 'unknown error'))
            return

        return decoded_response.get('result')

    @api.model
    def _check_peppol_participant_exists(self, edi_identification, check_company=False, ubl_cii_format=False):
        participant_info = self._peppol_lookup_participant(edi_identification)
        if participant_info is None:
            return False

        services = participant_info.get('services')
        if services:
            service_href = services[0].get('href', '')
        else:
            # participant exists and is registered, but doesn't expose any service
            service_href = ''

        participant_identifier = participant_info.get('identifier', '').lower()

        # peppol identifier must be case insensitive
        if edi_identification.lower() != participant_identifier or 'hermes-belgium' in service_href:
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

    @api.model
    def _get_customization_ids(self):
        # On model 'account.edi.xml.ubl_21' in `account_edi_ubl_cii` in 17.0
        # Moved here since we use the `ubl_cii_format` strings and not the 'account.edi.format' ones.
        return {
            'ubl_bis3': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'nlcius': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
            'xrechnung': 'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0',
        }

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        expected_customization_id = self._get_customization_ids()[ubl_cii_format]
        for service in participant_info.get('services', []):
            service_document_id = service.get('document_id')
            if service_document_id and expected_customization_id in service_document_id:
                return True
        return False

    @api.model
    def _get_ubl_cii_formats(self):
        return {
            'DE': 'xrechnung',
            'NL': 'nlcius',
        }

    def _peppol_eas_endpoint_depends(self):
        # field dependencies of methods _compute_peppol_endpoint() and _compute_peppol_eas()
        # because we need to extend depends in l10n modules
        return ['country_code', 'vat', 'company_registry']

    def _build_error_peppol_endpoint(self, eas, endpoint):
        """ This function contains all the rules regarding the peppol_endpoint."""
        if eas == '0208' and not re.match(r"^\d{10}$", endpoint):
            return _("The Peppol endpoint is not valid. The expected format is: 0239843188")
        if eas == '0009' and not siret.is_valid(endpoint):
            return _("The Peppol endpoint is not valid. The expected format is: 73282932000074")
        if eas == '0007' and not re.match(r"^\d{10}$", endpoint):
            return _("The Peppol endpoint is not valid. "
                     "It should contain exactly 10 digits (Company Registry number)."
                     "The expected format is: 1234567890")

    def _get_peppol_edi_format(self):
        # Note that `ubl_cii_format` uses the names from 17.0+
        if not self:
            return None
        self.ensure_one()
        if self.ubl_cii_format == 'ubl_bis3':
            return self.env.ref('account_edi_ubl_cii.ubl_bis3', raise_if_not_found=False)
        if self.ubl_cii_format == 'xrechnung':
            return self.env.ref('account_edi_ubl_cii.ubl_de', raise_if_not_found=False)
        if self.ubl_cii_format == 'nlcius':
            return self.env.ref('account_edi_ubl_cii.edi_nlcius_1', raise_if_not_found=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('peppol_eas', 'peppol_endpoint', 'ubl_cii_format')
    def _compute_account_peppol_is_endpoint_valid(self):
        for partner in self:
            partner.button_account_peppol_check_partner_endpoint()

    @api.depends('account_peppol_is_endpoint_valid', 'account_peppol_validity_last_check')
    def _compute_account_peppol_verification_label(self):
        for partner in self:
            if partner.account_peppol_validity_last_check and partner.ubl_cii_format:
                participant_info = self._peppol_lookup_participant(f'{partner.peppol_eas}:{partner.peppol_endpoint}'.lower())
            else:
                participant_info = None

            if not partner.account_peppol_validity_last_check:
                partner.account_peppol_verification_label = 'not_verified'
            elif (
                partner.ubl_cii_format
                and participant_info is not None
                and not partner._check_document_type_support(participant_info, partner.ubl_cii_format)
            ):
                # the partner might exist on the network, but not be able to receive that specific format
                partner.account_peppol_verification_label = 'not_valid_format'
            elif partner.account_peppol_is_endpoint_valid:
                partner.account_peppol_verification_label = 'valid'
            else:
                partner.account_peppol_verification_label = 'not_valid'

    @api.depends(lambda self: self._peppol_eas_endpoint_depends())
    def _compute_ubl_cii_format(self):
        format_mapping = self._get_ubl_cii_formats()
        for partner in self:
            country_code = partner._deduce_country_code()
            if country_code in format_mapping:
                partner.ubl_cii_format = format_mapping[country_code]
            elif country_code in PEPPOL_DEFAULT_COUNTRIES and country_code in EAS_MAPPING:
                partner.ubl_cii_format = 'ubl_bis3'
            else:
                partner.ubl_cii_format = partner.ubl_cii_format

    @api.depends(lambda self: self._peppol_eas_endpoint_depends() + ['peppol_eas'])
    def _compute_peppol_endpoint(self):
        """ If the EAS changes and a valid endpoint is available, set it. Otherwise, keep the existing value."""
        for partner in self:
            partner.peppol_endpoint = partner.peppol_endpoint
            country_code = partner._deduce_country_code()
            if country_code in EAS_MAPPING:
                field = EAS_MAPPING[country_code].get(partner.peppol_eas)
                if field \
                        and field in partner._fields \
                        and partner[field] \
                        and not partner._build_error_peppol_endpoint(partner.peppol_eas, partner[field]):
                    partner.peppol_endpoint = partner[field]

    @api.depends(lambda self: self._peppol_eas_endpoint_depends())
    def _compute_peppol_eas(self):
        """
        If the country_code changes, recompute the EAS only if there is a country_code, it exists in the
        EAS_MAPPING, and the current EAS is not consistent with the new country_code.
        """
        for partner in self:
            partner.peppol_eas = partner.peppol_eas
            country_code = partner._deduce_country_code()
            if country_code in EAS_MAPPING:
                eas_to_field = EAS_MAPPING[country_code]
                if partner.peppol_eas not in eas_to_field:
                    new_eas = next(iter(EAS_MAPPING[country_code].keys()))
                    # Iterate on the possible EAS until a valid one is found
                    for eas, field in eas_to_field.items():
                        if field and field in partner._fields and partner[field]:
                            if not partner._build_error_peppol_endpoint(eas, partner[field]):
                                new_eas = eas
                                break
                    partner.peppol_eas = new_eas

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
        strip-trailing(base32(sha256(lowercase(ID-VALUE))),"=") + "." + ID-SCHEME + "." + SML-ZONE-NAME
        The lookup should be done on NAPTR DNS from 2025-11-01
        (ref:https://peppol.helger.com/public/locale-en_US/menuitem-docs-doc-exchange)
        """
        self.ensure_one()

        if not (self.peppol_eas and self.peppol_endpoint) or not self.ubl_cii_format:
            self.account_peppol_is_endpoint_valid = False
        else:
            edi_identification = f'{self.peppol_eas}:{self.peppol_endpoint}'.lower()
            self.account_peppol_validity_last_check = fields.Date.context_today(self)
            self.account_peppol_is_endpoint_valid = bool(self._check_peppol_participant_exists(edi_identification, ubl_cii_format=self.ubl_cii_format))

            if (
                not self.account_peppol_is_endpoint_valid
                and self.peppol_eas in ('0208', '9925')
            ):
                inverse_eas = '9925' if self.peppol_eas == '0208' else '0208'
                inverse_endpoint = f'BE{self.peppol_endpoint}' if self.peppol_eas == '0208' else self.peppol_endpoint[2:]
                if self._check_peppol_participant_exists(f'{inverse_eas}:{inverse_endpoint}', ubl_cii_format=self.ubl_cii_format):
                    self.peppol_eas = inverse_eas
                    self.peppol_endpoint = inverse_endpoint
                    self.account_peppol_is_endpoint_valid = True
        return False
