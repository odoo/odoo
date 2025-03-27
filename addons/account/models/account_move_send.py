from collections import defaultdict
from markupsafe import Markup

from odoo import _, api, models, modules, tools
from odoo.exceptions import UserError


class AccountMoveSend(models.AbstractModel):
    """ Shared class between the two sending wizards.
    See 'account.move.send.batch.wizard' for multiple invoices sending wizard (async)
    and 'account.move.send.wizard' for single invoice sending wizard (sync).
    """
    _name = 'account.move.send'
    _description = "Account Move Send"

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_sending_method(self, move) -> set:
        """ By default, we use the sending method set on the partner or email. """
        return move.partner_id.with_company(move.company_id).invoice_sending_method or 'email'

    @api.model
    def _get_all_extra_edis(self) -> dict:
        """ Returns a dict representing EDI data such as:
        { 'edi_key': {'label': 'EDI label', 'is_applicable': function, 'help': 'optional help'} }
        """
        return {}

    @api.model
    def _get_default_extra_edis(self, move) -> set:
        """ By default, we use all applicable extra EDIs. """
        extra_edis = self._get_all_extra_edis()
        return {edi_key for edi_key, edi_vals in extra_edis.items() if edi_vals['is_applicable'](move)}

    @api.model
    def _get_default_invoice_edi_format(self, move) -> str:
        """ By default, we generate the EDI format set on partner. """
        return move.partner_id.with_company(move.company_id).invoice_edi_format

    @api.model
    def _get_default_pdf_report_id(self, move):
        return move.partner_id.with_company(move.company_id).invoice_template_pdf_report_id or self.env.ref('account.account_invoices')

    @api.model
    def _get_default_mail_template_id(self, move):
        return move._get_mail_template()

    @api.model
    def _get_default_sending_settings(self, move, from_cron=False, **custom_settings):
        """ Returns a dict with all the necessary data to generate and send invoices.
        Either takes the provided custom_settings, or the default value.
        """
        def get_setting(key, from_cron=False, default_value=None):
            return custom_settings.get(key) if key in custom_settings else move.sending_data.get(key) if from_cron else default_value

        vals = {
            'sending_methods': get_setting('sending_methods', default_value={self._get_default_sending_method(move)}) or {},
            'invoice_edi_format': get_setting('invoice_edi_format', default_value=self._get_default_invoice_edi_format(move)),
            'extra_edis': get_setting('extra_edis', default_value=self._get_default_extra_edis(move)) or {},
            'pdf_report': get_setting('pdf_report') or self._get_default_pdf_report_id(move),
            'author_user_id': get_setting('author_user_id', from_cron=from_cron) or self.env.user.id,
            'author_partner_id': get_setting('author_partner_id', from_cron=from_cron) or self.env.user.partner_id.id,
        }
        if 'email' in vals['sending_methods']:
            mail_template = get_setting('mail_template') or self._get_default_mail_template_id(move)
            mail_lang = get_setting('mail_lang') or self._get_default_mail_lang(move, mail_template)
            vals.update({
                'mail_template': mail_template,
                'mail_lang': mail_lang,
                'mail_body': get_setting('mail_body', default_value=self._get_default_mail_body(move, mail_template, mail_lang)),
                'mail_subject': get_setting('mail_subject', default_value=self._get_default_mail_subject(move, mail_template, mail_lang)),
                'mail_partner_ids': get_setting('mail_partner_ids', default_value=self._get_default_mail_partner_ids(move, mail_template, mail_lang).ids),
                'mail_attachments_widget': get_setting('mail_attachments_widget', default_value=self._get_default_mail_attachments_widget(move, mail_template, extra_edis=vals['extra_edis'], pdf_report=vals['pdf_report'])),
            })
        return vals

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_alerts(self, moves, moves_data):
        """ Returns a dict of all alerts corresponding to moves with the given context (sending method,
        edi format to generate, extra_edi to generate).
        An alert can have some information:
        - level (danger, info, warning, ...)  (! danger alerts are considered blocking and will be raised)
        - message to display
        - action_text for the text to show on the clickable link
        - action the action to run when the link is clicked
        """
        alerts = {}
        if len(moves) > 1 and (partners_without_mail := moves.filtered(
                lambda m: 'email' in moves_data[m]['sending_methods'] and not m.partner_id.email).partner_id
        ):
            # should only appear in mass invoice sending
            alerts['account_missing_email'] = {
                'level': 'warning',
                'message': _("Partner(s) should have an email address."),
                'action_text': _("View Partner(s)"),
                'action': partners_without_mail._get_records_action(name=_("Check Partner(s) Email(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # MAIL
    # -------------------------------------------------------------------------

    @api.model
    def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
        if not mail_template:
            return
        return mail_template\
            .with_context(lang=lang)\
            ._render_field(field, move.ids, **kwargs)[move._origin.id]

    @api.model
    def _get_default_mail_lang(self, move, mail_template):
        return mail_template._render_lang([move.id]).get(move.id)

    @api.model
    def _get_default_mail_body(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            'body_html',
            options={'post_process': True},
        )

    @api.model
    def _get_default_mail_subject(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            'subject',
        )

    @api.model
    def _get_default_mail_partner_ids(self, move, mail_template, mail_lang):
        partners = self.env['res.partner'].with_company(move.company_id)
        if mail_template.email_to:
            email_to = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_to')
            for mail_data in tools.email_split(email_to):
                partners |= partners.find_or_create(mail_data)
        if mail_template.email_cc:
            email_cc = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_cc')
            for mail_data in tools.email_split(email_cc):
                partners |= partners.find_or_create(mail_data)
        if mail_template.partner_to:
            partner_to = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'partner_to')
            partner_ids = mail_template._parse_partner_to(partner_to)
            partners |= self.env['res.partner'].sudo().browse(partner_ids).exists()
        return partners.filtered('email')

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_mail_attachments_widget(self, move, mail_template, extra_edis=None, pdf_report=None):
        return self._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis) \
            + self._get_placeholder_mail_template_dynamic_attachments_data(move, mail_template, pdf_report=pdf_report) \
            + self._get_invoice_extra_attachments_data(move) \
            + self._get_mail_template_attachments_data(mail_template)

    @api.model
    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        """ Returns all the placeholder data.
        Should be extended to add placeholder based on the sending method.
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
    def _get_placeholder_mail_template_dynamic_attachments_data(self, move, mail_template, pdf_report=None):
        invoice_template = pdf_report or self._get_default_pdf_report_id(move)
        extra_mail_templates = mail_template.report_template_ids - invoice_template
        filename = move._get_invoice_report_filename()
        return [
            {
                'id': f'placeholder_{extra_mail_template.name.lower()}_{filename}',
                'name': f'{extra_mail_template.name.lower()}_{filename}',
                'mimetype': 'application/pdf',
                'placeholder': True,
                'dynamic_report': extra_mail_template.report_name,
            } for extra_mail_template in extra_mail_templates
        ]

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
        """ Returns all mail template data. """
        return [
            {
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'placeholder': False,
                'mail_template_id': mail_template.id,
                'protect_from_deletion': True,
            }
            for attachment in mail_template.attachment_ids
        ]

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _raise_danger_alerts(self, alerts):
        danger_alert_messages = [alert['message'] for _key, alert in alerts.items() if alert.get('level') == 'danger']
        if danger_alert_messages:
            raise UserError('\n'.join(danger_alert_messages))

    @api.model
    def _check_move_constrains(self, moves):
        if any(move.state != 'posted' for move in moves):
            raise UserError(_("You can't generate invoices that are not posted."))
        if any(not move.is_sale_document(include_receipts=True) for move in moves):
            raise UserError(_("You can only generate sales documents."))

    @api.model
    def _check_invoice_report(self, moves, **custom_settings):
        if ((
                custom_settings.get('pdf_report')
                and not custom_settings['pdf_report'].is_invoice_report
            )
            or any(not self._get_default_pdf_report_id(move).is_invoice_report for move in moves)
        ):
            raise UserError(_("The sending of invoices is not set up properly, make sure the report used is set for invoices."))

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
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _is_applicable_to_company(self, method, company):
        """ TO OVERRIDE - used to determine if we should display the sending method in the selection."""
        return True

    @api.model
    def _is_applicable_to_move(self, method, move):
        """ TO OVERRIDE - """
        return True

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        """ Hook allowing to add some extra data for the invoice passed as parameter before the rendering of the pdf
        report.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        return

    @api.model
    def _prepare_invoice_pdf_report(self, invoices_data):
        """ Prepare the pdf report for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """

        company_id = next(iter(invoices_data)).company_id
        grouped_invoices_by_report = defaultdict(dict)
        for invoice, invoice_data in invoices_data.items():
            grouped_invoices_by_report[invoice_data['pdf_report']][invoice] = invoice_data

        for pdf_report, group_invoices_data in grouped_invoices_by_report.items():
            ids = [inv.id for inv in group_invoices_data]

            content, report_type = self.env['ir.actions.report'].with_company(company_id)._pre_render_qweb_pdf(pdf_report.report_name, res_ids=ids)
            content_by_id = self.env['ir.actions.report']._get_splitted_report(pdf_report.report_name, content, report_type)

            for invoice, invoice_data in group_invoices_data.items():
                invoice_data['pdf_attachment_values'] = {
                    'name': invoice._get_invoice_report_filename(),
                    'raw': content_by_id[invoice.id],
                    'mimetype': 'application/pdf',
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': 'invoice_pdf_report_file',  # Binary field
                }

    @api.model
    def _prepare_invoice_proforma_pdf_report(self, invoice, invoice_data):
        """ Prepare the proforma pdf report for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        pdf_report = invoice_data['pdf_report']
        content, report_type = self.env['ir.actions.report'].with_company(invoice.company_id)._pre_render_qweb_pdf(pdf_report.report_name, invoice.ids, data={'proforma': True})
        content_by_id = self.env['ir.actions.report']._get_splitted_report(pdf_report.report_name, content, report_type)

        invoice_data['proforma_pdf_attachment_values'] = {
            'raw': content_by_id[invoice.id],
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
    def _link_invoice_documents(self, invoices_data):
        """ Create the attachments containing the pdf/electronic documents for the invoice passed as parameter.
        :param invoice:         An account.move record.
        :param invoice_data:    The collected data for the invoice so far.
        """
        # create an attachment that will become 'invoice_pdf_report_file'
        # note: Binary is used for security reason
        attachment_to_create = [invoice_data['pdf_attachment_values'] for invoice_data in invoices_data.values() if invoice_data.get('pdf_attachment_values')]
        if not attachment_to_create:
            return

        attachments = self.sudo().env['ir.attachment'].create(attachment_to_create)
        res_id_to_attachment = {attachment.res_id: attachment for attachment in attachments}

        for invoice, invoice_data in invoices_data.items():
            if attachment := res_id_to_attachment.get(invoice.id):
                invoice.message_main_attachment_id = attachment
                invoice.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])
                invoice.is_move_sent = True

    @api.model
    def _hook_if_errors(self, moves_data, allow_raising=True):
        """ Process errors found so far when generating the documents.
        :param from_cron:   Flag indicating if the method is called from a cron. In that case, we avoid raising any
                            error.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        for move, move_data in moves_data.items():
            error = move_data['error']
            if allow_raising:
                raise UserError(self._format_error_text(error))

            move.with_context(no_new_invoice=True).message_post(body=self._format_error_html(error))

    @api.model
    def _hook_if_success(self, moves_data):
        """ Process (typically send) successful documents."""
        to_send_mail = {
            move: move_data
            for move, move_data in moves_data.items()
            if 'email' in move_data['sending_methods'] and self._is_applicable_to_move('email', move)
        }
        self._send_mails(to_send_mail)

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """ Send the journal entry passed as parameter by mail. """
        partner_ids = kwargs.get('partner_ids', [])
        author_id = kwargs.pop('author_id')

        new_message = move\
            .with_context(
                no_new_invoice=True,
                mail_notify_author=author_id in partner_ids,
                email_notification_allow_footer=True,
            ).message_post(
                message_type='comment',
                **kwargs,
                **{  # noqa: PIE804
                    'email_layout_xmlid': self._get_mail_layout(),
                    'email_add_signature': not mail_template,
                    'mail_auto_delete': mail_template.auto_delete,
                    'mail_server_id': mail_template.mail_server_id.id,
                    'reply_to_force_new': False,
                }
            )

        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.invalidate_recordset(['res_id', 'res_model'], flush=False)
        if new_message.attachment_ids.ids:
            self.env.cr.execute("UPDATE ir_attachment SET res_id = NULL WHERE id IN %s", [tuple(new_message.attachment_ids.ids)])
        new_message.attachment_ids.write({
            'res_model': new_message._name,
            'res_id': new_message.id,
        })

    @api.model
    def _get_mail_layout(self):
        return 'mail.mail_notification_layout_with_responsible_signature'

    @api.model
    def _get_mail_params(self, move, move_data):
        # We must ensure the newly created PDF are added. At this point, the PDF has been generated but not added
        # to 'mail_attachments_widget'.
        mail_attachments_widget = move_data.get('mail_attachments_widget')
        seen_attachment_ids = set()
        to_exclude = {x['name'] for x in mail_attachments_widget if x.get('skip')}
        for attachment_data in self._get_invoice_extra_attachments_data(move) + mail_attachments_widget:
            if attachment_data['name'] in to_exclude and not attachment_data.get('manual'):
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
            'author_id': move_data['author_partner_id'],
            'body': move_data['mail_body'],
            'subject': move_data['mail_subject'],
            'partner_ids': move_data['mail_partner_ids'],
            'attachments': mail_attachments,
        }

    @api.model
    def _generate_dynamic_reports(self, moves_data):
        for move, move_data in moves_data.items():
            mail_attachments_widget = move_data.get('mail_attachments_widget', [])

            dynamic_reports = [
                attachment_widget
                for attachment_widget in mail_attachments_widget
                if attachment_widget.get('dynamic_report')
                and not attachment_widget.get('skip')
            ]

            attachments_to_create = []
            for dynamic_report in dynamic_reports:
                content, _report_format = self.env['ir.actions.report']\
                .with_company(move.company_id)\
                .with_context(from_account_move_send=True)\
                ._render(dynamic_report['dynamic_report'], move.ids)

                attachments_to_create.append({
                    'raw': content,
                    'name': dynamic_report['name'],
                    'mimetype': 'application/pdf',
                    'res_model': move._name,
                    'res_id': move.id,
                })

            attachments = self.env['ir.attachment'].create(attachments_to_create)
            mail_attachments_widget += [{
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': 'application/pdf',
                'placeholder': False,
                'protect_from_deletion': True,
            } for attachment in attachments]

    @api.model
    def _send_mails(self, moves_data):
        subtype = self.env.ref('mail.mt_comment')

        self._generate_dynamic_reports(moves_data)

        for move, move_data in [
            (move, move_data)
            for move, move_data in moves_data.items()
            if move.partner_id.email or move_data.get('mail_partner_ids')
        ]:
            mail_template = move_data['mail_template']
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
        return not modules.module.current_test

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
        :param invoices_data:   The collected data for invoices so far.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        """
        for invoice, invoice_data in invoices_data.items():
            self._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
            invoice_data['blocking_error'] = invoice_data.get('error') \
                                             and not (allow_fallback_pdf and invoice_data.get('error_but_continue'))
            invoice_data['error_but_continue'] = allow_fallback_pdf and invoice_data.get('error_but_continue')

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
            if not invoice_data.get('error') or invoice_data.get('error_but_continue')
        }

        # Use batch to avoid memory error
        batch_size = self.env['ir.config_parameter'].sudo().get_param('account.pdf_generation_batch', '80')
        batches = []
        pdf_to_generate = {}
        for invoice, invoice_data in invoices_data_pdf.items():
            if not invoice_data.get('error') and not invoice.invoice_pdf_report_id:  # we don't regenerate pdf if it already exists
                pdf_to_generate[invoice] = invoice_data

                if (len(pdf_to_generate) > int(batch_size)):
                    batches.append(pdf_to_generate)
                    pdf_to_generate = {}

        if pdf_to_generate:
            batches.append(pdf_to_generate)

        for batch in batches:
            self._prepare_invoice_pdf_report(batch)

        for invoice, invoice_data in invoices_data_pdf.items():
            if not invoice_data.get('error') and not invoice.invoice_pdf_report_id:
                self._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)

        # Cleanup the error if we don't want to block the regular pdf generation.
        if allow_fallback_pdf:
            invoices_data_pdf_error = {
                invoice: invoice_data
                for invoice, invoice_data in invoices_data.items()
                if invoice_data.get('pdf_attachment_values') and invoice_data.get('error')
            }
            if invoices_data_pdf_error:
                self._hook_if_errors(invoices_data_pdf_error, allow_raising=not allow_fallback_pdf)

        # Web-service after the PDF generation.
        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get('error')
        }
        if invoices_data_web_service:
            self._call_web_service_after_invoice_pdf_render(invoices_data_web_service)

        # Create and link the generated documents to the invoice if the web-service didn't failed.
        invoices_to_link = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data_web_service.items()
            if not invoice_data.get('error') or allow_fallback_pdf
        }
        self._link_invoice_documents(invoices_to_link)

    @api.model
    def _generate_invoice_fallback_documents(self, invoices_data):
        """ Generate the invoice PDF and electronic documents.
        :param invoices_data:   The collected data for invoices so far.
        """
        for invoice, invoice_data in invoices_data.items():
            if not invoice.invoice_pdf_report_id and invoice_data.get('error'):
                invoice_data.pop('error')
                self._prepare_invoice_proforma_pdf_report(invoice, invoice_data)
                self._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
                invoice_data['proforma_pdf_attachment'] = self.env['ir.attachment']\
                    .create(invoice_data.pop('proforma_pdf_attachment_values'))

    def _check_sending_data(self, moves, **custom_settings):
        """Assert the data provided to _generate_and_send_invoices are correct.
        This is a security in case the method is called directly without going through the wizards.
        """
        self._check_move_constrains(moves)
        self._check_invoice_report(moves, **custom_settings)
        assert all(
            sending_method in dict(self.env['res.partner']._fields['invoice_sending_method'].selection)
            for sending_method in custom_settings.get('sending_methods', [])
        ) if 'sending_methods' in custom_settings else True

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        """ Generate and send the moves given custom_settings if provided, else their default configuration set on related partner/company.
        :param moves: account.move to process
        :param from_cron: whether the processing comes from a cron.
        :param allow_raising: whether the process can raise errors, or should log them on the move's chatter.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a proforma PDF report instead.
        :param custom_settings: settings to apply instead of related partner's defaults settings.
        """
        self._check_sending_data(moves, **custom_settings)
        moves_data = {
            move.sudo(): {
                **self._get_default_sending_settings(move, from_cron=from_cron, **custom_settings),
            }
            for move in moves
        }

        # Generate all invoice documents (PDF and electronic documents if relevant).
        self._generate_invoice_documents(moves_data, allow_fallback_pdf=allow_fallback_pdf)

        # Manage errors.
        errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
        if errors:
            self._hook_if_errors(errors, allow_raising=not from_cron and not allow_fallback_pdf and allow_raising)

        # Fallback in case of error.
        errors = {move: move_data for move, move_data in moves_data.items() if move_data.get('error')}
        if allow_fallback_pdf and errors:
            self._generate_invoice_fallback_documents(errors)

        # Successfully generated a PDF - Process sending.
        success = {move: move_data for move, move_data in moves_data.items() if not move_data.get('error')}
        if success:
            self._hook_if_success(success)

        # Update sending data of moves
        for move, move_data in moves_data.items():
            if from_cron and move_data.get('error'):
                move.sending_data = {'error': True}
            else:
                move.sending_data = False

        # Return generated attachments.
        attachments = self.env['ir.attachment']
        for move, move_data in success.items():
            attachments += self._get_invoice_extra_attachments(move) or move_data['proforma_pdf_attachment']
        return attachments
