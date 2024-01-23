# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, is_html_empty, html2plaintext, cleanup_xml_node
from lxml import etree

from datetime import datetime

import logging

_logger = logging.getLogger(__name__)

DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiXmlCII(models.AbstractModel):
    _name = "account.edi.xml.cii"
    _inherit = 'account.edi.common'
    _description = "Factur-x/XRechnung CII 2.2.0"

    def _export_invoice_filename(self, invoice):
        return "factur-x.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'de.xrechnung:cii:2.2.0',
            'credit_note': 'de.xrechnung:cii:2.2.0',
        }

    def _export_invoice_constraints(self, invoice, vals):
        constraints = self._invoice_constraints_common(invoice)
        constraints.update({
            # [BR-08]-An Invoice shall contain the Seller postal address (BG-5).
            # [BR-09]-The Seller postal address (BG-5) shall contain a Seller country code (BT-40).
            'seller_postal_address': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], 'country_id'
            ),
            # [BR-DE-9] The element "Buyer post code" (BT-53) must be transmitted. (only mandatory in Germany ?)
            'buyer_postal_address': self._check_required_fields(
                vals['record']['commercial_partner_id'], 'zip'
            ),
            # [BR-DE-4] The element "Seller post code" (BT-38) must be transmitted. (only mandatory in Germany ?)
            'seller_post_code': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], 'zip'
            ),
            # [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
            # the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
            'seller_identifier': self._check_required_fields(
                vals['record']['company_id'], ['vat']  # 'siret'
            ),
            # [BR-DE-1] An Invoice must contain information on "PAYMENT INSTRUCTIONS" (BG-16)
            # first check that a partner_bank_id exists, then check that there is an account number
            'seller_payment_instructions_1': self._check_required_fields(
                vals['record'], 'partner_bank_id'
            ),
            'seller_payment_instructions_2': self._check_required_fields(
                vals['record']['partner_bank_id'], 'sanitized_acc_number',
                _("The field 'Sanitized Account Number' is required on the Recipient Bank.")
            ),
            # [BR-DE-6] The element "Seller contact telephone number" (BT-42) must be transmitted.
            'seller_phone': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], ['phone', 'mobile'],
            ),
            # [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
            'seller_email': self._check_required_fields(
                vals['record']['company_id'], 'email'
            ),
            # [BR-CO-04]-Each Invoice line (BG-25) shall be categorized with an Invoiced item VAT category code (BT-151).
            'tax_invoice_line': self._check_required_tax(vals),
            # [BR-IC-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151)
            # is "Intra-community supply" shall contain the Seller VAT Identifier (BT-31) or the Seller tax representative
            # VAT identifier (BT-63) and the Buyer VAT identifier (BT-48).
            'intracom_seller_vat': self._check_required_fields(vals['record']['company_id'], 'vat') if vals['intracom_delivery'] else None,
            'intracom_buyer_vat': self._check_required_fields(vals['record']['commercial_partner_id'], 'vat') if vals['intracom_delivery'] else None,
            # [BR-IG-05]-In an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151) is "IGIC" the
            # invoiced item VAT rate (BT-152) shall be greater than 0 (zero).
            'igic_tax_rate': self._check_non_0_rate_tax(vals)
                if vals['record']['commercial_partner_id']['country_id']['code'] == 'ES'
                    and vals['record']['commercial_partner_id']['zip']
                    and vals['record']['commercial_partner_id']['zip'][:2] in ['35', '38'] else None,
        })
        return constraints

    def _check_required_tax(self, vals):
        for line_vals in vals['invoice_line_vals_list']:
            line = line_vals['line']
            if not vals['tax_details']['tax_details_per_record'][line]['tax_details']:
                return _("You should include at least one tax per invoice line. [BR-CO-04]-Each Invoice line (BG-25) "
                         "shall be categorized with an Invoiced item VAT category code (BT-151).")

    def _check_non_0_rate_tax(self, vals):
        for line_vals in vals['tax_details']['tax_details_per_record']:
            tax_rate_list = line_vals.tax_ids.flatten_taxes_hierarchy().mapped("amount")
            if not any([rate > 0 for rate in tax_rate_list]):
                return _("When the Canary Island General Indirect Tax (IGIC) applies, the tax rate on "
                         "each invoice line should be greater than 0.")

    def _get_scheduled_delivery_time(self, invoice):
        # don't create a bridge only to get line.sale_line_ids.order_id.picking_ids.date_done
        # line.sale_line_ids.order_id.picking_ids.scheduled_date or line.sale_line_ids.order_id.commitment_date
        return invoice.invoice_date

    def _get_invoicing_period(self, invoice):
        # get the Invoicing period (BG-14): a list of dates covered by the invoice
        # don't create a bridge to get the date range from the timesheet_ids
        return [invoice.invoice_date]

    def _get_exchanged_document_vals(self, invoice):
        return {
            'id': invoice.name,
            'type_code': '380' if invoice.move_type == 'out_invoice' else '381',
            'issue_date_time': invoice.invoice_date,
            'included_note': html2plaintext(invoice.narration) if invoice.narration else "",
        }

    def _export_invoice_vals(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, decimal_places=2):
            # Facturx requires the monetary values to be rounded to 2 decimal values
            return float_repr(number, decimal_places)

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            grouping_key = {
                **self._get_tax_unece_codes(invoice, tax),
                'amount': tax.amount,
                'amount_type': tax.amount_type,
            }
            # If the tax is fixed, we want to have one group per tax
            # s.t. when the invoice is imported, we can try to guess the fixed taxes
            if tax.amount_type == 'fixed':
                grouping_key['tax_name'] = tax.name
            return grouping_key

        # Validate the structure of the taxes
        self._validate_taxes(invoice)

        # Create file content.
        tax_details = invoice._prepare_invoice_aggregated_taxes(grouping_key_generator=grouping_key_generator)

        # Fixed Taxes: filter them on the document level, and adapt the totals
        # Fixed taxes are not supposed to be taxes in real live. However, this is the way in Odoo to manage recupel
        # taxes in Belgium. Since only one tax is allowed, the fixed tax is removed from totals of lines but added
        # as an extra charge/allowance.
        fixed_taxes_keys = [k for k in tax_details['tax_details'] if k['amount_type'] == 'fixed']
        for key in fixed_taxes_keys:
            fixed_tax_details = tax_details['tax_details'].pop(key)
            tax_details['tax_amount_currency'] -= fixed_tax_details['tax_amount_currency']
            tax_details['tax_amount'] -= fixed_tax_details['tax_amount']
            tax_details['base_amount_currency'] += fixed_tax_details['tax_amount_currency']
            tax_details['base_amount'] += fixed_tax_details['tax_amount']

        if 'siret' in invoice.company_id._fields and invoice.company_id.siret:
            seller_siret = invoice.company_id.siret
        else:
            seller_siret = invoice.company_id.company_registry

        buyer_siret = False
        if 'siret' in invoice.commercial_partner_id._fields and invoice.commercial_partner_id.siret:
            buyer_siret = invoice.commercial_partner_id.siret
        template_values = {
            **invoice._prepare_edi_vals_to_export(),
            'tax_details': tax_details,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'is_html_empty': is_html_empty,
            'scheduled_delivery_time': self._get_scheduled_delivery_time(invoice),
            'intracom_delivery': False,
            'ExchangedDocument_vals': self._get_exchanged_document_vals(invoice),
            'seller_specified_legal_organization': seller_siret,
            'buyer_specified_legal_organization': buyer_siret,
            'ship_to_trade_party': invoice.partner_shipping_id if 'partner_shipping_id' in invoice._fields and invoice.partner_shipping_id
                else invoice.commercial_partner_id,
            # Chorus Pro fields
            'buyer_reference': invoice.buyer_reference if 'buyer_reference' in invoice._fields
                and invoice.buyer_reference else invoice.commercial_partner_id.ref,
            'purchase_order_reference': invoice.purchase_order_reference if 'purchase_order_reference' in invoice._fields
                and invoice.purchase_order_reference else invoice.ref or invoice.name,
            'contract_reference': invoice.contract_reference if 'contract_reference' in invoice._fields and invoice.contract_reference else '',
        }

        # data used for IncludedSupplyChainTradeLineItem / SpecifiedLineTradeSettlement
        for line_vals in template_values['invoice_line_vals_list']:
            line = line_vals['line']
            line_vals['unece_uom_code'] = self._get_uom_unece_code(line)

        # data used for ApplicableHeaderTradeSettlement / ApplicableTradeTax (at the end of the xml)
        for tax_detail_vals in template_values['tax_details']['tax_details'].values():
            # /!\ -0.0 == 0.0 in python but not in XSLT, so it can raise a fatal error when validating the XML
            # if 0.0 is expected and -0.0 is given.
            amount_currency = tax_detail_vals['tax_amount_currency']
            tax_detail_vals['calculated_amount'] = amount_currency if not invoice.currency_id.is_zero(amount_currency) else 0

            if tax_detail_vals.get('tax_category_code') == 'K':
                template_values['intracom_delivery'] = True
            # [BR - IC - 11] - In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14) shall not be blank.
            if tax_detail_vals.get('tax_category_code') == 'K' and not template_values['scheduled_delivery_time']:
                date_range = self._get_invoicing_period(invoice)
                template_values['billing_start'] = min(date_range)
                template_values['billing_end'] = max(date_range)

        # One of the difference between XRechnung and Facturx is the following. Submitting a Facturx to XRechnung
        # validator raises a warning, but submitting a XRechnung to Facturx raises an error.
        supplier = invoice.company_id.partner_id.commercial_partner_id
        if supplier.country_id.code == 'DE':
            template_values['document_context_id'] = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2"
        else:
            template_values['document_context_id'] = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

        # Fixed taxes: add them as charges on the invoice lines
        for line_vals in template_values['invoice_line_vals_list']:
            line_vals['allowance_charge_vals_list'] = []
            for grouping_key, tax_detail in tax_details['tax_details_per_record'][line_vals['line']]['tax_details'].items():
                if grouping_key['amount_type'] == 'fixed':
                    line_vals['allowance_charge_vals_list'].append({
                        'indicator': 'true',
                        'reason': tax_detail['tax_name'],
                        'reason_code': 'AEO',
                        'amount': tax_detail['tax_amount_currency'],
                    })
            sum_fixed_taxes = sum(x['amount'] for x in line_vals['allowance_charge_vals_list'])
            line_vals['line_total_amount'] = line_vals['line'].price_subtotal + sum_fixed_taxes

        # Fixed taxes: set the total adjusted amounts on the document level
        template_values['tax_basis_total_amount'] = tax_details['base_amount_currency']
        template_values['tax_total_amount'] = tax_details['tax_amount_currency']

        return template_values

    def _export_invoice(self, invoice):
        vals = self._export_invoice_vals(invoice)
        errors = [constraint for constraint in self._export_invoice_constraints(invoice, vals).values() if constraint]
        xml_content = self.env['ir.qweb']._render('account_edi_ubl_cii.account_invoice_facturx_export_22', vals)
        return etree.tostring(cleanup_xml_node(xml_content), xml_declaration=True, encoding='UTF-8'), set(errors)

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        logs = []

        if qty_factor == -1:
            logs.append(_("The invoice has been converted into a credit note and the quantities have been reverted."))

        # ==== partner_id ====

        role = invoice.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
        name = self._find_value(f"//ram:{role}/ram:Name", tree)
        mail = self._find_value(f"//ram:{role}//ram:URIID[@schemeID='SMTP']", tree)
        vat = self._find_value(f"//ram:{role}/ram:SpecifiedTaxRegistration/ram:ID[string-length(text()) > 5]", tree)
        phone = self._find_value(f"//ram:{role}/ram:DefinedTradeContact/ram:TelephoneUniversalCommunication/ram:CompleteNumber", tree)
        country_code = self._find_value(f'//ram:{role}/ram:PostalTradeAddress//ram:CountryID', tree)
        self._import_retrieve_and_fill_partner(invoice, name=name, phone=phone, mail=mail, vat=vat, country_code=country_code)

        # ==== currency_id ====

        currency_code_node = tree.find('.//{*}InvoiceCurrencyCode')
        if currency_code_node is not None:
            currency = self.env['res.currency'].with_context(active_test=False).search([
                ('name', '=', currency_code_node.text),
            ], limit=1)
            if currency:
                if not currency.active:
                    logs.append(_("The currency '%s' is not active.", currency.name))
                invoice.currency_id = currency
            else:
                logs.append(_("Could not retrieve currency: %s. Did you enable the multicurrency option and "
                              "activate the currency?", currency_code_node.text))

        # ==== Reference ====

        ref_node = tree.find('./{*}ExchangedDocument/{*}ID')
        if ref_node is not None:
            invoice.ref = ref_node.text

        # ==== Invoice origin ====

        invoice_origin_node = tree.find('./{*}OrderReference/{*}ID')
        if invoice_origin_node is not None:
            invoice.invoice_origin = invoice_origin_node.text

        # === Note/narration ====

        narration = ""
        note_node = tree.find('./{*}ExchangedDocument/{*}IncludedNote/{*}Content')
        if note_node is not None and note_node.text:
            narration += note_node.text + "\n"

        payment_terms_node = tree.find('.//{*}SpecifiedTradePaymentTerms/{*}Description')
        if payment_terms_node is not None and payment_terms_node.text:
            narration += payment_terms_node.text + "\n"

        invoice.narration = narration

        # ==== payment_reference ====

        payment_reference_node = tree.find('.//{*}BuyerOrderReferencedDocument/{*}IssuerAssignedID')
        if payment_reference_node is not None:
            invoice.payment_reference = payment_reference_node.text

        # ==== invoice_date ====

        invoice_date_node = tree.find('./{*}ExchangedDocument/{*}IssueDateTime/{*}DateTimeString')
        if invoice_date_node is not None and invoice_date_node.text:
            date_str = invoice_date_node.text.strip()
            date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
            invoice.invoice_date = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # ==== invoice_date_due ====

        invoice_date_due_node = tree.find('.//{*}SpecifiedTradePaymentTerms/{*}DueDateDateTime/{*}DateTimeString')
        if invoice_date_due_node is not None and invoice_date_due_node.text:
            date_str = invoice_date_due_node.text.strip()
            date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
            invoice.invoice_date_due = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # ==== invoice_line_ids: AllowanceCharge (document level) ====

        logs += self._import_fill_invoice_allowance_charge(tree, invoice, qty_factor)

        # ==== Prepaid amount ====

        prepaid_node = tree.find('.//{*}ApplicableHeaderTradeSettlement/'
                                 '{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TotalPrepaidAmount')
        logs += self._import_log_prepaid_amount(invoice, prepaid_node, qty_factor)

        # ==== invoice_line_ids ====

        line_nodes = tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')
        if line_nodes is not None:
            for invl_el in line_nodes:
                invoice_line = invoice.invoice_line_ids.create({'move_id': invoice.id})
                invl_logs = self._import_fill_invoice_line_form(invoice.journal_id, invl_el, invoice, invoice_line, qty_factor)
                logs += invl_logs

        return logs

    def _import_fill_invoice_line_form(self, journal, tree, invoice_form, invoice_line, qty_factor):
        logs = []

        # Product.
        name = self._find_value('.//ram:SpecifiedTradeProduct/ram:Name', tree)
        invoice_line.product_id = self.env['product.product']._retrieve_product(
            default_code=self._find_value('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', tree),
            name=name,
            barcode=self._find_value('.//ram:SpecifiedTradeProduct/ram:GlobalID', tree)
        )
        # force original line description instead of the one copied from product's Sales Description
        if name:
            invoice_line.name = name

        xpath_dict = {
            'basis_qty': [
                './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}BasisQuantity',
                './{*}SpecifiedLineTradeAgreement/{*}NetPriceProductTradePrice/{*}BasisQuantity'
            ],
            'gross_price_unit': './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}ChargeAmount',
            'rebate': './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}AppliedTradeAllowanceCharge/{*}ActualAmount',
            'net_price_unit': './{*}SpecifiedLineTradeAgreement/{*}NetPriceProductTradePrice/{*}ChargeAmount',
            'billed_qty': './{*}SpecifiedLineTradeDelivery/{*}BilledQuantity',
            'allowance_charge': './/{*}SpecifiedLineTradeSettlement/{*}SpecifiedTradeAllowanceCharge',
            'allowance_charge_indicator': './{*}ChargeIndicator/{*}Indicator',
            'allowance_charge_amount': './{*}ActualAmount',
            'allowance_charge_reason': './{*}Reason',
            'allowance_charge_reason_code': './{*}ReasonCode',
            'line_total_amount': './{*}SpecifiedLineTradeSettlement/{*}SpecifiedTradeSettlementLineMonetarySummation/{*}LineTotalAmount',
        }
        inv_line_vals = self._import_fill_invoice_line_values(tree, xpath_dict, invoice_line, qty_factor)
        # retrieve tax nodes
        tax_nodes = tree.findall('.//{*}ApplicableTradeTax/{*}RateApplicablePercent')
        return self._import_fill_invoice_line_taxes(tax_nodes, invoice_line, inv_line_vals, logs)

    # -------------------------------------------------------------------------
    # IMPORT : helpers
    # -------------------------------------------------------------------------

    def _get_import_document_amount_sign(self, tree):
        """
        In factur-x, an invoice has code 380 and a credit note has code 381. However, a credit note can be expressed
        as an invoice with negative amounts. For this case, we need a factor to take the opposite of each quantity
        in the invoice.
        """
        move_type_code = tree.find('.//{*}ExchangedDocument/{*}TypeCode')
        if move_type_code is None:
            return None, None
        if move_type_code.text == '381':
            return 'refund', 1
        if move_type_code.text == '380':
            amount_node = tree.find('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TaxBasisTotalAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'refund', -1
            return 'invoice', 1
