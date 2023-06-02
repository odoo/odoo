# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, modules, tools, Command
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class AccountMoveSend(models.Model):
    _name = 'account.move.send'
    _description = "Account Move Send"

    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id', store=True)
    move_ids = fields.Many2many(comodel_name='account.move')
    mode = fields.Selection(
        selection=[
            ('invoice_single', "Invoice Single"),
            ('invoice_multi', "Invoice Multi"),
            ('done', "Done"),
        ],
        compute='_compute_mode',
        readonly=False,
        store=True,
    )

    # == PRINT ==
    enable_download = fields.Boolean(compute='_compute_enable_download')
    checkbox_download = fields.Boolean(
        string="Download",
        compute='_compute_checkbox_download',
        store=True,
        readonly=False,
    )

    # == MAIL ==
    enable_send_mail = fields.Boolean(compute='_compute_send_mail_extra_fields')
    checkbox_send_mail = fields.Boolean(
        string="Email",
        compute='_compute_checkbox_send_mail',
        store=True,
        readonly=False,
    )
    display_mail_composer = fields.Boolean(compute='_compute_send_mail_extra_fields')
    send_mail_warning_message = fields.Text(compute='_compute_send_mail_extra_fields')
    send_mail_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields')

    mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Use template",
        domain="[('model', '=', 'account.move')]",
    )
    mail_lang = fields.Char(
        string="Lang",
        compute='_compute_mail_lang',
    )
    mail_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Recipients",
        compute='_compute_mail_partner_ids',
        store=True,
        readonly=False,
    )
    mail_subject = fields.Char(
        string="Subject",
        compute='_compute_mail_subject',
        store=True,
        readonly=False,
    )
    mail_body = fields.Html(
        string="Contents",
        sanitize_style=True,
        compute='_compute_mail_body',
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        compute='_compute_mail_attachments_widget',
        store=True,
        readonly=False,
    )

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)

        if 'move_ids' in fields_list and 'move_ids' not in results:
            results['move_ids'] = [Command.set(self._context.get('active_ids', []))]

        return results

    @api.model
    def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
        return mail_template\
            .with_context(lang=lang)\
            ._render_field(field, move.ids, **kwargs)[move._origin.id]

    def _get_available_field_values_in_multi(self, move):
        self.ensure_one()
        return {
            'move_ids': [Command.set(move.ids)],
            'mail_template_id': self.mail_template_id.id,
            'checkbox_send_mail': self.checkbox_send_mail,
        }

    def _get_placeholder_mail_attachments_data(self, move):
        """ Returns all the placeholder data.
        Should be extended to add placeholder based on the checkboxes.

        :param: move:       The current move.
        :returns: A list of dictionary for each placeholder.
        * id:               str: The (fake) id of the attachment, this is needed in rendering in t-key.
        * name:             str: The name of the attachment.
        * mimetype:         str: The mimetype of the attachment.
        * placeholder       bool: Should be true to prevent download / deletion.
        """
        if move.invoice_pdf_report_id:
            return []

        filename = move._get_invoice_pdf_report_filename()
        return [{
            'id': f'placeholder_{filename}',
            'name': filename,
            'mimetype': 'application/pdf',
            'placeholder': True,
        }]

    @api.model
    def _get_invoice_extra_attachments(self, move):
        return move.invoice_pdf_report_id

    @api.model
    def _get_invoice_extra_attachments_data(self, move):
        return [
            {
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'placeholder': False,
            }
            for attachment in self._get_invoice_extra_attachments(move)
        ]

    @api.model
    def _get_mail_template_attachments_data(self, mail_template):
        """ Returns all the placeholder data and mail template data
        """
        return [
            {
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'placeholder': False,
                'mail_template_id': mail_template.id,
            }
            for attachment in mail_template.attachment_ids
        ]

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_company_id(self):
        for wizard in self:
            if len(wizard.move_ids.company_id) > 1:
                raise UserError(_("You can only send from the same company."))
            wizard.company_id = wizard.move_ids.company_id.id

    @api.depends('move_ids')
    def _compute_mode(self):
        for wizard in self:
            mode = 'done'
            if wizard.move_ids and all(x.is_invoice(include_receipts=True) for x in wizard.move_ids):
                mode = 'invoice_single' if len(wizard.move_ids) == 1 else 'invoice_multi'
            wizard.mode = mode

    @api.depends('move_ids')
    def _compute_enable_download(self):
        for wizard in self:
            wizard.enable_download = wizard.mode == 'invoice_single'

    @api.depends('enable_download')
    def _compute_checkbox_download(self):
        for wizard in self:
            wizard.checkbox_download = wizard.enable_download and wizard.company_id.invoice_is_download

    @api.depends('move_ids')
    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.enable_send_mail = wizard.mode in ('invoice_single', 'invoice_multi')
            wizard.display_mail_composer = wizard.mode == 'invoice_single'
            send_mail_readonly = False

            display_messages = []
            if wizard.enable_send_mail:
                invoices_without_mail_data = wizard.move_ids.filtered(lambda x: not x.partner_id.email)
                if invoices_without_mail_data:
                    if wizard.mode == 'invoice_multi':
                        display_messages.append(_(
                            "The following invoice(s) will not be sent by email, because the customers don't have email "
                            "address: "
                        ))
                        display_messages.append(", ".join(invoices_without_mail_data.mapped('name')))
                        send_mail_readonly = True
                    else:
                        display_messages.append(_("Please add an email address for your partner"))

            wizard.send_mail_readonly = send_mail_readonly
            wizard.send_mail_warning_message = "".join(display_messages) if display_messages else None

    @api.depends('move_ids')
    def _compute_checkbox_send_mail(self):
        for wizard in self:
            wizard.checkbox_send_mail = wizard.company_id.invoice_is_email and not wizard.send_mail_readonly

    @api.depends('mail_template_id')
    def _compute_mail_lang(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                move = wizard.move_ids
                wizard.mail_lang = wizard.mail_template_id._render_lang([move.id]).get(move.id)
            else:
                wizard.mail_lang = get_lang(self.env).code

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                move = wizard.move_ids
                partners = self.env['res.partner'].with_company(move.company_id)
                mail_template = wizard.mail_template_id
                if mail_template.email_to:
                    for mail_data in tools.email_split(mail_template.email_to):
                        partners |= partners.find_or_create(mail_data)
                if mail_template.email_cc:
                    for mail_data in tools.email_split(mail_template.email_cc):
                        partners |= partners.find_or_create(mail_data)
                if mail_template.partner_to:
                    partner_to = wizard._get_mail_default_field_value_from_template(mail_template, wizard.mail_lang, move,
                                                                                  'partner_to')
                    partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                    partners |= self.env['res.partner'].sudo().browse(partner_ids).exists()
                wizard.mail_partner_ids = partners
            else:
                wizard.mail_partner_ids = []

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_subject(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_subject = wizard._get_mail_default_field_value_from_template(
                    wizard.mail_template_id,
                    wizard.mail_lang,
                    wizard.move_ids,
                    'subject',
                )
            else:
                wizard.mail_subject = None

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_body(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_body = wizard._get_mail_default_field_value_from_template(
                    wizard.mail_template_id,
                    wizard.mail_lang,
                    wizard.move_ids,
                    'body_html',
                    options={'post_process': True},
                )
            else:
                wizard.mail_body = None

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mode == 'invoice_single':
                manual_attachments_data = [x for x in wizard.mail_attachments_widget or [] if x.get('manual')]
                wizard.mail_attachments_widget = \
                    wizard._get_placeholder_mail_attachments_data(wizard.move_ids) \
                    + wizard._get_invoice_extra_attachments_data(wizard.move_ids) \
                    + wizard._get_mail_template_attachments_data(wizard.mail_template_id) \
                    + manual_attachments_data
            else:
                wizard.mail_attachments_widget = []

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _need_invoice_document(self, invoice):
        """ Determine if we need to generate the documents for the invoice passed as parameter.

        :param invoice:         An account.move record.
        :return: True if the PDF / electronic documents must be generated, False otherwise.
        """
        self.ensure_one()
        return self.mode == 'invoice_single' and not invoice.invoice_pdf_report_id and invoice.state == 'posted'

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        """ Hook allowing to add some extra data for the invoice passed as parameter before the rendering of the pdf
        report.

        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        self.ensure_one()

    def _prepare_invoice_pdf_report(self, invoice, invoice_data):
        """ Prepare the pdf report for the invoice passed as parameter.

        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        self.ensure_one()

        if invoice.invoice_pdf_report_id:
            return

        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids)

        invoice_data['pdf_attachment_values'] = {
            'raw': content,
            'name': invoice._get_invoice_pdf_report_filename(),
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'invoice_pdf_report_file', # Binary field
        }

    def _prepare_invoice_proforma_pdf_report(self, invoice, invoice_data):
        """ Prepare the proforma pdf report for the invoice passed as parameter.

        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        self.ensure_one()

        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids, data={'proforma': True})

        invoice_data['proforma_pdf_attachment_values'] = {
            'raw': content,
            'name': invoice._get_invoice_proforma_pdf_report_filename(),
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
        }

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        """ Hook allowing to add some extra data for the invoice passed as parameter after the rendering of the
        (proforma) pdf report.

        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        self.ensure_one()

    def _link_invoice_documents(self, invoice, invoice_data):
        """ Create the attachments containing the pdf/electronic documents for the invoice passed as parameter.

        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        # create an attachment that will become 'invoice_pdf_report_file'
        # note: Binary is used for security reason
        invoice.message_main_attachment_id = self.env['ir.attachment'].create(invoice_data['pdf_attachment_values'])
        invoice.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])
        invoice.is_move_sent = True

    def _hook_if_errors(self, moves_data, from_cron=False, allow_fallback_pdf=False):
        """ Process errors found so far when generating the documents.

        :param from_cron:   Flag indicating if the method is called from a cron. In that case, we avoid raising any
                            error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        allow_raising = not from_cron and not allow_fallback_pdf
        for move, move_data in moves_data.items():
            error = move_data['error']
            if allow_raising:
                raise UserError(error)

            move.with_context(no_new_invoice=True).message_post(body=error)

    def _hook_if_success(self, moves_data, from_cron=False, allow_fallback_pdf=False):
        """ Process successful documents.

        :param from_cron:   Flag indicating if the method is called from a cron. In that case, we avoid raising any
                            error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        send_mail = self.enable_send_mail and self.checkbox_send_mail

        # Send mail.
        if send_mail:
            self._send_mails(moves_data)

    def _send_mail(self, move, **kwargs):
        """ Send the journal entry passed as parameter by mail. """
        self.ensure_one()
        partner_ids = kwargs.get('partner_ids', [])
        mail_template = self.mail_template_id

        new_message = move\
            .with_context(
                no_new_invoice=True,
                mail_notify_author=self.env.user.partner_id.id in partner_ids,
                mailing_document_based=True)\
            .message_post(
                message_type='comment',
                **kwargs,
                **{
                    'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                    'email_add_signature': not mail_template,
                    'mail_auto_delete': mail_template.auto_delete,
                    'mail_server_id': mail_template.mail_server_id.id,
                    'reply_to_force_new': False,
                },
            )

        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.write({
            'res_model': new_message._name,
            'res_id': new_message.id,
        })

    def _get_mail_params(self, move):
        self.ensure_one()

        if self.mode != 'invoice_single':
            return

        # We must ensure the newly created PDF are added. At this point, the PDF has been generated but not added
        # to 'mail_attachments_widget'.
        seen_attachment_ids = set()
        for attachment_data in self._get_invoice_extra_attachments_data(self.move_ids) + self.mail_attachments_widget:
            try:
                attachment_id = int(attachment_data['id'])
            except ValueError:
                continue

            seen_attachment_ids.add(attachment_id)

        mail_attachments = [
            (attachment.name, attachment.raw)
            for attachment in self.env['ir.attachment'].browse(list(seen_attachment_ids))
        ]

        return {
            'body': self.mail_body,
            'subject': self.mail_subject,
            'partner_ids': self.mail_partner_ids.ids,
            'attachments': mail_attachments,
        }

    def _send_mails(self, moves_data):
        self.ensure_one()
        subtype = self.env.ref('mail.mt_comment')
        mail_template = self.mail_template_id

        for move, move_data in moves_data.items():
            form = move_data['_form']
            mail_params = form._get_mail_params(move)
            if not mail_params:
                continue

            if move_data.get('proforma_pdf_attachment'):
                attachment = move_data['proforma_pdf_attachment']
                mail_params['attachments'].append((attachment.name, attachment.raw))

            mail_lang = form.mail_lang
            email_from = form._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
            model_description = move.with_context(lang=mail_lang).type_name

            form._send_mail(
                move,
                subtype_id=subtype.id,
                model_description=model_description,
                email_from=email_from,
                **mail_params,
            )

    def _can_commit(self):
        """ Helper to know if we can commit the current transaction or not.

        :return: True if commit is accepted, False otherwise.
        """
        self.ensure_one()
        return not tools.config['test_enable'] and not modules.module.current_test

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # TO OVERRIDE
        # call a web service before the pdfs are rendered
        self.ensure_one()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # TO OVERRIDE
        # call a web service after the pdfs are rendered
        self.ensure_one()

    def _generate_invoice_documents(self, invoices_data, allow_fallback_pdf=False):
        """ Generate the invoice PDF and electronic documents.

        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        :param invoices_data:   The collected data for invoices so far.
        """
        for invoice, invoice_data in invoices_data.items():
            form = invoice_data['_form']
            if form._need_invoice_document(invoice):
                form._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
                invoice_data['blocking_error'] = invoice_data.get('error') \
                                                 and not (allow_fallback_pdf and invoice_data.get('error_but_continue'))
                if invoice_data['blocking_error']:
                    continue

        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get('error')
        }
        if invoices_data_web_service:
            self._call_web_service_before_invoice_pdf_render(invoices_data_web_service)

        invoices_data_pdf = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get('error') or not invoice_data.get('blocking_error', True)
        }
        for invoice, invoice_data in invoices_data_pdf.items():
            form = invoice_data['_form']
            if form._need_invoice_document(invoice):
                form._prepare_invoice_pdf_report(invoice, invoice_data)
                form._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
                form._link_invoice_documents(invoice, invoice_data)

        # check for errors again
        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get('error')
        }
        if invoices_data_web_service:
            self._call_web_service_after_invoice_pdf_render(invoices_data_web_service)

    def _generate_invoice_fallback_documents(self, invoices_data):
        """ Generate the invoice PDF and electronic documents.

        :param invoices_data:   The collected data for invoices so far.
        """
        for invoice, invoice_data in invoices_data.items():
            if self._need_invoice_document(invoice) and invoice_data.get('error'):
                invoice_data.pop('error')
                self._prepare_invoice_proforma_pdf_report(invoice, invoice_data)
                self._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
                invoice_data['proforma_pdf_attachment'] = self.env['ir.attachment']\
                    .create(invoice_data.pop('proforma_pdf_attachment_values'))

    @api.model
    def _download(self, attachment_id):
        """ Download the PDF. """
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment_id}?download=true',
            'close': True, # close the wizard
        }

    def action_send_and_print(self, from_cron=False, allow_fallback_pdf=False):
        """ Create the documents and send them to the end customers.

        :param from_cron:   Flag indicating if the method is called from a cron. In that case, we avoid raising any
                            error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        self.ensure_one()

        download = self.enable_download and self.checkbox_download
        generate_invoice_documents = self.mode == 'invoice_single' or (self.mode == 'invoice_multi' and from_cron)
        moves_data = {move: {} for move in self.move_ids}

        if len(moves_data) == 1:
            moves_data[self.move_ids]['_form'] = self
        else:
            for move in self.move_ids:
                moves_data[move]['_form'] = self.new(self._get_available_field_values_in_multi(move))

        if generate_invoice_documents:
            # Generate all invoice documents.
            self._generate_invoice_documents(moves_data, allow_fallback_pdf=allow_fallback_pdf)

            # Manage errors.
            errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
            if errors:
                self._hook_if_errors(errors, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

            # Cleanup the error if we don't want to block the regular pdf generation.
            for move_data in errors.values():
                if move_data.get('pdf_attachment_values'):
                    move_data.pop('error')

            # Fallback in case of error.
            errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
            if allow_fallback_pdf and errors:
                self._generate_invoice_fallback_documents(errors)

            # Send mail.
            success = {move: move_data for move, move_data in moves_data.items() if not move_data.get('error')}
            if success:
                self._hook_if_success(success, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

            self.mode = 'done'

        if not from_cron:
            self.env.ref('account.ir_cron_account_move_send')._trigger()

        if download:
            attachment = self.move_ids.invoice_pdf_report_id
            if not attachment:
                attachment = list(moves_data.values())[0].get('proforma_pdf_attachment')
            if attachment:
                return self._download(attachment.id)

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        self.ensure_one()
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}
