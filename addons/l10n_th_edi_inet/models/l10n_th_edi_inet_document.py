# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from stdnum.th import tin

from odoo import fields, models
from odoo.exceptions import UserError

INET_URLS = {
    'staging': 'https://uatservice-etax.one.th',
    'production': 'https://service-etax.one.th',
}
INET_TIMEOUT = 60
INET_NOT_FOUND_ERROR_CODES = ('ER019', 'AU045')
INET_DUPLICATE_ERROR_CODE = 'ER011'


class L10nThEdiInetDocument(models.AbstractModel):
    _name = 'l10n_th_edi_inet.document'
    _inherit = ['l10n_th_edi.document']
    _description = "Thai e-Tax Document Signed by INET"

    l10n_th_edi_inet_transaction_code = fields.Char(string="INET Transaction Code", copy=False, readonly=True)

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------

    def _l10n_th_edi_inet_request(self, endpoint, data, files=None):
        """ Post a multipart request to INET.

        :return: (response_dict, error_message)
        """
        company = self.company_id.sudo()
        base_url = INET_URLS['staging' if company.l10n_th_edi_inet_staging_mode else 'production']
        form_data = {
            'SellerTaxId': tin.compact(company.vat or ''),
            'SellerBranchId': company._l10n_th_edi_get_branch_code(),
            'SourceSystem': 'Odoo',
            **({'APIKey': company.l10n_th_edi_inet_api_key} if company.l10n_th_edi_inet_api_key else {}),
            **data,
        }
        try:
            response = requests.post(
                base_url + endpoint,
                # Sending every field as a file part forces a multipart body, which is what INET expects.
                files={key: (None, value) for key, value in form_data.items()} | (files or {}),
                headers={'Authorization': company.l10n_th_edi_inet_authorization_code},
                timeout=INET_TIMEOUT,
            )
            response.raise_for_status()
            return response.json(), None
        except (requests.RequestException, ValueError) as error:
            return {}, self.env._("Could not reach INET: %s", error)

    def _l10n_th_edi_inet_download(self, url):
        """ Download a file from a link returned by INET. The links expire after 5 minutes.

        :return: (file_content, error_message)
        """
        try:
            response = requests.get(url, timeout=INET_TIMEOUT)
            response.raise_for_status()
            return response.content, None
        except requests.RequestException as error:
            return None, self.env._("Could not download the signed file from INET: %s", error)

    # -------------------------------------------------------------------------
    # SENDING
    # -------------------------------------------------------------------------

    def _l10n_th_edi_check(self, document_values):
        # EXTENDS 'l10n_th_edi.document'
        errors = super()._l10n_th_edi_check(document_values)
        if not self.company_id.sudo().l10n_th_edi_inet_authorization_code:
            errors.append(self.env._("Set the INET authorization code in the settings."))
        return errors

    def _l10n_th_edi_send(self):
        # EXTENDS 'l10n_th_edi.document'
        self.ensure_one()
        # INET may already hold this document: it must never be signed twice.
        if self.l10n_th_edi_state in ('processing', 'unknown') and self._l10n_th_edi_inet_fetch():
            return

        document_values = self._l10n_th_edi_get_document_values()
        if errors := self._l10n_th_edi_check(document_values):
            raise UserError("\n".join(errors))

        file_name = self._l10n_th_edi_get_file_name(document_values)
        response, error = self._l10n_th_edi_inet_request(
            '/service/etaxsigndocument',
            {'ServiceCode': 'S04'},
            files={
                'XMLContent': (f'{file_name}.xml', self._l10n_th_edi_get_xml(document_values), 'application/xml'),
                'PDFContent': (f'{file_name}.pdf', self._l10n_th_edi_get_pdf_content(), 'application/pdf'),
            },
        )
        if error:
            self.write({'l10n_th_edi_state': 'unknown', 'l10n_th_edi_error': error})
        else:
            self.l10n_th_edi_inet_transaction_code = response.get('status') != 'ER' and response.get('transactionCode')
            self._l10n_th_edi_inet_process_response(response, document_values)

    def _l10n_th_edi_inet_fetch(self):
        """ Update the document with what INET holds.

        :return: False if INET confirmed that it has no such document, so that it can be sent.
        """
        self.ensure_one()
        document_values = self._l10n_th_edi_get_document_values()
        if self.l10n_th_edi_inet_transaction_code:
            response, error = self._l10n_th_edi_inet_request('/getdocument/getdocumentstatus', {
                'TransactionCode': self.l10n_th_edi_inet_transaction_code,
            })
        else:
            # The answer to the sending was lost: look the document up by its number.
            response, error = self._l10n_th_edi_inet_request('/getdocument/getdocumentparams', {
                'InvoiceNumber': document_values['number'],
                'InvoiceDate': document_values['date'].strftime('%Y%m%d'),
            })
            if response.get('totalRecord'):
                # One pair of links per document found with that number.
                response = {**response, 'xmlURL': response['xmlURL'][0], 'pdfURL': response['pdfURL'][0]}
        if error:
            self.l10n_th_edi_error = error
            return True
        if response.get('errorCode') in INET_NOT_FOUND_ERROR_CODES:
            return False
        self._l10n_th_edi_inet_process_response(response, document_values, found_by_number=not self.l10n_th_edi_inet_transaction_code)
        return True

    def _l10n_th_edi_inet_format_error(self, response):
        return f"[{response.get('errorCode')}] {response.get('errorMessage')}"

    def _l10n_th_edi_inet_process_response(self, response, document_values, found_by_number=False):
        status = response.get('status')
        if response.get('errorCode') == INET_DUPLICATE_ERROR_CODE:
            # INET already holds a document with this number, and returns its signed files.
            status, found_by_number = 'OK', True
        if status == 'OK':
            xml_content, error = self._l10n_th_edi_inet_download(response.get('xmlURL'))
            if not error:
                pdf_content, error = self._l10n_th_edi_inet_download(response.get('pdfURL'))
            if error:
                # The document is signed, and its status gives new download links.
                vals = {'l10n_th_edi_state': 'processing', 'l10n_th_edi_error': error}
            elif found_by_number and not self._l10n_th_edi_is_same_document(xml_content, document_values):
                vals = {
                    'l10n_th_edi_state': 'error',
                    'l10n_th_edi_error': self.env._("INET holds another document numbered %s.", document_values['number']),
                }
            else:
                self._l10n_th_edi_save_signed_files(xml_content, pdf_content, document_values)
                vals = {'l10n_th_edi_state': 'signed', 'l10n_th_edi_error': False}
        elif status == 'PC':
            vals = {'l10n_th_edi_state': 'processing', 'l10n_th_edi_error': self._l10n_th_edi_inet_format_error(response)}
        elif status == 'ER':
            vals = {'l10n_th_edi_state': 'error', 'l10n_th_edi_error': self._l10n_th_edi_inet_format_error(response)}
        else:
            vals = {'l10n_th_edi_state': 'unknown', 'l10n_th_edi_error': self.env._("Unexpected answer from INET: %s", response)}
        self.write(vals)
