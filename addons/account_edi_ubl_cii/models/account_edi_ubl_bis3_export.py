from odoo import _, api, models
from odoo.tools import frozendict, html2plaintext
from odoo.tools.misc import formatLang, NON_BREAKING_SPACE

from lxml import etree

CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiUBLBis3(models.AbstractModel):
    _name = "account.edi.ubl.bis3"
    _inherit = 'account.edi.ubl'
    _description = "Base helpers for UBL Invoice BIS3"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _ubl_add_values_customer(self, vals, customer):
        # EXTENDS
        super()._ubl_add_values_customer(vals, customer)
        customer = vals['customer']['commercial_partner']
        vals['customer']['is_behind_chorus_pro'] = (
            customer.peppol_eas
            and customer.peppol_endpoint
            and f"{customer.peppol_eas}:{customer.peppol_endpoint}" == CHORUS_PRO_PEPPOL_ID
        )

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

    # -------------------------------------------------------------------------
    # EXPORT: Building nodes
    # -------------------------------------------------------------------------

    def _bis3_merge_notes_nodes(self, vals):
        nodes = vals['document_node']['cbc:Note']
        notes = []
        for node in nodes:
            notes.append(node['_text'])
        if notes:
            vals['document_node']['cbc:Note'] = [{'_text': ' '.join(notes)}]

    def _ubl_add_notes_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_notes_nodes(vals)

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
        vals['tax_withholding_amount'] = 0.0
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            tax_amount = values['tax_amount_currency']
            vals['tax_withholding_amount'] -= tax_amount

        if currency.is_zero(vals['tax_withholding_amount']):
            return

        nodes = vals['document_node']['cbc:Note']
        nodes.insert(0, {'_text': _(
            "The prepaid amount of %s corresponds to the withholding tax applied.",
            formatLang(self.env, vals['tax_withholding_amount'], currency_obj=vals['currency']).replace(NON_BREAKING_SPACE, ''),
        )})

        # BIS3 allows only one Note.
        self._bis3_merge_notes_nodes(vals)

    def _ubl_add_line_allowance_charge_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_line_allowance_charge_nodes(vals)

        # Discount.
        self._ubl_add_line_allowance_charge_nodes_for_discount(vals)

        # Recycling contribution taxes.
        self._ubl_add_line_allowance_charge_nodes_for_recycling_contribution_taxes(vals)

        # Excise taxes.
        self._ubl_add_line_allowance_charge_nodes_for_excise_taxes(vals)

    def _ubl_line_nodes_filter_base_lines(self, vals, filter_function=None):
        # EXTENDS
        # Early payment discount lines should not appear as lines but as allowances/charges.
        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        def new_filter_function(base_line):
            if self._ubl_is_early_payment_base_line(base_line) or self._ubl_is_cash_rounding_base_line(base_line):
                return False
            return not filter_function or filter_function(base_line)

        return super()._ubl_line_nodes_filter_base_lines(vals, filter_function=new_filter_function)

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS
        super()._ubl_add_customization_id_node(vals)
        vals['document_node']['cbc:CustomizationID']['_text'] = 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'

    def _ubl_add_profile_id_node(self, vals):
        # EXTENDS
        super()._ubl_add_profile_id_node(vals)
        vals['document_node']['cbc:ProfileID']['_text'] = 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'

    def _ubl_get_partner_address_node(self, vals, partner):
        # EXTENDS
        node = super()._ubl_get_partner_address_node(vals, partner)
        node['cbc:CountrySubentityCode'] = None
        node['cac:Country']['cbc:Name'] = None
        return node

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS
        super()._ubl_add_party_endpoint_id_node(vals)
        commercial_partner = vals['party_vals']['commercial_partner']
        vals['party_node']['cbc:EndpointID']['_text'] = commercial_partner.peppol_endpoint
        vals['party_node']['cbc:EndpointID']['schemeID'] = commercial_partner.peppol_eas

    def _ubl_add_party_identification_nodes(self, vals):
        # EXTENDS
        # TODO: add deep tests about that part
        super()._ubl_add_party_identification_nodes(vals)
        nodes = vals['party_node']['cac:PartyIdentification']

        commercial_partner = vals['party_vals']['commercial_partner']
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
        # EXTENDS
        # TODO: add deep tests about that part
        super()._ubl_add_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']

        commercial_partner = vals['party_vals']['commercial_partner']
        if commercial_partner.vat:
            # TaxScheme based on partner's VAT.
            # [BR-CO-09] if the PartyTaxScheme/TaxScheme/ID == 'VAT', CompanyID must start with a country code prefix.
            # In some countries however, the CompanyID can be with or without country code prefix and still be perfectly
            # valid (RO, HU, non-EU countries).
            # We have to handle their cases by changing the TaxScheme/ID to 'something other than VAT',
            # preventing the trigger of the rule.
            if commercial_partner.country_id and not commercial_partner.vat[:2].isalpha():
                tax_scheme_id = 'NOT_EU_VAT'
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
        # EXTENDS
        # TODO: add deep tests about that part
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        commercial_partner = vals['party_vals']['commercial_partner']

        if commercial_partner.country_code == 'NL':
            # For NL, VAT can be used as a Peppol endpoint, but KVK/OIN has to be used as PartyLegalEntity/CompanyID
            # To implement a workaround on stable, company_registry field is used without recording whether
            # the number is a KVK or OIN, and the length of the number (8 = KVK, 9 = OIN) is used to determine the type
            nl_id = commercial_partner.company_registry if commercial_partner.peppol_eas not in ('0106', '0190') else commercial_partner.peppol_endpoint
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': nl_id,
                    'schemeID': '0190' if nl_id and len(nl_id) == 20 else '0106',
                },
            })
        elif commercial_partner.country_code == 'LU' and commercial_partner.company_registry:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.company_registry,
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
                    'schemeID': commercial_partner.peppol_eas,
                },
            })
        elif commercial_partner.vat:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
            })
        elif commercial_partner.peppol_eas and commercial_partner.peppol_endpoint:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.peppol_endpoint,
                    'schemeID': commercial_partner.peppol_eas,
                },
            })

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        commercial_partner = vals['party_vals']['commercial_partner']

        if commercial_partner.country_code == 'NO':
            nodes.append({
                'cbc:CompanyID': {'_text': "Foretaksregisteret"},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': "TAX"},
                },
            })

    def _ubl_get_delivery_node_from_delivery_address(self, vals):
        # EXTENDS
        node = super()._ubl_get_delivery_node_from_delivery_address(vals)

        # Intracom delivery inside European area.
        invoice = vals['invoice']
        customer = vals['customer']['partner']
        supplier = vals['supplier']['partner']
        # TODO: missing countries in economic_area + what if the country of partner is not set but on commercial_partner
        # TODO add a dedicated test for that part
        economic_area = self.env.ref('base.europe').country_ids.mapped('code') + ['NO']
        if (
            customer.country_id.code in economic_area
            and supplier.country_id.code in economic_area
            and supplier.country_id != customer.country_id
        ):
            node['cbc:ActualDeliveryDate']['_text'] = invoice.invoice_date
        return node

    def _ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(self, vals, partner_bank_vals):
        # EXTENDS
        node = super()._ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(vals, partner_bank_vals)
        if node:
            node['cbc:ID']['schemeID'] = None
            node['cac:FinancialInstitution'] = None
        return node

    def _ubl_add_allowance_charge_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_allowance_charge_nodes(vals)

        # Early payment discount lines are treated as allowances/charges.
        self._ubl_add_allowance_charge_nodes_early_payment_discount(vals)

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS
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

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        # EXTENDS
        super()._ubl_add_legal_monetary_total_prepaid_payable_amount_node(vals, in_foreign_currency=in_foreign_currency)

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        # Suppose an invoice of 1000 with a tax 21% +100 -100.
        # The super will compute a PrepaidAmount or 0.0 and a PayableAmount or 1000.
        # This extension is there to increase PrepaidAmount to 210 and PayableAmount to 1210.
        node = vals['legal_monetary_total_node']
        node['cbc:PrepaidAmount']['_text'] += vals['tax_withholding_amount']

    def _ubl_add_legal_monetary_total_payable_rounding_amount_node(self, vals):
        # EXTENDS
        super()._ubl_add_legal_monetary_total_payable_rounding_amount_node(vals)

        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        self._ubl_add_legal_monetary_total_payable_rounding_amount_node_from_cash_rounding(vals)
