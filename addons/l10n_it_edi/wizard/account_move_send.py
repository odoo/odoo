# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from lxml import etree
from markupsafe import escape

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.l10n_it_edi.tools.xml_utils import format_errors
from odoo.addons.l10n_it_edi.models.l10n_it_edi_export import format_alphanumeric
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    l10n_it_edi_enable_send = fields.Boolean(compute='_compute_fields_from_moves_state')
    l10n_it_edi_checkbox_send = fields.Boolean('Tax Agency (Italy)', compute='_compute_l10n_it_edi_checkbox_send',
        store=True, readonly=False, help=(
            "Send the invoice to the Italian Tax Agency.\n"
            "It is set as readonly if a report has already been created, to avoid inconsistencies.\n"
            "To re-enable it, delete the PDF attachment."))
    l10n_it_edi_readonly = fields.Boolean(compute='_compute_fields_from_moves_state')
    l10n_it_edi_warning_message = fields.Html(compute='_compute_fields_from_moves_state')

    def _get_available_field_values_in_multi(self, move):
        # EXTENDS 'account'
        values = super()._get_available_field_values_in_multi(move)
        values['l10n_it_edi_checkbox_send'] = self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(move)
        return values

    # -------------------------------------------------------------------------
    # COMPUTE/CONSTRAINS METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_it_edi_enable_send')
    def _compute_fields_from_moves_state(self):
        # EXTENDS account
        super()._compute_fields_from_moves_state()
        for wizard in self:
            wizard.l10n_it_edi_enable_send = any(
                wizard._get_default_l10n_it_edi_enable_send(m)
                and not m.l10n_it_edi_attachment_id
                for m in wizard.move_ids
            )

            if not wizard.company_id.l10n_it_edi_proxy_user_id:
                wizard.l10n_it_edi_warning_message = _("You must accept the terms and conditions in the Settings to use the IT EDI.")
            else:
                errors = [
                    format_errors(
                        move.name + ":" if wizard.mode == 'invoice_multi' else False,
                        move_warnings
                    ) for move in wizard.move_ids
                      if (move_warnings := move._l10n_it_edi_export_data_check())
                ]
                wizard.l10n_it_edi_warning_message = "<br>".join(errors) if errors else False

            already_has_pdf = any(wizard.move_ids.mapped("invoice_pdf_report_id"))
            already_has_xml = any([x._l10n_it_edi_check_processable() for x in wizard.move_ids.mapped("attachment_ids")])
            wizard.l10n_it_edi_readonly = wizard.l10n_it_edi_warning_message or already_has_pdf or already_has_xml

    @api.depends('l10n_it_edi_readonly', 'l10n_it_edi_enable_send')
    def _compute_l10n_it_edi_checkbox_send(self):
        for wizard in self:
            wizard.l10n_it_edi_checkbox_send = wizard.l10n_it_edi_enable_send and not wizard.l10n_it_edi_readonly

    @api.depends('move_ids')
    def _get_default_l10n_it_edi_enable_send(self, move):
        return (
            move.company_id.account_fiscal_country_id.code == 'IT'
            and (move.journal_id.type == 'sale'
                 or move.journal_id.type == 'purchase' and move._l10n_it_edi_is_self_invoice())
            and move.l10n_it_edi_state in (False, 'rejected')
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(invoice):
            if errors := invoice._l10n_it_edi_export_data_check():
                error_str = _("Errors occured while creating the e-invoice file.")
                error_str += "\n- " + "\n- ".join(errors)
                invoice_data['error'] = error_str

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)

        if self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(invoice):
            # Inject the PDF inside the XML as Base64 encoded text
            xml = self.env['l10n_it_edi.export']._l10n_it_edi_export(invoice)
            tree = etree.fromstring(xml.encode())
            attachment_elements = tree.xpath("//Allegati")
            if len(attachment_elements) > 0:
                pdf_filename = invoice_data['pdf_attachment_values']['name']
                pdf_content = invoice_data['pdf_attachment_values']['raw']

                el = attachment_elements[0]
                for tagname, text in [
                    ('NomeAttachment', format_alphanumeric(pdf_filename, 60)),
                    ('FormatoAttachment', 'PDF'),
                    ('Attachment', b64encode(pdf_content).decode())
                ]:
                    new_el = etree.Element(tagname)
                    new_el.text = text
                    el.append(new_el)
                content = etree.tostring(cleanup_xml_node(tree), xml_declaration=True, encoding='UTF-8')

            invoice_data['l10n_it_edi_values'] = {
                'name': self.env['ir.attachment']._l10n_it_edi_generate_filename(invoice.company_id),
                'type': 'binary',
                'mimetype': 'application/xml',
                'description': _('IT EDI e-invoice: %s', invoice.move_type),
                'company_id': invoice.company_id.id,
                'res_id': invoice.id,
                'res_model': invoice._name,
                'res_field': 'l10n_it_edi_attachment_file',
                'raw': content,
            }

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        # If not selected, just delegate
        if not self.l10n_it_edi_checkbox_send:
            return

        # Mark the moves as 'being_sent'
        files_to_upload, pa_files, moves, attachments = [], [], {}, {}
        for move, invoice_data in invoices_data.items():
            if not self._get_default_l10n_it_edi_enable_send(move):
                continue

            move.l10n_it_edi_state = 'being_sent'
            move.l10n_it_edi_header = False

            filename = invoice_data['l10n_it_edi_values']['name']
            content = b64encode(invoice_data['l10n_it_edi_values']['raw']).decode()
            if not move.commercial_partner_id._is_pa():
                files_to_upload.append({'filename': filename, 'xml': content})
            else:
                pa_files.append({'move': move, 'filename': filename, 'xml': content})

            attachments[move.id] = filename
            moves[filename] = move

        # Upload the files
        if files_to_upload:
            try:
                results = self.company_id.l10n_it_edi_proxy_user_id._l10n_it_edi_upload(files_to_upload)
            except AccountEdiProxyError as e:
                for _move_id, filename in attachments.items():
                    message = nl2br(escape(_("Error uploading the e-invoice file %s.\n%s", filename, e.message)))
                    moves[filename].sudo().message_post(body=message)
                raise UserError(e.message)

            # Handle results
            for filename, vals in results.items():
                move = moves[filename]
                if 'error' in vals and vals.get('error_level', '') == 'error':
                    move.l10n_it_edi_state = False
                    move.l10n_it_edi_transaction = False
                    message = nl2br(escape(_("Error uploading the e-invoice file %s.\n%s", filename, vals['error'])))
                else:
                    move.l10n_it_edi_state = 'processing'
                    id_transaction = vals['id_transaction']
                    move.l10n_it_edi_transaction = id_transaction
                    if id_transaction == 'demo':
                        message = _("We are simulating the sending of the e-invoice file %s, as we are in demo mode.", filename)
                    else:
                        message = _("The e-invoice file %s was sent to the SdI for processing.", filename)
                move.sudo().message_post(body=message)
                move.l10n_it_edi_header = message

        # Handle PA files
        for vals in pa_files:
            move = vals['move']
            move.l10n_it_edi_state = 'requires_user_signature'
            move.l10n_it_edi_transaction = False
            message = nl2br(escape(_(
                "Sending invoices to Public Administration partners is not supported.\n"
                "The IT EDI XML file is generated, please sign the document and upload it "
                "through the 'Fatture e Corrispettivi' portal of the Tax Agency."
            )))
            move.l10n_it_edi_header = message
            move.sudo().message_post(body=message)

    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)

        if attachment_vals := invoice_data.get('l10n_it_edi_values'):
            self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'])
