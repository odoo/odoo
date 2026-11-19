import base64

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri

from odoo.addons.l10n_gr_edi_e_invoo.models.account_move import (
    E_INVOO_PROVIDER_NAME,
    E_INVOO_PROVIDER_WEBSITE,
    E_INVOO_SOFTWARE_LICENSE,
)
from odoo.addons.l10n_gr_edi_e_invoo_bridge.exceptions import EInvooAuthenticationError, EInvooRequestError
from odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move import E_INVOO_TOKEN_NOT_SET

# Fields e-invoo always returns for an issued document. `inv_identifier` is not part of them:
# when a submission is retried, e-invoo returns the already issued document without it.
E_INVOO_ISSUED_DOCUMENT_FIELDS = ('b1_auth_string', 'provider_uid', 'mark', 'uid', 'qrUrl', 'provider_qrUrl')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_gr_edi_state = fields.Selection(
        selection_add=[('delivery_note_pending', "Delivery note submission pending")],
        ondelete={'delivery_note_pending': 'set null'},
    )

    ################################################################################
    # Compute methods
    ################################################################################

    @api.depends(
        'l10n_gr_edi_document_ids',
        'l10n_gr_edi_document_ids.state',
        'l10n_gr_edi_document_ids.mydata_mark',
        'l10n_gr_edi_document_ids.attachment_id',
    )
    def _compute_from_l10n_gr_edi_document_ids(self):
        # EXTENDS 'l10n_gr_edi_delivery_note'
        super()._compute_from_l10n_gr_edi_document_ids()
        for picking in self:
            if (
                picking.l10n_gr_edi_state != 'delivery_note_sent'
                and 'delivery_note_pending' in picking.l10n_gr_edi_document_ids.mapped('state')
            ):
                picking.l10n_gr_edi_state = 'delivery_note_pending'

    @api.depends('is_greek_company', 'state', 'l10n_gr_edi_state', 'l10n_gr_edi_document_ids.provider_pdf_state')
    def _compute_l10n_gr_edi_enable_send(self):
        # EXTENDS 'l10n_gr_edi_delivery_note'
        super()._compute_l10n_gr_edi_enable_send()
        for picking in self.filtered(lambda picking: picking.l10n_gr_edi_state == 'delivery_note_sent'):
            # Allow retrying the final PDF upload of an issued delivery note
            document = picking._l10n_gr_edi_get_sent_document()
            picking.l10n_gr_edi_enable_send = bool(document.provider_qr_url) and document.provider_pdf_state != 'sent'

    ################################################################################
    # Checks
    ################################################################################

    def _l10n_gr_edi_get_pre_error_dict(self):
        # EXTENDS 'l10n_gr_edi_delivery_note'
        errors = super()._l10n_gr_edi_get_pre_error_dict()
        if not self.company_id.sudo().l10n_gr_edi_methodoos_api_token:
            errors['l10n_gr_edi_missing_methodoos_token'] = {
                'message': str(E_INVOO_TOKEN_NOT_SET),
                'action_text': self.env._("View Settings"),
                'action': {
                    'name': self.env._("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#l10n_gr_edi_aade_settings',
                },
            }
        return errors

    ################################################################################
    # Report
    ################################################################################

    def _l10n_gr_edi_get_extra_invoice_report_values(self):
        # OVERRIDE 'l10n_gr_edi_delivery_note'
        self.ensure_one()
        document = self._l10n_gr_edi_get_sent_document()
        if not document:
            return {}

        # Use the provider verification URL for provider-issued delivery notes
        verification_url = document.provider_qr_url or document.mydata_url
        values = {
            'mydata_mark': document.mydata_mark,
            'mydata_uid': document.mydata_uid,
            'mydata_authentication_code': document.mydata_authentication_code,
            'provider_invoice_identifier': document.provider_invoice_identifier,
            'verification_url': verification_url,
        }
        if document.provider_qr_url:
            values.update({
                'provider_name': E_INVOO_PROVIDER_NAME,
                'provider_website': E_INVOO_PROVIDER_WEBSITE,
                'provider_software_license': E_INVOO_SOFTWARE_LICENSE,
                'issuance_datetime': document.datetime,
            })
        if verification_url:
            values['barcode_src'] = image_data_uri(base64.b64encode(
                self.env['ir.actions.report'].barcode(
                    barcode_type='QR',
                    value=verification_url,
                    width=180,
                    height=180,
                    quiet=0,
                )
            ))
        return values

    ################################################################################
    # Send logic
    ################################################################################

    def _l10n_gr_edi_prepare_delivery_note_request(self, document):
        self.ensure_one()
        return {
            'xml': document.attachment_id.raw.decode('utf-8'),
            'invoice_name': self.name,
            'invoice_amount_total': 0,  # A delivery note has no amount
            'invoice_datetime': fields.Datetime.to_string(document.datetime),
            'invoice_id': str(self.id),
            'issue_date': fields.Date.to_string(self._l10n_gr_edi_get_issue_and_dispatch_datetimes(document.datetime)[0]),
        }

    def _l10n_gr_edi_prepare_delivery_note_submission(self):
        """Lock the transfer and return the pending document to submit with its request values.

        :return: (document, request_values), or None if the delivery note is already issued.
        """
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)

        # Search with sudo: stock users have no write access on myDATA documents
        documents = self.env['l10n_gr_edi.document'].sudo()
        # Recheck after locking in case another worker issued the delivery note
        if documents.search_count([('picking_id', '=', self.id), ('state', '=', 'delivery_note_sent')], limit=1):
            return None

        document = documents.search([
            ('picking_id', '=', self.id),
            ('state', '=', 'delivery_note_pending'),
        ], limit=1)
        if not document:
            document = documents.create({
                'picking_id': self.id,
                'state': 'delivery_note_pending',
            })
        if not document.attachment_id:
            document.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"mydata_{self.name.replace('/', '_')}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': self._l10n_gr_edi_generate_delivery_note_xml(document.datetime),
                'type': 'binary',
                'mimetype': 'application/xml',
            })

        return document, self._l10n_gr_edi_prepare_delivery_note_request(document)

    def _l10n_gr_edi_handle_delivery_note_result(self, document, result):
        self.ensure_one()
        unknown_result_message = self.env._(
            "The delivery note submission result could not be confirmed. "
            "Retry the submission to retrieve the existing result."
        )
        response = result.get('response') if isinstance(result, dict) else None
        upstream_status = result.get('upstream_status') if isinstance(result, dict) else None

        if not isinstance(response, dict):
            document.message = unknown_result_message
        elif response.get('success') is True and all(response.get(field) for field in E_INVOO_ISSUED_DOCUMENT_FIELDS):
            document.write({
                'state': 'delivery_note_sent',
                'message': False,
                'mydata_mark': str(response['mark']),
                'mydata_uid': response['uid'],
                'mydata_url': response['qrUrl'],
                'mydata_authentication_code': response['b1_auth_string'],
                'provider_uid': response['provider_uid'],
                'provider_invoice_identifier': response.get('inv_identifier') or document.provider_invoice_identifier,
                'provider_qr_url': response['provider_qrUrl'],
                'provider_pdf_state': 'pending',
                'provider_pdf_error': False,
            })
            self.l10n_gr_edi_document_ids.filtered(
                lambda candidate: candidate != document and candidate.state == 'delivery_note_error'
            ).sudo().unlink()
        elif response.get('success') is False and response.get('error') in ('tf1', 'tf2'):
            document.write({
                'state': 'delivery_note_error',
                'message': self.env._(
                    "The delivery note was not issued because of a transmission failure (%s). Retry the submission.",
                    response['error'].upper(),
                ),
            })
        elif (
            response.get('success') is False
            and response.get('error')
            and (upstream_status is None or 200 <= upstream_status < 300 or 400 <= upstream_status < 500)
        ):
            document.write({
                'state': 'delivery_note_error',
                'message': response['error'],
            })
        else:
            document.message = unknown_result_message

    def _l10n_gr_edi_post_delivery_note_pdf(self, document, pdf_content):
        """Send the final PDF of an issued delivery note to e-invoo.

        :return: an error message, or None if e-invoo stored the PDF.
        """
        self.ensure_one()
        api_token = self.company_id.sudo().l10n_gr_edi_methodoos_api_token
        if not api_token:
            return str(E_INVOO_TOKEN_NOT_SET)
        parent_token = document._l10n_gr_edi_get_provider_parent_token()
        if not parent_token:
            return self.env._("Missing the provider parent token of the delivery note.")

        try:
            result = self.env['account.move']._l10n_gr_edi_post_e_invoo(
                api_token,
                endpoint='save_invoice_fpdf',
                test_env=self.company_id.l10n_gr_edi_test_env,
                json={
                    'invoice_id': str(self.id),
                    'parent_token': parent_token,
                    'pdf_b64': base64.b64encode(pdf_content).decode(),
                },
            )
        except EInvooRequestError as e:
            return str(e)

        response = result.get('response')
        # e-invoo answers 200 even when it did not find the document: check `Found` explicitly
        if 200 <= (result.get('upstream_status') or -1) < 300 and isinstance(response, dict) and response.get('Found') is True:
            return None
        return (isinstance(response, dict) and response.get('error')) or self.env._(
            "The delivery note was issued, but its final PDF could not be sent to the provider. Retry the submission."
        )

    def _l10n_gr_edi_upload_delivery_note_pdf(self):
        """Upload the final delivery slip to e-invoo and post it in the chatter.

        :return: True if the PDF was uploaded.
        """
        self.ensure_one()
        document = self._l10n_gr_edi_get_sent_document().sudo()
        if not document or document.provider_pdf_state == 'sent':
            return True

        try:
            pdf_content = self.env['ir.actions.report']._render_qweb_pdf('stock.action_report_delivery', self.ids)[0]
        except UserError as e:
            # The delivery note is already issued: keep it and let the user retry the PDF
            error_message = e.args[0]
        else:
            error_message = self._l10n_gr_edi_post_delivery_note_pdf(document, pdf_content)

        if error_message:
            document.write({
                'provider_pdf_state': 'error',
                'provider_pdf_error': error_message,
                'message': error_message,
            })
            return False

        document.write({
            'provider_pdf_state': 'sent',
            'provider_pdf_error': False,
            'message': False,
        })
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name.replace('/', '_')}.pdf",
            'type': 'binary',
            'raw': pdf_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        # Log note: unlike `message_post`, it does not require the user to have an email address
        self._message_log(
            body=self.env._("Delivery note issued on myDATA through e-invoo (MARK %s).", document.mydata_mark),
            attachment_ids=attachment.ids,
        )
        return True

    def _l10n_gr_edi_send_delivery_note(self):
        # OVERRIDE 'l10n_gr_edi_delivery_note'
        self.ensure_one()
        api_token = self.company_id.sudo().l10n_gr_edi_methodoos_api_token
        if not api_token:
            raise UserError(str(E_INVOO_TOKEN_NOT_SET))

        submission = self._l10n_gr_edi_prepare_delivery_note_submission()
        if submission:
            document, request_values = submission
            try:
                result = self.env['account.move']._l10n_gr_edi_issue_invoice(
                    api_token,
                    test_env=self.company_id.l10n_gr_edi_test_env,
                    request_values=request_values,
                )
            except EInvooAuthenticationError as e:
                document.write({
                    'state': 'delivery_note_error',
                    'message': str(e),
                })
            except EInvooRequestError as e:
                document.message = str(e)
            else:
                self._l10n_gr_edi_handle_delivery_note_result(document, result)

            if self.env['account.move']._can_commit():
                self.env.cr.commit()

        if self.l10n_gr_edi_state == 'delivery_note_sent':
            self._l10n_gr_edi_upload_delivery_note_pdf()

    def action_l10n_gr_edi_try_send_delivery_note(self):
        # EXTENDS 'l10n_gr_edi_delivery_note'
        self.ensure_one()
        if self.l10n_gr_edi_state == 'delivery_note_sent':
            # Already issued: only the final PDF upload is left to retry
            self.env['res.company']._with_locked_records(self)
            self._l10n_gr_edi_upload_delivery_note_pdf()
            return
        return super().action_l10n_gr_edi_try_send_delivery_note()
