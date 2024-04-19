import requests

from odoo import models, fields, _, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ro_edi_document_ids = fields.One2many(
        comodel_name='l10n_ro_edi.document',
        inverse_name='invoice_id',
    )
    l10n_ro_edi_active_document_id = fields.Many2one(
        comodel_name='l10n_ro_edi.document',
        compute='_compute_from_l10n_ro_edi_document_ids',
    )
    l10n_ro_edi_state = fields.Selection(
        selection=[
            ('invoice_sending', 'Sending'),
            ('invoice_sending_failed', 'Error'),
            ('invoice_sent', 'Sent'),
        ],
        string='E-Factura Status',
        compute='_compute_from_l10n_ro_edi_document_ids_stored',
        store=True,
    )
    l10n_ro_edi_message = fields.Char(compute='_compute_from_l10n_ro_edi_document_ids')

    @api.depends('l10n_ro_edi_document_ids')
    def _compute_from_l10n_ro_edi_document_ids(self):
        for move in self:
            active_document = self.env['l10n_ro_edi.document'].search([('invoice_id', '=', move.id)], limit=1)
            move.l10n_ro_edi_active_document_id = active_document
            move.l10n_ro_edi_message = active_document.message

    @api.depends('l10n_ro_edi_document_ids')
    def _compute_from_l10n_ro_edi_document_ids_stored(self):
        for move in self:
            active_document = self.env['l10n_ro_edi.document'].search([('invoice_id', '=', move.id)], limit=1)
            move.l10n_ro_edi_state = active_document.state

    @api.depends('l10n_ro_edi_state')
    def _compute_show_reset_to_draft_button(self):
        """ Prevent user to reset move to draft when there's an
        active sending document or an OK response has been received """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_ro_edi_state in ('invoice_sending', 'invoice_sent'):
                move.show_reset_to_draft_button = False

    def _l10n_ro_edi_get_attachment_file_name(self):
        self.ensure_one()
        return f"{self.name.replace('/', '_')}.xml"

    def _l10n_ro_edi_compute_errors(self, xml_data):
        """ Compute possible errors before sending E-Factura """
        self.ensure_one()
        errors = []
        if not self.company_id.l10n_ro_edi_access_token:
            errors.append(_('Romanian access token not found. Please generate or fill it in the settings.'))
        if not xml_data:
            errors.append(_('CIUS-RO XML attachment not found.'))
        return errors

    def _l10n_ro_edi_send_invoice(self, xml_data):
        self.ensure_one()
        if errors := self.company_id._l10n_ro_edi_get_errors_pre_request():
            self.env['l10n_ro_edi.document']._create_document_invoice_sending_failed(self, '\n'.join(errors))
            return

        result = self.env['l10n_ro_edi.document']._request_ciusro_send_invoice(
            company=self.company_id,
            xml_data=xml_data,
            move_type=self.move_type,
        )
        if 'error' in result:
            self.env['l10n_ro_edi.document']._create_document_invoice_sending_failed(self, result['error'])
        else:
            self.env['l10n_ro_edi.document']._create_document_invoice_sending(self, result['key_loading'])

    def _l10n_ro_edi_fetch_invoice_sending_documents(self):
        """ Collects all selected active documents in self and process them as a batch.
        Make a fetch request for each document. Based on the received result,
        if error -> generate error document on that document's invoice
        else -> immediately make a download request and process it
        """
        documents = self.l10n_ro_edi_active_document_id.filtered(lambda d: d.state == 'invoice_sending')
        if not documents:
            return
        session = requests.session()
        to_delete_documents = self.env['l10n_ro_edi.document']

        for document in documents:
            if errors := document.invoice_id.company_id._l10n_ro_edi_get_errors_pre_request():
                self.env['l10n_ro_edi.document']._create_document_invoice_sending_failed(document.invoice_id, '\n'.join(errors))
                continue
            result = self.env['l10n_ro_edi.document']._request_ciusro_fetch_status(
                company=document.invoice_id.company_id,
                key_loading=document.key_loading,
                session=session,
            )
            if 'error' in result:
                self.env['l10n_ro_edi.document']._create_document_invoice_sending_failed(document.invoice_id, result['error'])
            elif 'key_download' in result:
                # use the obtained key_download to immediately make a download request and process them
                final_result = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                    company=document.invoice_id.company_id,
                    key_download=result['key_download'],
                    session=session,
                )
                if 'error' in final_result:
                    self.env['l10n_ro_edi.document']._create_document_invoice_sending_failed(document.invoice_id, final_result['error'])
                else:
                    self.env['l10n_ro_edi.document']._create_document_invoice_sent(document.invoice_id, final_result)
                    # Gather useless `invoice_sending_failed` documents from the successful document's invoice
                    to_delete_documents |= self.env['l10n_ro_edi.document'].filtered(
                        lambda d: d.invoice_id.id == document.invoice_id.id and d.state == 'invoice_sending_failed')

        # Delete useless documents in batches
        to_delete_documents.unlink()
