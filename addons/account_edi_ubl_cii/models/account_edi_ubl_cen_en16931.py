
from odoo import _, models
from odoo.addons.account.tools import dict_to_xml


class AccountEdiUBLCenEn16931(models.AbstractModel):
    _name = "account.edi.ubl_cen_en16931"
    _inherit = 'account.edi.ubl'
    _description = "UBL CEN-EN16931"

    # -------------------------------------------------------------------------
    # EXPORT: NODES
    # -------------------------------------------------------------------------

    def _ubl_add_line_allowance_charge_nodes(self, vals, in_foreign_currency=True):
        super()._ubl_add_line_allowance_charge_nodes(vals, in_foreign_currency)
        # Allowance/Charge for line discount
        self._ubl_add_line_allowance_charge_nodes_for_discount(vals)

    def _line_nodes_filter_base_lines(self, vals, filter_function=None):
        # Early payment discount lines should not appear as lines but as allowances/charges.
        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        def new_filter_function(base_line):
            if (
                self._ubl_is_early_payment_base_line(base_line)
                or self._ubl_is_global_discount_base_line(base_line)
                or self._ubl_is_cash_rounding_base_line(base_line)
            ):
                return False
            return not filter_function or filter_function(base_line)

        return super()._line_nodes_filter_base_lines(vals, filter_function=new_filter_function)

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        super()._ubl_add_party_tax_scheme_nodes(vals)

        # [BR-O-03]/[BR-O-04]/[BR-O-05] no party tax scheme with "Not subject to VAT" VAT Category Code
        base_lines = vals['base_lines']
        vals['no_party_tax_scheme'] = (
            'ubl_cii_tax_category_code' in self.env['account.tax']._fields
            and any(
                tax_data['tax'].ubl_cii_tax_category_code == 'O'
                for base_line in base_lines
                for tax_data in base_line['tax_details']['taxes_data']
            )
        )

    def _ubl_add_allowance_charge_nodes(self, vals):
        super()._ubl_add_allowance_charge_nodes(vals)

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            # Early payment discount lines are treated as allowances/charges.
            self._ubl_add_allowance_charge_nodes_early_payment_discount(vals)
            # Global discount lines are treated as allowances/charges.
            self._ubl_add_allowance_charge_nodes_global_discount(vals)

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # Recycling contribution taxes / excises should not appear anywhere as taxes but as allowances/charges.
        # Cash rounding lines should not appear as lines but in PayableRoundingAmount.
        # Since this method produces a default 0% tax automatically when no tax is set on the line by default,
        # we have to do something here to avoid it.
        if (
            self._ubl_is_cash_rounding_base_line(base_line)
            or self._ubl_is_allowance_charge_tax(tax_data)
        ):
            return
        return super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        tax_total_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

        # [BR-E-10]-A VAT breakdown (BG-23) with VAT Category code (BT-118) "Exempt from VAT" shall have
        # a VAT exemption reason code (BT-121) or a VAT exemption reason text (BT-120).
        tax_category_key = tax_total_keys['tax_category_key']
        if (
            tax_category_key
            and tax_category_key['tax_category_code'] == 'E'
            and not tax_category_key.get('tax_exemption_reason')
        ):
            tax_category_key['tax_exemption_reason'] = _("Exempt from tax")

        return tax_total_keys

    def _export_document_node_constraints(self, vals):
        constraints = super()._export_document_node_constraints(vals)
        if not self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            return constraints

        document_node = vals['document_node']
        nsmap = document_node['_nsmap']
        invoice = vals['invoice']

        eu_countries = self.env.ref('base.europe').country_ids
        intracom_delivery = (
            vals['customer'].country_id in eu_countries
            and vals['supplier'].country_id in eu_countries
            and vals['customer'].country_id != vals['supplier'].country_id
        )
        if intracom_delivery:
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            if dict_to_xml(document_node['cac:Delivery']['cac:DeliveryLocation'], nsmap=nsmap, tag='cac:DeliveryLocation') is None:
                constraints['cen_en16931_delivery_country_code'] = _("For intracommunity supply, the delivery address should be included.")

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            if (
                dict_to_xml(document_node['cac:Delivery']['cbc:ActualDeliveryDate'], nsmap=nsmap, tag='cbc:ActualDeliveryDate') is None
                and dict_to_xml(document_node['cac:InvoicePeriod'], nsmap=nsmap, tag='cac:InvoicePeriod') is None
            ):
                constraints['cen_en16931_delivery_date_invoicing_period'] = _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")

        # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
        # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
        # note: Payment account identifier is <cac:PayeeFinancialAccount>
        # note: no need to check account_number, because it's a required field for a partner_bank
        for node in document_node['cac:PaymentMeans']:
            if node['cbc:PaymentMeansCode']['_text'] in (30, 58):
                constraints['cen_en16931_payment_account_identifier'] = self._check_required_fields(invoice, 'partner_bank_id')

        line_nodes = []
        for line_key in ('cac:InvoiceLine', 'cac:CreditNoteLine', 'cac:DebitNoteLine'):
            line_nodes.extend(document_node.get(line_key, []))

        # [BR-25]-Each Invoice line (BG-25) shall contain the Item name (BT-153).
        for line_node in line_nodes:
            if not (line_node['cac:Item']['cbc:Name'] or {}).get('_text'):
                constraints['cen_en16931_item_name'] = _("Each invoice line should have a product or a label.")
                break

        tax_category_ids_per_line_node = [
            (
                line_node,
                [
                    tax_category_node.get('cbc:ID', {}).get('_text')
                    for tax_category_node in line_node.get('cac:Item', {}).get('cac:ClassifiedTaxCategory', [])
                ]
            )
            for line_node in line_nodes
        ]

        # [UBL-SR-48]-Invoice lines shall have one and only one classified tax category.
        for line_node, tax_categories in tax_category_ids_per_line_node:
            if len(tax_categories) != 1 or None in tax_categories:
                constraints['cen_en16931_tax_line'] = _("Each invoice line shall have one and only one tax.")

        # [BR-O-02] and other [BR-XX-02] contradict each other.
        # taxes of category 'O' should not be mixed with other.
        has_service_outside_scope_of_tax = False
        has_only_service_outside_scope_of_tax = True
        for line_node, tax_categories in tax_category_ids_per_line_node:
            if 'O' in tax_categories:
                has_service_outside_scope_of_tax = True
            if set(tax_categories) != {'O'}:
                has_only_service_outside_scope_of_tax = False
        if has_service_outside_scope_of_tax and not has_only_service_outside_scope_of_tax:
            constraints['cen_en16931_tax_category_o'] = _("Taxes of category 'Service outside scope of tax' shall not be mixed with tax from other categories. You should split your invoice in two")

        for party_node, role in (
            (document_node['cac:AccountingSupplierParty'], 'supplier'),
            (document_node['cac:AccountingCustomerParty'], 'customer'),
        ):
            # [BR-09] Seller postal address must contain Seller country code (BT-40).
            # [BR-11] Buyer postal address must contain Buyer country code (BT-55).
            if dict_to_xml(party_node['cac:Party']['cac:PostalAddress']['cac:Country']['cbc:IdentificationCode'], nsmap=nsmap, tag='cbc:IdentificationCode') is None:
                constraints[f'cen_en16931_{role}_country'] = _("The country is required for the %s.", role)

            # [BR-CO-09]-The Seller VAT identifier (BT-31), the Seller tax representative VAT identifier (BT-63)
            # and the Buyer VAT identifier (BT-48) shall have a prefix in accordance with ISO code ISO 3166-1
            # alpha-2 by which the country of issue may be identified. Nevertheless, Greece may use the prefix 'EL'.
            for tax_scheme_node in party_node['cac:Party']['cac:PartyTaxScheme']:
                if (
                    tax_scheme_node['cac:TaxScheme']['cbc:ID']['_text'] == 'VAT'
                    and not tax_scheme_node['cbc:CompanyID']['_text'][:2].isalpha()
                ):
                    constraints[f'cen_en16931_{role}_vat_country_code'] = _("The VAT of the %s should be prefixed with its country code.", role)

        # [BR-57]-Each Deliver to address (BG-15) shall contain a Deliver to country code (BT-80).
        if (
            document_node['cac:Delivery']
            and dict_to_xml(document_node['cac:Delivery']['cac:DeliveryLocation']['cac:Address']['cac:Country']['cbc:IdentificationCode'], nsmap=nsmap, tag='cbc:IdentificationCode') is None
        ):
            constraints['cen_en16931_delivery_address'] = self._check_required_fields(invoice.partner_shipping_id, 'country_id')

        if self.env.context.get('from_peppol'):
            # [PEPPOL-EN16931-R010]
            if not vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cbc:EndpointID']['_text']:
                constraints['ubl_peppol_en16931-r010'] = _(
                    "[PEPPOL-EN16931-R010] An electronic address (EAS) must be provided on the customer '%s'.",
                    vals['customer'].display_name,
                )

            # [PEPPOL-EN16931-R020]
            if not vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cbc:EndpointID']['_text']:
                constraints['ubl_peppol_en16931-r020'] = _(
                    "[PEPPOL-EN16931-R020] An electronic address (EAS) must be provided on the company '%s'.",
                    vals['supplier'].display_name,
                )

        return constraints

    def _init_invoice_export_values(self, invoice):
        vals = super()._init_invoice_export_values(invoice)

        # [BR-27]-The Item net price (BT-146) shall NOT be negative.
        self._ubl_turn_base_lines_price_unit_as_always_positive(vals)

        return vals
