# -*- coding: utf-8 -*-
from hashlib import sha256
from base64 import b64encode
from lxml import etree
from odoo import models, fields
from odoo.modules.module import get_module_resource
import re

TAX_EXEMPTION_CODES = ['VATEX-SA-29', 'VATEX-SA-29-7', 'VATEX-SA-30']
TAX_ZERO_RATE_CODES = ['VATEX-SA-32', 'VATEX-SA-33', 'VATEX-SA-34-1', 'VATEX-SA-34-2', 'VATEX-SA-34-3', 'VATEX-SA-34-4',
                       'VATEX-SA-34-5', 'VATEX-SA-35', 'VATEX-SA-36', 'VATEX-SA-EDU', 'VATEX-SA-HEA']

PAYMENT_MEANS_CODE = {
    'bank': 42,
    'card': 48,
    'cash': 10,
    'transfer': 30,
    'unknown': 1
}


class AccountEdiXmlUBL21Zatca(models.AbstractModel):
    _name = "account.edi.xml.ubl_21.zatca"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (ZATCA)"

    def _l10n_sa_get_namespaces(self):
        """
            Namespaces used in the final UBL declaration, required to canonalize the finalized XML document of the Invoice
        """
        return {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#'
        }

    def _l10n_sa_generate_invoice_xml_sha(self, xml_content):
        """
            Transform, canonicalize then hash the invoice xml content using the SHA256 algorithm,
            then return the hashed content
        """

        def _canonicalize_xml(content):
            """
                Canonicalize XML content using the c14n method. The specs mention using the c14n11 canonicalization,
                which is simply calling etree.tostring and setting the method argument to 'c14n'. There are minor
                differences between c14n11 and c14n canonicalization algorithms, but for the purpose of ZATCA signing,
                c14n is enough
            """
            return etree.tostring(content, method="c14n", exclusive=False, with_comments=False,
                                  inclusive_ns_prefixes=self._l10n_sa_get_namespaces())

        def _transform_and_canonicalize_xml(content):
            """ Transform XML content to remove certain elements and signatures using an XSL template """
            invoice_xsl = etree.parse(get_module_resource('l10n_sa_edi', 'data', 'pre-hash_invoice.xsl'))
            transform = etree.XSLT(invoice_xsl)
            return _canonicalize_xml(transform(content))

        root = etree.fromstring(xml_content)
        # Transform & canonicalize the XML content
        transformed_xml = _transform_and_canonicalize_xml(root)
        # Get the SHA256 hashed value of the XML content
        return sha256(transformed_xml)

    def _l10n_sa_generate_invoice_xml_hash(self, xml_content, mode='hexdigest'):
        """
            Generate the b64 encoded sha256 hash of a given xml string:
                - First: Transform the xml content using a pre-hash_invoice.xsl file
                - Second: Canonicalize the transformed xml content using the c14n method
                - Third: hash the canonicalized content using the sha256 algorithm then encode it into b64 format
        """
        xml_sha = self._l10n_sa_generate_invoice_xml_sha(xml_content)
        if mode == 'hexdigest':
            xml_hash = xml_sha.hexdigest().encode()
        elif mode == 'digest':
            xml_hash = xml_sha.digest()
        return b64encode(xml_hash)

    def _l10n_sa_get_previous_invoice_hash(self, invoice):
        """ Function that returns the Base 64 encoded SHA256 hash of the previously submitted invoice """
        if invoice.company_id.l10n_sa_api_mode == 'sandbox' or not invoice.journal_id.l10n_sa_latest_submission_hash:
            # If no invoice, or if using Sandbox, return the b64 encoded SHA256 value of the '0' character
            return "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
        return invoice.journal_id.l10n_sa_latest_submission_hash

    def _get_delivery_vals_list(self, invoice):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        shipping_address = False
        if 'partner_shipping_id' in invoice._fields and invoice.partner_shipping_id:
            shipping_address = invoice.partner_shipping_id
        return [{'actual_delivery_date': invoice.l10n_sa_delivery_date,
                 'delivery_address_vals': self._get_partner_address_vals(shipping_address) if shipping_address else {},}]

    def _get_partner_party_identification_vals_list(self, partner):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        return [{
            'id_attrs': {'schemeID': partner.l10n_sa_additional_identification_scheme},
            'id': partner.l10n_sa_additional_identification_number if partner.l10n_sa_additional_identification_scheme != 'TIN' else partner.vat
        }]

    def _l10n_sa_get_payment_means_code(self, invoice):
        """ Return payment means code to be used to set the value on the XML file """
        return 'unknown'

    def _get_invoice_payment_means_vals_list(self, invoice):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        res = super()._get_invoice_payment_means_vals_list(invoice)
        res[0]['payment_means_code'] = PAYMENT_MEANS_CODE.get(self._l10n_sa_get_payment_means_code(invoice), PAYMENT_MEANS_CODE['unknown'])
        res[0]['payment_means_code_attrs'] = {'listID': 'UN/ECE 4461'}
        res[0]['adjustment_reason'] = invoice.ref
        return res

    def _get_partner_address_vals(self, partner):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        return {
            **super()._get_partner_address_vals(partner),
            'building_number': partner.l10n_sa_edi_building_number,
            'neighborhood': partner.street2,
            'plot_identification': partner.l10n_sa_edi_plot_identification,
        }

    def _export_invoice_filename(self, invoice):
        """
            Generate the name of the invoice XML file according to ZATCA business rules:
            Seller Vat Number (BT-31), Date (BT-2), Time (KSA-25), Invoice Number (BT-1)
        """
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        invoice_number = re.sub("[^a-zA-Z0-9 -]", "-", invoice.name)
        invoice_date = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), invoice.l10n_sa_confirmation_datetime)
        return '%s_%s_%s.xml' % (vat, invoice_date.strftime('%Y%m%dT%H%M%S'), invoice_number)

    def _l10n_sa_get_invoice_transaction_code(self, invoice):
        """
            Returns the transaction code string to be inserted in the UBL file follows the following format:
                - NNPNESB, in compliance with KSA Business Rule KSA-2, where:
                    - NN (positions 1 and 2) = invoice subtype:
                        - 01 for tax invoice
                        - 02 for simplified tax invoice
                    - E (position 5) = Exports invoice transaction, 0 for false, 1 for true
        """
        return '0%s00%s00' % (
            '2' if invoice._l10n_sa_is_simplified() else '1',
            '1' if invoice.commercial_partner_id.country_id != invoice.company_id.country_id and not invoice._l10n_sa_is_simplified() else '0'
        )

    def _l10n_sa_get_invoice_type(self, invoice):
        """
            Returns the invoice type string to be inserted in the UBL file
                - 383: Debit Note
                - 381: Credit Note
                - 388: Invoice
        """
        return 383 if invoice.debit_origin_id else 381 if invoice.move_type == 'out_refund' else 388

    def _l10n_sa_get_billing_reference_vals(self, invoice):
        """ Get the billing reference vals required to render the BillingReference for credit/debit notes """
        if self._l10n_sa_get_invoice_type(invoice) != 388:
            return {
                'id': (invoice.reversed_entry_id.name or invoice.ref) if invoice.move_type == 'out_refund' else invoice.debit_origin_id.name,
                'issue_date': None,
            }
        return {}

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        """
            Override to return an empty list if the partner is a customer and their country is not KSA.
            This is according to KSA Business Rule BR-KSA-46 which states that in the case of Export Invoices,
            the buyer VAT registration number or buyer group VAT registration number must not exist in the Invoice
        """
        if role != 'customer' or partner.country_id.code == 'SA':
            return super()._get_partner_party_tax_scheme_vals_list(partner, role)
        return []

    def _apply_invoice_tax_filter(self, tax_values):
        """ Override to filter out withholding tax """
        res = not tax_values['tax_id'].l10n_sa_is_retention
        # If the move that is being sent is not a down payment invoice, and the sale module is installed
        # we need to make sure the line is neither retention, nor a down payment line
        if not tax_values['base_line_id'].move_id._is_downpayment():
            return not tax_values['tax_id'].l10n_sa_is_retention and not tax_values['base_line_id']._get_downpayment_lines()
        return res

    def _apply_invoice_line_filter(self, invoice_line):
        """ Override to filter out down payment lines """
        if not invoice_line.move_id._is_downpayment():
            return not invoice_line._get_downpayment_lines()
        return True

    def _l10n_sa_get_prepaid_amount(self, invoice, vals):
        """ Calculate the down-payment amount according to ZATCA rules """
        downpayment_lines = False if invoice._is_downpayment() else invoice.line_ids.filtered(lambda l: l._get_downpayment_lines())
        if downpayment_lines:
            tax_vals = invoice._prepare_edi_tax_details(filter_to_apply=lambda t: not t['tax_id'].l10n_sa_is_retention)
            base_amount = abs(sum(tax_vals['invoice_line_tax_details'][l]['base_amount_currency'] for l in downpayment_lines))
            tax_amount = abs(sum(tax_vals['invoice_line_tax_details'][l]['tax_amount_currency'] for l in downpayment_lines))
            return {
                'total_amount': base_amount + tax_amount,
                'base_amount': base_amount,
                'tax_amount': tax_amount
            }

    def _l10n_sa_get_monetary_vals(self, invoice, vals):
        """ Calculate the invoice monteray amount values, including prepaid amounts (down payment) """
        # We use base_amount_currency + tax_amount_currency instead of amount_total because we do not want to include
        # withholding tax amounts in our calculations
        total_amount = abs(vals['taxes_vals']['base_amount_currency'] + vals['taxes_vals']['tax_amount_currency'])

        tax_inclusive_amount = total_amount
        tax_exclusive_amount = abs(vals['taxes_vals']['base_amount_currency'])
        prepaid_amount = 0
        payable_amount = total_amount

        # - When we calculate the tax values, we filter out taxes and invoice lines linked to downpayments.
        #   As such, when we calculate the TaxInclusiveAmount, it already accounts for the tax amount of the downpayment
        #   Same goes for the TaxExclusiveAmount, and we do not need to add the Tax amount of the downpayment
        # - The payable amount does not account for the tax amount of the downpayment, so we add it
        downpayment_vals = self._l10n_sa_get_prepaid_amount(invoice, vals)

        if downpayment_vals:
            # Makes no sense, but according to ZATCA, if there is a downpayment, the TotalInclusiveAmount
            # should include the total amount of the invoice (including downpayment amount) PLUS the downpayment
            # total amount, AGAIN.
            prepaid_amount = tax_inclusive_amount + downpayment_vals['total_amount']
            payable_amount = - downpayment_vals['total_amount']

        return {
            'tax_inclusive_amount': tax_inclusive_amount,
            'tax_exclusive_amount': tax_exclusive_amount,
            'prepaid_amount': prepaid_amount,
            'payable_amount': payable_amount
        }

    def _get_tax_category_list(self, invoice, taxes):
        """ Override to filter out withholding taxes """
        non_retention_taxes = taxes.filtered(lambda t: not t.l10n_sa_is_retention)
        return super()._get_tax_category_list(invoice, non_retention_taxes)

    def _export_invoice_vals(self, invoice):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'main_template': 'account_edi_ubl_cii.ubl_20_Invoice',
            'InvoiceType_template': 'l10n_sa_edi.ubl_21_InvoiceType_zatca',
            'InvoiceLineType_template': 'l10n_sa_edi.ubl_21_InvoiceLineType_zatca',
            'AddressType_template': 'l10n_sa_edi.ubl_21_AddressType_zatca',
            'PartyType_template': 'l10n_sa_edi.ubl_21_PartyType_zatca',
            'TaxTotalType_template': 'l10n_sa_edi.ubl_21_TaxTotalType_zatca',
            'PaymentMeansType_template': 'l10n_sa_edi.ubl_21_PaymentMeansType_zatca',
        })

        vals['vals'].update({
            'profile_id': 'reporting:1.0',
            'invoice_type_code_attrs': {'name': self._l10n_sa_get_invoice_transaction_code(invoice)},
            'invoice_type_code': self._l10n_sa_get_invoice_type(invoice),
            'issue_date': fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'),
                                                            invoice.l10n_sa_confirmation_datetime),
            'previous_invoice_hash': self._l10n_sa_get_previous_invoice_hash(invoice),
            'billing_reference_vals': self._l10n_sa_get_billing_reference_vals(invoice),
            'tax_total_vals': self._l10n_sa_get_additional_tax_total_vals(invoice, vals),
            # Due date is not required for ZATCA UBL 2.1
            'due_date': None,
        })

        vals['vals']['legal_monetary_total_vals'].update(self._l10n_sa_get_monetary_vals(invoice, vals))

        return vals

    def _l10n_sa_get_additional_tax_total_vals(self, invoice, vals):
        """
            For ZATCA, an additional TaxTotal element needs to be included in the UBL file
            (Only for the Invoice, not the lines)

            If the invoice is in a different currency from the one set on the company (SAR), then the additional
            TaxAmount element needs to hold the tax amount converted to the company's currency.

            Business Rules: BT-110 & BT-111
        """
        curr_amount = abs(vals['taxes_vals']['tax_amount_currency'])
        if invoice.currency_id != invoice.company_currency_id:
            curr_amount = abs(vals['taxes_vals']['tax_amount'])
        return vals['vals']['tax_total_vals'] + [{
            'currency': invoice.company_currency_id,
            'currency_dp': invoice.company_currency_id.decimal_places,
            'tax_amount': curr_amount,
        }]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals['sellers_item_identification_vals'] = {'id': line.product_id.code or line.product_id.default_code}
        return vals

    def _l10n_sa_get_line_prepayment_vals(self, line, taxes_vals):
        """
            If an invoice line is linked to a down payment invoice, we need to return the proper values
            to be included in the UBL
        """
        if not line.move_id._is_downpayment() and line.sale_line_ids and all(sale_line.is_downpayment for sale_line in line.sale_line_ids):
            prepayment_move_id = line.sale_line_ids.invoice_lines.move_id.filtered(lambda m: m._is_downpayment())
            return {
                'prepayment_id': prepayment_move_id.name,
                'issue_date': fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'),
                                                                prepayment_move_id.l10n_sa_confirmation_datetime),
                'document_type_code': 386
            }
        return {}

    def _get_invoice_line_vals(self, line, taxes_vals):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """

        def grouping_key_generator(tax_values):
            tax = tax_values['tax_id']
            tax_category_vals = self._get_tax_category_list(line.move_id, tax)[0]
            return {
                'tax_category_id': tax_category_vals['id'],
                'tax_category_percent': tax_category_vals['percent'],
                '_tax_category_vals_': tax_category_vals,
            }

        if not line.move_id._is_downpayment() and line._get_downpayment_lines():
            # When we initially calculate the taxes_vals, we filter out the down payment lines, which means we have no
            # values to set in the TaxableAmount and TaxAmount nodes on the InvoiceLine for the down payment.
            # This means ZATCA will return a warning message for the BR-KSA-80 rule since it cannot calculate the
            # TaxableAmount and the TaxAmount nodes correctly. To avoid this, we re-caclculate the taxes_vals just before
            # we set the values for the down payment line, and we do not pass any filters to the _prepare_edi_tax_details
            # method
            line_taxes = line.move_id._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)
            taxes_vals = line_taxes['invoice_line_tax_details'][line]

        line_vals = super()._get_invoice_line_vals(line, taxes_vals)
        total_amount_sa = abs(taxes_vals['tax_amount_currency'] + taxes_vals['base_amount_currency'])
        extension_amount = abs(line_vals['line_extension_amount'])
        if not line.move_id._is_downpayment() and line._get_downpayment_lines():
            total_amount_sa = extension_amount = 0
            line_vals['price_vals']['price_amount'] = 0
            line_vals['tax_total_vals'][0]['tax_amount'] = 0
            line_vals['prepayment_vals'] = self._l10n_sa_get_line_prepayment_vals(line, taxes_vals)
        line_vals['tax_total_vals'][0]['total_amount_sa'] = total_amount_sa
        line_vals['invoiced_quantity'] = abs(line_vals['invoiced_quantity'])
        line_vals['line_extension_amount'] = extension_amount

        return line_vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        """
            Override to include/update values specific to ZATCA's UBL 2.1 specs.
            In this case, we make sure the tax amounts are always absolute (no negative values)
        """
        res = [{
            'currency': invoice.currency_id,
            'currency_dp': invoice.currency_id.decimal_places,
            'tax_amount': abs(taxes_vals['tax_amount_currency']),
            'tax_subtotal_vals': [{
                'currency': invoice.currency_id,
                'currency_dp': invoice.currency_id.decimal_places,
                'taxable_amount': abs(vals['base_amount_currency']),
                'tax_amount': abs(vals['tax_amount_currency']),
                'percent': vals['_tax_category_vals_']['percent'],
                'tax_category_vals': vals['_tax_category_vals_'],
            } for vals in taxes_vals['tax_details'].values()],
        }]
        return res

    def _get_tax_unece_codes(self, invoice, tax):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """

        def _exemption_reason(code, reason):
            return {
                'tax_category_code': code,
                'tax_exemption_reason_code': reason,
                'tax_exemption_reason': exemption_codes[reason].split(reason)[1].lstrip(),
            }

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if supplier.country_id.code == 'SA':
            if not tax or tax.amount == 0:
                exemption_codes = dict(tax._fields["l10n_sa_exemption_reason_code"]._description_selection(self.env))
                if tax.l10n_sa_exemption_reason_code in TAX_EXEMPTION_CODES:
                    return _exemption_reason('E', tax.l10n_sa_exemption_reason_code)
                elif tax.l10n_sa_exemption_reason_code in TAX_ZERO_RATE_CODES:
                    return _exemption_reason('Z', tax.l10n_sa_exemption_reason_code)
                else:
                    return {
                        'tax_category_code': 'O',
                        'tax_exemption_reason_code': 'Not subject to VAT',
                        'tax_exemption_reason': 'Not subject to VAT',
                    }
            else:
                return {
                    'tax_category_code': 'S',
                    'tax_exemption_reason_code': None,
                    'tax_exemption_reason': None,
                }
        return super()._get_tax_unece_codes(invoice, tax)

    def _get_invoice_payment_terms_vals_list(self, invoice):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        return []
