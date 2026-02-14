from odoo import _, models, tools
from odoo.tools import html2plaintext
from odoo.tools.float_utils import float_round

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID = '320'

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

SCHEME_ID_MAPPING = {
    '0088': 'GLN',
    '0184': 'DK:CVR',
    '9918': 'IBAN',
    '0198': 'DK:SE',
}


def format_vat_number(partner, vat):
    vat = (vat or '').replace(' ', '')
    if vat[:2].isnumeric():
        vat = partner.country_code.upper() + vat
    return vat


class AccountEdiXmlOIOUBL21(models.AbstractModel):
    _name = "account.edi.xml.oioubl_21"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "OIOUBL 2.1"

    # Data validation Schematron available at the following URL:
    # https://rep.erst.dk/git/openebusiness/common/-/tree/master/resources/Schematrons/OIOUBL

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_oioubl_21.xml"

    def _get_currency_decimal_places(self, currency_id):
        # OIOUBL needs the data to be formated to 2 decimals
        return 2

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'OIOUBL-2.1'

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_20
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            building_number = tools.street_split(partner.street).get('street_number')
            if not building_number:
                constraints[f"oioubl21_{partner_type}_building_number_required"] = _("The following partner's street number is missing: %s", partner.display_name)
            if partner.country_code == "FR" and not partner.commercial_partner_id.company_registry:
                constraints["oioubl21_company_registry_required_for_french_partner"] = _("The company registry is required for french partner: %s", partner.display_name)
            constraints[f'oioubl21_{partner_type}_vat_required'] = self._check_required_fields(partner.commercial_partner_id, 'vat')
        constraints['oioubl21_supplier_company_registry_required'] = self._check_required_fields(vals['supplier'], 'company_registry')

        return constraints

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_header_nodes(document_node, vals)
        document_node.update({
            'cbc:CustomizationID': {'_text': self._get_customization_id()},
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
            'cbc:CreditNoteTypeCode': {
                '_text': 381,
                'listID': 'urn:oioubl:codelist:invoicetypecode-1.2',
                'listAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,

            } if vals['document_type'] == 'credit_note' else None,
        })

    def _get_document_type_code_node(self, invoice, invoice_data):
        # EXTENDS 'account_edi_ubl_cii
        # http://www.datypic.com/sc/ubl20/e-cbc_DocumentTypeCode.html
        return {
            '_text': '380' if invoice.move_type == 'out_invoice' else '381',
            'listAgencyID': '6',
            'listID': 'UN/ECE 1001',
        }

    def _get_address_node(self, vals):
        # EXTENDS account.edi.xml.ubl_20
        address_node = super()._get_address_node(vals)
        # https://www.oioubl.info/Classes/en/Address.html
        address = tools.street_split(vals['partner'].street)
        street_name = address.get('street_name')
        building_number = address.get('street_number')
        address_node.update({
            'cbc:AddressFormatCode': {
                # could be 'UN/CEFACT codelist 3477' instead of StructuredDK' for partner out of DK
                # not implemented yet because `StructuredDK` seems more than enough
                '_text': 'StructuredDK',
                'listAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,
                'listID': 'urn:oioubl:codelist:addressformatcode-1.1',
            },
            'cbc:StreetName': {'_text': street_name},
            'cbc:BuildingNumber': {'_text': building_number},
        })

        return address_node

    def _get_party_node(self, vals):
        # EXTENDS account.edi.xml.ubl_20
        party_node = super()._get_party_node(vals)
        partner = vals['partner']
        vat = format_vat_number(partner, partner.vat)
        cvr = format_vat_number(partner, partner.company_registry) or vat
        party_node['cac:PartyLegalEntity'].update({
            # Even if not enforced by Schematron, only CVR (CPR which we don't use) can be used
            # https://oioubl21.oioubl.dk/Classes/da/PartyLegalEntity.html
            'cbc:CompanyID': {
                '_text': cvr,
                'schemeID': 'DK:CVR' if vat[:2] == 'DK' else 'ZZZ'
            },
        })
        if vat and vat != '/':
            party_node['cac:PartyTaxScheme'].update({
                # Only DK:SE for PartyTaxScheme https://oioubl21.oioubl.dk/Classes/da/PartyTaxScheme.html
                'cbc:CompanyID': {
                    '_text': vat,
                    'schemeID': 'DK:SE' if vat[:2] == 'DK' else 'ZZZ'
                },
                'cac:TaxScheme': {
                    'cbc:ID': {
                        '_text': 63,
                        'schemeID': 'urn:oioubl:id:taxschemeid-1.5',
                    },
                    'cbc:Name': {'_text': 'Moms'},
                },
            })
        if partner.nemhandel_identifier_type and partner.nemhandel_identifier_value:
            prefix = 'DK' if partner.nemhandel_identifier_type == '0184' else ''
            party_node['cbc:EndpointID'] = {
                '_text': f'{prefix}{partner.nemhandel_identifier_value}',
                'schemeID': SCHEME_ID_MAPPING[partner.nemhandel_identifier_type],
            }

        return party_node

    def _get_tax_subtotal_node(self, vals):
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        # No 'percent' node in OIOUBL https://www.oioubl.info/Classes/en/TaxSubtotal.html
        tax_subtotal_node['cbc:Percent'] = None
        return tax_subtotal_node

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_20
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        payment_means_node['cbc:PaymentMeansCode'] = {
            '_text': 1,
            'name': 'unknown',
        }

        invoice = vals['invoice']
        supplier = vals['supplier']
        if (
            invoice.partner_bank_id in supplier.bank_ids
            and payment_means_node.get('cac:PayeeFinancialAccount')
            and payment_means_node['cac:PayeeFinancialAccount'].get('cac:FinancialInstitutionBranch')
            and payment_means_node['cac:PayeeFinancialAccount']['cac:FinancialInstitutionBranch'].get('cac:FinancialInstitution')
        ):
            payment_means_node['cac:PayeeFinancialAccount']['cac:FinancialInstitutionBranch']['cac:FinancialInstitution']['cac:Address'] = None

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # EXTENDS account_edi_xml_ubl_20
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        currency_suffix = vals['currency_suffix']
        document_node[monetary_total_tag]['cbc:TaxExclusiveAmount'] = {
            # In OIOUBL context, tax_exclusive_amount means "tax only"
            '_text': self.format_float(
                vals[f'tax_inclusive_amount{currency_suffix}'] - vals[f'tax_exclusive_amount{currency_suffix}'],
                vals['currency_dp'],
            ),
            'currencyID': vals['currency_name'],
        }
        # PrepaidAmount must not be present if equal to 0
        if document_node[monetary_total_tag].get('cbc:PrepaidAmount') and document_node[monetary_total_tag]['cbc:PrepaidAmount'].get('_text') == FloatFmt(0, 2):
            document_node[monetary_total_tag]['cbc:PrepaidAmount'] = None

    def _get_tax_category_node(self, vals):
        # EXTENDS account_edi_xml_ubl_20
        tax_category_node = super()._get_tax_category_node(vals)
        # TaxCategory https://www.oioubl.info/Classes/en/TaxCategory.html
        tax_category_node['cbc:ID'].update({
            '_text': UBL_TO_OIOUBL_TAX_CATEGORY_ID_MAPPING.get(tax_category_node['cbc:ID']['_text']),
            'schemeID': 'urn:oioubl:id:taxcategoryid-1.3',
            'schemeAgencyID': DANISH_NATIONAL_IT_AND_TELECOM_AGENCY_ID,
        })
        tax_category_node['cac:TaxScheme'] = {
            'cbc:ID': {
                '_text': 63,
                'schemeID': 'urn:oioubl:id:taxschemeid-1.5',
            },
            'cbc:Name': {'_text': 'Moms'},
        }

        # OIOUBL can't contain name for category
        # /Invoice[1]/cac:InvoiceLine[1]/cac:Item[1]/cac:ClassifiedTaxCategory[1]
        # [W-LIB230] Name should only be used within NES profiles
        # (cbc:Name != '') and not(contains(/doc:Invoice/cbc:ProfileID, 'nesubl.eu'))
        tax_category_node['cbc:Name'] = None
        return tax_category_node

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        # Override account_edi_xml_ubl_20 and not extends as it is not returning a list in the base
        invoice = vals['invoice']
        if payment_term := invoice.invoice_payment_term_id:
            sign = 1 if invoice.is_inbound(include_receipts=True) else -1
            document_node['cac:PaymentTerms'] = [
                {
                    'cbc:ID': {'_text': line.id},
                    'cbc:Note': {'_text': html2plaintext(payment_term.note)},
                    'cbc:Amount': {
                        '_text': self.format_float(sign * line.amount_currency, 2),  # OIOUBL needs format to 2 decimals
                        'currencyID': line.currency_id.name,
                    },
                    'cac:SettlementPeriod': {
                        'cbc:StartDate': {'_text': invoice.invoice_date},
                        'cbc:EndDate': {'_text': line.date_maturity},
                    },
                }
                for line in
                invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term').sorted('date_maturity')
            ]

    def _add_document_line_price_nodes(self, line_node, vals):
        # Override 'account.edi.xml.ubl_20' to accomodate to oioubl_21 specific rules
        currency_suffix = vals['currency_suffix']
        base_line = vals['base_line']
        product_price_dp = self.env['decimal.precision'].precision_get('Product Price')

        line_node['cac:Price'] = {
            # Rule F-INV348 enforces that lineExtensionAmount equals directly PriceAmount * Quantity, while other
            # rules enforce that lineExtensionAmount should not change compared to what we do in ubl_20
            'cbc:PriceAmount': {
                '_text': float_round(
                    vals[f'gross_price_unit{currency_suffix}'] * (1 - base_line['discount'] / 100),
                    precision_digits=product_price_dp,
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _retrieve_rebate_val(self, tree, xpath_dict, quantity):
        # Override 'account.edi.xml.ubl_20' to include AllowanceCharge in it, as PriceAmount is different in OIOUBL
        rebate = super()._retrieve_rebate_val(tree, xpath_dict, quantity)

        discount_amount, charges = self._retrieve_charge_allowance_vals(tree, xpath_dict, quantity)
        charge_amount = sum(d['amount'] for d in charges)

        return rebate + (discount_amount - charge_amount) / quantity
