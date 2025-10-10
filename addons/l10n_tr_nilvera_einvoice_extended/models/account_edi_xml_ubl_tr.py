from collections import defaultdict
from lxml import etree

from odoo import api, models
from odoo.addons.l10n_tr_nilvera_einvoice_extended.tools import clean_node_dict, TrInvoice
from odoo.tools import float_compare, frozendict


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = "account.edi.xml.ubl.tr"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    def _get_invoice_node(self, vals):
        """Generate and clean the invoice XML node dictionary.

        Extends the base invoice node by adding buyer/customer party nodes
        and removing child nodes not defined in the template while keeping UBL attributes.

        :param vals: dict with invoice data.
        :return: cleaned invoice node dict for XML rendering.
        """
        document_node = super()._get_invoice_node(vals)
        self._add_invoice_buyer_customer_party_nodes(document_node, vals)
        return clean_node_dict(document_node, self._get_document_template({'document_node': document_node, 'document_type': 'invoice'}))

    def _add_invoice_header_nodes(self, document_node, vals):
        """Extend the invoice header node generation with Turkish-specific fields.

        The Extended flow is only applied for outgoing invoices (out_invoice). This method customizes
        the standard invoice XML header for Turkish e-Invoicing (UBL) by adding localized fields and
        structure required by GIB.

        :param document_node: dict
        :param vals: dict
        :return: None
        """
        super()._add_invoice_header_nodes(document_node, vals)
        # The Nilvera Extended flow is only for out_invoice type
        if vals['document_type'] != 'invoice':
            return
        invoice = vals['invoice']
        document_node.update({
            'cbc:ProfileID': {'_text': self._get_tr_profile_id(invoice)},
            'cbc:InvoiceTypeCode': {'_text': 'ISTISNA' if invoice.l10n_tr_is_export_invoice else invoice.l10n_tr_gib_invoice_type},
        })

    @api.model
    def _add_invoice_buyer_customer_party_nodes(self, document_node, vals):
        """Adds BuyerCustomerParty node for TR E-Invoicing.

        For export invoices, a buyer party node is created based on the customer,
        and the PartyIdentification values are updated to indicate an export customer.

        :param document_node: dict representing the invoice XML structure to modify.
        :param vals: dict containing invoice-related values, including 'invoice'.
        """
        if vals['invoice'].l10n_tr_is_export_invoice:
            buyer_party_node = self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'buyer'})
            buyer_party_node['cac:PartyIdentification'] = [{'cbc:ID': {
                '_text': 'EXPORT',
                'schemeID': 'PARTYTYPE',
                },
            }]
            document_node['cac:BuyerCustomerParty'] = {'cac:Party': buyer_party_node}

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        """Extend invoice accounting customer party nodes for TR E-Invoicing.

        For export invoice, the AccountingCustomerParty is set to the static
        Turkish Ministry of Customs and Trade node.

        :param document_node: dict representing the invoice XML structure to modify.
        :param vals: dict containing invoice-related values, including 'invoice'.
        """
        super()._add_invoice_accounting_customer_party_nodes(document_node, vals)
        if vals['invoice'].l10n_tr_is_export_invoice:
            document_node['cac:AccountingCustomerParty'] = {'cac:Party': self._get_ministry_party_node()}

    @api.model
    def _get_ministry_party_node(self):
        """Return the fixed ministry (party) information required for TR E-invoicing.

        This method provides identification, address, tax, and naming
        details of the Turkish Ministry of Customs and Trade.

        :return: dict containing ministry party node.
        """
        return {
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': '1460415308',
                    'schemeID': 'VKN',
                },
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': 'Gümrük ve Ticaret Bakanlığı Gümrükler Genel Müdürlüğü- Bilgi İşlem Dairesi Başkanlığı'},
            },
            'cac:PostalAddress': {
                'cbc:CitySubdivisionName': {'_text': 'Ulus'},
                'cbc:CityName': {'_text': 'Ankara'},
                'cac:Country': {'cbc:Name': {'_text': 'Türkiye'}},
            },
            'cac:PartyTaxScheme': {
                'cac:TaxScheme': {'cbc:Name': {'_text': 'Ulus'}},
            },
        }

    @api.model
    def _get_tr_profile_id(self, invoice):
        """Determine the TR profile ID for the given invoice.

        Logic:
        - If the customer is an e-invoice user and the invoice has a
          l10n_tr_gib_invoice_scenario, return that scenario.
        - If the invoice is marked as an export invoice, return "IHRACAT".
        - Otherwise:
            • Return "TEMELFATURA" if the customer is an e-invoice user.
            • Return "EARSIVFATURA" for e-archive invoices.

        :param invoice: account.move record (the invoice).
        :return: str, TR profile ID to be used in E-invoicing.
        """
        if (is_einvoice := invoice.l10n_tr_nilvera_customer_status == 'einvoice') and invoice.l10n_tr_gib_invoice_scenario:
            return invoice.l10n_tr_gib_invoice_scenario
        if invoice.l10n_tr_is_export_invoice:
            return 'IHRACAT'
        return 'TEMELFATURA' if is_einvoice else 'EARSIVFATURA'

    def _get_document_template(self, vals):
        if vals['document_node']['cbc:CustomizationID']['_text'] == 'TR1.2' and vals['document_type'] == 'invoice':
            return TrInvoice
        return super()._get_document_template(vals)

    def _get_party_node(self, vals):
        """Extend the party node getter with the Turkish tax office name.

        Adds the tax office name if the partner has a Turkish
        tax office set to the partner's PartyTaxScheme.

        :param vals: dict containing invoice-related values.
        :return: dict representing the updated party node.
        """
        partner = vals['partner']
        party_node = super()._get_party_node(vals)
        if tax_office := partner.l10n_tr_tax_office_id:
            party_node['cac:PartyTaxScheme']['cac:TaxScheme']['cbc:Name']['_text'] = tax_office.name
        return party_node

    def _get_invoice_line_node(self, vals):
        """Generate the invoice line XML node dictionary.

        Extends the base line node by adding delivery-specific nodes.
        Uses context to skip TR reason code processing.

        :param vals: dict with invoice line data.
        :return: invoice line node dict ready for XML rendering.
        """
        line_node = super(AccountEdiXmlUblTr, self.with_context(skip_tr_reason_code=True))._get_invoice_line_node(vals)
        self._add_invoice_line_delivery_nodes(line_node, vals)
        return line_node

    def _add_invoice_line_delivery_nodes(self, line_node, vals):
        """Add delivery information to an invoice line node for export invoices.

        For export invoice, it builds the cac:Delivery section of the
        UBL TR XML for invoice lines. The delivery node includes
        address, incoterms, shipment, and customs-related details.

        :param line_node: dict representing the invoice line XML structure to update.
        :param vals: dict containing invoice line data.
        """
        move_line = vals['base_line']['record']
        if move_line.move_id.l10n_tr_is_export_invoice:
            line_node['cac:Delivery'] = {
                'cac:DeliveryAddress': {
                    'cbc:StreetName': {'_text': move_line.move_id.partner_id.street},
                    'cbc:CitySubdivisionName': {'_text': move_line.move_id.partner_id.city},
                    'cbc:CityName': {'_text': move_line.move_id.partner_id.state_id.with_context(lang='tr_TR').name},
                    'cbc:PostalZone': {'_text': move_line.move_id.partner_id.zip},
                    'cac:Country': {'cbc:Name': {'_text': move_line.move_id.partner_id.country_id.with_context(lang='tr_TR').name}},
                },
                'cac:DeliveryTerms': {
                    'cbc:ID': {'_text': move_line.move_id.invoice_incoterm_id.code, 'schemeID': 'INCOTERMS'},
                },
                'cac:Shipment': {
                    'cbc:ID': {'_text': 'NO_ID'},
                    'cac:GoodsItem': {'cbc:RequiredCustomsID': {'_text': move_line.l10n_tr_ctsp_number or move_line.product_id.l10n_tr_ctsp_number}},
                    'cac:ShipmentStage': {'cbc:TransportModeCode': {'_text': move_line.move_id.l10n_tr_shipping_type}},
                },
            }

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        if vals['invoice'].l10n_tr_gib_invoice_type == "TEVKIFAT":
            return self._add_withholding_document_line_tax_total_nodes(line_node, vals)
        return super()._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        if vals['invoice'].l10n_tr_gib_invoice_type == "TEVKIFAT":
            return self._add_withholding_document_tax_total_nodes(document_node, vals)
        return super()._add_document_tax_total_nodes(document_node, vals)

    def _add_withholding_document_tax_total_nodes(self, line_node, vals):
        def grouping_function(base_line, tax_data):
            grouping_key = vals['tax_grouping_function'](base_line, tax_data)
            invoice = base_line["record"].move_id
            tax = tax_data["tax"]
            grouping_key["l10n_tr_tax_withheld"] = tax.l10n_tr_tax_withholding_code_id.id
            if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT" and tax.l10n_tr_tax_withholding_code_id:
                grouping_key["percent_withheld"] = int(tax.l10n_tr_tax_withholding_code_id.percentage * 100)
                grouping_key["name"] = tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name
                grouping_key["tax_type_code"] = tax.l10n_tr_tax_withholding_code_id.code
            return grouping_key

        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)

        for base_line, aggregated_values in base_lines_aggregated_tax_details:
            for grouping_key in aggregated_values:
                taxes_data = base_line.get("tax_details", {}).get("taxes_data", [])
                rounding = base_line.get("record").currency_id.rounding

                # Sum of positive tax amounts (with rounding check)
                total_taxed_amount = sum(
                    tax_line["tax_amount"]
                    for tax_line in taxes_data
                    if float_compare(tax_line["tax_amount"], 0, precision_rounding=rounding) > 0
                )

                # Sum of all tax amounts
                total_residual_amount = sum(tax_line["tax_amount"] for tax_line in taxes_data)

                # Update values_per_grouping_key
                group_vals = aggregated_tax_details[grouping_key]
                group_vals["tr_total_taxed_amount"] = group_vals.get("tr_total_taxed_amount", 0.0) + total_taxed_amount
                group_vals["tr_total_taxed_residual_amount"] = group_vals.get("tr_total_taxed_residual_amount", 0.0) + total_residual_amount

        aggregated_tax_details_by_l10n_tr_tax_withholding_code_id = {'tax': defaultdict(dict), 'withholding_tax': defaultdict(dict)}

        for grouping_key, values in aggregated_tax_details.items():
            if grouping_key:
                key = 'withholding_tax' if (l10n_tr_tax_withheld := grouping_key['l10n_tr_tax_withheld']) else 'tax'
                aggregated_tax_details_by_l10n_tr_tax_withholding_code_id[key][l10n_tr_tax_withheld][grouping_key] = values

        line_node['cac:TaxTotal'] = [
            self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line'})
            for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['tax'].values()
        ]
        if vals['document_type'] == 'invoice':
            line_node['cac:WithholdingTaxTotal'] = [
                self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line', 'withholding': True, 'sign': -1})
                for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['withholding_tax'].values()
            ]

    def _add_withholding_document_line_tax_total_nodes(self, line_node, vals):
        """Extends the aggregation of line tax details to include Turkish (TR) withholding-specific amounts.

        Adds two fields per grouping key:
            - tr_total_taxed_amount: The total tax amount used in the withholding tax line.
            - tr_total_taxed_residual_amount: The total tax amount after withholding, shown in the tax line.

            If there is a 20% tax and 18% is withheld on ₺10:
                - tr_total_taxed_amount = ₺2
                - tr_total_taxed_residual_amount = ₺0.2

        :param base_line: The invoice line with tax details.
        :param grouping_function: Function to determine how tax lines are grouped.
        :return: Dictionary of aggregated values per grouping key, including TR withholding amounts.

        """
        def grouping_function(base_line, tax_data):
            grouping_key = vals['tax_grouping_function'](base_line, tax_data)
            invoice = base_line["record"].move_id
            tax = tax_data["tax"]
            grouping_key["l10n_tr_tax_withheld"] = tax.l10n_tr_tax_withholding_code_id.id
            if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT" and tax.l10n_tr_tax_withholding_code_id:
                grouping_key["percent_withheld"] = int(tax.l10n_tr_tax_withholding_code_id.percentage * 100)
                grouping_key["name"] = tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name
                grouping_key["tax_type_code"] = tax.l10n_tr_tax_withholding_code_id.code
            return grouping_key

        encountered_groups = set()
        base_line = vals['base_line']
        tax_details = base_line["tax_details"]
        taxes_data = tax_details["taxes_data"]
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, grouping_function)

        for tax_data in taxes_data:
            grouping_key = grouping_function(vals['base_line'], tax_data)
            if isinstance(grouping_key, dict):
                grouping_key = frozendict(grouping_key)
            already_accounted = grouping_key in encountered_groups
            encountered_groups.add(grouping_key)
            if not already_accounted:
                taxes_data = base_line.get("tax_details", {}).get("taxes_data", [])
                rounding = base_line.get("record").currency_id.rounding

                total_taxed_amount = sum(tax_line["tax_amount"] for tax_line in taxes_data if float_compare(tax_line["tax_amount"], 0, precision_rounding=rounding) > 0)
                total_residual_amount = sum(tax_line["tax_amount"] for tax_line in taxes_data)

                group_vals = aggregated_tax_details[grouping_key]
                group_vals["tr_total_taxed_amount"] = group_vals.get("tr_total_taxed_amount", 0.0) + total_taxed_amount
                group_vals["tr_total_taxed_residual_amount"] = group_vals.get("tr_total_taxed_residual_amount", 0.0) + total_residual_amount

        aggregated_tax_details_by_l10n_tr_tax_withholding_code_id = {'tax': defaultdict(dict), 'withholding_tax': defaultdict(dict)}

        for grouping_key, values in aggregated_tax_details.items():
            if grouping_key:
                key = 'withholding_tax' if (l10n_tr_tax_withheld := grouping_key['l10n_tr_tax_withheld']) else 'tax'
                aggregated_tax_details_by_l10n_tr_tax_withholding_code_id[key][l10n_tr_tax_withheld][grouping_key] = values

        line_node['cac:TaxTotal'] = [
            self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line'})
            for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['tax'].values()
        ]
        if vals['document_type'] == 'invoice':
            line_node['cac:WithholdingTaxTotal'] = [
                self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line', 'withholding': True, 'sign': -1})
                for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['withholding_tax'].values()
            ]

    @api.model
    def _get_withholding_tax_total_node(self, vals):
        """Build the TaxTotal node for withholding taxes in TR E-Invoicing.

        This method calculates total and subtotal withholding tax amounts.

        :param vals: dict containing tax details, currency info, and related data.
        :return: dict representing the withholding tax total node.
        """
        aggregated_tax_details = vals['aggregated_tax_details']
        currency_suffix = vals['currency_suffix']
        currency_name = vals['currency_name']
        precision = vals['currency_dp']
        sign = vals.get('sign', 1)
        is_withholding = vals.get('withholding', False)

        def get_tax_amount_total():
            """Compute total tax amount depending on whether it is withholding."""
            if is_withholding:
                return sum(
                    details[f'tax_amount{currency_suffix}']
                    for grouping_key, details in aggregated_tax_details.items()
                    if grouping_key
                )
            return sum(
                values['tr_total_taxed_residual_amount']
                for grouping_key, values in aggregated_tax_details.items()
                if grouping_key
            )

        def get_total_tax_subtotal_amount(details):
            """Compute the total taxable amount depending on whether it is withholding."""
            if is_withholding:
                return details['tr_total_taxed_amount']
            return details.get(f'base_amount{currency_suffix}', 0)

        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * get_tax_amount_total(), precision),
                'currencyID': currency_name,
            },
            'cac:TaxSubtotal': [
                {
                    'cbc:TaxableAmount': {
                        '_text': self.format_float(get_total_tax_subtotal_amount(details), precision),
                        'currencyID': currency_name,
                    },
                    'cbc:TaxAmount': {
                        '_text': self.format_float(sign * details[f'tax_amount{currency_suffix}'], precision),
                        'currencyID': currency_name,
                    },
                    'cbc:Percent': {
                        # The percentatge can't be a float as it is expected to return as an integer
                        '_text': grouping_key['percent_withheld'] if is_withholding else False,
                    },
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key}),
                }
                for grouping_key, details in aggregated_tax_details.items()
                if grouping_key
            ],
        }

    def _get_tax_category_node(self, vals):
        grouping_key = vals['grouping_key']
        if grouping_key.get('l10n_tr_tax_withheld'):
            return {
                'cac:TaxScheme': {
                    'cbc:Name': {'_text': grouping_key["name"]},
                    'cbc:TaxTypeCode': {'_text': grouping_key["tax_type_code"]},
                },
            }
        tax_totals_vals = super()._get_tax_category_node(vals)
        tax_invoice_exemption = vals['invoice'].l10n_tr_exemption_code_id
        if self.env.context.get("skip_tr_reason_code") or not tax_invoice_exemption:
            return tax_totals_vals

        tax_totals_vals.update({
            'cbc:TaxExemptionReasonCode': {'_text': tax_invoice_exemption.code},
            'cbc:TaxExemptionReason': {'_text': tax_invoice_exemption.with_context(lang="tr_TR").name},
        })
        return tax_totals_vals

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the TR UBL version, we always want the Shipment with ID empty node, due to it being required.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        shipment_id_elements = xml_root.findall(".//cac:Shipment/cbc:ID", namespaces=xml_root.nsmap)
        for element in shipment_id_elements:
            if element.text == "NO_ID":
                element.text = ""
        return etree.tostring(xml_root, xml_declaration=True, encoding="UTF-8"), errors
