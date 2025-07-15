# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime

from pytz import UTC

from odoo import _, api, models
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

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
    # CRUD, inherited methods
    # -----------------------

    def _export_invoice_filename(self, invoice):
        # OVERRIDE 'account_edi_ubl_cii'
        return f"{invoice.name.replace('/', '_')}_myinvois.xml"

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            # MyInvois integration requires some template changes. All documents use the same template (Invoice)
            'InvoiceType_template': 'l10n_my_edi.ubl_21_InvoiceType_my',
            'CreditNoteType_template': 'l10n_my_edi.ubl_21_InvoiceType_my',
            'DebitNoteType_template': 'l10n_my_edi.ubl_21_InvoiceType_my',
            'main_template': 'account_edi_ubl_cii.ubl_20_Invoice',

            'InvoiceLineType_template': 'l10n_my_edi.ubl_20_InvoiceLineType_my',
            'CreditNoteLineType_template': 'l10n_my_edi.ubl_20_InvoiceLineType_my',
            'DebitNoteLineType_template': 'l10n_my_edi.ubl_20_InvoiceLineType_my',

            'DeliveryType_template': 'l10n_my_edi.ubl_20_DeliveryType_my',
        })

        document_type_code, original_document = self._l10n_my_edi_get_document_type_code(invoice)
        vals['vals'].update({
            # These data are not in the API description and thus removed to avoid issues.
            'customization_id': None,
            'profile_id': None,
            'ubl_version_id': None,
            'due_date': None,
            'order_reference': None,
            # The current version is 1.1 (document with signature), the type code depends on the move type.
            'document_type_code_attrs': {'listVersionID': 1.1},
            'document_type_code': document_type_code,
            # The issue date and time must be the current time set in the UTC time zone
            'issue_date': datetime.now(tz=UTC).strftime("%Y-%m-%d"),
            'issue_time': datetime.now(tz=UTC).strftime("%H:%M:%SZ"),
            # Exchange rate information must be provided if applicable
            'tax_exchange_rate': self._l10n_my_edi_get_tax_exchange_rate(invoice),
            'invoice_incoterm_code': invoice.invoice_incoterm_id.code,
            # Depending on the move type, it will either be about exports (invoices) or imports (bills)
            'custom_form_reference': invoice.l10n_my_edi_custom_form_reference if document_type_code in {"11", "12", "13", "14"} else None,
            'export_custom_form_reference': invoice.l10n_my_edi_custom_form_reference if document_type_code in {"01", "02", "03", "04"} else None,
        })

        # these are optional, and since we can't have the correct one at the time of generating, we avoid adding them.
        vals['vals'].pop('payment_means_vals_list', None)

        other_party = opposite_generic_tin = expected_generic_tin = None
        # For Myinvois, prepaid amount is defined as a separate node.
        vals['vals'].get('monetary_total_vals', {}).pop('prepaid_amount', None)

        # We add the company industrial classification to the supplier vals.
        if vals['vals']['document_type_code'] in ('01', '02', '03', '04'):  # Regular invoices
            vals['vals']['accounting_supplier_party_vals']['party_vals'].update({
                'industry_classification_code_attrs': {'name': invoice.company_id.l10n_my_edi_industrial_classification.name},
                'industry_classification_code': invoice.company_id.l10n_my_edi_industrial_classification.code,
            })

            other_party = vals["vals"]["accounting_customer_party_vals"]["party_vals"]
            opposite_generic_tin = 'EI00000000030'
            expected_generic_tin = 'EI00000000020'
        elif vals['vals']['document_type_code'] in ('11', '12', '13', '14'):  # Self billed.
            vals['vals']['accounting_supplier_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.partner_id, role='supplier')
            vals['vals']['accounting_customer_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.company_id.partner_id, role='customer')
            vals['vals']['accounting_supplier_party_vals']['party_vals'].update({
                'industry_classification_code_attrs': {'name': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.name},
                'industry_classification_code': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.code,
            })

            other_party = vals["vals"]["accounting_supplier_party_vals"]["party_vals"]
            opposite_generic_tin = 'EI00000000020'
            expected_generic_tin = 'EI00000000030'
            # Self-billed invoices must use the number given by the supplier.
            if invoice.ref:
                vals['vals']['id'] = invoice.ref

        # Switch the generic tin to the correct one when it makes sense (For example when a supplier has the buyer generic tin set)
        if other_party:
            for identification_val in other_party['party_identification_vals']:
                if identification_val.get('id_attrs', {}).get('schemeID') == 'TIN' and identification_val.get('id') == opposite_generic_tin:
                    identification_val['id'] = expected_generic_tin

        # We ensure that the customer does not have their ttx set (it could be on the record if they're also supplier)
        customer_identification_vals = [
            vals for vals in vals['vals']['accounting_customer_party_vals']['party_vals']['party_identification_vals'] if vals.get('id_attrs', {}) != {'schemeID': 'TTX'}
        ]
        vals['vals']['accounting_customer_party_vals']['party_vals']['party_identification_vals'] = customer_identification_vals

        # Debit/Credit note original invoice ref.
        # Applies to credit notes, debit notes, refunds for both invoices and self-billed invoices.
        # The original document is mandatory; but in some specific cases it will be empty (sending a credit note for an invoice
        # managed outside Odoo/...)
        if document_type_code in ('02', '03', '04', '12', '13', '14'):
            vals['vals'].update({
                'billing_reference_vals': {
                    'id': (original_document and original_document.name) or 'NA',
                    'uuid': (original_document and original_document.l10n_my_edi_external_uuid) or 'NA',
                },
            })

        vals['vals'].update({
            'prepaid_payment_vals': {
                'currency': invoice.currency_id,
                'currency_dp': self._get_currency_decimal_places(invoice.currency_id),
                'amount': invoice.amount_total - invoice.amount_residual,
            },
        })

        return vals

    def _get_delivery_vals_list(self, invoice):
        # OVERRIDE 'account_edi_ubl_cii'
        customer = invoice.company_id.partner_id if invoice.is_purchase_document() else invoice.partner_id
        return [{
            'accounting_delivery_party_vals': self._l10n_my_edi_get_delivery_party_vals(customer),
        }]

    def _get_partner_contact_vals(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        res = super()._get_partner_contact_vals(partner)
        res['telephone'] = self._l10n_my_edi_get_formatted_phone_number(res['telephone'])
        return res

    def _get_country_vals(self, country):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._get_country_vals(country)
        vals.update({
            'identification_code_attrs': {
                'listID': 'ISO3166-1',
                'listAgencyID': '6',
            },
            'identification_code': COUNTRY_CODE_MAP.get(country.code),
        })
        return vals

    def _get_partner_address_vals(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._get_partner_address_vals(partner)
        # We do not want to display the streets, but instead use the AddressLine element.
        vals.pop('street_name', None)
        vals.pop('additional_street_name', None)

        # The API expects the iso3166-2 code for the state, in the same way as it expects the iso3166 code for the countries.
        # In Odoo, we mostly use these (although there is no standard format) so we'll try to use what Odoo gives us.
        # For malaysia, the codes where updated, but we use a mapping to ensure that outdated data will still end up correct.

        subentity_code = ''

        if partner.state_id:
            if (
                partner._l10n_my_edi_get_tin_for_myinvois() == 'EI00000000010'
                and partner.l10n_my_identification_number == 'NA'
            ):
                # Special case for consolidated entities (e.g., general public).
                # When TIN is 'EI00000000010' and Identification Number is 'NA', MyInvois requires
                # the CountrySubentityCode to be fixed as '17' regardless of the actual state.
                subentity_code = '17'
            elif partner.country_id.code != 'MY':
                # For non-Malaysian partners return the state name instead of state code
                subentity_code = partner.state_id.name
            else:
                # Get the subentity code for the partner, based on its state.
                subentity_code = partner.state_id.code

            # Strip 'MY-' prefix if present as we only need number part
            subentity_code = subentity_code.split('-')[1] if 'MY-' in subentity_code else subentity_code

        vals.update({
            'address_lines': [partner.street or '', partner.street2 or ''],
            'country_subentity_code': subentity_code,
        })
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # OVERRIDE 'account_edi_ubl_cii'
        # We only want to display the registration name here.
        return [{
            'registration_name': partner.name,
        }]

    def _get_partner_party_identification_vals_list(self, partner):
        """ The id vals list must be filled with two values.
        The TIN, and then one of either:
            - Business registration number (BNR)
            - MyKad/MyTentera identification number (NRIC)
            - Passport number or MyPR/MyKAS identification number (PASSPORT)
            - (ARMY)
        Additionally, companies registered to use SST (sales & services tax) must provide their SST number.
        Finally, if a supplier is using TTX (tourism tax), once again that number must be provided.
        """
        # OVERRIDE 'account_edi_ubl_cii'
        vals = [{
            'id_attrs': {'schemeID': 'TIN'},
            'id': partner._l10n_my_edi_get_tin_for_myinvois(),
        }]

        if partner.l10n_my_identification_type and partner.l10n_my_identification_number:
            vals.append({
                'id_attrs': {'schemeID': partner.l10n_my_identification_type},
                'id': partner.l10n_my_identification_number,
            })
            if partner.sst_registration_number:
                # The supplier can input up to 2 SST numbers, in which case they need to separate both by a ;
                # They can do so in the existing field if they want.
                vals.append({
                    'id_attrs': {'schemeID': 'SST'},
                    'id': partner.sst_registration_number,
                })
            if partner.ttx_registration_number:
                vals.append({
                    'id_attrs': {'schemeID': 'TTX'},
                    'id': partner.ttx_registration_number,
                })
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        """ This information is not needed. Instead, the party identification vals must be filled. """
        # OVERRIDE 'account_edi_ubl_cii'
        return []

    def _get_tax_unece_codes(self, customer, supplier, tax):
        # OVERRIDE 'account_edi_ubl_cii'
        return {
            'tax_category_code': tax.l10n_my_tax_type,
            'tax_exemption_reason_code': None,  # Unused in this file.
            'tax_exemption_reason': None,  # Should be set here but we no longer have access to the invoice info...
        }

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)

        for vals in vals_list:
            vals['tax_scheme_vals']['id'] = 'OTH'
            vals['tax_scheme_vals']['id_attrs'] = {'schemeID': 'UN/ECE 5153', 'schemeAgencyID': '6'}

        return vals_list

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii'
        constraints = super()._export_invoice_constraints(invoice, vals)

        # In malaysia, tax on good is paid at the manufacturer level. It is thus common to invoice without taxes,
        # unless invoicing for a service.
        constraints.pop('tax_on_line', '')
        constraints.pop('cen_en16931_tax_line', '')

        if not invoice.company_id.l10n_my_edi_industrial_classification:
            self._l10n_my_edi_make_validation_error(constraints, 'industrial_classification_required', 'company', invoice.company_id.display_name)

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

        for line in invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section')):
            if (not line.product_id or not line.product_id.product_tmpl_id.l10n_my_edi_classification_code) and not line.l10n_my_edi_classification_code:
                self._l10n_my_edi_make_validation_error(constraints, 'class_code_required', line.id, line.display_name)
            if not line.tax_ids:
                self._l10n_my_edi_make_validation_error(constraints, 'tax_ids_required', line.id, line.display_name)
            elif any(tax.l10n_my_tax_type == 'E' for tax in line.tax_ids) and not invoice.l10n_my_edi_exemption_reason:
                self._l10n_my_edi_make_validation_error(constraints, 'tax_exemption_required', invoice.id, invoice.display_name)

        return constraints

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals['commodity_classification_vals'] = [{
            'item_classification_code': line.l10n_my_edi_classification_code,
            'item_classification_attrs': {'listID': 'CLASS'},
        }]
        # User the tax_details in order to fill the classified_tax_category_vals as would be expected.
        for tax_detail in taxes_vals['tax_details']:
            tax_category_vals = tax_detail['_tax_category_vals_']
            for classified_tax_category_vals in vals['classified_tax_category_vals']:
                if tax_category_vals['id'] == classified_tax_category_vals['id']:
                    classified_tax_category_vals['name'] = tax_category_vals['name']
                    classified_tax_category_vals['tax_exemption_reason'] = tax_category_vals['tax_exemption_reason']

        return vals

    def _get_tax_grouping_key(self, base_line, tax_data):
        # EXTENDS 'account_edi_ubl_cii'
        grouping_key = super()._get_tax_grouping_key(base_line, tax_data)
        # Add the tax exemption here as well to ensure consistency.
        tax = tax_data['tax']
        invoice = base_line['record'].move_id
        grouping_key['_tax_category_vals_']['name'] = invoice.l10n_my_edi_exemption_reason if tax.l10n_my_tax_type == 'E' else None
        grouping_key['_tax_category_vals_']['tax_exemption_reason'] = invoice.l10n_my_edi_exemption_reason if tax.l10n_my_tax_type == 'E' else None
        return grouping_key

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        vals['item_price_extension_amount'] = line.price_subtotal
        return vals

    def _import_retrieve_partner_vals(self, tree, role):
        """ Returns a dict of values that will be used to retrieve the partner """
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._import_retrieve_partner_vals(tree, role)
        # We invert the country map to get the country code.
        country_map = {v: k for k, v in COUNTRY_CODE_MAP.items()}
        # We can't use _find_value for the identifier since we need to get the attribute.
        vals.update({
            # Update some values to be correct.
            'vat': self._find_value(f'.//cac:Accounting{role}Party/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', tree),
            'country_code': country_map.get(self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cac:Country//cbc:IdentificationCode', tree)),
            'name': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:RegistrationName', tree),
            # And add new ones that are expected.
            'sst': self._find_value(f'.//cac:Accounting{role}Party/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="SST"]', tree),
            'ttx': self._find_value(f'.//cac:Accounting{role}Party/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="TTX"]', tree),
        })

        identifier = tree.xpath(f'.//cac:Accounting{role}Party/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="NRIC" or @schemeID="PASSPORT" or @schemeID="BRN" or @schemeID="ARMY"]', namespaces=UBL_NAMESPACES)
        if identifier:  # Technically it's required, but to be safe...
            vals.update({
                'id_type': identifier[0].attrib['schemeID'],
                'id_val': identifier[0].text,
            })

        return vals

    def _import_retrieve_and_fill_partner(self, invoice, name, phone, mail, vat, country_code, id_type, id_val, sst=False, ttx=False):
        """ In addition to the basic values, we need to fill the identifiers of the partner and eventual tax codes. """
        # OVERRIDE 'account_edi_ubl_cii'

        # I consider that the standard _retrieve_partner should be enough to match.
        invoice.partner_id = self.env['res.partner'].with_company(invoice.company_id)._retrieve_partner(name=name, phone=phone, mail=mail, vat=vat)

        if not invoice.partner_id and name and vat:
            partner_vals = {
                'name': name,
                'email': mail,
                'phone': phone,
                'sst_registration_number': sst,
                'ttx_registration_number': ttx,
                'l10n_my_identification_type': id_type,
                'l10n_my_identification_number': id_val,
            }
            country = self.env.ref(f'base.{country_code.lower()}', raise_if_not_found=False)
            if country:
                partner_vals['country_id'] = country.id
            invoice.partner_id = self.env['res.partner'].create(partner_vals)
            invoice.partner_id.vat, _country_code = self.env['res.partner']._run_vat_checks(country, vat, validation='setnull')

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        # EXTENDS 'account_edi_ubl_cii'
        logs = super()._import_fill_invoice_form(invoice, tree, qty_factor)
        # We get the incoterm
        incoterm_code = self._find_value('./cac:AdditionalDocumentReference[not(descendant::cbc:DocumentType)]/cbc:ID', tree)
        if incoterm_code is not None:
            invoice.invoice_incoterm_id = self.env['account.incoterms'].search([('code', '=', incoterm_code)], limit=1)
        custom_form_ref = self._find_value('./cac:AdditionalDocumentReference[descendant::cbc:DocumentType[text()="CustomsImportForm"]]/cbc:ID', tree)
        invoice.l10n_my_edi_custom_form_reference = custom_form_ref

        # So that we can find the original invoice in case of debit/credit note.
        invoice_type = self._find_value('./cbc:InvoiceTypeCode', tree)
        origin_uuid = self._find_value('.//cac:InvoiceDocumentReference[descendant::cbc:ID[text()="Document Internal ID"]]/cbc:UUID', tree)
        if invoice_type == '02':
            invoice.reversed_entry_id = self.env['account.move'].search([('l10n_my_edi_external_uuid', '=', origin_uuid)], limit=1)
        elif invoice_type == '03' and 'debit_origin_id' in self.env['account.move']._fields:
            invoice.debit_origin_id = self.env['account.move'].search([('l10n_my_edi_external_uuid', '=', origin_uuid)], limit=1)
        return logs

    # ----------------
    # Business methods
    # ----------------

    def _l10n_my_edi_get_delivery_party_vals(self, partner):
        """ Returns the vals required to display the delivery information in the invoice. """
        return {
            'partner': partner,
            'party_identification_vals': self._get_partner_party_identification_vals_list(partner.commercial_partner_id),
            'postal_address_vals': self._get_partner_address_vals(partner),
            'party_legal_entity_vals': self._get_partner_party_legal_entity_vals_list(partner.commercial_partner_id),
        }

    @api.model
    def _l10n_my_edi_get_document_type_code(self, invoice):
        """ Returns the code matching the invoice type, as well as the original document if any. """
        if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id:
            code = '03' if invoice.move_type == 'out_invoice' else '13'
            return code, invoice.debit_origin_id
        elif invoice.move_type in ('out_refund', 'in_refund'):
            # We consider a credit note a refund if it is paid and fully reconciled with a payment or bank transaction.
            payment_terms = invoice.line_ids.filtered(lambda aml: aml.display_type == 'payment_term')
            counterpart_amls = payment_terms.matched_debit_ids.debit_move_id + payment_terms.matched_credit_ids.credit_move_id
            counterpart_move_type = 'out_invoice' if invoice.move_type == 'out_refund' else 'out_refund'
            has_payments = bool(counterpart_amls.move_id.filtered(lambda move: move.move_type != counterpart_move_type))
            is_paid = invoice.payment_state in ('in_payment', 'paid', 'reversed')
            if is_paid and has_payments:
                code = '04' if invoice.move_type == 'out_refund' else '14'
            else:
                code = '02' if invoice.move_type == 'out_refund' else '12'

            return code, invoice.reversed_entry_id
        else:
            code = '01' if invoice.move_type == 'out_invoice' else '11'
            return code, None

    @api.model
    def _l10n_my_edi_get_tax_exchange_rate(self, invoice):
        """ Returns the tax exchange rate if applicable. We will compute it based on the invoice totals.
        This should be the rate to convert a foreign currency into MYR.
        """
        if invoice.currency_id.name != "MYR":
            # I couldn't find any information on maximum precision, so we will use the currency format.
            return self.env.ref('base.MYR').round(abs(invoice.amount_total_signed) / (invoice.amount_total or 1))
        return ''

    @api.model
    def _l10n_my_edi_get_formatted_phone_number(self, number):
        # the phone number MUST follow the E.164 format.
        # Don't try to reformat too much, we don't want to risk messing it up
        if not number:
            return ''  # This wouldn't happen in the file as it's caught in the validation errors, but the vals are exported before these checks are done.
        return number.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')

    @api.model
    def _l10n_my_edi_make_validation_error(self, constraints, code, record_identifier, record_name):
        """ Small helper that add new constrains into provided constrains dict.
        This helper is mainly there to keep the check method tidy, and focused on its purpose (validating data)
        """
        message_mapping = {
            'industrial_classification_required': _(
                "The industrial classification must be defined on company: %(company_name)s",
                company_name=record_name
            ),
            'phone_number_format': _(
                "The following partner's phone number should follow the E.164 format: %(partner_name)s",
                partner_name=record_name
            ),
            'phone_number_required': _(
                "The following partner's phone number is missing: %(partner_name)s",
                partner_name=record_name)
            ,
            'required_id': _(
                "The following partner's identification type or number is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_state': _(
                "The following partner's state is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_city': _(
                "The following partner's city is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_country': _(
                "The following partner's country is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'no_street': _(
                "The following partner's street is missing: %(partner_name)s",
                partner_name=record_name
            ),
            'class_code_required': _(
                "You must set a classification code either on the line itself or on the product of line: %(line_name)s",
                line_name=record_name
            ),
            'adjustment_origin': _(
                "You cannot send a debit / credit note for invoice %(invoice_number)s as it has not yet been sent to MyInvois.",
                invoice_number=record_name
            ),
            'too_many_sst': _(
                "The following partner's should have at most two SST numbers, separated by a semicolon : %(partner_name)s",
                partner_name=record_name
            ),
            'tax_ids_required': _(
                "You must set a tax on the line : %(line_name)s.\nIf taxes are not applicable, please set a 0%% tax with a tax type 'Not Applicable'.",
                line_name=record_name
            ),
            'tax_exemption_required': _(
                "You must set a Tax Exemption Reason on the invoice : %(invoice_name)s as some taxes have the type 'Tax exemption' without a reason set.",
                invoice_name=record_name
            ),
            'tax_exemption_required_on_tax': _(
                "You must set a Tax Exemption Reason on each tax exempt taxes in order to use them in a Myinvois Document.",
            ),
            'missing_general_public': _(
                "You must have a commercial partner named 'General Public' with a VAT number set to 'EI00000000010' in order to proceed.",
            ),
        }

        constraints[f'myinvois_{record_identifier}_{code}'] = message_mapping[code]
