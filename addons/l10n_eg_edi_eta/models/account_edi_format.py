# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import json
import logging
import requests
from werkzeug.urls import url_quote
from base64 import b64encode

from odoo import api, models, _
from odoo.tools.float_utils import json_float_round

_logger = logging.getLogger(__name__)


ETA_DOMAINS = {
    'preproduction': 'https://api.preprod.invoicing.eta.gov.eg',
    'production': 'https://api.invoicing.eta.gov.eg',
    'token.preproduction': 'https://id.preprod.eta.gov.eg',
    'token.production': 'https://id.eta.gov.eg',
}


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

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
            request_response = requests.request(method, request_url, data=request_data.get('body'), headers=request_data.get('header'), timeout=(5, 10))
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as ex:
            return {
                'error': str(ex),
                'blocking_level': 'warning'
            }
        if not request_response.ok:
            response_data = request_response.json()
            if isinstance(response_data, dict) and response_data.get('error'):
                return {
                    'error': response_data.get('error', _('Unknown error')),
                    'blocking_level': 'error'
                }
            return {
                'error': request_response.reason,
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
    def _l10n_eg_get_einvoice_status(self, invoice):
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
            'Cancelled': {'error': _('Document Canceled'), 'blocking_level': 'error'},
        }
        if document_summary and return_dict.get(document_summary[0].get('status')):
            return return_dict.get(document_summary[0]['status'])
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

        def group_tax_retention(tax_values):
            return {'l10n_eg_eta_code': tax_values['tax_id'].l10n_eg_eta_code.split('_')[0]}

        date_string = invoice.invoice_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        grouped_taxes = invoice._prepare_edi_tax_details(grouping_key_generator=group_tax_retention)
        invoice_line_data, totals = self._l10n_eg_eta_prepare_invoice_lines_data(invoice, grouped_taxes['invoice_line_tax_details'])
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
            'taxTotals': [{
                'taxType': tax['l10n_eg_eta_code'].split('_')[0].upper(),
                'amount': self._l10n_eg_edi_round(abs(tax['tax_amount'])),
            } for tax in grouped_taxes['tax_details'].values()],
            'totalDiscountAmount': self._l10n_eg_edi_round(totals['discount_total']),
            'totalSalesAmount': self._l10n_eg_edi_round(totals['total_price_subtotal_before_discount']),
            'netAmount': self._l10n_eg_edi_round(abs(invoice.amount_untaxed_signed)),
            'totalAmount': self._l10n_eg_edi_round(abs(invoice.amount_total_signed)),
            'extraDiscountAmount': 0.0,
            'totalItemsDiscountAmount': 0.0,
        })
        return eta_invoice

    @api.model
    def _l10n_eg_eta_prepare_invoice_lines_data(self, invoice, tax_data):
        lines = []
        totals = {
            'discount_total': 0.0,
            'total_price_subtotal_before_discount' : 0.0,
        }
        for line in invoice.invoice_line_ids.filtered(lambda x: not x.display_type):
            line_tax_details = tax_data.get(line, {})
            price_unit = self._l10n_eg_edi_round(abs((line.balance / line.quantity) / (1 - (line.discount / 100.0)))) if line.quantity and line.discount != 100.0 else line.price_unit
            price_subtotal_before_discount = self._l10n_eg_edi_round(abs(line.balance / (1 - (line.discount / 100)))) if line.discount != 100.0 else price_unit * line.quantity
            discount_amount = self._l10n_eg_edi_round(price_subtotal_before_discount - abs(line.balance))
            item_code = line.product_id.l10n_eg_eta_code or line.product_id.barcode
            lines.append({
                'description': line.name,
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
                        'taxType': tax['tax_id'].l10n_eg_eta_code.split('_')[0].upper().upper(),
                        'amount': self._l10n_eg_edi_round(abs(tax['tax_amount'])),
                        'subType': tax['tax_id'].l10n_eg_eta_code.split('_')[1].upper(),
                        'rate': abs(tax['tax_id'].amount),
                    }
                for tax_details in line_tax_details.get('tax_details', {}).values() for tax in tax_details.get('group_tax_details')
                ],
                'salesTotal': price_subtotal_before_discount,
                'netTotal': self._l10n_eg_edi_round(abs(line.balance)),
                'total': self._l10n_eg_edi_round(abs(line.balance + line_tax_details.get('tax_amount', 0.0))),
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
        if invoice.amount_total >= invoice.company_id.l10n_eg_invoicing_threshold or individual_type != 'P':
            address['type'] = individual_type or ''
            address['id'] = partner.vat or ''
        return address

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        return self.code == 'eg_eta' or super()._needs_web_services()

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
        if not all(aml.product_uom_id.l10n_eg_unit_code_id.code for aml in invoice.invoice_line_ids.filtered(lambda x: not x.display_type)):
            errors.append(_("Please make sure the invoice lines UoM codes are all set up correctly"))
        if not all(tax.l10n_eg_eta_code for tax in invoice.invoice_line_ids.filtered(lambda x: not x.display_type).tax_ids):
            errors.append(_("Please make sure the invoice lines taxes all have the correct ETA tax code"))
        if not all(aml.product_id.l10n_eg_eta_code or aml.product_id.barcode for aml in invoice.invoice_line_ids.filtered(lambda x: not x.display_type)):
            errors.append(_("Please make sure the EGS/GS1 Barcode is set correctly on all products"))
        return errors

    def _post_invoice_edi(self, invoices):
        if self.code != 'eg_eta':
            return super()._post_invoice_edi(invoices)
        invoice = invoices  # Batching is disabled for this EDI.

        # In case we have already sent it, but have not got a final answer yet.
        if invoice.l10n_eg_submission_number:
            return {invoice: self._l10n_eg_get_einvoice_status(invoice)}

        if not invoice.l10n_eg_eta_json_doc_id:
            return {
                invoice: {
                    'error':  _("An error occured in created the ETA invoice, please retry signing"),
                    'blocking_level': 'info'
                }
            }
        invoice_json = json.loads(invoice.l10n_eg_eta_json_doc_id.raw)['request']
        if not invoice_json.get('signatures'):
            return {
                invoice: {
                    'error':  _("Please make sure the invoice is signed"),
                    'blocking_level': 'info'
                }
            }
        return {invoice: self._l10n_eg_edi_post_invoice_web_service(invoice)}

    def _cancel_invoice_edi(self, invoices):
        if self.code != 'eg_eta':
            return super()._cancel_invoice_edi(invoices)
        invoice = invoices
        return {invoice: self._cancel_invoice_edi_eta(invoice)}

    def _get_invoice_edi_content(self, move):
        if self.code != 'eg_eta':
            return super()._get_invoice_edi_content(move)
        return json.dumps(self._l10n_eg_eta_prepare_eta_invoice(move)).encode()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        if self.code != 'eg_eta':
            return super()._is_compatible_with_journal(journal)
        return journal.country_code == 'EG' and journal.type == 'sale'
