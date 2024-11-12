# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from stdnum.fr import siret

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EAS_MAPPING


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
            ('0002', "0002 - System Information et Repertoire des Entreprise et des Etablissements: SIRENE"),
            ('0007', "0007 - Organisationsnummer (Swedish legal entities)"),
            ('0009', "0009 - SIRET-CODE"),
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
            ('0216', "0216 - OVTcode"),
            ('0221', "0221 - The registered number of the qualified invoice issuer (Japan)"),
            ('0230', "0230 - National e-Invoicing Framework (Malaysia)"),
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
            ('9957', "9957 - French VAT number"),
            ('9959', "9959 - Employer Identification Number (EIN, USA)"),
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
            'ubl_bis3': {'countries': list(EAS_MAPPING), 'on_peppol': True, 'sequence': 200},
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
