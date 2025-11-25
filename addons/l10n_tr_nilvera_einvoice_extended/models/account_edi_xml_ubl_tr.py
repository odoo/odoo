from collections import defaultdict

from lxml import etree

from odoo import Command, _, api, models
from odoo.tools import float_compare, frozendict
from odoo.tools.misc import clean_context

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.l10n_tr_nilvera_einvoice_extended.tools.clean_node_dict import (
    clean_node_dict,
)
from odoo.addons.l10n_tr_nilvera_einvoice_extended.tools.ubl_tr_invoice import TrInvoice


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

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        """Extend invoice monetary total nodes for TR E-Invoicing.

        For invoices registered as Export, the payable amount is set to the total amount
        without tax, as required by Turkish e-invoicing regulations.

        :param document_node: dict representing the invoice XML structure to modify.
        :param vals: dict containing invoice-related values, including 'invoice'.
        """
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        if vals['invoice'].l10n_tr_gib_invoice_type == "IHRACKAYITLI":
            document_node["cac:LegalMonetaryTotal"]["cbc:PayableAmount"]["_text"] = (
                document_node["cac:LegalMonetaryTotal"]["cbc:TaxExclusiveAmount"]["_text"]
            )

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
        """Determines the document template to use based on the provided values.

        If the document is a Turkish invoice (CustomizationID 'TR1.2' and document_type 'invoice'),
        it returns the `TrInvoice` template. Otherwise, it falls back to the default implementation.

        :param vals: Dictionary containing document data, including 'document_node' and 'document_type'.
        :return: Document template class to be used for generating the document.
        """
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
        """Adds tax total nodes to a document line.

        For Turkish withholding invoices TEVKIFAT, this method
        delegates to add_withholding_document_line_tax_total_nodes.
        Otherwise, it falls back to the default behavior.

        :param line_node: XML node representing the invoice line.
        :param vals: Dictionary containing the invoice data.
        :return: Updated XML line node with tax total information.
        """
        if vals['invoice'].l10n_tr_gib_invoice_type == 'TEVKIFAT':
            return self._add_withholding_document_line_tax_total_nodes(line_node, vals)
        return super()._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        """Adds tax total nodes to the invoice document.

        For Turkish withholding invoices ('TEVKIFAT'), this method
        delegates to `_add_withholding_document_tax_total_nodes`.
        Otherwise, it uses the default tax total behavior.

        :param document_node: XML node representing the full invoice document.
        :param vals: Dictionary containing the invoice data.
        :return: lxml.etree.Element or similar XML node representing the updated invoice document.

        """
        if vals['invoice'].l10n_tr_gib_invoice_type == 'TEVKIFAT':
            return self._add_withholding_document_tax_total_nodes(document_node, vals)
        return super()._add_document_tax_total_nodes(document_node, vals)

    def _add_withholding_document_tax_total_nodes(self, line_node, vals):
        """Extends the aggregation of tax details to include Turkish (TR) withholding-specific amounts
        for an invoice line.

        This method performs the following:
            - Aggregates tax details across all base lines.
            - Adds two fields per grouping key:
                - tr_total_taxed_amount: Total tax amount used in the withholding tax line.
                - tr_total_taxed_residual_amount: Total tax amount after withholding, shown in the tax line.
            - Splits aggregated tax details into normal taxes and withholding taxes.
            - Updates `line_node` with:
                - 'cac:TaxTotal' for normal taxes
                - 'cac:WithholdingTaxTotal' for withholding taxes (if the document is an invoice)

        If there is a 20% tax and 18% is withheld on ₺10:
            - tr_total_taxed_amount = ₺2
            - tr_total_taxed_residual_amount = ₺0.2

        :param line_node: XML node representing the invoice line to be updated.
        :param vals: Dictionary containing invoice data and base lines.
        """
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], self.tax_grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)

        for base_line, aggregated_values in base_lines_aggregated_tax_details:
            for grouping_key in aggregated_values:
                taxes_data = base_line.get('tax_details', {}).get('taxes_data', [])
                rounding = base_line.get('record').currency_id.rounding

                # Sum of positive tax amounts (with rounding check)
                total_taxed_amount = sum(
                    tax_line['tax_amount']
                    for tax_line in taxes_data
                    if float_compare(tax_line['tax_amount'], 0, precision_rounding=rounding) > 0
                )

                # Sum of all tax amounts
                total_residual_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data)

                # Update values_per_grouping_key
                group_vals = aggregated_tax_details[grouping_key]
                group_vals['tr_total_taxed_amount'] = group_vals.get('tr_total_taxed_amount', 0.0) + total_taxed_amount
                group_vals['tr_total_taxed_residual_amount'] = group_vals.get('tr_total_taxed_residual_amount', 0.0) + total_residual_amount

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
    def tax_grouping_function(self, base_line, tax_data):
        """Build a grouping key for tax aggregation, extended for Turkish (TR) withholding taxes.

        This method extends the default tax grouping logic to include TR-specific
        withholding details. It constructs a grouping key for each tax line and
        appends withholding-related fields when applicable.

        Specifically, for invoices of type TEVKIFAT with a withholding tax code,
        the following fields are added to the grouping key:
            - l10n_tr_tax_withheld: The ID of the withholding tax code.
            - percent_withheld: The percentage of tax to be withheld (as an integer).
            - name: The localized name of the withholding tax (in Turkish).
            - tax_type_code: The code of the withholding tax.

        :param dict base_line: The base invoice line containing the record and tax details.
        :param dict tax_data: The dictionary containing the tax and its computed values.
        :return: The grouping key dictionary for this tax line, including TR withholding details if applicable.
        """
        invoice = base_line["record"].move_id
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id
        tax = tax_data["tax"]

        grouping_key = {
            "tax_category_code": self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
            **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
            "amount": tax.amount if tax else 0.0,
            "amount_type": tax.amount_type if tax else "percent",
            "l10n_tr_tax_withheld": tax.l10n_tr_tax_withholding_code_id.id,
        }

        if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT" and tax.l10n_tr_tax_withholding_code_id:
            withholding_code = tax.l10n_tr_tax_withholding_code_id
            grouping_key.update(
                {
                    "percent_withheld": int(withholding_code.percentage * 100),
                    "name": withholding_code.with_context(lang="tr_TR").name,
                    "tax_type_code": withholding_code.code,
                },
            )

        return grouping_key

    def _add_withholding_document_line_tax_total_nodes(self, line_node, vals):
        """Extend aggregation of line tax details to include Turkish (TR) withholding-specific amounts.

        For each tax grouping key, this method adds two fields:
            - tr_total_taxed_amount: The total tax amount applied to the line before withholding.
            - tr_total_taxed_residual_amount: The remaining tax amount after withholding.

        If there is a 20% tax and 18% is withheld on ₺10:
            - tr_total_taxed_amount = ₺2
            - tr_total_taxed_residual_amount = ₺0.2

        :param line_node: The invoice line node containing tax details.
        :param vals: Tax values used to compute withholding amounts.
        """
        encountered_groups = set()
        base_line = vals['base_line']
        tax_details = base_line['tax_details']
        taxes_data = tax_details['taxes_data']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, self.tax_grouping_function)

        for tax_data in taxes_data:
            grouping_key = self.tax_grouping_function(base_line, tax_data)
            if isinstance(grouping_key, dict):
                grouping_key = frozendict(grouping_key)
            already_accounted = grouping_key in encountered_groups
            encountered_groups.add(grouping_key)
            if not already_accounted:
                taxes_data = base_line.get('tax_details', {}).get('taxes_data', [])
                rounding = base_line.get('record').currency_id.rounding

                total_taxed_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data if float_compare(tax_line['tax_amount'], 0, precision_rounding=rounding) > 0)
                total_residual_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data)

                group_vals = aggregated_tax_details[grouping_key]
                group_vals['tr_total_taxed_amount'] = group_vals.get('tr_total_taxed_amount', 0.0) + total_taxed_amount
                group_vals['tr_total_taxed_residual_amount'] = group_vals.get('tr_total_taxed_residual_amount', 0.0) + total_residual_amount

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
        is_withholding = vals.get('withholding')

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
            return details['tr_total_taxed_amount'] if is_withholding else details.get(f'base_amount{currency_suffix}', 0)

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
                        '_text': grouping_key['percent_withheld'] if is_withholding else grouping_key['amount'],
                    },
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key}),
                }
                for grouping_key, details in aggregated_tax_details.items()
                if grouping_key
            ],
        }

    def _get_tax_category_node(self, vals):
        """Returns the tax category node for a line or invoice, including TR-specific fields.

        - For lines with Turkish withholding (`l10n_tr_tax_withheld`), returns a minimal
        TaxScheme node with the tax name and type code.
        - For other lines, it extends the default tax category node to include:
            - `cbc:TaxExemptionReasonCode`: The TR tax exemption code.
            - `cbc:TaxExemptionReason`: The localized TR tax exemption name.
        These fields are only added if a TR exemption is set and the context does not skip it.

        :param vals: Dictionary containing: grouping_key & invoice record.
        :return: dict representing the XML structure of the tax category node.
        """
        grouping_key = vals['grouping_key']
        if grouping_key.get('l10n_tr_tax_withheld'):
            return {
                'cac:TaxScheme': {
                    'cbc:Name': {'_text': grouping_key['name']},
                    'cbc:TaxTypeCode': {'_text': grouping_key['tax_type_code']},
                },
            }
        tax_totals_vals = super()._get_tax_category_node(vals)
        tax_invoice_exemption = vals['invoice'].l10n_tr_exemption_code_id
        if self.env.context.get('skip_tr_reason_code') or not tax_invoice_exemption:
            return tax_totals_vals

        tax_totals_vals.update({
            'cbc:TaxExemptionReasonCode': {'_text': tax_invoice_exemption.code},
            'cbc:TaxExemptionReason': {'_text': tax_invoice_exemption.with_context(lang='tr_TR').name},
        })
        return tax_totals_vals

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the TR UBL version, we always want the Shipment with ID empty node, due to it being required.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        shipment_id_elements = xml_root.findall('.//cac:Shipment/cbc:ID', namespaces=xml_root.nsmap)
        for element in shipment_id_elements:
            if element.text == 'NO_ID':
                element.text = ''
        return etree.tostring(xml_root, xml_declaration=True, encoding='UTF-8'), errors

    # UBL TR 1.2 Decoder
    # ========================

    @api.model
    def _get_profile_id(self, tree):
        """Extracts ProfileID from the XML tree.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :return: str, ProfileID value.
        """
        return tree.findtext('.//cbc:ProfileID', namespaces=tree.nsmap)

    @api.model
    def _get_partner_node_name(self, tree):
        """Maps ProfileID to partner node name (e.g., IHRACAT → BuyerCustomer).
        :param tree: lxml.etree.Element, the root of the XML tree.
        :return: str, partner node name.
        """
        profile_id = self._get_profile_id(tree)
        profile_id_tree_node_map = defaultdict(lambda: 'AccountingCustomer', {
            'IHRACAT': 'BuyerCustomer',
        })
        return profile_id_tree_node_map[profile_id]

    @api.model
    def _get_invoice_type_code(self, tree):
        """Extracts the InvoiceTypeCode from the XML tree.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :return: str, InvoiceTypeCode value.
        """
        return tree.findtext('.//cbc:InvoiceTypeCode', namespaces=tree.nsmap)

    def _extract_postal_address_from_xml(self, tree, node_name):
        """Extracts postal address details (e.g., country, city, street) from XML for the given xml tree.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param node_name: str, i.e 'AccountingSupplier', 'AccountingCustomer', 'BuyerCustomer'.
        :return: dict with postal address details.
        """
        nsmap = tree.nsmap
        postal_address_cac = f'.//cac:{node_name}Party//cac:PostalAddress'

        return {
            'country_code': self._find_value(f'{postal_address_cac}/cac:Country/cbc:IdentificationCode', tree, nsmap),
            'country_name': self._find_value(f'{postal_address_cac}/cac:Country/cbc:Name', tree, nsmap),
            'street': self._find_value(f'{postal_address_cac}/cbc:StreetName', tree, nsmap),
            'city': self._find_value(f'{postal_address_cac}/cbc:CitySubdivisionName', tree, nsmap),
            'zip': self._find_value(f'{postal_address_cac}/cbc:PostalZone', tree, nsmap),
            'state_name': self._find_value(f'{postal_address_cac}/cbc:CityName', tree, nsmap),
        }

    @api.model
    def _extract_partner_vals_from_xml(self, tree, node_name):
        """
        Extracts partner values (name, VAT, address, etc.) for a given role.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param node_name: str, i.e 'AccountingSupplier', 'AccountingCustomer', 'BuyerCustomer'.
        :return: dict with partner values.
        """
        nsmap = tree.nsmap
        partner_vals = self._import_retrieve_partner_vals(tree, node_name)

        partner_vals.update({
            'vat': (
                    self._find_value(
                        f'.//cac:{node_name}Party//cac:PartyLegalEntity//cbc:CompanyID[string-length(text()) > 5]',
                        tree, nsmap)
                    or self._find_value(
                f'.//cac:{node_name}Party//cac:PartyIdentification//cbc:ID[@schemeID="VKN"][string-length(text()) > 5]',
                tree, nsmap)
            ),
            'phone': self._find_value(f'.//cac:{node_name}Party//cac:Contact//cbc:Telephone', tree, nsmap),
            'email': self._find_value(f'.//cac:{node_name}Party//cac:Contact//cbc:ElectronicMail', tree, nsmap),
            'name': (
                    self._find_value(f'.//cac:{node_name}Party//cac:PartyName//cbc:Name', tree, nsmap)
                    or self._find_value(f'.//cac:{node_name}Party//cbc:RegistrationName', tree, nsmap)
            ),
            'postal_address': self._extract_postal_address_from_xml(tree, node_name),
        })
        return partner_vals

    @api.model
    def _ensure_partner_address(self, partner, postal_address):
        """
        Checks and sets missing address details for the partner (e.g., country, state, city).
        :param partner: res.partner record.
        :param postal_address: dict with postal address details.
        return: None
        """
        if partner and not partner.country_id and not partner.street and not partner.street2 and not partner.city and not partner.zip and not partner.state_id:
            country_domain = []
            if country_code := postal_address.get('country_code'):
                country_domain.append(('code', '=', country_code))
            elif country_name := postal_address.get('country_name'):
                country_domain.append(('name', '=', country_name))
            country = self.env['res.country'].search(country_domain) if country_domain else \
                self.env[
                    'res.country']
            state_name = postal_address.get('state_name')
            state = self.env['res.country.state'].search(
                [('country_id', '=', country.id), ('name', '=', state_name)],
                limit=1,
            ) if state_name and country else self.env['res.country.state']

            partner.write({
                'country_id': country.id,
                'street': postal_address.get('street'),
                'street2': postal_address.get('additional_street'),
                'city': postal_address.get('city'),
                'zip': postal_address.get('zip'),
                'state_id': state.id,
            })

    @api.model
    def _create_partner(self, name, phone, email, vat, logs):
        """
        Creates a new partner with the given name, phone, email, and VAT details. If creation fails, returns False.
        :param name: str, partner name.
        :param phone: str, partner phone.
        :param email: str, partner email.
        :param vat: str, partner VAT number.
        :param logs: list, to append log messages.
        :return: res.partner record or False if creation failed.
        """
        if not name or not vat:
            logs.append(_("Could not create a partner due to name or vat missing"))
            return False

        partner_vals = {'name': name, 'email': email, 'phone': phone, 'vat': vat}
        partner = self.env['res.partner'].create(partner_vals)
        logs.append(_("Could not retrieve a partner corresponding to '%s'. A new partner was created.", name))
        return partner

    @api.model
    def _resolve_invoice_partner(self, tree, company_id, invoice_values, logs):
        """
        Retrieve or create the partner from the XML tree and set it to the invoice values.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param company_id: int, the company ID for context.
        :param invoice_values: dict, to set the 'partner_id' if found or created.
        :param logs: list, to append log messages.
        :return: res.partner record.
        """
        partner_node_name = self._get_partner_node_name(tree)
        partner_vals = self._extract_partner_vals_from_xml(tree, partner_node_name)

        if not partner_vals.get('vat'):
            logs.append(_("The partner VAT is missing; cannot retrieve or create the partner."))
            return self.env['res.partner']

        """ Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name) """
        partner = self.env['res.partner'] \
            .with_company(company_id) \
            ._retrieve_partner(domain=[('vat', '=', partner_vals.get('vat'))])

        if partner:
            self._ensure_partner_address(partner, partner_vals.get('postal_address', {}))
        else:
            logs.append(_("No partner found with VAT %s. A new partner is created.", partner_vals.get('vat')))
            # Create and verify partner
            partner = self._create_partner(
                partner_vals.get('name'),
                partner_vals.get('phone'),
                partner_vals.get('email'),
                partner_vals.get('vat'),
                logs,
            )
            self._ensure_partner_address(partner, partner_vals.get('postal_address', {}))
            if partner:
                partner.l10n_tr_check_nilvera_customer()

        if partner:
            invoice_values['partner_id'] = partner.id
        return partner

    @api.model
    def _resolve_bank_account(self, tree, partner, invoice_values, logs):
        """
        Extract bank account details from the XML tree and set them to the invoice values.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param partner: res.partner record.
        :param invoice_values: dict, to set 'partner_bank_id' if found or created
        :param logs: list, to append log messages.
        """
        ns = tree.nsmap
        payment_means = tree.find('.//cac:PaymentMeans', namespaces=ns)
        if payment_means is None:
            logs.append(_("No bank details were found in the document."))
            return

        bank_account_vals = []
        for acc in payment_means.findall('.//cac:PayeeFinancialAccount', namespaces=ns):
            bank_account_vals.append({
                'account_id': sanitize_account_number(
                    self._find_value('./cbc:ID', acc, ns),
                ),
                'currency_code': self._find_value('./cbc:CurrencyCode', acc, ns),
            })

        if not bank_account_vals:
            logs.append(_("No bank details were found in the document."))
            return

        account_numbers = [val['account_id'] for val in bank_account_vals if val['account_id']]
        existing_accounts = (self.env['res.partner.bank'].with_context(active_test=False)
                             .search([('acc_number', 'in', account_numbers), ('partner_id', '=', partner.id)]))

        if existing_accounts:
            invoice_values['partner_bank_id'] = existing_accounts[0].id

            if not existing_accounts[0].active:
                existing_accounts[0].active = True
                logs.append(_("An existing bank account %s has been reactivated", existing_accounts[0].acc_number))
            return

        ResPartnerBank = self.env['res.partner.bank'].with_env(self.env(context=clean_context(self.env.context)))
        bank_account = ResPartnerBank.create({
            'partner_id': partner.id,
            'acc_number': bank_account_vals[0]['account_id'],
            'currency_id': self.env['res.currency'].search([
                ('name', '=', bank_account_vals[0]['currency_code']),
            ], limit=1).id,
        })
        logs.append(_("A new bank account %s has been created.", bank_account.acc_number))
        invoice_values['partner_bank_id'] = bank_account.id

    @api.model
    def _resolve_delivery_details(self, tree, invoice_values):
        """
        Extract delivery details from the XML tree and set them to the invoice values.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param invoice_values: dict, to set delivery details.
        """
        delivery_tree = tree.find(".//cac:InvoiceLine/cac:Delivery", tree.nsmap)
        if delivery_tree is None:
            return

        delivery_terms_id = delivery_tree.findtext("cac:DeliveryTerms/cbc:ID", namespaces=tree.nsmap)
        transport_mode_code = delivery_tree.findtext(
            "cac:Shipment/cac:ShipmentStage/cbc:TransportModeCode", namespaces=tree.nsmap,
        )

        invoice_values['l10n_tr_shipping_type'] = transport_mode_code
        invoice_values['invoice_incoterm_id'] = self.env['account.incoterms'].search(
            [('code', '=', delivery_terms_id)], limit=1,
        ).id

    @api.model
    def _resolve_export_exemption(self, tree, invoice_values, logs):
        """
        Sets export exemption details (e.g., exemption code, reason) for IHRACAT invoices.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param invoice_values: dict, to set exemption details.
        :param logs: list, to append log messages.
        """
        invoice_type_code = self._get_invoice_type_code(tree)
        if invoice_type_code not in ['ISTISNA', 'IHRACKAYITLI']:
            return
        tax_category_node = tree.find('./cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory', tree.nsmap)
        if tax_category_node is not None:
            tax_exemption_reason_code = tax_category_node.findtext('cbc:TaxExemptionReasonCode', namespaces=tree.nsmap)
            tax_exemption_id = self.env['l10n_tr_nilvera_einvoice_extended.account.tax.code'].search([
                ('code', '=', tax_exemption_reason_code),
            ], limit=1)

            if tax_exemption_id:
                invoice_values['l10n_tr_exemption_code_id'] = tax_exemption_id.id
            else:
                logs.append(_("Could not find exemption code with reason '%s'"))

    @api.model
    def _resolve_basic_fields(self, tree, invoice_values, logs):
        """
        Set basic invoice fields from the XML tree.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param invoice_values: dict, to set basic invoice fields.
        :param logs: list, to append log messages.
        :return: None
        """

        profile_id = self._get_profile_id(tree)
        # under profile_id on xml there is a ID, we will map it to bill reference/reference for bill and invoice
        if profile_id == 'IHRACAT':
            invoice_values['l10n_tr_is_export_invoice'] = True
        elif profile_id in ['TEMELFATURA', 'KAMU']:
            # EARSIVFATURA is ignored as it's not in the l10n_tr_gib_invoice_scenario field
            invoice_values['l10n_tr_gib_invoice_scenario'] = profile_id

        invoice_values['l10n_tr_gib_invoice_type'] = tree.findtext('.//cbc:InvoiceTypeCode', namespaces=tree.nsmap)
        invoice_values['currency_id'], currency_logs = self._import_currency(tree, './/{*}DocumentCurrencyCode')
        logs.extend(currency_logs)

        invoice_values['invoice_date'] = tree.findtext('.//cbc:IssueDate', namespaces=tree.nsmap)
        invoice_values['invoice_date_due'] = self._find_value('.//cac:PaymentMeans/cbc:PaymentDueDate', tree,
                                                              tree.nsmap)
        invoice_values['ref'] = (
                self._find_value('./cac:OrderReference/cbc:ID', tree)
                or self._find_value('./cbc:ID', tree)
        )
        invoice_values['narration'] = self._import_description(tree, xpaths=['./{*}Note', './{*}PaymentTerms/{*}Note'])

    @api.model
    def _get_product_id_by_default_code_or_ctsp(self, vals):
        """
        Retrieves product records based on their default codes.
        :param vals: list of str, product default codes.
        :return: dict mapping default_code to product.product record.
        """
        default_codes = [val[0] for val in vals if val[0]]
        ctsp_numbers = [val[1] for val in vals if val[1]]
        data_list = self.env['product.product']._read_group(
            domain=[
                '|',
                ('default_code', 'in', default_codes),
                ('l10n_tr_ctsp_number', 'in', ctsp_numbers),
            ],
            aggregates=['id:recordset'],
            groupby=['default_code', 'l10n_tr_ctsp_number'],
        )
        result = {
            'default_codes': {},
            'ctsp_numbers': {},
        }
        for default_code, ctsp_number, records in data_list:
            if default_code and default_code not in result['default_codes']:
                result['default_codes'][default_code] = records
            if ctsp_number and ctsp_number not in result['ctsp_numbers']:
                result['ctsp_numbers'][ctsp_number] = records
        return result

    @api.model
    def _get_tax_id_by_percentage(self, amount, move_type):
        """
        Retrieves the tax ID based on the percentage amount and account move type.
        :param amount: float, tax percentage amount.
        :param move_type: str, 'sale' or 'purchase'.
        :return: int, tax ID.
        """
        return self.env['account.tax'].search([
            ('country_id.code', '=', 'TR'),
            ('amount', '=', amount),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', move_type),
        ], limit=1, order='sequence').id

    @api.model
    def _get_tax_id_by_reason_code(self, withholding_code, move_type):
        """
        Retrieves the tax ID based on the withholding reason code and account move type.
        :param withholding_code: str, withholding reason code.
        :param move_type: str, 'sale' or 'purchase'.
        :return: int, tax ID.
        """
        # There must be only one tax for each withholding code in Nilvera
        # But based on model structure there can be multiple parent tax for each withholding code
        return self.env['account.tax'].search([
            ('children_tax_ids.l10n_tr_tax_withholding_code_id.code', '=', withholding_code),
            ('country_id.code', '=', 'TR'),
            ('type_tax_use', '=', move_type),
        ], order='sequence', limit=1).id

    @api.model
    def _get_tax_id_by_tax_details(self, tax_details_list, profile_id, invoice_type, move_type):
        """
        Retrieves tax IDs for a list of tax details based on profile ID, invoice type, and account move type.
        :param tax_details_list: list of dicts, each containing tax details.
        :param profile_id: str, ProfileID from the XML.
        :param invoice_type: str, InvoiceTypeCode from the XML.
        :param move_type: str, 'sale' or 'purchase'.
        :return: list of lists, each inner list contains tax IDs for the corresponding tax details
        """
        result = []
        for tax_details in tax_details_list:
            if profile_id == 'IHRACAT':
                # this is a tax-exempt export
                tax_id = self._get_tax_id_by_percentage(0, move_type=move_type)
            elif invoice_type == 'TEVKIFAT':
                tax_id = self._get_tax_id_by_reason_code(tax_details['withholding_reason_code'],
                                                         move_type=move_type)
            else:
                tax_id = self._get_tax_id_by_percentage(tax_details['tax_percentage'], move_type=move_type)
            result.append([tax_id] if tax_id else [])
        return result

    @api.model
    def _extract_tax_details(self, line_tree, nsmap):
        """
        Extracts tax details (withholding reason code and tax percentage) from a line XML tree.
        :param line_tree: lxml.etree.Element, the line XML tree.
        :param nsmap: dict, namespace mapping for XML parsing.
        :return: dict with tax details.
        """
        tax_percentage = self._find_value('.//cac:TaxTotal//cac:TaxSubtotal//cbc:Percent', line_tree, nsmap)
        return {
            'withholding_reason_code': self._find_value(
                './/cac:WithholdingTaxTotal//cac:TaxSubtotal//cac:TaxCategory//cbc:TaxTypeCode', line_tree, nsmap),
            'tax_percentage': float(tax_percentage) if tax_percentage else 0.0,
        }

    @api.model
    def _parse_line_discount(self, line_tree, nsmap):
        """
        Extracts line discount percentage from a line XML tree.
        :param line_tree: lxml.etree.Element, the line XML tree.
        :param nsmap: dict, namespace mapping for XML parsing.
        :return: float, discount percentage.
        """
        discount_percentage = self._find_value('.//cac:AllowanceCharge/cbc:MultiplierFactorNumeric', line_tree, nsmap)
        return float(discount_percentage) * 100 if discount_percentage else 0.0

    @api.model
    def _resolve_invoice_lines(self, tree, invoice_values, move_type, logs):
        """
        Extracts and sets invoice line details from the XML tree into invoice values.
        :param tree: lxml.etree.Element, the root of the XML tree.
        :param invoice_values: dict, to set 'invoice_line_ids'.
        :param move_type: str, 'sale' or 'purchase'.
        :param logs: list, to append log messages.
        :return: None
        """
        nsmap = tree.nsmap
        profile_id = self._get_profile_id(tree)
        invoice_type = self._get_invoice_type_code(tree)
        lines_nodes = tree.findall('.//cac:InvoiceLine', namespaces=nsmap)
        if not lines_nodes:
            logs.append(_("No invoice lines were found in the document."))
            return

        # pre process data
        line_data = []
        for line_tree in lines_nodes:
            line_data.append({
                'default_code': self._find_value('.//cac:Item/cac:SellersItemIdentification/cbc:ID', line_tree, nsmap),
                'ctsp_number': self._find_value('.//cbc:RequiredCustomsID', line_tree, nsmap),
                'line_name': self._find_value('.//cac:Item/cbc:Description', line_tree, nsmap),
                'price_unit': self._find_value('.//cac:Price/cbc:PriceAmount', line_tree, nsmap),
                'discount_percentage': self._parse_line_discount(line_tree, nsmap),
                'qty': self._find_value('.//cbc:InvoicedQuantity', line_tree, nsmap),
                'tax_details': self._extract_tax_details(line_tree, nsmap),
            })
        product_ids_by_dc_ctsp = self._get_product_id_by_default_code_or_ctsp(
            [(line['default_code'], line['ctsp_number']) for line in line_data if
             line['default_code'] or line['ctsp_number']],
        )

        tax_id_by_tax_details = self._get_tax_id_by_tax_details(
            [(line['tax_details']) for line in line_data if line['tax_details']],
            profile_id,
            invoice_type,
            move_type,
        )

        # set line vals
        invoice_values['invoice_line_ids'] = []
        for i, data in enumerate(line_data):
            product_id = product_ids_by_dc_ctsp['ctsp_numbers'].get(data['ctsp_number'], False) or \
                         product_ids_by_dc_ctsp['default_codes'].get(data['default_code'], False)

            line_val = {
                'product_id': product_id.id if product_id else False,
                'price_unit': float(data['price_unit'] or 0),
                'quantity': float(data['qty'] or 0),
                'tax_ids': tax_id_by_tax_details[i] if tax_id_by_tax_details[i] else False,
                'discount': data['discount_percentage'],
            }
            if not product_id:
                line_val['name'] = data['line_name']

            invoice_values['invoice_line_ids'].append(Command.create(line_val))

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # EXTENDS account_edi_ubl_cii
        # Adding custom decoder for Nilvera's TR1.2 UBL format

        if tree.findtext('.//cbc:CustomizationID', namespaces=tree.nsmap) != 'TR1.2':
            return super()._import_fill_invoice(invoice, tree, qty_factor)

        if qty_factor == -1:
            # TODO: Support credit note for UBL TR1.2
            return [_("Invoice/Bill return creation from XML is not supported for TR1.2 UBL format yet.")]

        logs = []
        invoice_values = {}

        # ==== Nilvera UUID ====
        if uuid_node := tree.findtext('./{*}UUID'):
            invoice_values['l10n_tr_nilvera_uuid'] = uuid_node

        # ==== Process partner ====
        partner_id = self._resolve_invoice_partner(
            tree,
            invoice.company_id,
            invoice_values,
            logs,
        )

        # ==== Process Bank details ====
        bank_recipient = self.env.company.partner_id if invoice.is_inbound() else partner_id
        self._resolve_bank_account(tree, bank_recipient, invoice_values, logs)

        # ==== Delivery Details ====
        self._resolve_delivery_details(tree, invoice_values)

        # ==== Exemption Details ====
        self._resolve_export_exemption(tree, invoice_values, logs)

        # ==== Basic invoice fields ====
        self._resolve_basic_fields(tree, invoice_values, logs)

        # ==== Lines =====
        move_type = 'sale' if invoice.is_inbound() else 'purchase'
        self._resolve_invoice_lines(tree, invoice_values, move_type, logs)

        invoice.write(invoice_values)

        if not invoice.currency_id.active:
            invoice.currency_id.active = True
            logs.append(_("The currency %s has been reactivated.", invoice.currency_id.name))
        return logs
