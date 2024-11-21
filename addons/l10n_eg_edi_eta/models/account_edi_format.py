# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import json
import logging
import requests
from werkzeug.urls import url_quote
from base64 import b64encode
from odoo.addons.account.tools import LegacyHTTPAdapter
from json.decoder import JSONDecodeError

from odoo import api, models, _
from odoo.tools.float_utils import json_float_round

_logger = logging.getLogger(__name__)


ETA_DOMAINS = {
    'preproduction': 'https://api.preprod.invoicing.eta.gov.eg',
    'production': 'https://api.invoicing.eta.gov.eg',
    'invoice.preproduction': 'https://preprod.invoicing.eta.gov.eg/',
    'invoice.production': 'https://invoicing.eta.gov.eg',
    'token.preproduction': 'https://id.preprod.eta.gov.eg',
    'token.production': 'https://id.eta.gov.eg',
}


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    @api.model
    def _l10n_eg_get_eta_qr_domain(self, production_enviroment=False):
        return production_enviroment and ETA_DOMAINS['invoice.production'] or ETA_DOMAINS['invoice.preproduction']

    @api.model
    def _l10n_eg_get_eta_api_domain(self, production_enviroment=False):
        return production_enviroment and ETA_DOMAINS['production'] or ETA_DOMAINS['preproduction']

    @api.model
    def _l10n_eg_get_eta_token_domain(self, production_enviroment=False):
        return production_enviroment and ETA_DOMAINS['token.production'] or ETA_DOMAINS['token.preproduction']

    @api.model
    def _l10n_eg_eta_connect_to_server(self, request_data, request_url, method, is_access_token_req=False, production_enviroment=False):
        api_domain = is_access_token_req and self._l10n_eg_get_eta_token_domain(production_enviroment) or self._l10n_eg_get_eta_api_domain(production_enviroment)
        request_url = api_domain + request_url
        try:
            session = requests.session()
            session.mount("https://", LegacyHTTPAdapter())
            request_response = session.request(method, request_url, data=request_data.get('body'), headers=request_data.get('header'), timeout=(5, 10))
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as ex:
            return {
                'error': str(ex),
                'blocking_level': 'warning'
            }
        if not request_response.ok:
            try:
                response_data = request_response.json()
            except JSONDecodeError as ex:
                return {
                    'error': str(ex),
                    'blocking_level': 'error'
                }
            if response_data and response_data.get('error'):
                return {
                    'error': response_data.get('error'),
                    'blocking_level': 'error'
                }
        return {'response': request_response}

    @api.model
    def _l10n_eg_edi_round(self, amount, precision_digits=5):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return json_float_round(amount, precision_digits)

    @api.model
    def _l10n_eg_edi_post_invoice_web_service(self, invoice):
        access_data = self._l10n_eg_eta_get_access_token(invoice)
        if access_data.get('error'):
            return access_data
        invoice_json = json.loads(invoice.l10n_eg_eta_json_doc_id.raw)
        request_url = '/api/v1.0/documentsubmissions'
        request_data = {
            'body': json.dumps({'documents': [invoice_json['request']]}, ensure_ascii=False, indent=4).encode('utf-8'),
            'header': {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % access_data.get('access_token')}
        }
        response_data = self._l10n_eg_eta_connect_to_server(request_data, request_url, 'POST', production_enviroment=invoice.company_id.l10n_eg_production_env)
        if response_data.get('error'):
            return response_data
        response_data = response_data.get('response').json()
        if response_data.get('rejectedDocuments', False) and isinstance(response_data.get('rejectedDocuments'), list):
            return {
                'error': str(response_data.get('rejectedDocuments')[0].get('error')),
                'blocking_level': 'error'
            }
        if response_data.get('submissionId') is not None and response_data.get('acceptedDocuments'):
            invoice_json['response'] = {
                'l10n_eg_uuid': response_data['acceptedDocuments'][0].get('uuid'),
                'l10n_eg_long_id': response_data['acceptedDocuments'][0].get('longId'),
                'l10n_eg_internal_id': response_data['acceptedDocuments'][0].get('internalId'),
                'l10n_eg_hash_key': response_data['acceptedDocuments'][0].get('hashKey'),
                'l10n_eg_submission_number': response_data['submissionId'],
            }
            invoice.l10n_eg_eta_json_doc_id.raw = json.dumps(invoice_json)
            return {'attachment': invoice.l10n_eg_eta_json_doc_id}
        return {
            'error': _('an Unknown error has occurred'),
            'blocking_level': 'warning'
        }

    @api.model
    def _cancel_invoice_edi_eta(self, invoice):
        access_data = self._l10n_eg_eta_get_access_token(invoice)
        if access_data.get('error'):
            return access_data
        # Check current status. It may already be cancelled or rejected.
        if invoice.l10n_eg_submission_number:
            document_summary = self._l10n_eg_get_einvoice_document_summary(invoice)
            if document_summary.get('doc_data') and document_summary['doc_data'][0].get('status') in ('Cancelled', 'Rejected'):
                return {'success': True}
        request_url = f'/api/v1/documents/state/{url_quote(invoice.l10n_eg_uuid)}/state'
        request_data = {
            'body': json.dumps({'status': 'cancelled', 'reason': 'Cancelled'}),
            'header': {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % access_data.get('access_token')}
        }
        response_data = self._l10n_eg_eta_connect_to_server(request_data, request_url, 'PUT', production_enviroment=invoice.company_id.l10n_eg_production_env)
        if response_data.get('error'):
            return response_data
        if response_data.get('response').ok:
            return {'success': True}
        return {
            'error': _('an Unknown error has occurred'),
            'blocking_level': 'warning'
        }

    @api.model
    def _l10n_eg_get_einvoice_document_summary(self, invoice):
        access_data = self._l10n_eg_eta_get_access_token(invoice)
        if access_data.get('error'):
            return access_data
        request_url = f'/api/v1.0/documentsubmissions/{url_quote(invoice.l10n_eg_submission_number)}'
        request_data = {
            'body': None,
            'header': {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % access_data.get('access_token')}
        }
        response_data = self._l10n_eg_eta_connect_to_server(request_data, request_url, 'GET', production_enviroment=invoice.company_id.l10n_eg_production_env)
        if response_data.get('error'):
            return response_data
        response_data = response_data.get('response').json()
        document_summary = [doc for doc in response_data.get('documentSummary', []) if doc.get('uuid') == invoice.l10n_eg_uuid]
        return {'doc_data': document_summary}

    @api.model
    def _l10n_eg_get_einvoice_status(self, invoice):
        document_summary = self._l10n_eg_get_einvoice_document_summary(invoice)
        return_dict = {
            'Invalid': {
                'error': _("This invoice has been marked as invalid by the ETA. Please check the ETA website for more information"),
                'blocking_level': 'error'
            },
            'Submitted': {
                'error': _("This invoice has been sent to the ETA, but we are still awaiting validation"),
                'blocking_level': 'info'
            },
            'Valid': {'success': True},
            'Cancelled': {'error': _('Document Cancelled'), 'blocking_level': 'error'},
        }
        if document_summary.get('doc_data') and return_dict.get(document_summary['doc_data'][0].get('status')):
            return return_dict.get(document_summary['doc_data'][0]['status'])
        return {'error': _('an Unknown error has occured'), 'blocking_level': 'warning'}

    def _l10n_eg_eta_get_access_token(self, invoice):
        user = invoice.company_id.sudo().l10n_eg_client_identifier
        secret = invoice.company_id.sudo().l10n_eg_client_secret
        access = '%s:%s' % (user, secret)
        user_and_pass = b64encode(access.encode()).decode()
        request_url = '/connect/token'
        request_data = {'body': {'grant_type': 'client_credentials'}, 'header': {'Authorization': f'Basic {user_and_pass}'}}
        response_data = self._l10n_eg_eta_connect_to_server(request_data, request_url, 'POST', is_access_token_req=True, production_enviroment=invoice.company_id.l10n_eg_production_env)
        if response_data.get('error'):
            return response_data
        return {'access_token' : response_data.get('response').json().get('access_token')}

    @api.model
    def _l10n_eg_get_eta_invoice_pdf(self, invoice):
        access_data = self._l10n_eg_eta_get_access_token(invoice)
        if access_data.get('error'):
            return access_data
        request_url = f'/api/v1.0/documents/{url_quote(invoice.l10n_eg_uuid)}/pdf'
        request_data = {'body': None, 'header': {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % access_data.get('access_token')}}
        response_data = self._l10n_eg_eta_connect_to_server(request_data, request_url, 'GET', production_enviroment=invoice.company_id.l10n_eg_production_env)
        if response_data.get('error'):
            return response_data
        response_data = response_data.get('response')
        _logger.warning('PDF Function Response %s.', response_data)
        if response_data.ok:
            return {'data': response_data.content}
        else:
            return {'error': _('PDF Document is not available')}

    @api.model
    def _l10n_eg_validate_info_address(self, partner_id, issuer=False, invoice=False):
        fields = ["country_id",
                  "state_id", "city", "street",
                  "l10n_eg_building_no"]
        if (invoice and invoice.amount_total >= invoice.company_id.l10n_eg_invoicing_threshold) or self._l10n_eg_get_partner_tax_type(partner_id, issuer) != 'P':
            fields.append('vat')
        return all(partner_id[field] for field in fields)

    @api.model
    def _l10n_eg_eta_prepare_eta_invoice(self, invoice):
        AccountTax = self.env['account.tax']
        base_amls = invoice.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [invoice._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = invoice.line_ids.filtered(lambda x: x.display_type == 'tax')
        tax_lines = [invoice._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, invoice.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, invoice.company_id, tax_lines=tax_lines)

        # Tax amounts per line.

        def grouping_function_base_line(base_line, tax_data):
            tax = tax_data['tax']
            code_split = tax.l10n_eg_eta_code.split('_')
            return {
                'rate': abs(tax.amount) if tax.amount_type != 'fixed' else None,
                'tax_type': code_split[0].upper(),
                'sub_type': code_split[1].upper(),
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_base_line)
        invoice_line_data, totals = self._l10n_eg_eta_prepare_invoice_lines_data(invoice, base_lines_aggregated_values)

        # Tax amounts for the whole document.

        def grouping_function_global(base_line, tax_data):
            tax = tax_data['tax']
            code_split = tax.l10n_eg_eta_code.split('_')
            return {
                'tax_type': code_split[0].upper(),
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_global)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        date_string = invoice.invoice_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        eta_invoice = {
            'issuer': self._l10n_eg_eta_prepare_address_data(invoice.journal_id.l10n_eg_branch_id, invoice, issuer=True,),
            'receiver': self._l10n_eg_eta_prepare_address_data(invoice.partner_id, invoice),
            'documentType': 'i' if invoice.move_type == 'out_invoice' else 'c' if invoice.move_type == 'out_refund' else 'd' if invoice.move_type == 'in_refund' else '',
            'documentTypeVersion': '1.0',
            'dateTimeIssued': date_string,
            'taxpayerActivityCode': invoice.journal_id.l10n_eg_activity_type_id.code,
            'internalID': invoice.name,
        }
        eta_invoice.update({
            'invoiceLines': invoice_line_data,
            'taxTotals': [
                {
                    'taxType': grouping_key['tax_type'],
                    'amount': self._l10n_eg_edi_round(tax_values['tax_amount']),
                }
                for grouping_key, tax_values in values_per_grouping_key.items()
                if grouping_key
            ],
            'totalDiscountAmount': self._l10n_eg_edi_round(totals['discount_total']),
            'totalSalesAmount': self._l10n_eg_edi_round(totals['total_price_subtotal_before_discount']),
            'netAmount': self._l10n_eg_edi_round(sum(x['base_amount'] for x in values_per_grouping_key.values())),
            'totalAmount': self._l10n_eg_edi_round(sum(x['base_amount'] + x['tax_amount'] for x in values_per_grouping_key.values())),
            'extraDiscountAmount': 0.0,
            'totalItemsDiscountAmount': 0.0,
        })
        if invoice.ref:
            eta_invoice['purchaseOrderReference'] = invoice.ref
        if invoice.invoice_origin:
            eta_invoice['salesOrderReference'] = invoice.invoice_origin
        return eta_invoice

    @api.model
    def _l10n_eg_eta_prepare_invoice_lines_data(self, invoice, base_lines_aggregated_values):
        lines = []
        totals = {
            'discount_total': 0.0,
            'total_price_subtotal_before_discount' : 0.0,
        }
        for base_line, aggregated_values in base_lines_aggregated_values:
            line = base_line['record']
            tax_details = base_line['tax_details']
            price_unit = self._l10n_eg_edi_round(abs((line.balance / line.quantity) / (1 - (line.discount / 100.0)))) if line.quantity and line.discount != 100.0 else line.price_unit
            price_subtotal_before_discount = self._l10n_eg_edi_round(abs(line.balance / (1 - (line.discount / 100)))) if line.discount != 100.0 else self._l10n_eg_edi_round(price_unit * line.quantity)
            discount_amount = self._l10n_eg_edi_round(price_subtotal_before_discount - abs(line.balance))
            item_code = line.product_id.l10n_eg_eta_code or line.product_id.barcode
            lines.append({
                'description': line.product_id.display_name or line.name,
                'itemType': item_code.startswith('EG') and 'EGS' or 'GS1',
                'itemCode': item_code,
                'unitType': line.product_uom_id.l10n_eg_unit_code_id.code,
                'quantity': line.quantity,
                'internalCode': line.product_id.default_code or '',
                'valueDifference': 0.0,
                'totalTaxableFees': 0.0,
                'itemsDiscount': 0.0,
                'unitValue': {
                    'currencySold': invoice.currency_id.name,
                    'amountEGP': price_unit,
                },
                'discount': {
                    'rate': line.discount,
                    'amount': discount_amount,
                },
                'taxableItems': [
                    {
                        'taxType': grouping_key['tax_type'],
                        'amount': self._l10n_eg_edi_round(tax_values['tax_amount']),
                        'subType': grouping_key['sub_type'],
                        'rate': grouping_key['rate'],
                    }
                    for grouping_key, tax_values in aggregated_values.items()
                    if grouping_key
                ],
                'salesTotal': price_subtotal_before_discount,
                'netTotal': self._l10n_eg_edi_round(tax_details['total_excluded'] + tax_details['delta_base_amount']),
                'total': self._l10n_eg_edi_round(tax_details['total_included']),
            })
            totals['discount_total'] += discount_amount
            totals['total_price_subtotal_before_discount'] += price_subtotal_before_discount
            if invoice.currency_id != self.env.ref('base.EGP'):
                lines[-1]['unitValue']['currencyExchangeRate'] = self._l10n_eg_edi_round(invoice._l10n_eg_edi_exchange_currency_rate())
                lines[-1]['unitValue']['amountSold'] = line.price_unit
        return lines, totals

    @api.model
    def _l10n_eg_get_partner_tax_type(self, partner_id, issuer=False):
        if issuer:
            return 'B'
        elif partner_id.commercial_partner_id.country_code == 'EG':
            return 'B' if partner_id.commercial_partner_id.is_company else 'P'
        else:
            return 'F'

    @api.model
    def _l10n_eg_eta_prepare_address_data(self, partner, invoice, issuer=False):
        address = {
            'address': {
                'country': partner.country_id.code,
                'governate': partner.state_id.name or '',
                'regionCity': partner.city or '',
                'street': partner.street or '',
                'buildingNumber': partner.l10n_eg_building_no or '',
                'postalCode': partner.zip or '',
            },
            'name': partner.name,
        }
        if issuer:
            address['address']['branchID'] = invoice.journal_id.l10n_eg_branch_identifier or ''
        individual_type = self._l10n_eg_get_partner_tax_type(partner, issuer)
        address['type'] = individual_type or ''
        if invoice.amount_total >= invoice.company_id.l10n_eg_invoicing_threshold or individual_type != 'P':
            address['id'] = partner.vat or ''
        return address

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        return self.code == 'eg_eta' or super()._needs_web_services()

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'eg_eta':
            return super()._get_move_applicability(move)

        if move.is_invoice(include_receipts=True) and move.country_code == 'EG':
            return {
                'post': self._l10n_eg_edi_post_invoice,
                'cancel': self._l10n_eg_edi_cancel_invoice,
                'edi_content': self._l10n_eg_edi_xml_invoice_content,
            }

    def _check_move_configuration(self, invoice):
        errors = super()._check_move_configuration(invoice)
        if self.code != 'eg_eta':
            return errors

        if invoice.journal_id.l10n_eg_branch_id.vat == invoice.partner_id.vat:
            errors.append(_("You cannot issue an invoice to a partner with the same VAT number as the branch."))
        if not self._l10n_eg_get_eta_token_domain(invoice.company_id.l10n_eg_production_env):
            errors.append(_("Please configure the token domain from the system parameters"))
        if not self._l10n_eg_get_eta_api_domain(invoice.company_id.l10n_eg_production_env):
            errors.append(_("Please configure the API domain from the system parameters"))
        if not all([invoice.journal_id.l10n_eg_branch_id, invoice.journal_id.l10n_eg_branch_identifier, invoice.journal_id.l10n_eg_activity_type_id]):
            errors.append(_("Please set the all the ETA information on the invoice's journal"))
        if not self._l10n_eg_validate_info_address(invoice.journal_id.l10n_eg_branch_id):
            errors.append(_("Please add all the required fields in the branch details"))
        if not self._l10n_eg_validate_info_address(invoice.partner_id, invoice=invoice):
            errors.append(_("Please add all the required fields in the customer details"))
        if not all(aml.product_uom_id.l10n_eg_unit_code_id.code for aml in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section'))):
            errors.append(_("Please make sure the invoice lines UoM codes are all set up correctly"))
        if not all(tax.l10n_eg_eta_code for tax in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')).tax_ids):
            errors.append(_("Please make sure the invoice lines taxes all have the correct ETA tax code"))
        if not all(aml.product_id.l10n_eg_eta_code or aml.product_id.barcode for aml in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section'))):
            errors.append(_("Please make sure the EGS/GS1 Barcode is set correctly on all products"))
        return errors

    def _l10n_eg_edi_post_invoice(self, invoice):
        # In case we have already sent it, but have not got a final answer yet.
        if invoice.l10n_eg_submission_number:
            return {invoice: self._l10n_eg_get_einvoice_status(invoice)}

        if not invoice.l10n_eg_eta_json_doc_id:
            return {
                invoice: {
                    'error':  _("An error occured in created the ETA invoice, please retry signing"),
                    'blocking_level': 'error'
                }
            }
        invoice_json = json.loads(invoice.l10n_eg_eta_json_doc_id.raw)['request']
        if not invoice_json.get('signatures'):
            return {
                invoice: {
                    'error':  _("Please make sure the invoice is signed"),
                    'blocking_level': 'error'
                }
            }
        return {invoice: self._l10n_eg_edi_post_invoice_web_service(invoice)}

    def _l10n_eg_edi_cancel_invoice(self, invoice):
        return {invoice: self._cancel_invoice_edi_eta(invoice)}

    def _l10n_eg_edi_xml_invoice_content(self, invoice):
        return json.dumps(self._l10n_eg_eta_prepare_eta_invoice(invoice)).encode()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        if self.code != 'eg_eta':
            return super()._is_compatible_with_journal(journal)
        return journal.country_code == 'EG' and journal.type == 'sale'
