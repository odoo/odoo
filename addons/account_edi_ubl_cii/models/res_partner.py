# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from stdnum.fr import siret

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EAS_MAPPING
from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(
        selection_add=[
            ('facturx', "Factur-X (CII)"),
            ('ubl_bis3', "BIS Billing 3.0"),
            ('xrechnung', "XRechnung CIUS"),
            ('nlcius', "NLCIUS"),
            ('ubl_a_nz', "BIS Billing 3.0 A-NZ"),
            ('ubl_sg', "BIS Billing 3.0 SG"),
        ],
    )
    is_ubl_format = fields.Boolean(compute='_compute_is_ubl_format')
    is_peppol_edi_format = fields.Boolean(compute='_compute_is_peppol_edi_format')
    peppol_endpoint = fields.Char(
        string="Peppol Endpoint",
        help="Unique identifier used by the BIS Billing 3.0 and its derivatives, also known as 'Endpoint ID'.",
        compute="_compute_peppol_endpoint",
        store=True,
        readonly=False,
        tracking=True,
    )
    peppol_eas = fields.Selection(
        string="Peppol e-address (EAS)",
        help="""Code used to identify the Endpoint for BIS Billing 3.0 and its derivatives.
             List available at https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/""",
        compute="_compute_peppol_eas",
        store=True,
        readonly=False,
        tracking=True,
        selection=[
            ('9923', "Albania VAT - 9923"),
            ('9922', "Andorra VAT - 9922"),
            ('0151', "Australia ABN - 0151"),
            ('9914', "Austria UID - 9914"),
            ('9915', "Austria VOKZ - 9915"),
            ('0208', "Belgium CBE - 0208"),
            ('9925', "Belgium VAT - 9925"),
            ('9924', "Bosnia and Herzegovina VAT - 9924"),
            ('9926', "Bulgaria VAT - 9926"),
            ('9934', "Croatia VAT - 9934"),
            ('9928', "Cyprus VAT - 9928"),
            ('9929', "Czech Republic VAT - 9929"),
            ('0096', "Denmark CVR - 0096"),
            ('0184', "Denmark CVR - 0184"),
            ('0198', "Denmark SE - 0198"),
            ('0191', "Estonia Company code - 0191"),
            ('9931', "Estonia VAT - 9931"),
            ('0037', "Finland LY-tunnus - 0037"),
            ('0216', "Finland OVT code - 0216"),
            ('0213', "Finland VAT - 0213"),
            ('0002', "France SIRENE - 0002"),
            ('0009', "France SIRET - 0009"),
            ('9957', "France VAT - 9957"),
            ('0204', "Germany Leitweg-ID - 0204"),
            ('9930', "Germany VAT - 9930"),
            ('9933', "Greece VAT - 9933"),
            ('9910', "Hungary VAT - 9910"),
            ('0196', "Iceland Kennitala - 0196"),
            ('9935', "Ireland VAT - 9935"),
            ('0211', "Italia Partita IVA - 0211"),
            ('0097', "Italia FTI - 0097"),
            ('0188', "Japan SST - 0188"),
            ('0221', "Japan IIN - 0221"),
            ('9939', "Latvia VAT - 9939"),
            ('9936', "Liechtenstein VAT - 9936"),
            ('0200', "Lithuania JAK - 0200"),
            ('9937', "Lithuania VAT - 9937"),
            ('9938', "Luxemburg VAT - 9938"),
            ('9942', "Macedonia VAT - 9942"),
            ('0230', "Malaysia - 0230"),
            ('9943', "Malta VAT - 9943"),
            ('9940', "Monaco VAT - 9940"),
            ('9941', "Montenegro VAT - 9941"),
            ('0106', "Netherlands KvK - 0106"),
            ('0190', "Netherlands OIN - 0190"),
            ('9944', "Netherlands VAT - 9944"),
            ('0192', "Norway Org.nr. - 0192"),
            ('9945', "Poland VAT - 9945"),
            ('9946', "Portugal VAT - 9946"),
            ('9947', "Romania VAT - 9947"),
            ('9948', "Serbia VAT - 9948"),
            ('0195', "Singapore UEN - 0195"),
            ('9949', "Slovenia VAT - 9949"),
            ('9950', "Slovakia VAT - 9950"),
            ('9920', "Spain VAT - 9920"),
            ('0007', "Sweden Org.nr. - 0007"),
            ('9955', "Sweden VAT - 9955"),
            ('9927', "Swiss VAT - 9927"),
            ('0183', "Swiss UIDB - 0183"),
            ('9952', "Turkey VAT - 9952"),
            ('9932', "United Kingdom VAT - 9932"),
            ('9959', "USA EIN - 9959"),
            ('0060', "DUNS Number - 0060"),
            ('0088', "EAN Location Code - 0088"),
            ('0130', "Directorates of the European Commission - 0130"),
            ('0135', "SIA Object Identifiers - 0135"),
            ('0142', "SECETI Object Identifiers - 0142"),
            ('0193', "UBL.BE party identifier - 0193"),
            ('0199', "Legal Entity Identifier (LEI) - 0199"),
            ('0201', "Codice Univoco Unità  Organizzativa iPA - 0201"),
            ('0202', "Indirizzo di Posta Elettronica Certificata - 0202"),
            ('0209', "GS1 identification keys - 0209"),
            ('0210', "Codice Fiscale - 0210"),
            ('9913', "Business Registers Network - 9913"),
            ('9918', "S.W.I.F.T - 9918"),
            ('9919', "Kennziffer des Unternehmensregisters - 9919"),
            ('9951', "San Marino VAT - 9951"),
            ('9953', "Vatican VAT - 9953"),
        ]
    )

    @api.constrains('peppol_endpoint')
    def _check_peppol_fields(self):
        for partner in self:
            if partner.peppol_endpoint and partner.peppol_eas:
                error = self._build_error_peppol_endpoint(partner.peppol_eas, partner.peppol_endpoint)
                if error:
                    raise ValidationError(error)

    @api.model
    def _get_ubl_cii_formats(self):
        return list(self._get_ubl_cii_formats_info().keys())

    @api.model
    def _get_ubl_cii_formats_info(self):
        return {
            'ubl_bis3': {'countries': list(PEPPOL_DEFAULT_COUNTRIES), 'on_peppol': True, 'sequence': 200},
            'xrechnung': {'countries': ['DE'], 'on_peppol': True},
            'ubl_a_nz': {'countries': ['NZ', 'AU'], 'on_peppol': True},
            'nlcius': {'countries': ['NL'], 'on_peppol': True},
            'ubl_sg': {'countries': ['SG'], 'on_peppol': True},
            'facturx': {'countries': ['FR'], 'on_peppol': False},
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
        formats_info = self._get_ubl_cii_formats_info()
        format_mapping = self._get_ubl_cii_formats_by_country()
        country_code = self._deduce_country_code()
        if country_code in format_mapping:
            formats_by_country = format_mapping[country_code]
            # return the format with the smallest sequence
            if len(formats_by_country) == 1:
                return formats_by_country[0]
            else:
                return min(formats_by_country, key=lambda e: formats_info[e].get('sequence', 100))  # we use a sequence of 100 by default
        return False

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        return super()._get_suggested_invoice_edi_format() or self._get_suggested_ubl_cii_edi_format()

    @api.model
    def _get_peppol_formats(self):
        formats_info = self._get_ubl_cii_formats_info()
        return [format_key for format_key, format_vals in formats_info.items() if format_vals.get('on_peppol')]

    def _peppol_eas_endpoint_depends(self):
        # field dependencies of methods _compute_peppol_endpoint() and _compute_peppol_eas()
        # because we need to extend depends in l10n modules
        return ['country_code', 'vat', 'company_registry']

    @api.depends(lambda self: self._peppol_eas_endpoint_depends())
    def _compute_invoice_edi_format(self):
        # EXTENDS 'account' - add depends
        super()._compute_invoice_edi_format()

    @api.depends_context('company')
    @api.depends('invoice_edi_format')
    def _compute_is_ubl_format(self):
        for partner in self:
            partner.is_ubl_format = partner.invoice_edi_format in self._get_ubl_cii_formats()

    @api.depends_context('company')
    @api.depends('invoice_edi_format')
    def _compute_is_peppol_edi_format(self):
        for partner in self:
            partner.is_peppol_edi_format = partner.invoice_edi_format in self._get_peppol_formats()

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
                if partner.peppol_eas not in eas_to_field.keys():
                    new_eas = next(iter(EAS_MAPPING[country_code].keys()))
                    # Iterate on the possible EAS until a valid one is found
                    for eas, field in eas_to_field.items():
                        if field and field in partner._fields and partner[field]:
                            if not partner._build_error_peppol_endpoint(eas, partner[field]):
                                new_eas = eas
                                break
                    partner.peppol_eas = new_eas

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

    @api.model
    def _get_edi_builder(self, invoice_edi_format):
        if invoice_edi_format == 'xrechnung':
            return self.env['account.edi.xml.ubl_de']
        if invoice_edi_format == 'facturx':
            return self.env['account.edi.xml.cii']
        if invoice_edi_format == 'ubl_a_nz':
            return self.env['account.edi.xml.ubl_a_nz']
        if invoice_edi_format == 'nlcius':
            return self.env['account.edi.xml.ubl_nl']
        if invoice_edi_format == 'ubl_bis3':
            return self.env['account.edi.xml.ubl_bis3']
        if invoice_edi_format == 'ubl_sg':
            return self.env['account.edi.xml.ubl_sg']
