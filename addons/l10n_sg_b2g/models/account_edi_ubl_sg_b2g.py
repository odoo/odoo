from odoo import fields, models


class AccountEdiXml_SgB2G(models.AbstractModel):
    _name = 'account.edi.xml.sg_b2g'
    _inherit = 'account.edi.xml.pint_sg'
    _description = "UBL for Singapore Business-to-Government E-Invoicing"

    def _ubl_add_buyer_reference_node(self, vals):
        # OVERRIDES account.edi.ubl_pint
        invoice = vals['invoice']
        unit_code = invoice.l10n_sg_statutory_board_subbusiness_unit.code
        vals['document_node']['cbc:BuyerReference'] = {'_text': unit_code}

    def _ubl_add_billing_reference_nodes(self, vals):
        # OVERRIDES account.edi.ubl_pint
        invoice = vals['invoice']
        if 'refund' not in invoice.move_type:
            super()._ubl_add_billing_reference_nodes(vals)
            return
        vals['document_node']['cac:BillingReference'] = {
            'cac:InvoiceDocumentReference': {
                'cbc:ID': {'_text': invoice.ref},
            },
        }

    def _ubl_add_order_reference_node(self, vals):
        # OVERRIDES account.edi.xml.ubl_bis3. If there is no II/PO, omit the OrderReference node.
        invoice = vals['invoice']
        if not invoice.l10n_sg_is_from_po_invoice:
            return
        vals['document_node']['cac:OrderReference'] = {
            'cbc:ID': {'_text': invoice.ref},
        }

    def _ubl_add_party_name_node(self, vals):
        """
        OVERRIDE of `account.edi.ubl` to use partner.name instead of partner.display_name. In SG
        B2G, the partner name corresponds to "Attention To" field.
        """
        partner = vals['party_vals']['partner']
        name = partner.name or partner.commercial_partner_id.name

        vals['party_node']['cac:PartyName'] = {
            'cbc:Name': {'_text': name},
        }

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        invoice = vals['invoice']
        payment_term = invoice.invoice_payment_term_id
        if payment_term:
            document_node['cac:PaymentTerms'] = {
                'cbc:Note': {'_text': payment_term.l10n_sg_b2g_code},
            }

    def _is_document_allowance_charge(self, base_line):
        """
        EXTENDS `account.edi.xml.ubl_20` to comply with SG B2G requirements: Freight charge should
        be treated as a document-level AllowanceCharge.
        """
        is_freight_charge = base_line['product_id'] == self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        return is_freight_charge or super()._is_document_allowance_charge(base_line)

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        """
        EXTENDS 'account.edi.xml.ubl_bis3'
        BIS3 only generates AllowanceCharge nodes for early payment; freight charges must be
        appended separately since BIS3 bypasses the generic _add_document_allowance_charge_nodes.
        """
        super()._add_invoice_allowance_charge_nodes(document_node, vals)
        currency = vals['currency_id']
        freight_product = self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        for base_line in vals['base_lines']:
            if base_line['product_id'] != freight_product:
                continue
            aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(
                base_line,
                lambda bl, td: self._ubl_default_tax_category_grouping_key(bl, td, vals, currency),
            )
            amount = base_line['tax_details']['total_excluded_currency']
            document_node['cac:AllowanceCharge'].append({
                '_currency': currency,
                'cbc:ChargeIndicator': {'_text': 'true' if amount >= 0 else 'false'},
                'cbc:AllowanceChargeReasonCode': {'_text': 'FC'},
                'cbc:AllowanceChargeReason': {'_text': "Freight charge"},
                'cbc:Amount': {
                    '_text': currency.round(abs(amount)),
                    'currencyID': currency.name,
                },
                'cac:TaxCategory': [
                    self._ubl_get_allowance_charge_early_payment_tax_category_node(vals, grouping_key)
                    for grouping_key in aggregated_tax_details
                    if grouping_key
                ],
            })

    def _ubl_add_invoice_line_nodes(self, vals):
        # EXTENDS `account.edi.ubl` to exclude the freight charge from invoice lines.
        super()._ubl_add_invoice_line_nodes(
            vals,
            filter_function=lambda base_line: not self._is_document_allowance_charge(base_line),
        )

    def _ubl_add_credit_note_line_nodes(self, vals):
        # EXTENDS `account.edi.ubl` to exclude the freight charge from credit note lines.
        super()._ubl_add_credit_note_line_nodes(
            vals,
            filter_function=lambda base_line: not self._is_document_allowance_charge(base_line),
        )

    def _ubl_add_invoice_line_node(self, vals):
        # EXTENDS `account.edi.ubl`
        super()._ubl_add_invoice_line_node(vals)
        line_node = vals['line_node']
        base_line = vals['line_vals']['base_line']

        line_ref = base_line['record'].l10n_sg_b2g_invoice_line_no or line_node['cbc:ID']['_text']
        line_node['cac:OrderLineReference'] = {
            'cbc:LineID': {'_text': f"{line_ref}"},
        }

        move = vals['invoice']
        if move.l10n_sg_is_from_po_invoice and base_line['product_id'].type == 'service':
            item_qty_node = line_node['cbc:InvoicedQuantity']
            gross_price_unit_node = line_node['cac:Price']['cbc:PriceAmount']
            item_qty_node['_text'], gross_price_unit_node['_text'] = gross_price_unit_node['_text'], item_qty_node['_text']
            item_qty_node.pop('unitCode', None)

    def _ubl_add_credit_note_line_node(self, vals):
        # EXTENDS `account.edi.ubl`
        super()._ubl_add_credit_note_line_node(vals)
        line_node = vals['line_node']
        base_line = vals['line_vals']['base_line']

        line_ref = base_line['record'].l10n_sg_b2g_invoice_line_no or line_node['cbc:ID']['_text']
        line_node['cac:OrderLineReference'] = {
            'cbc:LineID': {'_text': f"{line_ref}"},
        }

        move = vals['invoice']
        if move.l10n_sg_is_from_po_invoice and base_line['product_id'].type == 'service':
            item_qty_node = line_node['cbc:CreditedQuantity']
            gross_price_unit_node = line_node['cac:Price']['cbc:PriceAmount']
            item_qty_node['_text'], gross_price_unit_node['_text'] = gross_price_unit_node['_text'], item_qty_node['_text']
            item_qty_node.pop('unitCode', None)

    def _get_invoice_node(self, vals):
        """
        EXTENDS `account.edi.xml.ubl_21` to add 'PayeeParty' node. The node is generated only when
        the vendor with multiple vendor IDs who wish to receive payment in the bank account
        registered with another vendor ID.
        """
        document_node = super()._get_invoice_node(vals)

        bank = vals['invoice'].partner_bank_id
        payee_partner = bank.partner_id
        supplier = vals['supplier']

        needs_separate_payee = (
            payee_partner
            and payee_partner != supplier
            and payee_partner.ref != supplier.ref
        )
        if needs_separate_payee:
            document_node['cac:PayeeParty'] = {
                'cac:PartyIdentification': {  # Mandatory field in SG B2G
                    'cbc:ID': {'_text': payee_partner.ref},
                },
                'cac:PartyName': {  # Mandatory field
                    'cbc:Name': {'_text': bank.holder_name},
                },
            }

        return document_node

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.pint_sg
        constraints = super()._export_invoice_constraints(invoice, vals)

        """ Business Unit
        Requirement: The Business Unit, which is a maximum 5-character code, must be based on the
        list of ministries / statutory boards.
        Ref: data/l10n.sg.statutory.board.subbusiness.unit.csv
        """
        if not invoice.l10n_sg_statutory_board_subbusiness_unit:
            constraints['sg_b2g_business_unit_required'] = self.env._(
                "You must specify a sub-business unit of Singaporean ministry / statutory board on"
                " the invoice.")

        """ Attention To
        Requirement: Maximum 20 characters. Limited set of acceptable characters (ASCII codes 32-127).
        Note: This field is not mandatory on PEPPOL BIS but mandatory on AGD B2G.
        """
        attention_to = vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cac:Contact']['cbc:Name']['_text']
        if len(attention_to) > 20:
            constraints['sg_b2g_attention_to_char_limit'] = self.env._(
                "The partner name must be less than 20 characters.")
        if not all(32 <= ord(c) <= 127 for c in attention_to):
            constraints['sg_b2g_attention_to_invalid_char'] = self.env._(
                "The partner name must contain only acceptable characters (ASCII codes 32-127).")

        """ Invoice Number
        Requirement: Maximum 27 characters. Cannot contain space. Limited set of acceptable characters.
        """
        invoice_number = vals['document_node']['cbc:ID']['_text']
        if len(invoice_number) > 27:
            constraints['sg_b2g_invoice_number_char_limit'] = self.env._(
                "The invoice number must be less than 27 characters.")
        if ' ' in invoice_number:
            constraints['sg_b2g_invoice_number_space_not_allowed'] = self.env._(
                "The invoice number cannot contain spaces.")
        if not all(32 <= ord(c) <= 127 for c in invoice_number):
            constraints['sg_b2g_invoice_number_invalid_char'] = self.env._(
                "The invoice number must contain only acceptable characters (ASCII codes 32-127).")

        """ Invoice Date
        Requirement: Cannot be backdated by more than 7 calendar days or forward-dated.
        """
        today = fields.Date.context_today(self)

        if invoice.invoice_date < fields.Date.subtract(today, days=7) or invoice.invoice_date > today:
            constraints['sg_b2g_invoice_date_out_of_range'] = self.env._(
                "The invoice date cannot be backdated by more than 7 calendar days or forward-dated.")

        """ Vendor ID
        Requirement: Vendor ID based on the vendor record created at Vendors@Gov must be provided.
        """
        party_id_node = vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cac:PartyIdentification']
        if not party_id_node or not party_id_node[0]['cbc:ID']['_text']:
            constraints['sg_b2g_vendor_id_required'] = self.env._(
                "You must specify a vendor ID based on the vendor record created at Vendors@Gov on"
                " the company contact's 'Reference' field.")

        """ Email Address
        Requirement: Email address of the user must be provided.
        Note: If user does not have a registered vendor record, the e-invoice will be rejected and
        a notification will be sent to this email.
        """
        contact_node = vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cac:Contact']
        if not contact_node or not contact_node['cbc:ElectronicMail']['_text']:
            constraints['sg_b2g_email_address_required'] = self.env._(
                "You must specify an email address on the company contact: %s", vals['supplier'].name)

        """ Invoicing Instruction ID/Purchase Order ID (Customer Reference field)
        This field is used to reference the II/PO. If the invoice is marked as from II/PO, this field
        must be populated.
        """
        po_ii_ref = vals['document_node'].get('cac:OrderReference', {}).get('cbc:ID', {}).get('_text')

        if invoice.l10n_sg_is_from_po_invoice and not po_ii_ref:
            constraints['sg_b2g_po_ii_ref_required'] = self.env._(
                "You must specify an Invoicing Instruction ID/Purchase Order ID on 'Customer Reference' field.")

        """ Invoice Description
        Requirement: This is a mandatory field for B2G invoices. Maximum 254 characters.
        """
        note_text = (vals['document_node']['cbc:Note'] or {}).get('_text')
        if not note_text:
            constraints['sg_b2g_invoice_description_required'] = self.env._(
                "You must specify an invoice description on 'Terms and Conditions' field.")
        elif len(note_text) > 254:
            constraints['sg_b2g_invoice_description_char_limit'] = self.env._(
                "The invoice description on 'Terms and Conditions' field must be less than 254 characters.")

        """ Related Invoice ID
        Requirement: Mandatory for credit notes - To indicate which credit note is meant to offset.
        """
        if 'refund' in invoice.move_type:
            related_invoice_id = vals['document_node'] \
                .get('cac:BillingReference', {}) \
                .get('cac:InvoiceDocumentReference', {}) \
                .get('cbc:ID', {}) \
                .get('_text')
            if not related_invoice_id:
                constraints['sg_b2g_related_invoice_id_required'] = self.env._(
                    "You must specify a related invoice ID on 'Customer Reference' field.")

        """ Remit To Vendor ID
        Requirement: Vendor ID based on the vendor record created at Vendors@Gov must be provided
        in case the seller partner is different from the recipient (bank account holder) partner.
        """
        payee_party_node = vals['document_node'].get('cac:PayeeParty', {})
        if payee_party_node:
            payee_party_id = payee_party_node['cac:PartyIdentification']['cbc:ID']['_text']
            if not payee_party_id:
                constraints['sg_b2g_remit_to_vendor_id_required'] = self.env._(
                    "You must specify a vendor ID based on the vendor record created at Vendors@Gov on"
                    " the bank account holder contact's 'Reference' field.")
            payee_party_name = payee_party_node['cac:PartyName']['cbc:Name']['_text']
            if not payee_party_name:
                constraints['sg_b2g_remit_to_acc_holder_name_required'] = self.env._(
                    "You must specify an account holder name on the bank account used for payment.")

        line_nodes = (
            vals['document_node'].get('cac:CreditNoteLine')
            if 'refund' in invoice.move_type
            else vals['document_node'].get('cac:InvoiceLine')
        ) or []

        """ Invoice Line Number
        Requirement: Maximum 5 characters.
        """
        for line_node in line_nodes:
            if len(line_node['cac:OrderLineReference']['cbc:LineID']['_text']) > 5:
                constraints['sg_b2g_invoice_line_number_char_limit'] = self.env._(
                    "The invoice line number must be less than 5 characters.")

        """ Invoice Line Description
        Requirement: Maximum 254 characters.
        """
        for line_node in line_nodes:
            if len(line_node['cac:Item']['cbc:Name']['_text']) > 254:
                constraints['sg_b2g_invoice_line_description_char_limit'] = self.env._(
                    "The invoice line description must be less than 254 characters.")

        """ Customer Accounting
        Requirement: Invoices for items subject to customer accounting (SRCA-S or SRCA-C) should be
        separately submitted from invoices for standard-rated and zero-rated items.
        """
        customer_accounting_codes = {'SRCA-S', 'SRCA-C'}
        tax_codes = set()
        for line_node in line_nodes:
            for tax_category_node in line_node['cac:Item']['cac:ClassifiedTaxCategory']:
                tax_codes.add(tax_category_node['cbc:ID']['_text'])
        if tax_codes & customer_accounting_codes and tax_codes - customer_accounting_codes:
            constraints['sg_b2g_customer_accounting_mixed'] = self.env._(
                "Invoices for items subject to customer accounting (SRCA-S/SRCA-C) should be"
                " separately submitted from invoices for standard-rated and zero-rated items.")

        """ Payment Terms Code
        Requirement: If payment terms are set, the B2G payment terms code must be specified.
        """
        payment_term = invoice.invoice_payment_term_id
        if payment_term and not payment_term.l10n_sg_b2g_code:
            constraints['sg_b2g_payment_term_code_required'] = self.env._(
                "The payment term '%s' must have a B2G payment terms code configured.",
                payment_term.name)

        return constraints
