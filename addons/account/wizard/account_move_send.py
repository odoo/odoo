# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class AccountMoveSend(models.Model):
    _name = 'account.move.send'
    _description = "Account Move Send"

    company_id = fields.Many2one(comodel_name='res.company')
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
        domain=[('type', '!=', 'private')],
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

        if 'move_ids' in results:
            moves = self.env['account.move'].browse(results['move_ids'][0][2])
            if len(moves.company_id) > 1:
                raise UserError(_("You can only send from the same company."))
            results['company_id'] = moves.company_id.id

        return results

    @api.model
    def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
        return mail_template\
            .with_context(lang=lang)\
            ._render_field(field, move.ids, **kwargs)[move._origin.id]

    @api.model
    def _get_default_mode_from_moves(self, moves):
        if all(x.is_invoice(include_receipts=True) for x in moves):
            return 'invoice_single' if len(moves) == 1 else 'invoice_multi'
        return None

    @api.model
    def _get_default_lang(self, mail_template, move):
        if mail_template:
            return mail_template._render_lang([move.id]).get(move.id)
        else:
            return get_lang(self.env).code

    @api.model
    def _get_default_mail_partners(self, mail_template, lang, move):
        partners = self.env['res.partner'].with_company(move.company_id)
        if mail_template.email_to:
            for mail_data in tools.email_split(mail_template.email_to):
                partners |= partners.find_or_create(mail_data)
        if mail_template.email_cc:
            for mail_data in tools.email_split(mail_template.email_cc):
                partners |= partners.find_or_create(mail_data)
        if mail_template.partner_to:
            partner_to = self._get_mail_default_field_value_from_template(mail_template, lang, move, 'partner_to')
            partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
            partners |= self.env['res.partner'].sudo().browse(partner_ids).exists()
        return partners

    @api.model
    def _get_default_mail_body(self, mail_template, lang, move):
        return self._get_mail_default_field_value_from_template(mail_template, lang, move, 'body_html', options={'post_process': True})

    @api.model
    def _get_default_mail_subject(self, mail_template, lang, move):
        return self._get_mail_default_field_value_from_template(mail_template, lang, move, 'subject')

    @api.model
    def _get_default_email_from(self, mail_template, lang, move):
        return self._get_mail_default_field_value_from_template(mail_template, lang, move, 'email_from')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_mode(self):
        for wizard in self:
            if wizard.move_ids:
                wizard.mode = wizard._get_default_mode_from_moves(wizard.move_ids)
            else:
                wizard.mode = 'done'

    @api.depends('move_ids')
    def _compute_enable_download(self):
        for wizard in self:
            wizard.enable_download = wizard.mode == 'invoice_single'

    @api.depends('enable_download')
    def _compute_checkbox_download(self):
        for wizard in self:
            wizard.checkbox_download = wizard.company_id.invoice_is_print

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
            if wizard.mode == 'invoice_single':
                wizard.mail_lang = wizard._get_default_lang(wizard.mail_template_id, wizard.move_ids)
            else:
                wizard.mail_lang = False

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_partner_ids = wizard._get_default_mail_partners(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_partner_ids = []

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_subject(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_subject = wizard._get_default_mail_subject(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_subject = None

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_body(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_body = wizard._get_default_mail_body(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_body = None

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mail_attachments_widget: # When checkboxes are ticked in UI
                wizard.mail_attachments_widget = wizard._get_placeholder_mail_attachments_data(wizard.move_ids)\
                    + wizard._get_selected_attachments_data()
            elif wizard.mode == 'invoice_single':
                wizard.mail_attachments_widget = wizard\
                    ._get_default_mail_attachments_data(wizard.mail_template_id, wizard.move_ids)
            else:
                wizard.mail_attachments_widget = []

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_linked_attachments(self, move):
        """ Returns all the attachments ids linked to the move to be sent in the email.
        Should be extended to add attachments based on the checkboxes.
        """
        return move.invoice_pdf_report_id

    def _get_mail_attachments_ids(self, mail_template, move):
        """ Returns all the attachments ids linked to the move to be sent in the email
        AND the attachments selected by the user or the one from the template (invoice multi)
        """
        self.ensure_one()
        if self.mode == 'invoice_single':
            return self._get_selected_attachments_ids() + self._get_linked_attachments(move).ids
        else:
            return mail_template.attachment_ids.ids + self._get_linked_attachments(move).ids

    def _get_selected_attachments_ids(self):
        """ Returns all the attachments ids selected by the user (invoice single)
        """
        return [vals['id'] for vals in self._get_selected_attachments_data()]

    def _get_selected_attachments_data(self):
        """ Returns all the attachments data selected by the user (invoice single)
        """
        return list(filter(lambda x: not x.get('placeholder'), self.mail_attachments_widget))

    def _get_placeholder_mail_attachments_data(self, move):
        """ Returns all the placeholder data.
        Should be extended to add placeholder based on the checkboxes.

        :returns: A list of dictionary for each placeholder.
        * id:               str: The (fake) id of the attachment, this is needed in rendering in t-key.
        * name:             str: The name of the attachment.
        * mimetype:         str: The mimetype of the attachment.
        * placeholder       bool: should be true to prevent download / deletion
        """
        self.ensure_one()
        filename = self._get_invoice_pdf_report_filename(move)
        return [{
            'id': f'placeholder_{filename}',
            'name': filename,
            'mimetype': 'application/pdf',
            'placeholder': True,
        }]

    def _get_default_mail_attachments_data(self, mail_template, move):
        """ Returns all the placeholder data and mail template data
        """
        results = []

        for attachment in mail_template.attachment_ids:
            results.append({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'placeholder': False,
            })

        return self._get_placeholder_mail_attachments_data(move) + results

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_pdf_report_filename(self, move):
        return f"{move.name.replace('/', '_')}.pdf"

    @api.model
    def _need_document(self, move):
        return not move.invoice_pdf_report_id and move.state == 'posted'

    @api.model
    def _download(self, move):
        """ Download the PDF. """
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{move.invoice_pdf_report_id.id}?download=true',
            'close': True, # close the wizard
        }

    @api.model
    def _send_mail(self, mail_template, move, **kwargs):
        """ Send the journal entries passed as parameter by mail. """
        partner_ids = kwargs.get('partner_ids', [])

        move\
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

    def _send_mails(self, moves):
        subtype = self.env.ref('mail.mt_comment')
        mail_template = self.mail_template_id

        for move in moves:
            attachment_ids = self._get_mail_attachments_ids(mail_template, move)
            mail_lang = self.mail_lang or self._get_default_lang(mail_template, move)
            partners = self.mail_partner_ids or self._get_default_mail_partners(mail_template, mail_lang, move)
            body = self.mail_body or self._get_default_mail_body(mail_template, mail_lang, move)
            subject = self.mail_subject or self._get_default_mail_subject(mail_template, mail_lang, move)
            email_from = self._get_default_email_from(mail_template, mail_lang, move)
            model_description = move.with_context(lang=mail_lang).type_name

            self._send_mail(
                mail_template,
                move,
                body=body,
                subject=subject,
                email_from=email_from,
                subtype_id=subtype.id,
                partner_ids=partners.ids,
                attachment_ids=attachment_ids,
                model_description=model_description,
            )

    def _generate_documents_success_hook(self, moves, from_cron):
        send_mail = self.enable_send_mail and self.checkbox_send_mail

        # Send mail.
        if send_mail:
            self._send_mails(moves)

        return moves

    def _generate_documents_failed_hook(self, errors, from_cron):
        for move, error in errors:
            if from_cron:
                move\
                    .with_context(no_new_invoice=True)\
                    .message_post(body=error)
            else:
                raise UserError(error)

    def _link_document(self, invoice, prepared_data):
        """ Link prepared_data to the record
        """
        # create an attachment that will become 'invoice_pdf_report_file'
        # note: Binary is used for security reason
        self.env['ir.attachment'].create(prepared_data['pdf_attachment_values'])
        invoice.invalidate_model(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])
        self.env.add_to_compute(invoice._fields['is_move_sent'], invoice)

    def _postprocess_document(self, invoice, prepared_data):
        """ Postprocess prepared_data before it gets linked to the record
        """
        self.ensure_one()

    def _render_document(self, invoice, prepared_data):
        """ Extend prepared_data with the rendered documents
        """
        self.ensure_one()

        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids)

        prepared_data['pdf_attachment_values'] = {
            'raw': content,
            'name': self._get_invoice_pdf_report_filename(invoice),
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'invoice_pdf_report_file', # Binary field
        }

    def _prepare_document(self, invoice):
        """ To be overridden by modules adding support for different action in send&print.
        :return: 'prepared_data'
            { 'error' : str - if any, will be raised
              'xxx_values': {} - prefered naming for object to be linked as attachments
              'xxx_options': {} - prefered naming for object to be used later on }
        """
        self.ensure_one()
        return {}

    def _call_web_service(self, prepared_data_list):
        # TO OVERRIDE
        return

    def _generate_documents(self, moves, from_cron):
        """ Main entry point to generate the invoice pdf and the related attachments.
        """
        prepared_data_list = []
        success, errors = self.env['account.move'], []
        for move in moves:
            try:
                if self._need_document(move):
                    prepared_data = self._prepare_document(move)
                    if prepared_data.get('error'):
                        raise UserError(prepared_data['error'])
                    else:
                        prepared_data_list.append((move, prepared_data))
            except UserError as e:
                errors.append((move, str(e)))

        try:
            self._call_web_service(prepared_data_list)
        except UserError as e:
            for move, _prepared_data in prepared_data_list:
                errors.append((move, str(e)))
            return success, errors

        for move, prepared_data in prepared_data_list:
            self._render_document(move, prepared_data)
            self._postprocess_document(move, prepared_data)
            self._link_document(move, prepared_data)
            success |= move

        return success, errors

    def action_send_and_print(self, from_cron=False):
        self.ensure_one()

        download = self.enable_download and self.checkbox_download
        generate_documents = self.mode == 'invoice_single' or from_cron

        if generate_documents:
            success_moves, errors = self._generate_documents(self.move_ids, from_cron)

            self._generate_documents_success_hook(success_moves, from_cron)
            self._generate_documents_failed_hook(errors, from_cron)

            self.mode = 'done'

        if not from_cron:
            self.env.ref('account.ir_cron_account_move_send')._trigger()

        if download:
            return self._download(self.move_ids)

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        self.ensure_one()
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}
