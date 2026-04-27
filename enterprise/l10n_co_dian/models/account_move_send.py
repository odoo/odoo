from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, SQL


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_co_edi_applicable(self, move):
        return not move.invoice_pdf_report_id and move.l10n_co_dian_is_enabled

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'co_dian': {'label': _("DIAN"), 'is_applicable': self._is_co_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _l10n_co_dian_build_zip_attachment(self, move, move_data):
        zip_attachment = self.env['ir.attachment']
        attached_document = move_data.get('l10n_co_dian_attached_document')
        if attached_document:
            zip_content = (attached_document + move.invoice_pdf_report_id)._build_zip_from_attachments()
            zip_attachment += self.env['ir.attachment'].create({
                'name': move._l10n_co_dian_get_attached_document_filename() + ".zip",
                'raw': zip_content,
                'res_model': 'account.move',
                'res_id': move.id,
            })
            attached_document.unlink()
        return zip_attachment

    @api.model
    def _get_mail_params(self, move, move_data):
        # EXTENDS 'account' to be able to zip the PDF and the Colombian xml attachment together
        if not move_data.get('l10n_co_dian_attached_document'):
            return super()._get_mail_params(move, move_data)

        mail_attachments_widget = move_data.get('mail_attachments_widget')
        seen_attachment_ids = set()
        for attachment_data in mail_attachments_widget:
            if attachment_data.get('skip'):
                continue

            try:
                attachment_id = int(attachment_data['id'])
            except ValueError:
                continue

            seen_attachment_ids.add(attachment_id)

        # DIAN zip attachment
        filename = move._l10n_co_dian_get_attached_document_filename() + '.zip'
        placeholder = next((att for att in move_data['mail_attachments_widget'] if att.get('id') == f'placeholder_{filename}'), {})
        if not placeholder.get('skip'):
            zip_attachment = self._l10n_co_dian_build_zip_attachment(move, move_data)
            if zip_attachment:
                seen_attachment_ids.add(zip_attachment.id)

        mail_attachments = [
            (attachment.name, attachment.raw)
            for attachment in self.env['ir.attachment'].browse(list(seen_attachment_ids)).exists()
        ]

        return {
            'author_id': move_data['author_partner_id'],
            'body': move_data['mail_body'],
            'subject': move_data['mail_subject'],
            'partner_ids': move_data['mail_partner_ids'],
            'attachments': mail_attachments,
        }

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis)

        if not move.l10n_co_dian_attachment_id and 'co_dian' in extra_edis:
            filename = move._l10n_co_dian_get_attached_document_filename() + '.zip'
            results = [{
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/zip',
                'placeholder': True,
            }]

        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'co_dian' in invoice_data['extra_edis']:
                # Fetch partner data if there is no move sent in the last 30 days to the current partner
                date = fields.Datetime.now() - timedelta(days=30)
                query = SQL(
                    # Check if we have sent an invoice to this partner in the last 30 days
                    '''SELECT am.id
                        FROM account_move am
                       WHERE am.partner_id = %(partner_id)s
                         AND am.invoice_date >= %(date)s
                         AND am.l10n_co_dian_state = 'invoice_accepted'
                       LIMIT 1''',
                    partner_id=invoice.partner_id.id,
                    date=date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                )
                self.env.cr.execute(query)
                if not self.env.cr.fetchone():
                    invoice.partner_id._l10n_co_dian_update_data(invoice.company_id)

                # Render
                xml, errors = self.env['account.edi.xml.ubl_dian']._export_invoice(invoice)
                if errors:
                    invoice_data['error'] = {
                        'error_title': _("Error(s) when generating the UBL attachment:"),
                        'errors': errors,
                    }
                    continue

                # 1. Build the xml representing the invoice and send it to the DIAN
                doc = invoice._l10n_co_dian_send_invoice_xml(xml)

                if doc.state in ('invoice_rejected', 'invoice_sending_failed'):
                    invoice_data['error'] = {
                        'error_title': _("Error(s) when sending the document to the DIAN:"),
                        'errors': doc.message_json.get('errors') or [doc.message_json['status']],
                    }
                elif doc.state == 'invoice_accepted':
                    # 2. Call DIAN again to get the Status of the invoice and generate the Attached Document
                    attached_document, error_msg = doc._get_attached_document()
                    if error_msg:
                        invoice_data['error'] = {
                            'error_title': _("Error(s) when generating the Attached Document:"),
                            'errors': error_msg,
                        }
                    else:
                        invoice_data['l10n_co_dian_attached_document'] = self.env['ir.attachment'].create({
                            'raw': attached_document,
                            'name': invoice._l10n_co_dian_get_attached_document_filename() + ".xml",
                            'res_model': 'account.move',
                            'res_id': invoice.id,
                        })

                if self._can_commit():
                    self._cr.commit()
