# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError, OperationalError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import _, LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    'error_internal': _lt("An error occurred"),
    'error_document_not_found': _lt("The document could not be found"),
    'error_unsupported_format': _lt("Unsupported image format"),
    'error_no_connection': _lt("Server not available. Please retry later"),
    'error_maintenance': _lt("Server is currently under maintenance. Please retry later"),
    'error_password_protected': _lt("Your PDF file is protected by a password. The OCR can't extract data from it"),
    'error_too_many_pages': _lt("Your document contains too many pages"),
    'error_invalid_account_token': _lt(
        "The 'invoice_ocr' IAP account token is invalid. "
        "Please delete it to let Odoo generate a new one or fill it with a valid token."),
    'error_unsupported_size': _lt("The document has been rejected because it is too small"),
    'error_no_page_count': _lt("Invalid PDF (Unable to get page count)"),
    'error_pdf_conversion_to_images': _lt("Invalid PDF (Conversion error)"),
}


class ExtractMixin(models.AbstractModel):
    """ Base model to inherit from to add extract functionality to a model. """
    _name = 'extract.mixin'
    _inherit = 'mail.thread.main.attachment'
    _description = 'Base class to extract data from documents'

    extract_state = fields.Selection([
            ('no_extract_requested', 'No extract requested'),
            ('not_enough_credit', 'Not enough credits'),
            ('error_status', 'An error occurred'),
            ('waiting_extraction', 'Waiting extraction'),
            ('extract_not_ready', 'waiting extraction, but it is not ready'),
            ('waiting_validation', 'Waiting validation'),
            ('to_validate', 'To validate'),
            ('done', 'Completed flow'),
        ],
        'Extract state', default='no_extract_requested', required=False, copy=False)
    extract_status = fields.Char('Extract status', copy=False)
    extract_error_message = fields.Text('Error message', compute='_compute_error_message')
    extract_document_uuid = fields.Char('ID of the request to IAP-OCR', copy=False, readonly=True)
    extract_can_show_send_button = fields.Boolean('Can show the ocr send button', compute='_compute_show_send_button')
    is_in_extractable_state = fields.Boolean(compute='_compute_is_in_extractable_state', store=True)
    extract_state_processed = fields.Boolean(compute='_compute_extract_state_processed', store=True)

    @api.depends('extract_status')
    def _compute_error_message(self):
        for record in self:
            if record.extract_status in ('success', 'processing'):
                record.extract_error_message = ''
            else:
                lazy_message = ERROR_MESSAGES.get(
                    record.extract_status, ERROR_MESSAGES['error_internal']
                )
                record.extract_error_message = self.env._(lazy_message)  # pylint: disable=gettext-variable

    @api.depends('extract_state')
    def _compute_extract_state_processed(self):
        for record in self:
            record.extract_state_processed = record.extract_state == 'waiting_extraction'

    @api.depends('is_in_extractable_state', 'extract_state', 'message_main_attachment_id')
    def _compute_show_send_button(self):
        for record in self:
            record.extract_can_show_send_button = (
                record._get_ocr_option_can_extract()
                and record.message_main_attachment_id
                and record.extract_state == 'no_extract_requested'
                and record.is_in_extractable_state
            )

    @api.depends()
    def _compute_is_in_extractable_state(self):
        """ Compute the is_in_extractable_state field. This method is meant to be overridden """
        return None

    def _get_iap_account(self):
        if self.company_id:
            return self.env['iap.account'].with_context(allowed_company_ids=[self.company_id.id]).get('invoice_ocr')
        else:
            return self.env['iap.account'].get('invoice_ocr')

    @api.model
    def check_all_status(self):
        for record in self.search(self._get_to_check_domain()):
            record._try_to_check_ocr_status()

    @api.model
    def _contact_iap_extract(self, pathinfo, params):
        """ Contact the IAP extract service and return the response. This method is meant to be overridden """
        return {}

    @api.model
    def _cron_validate(self):
        records_to_validate = self.with_context(skip_is_manually_modified=True).search(self._get_validation_domain())

        for record in records_to_validate:
            try:
                record._contact_iap_extract(
                    'validate',
                    params={
                        'document_token': record.extract_document_uuid,
                        'values': {
                            field: record._get_validation(field) for field in self._get_validation_fields()
                        }
                    }
                )
            except AccessError:
                pass

        records_to_validate.extract_state = 'done'
        return records_to_validate

    def _get_extract_status_channel(self):
        return f"extract.mixin.status#{self.extract_document_uuid}"

    @staticmethod
    def _get_ocr_selected_value(ocr_results, feature, default=None):
        return ocr_results.get(feature, {}).get('selected_value', {}).get('content', default)

    def _safe_upload(self):
        """
        This function prevents any exception from being thrown during the upload of a document.
        This is meant to be used for batch uploading where we don't want that an error rollbacks the whole transaction.
        """
        try:
            with self.env.cr.savepoint():
                self.with_company(self.company_id)._upload_to_extract()
        except Exception as e:
            if not isinstance(e, (IntegrityError, OperationalError)):
                self.extract_state = 'error_status'
                self.extract_status = 'error_internal'
            self.env['iap.account']._send_error_notification(
                message=self._get_iap_bus_notification_error(),
            )
            _logger.warning("Couldn't upload %s with id %d: %s", self._name, self.id, str(e))

    def _send_batch_for_digitization(self):
        for rec in self:
            rec._safe_upload()

    def action_send_batch_for_digitization(self):
        if any(not document.is_in_extractable_state for document in self):
            raise UserError(self._get_user_error_invalid_state_message())

        documents_to_send = self.filtered(
            lambda doc: doc.extract_state in ('no_extract_requested', 'not_enough_credit', 'error_status')
        )

        if not documents_to_send:
            self.env['iap.account']._send_status_notification(
                message=_('The selected documents are already digitized'),
                status='info',
            )
            return

        if len(documents_to_send) < len(self):
            self.env['iap.account']._send_status_notification(
                message=_('Some documents were skipped as they were already digitized'),
                status='info',
            )

        documents_to_send._send_batch_for_digitization()

        if len(documents_to_send) == 1:
            return {
                'name': _('Document sent for digitization'),
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'views': [[False, 'form']],
                'res_id': documents_to_send[0].id,
            }
        return {
            'name': _('Documents sent for digitization'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', documents_to_send.ids)],
        }

    def action_manual_send_for_digitization(self):
        """ Manually trigger the ocr flow for the records.
        This function is meant to be overridden, and called with a title.
        """
        self._upload_to_extract()
        return self.extract_state, self.extract_error_message, self.extract_document_uuid

    def buy_credits(self):
        url = self.env['iap.account'].get_credits_url(base_url='', service_name='invoice_ocr')
        return {
            'type': 'ir.actions.act_url',
            'url': url,
        }

    def check_ocr_status(self):
        """ Actively check the status of the extraction on the concerned records. """

        records_to_check = self.with_context(skip_is_manually_modified=True).filtered(lambda a: a.extract_state in ['waiting_extraction', 'extract_not_ready'])

        for record in records_to_check:
            record._check_ocr_status()

        limit = max(0, 20 - len(records_to_check))
        if limit > 0:
            records_to_preupdate = self.search([
                ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']),
                ('id', 'not in', records_to_check.ids),
                ('is_in_extractable_state', '=', True)], limit=limit)
            for record in records_to_preupdate:
                record._try_to_check_ocr_status()

        return [(rec.extract_state, rec.extract_error_message) for rec in self]

    def _get_user_infos(self):
        user_infos = {
            'user_lang': self.env.user.lang,
            'user_email': self.env.user.email,
        }
        return user_infos

    def _get_validation(self, field):
        """ Return the validation of the record. This method is meant to be overridden """
        return None

    def _upload_to_extract(self):
        """ Contacts IAP extract to parse the first attachment in the chatter."""
        self.ensure_one()
        if not self._get_ocr_option_can_extract():
            return False
        attachment = self.message_main_attachment_id
        if attachment and self.extract_state in ['no_extract_requested', 'not_enough_credit', 'error_status']:
            account_token = self._get_iap_account()

            if not account_token.account_token:
                self.extract_state = 'error_status'
                self.extract_status = 'error_invalid_account_token'
                return

            user_infos = self._get_user_infos()
            params = {
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'documents': [x.datas.decode('utf-8') for x in attachment],
                'user_infos': user_infos,
                'webhook_url': self._get_webhook_url(),
            }
            try:
                result = self._contact_iap_extract('parse', params=params)
                self.extract_status = result['status']
                if result['status'] == 'success':
                    self.extract_state = 'waiting_extraction'
                    self.extract_document_uuid = result['document_token']
                    if self.env['ir.config_parameter'].sudo().get_param("iap_extract.already_notified", True):
                        self.env['ir.config_parameter'].sudo().set_param("iap_extract.already_notified", False)
                    self.env['iap.account']._send_success_notification(
                        message=self._get_iap_bus_notification_success(),
                    )
                    self.env.user._bus_send("extract_mixin_new_document", {
                        'status': self.extract_state,
                        'error_message': self.extract_error_message,
                        'extract_document_uuid': self.extract_document_uuid,
                    })
                    self._upload_to_extract_success_callback()
                elif result['status'] == 'error_no_credit':
                    self._send_no_credit_notification()
                    self.extract_state = 'not_enough_credit'
                else:
                    self.extract_state = 'error_status'
                    _logger.warning(
                        'An error occurred during OCR parsing of %s %d. Status: %s',
                        self._name, self.id, self.extract_status,
                    )
            except AccessError:
                self.extract_state = 'error_status'
                self.extract_status = 'error_no_connection'
            if self.extract_state == 'error_status':
                self.env['iap.account']._send_error_notification(
                    message=self._get_iap_bus_notification_error(),
                )

    def _send_no_credit_notification(self):
        """
        Notify about the number of credit.
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """

        self.env['iap.account']._send_no_credit_notification(
            service_name='invoice_ocr',
            title=_("Not enough credits for data extraction"),
        )

        #If we don't find the config parameter, we consider it True, because we don't want to notify if no credits has been bought earlier.
        already_notified = self.env['ir.config_parameter'].sudo().get_param("iap_extract.already_notified", True)
        if already_notified:
            return
        try:
            mail_template = self.env.ref('iap_extract.iap_extract_no_credit')
        except ValueError:
            #if the mail template has not been created by an upgrade of the module
            return
        iap_account = self._get_iap_account()
        if iap_account:
            # Get the email address of the creators of the records
            res = self.env['res.users'].search_read([('id', '=', 2)], ['email'])
            if res:
                email_values = {
                    'email_to': res[0]['email']
                }
                mail_template.send_mail(iap_account.id, force_send=True, email_values=email_values)
                self.env['ir.config_parameter'].sudo().set_param("iap_extract.already_notified", True)

    def _validate_ocr(self):
        documents_to_validate = self.filtered(lambda doc: doc.extract_state == 'waiting_validation')
        documents_to_validate.extract_state = 'to_validate'

        if documents_to_validate:
            ocr_trigger_datetime = fields.Datetime.now() + relativedelta(minutes=self.env.context.get('ocr_trigger_delta', 0))
            self._get_cron_ocr('validate')._trigger(at=ocr_trigger_datetime)

    def _check_ocr_status(self):
        """ Contact iap to get the actual status of the ocr request. """
        self.ensure_one()
        self = self.with_context(skip_is_manually_modified=True)  # noqa: PLW0642
        result = self._contact_iap_extract('get_result', params={'document_token': self.extract_document_uuid})
        self.extract_status = result['status']
        if result['status'] == 'success':
            self.extract_state = 'waiting_validation'
            ocr_results = result['results'][0]
            self.with_company(self.company_id)._fill_document_with_results(ocr_results)
            # Set OdooBot as the author of the tracking message
            self._track_set_author(self.env.ref('base.partner_root'))
            if 'full_text_annotation' in ocr_results:
                self.message_main_attachment_id.index_content = ocr_results['full_text_annotation']

        elif result['status'] == 'processing':
            self.extract_state = 'extract_not_ready'
        else:
            self.extract_state = 'error_status'
        self.env["bus.bus"]._sendone(self._get_extract_status_channel(), "state_change", {
            'status': self.extract_state,
            'error_message': self.extract_error_message,
        })

    def _fill_document_with_results(self, ocr_results):
        """ Fill the document with the results of the OCR. This method is meant to be overridden """
        raise NotImplementedError()

    def _get_cron_ocr(self, ocr_action):
        """ Return the cron used to validate the documents, based on the module name.
        ocr_action can be 'validate'.
        """
        module_name = self._get_ocr_module_name()
        return self.env.ref(f'{module_name}.ir_cron_ocr_{ocr_action}')

    def _get_iap_bus_notification_success(self):
        return _("Document is being digitized")

    def _get_iap_bus_notification_error(self):
        return _("An error occurred during the upload")

    def _get_ocr_module_name(self):
        """ Returns the name of the module. This method is meant to be overridden """
        return 'iap_extract'

    def _get_ocr_option_can_extract(self):
        """ Returns if we can use the extract capabilities of the module. This method is meant to be overridden """
        return False

    def _get_to_check_domain(self):
        return [('is_in_extractable_state', '=', True),
                ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready'])]

    def _get_validation_domain(self):
        return [('extract_state', '=', 'to_validate')]

    def _get_validation_fields(self):
        """ Returns the fields that should be checked to validate the record. This method is meant to be overridden """
        return []

    def _get_webhook_url(self):
        """ Return the webhook url based on the module name. """
        baseurl = self.get_base_url()
        module_name = self._get_ocr_module_name()
        return f'{baseurl}/{module_name}/request_done'

    def _get_user_error_invalid_state_message(self):
        """
        Returns the message of the UserError when the user tries to send a document in an invalid state.
        This method is meant to be overridden.
        """
        return ''

    def _upload_to_extract_success_callback(self):
        """ This method is called when the OCR flow is successful. This method is meant to be overridden """
        return None

    def _try_to_check_ocr_status(self):
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self._check_ocr_status()
            self.env.cr.commit()
        except Exception as e:
            _logger.warning("Couldn't check OCR status of %s with id %d: %s", self._name, self.id, str(e))
