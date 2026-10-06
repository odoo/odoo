# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from datetime import datetime, UTC

from lxml import etree

from odoo import api, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

# Far from ideal, but no better solution yet.
COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}
E_164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class AccountEdiXmlUBLMyInvoisMY(models.AbstractModel):
    """
    * MyInvois API formats doc: https://sdk.myinvois.hasil.gov.my/documents
    """
    _inherit = "account.edi.ubl"
    _name = 'account.edi.xml.ubl_myinvois_my'
    _description = "Malaysian implementation of ubl for the MyInvois portal"

    # -----------------------
    # EXPORT
    # -----------------------

    def _export_myinvois_document(self, myinvois_document):
        """
        Entry point of the export of a MyInvois document.
        The returned values contain the 'document_node' to pass to dict_to_xml in order to generate the XML file to send
        to MyInvois, as well as the 'constraints' it failed.
        """
        vals = self._init_myinvois_document_export_values(myinvois_document)
        return self._export_document(vals)

    def _init_myinvois_document_export_values(self, myinvois_document):
        vals = {'myinvois_document': myinvois_document}

        # Even credit, debit and refund notes are sent as an Invoice, only the InvoiceTypeCode changes.
        self._define_document_type(vals, 'invoice')
        self._ubl_add_values_company(vals, myinvois_document.company_id)
        self._ubl_add_values_currency(vals, myinvois_document.currency_id)
        self._add_myinvois_document_config_vals(vals)

        vals['base_lines'] = myinvois_document._get_rounded_base_lines()
        self._ubl_setup_base_lines(vals)
        self._add_myinvois_document_monetary_total_vals(vals)
        return vals

    def _ubl_setup_base_lines(self, vals):
        # As we group lines together when consolidating, we lose the discount percentage in the process.
        # During the grouping, we stored the actual amount in the base line, so we turn it back into a percentage.
        for base_line in vals['base_lines']:
            discount_amount = base_line.get('discount_amount_currency')
            gross_amount = base_line['price_unit'] * base_line['quantity']
            if discount_amount and not base_line['discount'] and gross_amount:
                base_line['discount'] = discount_amount / gross_amount * 100.0
        super()._ubl_setup_base_lines(vals)

    def _add_myinvois_document_config_vals(self, vals):
        myinvois_document = vals['myinvois_document']
        supplier = myinvois_document.company_id.partner_id.commercial_partner_id

        if myinvois_document._is_consolidated_invoice() or myinvois_document._is_consolidated_invoice_refund():
            customer = self.env["res.partner"].search(
                domain=[
                    *self.env['res.partner']._check_company_domain(myinvois_document.company_id),
                    '|',
                    ('vat', '=', 'EI00000000010'),
                    ('l10n_my_edi_malaysian_tin', '=', 'EI00000000010'),
                ],
                limit=1,
            )

            if not customer and myinvois_document._is_consolidated_invoice():
                # This could happen if the General Public partner wasn't loaded, or was deleted.
                # To keep it simple, we will simply use a temporary partner record with the same data for that case.
                customer = self.env['res.partner'].new({
                    'name': 'General Public',
                    'vat': 'EI00000000010',
                    'country_id': self.env.ref('base.my'),
                    'state_id': self.env.ref('base.state_my_jhr'),
                    'phone': 'NA',
                    'street': 'NA',
                    'city': 'NA',
                    'l10n_my_identification_type': 'BRN',
                    'l10n_my_identification_number': 'NA',
                    'l10n_my_edi_industrial_classification': self.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False),
                })

            payment_term_id = None  # wouldn't make sense in a consolidated invoice.
        else:
            invoice = myinvois_document.invoice_ids[0]  # Otherwise it would be a consolidated invoice.
            customer = invoice.partner_id
            payment_term_id = invoice.invoice_payment_term_id

        document_type_code, original_documents = self._l10n_my_edi_get_document_type_code(myinvois_document)
        # In case of self billing, we want to invert the supplier and customer.
        if document_type_code in ("11", "12", "13", "14"):
            supplier, customer = customer, supplier
            document_ref = ','.join([invoice.ref for invoice in myinvois_document.invoice_ids if invoice.ref]) or None
        else:
            document_ref = None

        self._ubl_add_values_supplier(vals, supplier)
        self._ubl_add_values_customer(vals, customer)
        vals.update({
            'document_type_code': document_type_code,
            'original_documents': original_documents,
            'document_name': myinvois_document.name,
            'custom_form_reference': myinvois_document.myinvois_custom_form_reference,
            'document_ref': document_ref,
            'incoterm_id': myinvois_document.invoice_ids.invoice_incoterm_id,
            'invoice_payment_term_id': payment_term_id,
        })

    def _add_myinvois_document_monetary_total_vals(self, vals):
        vals['total_paid_amount_currency'] = 0.0
        myinvois_document = vals["myinvois_document"]
        if myinvois_document.invoice_ids:
            # Add the total amount paid.
            # Genuine prepayments only: any reconciled payment, regardless of its date, is not a deposit.
            vals['total_paid_amount_currency'] = sum(
                self._l10n_my_edi_get_prepaid_amount(invoice)
                for invoice in myinvois_document.invoice_ids
            )

    # -------------------------------------------------------------------------
    # EXPORT: Document nodes
    # -------------------------------------------------------------------------

    def _fill_document_values_invoice(self, vals):
        super()._fill_document_values_invoice(vals)
        self._add_myinvois_document_billing_reference_nodes(vals)
        self._add_myinvois_document_additional_document_reference_nodes(vals)
        self._add_myinvois_document_exchange_rate_nodes(vals)
        self._add_myinvois_document_monetary_total_nodes(vals)

    def _ubl_add_id_node(self, vals):
        vals['document_node']['cbc:ID'] = {'_text': vals['document_name']}

        # Self-billed invoices must use the number given by the supplier.
        if vals['document_type_code'] in ('11', '12', '13', '14') and vals['document_ref'] and not vals['myinvois_document']._is_consolidated_invoice():
            vals['document_node']['cbc:ID']['_text'] = vals['document_ref']

    def _ubl_add_issue_date_node(self, vals):
        # The issue date and time must be the current time set in the UTC time zone
        now = datetime.now(tz=UTC)
        vals['document_node']['cbc:IssueDate'] = {'_text': now.strftime("%Y-%m-%d")}
        vals['document_node']['cbc:IssueTime'] = {'_text': now.strftime("%H:%M:%SZ")}

    def _ubl_add_due_date_node(self, vals):
        vals['document_node']['cbc:DueDate'] = {'_text': None}

    def _ubl_add_invoice_type_code_node(self, vals):
        # The current version is 1.1 (document with signature), the type code depends on the move type.
        vals['document_node']['cbc:InvoiceTypeCode'] = {
            '_text': vals['document_type_code'],
            'listVersionID': '1.1',
        }

    def _ubl_add_document_currency_code_node(self, vals):
        self._ubl_add_document_currency_code_node_foreign_currency(vals)

    def _ubl_add_buyer_reference_node(self, vals):
        vals['document_node']['cbc:BuyerReference'] = {'_text': vals['customer'].commercial_partner_id.ref}

    def _ubl_add_order_reference_node(self, vals):
        vals['document_node']['cac:OrderReference'] = None

    def _add_myinvois_document_billing_reference_nodes(self, vals):
        """ Debit/Credit note original invoice ref.

        Applies to credit notes, debit notes, refunds for both invoices and self-billed invoices.
        The original document is mandatory; but in some specific cases it will be empty (sending a credit note for an
        invoice managed outside Odoo/...)
        """
        def _get_original_document_id(original_document):
            if original_document:
                if original_document.myinvois_file_id:
                    decoded_vals = self._l10n_my_edi_decode_myinvois_attachment(original_document.myinvois_file_id)
                    return decoded_vals.get('original_document_id')
                original_invoice = original_document.invoice_ids[:1]
                if vals['document_type_code'] in {'12', '13', '14'} and original_invoice.ref:
                    return original_invoice.ref
                if original_document.name:
                    return original_document.name
            return None

        nodes = vals['document_node']['cac:BillingReference'] = []
        if vals['document_type_code'] in {'02', '03', '04', '12', '13', '14'}:
            for original_document in vals['original_documents'] or [None]:
                nodes.append({
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': _get_original_document_id(original_document) or 'NA'},
                        'cbc:UUID': {'_text': (original_document and original_document.myinvois_external_uuid) or 'NA'},
                    }
                })

    def _add_myinvois_document_additional_document_reference_nodes(self, vals):
        vals['document_node']['cac:AdditionalDocumentReference'] = [
            {
                'cbc:ID': {'_text': vals['custom_form_reference']},
                'cbc:DocumentType': {'_text': 'CustomsImportForm'},
            } if vals['document_type_code'] in {'11', '12', '13', '14'} and vals['custom_form_reference'] else None,
            {
                'cbc:ID': {'_text': vals["incoterm_id"].code}
            } if vals["incoterm_id"] else None,
            {
                'cbc:ID': {'_text': vals['custom_form_reference']},
                'cbc:DocumentType': {'_text': 'K2'},
            } if vals['document_type_code'] in {'01', '02', '03', '04'} and vals['custom_form_reference'] else None,
        ]

    def _add_myinvois_document_exchange_rate_nodes(self, vals):
        currency = vals['currency']
        if currency.name != 'MYR':
            # I couldn't find any information on maximum precision, so we will use the currency format.
            total_amount_in_company_currency = total_amount_in_currency = 0.0
            for base_line in vals['base_lines']:
                total_amount_in_company_currency += base_line['tax_details']['raw_total_included']
                total_amount_in_currency += base_line['tax_details']['raw_total_included_currency']
            # We recalculate the rate so that it works in any cases, even when using consolidated invoices.
            rate = self.env.ref('base.MYR').round(abs(total_amount_in_company_currency) / (total_amount_in_currency or 1))
            # Exchange rate information must be provided if applicable
            vals['document_node']['cac:TaxExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': currency.name},
                'cbc:TargetCurrencyCode': {'_text': 'MYR'},
                'cbc:CalculationRate': {'_text': rate},
            }

    def _ubl_add_payment_terms_nodes(self, vals):
        nodes = vals['document_node']['cac:PaymentTerms'] = []

        payment_term = vals['invoice_payment_term_id']
        if (
            payment_term
            and not vals['myinvois_document']._is_consolidated_invoice()
            and (payment_terms_node := self._ubl_get_payment_terms_node_from_payment_term(vals, payment_term))
        ):
            nodes.append(payment_terms_node)

    def _ubl_add_allowance_charge_nodes(self, vals):
        super()._ubl_add_allowance_charge_nodes(vals)
        self._ubl_add_allowance_charge_nodes_early_payment_discount(vals)

    def _ubl_add_tax_totals_nodes(self, vals):
        super()._ubl_add_tax_totals_nodes(vals)

        # The taxes are only reported in the document currency.
        document_node = vals['document_node']
        document_node['cac:TaxTotal'] = [
            node for node in document_node['cac:TaxTotal'] if node['_currency'] == vals['currency']
        ]

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        currency = vals['currency'] if in_foreign_currency else vals['company_currency']
        node = vals['legal_monetary_total_node']
        node['cbc:PrepaidAmount'] = {
            '_text': FloatFmt(0.0, min_dp=currency.decimal_places),
            'currencyID': currency.name,
        }
        node['cbc:PayableAmount'] = {
            '_text': FloatFmt(node['cbc:TaxInclusiveAmount']['_text'], min_dp=currency.decimal_places),
            'currencyID': currency.name,
        }

    def _get_myinvois_document_paid_amount(self, vals):
        myinvois_document = vals["myinvois_document"]
        # For consolidated invoices, credit, debit, refund notes, and their self-billed variants, the prepaid amount
        # must be set to 0.
        if myinvois_document._is_consolidated_invoice() or vals['document_type_code'] in ('02', '03', '04', '12', '13', '14'):
            return 0.0
        return vals['total_paid_amount_currency']

    def _add_myinvois_document_monetary_total_nodes(self, vals):
        currency = vals['currency']
        document_node = vals['document_node']
        amount_paid = self._get_myinvois_document_paid_amount(vals)

        # Omit the node entirely rather than emitting it with a 0.00 amount when there is no genuine prepayment.
        if amount_paid:
            document_node['cac:PrepaidPayment'] = {
                'cbc:PaidAmount': {
                    '_text': FloatFmt(amount_paid, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                    'currencyID': currency.name,
                },
            }
        # For credit, debit, refund notes, and their self-billed variants, the PayableAmount reflects the full
        # refund/adjustment amount without being reduced by the prepayment, as per MyInvois specifications.
        monetary_total_node = document_node['cac:LegalMonetaryTotal']
        monetary_total_node['cbc:PayableAmount']['_text'] = FloatFmt(
            monetary_total_node['cbc:TaxInclusiveAmount']['_text'] - amount_paid,
            min_dp=currency.decimal_places,
            max_dp=currency.decimal_places,
        )

    # -------------------------------------------------------------------------
    # EXPORT: Party nodes
    # -------------------------------------------------------------------------

    def _get_myinvois_document_address_node(self, vals):
        partner = vals['partner']

        # The API expects the iso3166-2 code for the state, in the same way as it expects the iso3166 code for the countries.
        # In Odoo, we mostly use these (although there is no standard format) so we'll try to use what Odoo gives us.
        # For malaysia, the codes were updated..

        subentity_code = ''
        country = partner.country_id

        if partner.state_id:
            if (
                partner._l10n_my_edi_get_tin_for_myinvois() == 'EI00000000010'
                and partner.l10n_my_identification_number == 'NA'
            ) or country.code != 'MY':
                # Special case for consolidated entities (e.g., general public) and non-Malaysian partners:
                # MyInvois requires the CountrySubentityCode to be fixed as '17' ("not applicable") since
                # Malaysian state codes don't apply to them.
                subentity_code = '17'
            else:
                # Get the subentity code for the partner, based on its state.
                subentity_code = partner.state_id.code

            # Strip 'MY-' prefix if present as we only need number part
            subentity_code = subentity_code.split('-')[1] if 'MY-' in subentity_code else subentity_code

        return {
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': partner.state_id.name},
            'cbc:CountrySubentityCode': {'_text': subentity_code},
            'cac:AddressLine': [
                {'cbc:Line': {'_text': partner.street}},
                {'cbc:Line': {'_text': partner.street2}},
            ],
            'cac:Country': {
                'cbc:IdentificationCode': {
                    '_text': COUNTRY_CODE_MAP.get(country.code),
                    'listAgencyID': '6',
                    'listID': 'ISO3166-1',
                },
                'cbc:Name': {
                    '_text': country.name,
                    'languageID': vals.get('country_vals', {}).get('name_attrs', {}).get('languageID'),
                },
            },
        }

    def _get_myinvois_document_party_identification_node(self, vals):
        """ The id vals list must be filled with two values.
        The TIN, and then one of either:
            - Business registration number (BNR)
            - MyKad/MyTentera identification number (NRIC)
            - Passport number or MyPR/MyKAS identification number (PASSPORT)
            - (ARMY)
        Additionally, companies registered to use SST (sales & services tax) must provide their SST number.
        Finally, if a supplier is using TTX (tourism tax), once again that number must be provided.
        """
        partner = vals['partner']

        tin = partner._l10n_my_edi_get_tin_for_myinvois()

        # If the invoice's commercial partner uses a Generic TIN, set it to the correct generic TIN
        # depending on whether the invoice is self-billed or not.
        if vals['document_type_code'] in ('01', '02', '03', '04') and tin == 'EI00000000030' and vals['role'] == 'customer':
            tin = 'EI00000000020'  # For normal invoices, this partner TIN should be used
        elif vals['document_type_code'] in ('11', '12', '13', '14') and tin == 'EI00000000020' and vals['role'] == 'supplier':
            tin = 'EI00000000030'  # For self-billed invoices, this partner TIN should be used

        party_identification_node = [
            {
                'cbc:ID': {
                    '_text': tin,
                    'schemeID': 'TIN',
                }
            }
        ]

        if partner.l10n_my_identification_type and partner.l10n_my_identification_number:
            party_identification_node.append({
                'cbc:ID': {
                    '_text': partner.l10n_my_identification_number,
                    'schemeID': partner.l10n_my_identification_type,
                }
            })
            if partner.sst_registration_number:
                party_identification_node.append({
                    'cbc:ID': {
                        '_text': partner.sst_registration_number,
                        'schemeID': 'SST',
                    }
                })
            if partner.ttx_registration_number and vals['role'] == 'supplier':
                party_identification_node.append({
                    'cbc:ID': {
                        '_text': partner.ttx_registration_number,
                        'schemeID': 'TTX',
                    }
                })
        return party_identification_node

    def _get_myinvois_document_party_node(self, vals):
        partner = vals['partner']
        role = vals['role']

        return {
            'cbc:IndustryClassificationCode': {
                '_text': partner.commercial_partner_id.l10n_my_edi_industrial_classification.code,
                'name': partner.commercial_partner_id.l10n_my_edi_industrial_classification.name
            } if role == 'supplier' else None,
            'cac:PartyIdentification': self._get_myinvois_document_party_identification_node({**vals, 'partner': partner.commercial_partner_id}),
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            } if role != 'delivery' else None,
            'cac:PostalAddress': self._get_myinvois_document_address_node(vals),
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': partner.commercial_partner_id.name},
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': self._l10n_my_edi_get_formatted_phone_number(partner.phone)},
                'cbc:ElectronicMail': {'_text': partner.email},
            } if role != 'delivery' else None,
        }

    def _ubl_add_accounting_supplier_party_node(self, vals):
        vals['document_node']['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_myinvois_document_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _ubl_add_accounting_customer_party_node(self, vals):
        vals['document_node']['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_myinvois_document_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _ubl_add_delivery_nodes(self, vals):
        nodes = vals['document_node']['cac:Delivery'] = []
        if not vals['myinvois_document']._is_consolidated_invoice():
            nodes.append({
                'cac:DeliveryParty': self._get_myinvois_document_party_node({**vals, 'partner': vals['customer'], 'role': 'delivery'}),
            })

    # -------------------------------------------------------------------------
    # EXPORT: Tax nodes
    # -------------------------------------------------------------------------

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        tax = tax_data and tax_data['tax']
        myinvois_document = vals['myinvois_document']

        if (
            not tax
            and not myinvois_document._is_consolidated_invoice()
            and not myinvois_document._is_consolidated_invoice_refund()
        ):
            return None  # Triggers a validation error for the missing tax on a simple invoice.

        is_exempt_tax = tax and tax.l10n_my_tax_type == 'E'
        tax_exemption_reason = is_exempt_tax and (
            myinvois_document.myinvois_exemption_reason
            or tax.l10n_my_tax_exemption_reason
        )
        amount_type = tax.amount_type if tax else 'percent'
        return {
            'tax_category_code': tax.l10n_my_tax_type if tax else '06',
            'tax_exemption_reason': tax_exemption_reason or None,
            'percent': (tax.amount if tax else 0.0) if amount_type == 'percent' else None,
            'scheme_id': 'OTH',
            'is_withholding': False,
            'currency': currency,
        }

    def _get_myinvois_document_tax_category_node(self, tax_category):
        return {
            '_currency': tax_category['currency'],
            'cbc:ID': {'_text': tax_category['tax_category_code']},
            'cbc:Name': {'_text': tax_category['tax_exemption_reason']},
            'cbc:Percent': {'_text': tax_category['percent']},
            'cbc:TaxExemptionReason': {'_text': tax_category['tax_exemption_reason']},
            'cac:TaxScheme': {
                'cbc:ID': {
                    '_text': tax_category['scheme_id'],
                    'schemeID': 'UN/ECE 5153',
                    'schemeAgencyID': '6',
                }
            }
        }

    def _ubl_get_tax_category_node(self, vals, tax_category):
        return self._get_myinvois_document_tax_category_node(tax_category)

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        return self._get_myinvois_document_tax_category_node(tax_category)

    # -------------------------------------------------------------------------
    # EXPORT: Line nodes
    # -------------------------------------------------------------------------

    def _line_nodes_filter_base_lines(self, vals, filter_function=None):
        # Early payment discount lines are reported as allowances/charges, and cash rounding lines in PayableRoundingAmount.
        def new_filter_function(base_line):
            if self._ubl_is_early_payment_base_line(base_line) or self._ubl_is_cash_rounding_base_line(base_line):
                return False
            return not filter_function or filter_function(base_line)

        return super()._line_nodes_filter_base_lines(vals, filter_function=new_filter_function)

    def _ubl_add_invoice_line_node(self, vals):
        super()._ubl_add_invoice_line_node(vals)
        self._add_myinvois_document_line_item_price_extension_node(vals)

    def _ubl_add_line_allowance_charge_nodes(self, vals):
        super()._ubl_add_line_allowance_charge_nodes(vals)
        self._ubl_add_line_allowance_charge_nodes_for_discount(vals)

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        currency = discount_values['currency']
        return {
            '_currency': currency,
            'cbc:ChargeIndicator': {'_text': 'true' if discount_values['is_charge'] else 'false'},
            'cbc:AllowanceChargeReasonCode': {'_text': '95'},
            'cbc:Amount': {
                '_text': FloatFmt(abs(discount_values['amount']), min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
        }

    def _ubl_add_line_period_nodes(self, vals):
        # MyInvois does not report the deferred dates of the lines.
        vals['line_node']['cac:InvoicePeriod'] = []

    def _ubl_add_line_tax_totals_nodes(self, vals):
        # Same as the document level TaxTotal, but for this line only.
        sub_vals = {
            **vals,
            'base_lines': [vals['line_vals']['base_line']],
            'document_node': {},
        }
        self._ubl_add_tax_totals_nodes(sub_vals)
        vals['line_node']['cac:TaxTotal'] = sub_vals['document_node']['cac:TaxTotal']

    def _ubl_add_line_item_name_description_nodes(self, vals):
        super()._ubl_add_line_item_name_description_nodes(vals)
        item_node = vals['item_node']
        base_line = vals['line_vals']['base_line']

        record = base_line['record']
        if record and record.name:
            line_name = record.name.replace('\n', ' ')
        else:
            line_name = base_line.get('line_name', '')
        if line_name:
            item_node['cbc:Description'] = {'_text': line_name}
            if not item_node['cbc:Name']:
                item_node['cbc:Name'] = {'_text': line_name}

    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        item_node = vals['item_node']
        base_line = vals['line_vals']['base_line']

        # When the invoice is sent for the general public (refunding an order in a consolidated invoice/...) the item code
        # must be fixed to 004 (consolidated invoice) even if the product has something else set.
        myinvois_document = vals['myinvois_document']
        if myinvois_document._is_consolidated_invoice() or myinvois_document._is_consolidated_invoice_refund():
            class_code = '004'
        else:
            class_code = base_line['record'].l10n_my_edi_classification_code or \
                         base_line['record'].product_id.product_tmpl_id.l10n_my_edi_classification_code

        if class_code:
            item_node['cac:CommodityClassification'] = {
                'cbc:ItemClassificationCode': {
                    '_text': class_code,
                    'listID': 'CLASS',
                }
            }

    def _add_myinvois_document_line_item_price_extension_node(self, vals):
        base_line = vals['line_vals']['base_line']
        currency = base_line['currency_id']
        vals['line_node']['cac:ItemPriceExtension'] = {
            'cbc:Amount': {
                '_text': FloatFmt(base_line['tax_details']['total_excluded_currency'], min_dp=currency.decimal_places),
                'currencyID': currency.name,
            }
        }

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_document_node_constraints(self, vals):
        constraints = super()._export_document_node_constraints(vals)
        constraints.update(self._export_myinvois_document_constraints(vals))
        return constraints

    def _export_myinvois_document_constraints(self, vals):
        constraints = {
            'myinvois_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'myinvois_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'myinvois_document_name_required': self._check_required_fields(vals, 'document_name'),
        }

        if not vals['supplier'].commercial_partner_id.l10n_my_edi_industrial_classification:
            self._l10n_my_edi_make_validation_error(constraints, 'industrial_classification_required', 'supplier', vals['supplier'].display_name)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            phone_number = partner.phone
            # 'NA' is a valid value in some cases, e.g. consolidated invoices.
            if phone_number != 'NA':
                phone = self._l10n_my_edi_get_formatted_phone_number(phone_number)
                if E_164_REGEX.match(phone) is None:
                    self._l10n_my_edi_make_validation_error(constraints, 'phone_number_format', partner_type, partner.display_name)
            elif not phone_number:
                self._l10n_my_edi_make_validation_error(constraints, 'phone_number_required', partner_type, partner.display_name)

            # We need to provide both l10n_my_identification_type and l10n_my_identification_number
            if not partner.commercial_partner_id.l10n_my_identification_type or not partner.commercial_partner_id.l10n_my_identification_number:
                self._l10n_my_edi_make_validation_error(constraints, 'required_id', partner_type, partner.commercial_partner_id.display_name)

            if not partner.state_id:
                self._l10n_my_edi_make_validation_error(constraints, 'no_state', partner_type, partner.display_name)
            if not partner.city:
                self._l10n_my_edi_make_validation_error(constraints, 'no_city', partner_type, partner.display_name)
            if not partner.country_id:
                self._l10n_my_edi_make_validation_error(constraints, 'no_country', partner_type, partner.display_name)
            if not partner.street:
                self._l10n_my_edi_make_validation_error(constraints, 'no_street', partner_type, partner.display_name)

            if partner.commercial_partner_id.sst_registration_number and len(partner.commercial_partner_id.sst_registration_number.split(';')) > 2:
                self._l10n_my_edi_make_validation_error(constraints, 'too_many_sst', partner_type, partner.commercial_partner_id.display_name)

        for line_vals in vals['document_node']['cac:InvoiceLine']:
            myinvois_document = vals["myinvois_document"]
            line_item = line_vals['cac:Item']
            if 'cac:CommodityClassification' not in line_item:
                self._l10n_my_edi_make_validation_error(constraints, 'class_code_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])
            if not line_item.get('cac:ClassifiedTaxCategory'):
                self._l10n_my_edi_make_validation_error(constraints, 'tax_ids_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])
            for tax_category in line_item['cac:ClassifiedTaxCategory']:
                if tax_category['cbc:ID']['_text'] == 'E' and not tax_category['cbc:TaxExemptionReason']['_text']:
                    if not myinvois_document._is_consolidated_invoice():
                        self._l10n_my_edi_make_validation_error(constraints, 'tax_exemption_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])
                    else:  # On consolidated invoices, you cannot define the reason on the invoice and so the message should be different for clarity
                        self._l10n_my_edi_make_validation_error(constraints, 'tax_exemption_required_on_tax', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])

        # Code '004' (Consolidated e-Invoice) requires the General Public TIN + identification number, and
        # vice-versa: that TIN + identification number requires every line to use code '004'.
        invoice_type_code = vals['document_node']['cbc:InvoiceTypeCode']['_text']
        if invoice_type_code in ("11", "12", "13", "14"):  # For self billed, we validate the supplier
            party_identification_nodes = vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cac:PartyIdentification']
        else:
            party_identification_nodes = vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cac:PartyIdentification']
        vat = party_identification_nodes[0]['cbc:ID']['_text']
        identification_number = party_identification_nodes[1]['cbc:ID']['_text'] if len(party_identification_nodes) > 1 else None
        is_general_public = vat == 'EI00000000010' and identification_number == 'NA'

        line_classification_codes = [
            line_vals['cac:Item'].get('cac:CommodityClassification', {}).get('cbc:ItemClassificationCode', {}).get('_text')
            for line_vals in vals['document_node']['cac:InvoiceLine']
        ]

        if any(code == '004' for code in line_classification_codes) and not is_general_public:
            self._l10n_my_edi_make_validation_error(constraints, 'missing_general_public', vals['customer'].id, vals['customer'].name)
        if is_general_public and any(code != '004' for code in line_classification_codes):
            self._l10n_my_edi_make_validation_error(constraints, 'general_public_requires_004', vals['customer'].id, vals['customer'].name)

        # MyInvois limits the InternalID to 50 characters.
        document_id = vals['document_node']['cbc:ID']['_text']
        if document_id and len(document_id) > 50:
            self._l10n_my_edi_make_validation_error(constraints, 'document_id_too_long', vals['myinvois_document'].id, vals['myinvois_document'].display_name)

        return constraints

    @api.model
    def _l10n_my_edi_make_validation_error(self, constraints, code, record_identifier, record_name):
        """ Small helper that add new constrains into provided constrains dict.
        This helper is mainly there to keep the check method tidy, and focused on its purpose (validating data)
        """
        message_mapping = {
            'industrial_classification_required': self.env._(
                "The industrial classification must be defined on company: %(company_name)s",
                company_name=record_name
            ),
            'phone_number_format': self.env._(
                "The following partner's phone number should follow the E.164 format: %(partner_name)s",
                partner_name=record_name
            ),
            'phone_number_required': self.env._(
                "The following partner's phone number is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'required_id': self.env._(
                "The following partner's identification type or number is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_state': self.env._(
                "The following partner's state is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_city': self.env._(
                "The following partner's city is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_country': self.env._(
                "The following partner's country is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_street': self.env._(
                "The following partner's street is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'class_code_required': self.env._(
                "You must set a classification code either on the line itself or on the product of line: %(line_name)s",
                line_name=record_name
            ),
            'adjustment_origin': self.env._(
                "You cannot send a debit / credit note for invoice %(invoice_number)s as it has not yet been sent to MyInvois.",
                invoice_number=record_name
            ),
            'too_many_sst': self.env._(
                "The following partner's should have at most two SST numbers, separated by a semicolon : %(partner_name)s",
                partner_name=record_name
            ),
            'tax_ids_required': self.env._(
                "You must set a tax on the line : %(line_name)s.\nIf taxes are not applicable, please set a 0%% tax with a tax type 'Not Applicable'.",
                line_name=record_name
            ),
            'tax_exemption_required': self.env._(
                "You must set a Tax Exemption Reason on the invoice : %(invoice_name)s as some taxes have the type 'Tax exemption' without a reason set.",
                invoice_name=record_name
            ),
            'tax_exemption_required_on_tax': self.env._(
                "You must set a Tax Exemption Reason on each tax exempt taxes in order to use them in a Consolidated Invoice.",
            ),
            'missing_general_public': self.env._(
                "Classification code '004' can only be used for consolidated e-invoice issued to general public "
                "(TIN of 'EI00000000010', BRN/NRIC of 'NA')"
            ),
            'general_public_requires_004': self.env._(
                "TIN 'EI00000000010' (General Public / Consolidated e-Invoice) with BRN/NRIC of 'NA' requires "
                "classification code '004' on every invoice line."
            ),
            'document_id_too_long': self.env._(
                'The "Bill Reference" for %(invoice_name)s exceeds the maximum limit of 50 characters.',
                invoice_name=record_name
            ),
        }

        constraints[f'myinvois_{record_identifier}_{code}'] = message_mapping[code]

    @api.model
    def _l10n_my_edi_decode_myinvois_attachment(self, attachment):
        """ Extract data from MyInvois xml. """
        def get_node(node, xpath):
            nodes = node.xpath(xpath)
            return nodes[0] if nodes else None

        def get_value(node):
            if node is None:
                return None
            return node.text

        vals = {}
        try:
            root = etree.fromstring(attachment.raw.content)
            invoice_id_node = get_node(root, "//*[local-name()='Invoice']/*[local-name()='ID']")
        except etree.XMLSyntaxError:
            # Not an xml
            return {}
        except AttributeError:
            # Not a MyInvois xml
            return {}

        vals['original_document_id'] = get_value(invoice_id_node)
        return vals

    # ----------------
    # EXPORT: Business methods
    # ----------------

    @api.model
    def _l10n_my_edi_get_document_type_code(self, myinvois_document):
        """ Returns the code matching the invoice type, as well as the original document(s) if any. """
        document_type_code = '01'
        original_documents = None

        # For consolidated invoices, we treat PoS documents as invoice (01) but for accounting documents, we need to look into it for the exact type.
        if not myinvois_document._is_consolidated_invoice() or bool(myinvois_document.invoice_ids):
            invoices = myinvois_document.invoice_ids
            ref_invoice = invoices[0]  # There is only ever one move_type in a same document
            if self.env['myinvois.document']._myinvois_is_debit_notes_used() and ref_invoice.debit_origin_id:
                document_type_code = '03' if ref_invoice.move_type == 'out_invoice' else '13'
                original_documents = invoices.debit_origin_id._get_active_myinvois_document()
            elif ref_invoice.is_refund():
                is_refund, refunded_document = self._l10n_my_edi_get_refund_details(invoices)
                if is_refund:
                    document_type_code = '04' if ref_invoice.move_type == 'out_refund' else '14'
                else:
                    document_type_code = '02' if ref_invoice.move_type == 'out_refund' else '12'

                original_documents = refunded_document
            else:
                document_type_code = '01' if ref_invoice.move_type == 'out_invoice' else '11'

        return document_type_code, original_documents

    @api.model
    def _l10n_my_edi_get_refund_details(self, invoices):
        """
        Helper which returns the refunded document in case of out_refund/in_refund.
        In some cases, such as PoS, we could need a different logic than from the regular flow.
        :param invoices: The credit note for which we want to get the refunded document.
        :return: A tuple, where the first parameter indicates if this credit note is a refund and the second the credited/refunded document.
        """
        # We consider a credit note a refund if it is paid and fully reconciled with a payment or bank transaction.
        payment_terms = invoices.line_ids.filtered(lambda aml: aml.display_type == 'payment_term')
        counterpart_amls = payment_terms.reconciled_lines_ids
        counterpart_move_type = 'out_invoice' if invoices[0].move_type == 'out_refund' else 'in_invoice'
        has_payments = bool(counterpart_amls.move_id.filtered(lambda move: move.move_type != counterpart_move_type))
        # In practice, as a check on this is done when separating invoices for consolidation, checking all of them this way would be enough.
        is_paid = all(invoice.payment_state in ('in_payment', 'paid', 'reversed') for invoice in invoices)

        refunded_document = invoices.reversed_entry_id._get_active_myinvois_document()
        is_refund = is_paid and has_payments
        return is_refund, refunded_document

    @api.model
    def _l10n_my_edi_get_prepaid_amount(self, invoice):
        """ Compute the amount of the invoice that was genuinely paid in advance.

        LHDN only recognizes a reconciled payment as a deposit/prepayment if it was made strictly before the
        invoice date; a payment made on or after the invoice date is a regular settlement, not a prepayment.
        Additionally, LHDN never accepts a PayableAmount of 0, so a 100% advance payment must not be reported
        as a prepayment either: in that case, the full invoice amount is reported as payable instead.
        Credit/debit notes reconciled against the invoice are not prepayments.
        """
        if not invoice.invoice_date:
            return 0.0

        invoice_partials, exchange_diff_moves = invoice._get_reconciled_invoices_partials()
        prepaid_amount = sum(
            amount
            for partial, amount, aml in invoice_partials
            if (
                aml.move_id.id not in exchange_diff_moves
                and aml.move_id.move_type not in ('out_refund', 'in_refund')
                and aml.date and aml.date < invoice.invoice_date
            )
        )
        if invoice.currency_id.compare_amounts(prepaid_amount, invoice.amount_total) >= 0:
            return 0.0
        return prepaid_amount

    @api.model
    def _l10n_my_edi_get_formatted_phone_number(self, number):
        # the phone number MUST follow the E.164 format.
        # Don't try to reformat too much, we don't want to risk messing it up
        if not number:
            return ''  # This wouldn't happen in the file as it's caught in the validation errors, but the vals are exported before these checks are done.
        return number.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
