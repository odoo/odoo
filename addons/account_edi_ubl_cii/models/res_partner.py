# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.exceptions import (
    UserError,
    ValidationError,
)
from odoo.tools.partner_identifiers import (
    pick_preferred_identifier,
    validation_error_message,
)

from odoo.addons.account_edi_ubl_cii.tools.partner_identifiers import (
    ISO_IDENTIFIERS_METADATA,
    validate_participant_identifier,
)
from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(
        selection_add=[
            ('facturx', "France (FacturX)"),
            ('ubl_bis3', "EU Standard (Peppol Bis 3.0)"),
            ('zugferd', "Germany (ZUGFeRD)"),
            ('xrechnung', "Germany (XRechnung)"),
            ('nlcius', "Netherlands (NLCIUS)"),
            ('ubl_a_nz', "Australia (BIS Billing 3.0 A-NZ)"),
            ('ubl_sg', "Singapore (BIS Billing 3.0 SG)"),
        ],
    )
    is_ubl_format = fields.Boolean(compute='_compute_is_ubl_format')
    routing_scheme = fields.Selection(
        string="Routing ID",
        compute="_compute_routing_scheme_endpoint",
        store=True,
        readonly=False,
        tracking=True,
        selection=[
            ('9923', "Albania VAT"),
            ('9922', "Andorra VAT"),
            ('0151', "Australia ABN"),
            ('9914', "Austria UID"),
            ('9915', "Austria VOKZ"),
            ('0208', "Belgian Company Registry"),
            ('9925', "Belgian VAT"),
            ('9924', "Bosnia and Herzegovina VAT"),
            ('9926', "Bulgaria VAT"),
            ('9934', "Croatia VAT"),
            ('9928', "Cyprus VAT"),
            ('9929', "Czech Republic VAT"),
            ('0096', "Denmark P"),
            ('0184', "Denmark CVR"),
            ('0198', "Denmark SE"),
            ('0191', "Estonia Company code"),
            ('9931', "Estonia VAT"),
            ('0037', "Finland LY-tunnus"),
            ('0216', "Finland OVT code"),
            ('0213', "Finland VAT"),
            ('0002', "France SIRENE"),
            ('0009', "France SIRET"),
            ('9957', "France VAT"),
            ('0225', "France FRCTC Electronic Address"),
            ('0240', "France Register of legal persons"),
            ('0246', "German Electronic Business Address"),
            ('0204', "Germany Leitweg-ID"),
            ('9930', "Germany VAT"),
            ('9933', "Greece VAT"),
            ('9910', "Hungary VAT"),
            ('0196', "Iceland Kennitala"),
            ('9935', "Ireland VAT"),
            ('0211', "Italia Partita IVA"),
            ('0097', "Italia FTI"),
            ('0188', "Japan SST"),
            ('0221', "Japan IIN"),
            ('0218', "Latvia Unified registration number"),
            ('9939', "Latvia VAT"),
            ('9936', "Liechtenstein VAT"),
            ('0200', "Lithuania JAK"),
            ('9937', "Lithuania VAT"),
            ('9938', "Luxembourg VAT"),
            ('9942', "Macedonia VAT"),
            ('0230', "Malaysia"),
            ('9943', "Malta VAT"),
            ('9940', "Monaco VAT"),
            ('9941', "Montenegro VAT"),
            ('0106', "Netherlands KvK"),
            ('0190', "Netherlands OIN"),
            ('9944', "Netherlands VAT"),
            ('0244', "Nigeria Tax Identification"),
            ('0192', "Norway Org.nr."),
            ('9945', "Poland VAT"),
            ('9946', "Portugal VAT"),
            ('9947', "Romania VAT"),
            ('9948', "Serbia VAT"),
            ('0195', "Singapore UEN"),
            ('0245', "SK Tax identification number (DIČ)"),
            ('9949', "Slovenia VAT"),
            ('9950', "Slovakia VAT"),
            ('9920', "Spain VAT"),
            ('0007', "Sweden Org.nr."),
            ('9955', "Sweden VAT"),
            ('9927', "Swiss VAT"),
            ('0183', "Swiss UIDB"),
            ('9952', "Turkey VAT"),
            ('0235', "UAE Tax Identification Number (TIN)"),
            ('9932', "United Kingdom VAT"),
            ('9959', "USA EIN"),
            ('0060', "DUNS Number"),
            ('0088', "EAN Location Code"),
            ('0130', "Directorates of the European Commission"),
            ('0135', "SIA Object Identifiers"),
            ('0142', "SECETI Object Identifiers"),
            ('0193', "UBL.BE party identifier"),
            ('0199', "Legal Entity Identifier (LEI)"),
            ('0201', "Codice Univoco Unità Organizzativa iPA"),
            ('0202', "Indirizzo di Posta Elettronica Certificata"),
            ('0209', "GS1 identification keys"),
            ('0210', "Codice Fiscale"),
            ('9913', "Business Registers Network"),
            ('9918', "S.W.I.F.T"),
            ('9919', "Kennziffer des Unternehmensregisters"),
            ('9951', "San Marino VAT"),
            ('9953', "Vatican VAT"),
            ('AN', "O.F.T.P. (ODETTE File Transfer Protocol)"),
            ('AQ', "X.400 address for mail text"),
            ('AS', "AS2 exchange"),
            ('AU', "File Transfer Protocol"),
            ('EM', "Electronic mail"),
        ],
    )
    routing_endpoint = fields.Char(
        string="Routing Endpoint",
        compute="_compute_routing_scheme_endpoint",
        store=True,
        readonly=False,
        tracking=True,
    )
    routing_identifier = fields.Char(
        string="EDI Routing Address",
        compute='_compute_routing_identifier',
        inverse='_inverse_routing_identifier',
    )
    available_routing_schemes = fields.Json(compute='_compute_available_routing_schemes')

    @api.depends_context('company')
    @api.depends('invoice_edi_format')
    def _compute_is_ubl_format(self):
        for partner in self:
            partner.is_ubl_format = partner.invoice_edi_format in self._get_ubl_cii_formats()

    @api.depends('vat', 'additional_identifiers', 'country_id')
    def _compute_routing_scheme_endpoint(self):
        for partner in self:
            identifier_vals = partner._get_preferred_routing_identifier_vals(force_recompute=True)
            partner.routing_scheme = identifier_vals.get('scheme') or False
            partner.routing_endpoint = identifier_vals.get('value') or False

    @api.depends('routing_scheme', 'routing_endpoint')
    def _compute_routing_identifier(self):
        for partner in self:
            partner.routing_identifier = (
                f'{partner.routing_scheme}:{partner.routing_endpoint}'
                if partner.routing_scheme and partner.routing_endpoint
                else False
            )

    def _inverse_routing_identifier(self):
        for partner in self:
            routing_identifier = partner.routing_identifier or ''
            scheme, sep, endpoint = routing_identifier.partition(':')
            if routing_identifier and not sep:
                raise UserError(self.env._("Routing identifier should be in the format 'SCHEME:ENDPOINT'."))
            if scheme and endpoint:  # validated through '_clean_routing_endpoint'.
                partner.write({'routing_scheme': scheme, 'routing_endpoint': endpoint})
            else:
                partner.write({'routing_scheme': False, 'routing_endpoint': False})

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_available_routing_schemes(self):
        # TO OVERRIDE
        self.available_routing_schemes = list(dict(self._fields['routing_scheme'].selection))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._clean_routing_endpoint(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._clean_routing_endpoint(vals, partners=self)
        return super().write(vals)

    def _clean_routing_endpoint(self, vals, partners=None):
        """ Pre-create/write on a `vals` dict:
        - normalize
        - reject malformed values (raises ValidationError)
        Mutates `vals` in place.
        """
        if (scheme := vals.get('routing_scheme')) and (endpoint := vals.get('routing_endpoint')):
            result = validate_participant_identifier(scheme, endpoint)
            if not result['valid']:
                raise ValidationError(validation_error_message(self.env, result['key'], result['example']))
            vals['routing_endpoint'] = result['value']

    def _get_all_identifiers(self, enrich=False):
        # EXTENDS 'account'
        all_identifiers = super()._get_all_identifiers(enrich)
        if enrich and self.routing_identifier and (metadata := ISO_IDENTIFIERS_METADATA.get(self.routing_scheme)) and metadata['key'] not in all_identifiers:
            all_identifiers[metadata['key']] = self.routing_endpoint
        return all_identifiers

    def _get_preferred_routing_identifier_vals(self, force_recompute=False):
        """Returns a dict {'scheme': scheme, 'value': value, ...metadata} of the preferred identifier for the given partner.
        - When `partner.routing_identifier` is set, return it.
        - Otherwise picks the lowest-sequence identifier carrying an ISO scheme from `_get_all_identifiers(enrich=True)`.
        - Returns empty dict when nothing routable is available.
        """
        self.ensure_one()
        partner = self.commercial_partner_id or self  # if it's a new record, the commercial can be empty
        if not force_recompute and partner.routing_scheme and partner.routing_endpoint and partner.routing_scheme in ISO_IDENTIFIERS_METADATA:
            return {'scheme': partner.routing_scheme, 'value': partner.routing_endpoint}
        identifier_vals = pick_preferred_identifier(
            partner._get_all_identifiers(enrich=True),
            filter_func=lambda k, v, m: m.get('scheme') in ISO_IDENTIFIERS_METADATA and v,
            sort_key=lambda k, v, m: (m.get('sequence', 100), k),
        )
        return identifier_vals or {}

    @api.model
    def _get_ubl_cii_formats(self):
        return list(self._get_ubl_cii_formats_info().keys())

    @api.model
    def _get_ubl_cii_formats_info(self):
        return {
            'ubl_bis3': {
                'countries': list(PEPPOL_DEFAULT_COUNTRIES),
                'on_peppol': True,
                'sequence': 200,
                'embed_attachments': True,
            },
            'xrechnung': {'countries': ['DE'], 'sequence': 200, 'on_peppol': True},
            'ubl_a_nz': {'countries': ['NZ', 'AU'], 'on_peppol': False},  # Not yet available through Odoo's Access Point, although it's a Peppol valid format
            'nlcius': {'countries': ['NL'], 'on_peppol': True},
            'ubl_sg': {'countries': ['SG'], 'on_peppol': False},  # Same.
            'facturx': {'countries': ['FR'], 'on_peppol': False},
            'zugferd': {'countries': ['DE'], 'on_peppol': False},
        }

    @api.model
    def _get_ubl_cii_formats_by_country(self):
        formats_info = self._get_ubl_cii_formats_info()
        countries = {country for format_val in formats_info.values() for country in (format_val.get('countries') or [])}
        return {
            country_code: [
                format_key
                for format_key, format_val in formats_info.items() if country_code in (format_val.get('countries') or [])
            ]
            for country_code in countries
        }

    def _get_suggested_ubl_cii_edi_format(self):
        self.ensure_one()
        format_mapping = self._get_ubl_cii_formats_by_country()
        country_code = self.commercial_partner_id._deduce_country_code()
        if country_code in format_mapping:
            formats_by_country = format_mapping[country_code]
            # return the format with the smallest sequence
            if len(formats_by_country) == 1:
                return formats_by_country[0]
            # Prefer xrechnung when the partner has a Leitweg-ID (B2G in Germany).
            if 'DE_LTW' in self.commercial_partner_id._get_all_identifiers(enrich=True):
                return 'xrechnung'
            formats_info = self._get_ubl_cii_formats_info()
            return min(formats_by_country, key=lambda e: formats_info[e].get('sequence', 100))  # we use a sequence of 100 by default
        return False

    def _get_ubl_cii_edi_format(self):
        self.ensure_one()
        return self.invoice_edi_format or self._get_suggested_ubl_cii_edi_format()

    def _get_suggested_peppol_edi_format(self):
        self.ensure_one()
        suggested_format = self.commercial_partner_id._get_suggested_ubl_cii_edi_format()
        return suggested_format if suggested_format in self.env['res.partner']._get_peppol_formats() else 'ubl_bis3'

    def _get_peppol_edi_format(self):
        self.ensure_one()
        return self.invoice_edi_format or self._get_suggested_peppol_edi_format()

    @api.model
    def _get_peppol_formats(self):
        formats_info = self._get_ubl_cii_formats_info()
        return [format_key for format_key, format_vals in formats_info.items() if format_vals.get('on_peppol')]

    @api.model
    def _get_edi_builder(self, invoice_edi_format):
        if invoice_edi_format == 'xrechnung':
            return self.env['account.edi.xml.ubl_de']
        # Same template for the two formats (France and Germany)
        if invoice_edi_format in ('facturx', 'zugferd'):
            return self.env['account.edi.xml.cii']
        if invoice_edi_format == 'ubl_a_nz':
            return self.env['account.edi.xml.ubl_a_nz']
        if invoice_edi_format == 'nlcius':
            return self.env['account.edi.xml.ubl_nl']
        if invoice_edi_format == 'ubl_bis3':
            return self.env['account.edi.xml.ubl_bis3']
        if invoice_edi_format == 'ubl_sg':
            return self.env['account.edi.xml.ubl_sg']

    @api.model
    def _import_retrieve_customer_from_routing_identifier(self, customer_values):
        routing_scheme = customer_values.get('routing_scheme')
        routing_endpoint = customer_values.get('routing_endpoint')
        if not routing_scheme or not routing_endpoint:
            return

        return {
            'criteria': [{
                'domain': [('routing_scheme', '=', routing_scheme), ('routing_endpoint', '=', routing_endpoint)],
            }],
        }
