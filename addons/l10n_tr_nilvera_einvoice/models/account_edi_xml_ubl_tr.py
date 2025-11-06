import math
from collections import defaultdict

from lxml import etree
from num2words import num2words

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict, html2plaintext

from odoo.addons.l10n_tr_nilvera_einvoice.tools.clean_node_dict import clean_node_dict
from odoo.addons.l10n_tr_nilvera_einvoice.tools.ubl_tr_invoice import TrInvoice


class AccountEdiXmlUblTr(models.AbstractModel):
    _name = "account.edi.xml.ubl.tr"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL-TR 1.2"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

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

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return '%s_einvoice.xml' % invoice.name.replace("/", "_")

    def _get_tax_category_code(self, customer, supplier, tax):
        # OVERRIDES account.edi.ubl_21
        if tax.amount < 0:  # This is a withholding
            return '9015'
        return '0015'

    def _add_invoice_currency_vals(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_currency_vals(vals)
        vals['currency_dp'] = 2  # Force 2 decimal places everywhere

    # -------------------------------------------------------------------------
    # EXPORT: TEMPLATES
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Check the customer status if it hasn't been done before as it's needed for profile_id
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'not_checked':
            invoice.partner_id._check_nilvera_customer()

        if invoice._l10n_tr_nilvera_einvoice_check_negative_lines():
            raise UserError(self.env._("Nilvera portal cannot process negative quantity nor negative price on invoice lines"))

        # Using _get_sequence_format_param to extract the invoice sequence components for various formats.
        # To send an invoice to Nilvera, the format needs to follow ABC2009123456789.
        _, parts = invoice._get_sequence_format_param(invoice.name)
        prefix, year, number = parts['prefix1'][:3], parts['year'], str(parts['seq']).zfill(9)
        invoice_id = f"{prefix.upper()}{year}{number}"

        document_node.update({
            'cbc:CustomizationID': {'_text': 'TR1.2'},
            'cbc:ProfileID': {'_text': self._get_tr_profile_id(invoice)},
            'cbc:ID': {'_text': invoice_id},
            'cbc:CopyIndicator': {'_text': 'false'},
            'cbc:UUID': {'_text': invoice.l10n_tr_nilvera_uuid},
            'cbc:DueDate': None,
            'cbc:InvoiceTypeCode': {'_text': 'ISTISNA' if invoice.l10n_tr_is_export_invoice else invoice.l10n_tr_gib_invoice_type},
            'cbc:CreditNoteTypeCode': {'_text': 'IADE'} if vals['document_type'] == 'credit_note' else None,
            'cbc:PricingCurrencyCode': {'_text': invoice.currency_id.name.upper()}
                if vals['currency_id'] != vals['company_currency_id'] else None,
            'cbc:LineCountNumeric': {'_text': len(invoice.line_ids)},
            'cbc:BuyerReference': None,  # Nilvera will reject any <BuyerReference> tag, so remove it
            'cbc:Note': {
                '_text': html2plaintext(invoice.narration, include_references=False) if invoice.narration else None,
            },
        })

        if invoice.invoice_line_ids._fields.get('deferred_start_date'):
            line_ids = invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line.deferred_start_date)
            if line_ids:
                document_node['cac:InvoicePeriod'] = {
                    'cbc:StartDate': {'_text': line_ids[0].deferred_start_date},
                    'cbc:EndDate': {'_text': line_ids[0].deferred_end_date},
                }

        document_node['cac:OrderReference']['cbc:IssueDate'] = {'_text': invoice.invoice_date}

        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'earchive':
            document_node['cac:AdditionalDocumentReference'] = {
                'cbc:ID': {'_text': 'ELEKTRONIK'},
                'cbc:IssueDate': {'_text': invoice.invoice_date},
                'cbc:DocumentTypeCode': {'_text': 'SEND_TYPE'},
            }
        document_node['cbc:Note'] = [
            document_node['cbc:Note'],
            {'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual_signed, self.env.ref('base.TRY')), 'note_attrs': {}}
        ]
        if vals['invoice'].currency_id.name != 'TRY':
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual, vals['invoice'].currency_id), 'note_attrs': {}})
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_invoice_currency_exchange_rate(invoice)})

    @api.model
    def _l10n_tr_get_amount_integer_partn_text_note(self, amount, currency):
        sign = math.copysign(1.0, amount)
        amount_integer_part, amount_decimal_part = divmod(abs(amount), 1)
        amount_decimal_part = int(amount_decimal_part * 100)

        text_i = num2words(amount_integer_part * sign, lang="tr") or 'Sifir'
        text_d = num2words(amount_decimal_part * sign, lang="tr") or 'Sifir'
        return f'YALNIZ : {text_i} {currency.name} {text_d} {currency.currency_subunit_label}'.upper()

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

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']
        if 'picking_ids' in invoice._fields and invoice.picking_ids:
            document_node['cac:Delivery']['cbc:ID'] = {'_text': invoice.picking_ids[0].name}
            document_node['cac:Delivery']['cbc:ActualDeliveryDate'] = {'_text': invoice.delivery_date}
        else:
            document_node['cac:Delivery'] = None

    def _l10n_tr_get_invoice_currency_exchange_rate(self, invoice):
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            from_currency=invoice.currency_id,
            to_currency=invoice.company_currency_id,
            company=invoice.company_id,
            date=invoice.invoice_date,
        )
        # Nilvera Portal accepts the exchange rate for 6 decimals places only.
        return f'KUR : {conversion_rate:.6f} TL'

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        payment_means_node['cbc:InstructionID'] = None
        payment_means_node['cbc:PaymentID'] = None

    def _add_invoice_exchange_rate_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if vals['currency_id'] != vals['company_currency_id']:
            document_node['cac:PricingExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': vals['currency_name']},
                'cbc:TargetCurrencyCode': {'_text': vals['company_currency_id'].name},
                'cbc:CalculationRate': {'_text': round(invoice.currency_id._get_conversion_rate(invoice.currency_id, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date), 6)},
                'cbc:Date': {'_text': invoice.invoice_date},
            }

    def _l10n_tr_get_total_invoice_discount_amount(self, vals):
        invoice = vals['invoice']
        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in {'line_note', 'line_section'})
        return sum(
            line.currency_id.round(line.price_unit * line.quantity * (line.discount / 100))
            for line in invoice_lines
        )

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        super()._add_document_allowance_charge_nodes(document_node, vals)
        for node in document_node['cac:AllowanceCharge']:
            node['cbc:AllowanceChargeReasonCode'] = None

        total_discount_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        if total_discount_amount:
            document_node['cac:AllowanceCharge'].append({
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReason': {'_text': "Discount"},
                'cbc:Amount': {
                    '_text': self.format_float(total_discount_amount, vals['currency_dp']),
                    'currencyID': vals['currency_name'],
                },
            })

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

    def _get_address_node(self, vals):
        partner = vals['partner']
        model = vals.get('model', 'res.partner')
        country = partner['country' if model == 'res.bank' else 'country_id']
        state = partner['state' if model == 'res.bank' else 'state_id']

        return {
            'cbc:StreetName': {'_text': ' '.join(s for s in [partner.street, partner.street2] if s)},
            'cbc:CitySubdivisionName': {'_text': partner.city},
            'cbc:CityName': {'_text': state.name},
            'cbc:PostalZone': {'_text': partner.zip},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.with_context(lang='tr_TR').name},
            }
        }

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

    def _get_party_node(self, vals):
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        party_node = {
            'cac:PartyIdentification': self._get_party_identification_node_list(partner),
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cac:TaxScheme': {
                    'cbc:Name': {
                        '_text': partner.l10n_tr_tax_office_id.name,
                    }
                }
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            }
        }
        if not partner.is_company:
            name_parts = partner.name.split(' ', 1)
            party_node['cac:Person'] = {
                'cbc:FirstName': {'_text': name_parts[0]},
                # If no family name is present, use a zero-width space (U+200B) to ensure the XML tag is rendered. This is required by Nilvera.
                'cbc:FamilyName': {'_text': name_parts[1] if len(name_parts) > 1 else '\u200B'},
            }
        return party_node

    def _get_party_identification_node_list(self, partner):
        official_categories = partner.category_id._get_l10n_tr_official_categories()
        return [
            {
                'cbc:ID': {
                    '_text': partner.vat,
                    'schemeID': 'VKN' if partner.is_company else 'TCKN',
                },
            },
            *(
                {
                    'cbc:ID': {
                        '_text': category.name,
                        'schemeID': category.parent_id.name,
                    },
                }
                for category in partner.category_id
                if category.parent_id in official_categories
            ),
        ]

    def _get_tax_category_node(self, vals):
        """Overrides UBL 21 to returns the tax category node for a line or invoice, including TR-specific fields.

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
        is_withholding = grouping_key['tax_category_code'] == '9015'
        tax_category_node = {
            'cac:TaxScheme': {
                'cbc:Name': {'_text': 'KDV Tevkifatı' if is_withholding else 'Gerçek Usulde KDV'},
                'cbc:TaxTypeCode': {'_text': grouping_key['tax_category_code']}
            }
        }
        tax_invoice_exemption = vals['invoice'].l10n_tr_exemption_code_id
        if self.env.context.get('skip_tr_reason_code') or not tax_invoice_exemption:
            return tax_category_node
        tax_category_node.update({
            'cbc:TaxExemptionReasonCode': {'_text': tax_invoice_exemption.code},
            'cbc:TaxExemptionReason': {'_text': tax_invoice_exemption.with_context(lang='tr_TR').name},
        })
        return tax_category_node

    def _get_tax_subtotal_node(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cac:TaxCategory']['cbc:Percent'] = None
        return tax_subtotal_node

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

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        invoice = vals['invoice']

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]

        # allowance_total_amount needs to have a value even if 0.0 otherwise it's blank in the Nilvera PDF.
        total_allowance_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        monetary_total_node['cbc:AllowanceTotalAmount'] = {
            '_text': self.format_float(total_allowance_amount, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }

        # <cbc:PrepaidAmount> tag is not supported by Nilvera. so it is removed and <cbc:PayableAmount> holds the
        # amount_total so that the total invoice amount (in invoice currency) is preserved.
        monetary_total_node['cbc:PrepaidAmount'] = None
        monetary_total_node['cbc:PayableAmount'] = {
            '_text': self.format_float(invoice.amount_total, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }
        # For invoices registered as Export, the payable amount is set to the total amount
        # without tax, as required by Turkish e-invoicing regulations.
        if invoice.l10n_tr_gib_invoice_type == "IHRACKAYITLI":
            document_node["cac:LegalMonetaryTotal"]["cbc:PayableAmount"]["_text"] = document_node["cac:LegalMonetaryTotal"]["cbc:TaxExclusiveAmount"]["_text"]

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_document_line_allowance_charge_nodes(line_node, vals)
        for allowance_charge_node in line_node['cac:AllowanceCharge']:
            allowance_charge_node['cbc:AllowanceChargeReasonCode'] = None
            discount_percentage = vals.get('discount_amount') / vals.get('gross_subtotal') if vals.get('gross_subtotal') else 0
            allowance_charge_node['cbc:MultiplierFactorNumeric'] = {
            '_text': self.format_float(discount_percentage, vals['currency_dp']),
            }

    def _add_document_line_item_nodes(self, line_node, vals):
        super()._add_document_line_item_nodes(line_node, vals)
        if line_node.get('cac:Item', {}).get('cac:StandardItemIdentification'):
            line_node['cac:Item']['cac:StandardItemIdentification'] = None

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        # No InvoiceLine/Item/ClassifiedTaxCategory in Turkey
        pass

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # Start and End Dates on Invoice Lines is not allowed in Turkey
        pass

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

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        partner_vals.update({
            'vat': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cac:PartyIdentification//cbc:ID[string-length(text()) > 5]', tree),
        })
        return partner_vals

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        # EXTENDS account.edi.xml.ubl_20
        logs = super()._import_fill_invoice_form(invoice, tree, qty_factor)

        # ==== Nilvera UUID ====
        if uuid_node := tree.findtext('./{*}UUID'):
            invoice.l10n_tr_nilvera_uuid = uuid_node

        return logs
