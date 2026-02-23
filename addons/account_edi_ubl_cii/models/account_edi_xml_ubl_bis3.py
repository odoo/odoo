# -*- coding: utf-8 -*-
from markupsafe import Markup
from typing import Literal

from odoo import _, api, models
from odoo.tools.misc import formatLang, NON_BREAKING_SPACE
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import (
    FloatFmt,
    GST_COUNTRY_CODES,
    EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES,
)
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

from stdnum.no import mva

CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'account.edi.xml.ubl_bis3'
    _inherit = ['account.edi.xml.ubl_21']
    _description = "UBL BIS Billing 3.0.12"

    """
    * Documentation of EHF Billing 3.0: https://anskaffelser.dev/postaward/g3/
    * EHF 2.0 is no longer used:
      https://anskaffelser.dev/postaward/g2/announcement/2019-11-14-removal-old-invoicing-specifications/
    * Official doc for EHF Billing 3.0 is the OpenPeppol BIS 3 doc +
      https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/

        "Based on work done in PEPPOL BIS Billing 3.0, Difi has included Norwegian rules in PEPPOL BIS Billing 3.0 and
        does not see a need to implement a different CIUS targeting the Norwegian market. Implementation of EHF Billing
        3.0 is therefore done by implementing PEPPOL BIS Billing 3.0 without extensions or extra rules."

    Thus, EHF 3 and Bis 3 are actually the same format. The specific rules for NO defined in Bis 3 are added in Bis 3.

    To avoid multi-parental inheritance in case of UBL 4.0, we're adding the sale/purchase logic here.
    * Documentation for Peppol Order transaction 3.5: https://docs.peppol.eu/poacc/upgrade-3/syntax/Order/tree/
    """

    @api.model
    def _is_customer_behind_chorus_pro(self, customer):
        return customer.peppol_eas and customer.peppol_endpoint and f"{customer.peppol_eas}:{customer.peppol_endpoint}" == CHORUS_PRO_PEPPOL_ID

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_bis3.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates for invoice header nodes
    # -------------------------------------------------------------------------

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)
        invoice = vals['invoice']
        vals['process_type'] = 'selfbilling' if invoice.is_purchase_document() and invoice.journal_id.is_self_billing else 'billing'
        self._ubl_add_values_company(vals, invoice.company_id)
        self._ubl_add_values_currency(vals, invoice.currency_id)
        self._ubl_add_values_customer(vals, invoice.partner_id)
        self._ubl_add_values_delivery(vals, invoice.partner_shipping_id or invoice.partner_id)
        if vals['process_type'] == 'selfbilling':
            customer = vals['customer']
            supplier = vals['supplier']
            vals['supplier'] = customer
            vals['customer'] = supplier
            vals['delivery'] = supplier

    def _can_export_selfbilling(self):
        return bool(self._get_customization_id(process_type='selfbilling'))

    def _get_customization_id(self, process_type: Literal['billing', 'selfbilling'] = 'billing'):
        if process_type == 'billing':
            return 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'
        else:
            return 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0'

    def _add_invoice_header_nodes(self, document_node, vals):
        # Call the parent method from UBL 2.1
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        ubl_values = vals['_ubl_values']

        # Override specific BIS3 values
        document_node.update({
            'cbc:UBLVersionID': None,
            'cbc:CustomizationID': {'_text': self._get_customization_id(vals['process_type'])},
            'cbc:ProfileID': {'_text': f"urn:fdc:peppol.eu:2017:poacc:{vals['process_type']}:01:1.0"},
            'cbc:TaxCurrencyCode': {'_text': vals['tax_currency_code']},
        })
        # For B2G transactions in Germany: set the buyer_reference to the Leitweg-ID (code 0204)
        if invoice.commercial_partner_id.peppol_eas == '0204':
            document_node.update({
                'cbc:BuyerReference': {'_text': invoice.commercial_partner_id.peppol_endpoint}
            })

        if tax_withholding_amount := ubl_values['payable_amount_tax_withholding_currency']:
            note = _(
                "The prepaid amount of %s corresponds to the withholding tax applied.",
                formatLang(self.env, tax_withholding_amount, currency_obj=vals['currency_id']).replace(NON_BREAKING_SPACE, ''),
            )
            narration_note = document_node['cbc:Note']['_text']
            if narration_note:
                note = f'{note} {narration_note}'
            document_node['cbc:Note']['_text'] = note

        # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST
        # contain an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
        if vals['supplier'].country_id.code == 'NL' and 'refund' in invoice.move_type:
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.ref},
                }
            }

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        super()._add_invoice_payment_means_nodes(document_node, vals)
        document_node['cac:PaymentMeans']['cbc:PaymentDueDate'] = None
        document_node['cac:PaymentMeans']['cbc:InstructionID'] = None

    def _get_financial_account_node(self, vals):
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-664]-A UBL invoice should not include the FinancialInstitutionBranch FinancialInstitution
        # xpath test: not(//cac:FinancialInstitution)
        financial_account_node = super()._get_financial_account_node(vals)

        if financial_account_node['cac:FinancialInstitutionBranch']:
            financial_account_node['cac:FinancialInstitutionBranch']['cac:FinancialInstitution'] = None

            if financial_account_node['cac:FinancialInstitutionBranch']['cbc:ID']:
                financial_account_node['cac:FinancialInstitutionBranch']['cbc:ID']['schemeID'] = None

        return financial_account_node

    # -------------------------------------------------------------------------
    # EXPORT: Gathering data
    # -------------------------------------------------------------------------

    def _setup_base_lines(self, vals):
        # OVERRIDE
        AccountTax = self.env['account.tax']
        company = vals['company']

        # Avoid negative unit price.
        self._ubl_turn_base_lines_price_unit_as_always_positive(vals)

        # Manage taxes for emptying.
        vals['base_lines'] = self._ubl_turn_emptying_taxes_as_new_base_lines(vals['base_lines'], company, vals)

        vals['_ubl_values'] = {}
        for base_line in vals['base_lines']:
            base_line['_ubl_values'] = {}

        # Global rounding of tax_details using 6 digits.
        AccountTax._round_raw_total_excluded(vals['base_lines'], company)
        AccountTax._round_raw_total_excluded(vals['base_lines'], company, in_foreign_currency=False)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company, in_foreign_currency=False)
        AccountTax._round_raw_gross_total_excluded_and_discount(vals['base_lines'], company)
        AccountTax._round_raw_gross_total_excluded_and_discount(vals['base_lines'], company, in_foreign_currency=False)

        # Add 'price_amount' being the original price unit without tax.
        self._ubl_add_base_line_ubl_values_price(vals)

        # Add 'tax_currency_code'.
        self._ubl_add_values_tax_currency_code(vals)

        # Add 'payable_rounding_amount' to manage cash rounding.
        self._ubl_add_values_payable_rounding_amount(vals)

        # Extract cash rounding lines.
        vals['base_lines'] = [
            base_line
            for base_line in vals['base_lines']
            if base_line not in vals['_ubl_values']['payable_rounding_base_lines']
        ]

        # Add 'payable_amount' to manage withholding taxes.
        self._ubl_add_values_payable_amount_tax_withholding(vals)

        # Add 'allowance_charge_early_payment' to manage the early payment discount.
        self._ubl_add_values_allowance_charge_early_payment(vals)

    def _add_invoice_line_vals(self, vals):
        # OVERRIDE
        # Those temporary values are wrongly computed and the similar data are added to the base lines in
        # 'setup_base_lines' because we need to compute them on all lines at once instead of on each line
        # separately.
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Build Nodes
    # -------------------------------------------------------------------------

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS
        # Recycling contribution taxes / excises should not appear anywhere as taxes but as allowances/charges.
        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        # Since this method produces a default 0% tax automatically when no tax is set on the line by default,
        # we have to do something here to avoid it.
        if (
            self._ubl_is_cash_rounding_base_line(base_line)
            or self._ubl_is_recycling_contribution_tax(tax_data)
            or self._ubl_is_excise_tax(tax_data)
        ):
            return
        return super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'line_vals': {
                'base_line': vals['base_line'],
            },
        }
        self._ubl_add_line_allowance_charge_nodes(sub_vals)

        # Discount.
        self._ubl_add_line_allowance_charge_nodes_for_discount(sub_vals)

        # Recycling contribution taxes.
        self._ubl_add_line_allowance_charge_nodes_for_recycling_contribution_taxes(sub_vals)

        # Excise taxes.
        self._ubl_add_line_allowance_charge_nodes_for_excise_taxes(sub_vals)

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'line_vals': {
                'base_line': vals['base_line'],
            },
        }

        if vals['document_type'] == 'credit_note':
            self._ubl_add_line_credited_quantity_node(sub_vals)
        elif vals['document_type'] == 'debit_note':
            self._ubl_add_line_debited_quantity_node(sub_vals)
        else:
            self._ubl_add_line_invoiced_quantity_node(sub_vals)

        self._ubl_add_line_extension_amount_node(sub_vals)

    def _add_invoice_line_item_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'line_vals': {
                'base_line': vals['base_line'],
            },
        }
        self._ubl_add_line_item_node(sub_vals)

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_price_nodes(self, line_node, vals):
        # OVERRIDE
        base_line = vals['base_line']
        ubl_values = base_line['_ubl_values']

        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': FloatFmt(ubl_values['price_amount_currency'], min_dp=1, max_dp=6),
                'currencyID': vals['currency_name'],
            },
        }

    def _ubl_get_partner_address_node(self, vals, partner):
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_partner_address_node(vals, partner)
        node['cbc:CountrySubentityCode'] = None
        node['cac:Country']['cbc:Name'] = None
        return node

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_endpoint_id_node(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        if commercial_partner.peppol_endpoint and commercial_partner.peppol_eas:
            vals['party_node']['cbc:EndpointID']['_text'] = commercial_partner.peppol_endpoint
            vals['party_node']['cbc:EndpointID']['schemeID'] = commercial_partner.peppol_eas

    def _ubl_add_party_identification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_identification_nodes(vals)
        nodes = vals['party_node']['cac:PartyIdentification']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code == 'BE' and commercial_partner.company_registry:
            nodes.append({
                'cbc:ID': {
                    '_text': commercial_partner.company_registry,
                    'schemeID': '0208',
                },
            })
        elif commercial_partner.ref:
            nodes.append({
                'cbc:ID': {
                    '_text': commercial_partner.ref,
                    'schemeID': None,
                },
            })

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.vat and commercial_partner.vat != '/':
            country_code = commercial_partner.country_id.code
            if country_code in GST_COUNTRY_CODES:
                tax_scheme_id = 'GST'
            else:
                tax_scheme_id = 'VAT'

            nodes.append({
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': tax_scheme_id},
                },
            })
        elif commercial_partner.peppol_endpoint and commercial_partner.peppol_eas:
            # TaxScheme based on partner's EAS/Endpoint.
            nodes.append({
                'cbc:CompanyID': {'_text': commercial_partner.peppol_endpoint},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': commercial_partner.peppol_eas},
                },
            })

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.peppol_eas in ('0106', '0190'):
            nl_id = commercial_partner.peppol_endpoint
        else:
            nl_id = commercial_partner.company_registry

        if commercial_partner.country_code == 'NL' and nl_id:
            # For NL, VAT can be used as a Peppol endpoint, but KVK/OIN has to be used as PartyLegalEntity/CompanyID
            # To implement a workaround on stable, company_registry field is used without recording whether
            # the number is a KVK or OIN, and the length of the number (8 = KVK, 20 = OIN) is used to determine the type
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': nl_id,
                    'schemeID': '0190' if len(nl_id) == 20 else '0106',
                },
            })
        elif commercial_partner.country_code == 'LU' and commercial_partner.company_registry:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.company_registry,
                    'schemeID': None,
                },
            })
        elif commercial_partner.country_code == 'SE' and commercial_partner.company_registry:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': ''.join(char for char in commercial_partner.company_registry if char.isdigit()),
                },
            })
        elif commercial_partner.country_code == 'BE' and commercial_partner.company_registry:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.company_registry,
                    'schemeID': '0208',
                },
            })
        elif (
            commercial_partner.country_code == 'DK'
            and commercial_partner.peppol_eas == '0184'
            and commercial_partner.peppol_endpoint
        ):
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.peppol_endpoint,
                    'schemeID': '0184',
                },
            })
        elif commercial_partner.vat and commercial_partner.vat != '/':
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.vat,
                    'schemeID': None,
                },
            })
        elif commercial_partner.peppol_endpoint:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.peppol_endpoint,
                    'schemeID': None,
                },
            })

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code == 'NO':
            nodes.append({
                'cbc:CompanyID': {'_text': "Foretaksregisteret"},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': "TAX"},
                },
            })

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_supplier_party_node(sub_vals)

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_customer_party_node(sub_vals)

    def _ubl_add_delivery_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_endpoint_id_node(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cbc:EndpointID'] = {
            '_text': None,
            'schemeID': None,
        }

    def _ubl_add_delivery_party_identification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_identification_nodes(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cac:PartyIdentification'] = []

    def _ubl_add_delivery_party_postal_address_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_postal_address_node(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cac:PostalAddress'] = None

    def _ubl_add_delivery_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_tax_scheme_nodes(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cac:PartyTaxScheme'] = []

    def _ubl_add_delivery_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_legal_entity_nodes(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cac:PartyLegalEntity'] = []

    def _ubl_add_delivery_party_contact_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_party_contact_node(vals)
        if not vals.get('invoice'):
            return

        vals['party_node']['cac:Contact'] = None

    def _ubl_get_delivery_node_from_delivery_address(self, vals):
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_delivery_node_from_delivery_address(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return node

        if invoice.delivery_date:
            node['cbc:ActualDeliveryDate']['_text'] = invoice.delivery_date

        # Intracom delivery inside European area.
        customer = vals['customer']
        supplier = vals['supplier']
        if (
            customer.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
            and supplier.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
            and supplier.country_id != customer.country_id
        ):
            node['cbc:ActualDeliveryDate']['_text'] = invoice.invoice_date
        return node

    def _add_invoice_delivery_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_delivery_nodes(sub_vals)
        # Retro-compatibility with the "old" code.
        if document_node['cac:Delivery']:
            document_node['cac:Delivery'] = document_node['cac:Delivery'][0]

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        # OVERRIDE
        ubl_values = vals['_ubl_values']
        document_node['cac:AllowanceCharge'] = [
            self._ubl_get_allowance_charge_early_payment(vals, early_payment_values)
            for early_payment_values in ubl_values['allowance_charges_early_payment_currency']
        ]

    def _ubl_get_tax_subtotal_node(self, vals, tax_subtotal):
        # EXTENDS account.edi.xml.ubl
        node = super()._ubl_get_tax_subtotal_node(vals, tax_subtotal)

        # [BR-S-08] cac:TaxSubtotal -> cbc:TaxableAmount should be computed based on the
        # cbc:LineExtensionAmount of each line linked to the tax when cac:TaxCategory -> cbc:ID is S
        # (Standard Rate).
        currency = tax_subtotal['currency']
        corresponding_line_node_amounts = [
            line_node['cbc:LineExtensionAmount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            if tax_category_node['cbc:ID']['_text'] == 'S'
            for line_key in ('cac:InvoiceLine', 'cac:CreditNoteLine', 'cac:DebitNoteLine')
            for line_node in vals['document_node'].get(line_key, [])
            for line_node_tax_category_node in line_node['cac:Item']['cac:ClassifiedTaxCategory']
            if (
                line_node_tax_category_node['cbc:ID']['_text'] == 'S'
                and line_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                and line_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
        ] + [
            -allowance_node['cbc:Amount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            if tax_category_node['cbc:ID']['_text'] == 'S'
            for allowance_node in vals['document_node']['cac:AllowanceCharge']
            if allowance_node['cbc:ChargeIndicator']['_text'] == 'false'
            for allowance_node_tax_category_node in allowance_node['cac:TaxCategory']
            if (
                allowance_node_tax_category_node['cbc:ID']['_text'] == 'S'
                and allowance_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                and allowance_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
        ] + [
            allowance_node['cbc:Amount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            if tax_category_node['cbc:ID']['_text'] == 'S'
            for allowance_node in vals['document_node']['cac:AllowanceCharge']
            if allowance_node['cbc:ChargeIndicator']['_text'] == 'true'
            for allowance_node_tax_category_node in allowance_node['cac:TaxCategory']
            if (
                allowance_node_tax_category_node['cbc:ID']['_text'] == 'S'
                and allowance_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                and allowance_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
        ]
        if corresponding_line_node_amounts:
            node['cbc:TaxableAmount'] = {
                '_text': FloatFmt(sum(corresponding_line_node_amounts), min_dp=currency.decimal_places),
                'currencyID': currency.name,
            }

        return node

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl
        tax_total_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        if tax_total_keys['tax_total_key'] and tax_total_keys['tax_total_key']['is_withholding']:
            tax_total_keys['tax_total_key'] = None

        # In case of multi-currencies, there will be 2 TaxTotals but the one expressed in
        # foreign currency must not have any TaxSubtotal.
        company_currency = vals['company'].currency_id
        if (
            tax_total_keys['tax_subtotal_key']
            and company_currency != vals['currency']
            and tax_total_keys['tax_subtotal_key']['currency'] == company_currency
        ):
            tax_total_keys['tax_subtotal_key'] = None

        return tax_total_keys

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_tax_totals_nodes(sub_vals)

    def _add_invoice_monetary_total_vals(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        ubl_values = vals['_ubl_values']
        invoice = vals['invoice']
        line_tag = self._get_tags_for_document_type(vals)['document_line']

        line_extension_amount = sum(
            line_node['cbc:LineExtensionAmount']['_text']
            for line_node in document_node[line_tag]
        )
        tax_amount = sum(
            tax_total['cbc:TaxAmount']['_text']
            for tax_total in document_node['cac:TaxTotal']
            if tax_total['cbc:TaxAmount']['currencyID'] == vals['currency_id'].name
        )
        total_allowance = sum(
            allowance_charge['cbc:Amount']['_text']
            for allowance_charge in document_node['cac:AllowanceCharge']
            if allowance_charge['cbc:ChargeIndicator']['_text'] == 'false'
        )
        total_charge = sum(
            allowance_charge['cbc:Amount']['_text']
            for allowance_charge in document_node['cac:AllowanceCharge']
            if allowance_charge['cbc:ChargeIndicator']['_text'] == 'true'
        )
        payable_rounding_amount = ubl_values['payable_rounding_amount_currency']
        payable_amount_tax_withholding_currency = ubl_values['payable_amount_tax_withholding_currency']

        document_node[monetary_total_tag] = {
            'cbc:LineExtensionAmount': {
                '_text': FloatFmt(line_extension_amount, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxExclusiveAmount': {
                '_text': FloatFmt(line_extension_amount, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxInclusiveAmount': {
                '_text': FloatFmt(line_extension_amount + tax_amount, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:AllowanceTotalAmount': {
                '_text': FloatFmt(total_allowance, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if total_allowance else None,
            'cbc:ChargeTotalAmount': {
                '_text': FloatFmt(total_charge, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if total_charge else None,
            'cbc:PrepaidAmount': {
                '_text': FloatFmt(payable_amount_tax_withholding_currency + invoice.amount_total - invoice.amount_residual, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableRoundingAmount': {
                '_text': FloatFmt(payable_rounding_amount, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if payable_rounding_amount else None,
            'cbc:PayableAmount': {
                '_text': FloatFmt(invoice.amount_residual, min_dp=vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_21
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )

        return constraints

    def _invoice_constraints_cen_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by ' schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt' for invoices.
        This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/CEN-EN16931-UBL.sch.
        """
        eu_countries = self.env.ref('base.europe').country_ids
        intracom_delivery = (vals['customer'].country_id in eu_countries
                             and vals['supplier'].country_id in eu_countries
                             and vals['customer'].country_id != vals['supplier'].country_id)

        nsmap = self._get_document_nsmap(vals)

        constraints = {
            # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
            # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
            # note: Payment account identifier is <cac:PayeeFinancialAccount>
            # note: no need to check account_number, because it's a required field for a partner_bank
            'cen_en16931_payment_account_identifier': self._check_required_fields(
                invoice, 'partner_bank_id'
            ) if vals['document_node']['cac:PaymentMeans']['cbc:PaymentMeansCode']['_text'] in (30, 58) else None,
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            'cen_en16931_delivery_country_code': (
                _("For intracommunity supply, the delivery address should be included.")
            ) if intracom_delivery and dict_to_xml(vals['document_node']['cac:Delivery']['cac:DeliveryLocation'], nsmap=nsmap, tag='cac:DeliveryLocation') is None else None,

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            'cen_en16931_delivery_date_invoicing_period': (
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
                if (
                    intracom_delivery
                    and dict_to_xml(vals['document_node']['cac:Delivery']['cbc:ActualDeliveryDate'], nsmap=nsmap, tag='cbc:ActualDeliveryDate') is None
                    and dict_to_xml(vals['document_node']['cac:InvoicePeriod'], nsmap=nsmap, tag='cac:InvoicePeriod') is None
                )
                else None
            )
        }

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        line_nodes = vals['document_node'][line_tag]

        for line_node in line_nodes:
            if not (line_node['cac:Item']['cbc:Name'] or {}).get('_text'):
                # [BR-25]-Each Invoice line (BG-25) shall contain the Item name (BT-153).
                constraints.update({'cen_en16931_item_name': _("Each invoice line should have a product or a label.")})
                break

            if len(line_node['cac:Item']['cac:ClassifiedTaxCategory']) != 1:
                # [UBL-SR-48]-Invoice lines shall have one and only one classified tax category.
                # /!\ exception: possible to have any number of ecotaxes (fixed tax) with a regular percentage tax
                constraints['cen_en16931_tax_line'] = _("Each invoice line shall have one and only one tax.")

        for role in ('supplier', 'customer'):
            party_node = vals['document_node']['cac:AccountingCustomerParty'] if role == 'customer' else vals['document_node']['cac:AccountingSupplierParty']
            constraints[f'cen_en16931_{role}_country'] = (
                _("The country is required for the %s.", role)
                if not party_node['cac:Party']['cac:PostalAddress']['cac:Country']['cbc:IdentificationCode']['_text']
                else None
            )
            tax_scheme_node = party_node['cac:Party']['cac:PartyTaxScheme']
            if tax_scheme_node and (
                self._name in ('account.edi.xml.ubl_bis3', 'account.edi.xml.ubl_nl', 'account.edi.xml.ubl_de')
                and (tax_scheme_node[0]['cac:TaxScheme']['cbc:ID']['_text'] == 'VAT')
                and not (tax_scheme_node[0]['cbc:CompanyID']['_text'][:2].isalpha())
            ):
                # [BR-CO-09]-The Seller VAT identifier (BT-31), the Seller tax representative VAT identifier (BT-63)
                # and the Buyer VAT identifier (BT-48) shall have a prefix in accordance with ISO code ISO 3166-1
                # alpha-2 by which the country of issue may be identified. Nevertheless, Greece may use the prefix 'EL'.
                constraints.update({f'cen_en16931_{role}_vat_country_code': _(
                    "The VAT of the %s should be prefixed with its country code.", role)})

        if invoice.partner_shipping_id:
            # [BR-57]-Each Deliver to address (BG-15) shall contain a Deliver to country code (BT-80).
            constraints['cen_en16931_delivery_address'] = self._check_required_fields(invoice.partner_shipping_id, 'country_id')
        return constraints

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        nsmap = self._get_document_nsmap(vals)
        constraints = {
            # PEPPOL-EN16931-R003: A buyer reference or purchase order reference MUST be provided.
            'peppol_en16931_ubl_buyer_ref_po_ref':
                "A buyer reference or purchase order reference must be provided." if (
                    dict_to_xml(vals['document_node']['cbc:BuyerReference'], nsmap=nsmap, tag='cbc:BuyerReference') is None
                    and dict_to_xml(vals['document_node']['cac:OrderReference'], nsmap=nsmap, tag='cac:OrderReference') is None
                ) else None,
        }

        if vals['supplier'].country_id.code == 'NL':
            constraints.update({
                # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST contain
                # an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
                'nl_r_001': self._check_required_fields(invoice, 'ref') if 'refund' in invoice.move_type else '',

                # [NL-R-002] For suppliers in the Netherlands the supplier's address (cac:AccountingSupplierParty/cac:Party
                # /cac:PostalAddress) MUST contain street name (cbc:StreetName), city (cbc:CityName) and post code (cbc:PostalZone)
                'nl_r_002_street': self._check_required_fields(vals['supplier'], 'street'),
                'nl_r_002_zip': self._check_required_fields(vals['supplier'], 'zip'),
                'nl_r_002_city': self._check_required_fields(vals['supplier'], 'city'),

                # [NL-R-003] For suppliers in the Netherlands, the legal entity identifier MUST be either a
                # KVK or OIN number (schemeID 0106 or 0190)
                'nl_r_003': _(
                    "%s should have a KVK or OIN number set in Company ID field or as Peppol e-address (EAS code 0106 or 0190).",
                    vals['supplier'].display_name
                ) if (
                    not vals['supplier'].peppol_eas in ('0106', '0190') and
                    (not vals['supplier'].company_registry or len(vals['supplier'].company_registry) not in (8, 9))
                ) else '',

                # [NL-R-007] For suppliers in the Netherlands, the supplier MUST provide a means of payment
                # (cac:PaymentMeans) if the payment is from customer to supplier
                'nl_r_007': self._check_required_fields(invoice, 'partner_bank_id')
            })

            if vals['customer'].country_id.code == 'NL':
                constraints.update({
                    # [NL-R-004] For suppliers in the Netherlands, if the customer is in the Netherlands, the customer
                    # address (cac:AccountingCustomerParty/cac:Party/cac:PostalAddress) MUST contain the street name
                    # (cbc:StreetName), the city (cbc:CityName) and post code (cbc:PostalZone)
                    'nl_r_004_street': self._check_required_fields(vals['customer'], 'street'),
                    'nl_r_004_city': self._check_required_fields(vals['customer'], 'city'),
                    'nl_r_004_zip': self._check_required_fields(vals['customer'], 'zip'),

                    # [NL-R-005] For suppliers in the Netherlands, if the customer is in the Netherlands,
                    # the customer's legal entity identifier MUST be either a KVK or OIN number (schemeID 0106 or 0190)
                    'nl_r_005': _(
                        "%s should have a KVK or OIN number set in Company ID field or as Peppol e-address (EAS code 0106 or 0190).",
                        vals['customer'].display_name
                    ) if (
                        not vals['customer'].commercial_partner_id.peppol_eas in ('0106', '0190') and
                        (not vals['customer'].commercial_partner_id.company_registry or len(vals['customer'].commercial_partner_id.company_registry) not in (8, 9))
                    ) else '',
                })

        if vals['supplier'].country_id.code == 'NO':
            vat = vals['supplier'].vat
            constraints.update({
                # NO-R-001: For Norwegian suppliers, a VAT number MUST be the country code prefix NO followed by a
                # valid Norwegian organization number (nine numbers) followed by the letters MVA.
                # Note: mva.is_valid("179728982MVA") is True while it lacks the NO prefix
                'no_r_001': _(
                    "The VAT number of the supplier does not seem to be valid. It should be of the form: NO179728982MVA."
                ) if not mva.is_valid(vat) or len(vat) != 14 or vat[:2] != 'NO' or vat[-3:] != 'MVA' else "",
            })

        return constraints

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        endpoint_node = tree.find(f'.//cac:{role}Party/cac:Party/cbc:EndpointID', UBL_NAMESPACES)
        if endpoint_node is not None:
            peppol_eas = endpoint_node.attrib.get('schemeID')
            peppol_endpoint = endpoint_node.text
            if peppol_eas and peppol_endpoint:
                # include the EAS and endpoint in the search domain when retrieving the partner
                partner_vals.update({
                    'peppol_eas': peppol_eas,
                    'peppol_endpoint': peppol_endpoint,
                })
        return partner_vals

    # -------------------------------------------------------------------------
    # Sale/Purchase Order: Import
    # -------------------------------------------------------------------------

    def _import_order_payment_terms_id(self, company_id, tree, xpath):
        """ Return payment term name from given tree and try to find a match. """
        payment_term_name = self._find_value(xpath, tree)
        if not payment_term_name:
            return False
        payment_term_domain = self.env['account.payment.term']._check_company_domain(company_id)
        payment_term_domain.append(('name', '=', payment_term_name))
        return self.env['account.payment.term'].search(payment_term_domain, limit=1)

    def _retrieve_order_vals(self, order, tree):
        order_vals = {}
        logs = []

        order_vals['date_order'] = tree.findtext('.//{*}EndDate') or tree.findtext('.//{*}IssueDate')
        order_vals['note'] = self._import_description(tree, xpaths=['./{*}Note'])
        order_vals['payment_term_id'] = self._import_order_payment_terms_id(order.company_id, tree, './/cac:PaymentTerms/cbc:Note')
        order_vals['currency_id'], currency_logs = self._import_currency(tree, './/{*}DocumentCurrencyCode')

        logs += currency_logs
        return order_vals, logs

    def _import_order_ubl(self, order, file_data, new):
        """ Common importing method to extract order data from file_data.
        :param order: Order to fill details from file_data.
        :param file_data: File data to extract order related data from.
        :return: True if there's no exception while extraction.
        :rtype: Boolean
        """
        tree = file_data['xml_tree']

        # Update the order.
        order_vals, logs = self._retrieve_order_vals(order, tree)
        if order:
            order.write(order_vals)
            order.message_post(body=Markup("<strong>%s</strong>") % _("Format used to import the document: %s", self._description))
            if logs:
                order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in logs))
