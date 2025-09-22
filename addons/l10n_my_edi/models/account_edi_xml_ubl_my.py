# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from datetime import datetime

from pytz import UTC

from odoo import api, models
from odoo.tools import html2plaintext

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
    _inherit = "account.edi.xml.ubl_21"
    _name = 'account.edi.xml.ubl_myinvois_my'
    _description = "Malaysian implementation of ubl for the MyInvois portal"

    # -----------------------
    # EXPORT
    # -----------------------

    def _get_myinvois_document_node(self, vals):
        """
        Entry point of the export of a MyInvois document.
        The node returned by this function should be passed into dict_to_xml in order to generate the XML file to send to
        MyInvois.
        """
        self._add_myinvois_document_config_vals(vals)
        self._add_myinvois_document_base_lines_vals(vals)
        self._add_document_currency_vals(vals)
        self._add_myinvois_document_tax_grouping_function_vals(vals)
        self._add_myinvois_document_monetary_total_vals(vals)

        document_node = {}
        self._add_myinvois_document_header_nodes(document_node, vals)
        self._add_myinvois_document_accounting_supplier_party_nodes(document_node, vals)
        self._add_myinvois_document_accounting_customer_party_nodes(document_node, vals)

        myinvois_document = vals["myinvois_document"]
        if vals['document_type'] == 'invoice' and not myinvois_document._is_consolidated_invoice():
            self._add_myinvois_document_delivery_nodes(document_node, vals)
            self._add_myinvois_document_payment_terms_nodes(document_node, vals)

        self._add_document_allowance_charge_nodes(document_node, vals)
        self._add_myinvois_document_exchange_rate_nodes(document_node, vals)
        self._add_document_tax_total_nodes(document_node, vals)
        self._add_myinvois_document_monetary_total_nodes(document_node, vals)
        self._add_myinvois_document_line_nodes(document_node, vals)
        return document_node

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
            partner_shipping = None
            payment_term_id = None  # wouldn't make sense in a consolidated invoice.
        else:
            invoice = myinvois_document.invoice_ids[0]  # Otherwise it would be a consolidated invoice.
            customer = invoice.partner_id
            partner_shipping = invoice.partner_shipping_id or customer
            payment_term_id = invoice.invoice_payment_term_id

        document_type_code, original_document = self._l10n_my_edi_get_document_type_code(myinvois_document)
        # In case of self billing, we want to invert the supplier and customer.
        if document_type_code in ("11", "12", "13", "14"):
            supplier, customer = customer, supplier
            partner_shipping = customer
            # In practice, we should never have multiple self billed invoices being part of a consolidated invoices,
            # but it doesn't hurt to support it.
            document_ref = ','.join([invoice.ref for invoice in myinvois_document.invoice_ids if invoice.ref]) or None
        else:
            document_ref = None

        vals.update({
            'document_type': 'invoice',
            'document_type_code': document_type_code,
            'original_document': original_document,

            'document_name': myinvois_document.name,

            'supplier': supplier,
            'customer': customer,
            'partner_shipping': partner_shipping,

            'currency_id': myinvois_document.currency_id,
            'company_currency_id': myinvois_document.company_id.currency_id,

            'use_company_currency': False,
            'fixed_taxes_as_allowance_charges': True,
            'custom_form_reference': myinvois_document.myinvois_custom_form_reference,
            'document_ref': document_ref,
            'incoterm_id': myinvois_document.invoice_ids.invoice_incoterm_id,
            'invoice_payment_term_id': payment_term_id,
        })

    def _add_myinvois_document_base_lines_vals(self, vals):
        myinvois_document = vals['myinvois_document']
        vals['base_lines'] = myinvois_document._get_rounded_base_lines()

    def _add_myinvois_document_tax_grouping_function_vals(self, vals):
        def total_grouping_function(base_line, tax_data):
            return True

        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            myinvois_document = base_line['myinvois_document']

            if (
                not tax
                and not myinvois_document._is_consolidated_invoice()
                and not myinvois_document._is_consolidated_invoice_refund()
            ):
                return None  # Triggers UserError for missing tax on simple invoice.

            is_exempt_tax = tax and tax.l10n_my_tax_type == 'E'
            tax_exemption_reason = is_exempt_tax and (
                myinvois_document.myinvois_exemption_reason
                or tax.l10n_my_tax_exemption_reason
            )

            return {
                'tax_category_code': tax.l10n_my_tax_type if tax else '06',
                'tax_exemption_reason': tax_exemption_reason,
                'amount': tax.amount if tax else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    def _add_myinvois_document_monetary_total_vals(self, vals):
        self._add_document_monetary_total_vals(vals)
        myinvois_document = vals["myinvois_document"]
        if myinvois_document.invoice_ids:
            # Add the total amount paid.
            vals.update({
                'total_paid_amount': sum((invoice.amount_total - invoice.amount_residual) * invoice.invoice_currency_rate for invoice in myinvois_document.invoice_ids),
                'total_paid_amount_currency': sum(invoice.amount_total - invoice.amount_residual for invoice in myinvois_document.invoice_ids),
            })

    # -------------------------------------------------------------------------
    # EXPORT: Templates
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
            ):
                # Special case for consolidated entities (e.g., general public).
                # When TIN is 'EI00000000010' and Identification Number is 'NA', MyInvois requires
                # the CountrySubentityCode to be fixed as '17' regardless of the actual state.
                subentity_code = '17'
            elif country.code != 'MY':
                # For non-Malaysian partners return the state name instead of state code
                subentity_code = partner.state_id.name
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

    def _get_tax_category_node(self, vals):
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {'_text': grouping_key['tax_category_code']},
            'cbc:Name': {'_text': grouping_key['tax_exemption_reason']},
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cbc:TaxExemptionReason': {'_text': grouping_key['tax_exemption_reason']},
            'cac:TaxScheme': {
                'cbc:ID': {
                    '_text': 'OTH',
                    'schemeID': 'UN/ECE 5153',
                    'schemeAgencyID': '6',
                }
            }
        }

    def _add_myinvois_document_header_nodes(self, document_node, vals):
        document_node.update({
            'cbc:UBLVersionID': None,
            'cbc:ID': {'_text': vals['document_name']},
            # The issue date and time must be the current time set in the UTC time zone
            'cbc:IssueDate': {'_text': datetime.now(tz=UTC).strftime("%Y-%m-%d")},
            'cbc:IssueTime': {'_text': datetime.now(tz=UTC).strftime("%H:%M:%SZ")},
            'cbc:DueDate': None,

            # The current version is 1.1 (document with signature), the type code depends on the move type.
            'cbc:InvoiceTypeCode': {
                '_text': vals['document_type_code'],
                'listVersionID': '1.1',
            },
            'cbc:DocumentCurrencyCode': {'_text': vals['currency_id'].name},
            'cac:OrderReference': None,
            'cbc:BuyerReference': {'_text': vals['customer'].commercial_partner_id.ref},

            # Debit/Credit note original invoice ref.
            # Applies to credit notes, debit notes, refunds for both invoices and self-billed invoices.
            # The original document is mandatory; but in some specific cases it will be empty (sending a credit note for an invoice
            # managed outside Odoo/...)
            'cac:BillingReference': {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': (vals['original_document'] and vals['original_document'].name) or 'NA'},
                    'cbc:UUID': {'_text': (vals['original_document'] and vals['original_document'].myinvois_external_uuid) or 'NA'},
                }
            } if vals['document_type_code'] in {'02', '03', '04', '12', '13', '14'} else None,
            'cac:AdditionalDocumentReference': [
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
            ],
        })

        # Self-billed invoices must use the number given by the supplier.
        if vals['document_type_code'] in ('11', '12', '13', '14') and vals['document_ref']:
            document_node['cbc:ID']['_text'] = vals['document_ref']

    def _add_myinvois_document_accounting_supplier_party_nodes(self, document_node, vals):
        document_node['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_myinvois_document_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _add_myinvois_document_accounting_customer_party_nodes(self, document_node, vals):
        document_node['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_myinvois_document_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _add_myinvois_document_delivery_nodes(self, document_node, vals):
        document_node['cac:Delivery'] = {
            'cac:DeliveryParty': self._get_myinvois_document_party_node({**vals, 'partner': vals['customer'], 'role': 'delivery'}),
        }

    def _add_myinvois_document_payment_terms_nodes(self, document_node, vals):
        if vals['invoice_payment_term_id']:
            document_node['cac:PaymentTerms'] = {
                # The payment term's note is automatically embedded in a <p> tag in Odoo
                'cbc:Note': {'_text': html2plaintext(vals['invoice_payment_term_id'].note)}
            }

    def _add_myinvois_document_exchange_rate_nodes(self, document_node, vals):
        if vals['currency_id'].name != 'MYR':
            # I couldn't find any information on maximum precision, so we will use the currency format.
            total_amount_in_company_currency = total_amount_in_currency = 0.0
            for base_line in vals['base_lines']:
                total_amount_in_company_currency += base_line['tax_details']['raw_total_included']
                total_amount_in_currency += base_line['tax_details']['raw_total_included_currency']
            # We recalculate the rate so that it works in any cases, even when using consolidated invoices.
            rate = self.env.ref('base.MYR').round(abs(total_amount_in_company_currency) / (total_amount_in_currency or 1))
            # Exchange rate information must be provided if applicable
            document_node['cac:TaxExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': vals['currency_id'].name},
                'cbc:TargetCurrencyCode': {'_text': 'MYR'},
                'cbc:CalculationRate': {'_text': rate},
            }

    def _add_myinvois_document_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)
        currency_suffix = vals['currency_suffix']

        amount_paid = vals[f'total_paid_amount{currency_suffix}']
        if amount_paid:
            document_node['cac:PrepaidPayment'] = {
                'cbc:PaidAmount': {
                    '_text': self.format_float(amount_paid, vals['currency_dp']),
                    'currencyID': vals['currency_name'],
                },
            }
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        payable_amount = self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'] - amount_paid, vals['currency_dp'])
        document_node[monetary_total_tag]['cbc:PayableAmount']['_text'] = payable_amount

    def _add_myinvois_document_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_myinvois_document_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    def _get_myinvois_document_line_node(self, vals):
        self._add_myinvois_document_line_vals(vals)

        line_node = {}
        self._add_document_line_id_nodes(line_node, vals)
        self._add_document_line_id_nodes(line_node, vals)
        self._add_myinvois_document_line_amount_nodes(line_node, vals)
        self._add_document_line_allowance_charge_nodes(line_node, vals)
        self._add_document_line_tax_total_nodes(line_node, vals)
        self._add_myinvois_document_line_item_nodes(line_node, vals)
        self._add_document_line_tax_category_nodes(line_node, vals)
        self._add_document_line_price_nodes(line_node, vals)
        return line_node

    def _add_myinvois_document_line_vals(self, vals):
        """ Generic helper to calculate the amounts for a document line. """
        self._add_document_line_total_vals(vals)
        self._add_myinvois_document_line_gross_subtotal_and_discount_vals(vals)

    def _add_myinvois_document_line_gross_subtotal_and_discount_vals(self, vals):
        """
        As we group lines together when consolidating, we lose the discount percentage in the process.
        During the grouping, we stored the actual amount in the base line, se we will override here in order to use that
        pre-computed amount.
        """
        self._add_document_line_gross_subtotal_and_discount_vals(vals)
        myinvois_document = vals["myinvois_document"]
        if myinvois_document._is_consolidated_invoice():
            base_line = vals['base_line']

            for currency_suffix in ['', '_currency']:
                discount_amount = base_line[f'discount_amount{currency_suffix}']

                vals[f'discount_amount{currency_suffix}'] = discount_amount
                vals[f'gross_price_unit{currency_suffix}'] += discount_amount  # Price unit should be excluding discounts.

    def _add_myinvois_document_line_amount_nodes(self, line_node, vals):
        super()._add_document_line_amount_nodes(line_node, vals)

        base_line = vals['base_line']
        line_node['cac:ItemPriceExtension'] = {
            'cbc:Amount': {
                '_text': self.format_float(base_line['tax_details']['total_excluded_currency'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            }
        }

    def _add_myinvois_document_line_item_nodes(self, line_node, vals):
        self._add_document_line_item_nodes(line_node, vals)

        record = vals['base_line']['record']
        if record and record.name:
            line_name = record.name and record.name.replace('\n', ' ')
        else:
            line_name = vals['base_line']['line_name']
        if line_name:
            line_node['cac:Item']['cbc:Description']['_text'] = line_name
            if not line_node['cac:Item']['cbc:Name']['_text']:
                line_node['cac:Item']['cbc:Name']['_text'] = line_name

        # When the invoice is sent for the general public (refunding an order in a consolidated invoice/...) the item code
        # must be fixed to 004 (consolidated invoice) even if the product has something else set.
        myinvois_document = vals['myinvois_document']
        if myinvois_document._is_consolidated_invoice() or myinvois_document._is_consolidated_invoice_refund():
            class_code = '004'
        else:
            base_line = vals['base_line']
            class_code = base_line['record'].l10n_my_edi_classification_code or \
                         base_line['record'].product_id.product_tmpl_id.l10n_my_edi_classification_code

        if class_code:
            line_node['cac:Item']['cac:CommodityClassification'] = {
                'cbc:ItemClassificationCode': {
                    '_text': class_code,
                    'listID': 'CLASS',
                }
            }

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

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
            line_item = line_vals['cac:Item']
            if 'cac:CommodityClassification' not in line_item:
                self._l10n_my_edi_make_validation_error(constraints, 'class_code_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])
            if not line_item.get('cac:ClassifiedTaxCategory'):
                self._l10n_my_edi_make_validation_error(constraints, 'tax_ids_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])
            for tax_category in line_item['cac:ClassifiedTaxCategory']:
                if tax_category['cbc:ID']['_text'] == 'E' and not tax_category['cbc:TaxExemptionReason']['_text']:
                    self._l10n_my_edi_make_validation_error(constraints, 'tax_exemption_required', line_vals['cbc:ID']['_text'], line_item['cbc:Name']['_text'])

            myinvois_document = vals["myinvois_document"]
            if myinvois_document._is_consolidated_invoice() or myinvois_document._is_consolidated_invoice_refund():
                customer_vat = vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cac:PartyIdentification'][0]['cbc:ID']['_text']
                if customer_vat != 'EI00000000010':
                    self._l10n_my_edi_make_validation_error(constraints, 'missing_general_public', vals['customer'].id, vals['customer'].name)

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
                "You must set a Tax Exemption Reason on each tax exempt taxes in order to use them in a Myinvois Document.",
            ),
            'missing_general_public': self.env._(
                "You must have a commercial partner named 'General Public' with a VAT number set to 'EI00000000010' in order to proceed.",
            ),
        }

        constraints[f'myinvois_{record_identifier}_{code}'] = message_mapping[code]

    # ----------------
    # EXPORT: Business methods
    # ----------------

    @api.model
    def _l10n_my_edi_get_document_type_code(self, myinvois_document):
        """ Returns the code matching the invoice type, as well as the original document if any. """
        document_type_code = '01'
        original_document = None

        if not myinvois_document._is_consolidated_invoice():
            invoice = myinvois_document.invoice_ids[0]  # Otherwise it would be a consolidated invoice.
            if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id:
                document_type_code = '03' if invoice.move_type == 'out_invoice' else '13'
                original_document = invoice.debit_origin_id._get_active_myinvois_document()
            elif invoice.move_type in ('out_refund', 'in_refund'):
                is_refund, refunded_document = self._l10n_my_edi_get_refund_details(invoice)
                if is_refund:
                    document_type_code = '04' if invoice.move_type == 'out_refund' else '14'
                else:
                    document_type_code = '02' if invoice.move_type == 'out_refund' else '12'

                original_document = refunded_document
            else:
                document_type_code = '01' if invoice.move_type == 'out_invoice' else '11'

        return document_type_code, original_document  # Consolidated invoices are fixed to '01'

    @api.model
    def _l10n_my_edi_get_refund_details(self, invoice):
        """
        Helper which returns the refunded document in case of out_refund/in_refund.
        In some cases, such as PoS, we could need a different logic than from the regular flow.
        :param invoice: The credit note for which we want to get the refunded document.
        :return: A tuple, where the first parameter indicates if this credit note is a refund and the second the credited/refunded document.
        """
        # We consider a credit note a refund if it is paid and fully reconciled with a payment or bank transaction.
        payment_terms = invoice.line_ids.filtered(lambda aml: aml.display_type == 'payment_term')
        counterpart_amls = payment_terms.reconciled_lines_ids
        counterpart_move_type = 'out_invoice' if invoice.move_type == 'out_refund' else 'in_invoice'
        has_payments = bool(counterpart_amls.move_id.filtered(lambda move: move.move_type != counterpart_move_type))
        is_paid = invoice.payment_state in ('in_payment', 'paid', 'reversed')

        refunded_document = invoice.reversed_entry_id._get_active_myinvois_document()
        is_refund = is_paid and has_payments
        return is_refund, refunded_document

    @api.model
    def _l10n_my_edi_get_formatted_phone_number(self, number):
        # the phone number MUST follow the E.164 format.
        # Don't try to reformat too much, we don't want to risk messing it up
        if not number:
            return ''  # This wouldn't happen in the file as it's caught in the validation errors, but the vals are exported before these checks are done.
        return number.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
