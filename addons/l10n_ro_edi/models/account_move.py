import base64

import requests

from odoo import _, api, fields, models

from .utils import (
    _request_ciusro_download_answer,
    _request_ciusro_fetch_status,
    _request_ciusro_send_invoice,
)


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
            if move.l10n_ro_edi_state:
                move.show_reset_to_draft_button = False

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
            self._cr.commit()
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
            self._cr.commit()
