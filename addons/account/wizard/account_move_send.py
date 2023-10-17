# -*- coding: utf-8 -*-
from markupsafe import Markup
from werkzeug.urls import url_encode

from odoo import _, api, fields, models, modules, tools, Command
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class AccountMoveSend(models.TransientModel):
    _name = 'account.move.send'
    _description = "Account Move Send"

    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id', store=True)
    move_ids = fields.Many2many(comodel_name='account.move')
    mode = fields.Selection(
        selection=[
            ('invoice_single', "Invoice Single"),
            ('invoice_multi', "Invoice Multi"),
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
    enable_send_mail = fields.Boolean(compute='_compute_enable_send_mail')
    checkbox_send_mail = fields.Boolean(
        string="Email",
        compute='_compute_checkbox_send_mail',
        store=True,
        readonly=False,
    )
    display_mail_composer = fields.Boolean(compute='_compute_send_mail_extra_fields')
    send_mail_warning_message = fields.Boolean(compute='_compute_send_mail_extra_fields')
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
        compute='_compute_mail_subject_body',
        store=True,
        readonly=False,
    )
    mail_body = fields.Html(
        string="Contents",
        sanitize_style=True,
        compute='_compute_mail_subject_body',
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
            move_ids = self._context.get('active_ids', [])
            if any(move.state == 'draft' for move in self.env['account.move'].browse(move_ids)):
                raise UserError(_("You can't Send & Print invoice(s) in draft state."))
            results['move_ids'] = [Command.set(move_ids)]

        return results

    @api.model
    def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
        if not mail_template:
            return
        return mail_template\
            .with_context(lang=lang)\
            ._render_field(field, move.ids, **kwargs)[move._origin.id]

    def _get_default_mail_lang(self, move, mail_template=None):
        return mail_template._render_lang([move.id]).get(move.id) if mail_template else get_lang(self.env).code

    def _get_default_mail_body(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            'body_html',
            options={'post_process': True},
        )

    def _get_default_mail_subject(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            'subject',
        )

    def _get_default_mail_partner_ids(self, move, mail_template, mail_lang):
        partners = self.env['res.partner'].with_company(move.company_id)
        if mail_template.email_to:
            for mail_data in tools.email_split(mail_template.email_to):
                partners |= partners.find_or_create(mail_data)
        if mail_template.email_cc:
            for mail_data in tools.email_split(mail_template.email_cc):
                partners |= partners.find_or_create(mail_data)
        if mail_template.partner_to:
            partner_to = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'partner_to')
            partner_ids = mail_template._parse_partner_to(partner_to)
            partners |= self.env['res.partner'].sudo().browse(partner_ids).exists()
        return partners

    def _get_default_mail_attachments_widget(self, move, mail_template):
        return self._get_placeholder_mail_attachments_data(move) \
            + self._get_invoice_extra_attachments_data(move) \
            + self._get_mail_template_attachments_data(mail_template)

    def _get_wizard_values(self):
        self.ensure_one()
        return {
            'mail_template_id': self.mail_template_id.id,
            'download': self.checkbox_download,
            'send_mail': self.checkbox_send_mail,
        }

    def _get_mail_move_values(self, move, wizard=None):
        mail_template_id = move.send_and_print_values and move.send_and_print_values.get('mail_template_id')
        mail_template = wizard and wizard.mail_template_id or self.env['mail.template'].browse(mail_template_id)
        mail_lang = self._get_default_mail_lang(move, mail_template)
        return {
            'mail_template_id': mail_template,
            'mail_lang': mail_lang,
            'mail_body': wizard and wizard.mail_body or self._get_default_mail_body(move, mail_template, mail_lang),
            'mail_subject': wizard and wizard.mail_subject or self._get_default_mail_subject(move, mail_template, mail_lang),
            'mail_partner_ids': wizard and wizard.mail_partner_ids or self._get_default_mail_partner_ids(move, mail_template, mail_lang),
            'mail_attachments_widget': wizard and wizard.mail_attachments_widget or self._get_default_mail_attachments_widget(move, mail_template),
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

        filename = move._get_invoice_report_filename()
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
                'protect_from_deletion': True,
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
            wizard.mode = 'invoice_single' if len(wizard.move_ids) == 1 else 'invoice_multi'

    @api.depends('move_ids')
    def _compute_enable_download(self):
        for wizard in self:
            wizard.enable_download = wizard.mode in ('invoice_single', 'invoice_multi')

    @api.depends('enable_download')
    def _compute_checkbox_download(self):
        for wizard in self:
            wizard.checkbox_download = wizard.enable_download and wizard.company_id.invoice_is_download

    @api.depends('move_ids')
    def _compute_enable_send_mail(self):
        for wizard in self:
            wizard.enable_send_mail = wizard.mode in ('invoice_single', 'invoice_multi')

    @api.depends('enable_send_mail')
    def _compute_checkbox_send_mail(self):
        for wizard in self:
            wizard.checkbox_send_mail = wizard.company_id.invoice_is_email and not wizard.send_mail_readonly

    @api.depends('checkbox_send_mail')
    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == 'invoice_single'
            invoices_without_mail_data = wizard.move_ids.filtered(lambda x: not x.partner_id.email)
            wizard.send_mail_readonly = invoices_without_mail_data == wizard.move_ids
            wizard.send_mail_warning_message = bool(invoices_without_mail_data) and (wizard.checkbox_send_mail or wizard.send_mail_readonly)

    @api.depends('mail_template_id')
    def _compute_mail_lang(self):
        for wizard in self:
            if wizard.mode == 'invoice_single':
                wizard.mail_lang = self._get_default_mail_lang(wizard.move_ids, wizard.mail_template_id)
            else:
                wizard.mail_lang = get_lang(self.env).code

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            if wizard.mode == 'invoice_single' and wizard.mail_template_id:
                wizard.mail_partner_ids = self._get_default_mail_partner_ids(self.move_ids, wizard.mail_template_id, wizard.mail_lang)
            else:
                wizard.mail_partner_ids = None

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_subject_body(self):
        for wizard in self:
            if wizard.mode == 'invoice_single' and wizard.mail_template_id:
                wizard.mail_subject = self._get_default_mail_subject(wizard.move_ids, wizard.mail_template_id, wizard.mail_lang)
                wizard.mail_body = self._get_default_mail_body(wizard.move_ids, wizard.mail_template_id, wizard.mail_lang)
            else:
                wizard.mail_subject = wizard.mail_body = None

    @api.depends('mail_template_id')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mode == 'invoice_single':
                manual_attachments_data = [x for x in wizard.mail_attachments_widget or [] if x.get('manual')]
                wizard.mail_attachments_widget = (
                        self._get_default_mail_attachments_widget(wizard.move_ids, wizard.mail_template_id)
                        + manual_attachments_data
                )
            else:
                wizard.mail_attachments_widget = []

    @api.model
    def _format_error_text(self, error):
        """ Format the error that can be either a dict (complex format needed) or a string (simple format) into a
        regular string.

        :param error: the error to format.
        :return: a text formatted error.
        """
        if isinstance(error, dict):
            errors = '\n- '.join(error['errors'])
            return f"{error['error_title']}\n- {errors}" if errors else error['error_title']
        else:
            return error

    @api.model
    def _format_error_html(self, error):
        """ Format the error that can be either a dict (complex format needed) or a string (simple format) into a
        valid html format.

        :param error: the error to format.
        :return: a html formatted error.
        """
        if isinstance(error, dict):
            errors = Markup().join(Markup("<li>%s</li>") % error for error in error['errors'])
            return Markup("%s<ul>%s</ul>") % (error['error_title'], errors)
        else:
            return error

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_partners_without_email(self, res_ids=None):
        partners = self.move_ids.mapped("partner_id").filtered(lambda x: not x.email)
        if len(partners) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'target': 'current',
                'res_id': partners.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'tree,form',
                'target': 'current',
                'name': _('Partners without email'),
                'context': {'create': False, 'delete': False},
                'domain': [('id', 'in', partners.ids)],
            }

    @api.model
    def _need_invoice_document(self, invoice):
        """ Determine if we need to generate the documents for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :return: True if the PDF / electronic documents must be generated, False otherwise.
        """
        return not invoice.invoice_pdf_report_id and invoice.state == 'posted'

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        """ Hook allowing to add some extra data for the invoice passed as parameter before the rendering of the pdf
        report.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        return

    @api.model
    def _prepare_invoice_pdf_report(self, invoice, invoice_data):
        """ Prepare the pdf report for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        if invoice.invoice_pdf_report_id:
            return

        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids)

        invoice_data['pdf_attachment_values'] = {
            'raw': content,
            'name': invoice._get_invoice_report_filename(),
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'invoice_pdf_report_file', # Binary field
        }

    @api.model
    def _prepare_invoice_proforma_pdf_report(self, invoice, invoice_data):
        """ Prepare the proforma pdf report for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids, data={'proforma': True})

        invoice_data['proforma_pdf_attachment_values'] = {
            'raw': content,
            'name': invoice._get_invoice_proforma_pdf_report_filename(),
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
        }

    @api.model
    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        """ Hook allowing to add some extra data for the invoice passed as parameter after the rendering of the
        (proforma) pdf report.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        return

    @api.model
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

    @api.model
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
                raise UserError(self._format_error_text(error))

            move.with_context(no_new_invoice=True).message_post(body=self._format_error_html(error))

    @api.model
    def _hook_if_success(self, moves_data, from_cron=False, allow_fallback_pdf=False):
        """ Process successful documents.
        :param from_cron:   Flag indicating if the method is called from a cron. In that case, we avoid raising any
                            error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        to_send_mail = {move: move_data for move, move_data in moves_data.items() if move_data.get('send_mail')}
        self._send_mails(to_send_mail)

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """ Send the journal entry passed as parameter by mail. """
        partner_ids = kwargs.get('partner_ids', [])

        new_message = move\
            .with_context(
                no_new_invoice=True,
                mail_notify_author=self.env.user.partner_id.id in partner_ids,
            ).message_post(
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

    @api.model
    def _get_mail_params(self, move, move_data):
        # We must ensure the newly created PDF are added. At this point, the PDF has been generated but not added
        # to 'mail_attachments_widget'.
        mail_attachments_widget = move_data.get('mail_attachments_widget')
        seen_attachment_ids = set()
        to_exclude = {x['name'] for x in mail_attachments_widget if x.get('skip')}
        for attachment_data in self._get_invoice_extra_attachments_data(move) + mail_attachments_widget:
            if attachment_data['name'] in to_exclude:
                continue

            try:
                attachment_id = int(attachment_data['id'])
            except ValueError:
                continue

            seen_attachment_ids.add(attachment_id)

        mail_attachments = [
            (attachment.name, attachment.raw)
            for attachment in self.env['ir.attachment'].browse(list(seen_attachment_ids)).exists()
        ]

        return {
            'body': move_data['mail_body'],
            'subject': move_data['mail_subject'],
            'partner_ids': move_data['mail_partner_ids'].ids,
            'attachments': mail_attachments,
        }

    @api.model
    def _send_mails(self, moves_data):
        subtype = self.env.ref('mail.mt_comment')

        for move, move_data in moves_data.items():
            mail_template = move_data['mail_template_id']
            mail_lang = move_data['mail_lang']
            mail_params = self._get_mail_params(move, move_data)
            if not mail_params:
                continue

            if move_data.get('proforma_pdf_attachment'):
                attachment = move_data['proforma_pdf_attachment']
                mail_params['attachments'].append((attachment.name, attachment.raw))

            email_from = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
            model_description = move.with_context(lang=mail_lang).type_name

            self._send_mail(
                move,
                mail_template,
                subtype_id=subtype.id,
                model_description=model_description,
                email_from=email_from,
                **mail_params,
            )

    @api.model
    def _can_commit(self):
        """ Helper to know if we can commit the current transaction or not.
        :return: True if commit is accepted, False otherwise.
        """
        return not tools.config['test_enable'] and not modules.module.current_test

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # TO OVERRIDE
        # call a web service before the pdfs are rendered
        return

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # TO OVERRIDE
        # call a web service after the pdfs are rendered
        return

    @api.model
    def _generate_invoice_documents(self, invoices_data, allow_fallback_pdf=False):
        """ Generate the invoice PDF and electronic documents.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        :param invoices_data:   The collected data for invoices so far.
        """
        for invoice, invoice_data in invoices_data.items():
            if self._need_invoice_document(invoice):
                self._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
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
            if self._need_invoice_document(invoice) and not invoice_data.get('error'):
                self._prepare_invoice_pdf_report(invoice, invoice_data)
                self._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)

        # Cleanup the error if we don't want to block the regular pdf generation.
        if allow_fallback_pdf:
            invoices_data_pdf_error = {
                invoice: invoice_data
                for invoice, invoice_data in invoices_data.items()
                if invoice_data.get('pdf_attachment_values') and invoice_data.get('error')
            }
            if invoices_data_pdf_error:
                self._hook_if_errors(invoices_data_pdf_error, allow_fallback_pdf=allow_fallback_pdf)

        # Web-service after the PDF generation.
        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get('error')
        }
        if invoices_data_web_service:
            self._call_web_service_after_invoice_pdf_render(invoices_data_web_service)

        # Create and link the generated documents to the invoice if the web-service didn't failed.
        for invoice, invoice_data in invoices_data_pdf.items():
            if not invoice_data.get('error') and self._need_invoice_document(invoice):
                self._link_invoice_documents(invoice, invoice_data)

    @api.model
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

    def _download(self, attachment_ids, moves_data=None):
        """ Download the PDF or the zip of PDF if we are in 'multi' mode. """
        if len(attachment_ids) == 1:
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{attachment_ids[0]}?download=true",
                'close': True,  # close the wizard
            }
        else:
            filename = next(iter(moves_data))._get_invoice_report_filename(extension='zip') if len(moves_data) == 1 else 'invoices.zip'
            return {
                'type': 'ir.actions.act_url',
                'url': f"/account/export_zip_documents?{url_encode({'ids': attachment_ids, 'filename': filename})}",
                'close': True,
            }

    @api.model
    def _process_send_and_print(self, moves, wizard=None, allow_fallback_pdf=False, **kwargs):
        """ Process the moves given their individual configuration set on move.send_and_print_values.
        :param moves: account.move to process
        :param wizard: account.move.send wizard if exists. If not we avoid raising any error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a proforma PDF report instead.
        """
        from_cron = not wizard

        moves_data = {
            move: {
                **(move.send_and_print_values if not wizard else wizard._get_wizard_values()),
                **self._get_mail_move_values(move, wizard),
            }
            for move in moves
        }

        # Generate all invoice documents.
        self._generate_invoice_documents(moves_data, allow_fallback_pdf=allow_fallback_pdf)

        # Manage errors.
        errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
        if errors:
            self._hook_if_errors(errors, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

        # Fallback in case of error.
        errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
        if allow_fallback_pdf and errors:
            self._generate_invoice_fallback_documents(errors)

        # Send mail.
        success = {move: move_data for move, move_data in moves_data.items() if not move_data.get('error') and move.partner_id.email}
        if success:
            self._hook_if_success(success, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

        # Update send and print values of moves
        for move in moves:
            if move.send_and_print_values:
                move.send_and_print_values = False

        to_download = {move: move_data for move, move_data in moves_data.items() if move_data.get('download')}
        if to_download:
            attachment_ids = []
            for move, move_data in to_download.items():
                attachment_ids += self._get_invoice_extra_attachments(move).ids or move_data.get('proforma_pdf_attachment').ids
            if attachment_ids:
                if kwargs.get('bypass_download'):
                    return attachment_ids
                return self._download(attachment_ids, to_download)

        return {'type': 'ir.actions.act_window_close'}

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False, **kwargs):
        """ Create the documents and send them to the end customers.
        If we are sending multiple invoices and not downloading them we will process the moves asynchronously.
        :param force_synchronous:   Flag indicating if the method should be done synchronously.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        self.ensure_one()

        if self.mode == 'invoice_multi' and self.checkbox_send_mail and not self.mail_template_id:
            raise UserError(_('Please select a mail template to send multiple invoices.'))

        force_synchronous = force_synchronous or self.checkbox_download
        process_later = self.mode == 'invoice_multi' and not force_synchronous
        if process_later:
            # Set sending information on moves
            for move in self.move_ids:
                move.send_and_print_values = self._get_wizard_values()
            self.env.ref('account.ir_cron_account_move_send')._trigger()
            return {'type': 'ir.actions.act_window_close'}

        return self._process_send_and_print(
            self.move_ids,
            wizard=self,
            allow_fallback_pdf=allow_fallback_pdf,
            **kwargs,
        )
