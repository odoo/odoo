# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Written with the help from Komit

import json
import uuid
import urllib3
from num2words import num2words
from odoo import _, api, fields, models
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)
try:
    import certifi
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
except ImportError:
    _logger.warning(_('Could not import certifi. Please see https://pypi.org/project/certifi/. SSL verification is disabled for communications with Viettel.'))
    http = urllib3.PoolManager()


class CustomException(Exception):
    pass


inv_fields_mapping = {
        "invoiceIssuedDate": "create_date",
        "invoiceNote": "summary",
        "buyerName": "customer_name",
        "buyerLegalName": "customer_legal_name",
        "buyerTaxCode": "customer_tax_code",
        "buyerAddressLine": "customer_address",
        "buyerEmail": "customer_email",
        "transactionUuid": "transaction_uuid",
        # seller info
        "sellerLegalName": "company_name",
        "sellerTaxCode": "company_tax_code",
        "sellerAddressLine": "company_address",
        "sellerPhoneNumber": "company_number",
        "sellerWebsite": "company_website",
        "sellerBankAccount": "company_bank_account",
        "sellerBankName": "company_bank_name",

        "paymentMethodName": "payment_method_name",
        # summary
        "sumOfTotalLineAmountWithoutTax": "total_line_amount_wo_tax",
        "totalAmountWithoutTax": "amount_untaxed",
        "totalTaxAmount": "amount_tax",
        "totalAmountWithTax": "amount_total",
        "totalAmountWithTaxInWords": "amount_total_text",
        "taxPercentage": "total_tax_percent",
        "taxBreakdowns": "tax_list",
        "discountAmount": ""
}

inv_line_fields_mapping = {
    "lineNumber": "sequence",
    "itemCode": "product_ref",
    "itemName": "product_name",
    "unitName": "uom_name",
    "unitPrice": "price_unit",
    "quantity": "quantity",
    "itemTotalAmountWithoutTax": "price_subtotal",
    "taxAmount": "amount_tax",
    "taxableAmount": "taxable_amount",
    "taxPercentage": "tax_percent",
}



class AccountMove(models.Model):
    _inherit = "account.move"

    country_code = fields.Char(related='company_id.country_id.code', string='Country Code')
    l10n_vn_transaction_id = fields.Char(copy=False)
    l10n_vn_invoice_no = fields.Char(string='Invoice No (Số hóa đơn)', copy=False)
    l10n_vn_reservation_code = fields.Char(string='Reservation Code (Mã số bí mật)', copy=False)
    l10n_vn_uuid = fields.Char(readonly=True, copy=False)
    l10n_vn_is_send_mail_success = fields.Boolean(default=False, readonly=True, copy=False)
    l10n_vn_transaction_date = fields.Char(string='Transaction ID (Ngày lập)', readonly=True, copy=False)
    l10n_vn_file = fields.Binary(readonly=True, copy=False)
    l10n_vn_vas_invoice_date = fields.Datetime(compute='_compute_l10n_vn_vas_invoice_date', store=True)
    l10n_vn_tax_invoice_number = fields.Char(copy=False)
    l10n_vn_tax_invoice_series = fields.Char(copy=False)

    @api.depends('l10n_vn_transaction_date')
    def _compute_l10n_vn_vas_invoice_date(self):
        for record in self:
            if record.l10n_vn_transaction_date:
                record.l10n_vn_vas_invoice_date = record.l10n_vn_transaction_date[:10]
            else:
                record.l10n_vn_vas_invoice_date = False

    # #### ACTIONS

    def button_export_draft_invoice(self):
        self.action_export_einvoice(is_draft=True)

    def button_export_confirmed_invoice(self):
        self.action_export_einvoice(is_draft=False)

    def action_export_einvoice(self, is_draft):
        self.ensure_one()
        customer_address = self.partner_id._display_address(without_company=True).replace('\n', ', ')
        company_address = self.partner_id.company_id.partner_id._display_address(without_company=True).replace('\n', ', ')

        if not customer_address:
            raise UserError(_("The legal address of partner is not set. Please set it first in order to export!"))
        vnd_cur = self.env.ref('base.VND')
        create_date = fields.Datetime.from_string(fields.Datetime.now()).strftime("%Y-%m-%dT%H:%M:%S.%f%z")

        payment_method_name = self.invoice_partner_bank_id and "CK" or "TM"
        bank_ids = self.env['res.partner.bank'].search([('partner_id', '=', self.env.company.partner_id.id)])

        inv_vals = {
            'create_date': create_date,
            'customer_legal_name': self.partner_id.name,
            'customer_tax_code': self.partner_id.vat or '',
            'customer_address': customer_address,
            'customer_email': self.partner_id.email if self.currency_id == vnd_cur else 'accounting@komit-consulting.com',  # TODO unhardcode
            'transaction_uuid': '%s' % uuid.uuid1(),
            'company_name': self.company_id.name,
            'company_tax_code': self.company_id.vat or '',
            'company_address': company_address,
            'company_number': self.company_id.phone or '',
            'company_website': self.company_id.website or '',
            'company_bank_account': ', '.join(bank_ids.mapped(lambda b: '%s (%s)' % (b.acc_number, (b.currency_id or self.company_id.currency_id).name))),
            'company_bank_name': ', '.join(bank_ids.mapped('bank_id.name')),
            'payment_method_name': payment_method_name,
            'currency_name': self.currency_id.name,
        }

        inv_lines_vals = []
        index = 1
        total_line_amount_wo_tax = 0
        tax_dict = {}
        no_tax = self.env.ref('l10n_vn.%s_tax_sale_vat0' % self.company_id.id)
        for line in self.invoice_line_ids:
            total_line_amount_wo_tax += line.price_subtotal
            if not line.tax_ids:
                raise UserError(_('There is no tax set on line %s') % line.name)
            # taxPercentage from Viettel: no tax = -2
            tax_percent = -2 if no_tax in line.tax_ids else line.tax_ids.amount

            if tax_dict.get(tax_percent, False):
                tax_dict[tax_percent]['taxable_amount'] += line.price_subtotal
                tax_dict[tax_percent]['tax_amount'] += line.price_total - line.price_subtotal
            else:
                tax_dict[tax_percent] = {
                    'taxable_amount': line.price_subtotal,
                    'tax_amount': line.price_total - line.price_subtotal,
                }
            inv_lines_vals.append({
                'sequence': index,
                'product_ref': line.product_id.default_code,
                'product_name': line.display_name,  # TODO was line.local_description
                'uom_name': line.product_uom_id.display_name,  # TODO was line.local_name
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price_subtotal': line.price_subtotal,
                'tax_percent': tax_percent,
                'amount_tax': line.price_total - line.price_subtotal,
            })
            index += 1

        tax_list = []
        for key in tax_dict:
            tax_list.append({
                'tax_percent': key,
                'taxable_amount': tax_dict[key]['taxable_amount'],
                'amount_tax': tax_dict[key]['tax_amount'],
            })

        inv_vals.update({
            'total_line_amount_wo_tax': total_line_amount_wo_tax,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            'amount_total_text': num2words(self.amount_total, lang='vi_VN'),
            'tax_list': tax_list,
        })

        data_return, viettel_input = self._l10n_vn_export_to_viettel(inv_vals, inv_lines_vals, is_draft=is_draft)
        self.write({
            'l10n_vn_transaction_id': data_return['transaction_id'],
            'l10n_vn_invoice_no': data_return['inv_no'],
            'l10n_vn_reservation_code': data_return['reservation_code'],
            'l10n_vn_uuid': inv_vals['transaction_uuid'],
            'l10n_vn_transaction_date': inv_vals['create_date'],
        })

        if data_return['status'] != '200' or data_return['result_error']:
            raise UserError(_('Network error: %s\n\n%s') % (data_return['status'], data_return['result_error']))

        if data_return['error_code']:
            raise UserError(_('%s\nError code:%s') % (data_return['description'], data_return['error_code']))

        if self.l10n_vn_invoice_no:
            self.message_post(body="Export E-Invoice to Viettel successfully!")
        else:
            self.message_post(body="Export Draft E-Invoice successfully!")

    def action_get_l10n_vn_file(self):
        self.ensure_one()
        if not self.l10n_vn_invoice_no:
            raise UserError(_('The invoice has not been exported to Viettel.\nPlease click to button Export E-Invoice first'))
        data = self._l10n_vn_get_invoice(self.company_id.vat, self.l10n_vn_invoice_no)[0]
        if not data['description'] and not data['errorCode']:
            self.l10n_vn_file = data['fileToBytes']
        else:
            raise UserError(_('%s\nError code:%s' % (data['description'], data['errorCode'])))

    def action_send_l10n_vn_mail(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_("You cannot send email because you did not specify the customer's email. Please setup email for the customer"))
        data = self._l10n_vn_send_mail(self.company_id.vat, self.l10n_vn_uuid)
        data_output = data['commonOutputs']
        if data_output[0]['description'] == 'SUCCESS':
            self.message_post(body="Sent E-Invoice mail to customer")
            self.l10n_vn_is_send_mail_success = True
        else:
            raise UserError(_('%s\nError code:%s' % (data_output['description'], data_output['errorCode'])))

    # #### VIETTEL API METHODS

    def _l10n_vn_request_http(self, body, headers, url_tail, return_dict=True):
        self.ensure_one()
        l10n_vn_base_url = self.company_id.l10n_vn_base_url
        encoded_body = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        request_status = 'fail'
        try:
            response = http.request('POST', '%s/InvoiceAPI/%s' % (l10n_vn_base_url, url_tail), headers=headers, body=encoded_body)
            if str(response.status) != '200':
                raise CustomException(response.status)
            try:
                json.loads(response.data.decode())
                if return_dict:
                    response = json.loads(response.data.decode())
                request_status = 'success'
            except json.decoder.JSONDecodeError:
                response = response.data.decode()
        except (urllib3.exceptions.LocationValueError, CustomException) as e:
            _logger.error(e)
            _logger.info('l10n_vn_base_url: %s', l10n_vn_base_url)
            _logger.info('url_tail: %s', url_tail)
            _logger.info('headers: %s', headers)
            _logger.info('encoded_body: %s', encoded_body)
            response = e
        return response, request_status

    def _l10n_vn_export_to_viettel(self, inv_vals, inv_lines_vals, is_draft=True):
        self.ensure_one()

        invoice = {
            "generalInvoiceInfo": {
                "invoiceType": self.company_id.l10n_vn_type,
                "templateCode": self.company_id.l10n_vn_template_code,
                "invoiceSeries": self.company_id.l10n_vn_series,
                "invoiceIssuedDate": inv_vals.get(inv_fields_mapping['invoiceIssuedDate']),
                "currencyCode": inv_vals.get('currency_name'),
                "adjustmentType": "1",
                "paymentStatus": True,
                "paymentType": "CK",
                "paymentTypeName": "CK",
                "cusGetInvoiceRight": True,
                "transactionUuid": inv_vals.get(inv_fields_mapping['transactionUuid']),
            },
            "buyerInfo": {field: inv_vals.get(inv_fields_mapping[field], '') for field in ['buyerName', 'buyerLegalName', 'buyerTaxCode', 'buyerAddressLine', 'buyerEmail']},
            "sellerInfo": {field: inv_vals.get(inv_fields_mapping[field]) for field in ['sellerLegalName', 'sellerTaxCode', 'sellerAddressLine', 'sellerPhoneNumber', 'sellerWebsite', 'sellerBankAccount', 'sellerBankName']},
            "payments": [{"paymentMethodName": inv_vals.get(inv_fields_mapping['paymentMethodName'])}],
            "itemInfo": [
                {field: line.get(inv_line_fields_mapping[field]) for field in ['lineNumber', 'itemCode', 'itemName', 'unitName', 'unitPrice', 'quantity', 'itemTotalAmountWithoutTax', 'taxPercentage', 'taxAmount']}
                for line in inv_lines_vals
            ],
            "summarizeInfo": {field: inv_vals.get(inv_fields_mapping[field], 0.0) for field in ['sumOfTotalLineAmountWithoutTax', 'totalAmountWithoutTax', 'totalTaxAmount', 'totalAmountWithTax', 'totalAmountWithTaxInWords', 'discountAmount']},
            "taxBreakdowns": [
                {field: item.get(inv_line_fields_mapping[field]) for field in ['taxPercentage', 'taxableAmount', 'taxAmount']}
                for item in inv_vals.get(inv_fields_mapping['taxBreakdowns'])
            ],
        }
        headers = urllib3.util.make_headers(basic_auth=self.company_id.l10n_vn_authority)
        create_status = 'createOrUpdateInvoiceDraft' if is_draft else 'createInvoice'
        url_tail = 'InvoiceWS/{0}/{1}'.format(create_status, inv_vals.get('company_tax_code'))
        r, request_status = self._l10n_vn_request_http(invoice, headers, url_tail, return_dict=False)

        if request_status == 'fail':
            result = {
                'status': 'Connection error',
                'description': 'N/A',
                'tax_code': 'N/A',
                'transaction_id': 'N/A',
                'inv_no': 'N/A',
                'reservation_code': 'N/A',
                'error_code': 'K500',
                'result_error': r,
            }
            return result, invoice

        data_dict = json.loads(r.data.decode())
        data_description = data_dict['description']
        data_tax_code = data_tran_id = data_inv_no = data_reservation_code = data_result_error = ''
        if isinstance(data_dict['result'], dict):
            data_tax_code = data_dict['result'].get('supplierTaxCode')
            data_tran_id = data_dict['result'].get('transactionID')
            data_inv_no = data_dict['result'].get('invoiceNo', "")
            data_reservation_code = data_dict['result'].get('reservationCode')
        else:
            data_result_error = data_dict['result']

        data_error_code = data_dict['errorCode']

        result = {
            'status': str(r.status),
            'description': data_description,
            'tax_code': data_tax_code,
            'transaction_id': data_tran_id,
            'inv_no': data_inv_no,
            'reservation_code': data_reservation_code,
            'error_code': data_error_code,
            'result_error': data_result_error
        }
        return result, invoice

    def _l10n_vn_get_invoice(self, tax_code, inv_no):
        self.ensure_one()
        body = {
            "supplierTaxCode": tax_code,
            "invoiceNo": inv_no,
            "pattern": self.company_id.l10n_vn_template_code,
            "fileType": "PDF",
        }

        headers = urllib3.util.make_headers(basic_auth=self.company_id.l10n_vn_authority)
        url_tail = 'InvoiceUtilsWS/getInvoiceRepresentationFile'
        return self._l10n_vn_request_http(body, headers, url_tail)

    def _l10n_vn_send_mail(self, tax_code, uuid):
        self.ensure_one()
        body = {
            "supplierTaxCode": tax_code,
            "lstTransactionUuid": uuid,
        }
        l10n_vn_auth = self.company_id.l10n_vn_authority
        headers = urllib3.util.make_headers(basic_auth=l10n_vn_auth)
        url_tail = 'InvoiceUtilsWS/sendHtmlMailProcess'
        return self._l10n_vn_request_http(body, headers, url_tail)
