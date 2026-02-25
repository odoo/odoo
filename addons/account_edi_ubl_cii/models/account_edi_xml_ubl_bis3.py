# -*- coding: utf-8 -*-
from markupsafe import Markup
from typing import Literal

from odoo import _, api, models
from odoo.tools import html2plaintext
from odoo.tools.misc import formatLang, NON_BREAKING_SPACE
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import (
    FloatFmt,
    GST_COUNTRY_CODES,
    EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES,
)
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

from stdnum.no import mva
from stdnum.be import vat as be_vat

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

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_customization_id_node(vals)
        if vals.get('process_type') == 'selfbilling':
            vals['document_node']['cbc:CustomizationID']['_text'] = 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0'
        else:
            vals['document_node']['cbc:CustomizationID']['_text'] = 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'

    def _ubl_add_profile_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_profile_id_node(vals)
        if vals.get('process_type') == 'selfbilling':
            vals['document_node']['cbc:ProfileID']['_text'] = 'urn:fdc:peppol.eu:2017:poacc:selfbilling:01:1.0'
        else:
            vals['document_node']['cbc:ProfileID']['_text'] = 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'

    def _ubl_add_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_id_node(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        vals['document_node']['cbc:ID']['_text'] = invoice.name

    def _ubl_add_issue_date_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_issue_date_node(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        vals['document_node']['cbc:IssueDate']['_text'] = invoice.invoice_date

    def _ubl_add_due_date_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_due_date_node(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        vals['document_node']['cbc:DueDate']['_text'] = invoice.invoice_date_due

    def _ubl_add_invoice_type_code_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_invoice_type_code_node(vals)
        if vals['document_type'] != 'invoice':
            return

        if vals.get('process_type') == 'selfbilling':
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 389
        else:
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 380

    def _ubl_add_credit_note_type_code_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_credit_note_type_code_node(vals)
        if vals['document_type'] != 'credit_note':
            return

        if vals.get('process_type') == 'selfbilling':
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 261
        else:
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 381

    def _bis3_merge_notes_nodes(self, vals):
        nodes = vals['document_node']['cbc:Note']
        notes = []
        for node in nodes:
            notes.append(node['_text'])
        if notes:
            vals['document_node']['cbc:Note'] = [{'_text': ' '.join(notes)}]

    def _ubl_add_notes_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_notes_nodes(vals)
        invoice = vals.get('invoice')

        if invoice:
            terms_and_condition = html2plaintext(invoice.narration) if invoice.narration else None
            if terms_and_condition:
                vals['document_node']['cbc:Note'].append({'_text': terms_and_condition})

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        AccountTax = self.env['account.tax']
        base_lines = vals['base_lines']
        currency = vals['currency']

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            tax_grouping_key = self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
            if not tax_grouping_key:
                return
            return tax_grouping_key['is_withholding']

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        ubl_values = vals['_ubl_values']
        ubl_values['tax_withholding_amount'] = 0.0
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            tax_amount = values['tax_amount_currency']
            ubl_values['tax_withholding_amount'] -= tax_amount

        if currency.is_zero(ubl_values['tax_withholding_amount']):
            return

        nodes = vals['document_node']['cbc:Note']
        nodes.insert(0, {'_text': _(
            "The prepaid amount of %s corresponds to the withholding tax applied.",
            formatLang(self.env, ubl_values['tax_withholding_amount'], currency_obj=vals['currency']).replace(NON_BREAKING_SPACE, ''),
        )})

        # BIS3 allows only one Note.
        self._bis3_merge_notes_nodes(vals)

    def _ubl_add_document_currency_code_node(self, vals):
        # OVERRIDE
        self._ubl_add_document_currency_code_node_foreign_currency(vals)

    def _ubl_add_tax_currency_code_node(self, vals):
        # OVERRIDE
        self._ubl_add_tax_currency_code_node_company_currency_if_foreign_currency(vals)

    def _ubl_add_buyer_reference_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_buyer_reference_node(vals)

        # For B2G transactions in Germany: set the buyer_reference to the Leitweg-ID (code 0204)
        customer = vals['customer']
        if customer.peppol_eas == "0204":
            vals['document_node']['cbc:BuyerReference']['_text'] = customer.peppol_endpoint
        elif customer_ref := customer.commercial_partner_id.ref:
            vals['document_node']['cbc:BuyerReference']['_text'] = customer_ref

    def _ubl_add_order_reference_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_order_reference_node(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        order_ref_node = vals['document_node']['cac:OrderReference']
        order_ref_node['cbc:ID']['_text'] = invoice.ref or invoice.name

        if self.module_installed('sale'):
            so_names = set(invoice.invoice_line_ids.sale_line_ids.order_id.mapped('name'))
            if so_names:
                order_ref_node['cbc:SalesOrderID']['_text'] = ",".join(so_names)

    def _ubl_add_billing_reference_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_billing_reference_nodes(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        nodes = vals['document_node']['cac:BillingReference']
        # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST
        # contain an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
        if (
            vals['supplier'].country_code == 'NL'
            and vals['document_type'] == 'credit_note'
            and invoice.ref
        ):
            nodes.append({
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.ref},
                }
            })

    def _ubl_add_legal_monetary_total_payable_rounding_amount_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_legal_monetary_total_payable_rounding_amount_node(vals)

        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        self._ubl_add_legal_monetary_total_payable_rounding_amount_node_from_cash_rounding(vals)

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_legal_monetary_total_prepaid_payable_amount_node(vals, in_foreign_currency=in_foreign_currency)
        invoice = vals.get('invoice')
        if not invoice:
            return

        currency = vals['currency_id'] if in_foreign_currency else vals['company_currency']
        node = vals['legal_monetary_total_node']

        if in_foreign_currency:
            amount_total = invoice.amount_total
            amount_residual = invoice.amount_residual
        else:
            amount_total = invoice.amount_total_signed * -invoice.direction_sign
            amount_residual = invoice.amount_residual_signed * -invoice.direction_sign

        node['cbc:PayableAmount']['_text'] = FloatFmt(
            amount_residual,
            min_dp=currency.decimal_places,
        )
        node['cbc:PrepaidAmount']['_text'] = FloatFmt(
            amount_total
            - amount_residual
            # WithholdingTaxTotal is not allowed.
            # Instead, withholding tax amounts are reported as a PrepaidAmount.
            # Suppose an invoice of 1000 with a tax 21% +100 -100.
            # The super will compute a PrepaidAmount or 0.0 and a PayableAmount or 1000.
            # This extension is there to increase PrepaidAmount to 210 and PayableAmount to 1210.
            + vals['_ubl_values']['tax_withholding_amount'],
            min_dp=currency.decimal_places,
        )

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # OVERRIDE
        invoice = vals.get('invoice')
        if not invoice:
            return

        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_legal_monetary_total_node(sub_vals)

    def _ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(self, vals, partner_bank):
        # EXTENDS
        node = super()._ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(vals, partner_bank)
        if node:
            node['cbc:ID']['schemeID'] = None
            node['cac:FinancialInstitution'] = None
        return node

    def _ubl_add_payment_means_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_payment_means_nodes(vals)
        nodes = vals['document_node']['cac:PaymentMeans']
        invoice = vals.get('invoice')
        if not invoice:
            return

        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = 30, 'credit transfer'
            else:
                payment_means_code, payment_means_name = 'ZZZ', 'mutually defined'
        else:
            payment_means_code, payment_means_name = 57, 'standing agreement'

        # TODO: This override is probably no longer necessary
        # in Denmark payment code 30 is not allowed. we hardcode it to 1 ("unknown") for now
        # as we cannot deduce this information from the invoice
        customer = vals['customer'].commercial_partner_id
        if customer.country_code == 'DK':
            payment_means_code, payment_means_name = 1, 'unknown'

        partner_bank = invoice.partner_bank_id
        payment_means_node = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
        }

        if partner_bank:
            payment_means_node['cac:PayeeFinancialAccount'] = self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, partner_bank)
        else:
            payment_means_node['cac:PayeeFinancialAccount'] = None

        nodes.append(payment_means_node)

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # OVERRIDE
        invoice = vals.get('invoice')
        if not invoice:
            return

        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_payment_means_nodes(sub_vals)

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_payment_terms_nodes(sub_vals)

        invoice = vals.get('invoice')
        if not invoice:
            return

        nodes = document_node['cac:PaymentTerms']
        nodes.append(self._ubl_get_payment_terms_node_from_payment_term(vals, invoice.invoice_payment_term_id))

    def _add_invoice_header_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_copy_indicator_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        if vals['document_type'] == 'invoice':
            self._ubl_add_due_date_node(sub_vals)
            self._ubl_add_invoice_type_code_node(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_type_code_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_buyer_reference_node(sub_vals)
        self._ubl_add_invoice_period_nodes(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_billing_reference_nodes(sub_vals)

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

    def _add_invoice_line_id_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_id_node(sub_vals)

    def _add_invoice_line_note_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_note_nodes(sub_vals)

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
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
            'base_line': vals['line_vals']['base_line'],
        }

        if vals['document_type'] == 'credit_note':
            self._ubl_add_line_credited_quantity_node(sub_vals)
        else:
            self._ubl_add_line_invoiced_quantity_node(sub_vals)

        self._ubl_add_line_extension_amount_node(sub_vals)

    def _ubl_add_line_period_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl
        super()._ubl_add_line_period_nodes(vals)
        invoice = vals.get('invoice')
        if not invoice:
            return

        base_line = vals['line_vals']['base_line']
        nodes = vals['line_node']['cac:InvoicePeriod']
        if base_line.get('deferred_start_date') or base_line.get('deferred_end_date'):
            nodes.append({
                'cbc:StartDate': {'_text': base_line['deferred_start_date']},
                'cbc:EndDate': {'_text': base_line['deferred_end_date']},
            })

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_period_nodes(sub_vals)

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_tax_totals_nodes(sub_vals)

    def _add_invoice_line_item_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_item_node(sub_vals)

    def _add_invoice_line_pricing_reference_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_pricing_reference_node(sub_vals)

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_price_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_price_node(sub_vals)

    def _line_nodes_filter_base_lines(self, vals, filter_function=None):
        # EXTENDS account.edi.xml.ubl
        # Early payment discount lines should not appear as lines but as allowances/charges.
        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        def new_filter_function(base_line):
            if self._ubl_is_early_payment_base_line(base_line) or self._ubl_is_cash_rounding_base_line(base_line):
                return False
            return not filter_function or filter_function(base_line)

        return super()._line_nodes_filter_base_lines(vals, filter_function=new_filter_function)

    def _ubl_add_invoice_line_node(self, vals):
        # OVERRIDE. For retro-compatibility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _ubl_add_credit_note_line_node(self, vals):
        # OVERRIDE. For retro-compatbility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _add_invoice_line_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        if vals['document_type'] == 'invoice':
            self._ubl_add_invoice_line_nodes(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_line_nodes(sub_vals)

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
        country_code = commercial_partner.country_code
        if country_code == 'BE' and commercial_partner.company_registry:
            nodes.append({
                'cbc:ID': {
                    '_text': be_vat.compact(commercial_partner.company_registry),
                    'schemeID': '0208',
                },
            })
        elif commercial_partner.ref and country_code != 'DK':  # DK-R-013
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
            vat = commercial_partner.vat
            country_code = commercial_partner.country_id.code
            if country_code in GST_COUNTRY_CODES:
                tax_scheme_id = 'GST'
            else:
                tax_scheme_id = 'VAT'

            if country_code == 'HU' and not vat.upper().startswith('HU'):
                vat = 'HU' + vat[:8]

            nodes.append({
                'cbc:CompanyID': {'_text': vat},
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
                    '_text': be_vat.compact(commercial_partner.company_registry),
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

        if commercial_partner.country_code == 'SE':
            nodes.append({
                'cbc:CompanyID': {'_text': "GODKÄND FÖR F-SKATT"},
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
            invoice
            and invoice.invoice_date
            and customer.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
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
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_allowance_charge_nodes(sub_vals)

        invoice = vals.get('invoice')
        if not invoice:
            return

        # Early payment discount lines are treated as allowances/charges.
        self._ubl_add_allowance_charge_nodes_early_payment_discount(sub_vals)

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

        # Percent is not reported in TaxSubtotal
        node['cbc:Percent']['_text'] = None

        return node

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl
        tax_total_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        if tax_total_keys['tax_total_key'] and tax_total_keys['tax_total_key']['is_withholding']:
            tax_total_keys['tax_total_key'] = None

        tax_category_key = tax_total_keys['tax_category_key']
        if (
            tax_category_key
            and tax_category_key['tax_category_code'] == 'E'
            and not tax_category_key.get('tax_exemption_reason')
            ):
            tax_category_key['tax_exemption_reason'] = _("Exempt from tax")
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

        # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
        # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
        # note: Payment account identifier is <cac:PayeeFinancialAccount>
        # note: no need to check account_number, because it's a required field for a partner_bank
        for node in vals['document_node']['cac:PaymentMeans']:
            if node['cbc:PaymentMeansCode']['_text'] in (30, 58):
                constraints['cen_en16931_payment_account_identifier'] = self._check_required_fields(invoice, 'partner_bank_id')

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

        if vals['supplier'].country_id.code == 'BE' and vals['supplier'].company_registry:
            if not be_vat.is_valid(vals['supplier'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_supplier': _('%s should have a valid KBO/BCE number in the Company ID field', vals['supplier'].display_name),
                })

        if vals['customer'].country_id.code == 'BE' and vals['customer'].company_registry:
            if not be_vat.is_valid(vals['customer'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_customer': _('%s should have a valid KBO/BCE number in the Company ID field', vals['customer'].display_name),
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
