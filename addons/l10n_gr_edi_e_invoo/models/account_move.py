import base64

from lxml import etree

from odoo import api, fields, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node, float_repr
from odoo.tools.image import image_data_uri


E_INVOO_PROVIDER_NAME = 'Methodoos ΙΚΕ'
E_INVOO_PROVIDER_WEBSITE = 'https://e-invoo.com'
E_INVOO_SOFTWARE_LICENSE = '2026_04_137Methodoos_001_e-invoo_V1_30042026'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_state = fields.Selection(
        selection_add=[('invoice_pending', "Invoice submission pending")],
        ondelete={'invoice_pending': 'set null'},
    )

    @api.depends(
        'l10n_gr_edi_document_ids',
        'l10n_gr_edi_document_ids.attachment_id',
        'l10n_gr_edi_document_ids.mydata_cls_mark',
        'l10n_gr_edi_document_ids.mydata_mark',
        'l10n_gr_edi_document_ids.state',
    )
    def _compute_from_l10n_gr_edi_document_ids(self):
        # EXTENDS 'l10n_gr_edi'
        super()._compute_from_l10n_gr_edi_document_ids()
        for move in self:
            document = move.l10n_gr_edi_document_ids.filtered(
                lambda candidate: candidate.state in (
                    'invoice_pending',
                    'invoice_sent',
                    'bill_fetched',
                    'bill_sent',
                )
            ).sorted()[:1]
            if document.state == 'invoice_pending':
                move.l10n_gr_edi_state = document.state
                move.l10n_gr_edi_mark = document.mydata_mark
                move.l10n_gr_edi_cls_mark = document.mydata_cls_mark
                move.l10n_gr_edi_attachment_id = document.attachment_id

    @api.depends('l10n_gr_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_gr_edi_state == 'invoice_pending':
                move.show_reset_to_draft_button = False

    def _check_draftable(self):
        if self.filtered(
            lambda move: move.l10n_gr_edi_state in (
                'invoice_pending',
                'invoice_sent',
            )
        ):
            raise UserError(self.env._("You cannot reset this invoice to draft."))
        return super()._check_draftable()

    @api.depends('state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_enable_fields(self):
        # EXTENDS 'l10n_gr_edi'
        super()._compute_l10n_gr_edi_enable_fields()
        for move in self.filtered(lambda move: move.l10n_gr_edi_state == 'invoice_pending'):
            move.l10n_gr_edi_enable_send_invoices = move._l10n_gr_edi_eligible_for_mydata() and move.is_sale_document(include_receipts=True)

    def _l10n_gr_edi_get_pre_error_dict(self):
        # EXTENDS 'l10n_gr_edi'
        errors = super()._l10n_gr_edi_get_pre_error_dict()
        if self.is_sale_document(include_receipts=True) and self.l10n_gr_edi_state != 'invoice_pending':
            greece_today = fields.Date.context_today(self.with_context(tz='Europe/Athens'))
            if self.date != greece_today:
                errors['l10n_gr_edi_invalid_issue_date'] = {
                    'message': self.env._(
                        "The accounting date must be %(date)s, the current date in Greece, "
                        "to issue this invoice electronically.",
                        date=fields.Date.to_string(greece_today),
                    ),
                }
        return errors

    def _l10n_gr_edi_get_provider_invoice_id(self):
        """Return an invoice ID that is unique across Odoo databases."""
        self.ensure_one()
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return f'{database_uuid}-{self.id}'

    def _l10n_gr_edi_prepare_invoice_proxy_request(self, invoice_datetime):
        self.ensure_one()

        xml_vals = self._l10n_gr_edi_get_invoices_xml_vals()
        xml_content = self.env['ir.qweb']._render('l10n_gr_edi.mydata_invoice', xml_vals)
        xml_content = etree.tostring(
            element_or_tree=cleanup_xml_node(xml_content),
            encoding='UTF-8',
            standalone='yes',
        )

        return {
            'xml': xml_content.decode('utf-8'),
            'invoice_name': self.name,
            'invoice_amount_total': float_repr(self.amount_total, self.currency_id.decimal_places),
            'invoice_datetime': fields.Datetime.to_string(invoice_datetime),
            'invoice_id': self._l10n_gr_edi_get_provider_invoice_id(),
            'invoice_currency': self.currency_id.name,
            'issue_date': fields.Date.to_string(self.date),
        }

    def _l10n_gr_edi_prepare_invoice_submission(self):
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)

        # Recheck after locking in case another worker issued the invoice
        if self.env['l10n_gr_edi.document'].search([
            ('move_id', '=', self.id),
            ('state', '=', 'invoice_sent'),
        ], limit=1):
            return None

        # Reuse a pending submission to preserve its timestamp and exact XML on retry.
        document = self.env['l10n_gr_edi.document'].search([
            ('move_id', '=', self.id),
            ('state', '=', 'invoice_pending'),
        ], limit=1)
        document_created = False
        attachment_created = False

        if not document:
            document = self.env['l10n_gr_edi.document'].create({
                'move_id': self.id,
                'state': 'invoice_pending',
            })
            document_created = True

        request_values = self._l10n_gr_edi_prepare_invoice_proxy_request(document.datetime)
        if document.attachment_id:
            request_values['xml'] = document.attachment_id.sudo().raw.decode('utf-8')
        else:
            document.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"mydata_{self.name.replace('/', '_')}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': request_values['xml'].encode('utf-8'),
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            attachment_created = True

        if (document_created or attachment_created) and self._can_commit():
            self.env.cr.commit()
            # The commit released the invoice lock; reacquire it before contacting the provider.
            self.env['res.company']._with_locked_records(self)

        return document, request_values

    def _l10n_gr_edi_handle_invoice_proxy_result(self, document, result):
        unknown_result_message = self.env._(
            "The electronic invoice submission result could not be confirmed. "
            "Retry the submission to retrieve the existing result."
        )
        if not isinstance(result, dict):
            document.message = unknown_result_message
            return

        response = result.get('response')
        upstream_status = result.get('upstream_status')

        if (
            isinstance(response, dict)
            and response.get('success') is True
            and all(response.get(field) for field in (
                'b1_auth_string',
                'provider_uid',
                'mark',
                'uid',
                'qrUrl',
                'inv_identifier',
                'provider_qrUrl',
            ))
        ):
            document.write({
                'state': 'invoice_sent',
                'message': False,
                'mydata_mark': response['mark'],
                'mydata_uid': response['uid'],
                'mydata_url': response['qrUrl'],
                'mydata_authentication_code': response['b1_auth_string'],
                'provider_uid': response['provider_uid'],
                'provider_invoice_identifier': response['inv_identifier'],
                'provider_qr_url': response['provider_qrUrl'],
                'provider_pdf_state': 'pending',
                'provider_pdf_error': False,
            })

            # Discard any PDF generated before receiving the provider values
            if self.invoice_pdf_report_id:
                self.invoice_pdf_report_file = False

            self.l10n_gr_edi_document_ids.filtered(
                lambda candidate: (
                    candidate != document
                    and candidate.state == 'invoice_error'
                )
            ).unlink()
        elif (
            isinstance(response, dict)
            and response.get('success') is False
            and response.get('error') in ('tf1', 'tf2')
        ):
            document.write({
                'state': 'invoice_error',
                'message': self.env._(
                    "The invoice was not issued because of a transmission "
                    "failure (%s). Retry the submission.",
                    response['error'].upper(),
                ),
            })
        elif (
            isinstance(response, dict)
            and response.get('success') is False
            and response.get('error')
            and (
                upstream_status is None
                or 200 <= upstream_status < 300
                or 400 <= upstream_status < 500
            )
        ):
            document.write({
                'state': 'invoice_error',
                'message': response['error'],
            })
        else:
            document.message = unknown_result_message

    def _l10n_gr_edi_get_extra_invoice_report_values(self):
        # EXTENDS 'l10n_gr_edi'
        self.ensure_one()
        document = self.l10n_gr_edi_document_ids.filtered(
            lambda candidate: candidate.state in ('invoice_sent', 'bill_sent')
        ).sorted()[:1]
        if not document:
            return {}

        # Use the provider verification URL for provider-issued invoices while
        # preserving the AADE URL for historical direct submissions
        verification_url = document.provider_qr_url or document.mydata_url
        values = {
            'mydata_mark': document.mydata_mark,
            'mydata_cls_mark': document.mydata_cls_mark,
            'mydata_uid': document.mydata_uid,
            'mydata_authentication_code': document.mydata_authentication_code,
            'provider_invoice_identifier': document.provider_invoice_identifier,
            'verification_url': verification_url,
        }

        if document.provider_invoice_identifier:
            values.update({
                'provider_name': E_INVOO_PROVIDER_NAME,
                'provider_website': E_INVOO_PROVIDER_WEBSITE,
                'provider_software_license': E_INVOO_SOFTWARE_LICENSE,
                'invoice_datetime': document.datetime,
            })

        if verification_url:
            values['barcode_src'] = image_data_uri(
                base64.b64encode(
                    self.env['ir.actions.report'].barcode(
                        barcode_type='QR',
                        value=verification_url,
                        width=180,
                        height=180,
                        quiet=0,
                    )
                )
            )

        return values

    def _l10n_gr_edi_send_invoices(self):
        # EXTENDS 'l10n_gr_edi'
        """Send customer invoices individually through the IAP proxy."""
        for company, invoices in self.grouped('company_id').items():
            proxy_user = company._l10n_gr_edi_get_proxy_user()

            for invoice in invoices:
                submission = invoice._l10n_gr_edi_prepare_invoice_submission()
                if not submission:
                    continue

                document, request_values = submission
                try:
                    result = proxy_user._l10n_gr_edi_proxy_request('send_invoice', request_values)
                except AccountEdiProxyError as error:
                    unknown_result_message = self.env._(
                        "The electronic invoice submission result could not be confirmed. "
                        "Retry the submission to retrieve the existing result."
                    )
                    if error.code == 'invalid_request':
                        document.write({
                            'state': 'invoice_error',
                            'message': error.message or self.env._(
                                "The electronic invoice request could not be processed. "
                                "Please contact Odoo support if the problem persists."
                            ),
                        })
                    elif error.code == 'e_invoo_request_failed':
                        document.message = error.message or unknown_result_message
                    else:
                        document.message = unknown_result_message
                else:
                    invoice._l10n_gr_edi_handle_invoice_proxy_result(document, result)

                if self._can_commit():
                    self.env.cr.commit()

    def l10n_gr_edi_try_send_invoices(self):
        # EXTENDS 'l10n_gr_edi'
        valid_move_ids = []
        for move in self.filtered('l10n_gr_edi_enable_send_invoices'):
            if error := move._l10n_gr_edi_get_pre_error_string():
                move._l10n_gr_edi_create_error_document({'error': error})
            else:
                valid_move_ids.append(move.id)

        moves_to_send = self.browse(valid_move_ids)

        if moves_to_send:
            moves_to_send._l10n_gr_edi_send_invoices()
