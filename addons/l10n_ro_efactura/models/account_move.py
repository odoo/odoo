import requests

from odoo import models, fields, _, api, modules, tools


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ro_edi_document_ids = fields.One2many(
        comodel_name='l10n_ro_edi.document',
        inverse_name='invoice_id',
    )
    l10n_ro_edi_state = fields.Selection(
        selection=[
            ('invoice_sending', 'Sending'),
            ('invoice_sent', 'Sent'),
        ],
        string='E-Factura Status',
        compute='_compute_l10n_ro_edi_state',
        store=True,
    )
    l10n_ro_edi_attachment_id = fields.Many2one(comodel_name='ir.attachment')

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends('l10n_ro_edi_document_ids')
    def _compute_l10n_ro_edi_state(self):
        self.l10n_ro_edi_state = False
        for move in self:
            for document in move.l10n_ro_edi_document_ids.sorted():
                if document.state in ('invoice_sending', 'invoice_sent'):
                    move.l10n_ro_edi_state = document.state
                    break

    @api.depends('l10n_ro_edi_state')
    def _compute_show_reset_to_draft_button(self):
        """ Prevent user to reset move to draft when there's an
            active sending document or a successful response has been received """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_ro_edi_state in ('invoice_sending', 'invoice_sent'):
                move.show_reset_to_draft_button = False

    ################################################################################
    # Romanian Document Shorthands & Helpers
    ################################################################################

    def _l10n_ro_edi_create_attachment_values(self, raw, res_model=None, res_id=None):
        """ Shorthand for creating the attachment_id values on the invoice's document """
        self.ensure_one()
        res_model = res_model or self._name
        res_id = res_id or self.id
        return {
            'name': f"ciusro_{self.name.replace('/', '_')}.xml",
            'res_model': res_model,
            'res_id': res_id,
            'raw': raw,
            'type': 'binary',
            'mimetype': 'application/xml',
        }

    def _l10n_ro_edi_create_document_invoice_sending(self, key_loading, attachment_raw):
        """ Shorthand for creating a `l10n_ro_edi.document` of state `invoice_sending` """
        self.ensure_one()
        document = self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sending',
            'key_loading': key_loading,
        })
        attachment_values = self._l10n_ro_edi_create_attachment_values(
            raw=attachment_raw,
            res_model=document._name,
            res_id=document.id,
        )
        document.attachment_id = self.env['ir.attachment'].sudo().create(attachment_values)
        return document

    def _l10n_ro_edi_create_document_invoice_sending_failed(self, message, attachment_raw=None):
        """ Shorthand for creating a ``l10n_ro_edi.document`` of state ``invoice_sending_failed``.
            Attachment (attachment_raw param) is optional in case the error is from pre_send. """
        self.ensure_one()
        document = self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sending_failed',
            'message': _("Error when sending the document to the SPV:\n%s", message),
        })
        if attachment_raw:
            attachment_values = self._l10n_ro_edi_create_attachment_values(
                raw=attachment_raw,
                res_model=document._name,
                res_id=document.id,
            )
            document.attachment_id = self.env['ir.attachment'].sudo().create(attachment_values)
        return document

    def _l10n_ro_edi_create_document_invoice_sent(self, result: dict):
        """ Shorthand for creating a `l10n_ro_edi.document` of state `invoice_sent`.
            The created attachment are saved on both the document and on the invoice. """
        self.ensure_one()
        document = self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sent',
            'key_signature': result['key_signature'],
            'key_certificate': result['key_certificate'],
        })
        attachment = self.env['ir.attachment'].sudo().create(self._l10n_ro_edi_create_attachment_values(result['attachment_raw']))
        document.attachment_id = self.l10n_ro_edi_attachment_id = attachment
        return document

    def _l10n_ro_edi_get_attachment_file_name(self):
        """ Returns the signature file attachment's name from ``l10n_ro_edi.document``/``invoice_sent`` """
        self.ensure_one()
        return f"ciusro_{self.name.replace('/', '_')}.xml"

    def _l10n_ro_edi_get_failed_documents(self):
        """ Shorthand for getting all l10n_ro_edi.document in invoice_sending_failed state """
        self.ensure_one()
        return self.l10n_ro_edi_document_ids.filtered(lambda d: d.state == 'invoice_sending_failed')

    def _l10n_ro_edi_get_sending_and_failed_documents(self):
        """ Shorthand for getting all l10n_ro_edi.document in invoice_sending and invoice_sending_failed state """
        self.ensure_one()
        return self.l10n_ro_edi_document_ids.filtered(lambda d: d.state in ('invoice_sending', 'invoice_sending_failed'))

    ################################################################################
    # Send Logics
    ################################################################################

    def _l10n_ro_edi_get_pre_send_errors(self, xml_data='', assert_xml=False):
        """ Compute all possible common errors before sending the XML to the SPV """
        self.ensure_one()
        errors = []
        if not self.company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))
        if not xml_data and assert_xml:
            errors.append(_('CIUS-RO XML attachment not found.'))
        return errors

    def _l10n_ro_edi_send_invoice(self, xml_data):
        """
        This method send xml_data to the Romanian SPV using the single invoice's (self) data.
        The invoice's company and move_type will be used to calculate the required params in the send request.
        The state of the document deletion/creation are as follows:

         - Pre-check any errors from the invoice's pre_send check before sending

            - if error -> delete all error documents, create a new error document
            - else -> continue to the next step

         - Send to E-Factura, and based on the result:

            - if error -> delete all error documents, create a new error document
            - if success -> delete all error & sending documents, create a new sending document

        :param xml_data: string of the xml data to be sent
        """
        self.ensure_one()
        if errors := self._l10n_ro_edi_get_pre_send_errors(xml_data, True):
            self._l10n_ro_edi_get_failed_documents().unlink()
            self._l10n_ro_edi_create_document_invoice_sending_failed('\n'.join(errors))
            return

        self.env['res.company']._with_locked_records(self)
        result = self.env['l10n_ro_edi.document']._request_ciusro_send_invoice(
            company=self.company_id,
            xml_data=xml_data,
            move_type=self.move_type,
        )
        if 'error' in result:
            self._l10n_ro_edi_get_failed_documents().unlink()
            self._l10n_ro_edi_create_document_invoice_sending_failed(result['error'], xml_data)
        else:
            self._l10n_ro_edi_get_sending_and_failed_documents().unlink()
            self._l10n_ro_edi_create_document_invoice_sending(result['key_loading'], xml_data)

    def _l10n_ro_edi_fetch_invoice_sending_documents(self):
        """
        This method loops over all invoice with sending document in `self`. For each of them,
        it pre-checks error and make a fetch request for the invoice. Based on the answer, it will then:

         - if no answer is received, it will do nothing on the selected invoice
         - if error -> delete all errors, create a new error document
         - else (receives `key_download`) -> immediately make a download request and process it:

            - if error -> delete all sending and error documents, create a new error document
            - if success -> delete all sending and error documents, create success document
        """
        session = requests.Session()
        to_delete_documents = self.env['l10n_ro_edi.document']
        invoices_to_fetch = self.filtered(lambda inv: inv.l10n_ro_edi_state == 'invoice_sending')

        for invoice in invoices_to_fetch:
            if errors := invoice._l10n_ro_edi_get_pre_send_errors():
                to_delete_documents |= invoice._l10n_ro_edi_get_failed_documents()
                invoice._l10n_ro_edi_create_document_invoice_sending_failed('\n'.join(errors))
                continue

            active_sending_document = invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == 'invoice_sending')[0]
            previous_raw = active_sending_document.attachment_id.sudo().raw
            self.env['res.company']._with_locked_records(invoices_to_fetch)
            result = self.env['l10n_ro_edi.document']._request_ciusro_fetch_status(
                company=invoice.company_id,
                key_loading=active_sending_document.key_loading,
                session=session,
            )

            if result == {}:
                continue
            elif 'error' in result:
                to_delete_documents |= invoice._l10n_ro_edi_get_sending_and_failed_documents()
                invoice._l10n_ro_edi_create_document_invoice_sending_failed(result['error'], previous_raw)
            else:  # result == {'key_download': <str>}
                # use the obtained key_download to immediately make a download request and process them
                final_result = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                    company=invoice.company_id,
                    key_download=result['key_download'],
                    session=session,
                )
                to_delete_documents |= invoice._l10n_ro_edi_get_sending_and_failed_documents()
                if 'error' in final_result:
                    invoice._l10n_ro_edi_create_document_invoice_sending_failed(final_result['error'], previous_raw)
                else:
                    invoice._l10n_ro_edi_create_document_invoice_sent(final_result)

            if not tools.config['test_enable'] and not modules.module.current_test:
                self._cr.commit()

        # Delete outdated documents in batches
        to_delete_documents.unlink()
