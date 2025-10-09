# MojERacun version of the proxy user,
# seems to require a lot of adjustments to work directly with an extrenal service provier
# as the original edi_proxy_user is tooled for Odoo IAP

import contextlib
import json
import logging
import requests
import uuid

from odoo import api, fields, models, modules, tools, _
from odoo.tools import index_exists
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
# from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50
TIMEOUT = 30


class AccountEdiProxyClientUser(models.Model):
    _name = 'account_edi_mojerakun_proxy_client.user' # Separate entity
    _description = 'MojEracun external service proxy user for HR eRacun'
    # _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection=[('mojeracun', 'MojEracun')], ondelete={'mojeracun': 'cascade'}) # No other options
    # Copied from 'account_edi_proxy_client.user'
    active = fields.Boolean(default=True)
    #id_client = fields.Char(required=True) # Does not appear to be required here because it is only used in Odoo IAP auth
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    edi_identification = fields.Char(required=True, help="The unique id that identifies this user, typically the vat")
    edi_mode = fields.Selection(
        selection=[
            ('prod', 'Production mode'),
            ('test', 'Test mode'),
            ('demo', 'Demo mode'),
        ],
        string='EDI operating mode',
    )

    #_sql_constraints = [
    #    ('unique_id_client', 'unique(id_client)', 'This id_client is already used on another user.'),
    #    ('unique_active_edi_identification', '', 'This edi identification is already assigned to an active user'),
    #    ('unique_active_company_proxy', '', 'This company has an active user already created for this EDI type'),
    #]

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'account_edi_mojerakun_proxy_client_user_unique_active_edi_identification'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_edi_mojerakun_proxy_client_user_unique_active_edi_identification
                                 ON account_edi_mojerakun_proxy_client_user(edi_identification, proxy_type, edi_mode)
                              WHERE (active = True)
            """)
        if not index_exists(self.env.cr, 'account_edi_mojerakun_proxy_client_user_unique_active_company_proxy'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_edi_mojerakun_proxy_client_user_unique_active_company_proxy
                                 ON account_edi_mojerakun_proxy_client_user(company_id, proxy_type, edi_mode)
                              WHERE (active = True)
            """)

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = {}
        urls['mojeracun'] = {
            'prod': '???',
            'test': 'https://demo.moj-eracun.hr',
        }
        return urls

    def _get_server_url(self, proxy_type=None, edi_mode=None):
        proxy_type = proxy_type or self.proxy_type
        edi_mode = edi_mode or self.edi_mode
        proxy_urls = self._get_proxy_urls()
        # letting this traceback in case of a KeyError, as that would mean something's wrong with the code
        return proxy_urls[proxy_type][edi_mode]

    def _get_proxy_users(self, company, proxy_type):
        '''Returns proxy users associated with the given company and proxy type.
        '''
        return company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == proxy_type)

    def _make_request(self, url, params=False):
        ''' Make a request to proxy and handle the generic elements of the reponse (errors, new refresh token).
        '''
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': params or {},
            'id': uuid.uuid4().hex,
        }
        payload = params

        # Last barrier : in case the demo mode is not handled by the caller, we block access.
        if self.edi_mode == 'demo':
            raise AccountEdiProxyError("block_demo_mode", "Can't access the proxy in demo mode")

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=TIMEOUT,
                headers={'content-type': 'application/json', 'charset' :'utf-8'}
            )
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
            raise AccountEdiProxyError('connection_error',
                _('The url that this service requested returned an error. The url it tried to contact was %s', url))

        if 'error' in response:
            message = _('The url that this service requested returned an error. The url it tried to contact was %(url)s. %(error_message)s', url=url, error_message=response['error']['message'])
            if response['error']['code'] == 404:
                message = _('The url that this service tried to contact does not exist. The url was “%s”', url)
            raise AccountEdiProxyError('connection_error', message)

        return response

    def _call_mer_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'mojeracun':
            raise UserError(_('EDI user should be of type eRacun'))

        params_base = {
            'Username': self.company_id.l10n_hr_mer_username,
            'Password': self.company_id.l10n_hr_mer_password,
            'CompanyId': self.company_id.l10n_hr_mer_company_id,
            'CompanyBu': self.company_id.l10n_hr_mer_company_bu,
            'SoftwareId': self.company_id.l10n_hr_mer_software_id,
        }
        if params:
            params = params_base | params
        else:
            params = params_base
        params_to_delete = []
        for key, value in params.items():
            if not value:
                params_to_delete.append(key)
        for key in params_to_delete:
            params.pop(key)
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            # No need to handle Odoo IAP specific errors
            raise UserError(e.message)

        if 'error' in response:
            error_code = response['error'].get('code')
            error_message = response['error'].get('subject') or response['error'].get('data', {}).get('message')
            raise UserError(error_message or _('Connection error, please try again later.'))
        return response

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    # Crons not brought in yet
    def _cron_mer_get_new_documents(self):
        edi_users = self.search([('proxy_type', '=', 'mojeracun'), ('company_id.l10n_hr_mer_proxy_state', '=', 'receiver')])
        edi_users._mer_get_new_documents()

    def _cron_mer_get_message_status(self):
        edi_users = self.search([('proxy_type', '=', 'mojeracun'), ('company_id.l10n_hr_mer_proxy_state', '=', 'receiver')])
        edi_users._mer_get_message_status()

    def _cron_mer_get_participant_status(self):
        edi_users = self.search([('proxy_type', '=', 'mojeracun')])
        edi_users._mer_get_participant_status()

    def _cron_mer_webhook_keepalive(self):
        edi_users = self.search([('proxy_type', '=', 'mojeracun'), ('company_id.l10n_hr_mer_proxy_state', 'in', ['receiver'])])
        edi_users._mer_reset_webhook()

    # -------------------------------------------------------------------------
    # MOJERACUN API CALL METHODS
    # -------------------------------------------------------------------------
    
    def _mer_api_ping(self):
        """
        Checks if service is up.
        """
        return requests.get(f'{self._get_server_url()}/apis/v2/Ping/')

    def _mer_api_send(self, xml_file):
        """
        Send electronic document to a recipient.
        """
        self.ensure_one() # Calling this should only be done for one user, and there is no point in bundling things here
        params=json.dumps({
            'File': xml_file, # Needs to be JSON-escaped
        })
        response = self._call_mer_proxy('/apis/v2/send', params=params)
        return response

    def _mer_api_query_inbox(self, filter=None, electronic_id=None, status_id=None, date_from=None, date_to=None):
        """
        Status description. Query methods are refered as basic MER document statuses.
        When receiving response from query methods, you will get croatian names of statuses
        (U obradi, Poslan, Preuzet, Povučeno preuzimanje, Neuspjelo).
        """
        self.ensure_one()
        params={
            'Filter': filter,
            'ElectronicId': electronic_id,
            'StatusId': status_id,
            'From': date_from,
            'To': date_to,
        }
        response = self._call_mer_proxy('/apis/v2/queryInbox', params=params)
        return response

    def _mer_api_query_outbox(self, filter=None, electronic_id=None, status_id=None, invoice_year=None, invoice_number=None, date_from=None, date_to=None):
        """
        Query outbox is used to check the statuses of your sent documents. For this method, the API returns 10.000 results.
        """
        self.ensure_one()
        params={
            'Filter': filter,
            'ElectronicId': electronic_id,
            'StatusId': status_id,
            'InvoiceYear': invoice_year,
            'InvoiceNumber': invoice_number,
            'From': date_from,
            'To': date_to,
        }
        response = self._call_mer_proxy('/apis/v2/queryOutbox', params=params)
        return response

    def _mer_api_recieve_document(self, electronic_id):
        """
        Receive method is used for downloading documents. Both sent and incoming, eg. Inbox and Outbox documents.
        """
        # Response object just contains the bytestring XML in _content 
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
        }
        response = self._call_mer_proxy('/apis/v2/receive', params=params)
        return response

    def _mer_api_update_document_process_status(self, electronic_id, status_id, rejection_reason=None):
        """
        Document process status codes are used to update status of document after it has been
        downloaded or received in the system of the another information provider / access points.
        They are also referred as business document statuses.
        Statuses 4 and 99 cannot be modified via API.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'StatusId': status_id,
            'RejectReason': rejection_reason,
        }
        response = self._call_mer_proxy('/apis/v2/UpdateDokumentProcessStatus', params=params)
        return response

    def _mer_api_query_document_process_status_inbox(self, electronic_id=None, status_id=None, invoice_year=None, invoice_number=None, date_from=None, date_to=None, by_update_date=None):
        """
        Query inbox is used to discover new documents sent to your company or business unit. For this method, the API returns 20.000 results.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'StatusId': status_id,
            'InvoiceYear': invoice_year,
            'InvoiceNumber': invoice_number,
            'From': date_from,
            'To': date_to,
            'ByUpdateDate': by_update_date,
        }
        response = self._call_mer_proxy('/apis/v2/queryDocumentProcessStatusInbox', params=params)
        return response

    def _mer_api_query_document_process_status_outbox(self, electronic_id=None, status_id=None, invoice_year=None, invoice_number=None, date_from=None, date_to=None, by_update_date=None):
        """
        Query inbox is used to discover new documents sent to your company or business unit. For this method, the API returns 20.000 results.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'StatusId': status_id,
            'InvoiceYear': invoice_year,
            'InvoiceNumber': invoice_number,
            'From': date_from,
            'To': date_to,
            'ByUpdateDate': by_update_date,
        }
        response = self._call_mer_proxy('/apis/v2/queryDocumentProcessStatusOutbox', params=params)
        return response

    def _mer_api_update_document_process_status(self, electronic_id):
        """
        Notify import method is used for sending an information that an invoice is imported into an ERP.
        You can use it to update which document you have successfully imported and to make procedure for
        importing  only documents that you previously didn’t download and import.
        """
        self.ensure_one()
        response = self._call_mer_proxy(f'/apis/v2/notifyimport/{electronic_id}', params={})
        return response

    def _mer_api_mark_paid(self, electronic_id, payment_date, payment_method):
        """
        Methods for sending payment information for sent documents.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'PaymentDate': payment_date,
            'PaymentMethod': payment_method,
        }
        response = self._call_mer_proxy('/api/fiscalization/markPaid', params=params)
        return response

    def _mer_api_mark_paid_without_id(self, electronic_id, internal_mark, issue_date, sender_id, recipient_id, payment_date, payment_amount, payment_method):
        """
        Methods for sending payment information for sent documents.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'InternalMark': internal_mark,
            'IssueDate': issue_date,
            'SenderIdentifierValue': sender_id,
            'RecipientIdentifierValue': recipient_id,
            'PaymentDate': payment_date,
            'PaymentAmount': payment_amount,
            'PaymentMethod': payment_method,
        }
        response = self._call_mer_proxy('/api/fiscalization/markPaidWithoutElectronicID', params=params)
        return response

    def _mer_api_reject_with_id(self, electronic_id, rejection_date, rejection_type, rejection_desc):
        """
        Methods for sending information regarding rejection for received electronic documents.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'RejectionDate': rejection_date,
            'RejectionReasonType': rejection_type,
            'RejectionReasonDescription': rejection_desc,
        }
        response = self._call_mer_proxy('/api/fiscalization/markPaidWithoutElectronicID', params=params)
        return response

    def _mer_api_reject_without_id(self, internal_mark, issue_date, sender_id, recipient_id, rejection_date, rejection_type, rejection_desc):
        """
        Methods for sending information regarding rejection for received electronic documents.
        """
        self.ensure_one()
        params={
            'InternalMark': internal_mark,
            'IssueDate': issue_date,
            'SenderIdentifierValue': sender_id,
            'RecipientIdentifierValue': recipient_id,
            'RejectionDate': rejection_date,
            'RejectionReasonType': rejection_type,
            'RejectionReasonDescription': rejection_desc,
        }
        response = self._call_mer_proxy('/api/fiscalization/markPaidWithoutElectronicID', params=params)
        return response

    def _mer_api_report_operation(self, invoice_xml, delivery_date, is_copy, invoice_type):
        """
        Report operation is only used in case of unsuccessful fiscalization using API method SEND.
        When sending document gets rejected from SEND method, you need to create API request for
        sending electronic document to eReporting system of Tax Authority via MER service. After
        you got success response from sending document to this API, you have an option do deliver
        document to the customer in any format and send option (paper, PDF as an attachment to an email)
        """
        self.ensure_one()
        params=json.dumps({
            'xmlInvoice': invoice_xml, # Needs to be JSON-escaped
            'DeliveryDate': delivery_date,
            'IsCopy': is_copy,
            'InvoiceType': invoice_type,
        })
        response = self._call_mer_proxy('/api/fiscalization/eReporting', params=params)
        return response

    def _mer_api_check_id(self, id_type, id_value):
        """
        This endpoint checks if a given identifier is registered in the AMS system and returns
        its registration status. If the identifier is found, it returns a 200 OK status;
        otherwise, it returns an appropriate error status.
        """
        self.ensure_one()
        params={
            'IdentifierType': id_type,
            'IdentifierValue': id_value,
        }
        response = self._call_mer_proxy('/api/mps/check', params=params)
        return response

    def _mer_api_check_fiscalization_status(self, electronic_id, message_type):
        """
        This endpoint retrieves the fiscalization status of a document using its ElectronicId and MessageType.
        """
        self.ensure_one()
        params={
            'ElectronicId': electronic_id,
            'MessageType': message_type,
        }
        response = self.edi_user._call_mer_proxy('/api/fiscalization/status', params=params)
        return response


    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    #@handle_demo
    def _check_user_on_alternative_service(self):
        # This is not currently used as there is no good way to handle it (and it is not necessary)
        # MER has a method for checking a specific separate identifier, but it doesn't appear to mirror this in function
        return

    def _mer_register_proxy_user(self, company, proxy_type, edi_mode, mer_username, mer_password, mer_company_id, mer_company_bu, mer_software_id):
        """Creates a new user record for MojEracun service and sets up authentification credentials for the company."""
        company.l10n_hr_mer_proxy_state = 'receiver'
        company.l10n_hr_mer_username = mer_username
        company.l10n_hr_mer_password = mer_password
        company.l10n_hr_mer_company_id = mer_company_id
        company.l10n_hr_mer_company_bu = mer_company_bu
        company.l10n_hr_mer_software_id = mer_software_id
        return self.create({
            'company_id': company.id,
            'proxy_type': proxy_type,
            'edi_mode': edi_mode,
            'edi_identification': company.l10n_hr_mer_company_id,
        })

    # There doesn't appear to be corresponding functionality in MER, or it is broken at the moment
    """def _eracun_get_participant_status(self):
        for edi_user in self:
            try:
                proxy_user = edi_user._call_eracun_proxy("/api/eracun/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating eRacun participant status: %s', e)
                continue

            if proxy_user['eracun_state'] in {'not_registered', 'receiver', 'rejected'}:
                edi_user.company_id.l10n_hr_eracun_proxy_state = proxy_user['eracun_state']"""

    # Likely not necessary
    def _get_mer_company_details(self):
        self.ensure_one()
        return {
            'Username': self.company_id.l10n_hr_mer_username,
            'Password': self.company_id.l10n_hr_mer_password,
            'CompanyId': self.company_id.l10n_hr_mer_company_id,
            'CompanyBu': self.company_id.l10n_hr_mer_company_bu,
            'SoftwareId': self.company_id.l10n_hr_mer_software_id,
        }

    def _mer_deregister_participant(self):
        self.ensure_one()

        if self.company_id.l10n_hr_mer_proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_mer_get_message_status()
            self._cron_mer_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        self.company_id.l10n_hr_mer_proxy_state = 'not_registered'
        self.unlink()

    def _mer_import_invoice(self, attachment, electronic_id, mer_document_status, business_document_status):
        """
        Save new documents in an accounting journal, when one is specified on the company.
        :param attachment: the new document
        :param electronic_id: ElectronicId assigned to the document by MER
        :param mer_document_status: basic status of the recieved document on MER
        :param business_document_status: business status of the document on eRacun
        :return: `True` if the document was saved, `False` if it was not
        """
        self.ensure_one()
        journal = self.company_id.eracun_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'l10n_hr_mer_document_id': electronic_id,
            'l10n_hr_mer_document_status': mer_document_status,
            'l10n_hr_business_document_status': business_document_status,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        # This should be the same for eRacun since the UBL format is universal
        move._extend_with_attachments(attachment, new=True)
        move._message_log(
            body=_(
                "eRacun document (ElectroicId: %(electronic_id)s) has been received from MojEracun successfully.",
                electronic_id=electronic_id,
            ),
            attachment_ids=attachment.ids,
        )
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return True

    def _mer_get_new_documents(self, undelivered=True, notify=True):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self._context.get('mer_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        if undelivered:
            params = {
                'Filter': 'Undelivered'
            }
        else:
            params = {}
        imported_documents = {}
        for edi_user in self:
            # This needs to be adjusted for MER: auth params, /apis/v2/queryInbox, 'Filter': 'Undelivered' - up to 10000 documents
            try:
                # request all documents that haven't been acknowledged
                response = edi_user._call_mer_proxy(
                    "/apis/v2/queryInbox",
                    params=params,
                )
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from MojEracun Proxy: %s', e.message,
                )
                continue

            print("--- DEBUG: _mer_get_new_documents() response._content:", response.json(), "---")
            documents = [
                {
                    'ElectronicId': document['ElectronicId'],
                    'StatusId': document['StatusId']
                }
                for document in response.json()
            ]
            if not documents:
                continue

            need_retrigger = need_retrigger or len(documents) > job_count
            documents = documents[:job_count]

            proxy_acks = []
            # retrieve attachments for filtered messages
            # Adjustments for MER: /apis/v2/receive, auth fields, 'ElectronicId' of a specific document to get one-by-one
            for document in documents:
                document.update({'xml': edi_user._call_mer_proxy(
                    "/apis/v2/receive",
                    params={'ElectronicId': document['ElectronicId']},
                )._content})
            
            print("--- DEBUG: _mer_get_new_documents() documents:", [document.keys() for document in documents], "---")
            # Adjustments for MER: no need to decode, process and import UBL invoice
            for document in documents:
                filename = f'mojeracun_{document['ElectronicId']}_attachment'  # default to attachment, which should not usually happen
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"{filename}.xml",
                        "raw": document['xml'],
                        "type": "binary",
                        "mimetype": "application/xml",
                    }
                )
                # ElectronucId and StatusID are ints on MER, need to be converted back and forth
                # Currently doesn't process business status correctly - what is it?
                if edi_user._mer_import_invoice(attachment, str(document['ElectronicId']), str(document['StatusId']), '0'):
                    # Only acknowledge when we saved the document somewhere
                    proxy_acks.append(document['ElectronicId'])

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if notify:
                for electronic_id in proxy_acks:
                    # Adjustments for MER: /apis/v2/notifyimport/[ElectronicId]
                    edi_user._call_mer_proxy(
                        f"/apis/v2/notifyimport/{electronic_id}",
                    )
            imported_documents.update({edi_user.id: proxy_acks})
        if need_retrigger:
            self.env.ref('l10n_hr_edi.ir_cron_mer_get_new_documents')._trigger()
        print("--- DEBUG: _mer_get_new_documents() imported_documents:", imported_documents, "---")
        # Return which documents were imported, for testing reasons
        return imported_documents

    def _eracun_get_message_status(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        # MER: /apis/v2/queryDocumentProcessStatusInbox, /apis/v2/queryDocumentProcessStatusOutbox
        job_count = self._context.get('mer_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user_moves = self.env['account.move'].search(
                [
                    ('eracun_move_state', '=', 'processing'),
                    ('company_id', '=', edi_user.company_id.id),
                ],
                limit=job_count + 1,
            )
            if not edi_user_moves:
                continue

            need_retrigger = need_retrigger or len(edi_user_moves) > job_count
            message_uuids = {move.eracun_message_uuid: move for move in edi_user_moves[:job_count]}
            messages_to_process = edi_user._call_eracun_proxy(
                "/api/eracun/1/get_document",
                params={'message_uuids': list(message_uuids.keys())},
            )

            for uuid, content in messages_to_process.items():
                if uuid == 'error':
                    # this rare edge case can happen if the participant is not active on the proxy side
                    # in this case we can't get information about the invoices
                    edi_user_moves.eracun_move_state = 'error'
                    log_message = _("eRacun error: %s", content['message'])
                    edi_user_moves._message_log_batch(bodies={move.id: log_message for move in edi_user_moves})
                    break

                move = message_uuids[uuid]
                if content.get('error'):
                    # "eRacun request not ready" error:
                    # thrown when the IAP is still processing the message
                    if content['error'].get('code') == 702:
                        continue

                    move.eracun_move_state = 'error'
                    move._message_log(body=_("eRacun error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
                    continue

                move.eracun_move_state = content['state']
                move._message_log(body=_('eRacun status update: %s', content['state']))

                edi_user._call_eracun_proxy(
                    "/api/eracun/1/ack",
                    params={'message_uuids': list(message_uuids.keys())},
                )
        if need_retrigger:
            self.env.ref('l10n_hr_eracun.ir_cron_eracun_get_message_status')._trigger()
