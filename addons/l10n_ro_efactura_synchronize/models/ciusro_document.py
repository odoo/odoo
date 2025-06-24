import json
from datetime import datetime

import requests
from lxml import etree

from odoo import _, api, models
from odoo.addons.l10n_ro_edi.models.ciusro_document import (
    make_efactura_request,
)

NS_DOWNLOAD = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


class L10nRoEdiDocument(models.Model):
    _inherit = 'l10n_ro_edi.document'

    @api.model
    def _request_ciusro_send_invoice(self, company, xml_data, move_type='out_invoice'):
        # Override to catch Timeout exception and set a sent state on the document
        # to avoid sending it several times; hoping that the synchronize will be able
        # to recover the index
        try:
            return super()._request_ciusro_send_invoice(company, xml_data, move_type)
        except requests.Timeout:
            return {'key_loading': False}

    @api.model
    def _request_ciusro_fetch_status(self, company, key_loading, session):
        # Override to process sent invoices with no ANAF index (due to timeout during
        # the sending of the invoide)
        if not key_loading:
            return {}
        return super()._request_ciusro_fetch_status(company, key_loading, session)

    @api.model
    def _request_ciusro_synchronize_invoices(self, company, session, nb_days=1):
        result = make_efactura_request(
            session=session,
            company=company,
            endpoint='listaMesajeFactura',
            method='GET',
            params={'zile': nb_days, 'cif': company.vat.replace('RO', '')},
        )
        if 'error' in result:
            return {'error': result['error']}

        try:
            msg_content = json.loads(result['content'])
        except ValueError:
            return {'error': _("The SPV data could not be parsed.")}

        if eroare := msg_content.get('eroare'):
            return {'error': eroare}

        received_bills_messages = []
        sent_invoices_accepted_messages = []
        sent_invoices_refused_messages = []
        for message in msg_content.get('mesaje'):

            # We need to call `_request_ciusro_download_answer` twice, once to recover
            # the original invoice data or error message using status='nok' and the
            # second one to get the signature using status=None
            # This is removed in the refactor in saas~18.4

            invoice_data = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                key_download=message['id'],
                company=company,
                session=session,
                status='nok'
            )
            signature_data = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                key_download=message['id'],
                company=company,
                session=session,
            )

            answer = dict()

            # If the signature data contains an error, this is a connection error
            if signature_data['error']:
                message['error'] = signature_data['error']
            else:
                answer['signature'] = {
                    'attachment_raw': signature_data['attachment_raw'],
                    'key_signature': signature_data['key_signature'],
                    'key_certificate': signature_data['key_certificate'],
                }

            # If the invoice data contains an error and the invoice is not refused, this is either
            # - a connection error
            # - a refused invoice
            if invoice_data['error']:
                if message['tip'] != 'ERORI FACTURA':
                    message['error'] = invoice_data['error']
                else:
                    answer['invoice'] = {
                        'error': invoice_data['error'],
                        'attachment_raw': invoice_data['attachment_raw'],
                    }
            else:
                root = etree.fromstring(invoice_data['attachment_raw'])
                answer['invoice'] = {
                    'name': root.findtext('.//cbc:ID', namespaces=NS_DOWNLOAD),
                    'amount_total': root.findtext('.//cbc:TaxInclusiveAmount', namespaces=NS_DOWNLOAD),
                    'buyer_vat': root.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                    'seller_vat': root.findtext('.//cac:AccountingCustomerParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                    'date': datetime.strptime(root.findtext('.//cbc:IssueDate', namespaces=NS_DOWNLOAD), '%Y-%m-%d').date(),
                    'attachment_raw': invoice_data['attachment_raw'],
                }

            message['answer'] = answer

            if message['tip'] == 'FACTURA TRIMISA':
                sent_invoices_accepted_messages.append(message)
            elif message['tip'] == 'ERORI FACTURA':
                sent_invoices_refused_messages.append(message)
            elif message['tip'] == 'FACTURA PRIMITA':
                received_bills_messages.append(message)

        return {
            'sent_invoices_accepted_messages': sent_invoices_accepted_messages,
            'sent_invoices_refused_messages': sent_invoices_refused_messages,
            'received_bills_messages': received_bills_messages,
        }
