# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip

from base64 import b64decode, b64encode
from lxml import etree
from markupsafe import Markup

from odoo import Command, api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _l10n_hu_edi_parse_digest_response(self, response_xml, company):
        digests = []
        for digest in response_xml.iterfind('{*}invoiceDigestResult/{*}invoiceDigest'):
            invoice_number = digest.findtext('{*}invoiceNumber')
            batch_index = digest.findtext('{*}batchIndex')
            ref = f'{invoice_number}-{batch_index}' if batch_index else invoice_number

            supplier_tax_number = digest.findtext('{*}supplierTaxNumber')
            supplier_group_member_tax_number = digest.findtext('{*}supplierGroupMemberTaxNumber')
            taxpayer_id = supplier_group_member_tax_number or supplier_tax_number

            move_domain = [
                *self._check_company_domain(company),
                ('move_type', 'in', self.get_purchase_types()),
                ('ref', '=', ref),
                ('partner_id.vat', '=ilike', f'{taxpayer_id}%'),
            ]
            # If the invoice is already in the system, we skip it to avoid duplicates.
            # We can't use l10n_hu_eu_vat in the domain because it is computed and not stored,
            # So we first fetch all likely vat matches and then filter using l10n_hu_eu_vat.
            if self.search(move_domain).filtered(lambda m: (m.partner_id.l10n_hu_eu_vat or '')[2:] == taxpayer_id):
                continue

            query_invoice_data_params = {
                'invoiceNumber': invoice_number,
                'invoiceDirection': 'INBOUND',
                'batchIndex': batch_index,
                'supplierTaxNumber': supplier_tax_number,
            }

            digests.append(query_invoice_data_params)

        return digests

    @api.model
    def _l10n_hu_edi_parse_query_invoice_data_response(self, response_xml, company=None):
        if response_xml.find('{*}invoiceDataResult') is None:
            return [], []
        invoice_data = b64decode(response_xml.findtext('{*}invoiceDataResult/{*}invoiceData'))
        if response_xml.findtext('{*}invoiceDataResult/{*}compressedContentIndicator') == 'true':
            invoice_data = gzip.decompress(invoice_data)

        audit_data = response_xml.find('{*}invoiceDataResult/{*}auditData')
        move_vals = {
            'l10n_hu_edi_transaction_code': audit_data.findtext('{*}transactionId'),
            'l10n_hu_edi_batch_upload_index': int(audit_data.findtext('{*}index')),
            'l10n_hu_edi_send_time': audit_data.findtext('{*}insdate').rstrip('Z').replace('T', ' '),
        }

        return self._l10n_hu_edi_parse_invoice_data_xml(etree.fromstring(invoice_data), move_vals, company)

    @api.model
    def _l10n_hu_edi_parse_invoice_data_xml(self, invoice_data_xml, common_move_vals=None, company=None):
        if common_move_vals is None:
            common_move_vals = {}
        common_move_vals.update({
            'ref': invoice_data_xml.findtext('{*}invoiceNumber'),
            'invoice_date': invoice_data_xml.findtext('{*}invoiceIssueDate'),
            'l10n_hu_edi_attachment': b64encode(etree.tostring(invoice_data_xml)),
        })
        moves_vals_list = []
        post_process_data_list = []

        if (invoice_xml := invoice_data_xml.find('{*}invoiceMain/{*}invoice')) is not None:
            move_vals, post_process_data = self._l10n_hu_edi_parse_invoice_xml(invoice_xml, company)
            move_vals.update(common_move_vals)
            moves_vals_list.append(move_vals)
            post_process_data_list.append(post_process_data)
        else:
            for batch_invoice in invoice_data_xml.iterfind('{*}invoiceMain/{*}batchInvoice'):
                move_vals, post_process_data = self._l10n_hu_edi_parse_invoice_xml(batch_invoice.find('{*}invoice'), company)
                move_vals.update({
                    **common_move_vals,
                    'ref': f"{common_move_vals['ref']}-{batch_invoice.findtext('{*}batchIndex')}",
                })
                moves_vals_list.append(move_vals)
                post_process_data_list.append(post_process_data)

        return moves_vals_list, post_process_data_list

    @api.model
    def _l10n_hu_edi_parse_invoice_xml(self, invoice_xml, company):
        """ Returns a tuple of (move_vals, post_process_data)

        :return: tuple(move_vals, post_process_data)
            * move_vals: dict of values to create an `account.move`.
            * post_process_data: dict containing additional data used during
            move post-processing, with the following shape:
                - gross_total (float): Gross total parsed from the XML.
                - missing_taxes_error (Markup | None): HTML formatted message
                listing missing taxes, if any.
        """
        def parse_vat(tax_number_xml):
            if tax_number_xml is None:
                return

            parts = [
                tax_number_xml.findtext('{*}taxpayerId'),
                tax_number_xml.findtext('{*}vatCode'),
                tax_number_xml.findtext('{*}countyCode'),
            ]

            return '-'.join(filter(None, parts))

        def _import_retrieve_tax_plan(tax_values):
            domain = [('price_include', '=', tax_values.get('price_include'))]
            if l10n_hu_tax_type := tax_values.get('l10n_hu_tax_type'):
                domain.append(('l10n_hu_tax_type', '=', l10n_hu_tax_type))
            return {'criteria': [{'domain': domain}]}

        def _import_retrieve_product_from_code_and_category(product_values):
            l10n_hu_product_code_type = product_values.get('l10n_hu_product_code_type')
            l10n_hu_product_code = product_values.get('l10n_hu_product_code')
            if not (l10n_hu_product_code_type and l10n_hu_product_code):
                return
            return {'criteria': [{'domain': [
                ('l10n_hu_product_code_type', '=', l10n_hu_product_code_type),
                ('l10n_hu_product_code', '=', l10n_hu_product_code),
            ]}]}

        company = company or self.env.company

        invoice_head = invoice_xml.find('{*}invoiceHead')
        invoice_detail = invoice_head.find('{*}invoiceDetail')
        invoice_category = invoice_detail.findtext('{*}invoiceCategory')

        invoice_reference = invoice_xml.find('{*}invoiceReference')

        if invoice_category == 'SIMPLIFIED':
            gross_total = sum(
                float(summary_simplified.findtext('{*}vatContentGrossAmount'))
                for summary_simplified in invoice_xml.iterfind('{*}invoiceSummary/{*}summarySimplified')
            )
        else:
            gross_total = (
                float(invoice_xml.findtext('{*}invoiceSummary/{*}summaryNormal/{*}invoiceNetAmount')) +
                float(invoice_xml.findtext('{*}invoiceSummary/{*}summaryNormal/{*}invoiceVatAmount'))
            )

        move_type = 'in_invoice' if (invoice_reference is None) or (gross_total >= 0) else 'in_refund'

        supplier_info = invoice_head.find('{*}supplierInfo')
        taxpayer_id = (
            supplier_info.findtext('{*}groupMemberTaxNumber/{*}taxpayerId') or
            supplier_info.findtext('{*}supplierTaxNumber/{*}taxpayerId')
        )
        partner = self.env['res.partner'].search([
            *self.env['res.partner']._check_company_domain(company),
            ('vat', '=ilike', f'{taxpayer_id}%'),
        ]).filtered(lambda p: (p.l10n_hu_eu_vat or '')[2:] == taxpayer_id)[:1]
        if not partner:
            supplier_tax_number = parse_vat(supplier_info.find('{*}supplierTaxNumber'))
            supplier_group_member_tax_number = parse_vat(supplier_info.find('{*}groupMemberTaxNumber'))
            supplier_address = supplier_info.find('{*}supplierAddress/{*}simpleAddress')
            if supplier_address is None:
                supplier_address = supplier_info.find('{*}supplierAddress/{*}detailedAddress')

            country = self.env.ref(f'base.{supplier_address.findtext("{*}countryCode").lower()}', raise_if_not_found=False)
            partner = self.env['res.partner'].create({
                'name': supplier_info.findtext('{*}supplierName'),
                'vat': supplier_group_member_tax_number or supplier_tax_number,
                'l10n_hu_group_vat': supplier_group_member_tax_number and supplier_tax_number,
                'country_id': country.id if country else None,
                'zip': supplier_address.findtext('{*}postalCode'),
                'city': supplier_address.findtext('{*}city'),
                'street': supplier_address.findtext('{*}additionalAddressDetail') or supplier_address.findtext('{*}streetName'),
                'is_company': True,
                'company_id': company.id,
            })

            if supplier_bank_account_number := supplier_info.findtext('{*}supplierBankAccountNumber'):
                partner.with_context(default_journal_id=None).bank_ids = [Command.create({'acc_number': supplier_bank_account_number})]

        currency = self.env.ref(f'base.{invoice_detail.findtext("{*}currencyCode")}', raise_if_not_found=False)
        move_vals = {
            'company_id': company.id,
            'l10n_hu_invoice_chain_index': -1 if invoice_reference is None else int(invoice_reference.findtext('{*}modificationIndex')),
            'l10n_hu_payment_mode': invoice_detail.findtext('{*}paymentMethod'),
            'delivery_date': invoice_detail.findtext('{*}invoiceDeliveryDate'),
            'invoice_date_due': invoice_detail.findtext('{*}paymentDate'),
            'currency_id': currency.id if currency else None,
            'invoice_currency_rate': float(invoice_detail.findtext('{*}exchangeRate')),
            'move_type': move_type,
            'partner_id': partner.id,
            'invoice_line_ids': [],
        }

        if invoice_reference is not None:
            original_invoice_number = invoice_reference.findtext('{*}originalInvoiceNumber')
            original_invoice = self.search([
                *self._check_company_domain(company),
                ('ref', '=', original_invoice_number),
                ('partner_id', '=', partner.id),
            ], limit=1)
            if original_invoice:
                original_invoice_field = 'reversed_entry_id' if move_type == 'in_refund' else 'debit_origin_id'
                move_vals[original_invoice_field] = original_invoice.id

        if move_type == 'in_refund':
            account_number_path = '{*}customerInfo/{*}customerBankAccountNumber'
            bank_partner = company.partner_id
        else:
            account_number_path = '{*}supplierInfo/{*}supplierBankAccountNumber'
            bank_partner = partner
        account_number = invoice_head.findtext(account_number_path)
        if account_number:
            partner_bank = self.env['res.partner.bank'].search([
                *self.env['res.partner.bank']._check_company_domain(company),
                ('acc_number', '=', account_number),
                ('partner_id', '=', bank_partner.id),
            ], limit=1)
            if not partner_bank:
                partner_bank = self.env['res.partner.bank'].with_context(default_journal_id=None).create({
                    'acc_number': account_number,
                    'partner_id': bank_partner.id,
                })
            move_vals['partner_bank_id'] = partner_bank.id

        lines_vals = []
        lines_tax_values = []
        lines_product_values = []
        has_downpayment_field = 'is_downpayment' in self.env['account.move.line']._fields
        for line in invoice_xml.iterfind('{*}invoiceLines/{*}line'):
            quantity = float(line.findtext('{*}quantity') or 1)
            discount = float(line.findtext('{*}lineDiscountData/{*}discountRate') or 0) * 100
            amounts = line.find('{*}lineAmountsSimplified' if invoice_category == 'SIMPLIFIED' else '{*}lineAmountsNormal')
            skip_tax = False
            price_unit = float(line.findtext('{*}unitPrice') or 0)
            if not price_unit:
                if invoice_category == 'SIMPLIFIED':
                    price_unit = float(amounts.findtext('{*}lineGrossAmountSimplified') or 0)
                else:
                    net = float(amounts.findtext('{*}lineNetAmountData/{*}lineNetAmount') or 0)
                    vat = float(amounts.findtext('{*}lineVatData/{*}lineVatAmount') or 0)
                    gross = amounts.findtext('{*}lineGrossAmountData/{*}lineGrossAmountNormal')
                    if not net and vat:                                               # net:0, vat:x, gross:x
                        price_unit = vat
                        skip_tax = True
                    elif net and vat and (gross is not None) and (not float(gross)):  # net:-x, vat: x, gross:0
                        price_unit = 0
                    else:                                                             # (net:x, vat:0/y) OR (net:0, vat:0)
                        price_unit = net
                price_unit += price_unit * discount / 100
                quantity = 1

            line_vals = {
                'display_type': 'product',
                'name': line.findtext('{*}lineDescription'),
                'discount': discount,
                'quantity': abs(quantity) if move_type == 'in_refund' else quantity,
                'price_unit': abs(price_unit) if move_type == 'in_refund' else price_unit
            }

            if has_downpayment_field:
                line_vals['is_downpayment'] = (line.findtext('{*}advanceData/{*}advanceIndicator') == 'true')

            product_values = {'name': line_vals['name']}
            if (product_codes := line.find('{*}productCodes')) is not None:
                for product_code in product_codes.iterfind('{*}productCode'):
                    if product_code_own_value := product_code.findtext('{*}productCodeOwnValue'):
                        product_values['default_code'] = product_code_own_value
                    else:
                        product_values.update({
                            'l10n_hu_product_code_type': product_code.findtext('{*}productCodeCategory'),
                            'l10n_hu_product_code': product_code.findtext('{*}productCodeValue'),
                        })
            lines_product_values.append(product_values)

            if unit_of_measure := line.findtext('{*}unitOfMeasure'):
                if unit_of_measure == 'OWN':
                    uom_name = line.findtext('{*}unitOfMeasureOwn')
                    uom_domain = [('name', '=', uom_name)]
                else:
                    uom_domain = [('l10n_hu_edi_code', '=', unit_of_measure)]

                if uom := self.env['uom.uom'].search(uom_domain, limit=1):
                    line_vals['product_uom_id'] = uom.id

            if not skip_tax:
                line_vat_rate = amounts.find('{*}lineVatRate')
                l10n_hu_tax_type = rate = None
                if vat_percentage := line_vat_rate.findtext('{*}vatPercentage'):
                    rate = vat_percentage
                    l10n_hu_tax_type = 'VAT'
                elif (vat_exemption := line_vat_rate.find('{*}vatExemption')) is not None:
                    l10n_hu_tax_type = vat_exemption.findtext('{*}case')
                elif (vat_out_of_scope := line_vat_rate.find('{*}vatOutOfScope')) is not None:
                    l10n_hu_tax_type = vat_out_of_scope.findtext('{*}case')
                elif line_vat_rate.findtext('{*}vatDomesticReverseCharge') == 'true':
                    l10n_hu_tax_type = 'DOMESTIC_REVERSE'
                elif margin_scheme_indicator := line_vat_rate.findtext('{*}marginSchemeIndicator'):
                    l10n_hu_tax_type = margin_scheme_indicator
                elif (vat_amount_mismatch := line_vat_rate.find('{*}vatAmountMismatch')) is not None:
                    l10n_hu_tax_type = vat_amount_mismatch.findtext('{*}case')
                    rate = vat_amount_mismatch.findtext('{*}vatRate/{*}vatPercentage')
                elif line_vat_rate.findtext('{*}noVatCharge') == 'true':
                    l10n_hu_tax_type = 'NO_VAT'
                else:
                    rate = line_vat_rate.findtext('{*}vatContent')

                tax_values = {
                    'amount_type': 'percent',
                    'type_tax_use': 'purchase',
                    'amount': float(rate) * 100 if rate else 0.0,
                    'price_include': invoice_category == 'SIMPLIFIED',
                    'l10n_hu_tax_type': l10n_hu_tax_type,
                    'label': line_vals['name'],
                }
                lines_tax_values.append(tax_values)
            else:
                lines_tax_values.append(None)

            lines_vals.append(line_vals)

        self.env['account.tax']._import_retrieve_tax(
            search_plan=[_import_retrieve_tax_plan],
            company=company,
            tax_values_list=filter(None, lines_tax_values),
        )
        self.env['product.product']._import_retrieve_product(
            search_plan=[
                self.env['product.product']._import_retrieve_product_from_default_code,
                self.env['product.product']._import_retrieve_product_from_name,
                _import_retrieve_product_from_code_and_category,
            ],
            company=company,
            product_values_list=lines_product_values,
        )
        no_tax_logs = []
        for line_vals, tax_values, product_values in zip(lines_vals, lines_tax_values, lines_product_values):
            if tax_values is not None:
                if tax := tax_values.get('tax'):
                    line_vals['tax_ids'] = [Command.set([tax.id])]
                else:
                    tax_label = ' '.join(filter(None, [
                        tax_values['amount'] and f"{tax_values['amount']}%",
                        tax_values.get('l10n_hu_tax_type'),
                    ]))
                    no_tax_logs.append(self.env._(
                        "Could not retrieve the tax: %(tax_label)s for line '%(line)s'.",
                        tax_label=tax_label,
                        line=tax_values.get('label'),
                    ))
            if product := product_values.get('product'):
                line_vals['product_id'] = product.id
            move_vals['invoice_line_ids'].append(Command.create(line_vals))

        post_process_data = {
            'gross_total': gross_total,
            'missing_taxes_error': Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in no_tax_logs) if no_tax_logs else None,
        }

        return move_vals, post_process_data

    @api.model
    def _l10n_hu_edi_post_process_data(self, moves, post_process_data_list):
        for move, post_process_data in zip(moves, post_process_data_list):
            if move.currency_id.compare_amounts(post_process_data['gross_total'], -move.amount_total_in_currency_signed) != 0:
                move.l10n_hu_edi_messages = {
                    'error_title': self.env._("Amount mismatch detected."),
                    'errors': [self.env._("The gross total on the bill received from NAV and computed is not the same. Please check XML file in 'NAV 3.0' tab.")],
                    'blocking_level': 'warning',
                }

            if missing_taxes_error := post_process_data.get('missing_taxes_error'):
                move.message_post(body=missing_taxes_error)

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if (
            self.country_code == 'HU'
            and file_data['xml_tree'] is not None
            and (root := etree.QName(file_data['xml_tree']).localname) in ('InvoiceData', 'QueryInvoiceDataResponse')
        ):
            def decoder(invoice, file_data, new):
                xml_tree = file_data['xml_tree']
                if root == 'InvoiceData':
                    moves_vals_list, post_process_data_list = self._l10n_hu_edi_parse_invoice_data_xml(xml_tree)
                elif root == 'QueryInvoiceDataResponse':
                    moves_vals_list, post_process_data_list = self._l10n_hu_edi_parse_query_invoice_data_response(xml_tree)
                invoice.write(moves_vals_list[0])
                moves = invoice + self.create(moves_vals_list[1:])
                self._l10n_hu_edi_post_process_data(moves, post_process_data_list)

            return {
                'priority': 20,
                'decoder': decoder,
            }

        return super()._get_edi_decoder(file_data, new=new)
