from odoo import _, models, tools

DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID = '320'

PAYMENT_MEANS_CODE = {
    # https://www.oioubl.info/codelists/en/urn_oioubl_codelist_paymentmeanscode-1.1.html
    'unknown': 1,
    'cash': 10,
    'cheque': 20,
    'debit': 31,
    'bank': 42,
    'card': 48,  # credit card
    'direct debit': 49,
    'compensation': 97,
}
UBL_TO_OIOUBL_TAX_CATEGORY_ID_MAPPING = {
    # Simple mapping between tax type provided in UBL and what is accepted in OIOUBL
    # https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/
    # https://www.oioubl.info/codelists/en/urn_oioubl_id_taxcategoryid-1.1.html
    'AE': 'ReverseCharge',
    'E': 'ZeroRated',
    'S': 'StandardRated',
    'Z': 'ZeroRated',
    'G': 'ZeroRated',
    'O': 'ZeroRated',
    'K': 'ReverseCharge',
    'L': 'ZeroRated',
    'M': 'ZeroRated',
}
EAS_SCHEME_ID_MAPPING = {
    '0007': 'SE:ORGNR',
    '0009': 'FR:SIRET',
    '0060': 'DUNS',
    '0088': 'GLN',
    '0096': 'DK:P',
    '0097': 'IT:FTI',
    '0135': 'IT:SIA',
    '0142': 'IT:SECETI',
    '0184': 'DK:CVR',
    '0192': 'NO:ORGNR',
    '0196': 'IS:KT',
    '0198': 'DK:SE',
    '0201': 'IT:IPA',
    '0208': 'BE:VAT',
    '0210': 'IT:CF',
    '0211': 'IT:VAT',
    '0212': 'FI:ORGNR',
    '0213': 'FI:VAT',
    '0216': 'FI:OVT',
    '9955': 'SE:VAT',
    '9910': 'HU:VAT',
    '9915': 'AT:VAT',
    '9918': 'IBAN',
    '9919': 'AT:KUR',
    '9920': 'ES:VAT',
    '9922': 'AD:VAT',
    '9923': 'AL:VAT',
    '9924': 'BA:VAT',
    '9925': 'BE:VAT',
    '9926': 'BG:VAT',
    '9927': 'CH:VAT',
    '9928': 'CY:VAT',
    '9929': 'CZ:VAT',
    '9930': 'DE:VAT',
    '9931': 'EE:VAT',
    '9932': 'GB:VAT',
    '9933': 'GR:VAT',
    '9934': 'HR:VAT',
    '9935': 'IE:VAT',
    '9936': 'LI:VAT',
    '9937': 'LT:VAT',
    '9938': 'LU:VAT',
    '9939': 'LV:VAT',
    '9940': 'MC:VAT',
    '9941': 'ME:VAT',
    '9942': 'MK:VAT',
    '9943': 'MT:VAT',
    '9944': 'NL:VAT',
    '9945': 'PL:VAT',
    '9946': 'PT:VAT',
    '9947': 'RO:VAT',
    '9948': 'RS:VAT',
    '9949': 'SI:VAT',
    '9950': 'SK:VAT',
    '9951': 'SM:VAT',
    '9952': 'TR:VAT',
    '9953': 'VA:VAT',
}


def format_vat_number(partner):
    vat = (partner.vat or '').replace(' ', '')
    if vat[:2].isnumeric():
        vat = partner.country_code.upper() + vat
    return vat


class AccountEdiXmlOioubl_201(models.AbstractModel):
    _name = 'account.edi.xml.oioubl_201'
    _inherit = ['account.edi.xml.ubl_20']
    _description = "OIOUBL 2.01"

    # Data validation Schematron available at the following URL:
    # https://rep.erst.dk/git/openebusiness/common/-/tree/master/resources/Schematrons/OIOUBL

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_oioubl_201.xml"

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_20
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            building_number = tools.street_split(partner.street).get('street_number')
            if not building_number:
                constraints[f"oioubl201_{partner_type}_building_number_required"] = \
                        _("The following partner's street number is missing: %s", partner.display_name)
            if partner.country_code == "FR" and not partner.commercial_partner_id.company_registry:
                constraints["oioubl201_company_registry_required_for_french_partner"] = \
                        _("The company registry is required for french partner: %s", partner.display_name)
            constraints[f'oioubl201_{partner_type}_vat_required'] = self._check_required_fields(partner.commercial_partner_id, 'vat')

        return constraints

    def _get_currency_decimal_places(self, currency_id):
        # OIOUBL needs the data to be formated to 2 decimals
        return 2

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        document_node.update({
            'cbc:CustomizationID': {'_text': 'OIOUBL-2.01'},

            # ProfileID is the property that defines which documents the company can send and receive
            # 'Procurement-BilSim-1.0' is the simplest one: invoice and bill
            # https://www.oioubl.info/documents/en/en/Guidelines/OIOUBL_GUIDE_PROFILES.pdf
            'cbc:ProfileID': {
                '_text': 'Procurement-BilSim-1.0',
                'schemeID': 'urn:oioubl:id:profileid-1.6',
                'schemeAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,
            },

            'cbc:InvoiceTypeCode': {
                '_text': 380,
                'listID': 'urn:oioubl:codelist:invoicetypecode-1.2',
                'listAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,
            } if vals['document_type'] == 'invoice' else None,
        })

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_20
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']

        # Hardcoded 'unknown' for now
        # Later on, it would be nice to create a dynamically selected template that would depends on the payment means
        payment_means_node['cbc:PaymentMeansCode']['_text'] = PAYMENT_MEANS_CODE['unknown']

        invoice = vals['invoice']
        supplier = vals['supplier']
        if (
            invoice.partner_bank_id in supplier.bank_ids
            and payment_means_node.get('cac:PayeeFinancialAccount')
            and payment_means_node['cac:PayeeFinancialAccount'].get('cac:FinancialInstitutionBranch')
            and payment_means_node['cac:PayeeFinancialAccount']['cac:FinancialInstitutionBranch'].get('cac:FinancialInstitution')
        ):
            payment_means_node['cac:PayeeFinancialAccount']['cac:FinancialInstitutionBranch']['cac:FinancialInstitution']['cac:Address'] = None

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        # OVERRIDES 'account_edi_ubl_cii'
        invoice = vals['invoice']
        if not invoice.invoice_payment_term_id:
            return

        sign = 1 if invoice.is_inbound(include_receipts=True) else -1
        document_node['cac:PaymentTerms'] = [
            {
                'cbc:ID': {'_text': line.id},
                'cbc:Amount': {
                    '_text': self.format_float(sign * line.amount_currency, self._get_currency_decimal_places(line.currency_id)),
                    'currencyID': line.currency_id.name
                },
                'cac:SettlementPeriod': {
                    'cbc:StartDate': {'_text': invoice.invoice_date},
                    'cbc:EndDate': {'_text': line.date_maturity},
                }
            }
            for line in invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term').sorted('date_maturity')
        ]

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]

        # In OIOUBL context, tax_exclusive_amount means "tax only"
        tax_exclusive_amount = monetary_total_node['cbc:TaxInclusiveAmount']['_text'] - monetary_total_node['cbc:TaxExclusiveAmount']['_text']
        monetary_total_node['cbc:TaxExclusiveAmount'] = {
            '_text': self.format_float(tax_exclusive_amount, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }
        monetary_total_node['cbc:PrepaidAmount'] = None

    def _get_address_node(self, vals):
        # https://www.oioubl.info/Classes/en/Address.html
        partner = vals['partner']
        model = vals.get('model', 'res.partner')
        country = partner['country' if model == 'res.bank' else 'country_id']
        state = partner['state' if model == 'res.bank' else 'state_id']
        address = tools.street_split(partner.street)

        return {
            'cbc:AddressFormatCode': {
                '_text': 'StructuredDK',
                'listAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,
                'listID': 'urn:oioubl:codelist:addressformatcode-1.1',
            },
            'cbc:StreetName': {'_text': address.get('street_name')},
            'cbc:BuildingNumber': {'_text': address.get('street_number')},
            'cbc:AdditionalStreetName': {'_text': partner.street2},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name},
            'cbc:CountrySubentityCode': {'_text': state.code},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.name},
            },
        }

    def _get_party_node(self, vals):
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id
        vat = format_vat_number(commercial_partner)

        if partner.peppol_endpoint and partner.peppol_eas in EAS_SCHEME_ID_MAPPING:
            # if we don't know the mapping with real names for the Peppol Endpoint, fallback on VAT simply
            endpoint_id = partner.peppol_endpoint
            scheme_id = EAS_SCHEME_ID_MAPPING[partner.peppol_eas]
            if (scheme_id in ('DK:CVR', 'FR:SIRET') or scheme_id[3:] == 'VAT') and endpoint_id.isnumeric():
                endpoint_id = scheme_id[:2] + endpoint_id
        else:
            endpoint_id = format_vat_number(partner)
            country_code = endpoint_id[:2]
            match country_code:
                case 'DK':
                    scheme_id = 'DK:CVR'
                case 'FR':
                    scheme_id = 'FR:SIRET'
                    # SIRET is the french company registry
                    endpoint_id = (partner.company_registry or "").replace(" ", "")
                case _:
                    scheme_id = f'{country_code}:VAT'

        return {
            'cbc:EndpointID': {
                # list of possible endpointID available at
                # https://www.oioubl.info/documents/en/en/Guidelines/OIOUBL_GUIDE_ENDPOINT.pdf
                '_text': endpoint_id,
                'schemeID': scheme_id,
            },
            'cbc:IndustryClassificationCode': None,
            'cac:PartyIdentification': [
                {
                    'cbc:ID': {
                        '_text': party_vals.get('id'),
                        'schemeName': party_vals.get('id_attrs', {}).get('schemeName'),
                        'schemeID': party_vals.get('id_attrs', {}).get('schemeID'),
                    }
                }
                for party_vals in vals.get('party_identification_vals', [])
            ],
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': vat,
                    # SE is the danish vat number
                    # DK:SE indicates we're using it and 'ZZZ' is for international number
                    # https://www.oioubl.info/Codelists/en/urn_oioubl_scheme_partytaxschemecompanyid-1.1.html
                    'schemeID': 'DK:SE' if vat[:2] == 'DK' else 'ZZZ',
                },
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
                'cac:TaxScheme': {
                    # [BR-CO-09] if the PartyTaxScheme/TaxScheme/ID == 'VAT', CompanyID must start with a country code prefix.
                    # In some countries however, the CompanyID can be with or without country code prefix and still be perfectly
                    # valid (RO, HU, non-EU countries).
                    # We have to handle their cases by changing the TaxScheme/ID to 'something other than VAT',
                    # preventing the trigger of the rule.
                    'cbc:ID': {
                        '_text': 'VAT',
                        # the doc says it could be empty but the schematron says otherwise
                        # https://www.oioubl.info/Classes/en/TaxScheme.html
                        'schemeID': 'urn:oioubl:id:taxschemeid-1.5',
                    },
                    'cbc:Name': {'_text': 'VAT'},
                },
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': vat,
                    'schemeID': 'DK:CVR' if vat[:2] == 'DK' else 'ZZZ',
                },
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            }
        }

    def _get_document_type_code_node(self, invoice, invoice_data):
        # http://www.datypic.com/sc/ubl20/e-cbc_DocumentTypeCode.html
        return {
            '_text': '380' if invoice.move_type == 'out_invoice' else '381',
            'listAgencyID': '6',
            'listID': 'UN/ECE 1001',
        }

    def _get_tax_category_node(self, vals):
        # TaxCategory id list: https://www.oioubl.info/codelists/en/urn_oioubl_id_taxcategoryid-1.1.html
        grouping_key = vals['grouping_key']
        grouping_key = {**grouping_key, 'tax_category_code': UBL_TO_OIOUBL_TAX_CATEGORY_ID_MAPPING.get(grouping_key['tax_category_code'])}
        tax_category_node = super()._get_tax_category_node({**vals, 'grouping_key': grouping_key})

        # TaxCategory https://www.oioubl.info/Classes/en/TaxCategory.html
        tax_category_node['cbc:ID']['schemeID'] = 'urn:oioubl:id:taxcategoryid-1.3'
        tax_category_node['cbc:ID']['schemeAgencyID'] = DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID

        tax_category_node['cac:TaxScheme']['cbc:ID']['schemeID'] = 'urn:oioubl:id:taxschemeid-1.5'
        tax_category_node['cac:TaxScheme']['cbc:Name'] = {'_text': 'VAT'}

        return tax_category_node

    def _get_tax_subtotal_node(self, vals):
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cbc:Percent'] = None
        return tax_subtotal_node
