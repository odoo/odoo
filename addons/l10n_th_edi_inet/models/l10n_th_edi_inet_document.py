# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from stdnum.th import tin

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import hash_sign, verify_hash_signed

INET_URLS = {
    'staging': 'https://uatservice-etax.one.th',
    'production': 'https://service-etax.one.th',
}
INET_TIMEOUT = 60
INET_NOT_FOUND_ERROR_CODES = ('ER019', 'AU045')
INET_DUPLICATE_ERROR_CODE = 'ER011'
INET_RD_STATES = {
    'Sending': 'sending',
    'Under RD review': 'in_review',
    'Submitted': 'accepted',
    'Failed': 'failed',
}
INET_RD_STATUS_SCOPE = 'l10n_th_edi_inet_rd_status'


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
            {'ServiceCode': 'S04', 'callbackUrl': self._l10n_th_edi_inet_get_callback_url()},
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
                vals = {'l10n_th_edi_state': 'signed', 'l10n_th_edi_error': False, 'l10n_th_edi_rd_state': 'waiting'}
        elif status == 'PC':
            vals = {'l10n_th_edi_state': 'processing', 'l10n_th_edi_error': self._l10n_th_edi_inet_format_error(response)}
        elif status == 'ER':
            vals = {'l10n_th_edi_state': 'error', 'l10n_th_edi_error': self._l10n_th_edi_inet_format_error(response)}
        else:
            vals = {'l10n_th_edi_state': 'unknown', 'l10n_th_edi_error': self.env._("Unexpected answer from INET: %s", response)}
        self.write(vals)

    # -------------------------------------------------------------------------
    # RD STATUS
    # -------------------------------------------------------------------------

    def _l10n_th_edi_inet_get_callback_url(self):
        """ INET calls this URL when the RD status of the document changes. Its token identifies the document. """
        token = hash_sign(self.sudo().env, INET_RD_STATUS_SCOPE, [self._name, self.id])
        return f'{self.get_base_url()}/l10n_th_edi_inet/rd_status/{token}'

    @api.model
    def _l10n_th_edi_inet_get_document_from_token(self, token):
        try:
            document_ref = verify_hash_signed(self.sudo().env, INET_RD_STATUS_SCOPE, token)
        except ValueError:
            return None
        if document_ref:
            model_name, document_id = document_ref
            return self.env[model_name].sudo().browse(document_id).exists()
        return None

    def _l10n_th_edi_inet_update_rd_state(self, response):
        """ Update the RD status from INET's webhook or status answer, which carry the same values. """
        if rd_state := INET_RD_STATES.get(response.get('rdStatus')):
            self.write({
                'l10n_th_edi_rd_state': rd_state,
                'l10n_th_edi_error': rd_state == 'failed' and response.get('rdMessage'),
            })

    def _l10n_th_edi_inet_fetch_rd_state(self):
        self.ensure_one()
        response, error = self._l10n_th_edi_inet_request('/getdocument/getdocumentstatus', {
            'TransactionCode': self.l10n_th_edi_inet_transaction_code,
        })
        if error or response.get('status') == 'ER':
            self.l10n_th_edi_error = error or self._l10n_th_edi_inet_format_error(response)
        else:
            self._l10n_th_edi_inet_update_rd_state(response)

    def action_l10n_th_edi_inet_update_rd_state(self):
        for document in self:
            document._l10n_th_edi_inet_fetch_rd_state()

    @api.model
    def _cron_l10n_th_edi_inet_update_rd_states(self):
        """ Fallback for the webhooks that did not reach Odoo. """
        documents = self.search([
            ('l10n_th_edi_rd_state', 'in', ('waiting', 'sending', 'in_review')),
            # A document found at INET by its number has no transaction code to follow.
            ('l10n_th_edi_inet_transaction_code', '!=', False),
        ])
        self.env['ir.cron']._commit_progress(remaining=len(documents))
        for document in documents:
            document._l10n_th_edi_inet_fetch_rd_state()
            if not self.env['ir.cron']._commit_progress(1):
                break
