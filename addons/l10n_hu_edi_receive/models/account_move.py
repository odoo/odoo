# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from datetime import datetime
from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import XML_NAMESPACES


def boolean(value):
    return value.lower() in ('true', '1') if value else False


def parse_vat(tax_number_xml):
    if tax_number_xml is None:
        return

    vat = tax_number_xml.findtext('base:taxpayerId', namespaces=XML_NAMESPACES)
    if vat_code := tax_number_xml.findtext('base:vatCode', namespaces=XML_NAMESPACES):
        vat += '-' + vat_code
    if county_code := tax_number_xml.findtext('base:countyCode', namespaces=XML_NAMESPACES):
        vat += '-' + county_code
    return vat


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hu_edi_state = fields.Selection(selection_add=[
        ('digested', "Digested"),
        ('received', "Received"),
        ('parsed', "Parsed"),
    ])
    l10n_hu_edi_batch_index = fields.Integer(
        string='Index of invoice within a batch modification',
        copy=False,
    )

    @api.depends('name', 'ref')
    def _compute_l10n_hu_edi_attachment_filename(self):
        nav_receiving_moves = self.filtered(lambda m: m.l10n_hu_edi_state in ('digested', 'received', 'parsed'))
        for move in nav_receiving_moves:
            move.l10n_hu_edi_attachment_filename = f'{move.ref.replace("/", "_")}.xml'
        super(AccountMove, self - nav_receiving_moves)._compute_l10n_hu_edi_attachment_filename()

    @api.model
    def _l10n_hu_edi_get_moves_vals_from_digest(self, response_xml):
        moves_vals = []
        for digest in response_xml.iterfind('api:invoiceDigestResult/api:invoiceDigest', namespaces=XML_NAMESPACES):
            invoice_operation = digest.findtext('api:invoiceOperation', namespaces=XML_NAMESPACES)
            if invoice_operation == 'CREATE':
                move_type = 'in_invoice'
            elif invoice_operation == 'STORNO':
                move_type = 'in_refund'
            elif invoice_operation == 'MODIFY':
                invoice_net_amount = digest.findtext('api:invoiceNetAmount', namespaces=XML_NAMESPACES)
                move_type = 'in_refund' if invoice_net_amount and float(invoice_net_amount) < 0 else 'in_invoice'

            l10n_hu_edi_transaction_code = digest.findtext('api:transactionId', namespaces=XML_NAMESPACES)
            l10n_hu_edi_batch_upload_index = int(digest.findtext('api:index', namespaces=XML_NAMESPACES))
            move_domain = [
                ('l10n_hu_edi_transaction_code', '=', l10n_hu_edi_transaction_code),
                ('l10n_hu_edi_batch_upload_index', '=', l10n_hu_edi_batch_upload_index),
                ('company_id', '=', self.env.company.id),
                ('move_type', '=', move_type),
            ]
            if l10n_hu_edi_batch_index := digest.findtext('api:batchIndex', namespaces=XML_NAMESPACES):
                move_domain.append(('l10n_hu_edi_batch_index', '=', int(l10n_hu_edi_batch_index)))
            move = self.env['account.move'].search(move_domain, limit=1)
            if move:
                continue

            supplier_name = digest.findtext('api:supplierName', namespaces=XML_NAMESPACES)
            supplier_tax_number = digest.findtext('api:supplierTaxNumber', namespaces=XML_NAMESPACES)
            supplier_group_member_tax_number = digest.findtext('api:supplierGroupMemberTaxNumber', namespaces=XML_NAMESPACES)
            partner_domain = [('vat', '=ilike', (supplier_group_member_tax_number or supplier_tax_number) + '%')]
            if supplier_group_member_tax_number:
                partner_domain.append(('l10n_hu_group_vat', '=ilike', supplier_tax_number + '%'))
            partner = self.env['res.partner'].search(partner_domain, limit=1)
            if not partner:
                partner_vals = {
                    'name': supplier_name,
                    'vat': supplier_group_member_tax_number or supplier_tax_number,
                }
                if supplier_group_member_tax_number:
                    partner_vals['l10n_hu_group_vat'] = supplier_tax_number
                partner = self.env['res.partner'].create(partner_vals)

            move_vals = {
                'ref': digest.findtext('api:invoiceNumber', namespaces=XML_NAMESPACES),
                'move_type': move_type,
                'l10n_hu_edi_state': 'digested',
                'invoice_date': fields.Date.from_string(digest.findtext('api:invoiceIssueDate', namespaces=XML_NAMESPACES)),
                'partner_id': partner.id,
                'l10n_hu_edi_transaction_code': l10n_hu_edi_transaction_code,
                'l10n_hu_edi_send_time': datetime.fromisoformat(digest.findtext('api:insDate', namespaces=XML_NAMESPACES).replace('Z', '')),
                'l10n_hu_invoice_chain_index': -1 if invoice_operation == 'CREATE' else int(digest.findtext('api:modificationIndex', namespaces=XML_NAMESPACES)),
                'l10n_hu_edi_batch_upload_index': l10n_hu_edi_batch_upload_index,
            }
            if l10n_hu_edi_batch_index:
                move_vals['l10n_hu_edi_batch_index'] = l10n_hu_edi_batch_index
            if l10n_hu_payment_mode := digest.findtext('api:paymentMethod', namespaces=XML_NAMESPACES):
                move_vals['l10n_hu_payment_mode'] = l10n_hu_payment_mode
            if invoice_date_due := digest.findtext('api:paymentDate', namespaces=XML_NAMESPACES):
                move_vals['invoice_date_due'] = fields.Date.from_string(invoice_date_due)
            if delivery_date := digest.findtext('api:invoiceDeliveryDate', namespaces=XML_NAMESPACES):
                move_vals['delivery_date'] = fields.Date.from_string(delivery_date)

            currency_name = digest.findtext('api:currency', namespaces=XML_NAMESPACES)
            currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', currency_name)], limit=1) if currency_name else None
            if currency:
                move_vals['currency_id'] = currency.id

            moves_vals.append(move_vals)

        return moves_vals

    @api.model
    def _l10n_hu_edi_cron_parse_invoice_data(self):
        for move in self.search([('l10n_hu_edi_state', '=', 'received')]):
            move._l10n_hu_edi_parse_invoice_data()

    def _l10n_hu_edi_parse_invoice_data(self):
        self.ensure_one()

        move_vals = {'l10n_hu_edi_state': 'parsed'}
        invoice_tree = etree.fromstring(b64decode(self.l10n_hu_edi_attachment))
        invoice_path = 'data:invoiceMain/data:batchInvoice/data:invoice' if self.l10n_hu_edi_batch_index else 'data:invoiceMain/data:invoice'
        invoice = invoice_tree.find(invoice_path, namespaces=XML_NAMESPACES)

        invoice_head = invoice.find('data:invoiceHead', namespaces=XML_NAMESPACES)
        supplier_info = invoice_head.find('data:supplierInfo', namespaces=XML_NAMESPACES)
        if supplier_bank_account_number := supplier_info.findtext('data:supplierBankAccountNumber', namespaces=XML_NAMESPACES):
            partner_bank = self.env['res.partner.bank'].search([('sanitized_acc_number', '=', sanitize_account_number(supplier_bank_account_number)), ('partner_id', '=', self.partner_id.id)], limit=1)
            if not partner_bank:
                partner_bank = self.env['res.partner.bank'].create({
                    'acc_number': supplier_bank_account_number,
                    'partner_id': self.partner_id.id,
                })
            move_vals['partner_bank_id'] = partner_bank.id

        invoice_detail = invoice_head.find('data:invoiceDetail', namespaces=XML_NAMESPACES)
        if invoice_currency_rate := invoice_detail.findtext('data:exchangeRate', namespaces=XML_NAMESPACES):
            move_vals['invoice_currency_rate'] = float(invoice_currency_rate)

        invoice_category = invoice_detail.findtext('data:invoiceCategory', namespaces=XML_NAMESPACES)
        if invoice_category == 'AGGREGATE':
            self.message_post(body=_(
                "This is an aggregate invoice covering time period from %(start)s to %(end)s.",
                start=invoice_detail.findtext('data:invoiceDeliveryPeriodStart', namespaces=XML_NAMESPACES),
                end=invoice_detail.findtext('data:invoiceDeliveryPeriodEnd', namespaces=XML_NAMESPACES),
            ))

        invoice_reference = invoice.find('data:invoiceReference', namespaces=XML_NAMESPACES)
        invoice_summary = invoice.find('data:invoiceSummary', namespaces=XML_NAMESPACES)
        simplified = invoice_category == 'SIMPLIFIED'
        gross_total = float(invoice_summary.findtext('data:summaryGrossData/data:invoiceGrossAmount', namespaces=XML_NAMESPACES)) if simplified else False
        if (
            simplified
            and invoice_reference is not None
            and self.move_type == 'in_invoice'
            and gross_total < 0
        ):
            self.move_type = 'in_refund'

        if (invoice_reference is not None) and not boolean(invoice_reference.findtext('data:modifyWithoutMaster', namespaces=XML_NAMESPACES)):
            original_invoice = self.search([('ref', '=', invoice_reference.findtext('data:originalInvoiceNumber', namespaces=XML_NAMESPACES)), ('partner_id', '=', self.partner_id.id)], limit=1)
            if self.move_type == 'in_refund':
                move_vals['reversed_entry_id'] = original_invoice.id
            elif self.move_type == 'in_invoice':
                move_vals['debit_origin_id'] = original_invoice.id

        lines_vals = []
        for line in invoice.iterfind('data:invoiceLines/data:line', namespaces=XML_NAMESPACES):
            line_vals = {'display_type': 'product'}

            if boolean(line.findtext('data:advanceData/data:advanceIndicator', namespaces=XML_NAMESPACES)) and 'is_downpayment' in self.env['account.move.line']:
                line_vals['is_downpayment'] = True

            if line_description := line.findtext('data:lineDescription', namespaces=XML_NAMESPACES):
                line_vals['name'] = line_description

            if (product_codes := line.find('data:productCodes', namespaces=XML_NAMESPACES)) is not None:
                for product_code in product_codes.iterfind('data:productCode', namespaces=XML_NAMESPACES):
                    product_info = {
                        'name': line_vals.get('name'),
                        'company': self.company_id,
                    }
                    if product_code_own_value := product_code.findtext('data:productCodeOwnValue', namespaces=XML_NAMESPACES):
                        product_info['default_code'] = product_code_own_value
                    else:
                        product_info['extra_domain'] = [
                            ('l10n_hu_product_code_type', '=', product_code.findtext('data:productCodeCategory', namespaces=XML_NAMESPACES)),
                            ('l10n_hu_product_code', '=', product_code.findtext('data:productCodeValue', namespaces=XML_NAMESPACES)),
                        ]

                    product = self.env['product.product']._retrieve_product(**product_info)
                    if product:
                        line_vals['product_id'] = product.id
                        break

            if unit_of_measure := line.findtext('data:unitOfMeasure', namespaces=XML_NAMESPACES):
                uom_domain = [('name', '=', line.findtext('data:unitOfMeasureOwn', namespaces=XML_NAMESPACES))] if unit_of_measure == 'OWN' else [('l10n_hu_edi_code', '=', unit_of_measure)]
                if uom := self.env['uom.uom'].search(uom_domain, limit=1):
                    line_vals['product_uom_id'] = uom.id

            if discount_rate := line.findtext('data:lineDiscountData/data:discountRate', namespaces=XML_NAMESPACES):
                line_vals['discount'] = float(discount_rate) * 100

            if invoice_category == 'SIMPLIFIED':
                amounts_path = 'lineAmountsSimplified'
                price_include = True
            else:
                amounts_path = 'lineAmountsNormal'
                price_include = False

            amounts = line.find(f'data:{amounts_path}', namespaces=XML_NAMESPACES)

            sign = -1 if self.move_type == 'in_refund' else 1
            if quantity := line.findtext('data:quantity', namespaces=XML_NAMESPACES):
                quantity = float(quantity)
                if quantity < 0:
                    quantity *= sign
                    sign = 1
            else:
                quantity = 1
            line_vals['quantity'] = quantity

            if price_unit := line.findtext('data:unitPrice', namespaces=XML_NAMESPACES):
                line_vals['price_unit'] = sign * float(price_unit)
            else:
                total_path = 'data:lineGrossAmountSimplified' if price_include else 'data:lineNetAmountData/data:lineNetAmount'
                total = amounts.findtext(total_path, namespaces=XML_NAMESPACES)
                line_vals['price_unit'] = sign * float(total) / quantity

            line_vat_rate = amounts.find('data:lineVatRate', namespaces=XML_NAMESPACES)
            l10n_hu_tax_type = rate = None
            if vat_percentage := line_vat_rate.findtext('data:vatPercentage', namespaces=XML_NAMESPACES):
                rate = vat_percentage
                l10n_hu_tax_type = 'VAT'
            elif (vat_exemption := line_vat_rate.find('data:vatExemption', namespaces=XML_NAMESPACES)) is not None:
                l10n_hu_tax_type = vat_exemption.findtext('data:case', namespaces=XML_NAMESPACES)
            elif (vat_out_of_scope := line_vat_rate.find('data:vatOutOfScope', namespaces=XML_NAMESPACES)) is not None:
                l10n_hu_tax_type = vat_out_of_scope.findtext('data:case', namespaces=XML_NAMESPACES)
            elif boolean(line_vat_rate.findtext('data:vatDomesticReverseCharge', namespaces=XML_NAMESPACES)):
                l10n_hu_tax_type = 'DOMESTIC_REVERSE'
            elif margin_scheme_indicator := line_vat_rate.findtext('data:marginSchemeIndicator', namespaces=XML_NAMESPACES):
                l10n_hu_tax_type = margin_scheme_indicator
            elif (vat_amount_mismatch := line_vat_rate.find('data:vatAmountMismatch', namespaces=XML_NAMESPACES)) is not None:
                l10n_hu_tax_type = vat_amount_mismatch.findtext('data:case', namespaces=XML_NAMESPACES)
                rate = vat_amount_mismatch.findtext('data:vatRate/data:vatPercentage', namespaces=XML_NAMESPACES)
            elif boolean(line_vat_rate.findtext('data:noVatCharge', namespaces=XML_NAMESPACES)):
                l10n_hu_tax_type = 'NO_VAT'
            elif rate := line_vat_rate.findtext('data:vatContent', namespaces=XML_NAMESPACES):
                pass

            tax_domain = [
                *self.env['account.tax']._check_company_domain(self.company_id),
                ('type_tax_use', '=', 'purchase'),
                ('price_include', '=', price_include),
            ]
            if l10n_hu_tax_type:
                tax_domain.append(('l10n_hu_tax_type', '=', l10n_hu_tax_type))
            if rate:
                tax_domain.append(('amount', '=', float(rate) * 100))
            if tax := self.env['account.tax'].search(tax_domain, limit=1):
                line_vals['tax_ids'] = [Command.set([tax.id])]

            lines_vals.append(Command.create(line_vals))

        move_vals['invoice_line_ids'] = lines_vals

        self.write(move_vals)
        self._l10n_hu_edi_check_amounts_mismatch(invoice_summary, simplified, gross_total)

    def _l10n_hu_edi_check_amounts_mismatch(self, invoice_summary, simplified, gross_total):
        self.ensure_one()

        if not simplified:
            net_amount = float(invoice_summary.findtext('data:summaryNormal/data:invoiceNetAmount', namespaces=XML_NAMESPACES))
            vat_amount = float(invoice_summary.findtext('data:summaryNormal/data:invoiceVatAmount', namespaces=XML_NAMESPACES))
            gross_total = net_amount + vat_amount

        currency = self.currency_id or self.company_id.currency_id
        if currency.compare_amounts(gross_total, -self.amount_total_in_currency_signed) != 0:
            self.l10n_hu_edi_messages = {
                'error_title': _("Amount mismatch detected."),
                'errors': [_("The gross total on the bill received from NAV and computed is not the same. Please check XML file in 'NAV 3.0' tab.")],
                'blocking_level': 'warning',
            }
