import base64

import requests
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from .utils import (
    _request_ciusro_download_answer,
    _request_ciusro_fetch_status,
    _request_ciusro_send_invoice,
    _request_ciusro_synchronize_invoices,
     _request_ciusro_xml_to_pdf,
)

HOLDING_DAYS = 3  # Arbitrary


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ro_edi_document_ids = fields.One2many(
        comodel_name='l10n_ro_edi.document',
        inverse_name='invoice_id',
    )
    l10n_ro_edi_state = fields.Selection(
        selection=[
            ('invoice_not_indexed', 'Not indexed'),
            ('invoice_sent', 'Sent'),
            ('invoice_refused', 'Refused'),
            ('invoice_validated', 'Validated'),
        ],
        string='E-Factura Status',
        compute='_compute_l10n_ro_edi_state',
        store=True,
        help="""- Not indexed: Invoice index was not received on time due to a server timeout
                - Sent: Successfully sent to the SPV, waiting for validation
                - Validated: Sent & validated by the SPV
                - Refused: Validation error from the SPV
        """,
    )
    l10n_ro_edi_index = fields.Char(string='E-Factura Index', readonly=True, copy=False)

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends('l10n_ro_edi_document_ids')
    def _compute_l10n_ro_edi_state(self):
        self.l10n_ro_edi_state = False
        for move in self:
            # set the state of the move depending on the last document created
            move.l10n_ro_edi_state = move.l10n_ro_edi_document_ids and move.l10n_ro_edi_document_ids.sorted()[0].state

    @api.depends('l10n_ro_edi_state')
    def _compute_show_reset_to_draft_button(self):
        """ Prevent user to reset move to draft when there's an
            active sending document or a successful response has been received """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and move.l10n_ro_edi_state in ('invoice_sent', 'invoice_validated'):
                move.show_reset_to_draft_button = False

    ################################################################################
    # EDI
    ################################################################################

    def _get_import_file_type(self, file_data):
        """ Identify OIOUBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and 'CIUS-RO' in customization_id
        ):
            return 'account.edi.xml.ubl_ro'

        return super()._get_import_file_type(file_data)

    ################################################################################
    # Send Logics
    ################################################################################

    def _l10n_ro_edi_get_pre_send_errors(self, xml_data):
        """ Compute all possible common errors before sending the XML to the SPV """
        self.ensure_one()
        errors = []
        if self.state != 'posted':
            errors.append(_('Only posted entries can be sent to SPV.'))
        if not self.company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))
        if not xml_data:
            errors.append(_('CIUS-RO XML attachment not found.'))
        if self.l10n_ro_edi_document_ids:
            errors.append(_('The invoice has already been sent to the SPV.'))
        return errors

    def _l10n_ro_edi_send_invoice(self, xml_data):
        """
        This method send xml_data to the Romanian SPV using the single invoice's (self) data.
        The invoice's company and move_type will be used to calculate the required params in the send request.
        The state of the document deletion/creation are as follows:

         - Pre-check any errors from the invoice's pre_send check before sending
         - Send to E-Factura

        :param xml_data: string of the xml data to be sent
        :return: the `list` of errors that occured during the sending and processing of data, if any
        """
        self.ensure_one()
        if errors := self._l10n_ro_edi_get_pre_send_errors(xml_data):
            self.message_post(body=_("The invoice is not ready to be sent: %s", ", ".join(errors)))
            return errors

        self.env['res.company']._with_locked_records(self)
        result = _request_ciusro_send_invoice(
            company=self.company_id,
            xml_data=xml_data,
            move_type=self.move_type,
            is_b2b=self.partner_id.commercial_partner_id.is_company,
        )
        if 'error' in result:
            self.message_post(body=_(
                "Error when trying to send the e-Factura to the SPV: %s",
                result['error']
            ))
            return [result['error']]

        self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sent',
            'attachment': base64.b64encode(xml_data),
        })
        if result['key_loading']:
            self.l10n_ro_edi_index = result['key_loading']
            self.message_post(body=_(
                "The e-Factura has been sent and is now being validated by the SPV with index key: %s",
                self.l10n_ro_edi_index,
            ))
        else:
            self.l10n_ro_edi_state = 'invoice_not_indexed'
            self.message_post(body=_(
                "SPV failed to return with an index on time, synchronize this invoice to recover the index and the status."
            ))

        if self._can_commit():
            self.env.cr.commit()
        return None

    def _l10n_ro_edi_fetch_invoice_sent_documents(self):
        """
        This method loops over all invoice with sending document in `self`. For each of them,
        it pre-checks errors and make a fetch request for the invoice. Then:

         - if no answer is received, it will do nothing on the current invoice
         - if there is an error during the communication with the server -> log it in the chatter
         - else (receives `key_download`) -> immediately make a download request and process it:
            - if there is an error during the communication with the server -> log it in the chatter
            - if 'nok', then the invoice has been refused by ANAF -> create a refused document
            - if 'ok', then the invoice has been accepted by ANAF -> create a success document
        """
        session = requests.Session()
        invoices_to_fetch = self.filtered(lambda inv: inv.l10n_ro_edi_state == 'invoice_sent')
        documents_to_create = []
        document_ids_to_delete = []

        for invoice in invoices_to_fetch:
            self.env['res.company']._with_locked_records(invoice)
            result = _request_ciusro_fetch_status(
                company=invoice.company_id,
                key_loading=invoice.l10n_ro_edi_index,
                session=session,
            )
            if not result:  # SPV is still processing the XML (no answer yet); do nothing
                invoice.message_post(body=_("SPV has not finished processing the invoice, try again later."))
                continue

            if 'error' in result:  # Fetch error
                invoice.message_post(body=_(
                    "Error when trying to fetch the E-Factura status from the SPV: %s",
                    result['error']
                ))
                continue

            # SPV finished the validation process and sent us an answer containing: `key_download`` a key
            # to obtain the signature and, if the invoice is refused, the reason why.
            download_data = _request_ciusro_download_answer(
                company=invoice.company_id,
                key_download=result['key_download'],
                session=session,
            )
            if 'error' in download_data:  # Fetch error
                invoice.message_post(body=_(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    result['error']
                ))
                continue

            document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

            document_data = {
                'invoice_id': invoice.id,
                'key_download': result['key_download'],
                'key_signature': download_data['signature']['key_signature'],
                'key_certificate': download_data['signature']['key_certificate'],
                'attachment': base64.b64encode(download_data['signature']['attachment_raw']),
            }
            if result['state_status'] == 'nok':  # Invoice refused
                error_message = download_data['invoice']['error'].replace('\t', '')
                invoice.message_post(body=_(
                    "This invoice was refused by the SPV for the following reason: %s",
                    error_message
                ))
                document_data.update({
                    'state': 'invoice_refused',
                    'message': error_message,
                })
            else:  # Invoice accepted
                invoice.message_post(body=_("This invoice has been accepted by the SPV."))
                document_data['state'] = 'invoice_validated'

            documents_to_create.append(document_data)

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()
        self.env['l10n_ro_edi.document'].sudo().create(documents_to_create)
        if self._can_commit():
            self.env.cr.commit()

    @api.model
    def _l10n_ro_edi_fetch_invoices(self):
        """ Synchronize bills/invoices from SPV """
        result = _request_ciusro_synchronize_invoices(
            company=self.env.company,
            session=requests.Session(),
        )
        if 'error' in result:
            raise UserError(result['error'])

        if result['sent_invoices_accepted_messages']:
            self._l10n_ro_edi_process_invoice_accepted_messages(result['sent_invoices_accepted_messages'])

        if result['sent_invoices_refused_messages']:
            self._l10n_ro_edi_process_invoice_refused_messages(result['sent_invoices_refused_messages'])

        if result['received_bills_messages']:
            self._l10n_ro_edi_process_bill_messages(result['received_bills_messages'])

        # Non-indexed moves that were not processed after some time have probably been refused by the SPV. Since
        # there is no way to recover the index for refused invoices, we simply refuse them manually without proper reason.
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('l10n_ro_edi_index', '=', False)
            & Domain('l10n_ro_edi_state', '=', 'invoice_not_indexed')
        )
        non_indexed_invoices = self.env['account.move'].search(domain)

        document_ids_to_delete = []
        for invoice in non_indexed_invoices:
            # At that point, only one sent document should exists on an invoice
            sent_document = invoice.l10n_ro_edi_document_ids

            if (fields.Datetime.today() - sent_document.create_date).days > HOLDING_DAYS:
                document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

                error_message = _(
                    "The invoice has probably been refused by the SPV. We were unable to recover the reason of the refusal because "
                    "the invoice had not received its index. Duplicate the invoice and attempt to send it again."
                )
                invoice.message_post(body=error_message)
                self.env['l10n_ro_edi.document'].sudo().create({
                    'invoice_id': invoice.id,
                    'state': 'invoice_refused',
                    'message': error_message,
                })

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

        if self._can_commit():
            self.env.cr.commit()

    @api.model
    def _l10n_ro_edi_process_invoice_accepted_messages(self, sent_invoices_accepted_messages):
        ''' Process the validation messages of invoices sent

            It will also attempt to recover the original invoices, that are missing their index,
            by matching the name returned by the server and the one in the database.

            note: There is an edge case where 2 messages have the same invoice name but different indexes in
            their data; this could be due to a resequencing of the invoice and/or re-sending of an invoice. In
            that case coupled with name matching where none of the two invoices received an index, all signatures
            are added to the invoice; the user will have to manually update/select the correct one.

            For example: 2 invoices in the database
                - 11 already sent and should have gotten index AA, but did not receive it
                - 12 not sent
            Resequence them: 11->12 and 12->11
            Send new 11 that has not yet been sent, it should have gotten index AB but did not receive it.
            => In the messages, 2 invoices with name 11 and both index AA and AB.
        '''
        invoice_names = {message['answer']['invoice']['name'] for message in sent_invoices_accepted_messages if 'error' not in message['answer']}
        invoice_indexes = [message['id_solicitare'] for message in sent_invoices_accepted_messages]
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_sale_types())
            & (
                (
                    Domain('l10n_ro_edi_index', 'in', invoice_indexes)
                    & Domain('l10n_ro_edi_state', '=', 'invoice_sent')
                )
                | (
                    Domain('name', 'in', list(invoice_names))
                    & Domain('l10n_ro_edi_index', '=', False)
                    & Domain('l10n_ro_edi_state', '=', 'invoice_not_indexed')
                )
            )
        )
        invoices = self.env['account.move'].search(domain)

        document_ids_to_delete = []
        index_to_move = {move.l10n_ro_edi_index: move for move in invoices}
        name_to_move = {move.name: move for move in invoices}
        for message in sent_invoices_accepted_messages:
            invoice = index_to_move.get(message['id_solicitare'])

            if not invoice:
                # The move related to the message does not have an index
                if 'error' in message['answer'] or not name_to_move.get(message['answer']['invoice']['name']):
                    continue

                # An invoice with the same name has been found
                invoice = name_to_move.get(message['answer']['invoice']['name'])

                # Update the index of invoices succesfully sent but without SPV indexes due to server
                # time-out for unknown reasons during the upload
                invoice.l10n_ro_edi_index = message['id_solicitare']
                invoice.l10n_ro_edi_state = 'invoice_sent'

            if 'error' in message['answer']:
                invoice.message_post(body=_(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    message['answer']['error']
                ))
                continue

            # Only delete invoice_sent documents and not all because one invoice can contain several signature due to
            # the edge case where 2 messages have the same invoice name but different indexes in their data; this could
            # be due to a resequencing of the invoice and/or re-sending of an invoice. In that case coupled with name
            # matching where none of the two invoices received an index, all signatures are added to the invoice; the
            # user will have to manually update/select the correct one.
            document_ids_to_delete += invoice.l10n_ro_edi_document_ids.filtered(lambda document: document.state == 'invoice_sent').ids

            invoice.message_post(body=_("This invoice has been accepted by the SPV."))
            self.env['l10n_ro_edi.document'].sudo().create({
                'invoice_id': invoice.id,
                'state': 'invoice_validated',
                'key_download': message['id'],
                'key_signature': message['answer']['signature']['key_signature'],
                'key_certificate': message['answer']['signature']['key_certificate'],
                'attachment': message['answer']['signature']['attachment_raw'],
            })

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

    @api.model
    def _l10n_ro_edi_process_invoice_refused_messages(self, sent_invoices_refused_messages):
        ''' Process the refusal messages of invoices sent

            For refused invoices, it is impossible to recover the original invoice from the message content like
            in `_l10n_ro_edi_process_invoice_accepted_messages` since the message only contains the index and
            error message (as relevant information).
        '''
        refused_invoice_indexes = [message['id_solicitare'] for message in sent_invoices_refused_messages]
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_sale_types())
            & Domain('l10n_ro_edi_index', 'in', refused_invoice_indexes)
            & Domain('l10n_ro_edi_state', '=', 'invoice_sent')
        )
        invoices = self.env['account.move'].search(domain)
        index_to_move = {move.l10n_ro_edi_index: move for move in invoices}

        document_ids_to_delete = []
        for message in sent_invoices_refused_messages:
            invoice = index_to_move.get(message['id_solicitare'])
            if not invoice:
                continue

            if 'error' in message['answer']:
                invoice.message_post(body=_(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    message['answer']['error']
                ))
                continue

            document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

            error_message = message['answer']['invoice']['error'].replace('\t', '')
            invoice.message_post(body=_(
                "This invoice was refused by the SPV for the following reason: %s",
                error_message
            ))
            self.env['l10n_ro_edi.document'].sudo().create({
                'invoice_id': invoice.id,
                'state': 'invoice_refused',
                'message': error_message,
                'key_download': message['id'],
                'key_signature': message['answer']['signature']['key_signature'],
                'key_certificate': message['answer']['signature']['key_certificate'],
                'attachment': message['answer']['signature']['attachment_raw'],
            })

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

    @api.model
    def _l10n_ro_edi_process_bill_messages(self, received_bills_messages):
        ''' Create bill received on the SPV, it it does not already exists.
        '''
        # Search potential similar bills: similar bills either:
        # - have an index that is present in the message data or,
        # - the same amount and seller VAT, and optionally the same bill date
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_purchase_types())
            & (
                (
                    Domain('l10n_ro_edi_index', '=', False)
                    & Domain('l10n_ro_edi_state', '=', False)
                    & Domain.OR([
                        Domain('amount_total', '=', message['answer']['invoice']['amount_total'])
                        & Domain('commercial_partner_id.vat', '=', message['answer']['invoice']['seller_vat'])
                        & Domain('invoice_date', 'in', [message['answer']['invoice']['date'], False])
                        for message in received_bills_messages
                        if 'error' not in message['answer']
                    ])
                )
                | (
                    Domain('l10n_ro_edi_index', 'in', [message['id_solicitare'] for message in received_bills_messages])
                    & Domain('l10n_ro_edi_state', '=', 'invoice_validated')
                )
            )
        )
        similar_bills = self.env['account.move'].search(domain)

        indexed_similar_bills = similar_bills.filtered('l10n_ro_edi_index').mapped('l10n_ro_edi_index')
        non_indexed_similar_bills_dict = {
            (bill.commercial_partner_id.vat, bill.amount_total, bill.invoice_date): bill
            for bill in similar_bills
            if not bill.l10n_ro_edi_index
        }

        for message in received_bills_messages:
            if 'error' in message['answer']:
                continue

            if message['id_solicitare'] in indexed_similar_bills:
                # A bill with the same SPV index was already imported, skip it as we don't want it twice.
                continue

            # Create new bills if they don't already exist, else update their content
            bill = non_indexed_similar_bills_dict.get(
                (message['answer']['invoice']['seller_vat'], float(message['answer']['invoice']['amount_total']), message['answer']['invoice']['date'])
            )
            if not bill:
                bill = non_indexed_similar_bills_dict.get(
                (message['answer']['invoice']['seller_vat'], float(message['answer']['invoice']['amount_total']), False)
            )
            if not bill:
                bill = self.env['account.move'].create({
                'company_id': self.env.company.id,
                'move_type': 'in_invoice',
                'journal_id': self.env.company.l10n_ro_edi_anaf_imported_inv_journal_id.id,
            })

            bill.l10n_ro_edi_index = message['id_solicitare']

            self.env['l10n_ro_edi.document'].sudo().create({
                'invoice_id': bill.id,
                'state': 'invoice_validated',
                'key_download': message['id'],
                'key_signature': message['answer']['signature']['key_signature'],
                'key_certificate': message['answer']['signature']['key_certificate'],
                'attachment': base64.b64encode(message['answer']['signature']['attachment_raw']),
            })
            xml_attachment_raw = message['answer']['invoice']['attachment_raw']
            xml_attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"ciusro_{message['answer']['invoice']['name'].replace('/', '_')}.xml",
                'raw': xml_attachment_raw,
                'res_model': 'account.move',
                'res_id': bill.id,
            }).id
            files_data = self._to_files_data(self.env['ir.attachment'].browse(xml_attachment_id))
            bill._extend_with_attachments(files_data)
            chatter_message = self.env._("Synchronized with SPV from message %s", message['id'])
            if (bill.message_main_attachment_id.mimetype or '') != 'application/pdf':
                pdf = _request_ciusro_xml_to_pdf(self.env.company, xml_attachment_raw)
                if 'error' in pdf:
                    bill.message_post(body=self.env._(
                    "It was not possible to retrieve the PDF from the SPV for the following reason: %s",
                    pdf['error']
                    ))
                else:
                    pdf_attachment_id = self.env['ir.attachment'].sudo().create({
                        'name': f"ciusro_{message['answer']['invoice']['name'].replace('/', '_')}.pdf",
                        'raw': pdf['content'],
                        'res_model': 'account.move',
                        'res_id': bill.id,
                    }).id
                    bill.message_main_attachment_id = pdf_attachment_id
                    chatter_message += Markup("<br/>%s") % self.env._("No PDF found: PDF imported from SPV.")
            bill.message_post(body=chatter_message)

    def action_l10n_ro_edi_fetch_invoices(self):
        self._l10n_ro_edi_fetch_invoices()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
