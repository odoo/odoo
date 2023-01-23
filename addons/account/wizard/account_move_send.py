# -*- coding: utf-8 -*-
import io

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


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
    button_name = fields.Char(compute='_compute_button_name')

    # == PRINT ==
    enable_download = fields.Boolean(compute='_compute_enable_download')
    download = fields.Boolean(
        string="Download",
        compute='_compute_download',
        store=True,
        readonly=False,
    )

    # == MAIL ==
    display_mail_composer = fields.Boolean(compute='_compute_send_mail_extra_fields')
    enable_send_mail = fields.Boolean(compute='_compute_send_mail_extra_fields')
    send_mail_warning_message = fields.Text(compute='_compute_send_mail_extra_fields')
    send_mail_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields')
    send_mail = fields.Boolean(
        string="Email",
        compute='_compute_send_mail',
        store=True,
        readonly=False,
    )

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
    def _get_mail_default_field_value_from_template(self, mail_template, lang, move, field, **kwargs):
        return mail_template\
            .with_context(lang=lang)\
            ._render_field(field, move.ids, **kwargs)[move._origin.id]

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

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_mode_from_moves(self, moves):
        self.ensure_one()
        if all(x.is_invoice(include_receipts=True) for x in moves):
            return 'invoice_single' if len(moves) == 1 else 'invoice_multi'
        return None

    @api.depends('move_ids')
    def _compute_mode(self):
        for wizard in self:
            if wizard.move_ids:
                wizard.mode = wizard._get_default_mode_from_moves(wizard.move_ids)
            else:
                wizard.mode = 'done'

    @api.depends('enable_download', 'download', 'enable_send_mail', 'send_mail')
    def _compute_button_name(self):
        for wizard in self:
            actions = []
            if wizard.enable_send_mail and wizard.send_mail:
                actions.append(_("Send"))
            if wizard.enable_download and wizard.download:
                actions.append(_("Print"))
            wizard.button_name = " & ".join(actions) if actions else None

    @api.depends('move_ids')
    def _compute_enable_download(self):
        for wizard in self:
            wizard.enable_download = wizard.mode == 'invoice_single'

    @api.depends('enable_download')
    def _compute_download(self):
        for wizard in self:
            wizard.download = wizard.company_id.invoice_is_print

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
    def _compute_send_mail(self):
        for wizard in self:
            wizard.send_mail = wizard.company_id.invoice_is_email and not wizard.send_mail_readonly

    @api.model
    def _get_default_lang(self, mail_template):
        if mail_template:
            return mail_template._render_lang([0])[0]
        else:
            return get_lang(self.env).code

    @api.depends('mail_template_id')
    def _compute_mail_lang(self):
        for wizard in self:
            wizard.mail_lang = wizard._get_default_lang(wizard.mail_template_id)

    @api.model
    def _get_default_mail_partners(self, mail_template, lang, move):
        self.ensure_one()
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

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_partner_ids = wizard._get_default_mail_partners(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_partner_ids = []

    @api.model
    def _get_default_mail_subject(self, mail_template, lang, move):
        return self._get_mail_default_field_value_from_template(mail_template, lang, move, 'subject')

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_subject(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_subject = wizard._get_default_mail_subject(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_subject = None

    @api.model
    def _get_default_mail_body(self, mail_template, lang, move):
        return self._get_mail_default_field_value_from_template(mail_template, lang, move, 'body_html', options={'post_process': True})

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_body(self):
        for wizard in self:
            if wizard.mail_template_id and wizard.mode == 'invoice_single':
                wizard.mail_body = wizard._get_default_mail_body(wizard.mail_template_id, wizard.mail_lang, wizard.move_ids)
            else:
                wizard.mail_body = None

    @api.model
    def _get_default_mail_attachments_data(self, mail_template, move):
        results = []

        if self._get_default_mode_from_moves(move) == 'invoice_single' and move.pdf_report_id:
            attachment = move.pdf_report_id
            results.append({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
            })

        for attachment in mail_template.attachment_ids:
            results.append({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
            })

        return results

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mode == 'invoice_single':
                wizard.mail_attachments_widget = wizard\
                    ._get_default_mail_attachments_data(wizard.mail_template_id, wizard.move_ids)
            else:
                wizard.mail_attachments_widget = []

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _need_pdf_report(self, move):
        return not move.pdf_report_id and move.state == 'posted'

    def _prepare_invoice_documents(self, invoice):
        self.ensure_one()

        content, _report_format = self.env['ir.actions.report']._render('account.account_invoices', invoice.ids)
        filename = f"{invoice.name.replace('/', '_')}.pdf"
        return {
            'pdf_attachment_values': {
                'raw': content,
                'name': filename,
                'mimetype': 'application/pdf',
                'res_model': invoice._name,
                'res_id': invoice.id,
            },
            'pdf_attachment_options': {
                'need_postprocess_pdf': False,
            },
        }

    def _prepare_invoice_documents_failed(self, invoice, prepared_data, from_cron=False):
        self.ensure_one()
        if from_cron:
            invoice\
                .with_context(no_new_invoice=True)\
                .message_post(body=prepared_data['error'])
        else:
            raise UserError(prepared_data['error'])

    def _postprocess_invoice_pdf(self, invoice, pdf_writer, prepared_data):
        self.ensure_one()

    def _generate_invoice_documents(self, invoice, prepared_data):
        self.ensure_one()

        if prepared_data['pdf_attachment_options'].get('need_postprocess_pdf'):
            # Read pdf content.
            reader_buffer = io.BytesIO(prepared_data['pdf_attachment_values']['raw'])
            reader = OdooPdfFileReader(reader_buffer, strict=False)

            # Post-process.
            writer = OdooPdfFileWriter()
            writer.cloneReaderDocumentRoot(reader)
            self._postprocess_invoice_pdf(invoice, writer, prepared_data)

            # Replace the current content.
            writer_buffer = io.BytesIO()
            writer.write(writer_buffer)
            prepared_data['pdf_attachment_values']['raw'] = writer_buffer.getvalue()
            reader_buffer.close()
            writer_buffer.close()

        invoice.pdf_report_id = self.env['ir.attachment'].create(prepared_data['pdf_attachment_values'])

        self.mail_attachments_widget = (self.mail_attachments_widget or []) + [{
            'id': invoice.pdf_report_id.id,
            'name': invoice.pdf_report_id.name,
            'mimetype': invoice.pdf_report_id.mimetype,
        }]

    @api.model
    def _send_mail(self, mail_template, lang, move, **kwargs):
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
        move.is_move_sent = True

    def _download(self):
        """ Download the PDF. """
        if self.mode != 'invoice_single' or not self.move_ids.pdf_report_id:
            return

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.move_ids.pdf_report_id.id}?download=true',
            'close_on_report_download': True,
        }

    def action_send_and_print(self, from_cron=False):
        self.ensure_one()

        send_mail = self.enable_send_mail and self.send_mail
        download = self.enable_download and self.download

        subtype = self.env.ref('mail.mt_comment')
        mail_template = self.mail_template_id
        mail_lang = self.mail_lang
        if self.mode == 'invoice_single':
            move = self.move_ids

            # Ensure the invoice report is generated.
            if self._need_pdf_report(move):
                prepared_data = self._prepare_invoice_documents(move)
                if prepared_data.get('error'):
                    self._prepare_invoice_documents_failed(move, prepared_data, from_cron=from_cron)
                else:
                    self._generate_invoice_documents(move, prepared_data)

            # Send mail.
            if send_mail:
                attachment_ids = set(
                    attachment_vals['id']
                    for attachment_vals in self.mail_attachments_widget or []
                )
                attachment_ids.add(move.pdf_report_id.id)

                email_from = self\
                    ._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')

                partners = self.mail_partner_ids

                self._send_mail(
                    mail_template,
                    mail_lang,
                    move,
                    body=self.mail_body,
                    subject=self.mail_subject,
                    email_from=email_from,
                    subtype_id=subtype.id,
                    partner_ids=partners.ids,
                    attachment_ids=list(attachment_ids),
                )

            # Download.
            if download:
                action = self._download()
                if action:
                    return action

            self.mode = 'done'

        elif from_cron and self.mode == 'invoice_multi':
            for move in self.move_ids:

                # Ensure the invoice report is generated.
                if self._need_pdf_report(move):
                    prepared_data = self._prepare_invoice_documents(move)
                    if prepared_data.get('error'):
                        self._prepare_invoice_documents_failed(move, prepared_data, from_cron=from_cron)
                    else:
                        self._generate_invoice_documents(move, prepared_data)

                # Send mail.
                if send_mail:
                    attachment_ids = set(
                        attachment_vals['id']
                        for attachment_vals in self._get_default_mail_attachments_data(mail_template, move)
                    )
                    attachment_ids.add(move.pdf_report_id.id)

                    email_from = self._get_mail_default_field_value_from_template(
                        mail_template,
                        mail_lang,
                        move,
                        'email_from',
                    )

                    partners = self._get_default_mail_partners(mail_template, mail_lang, move)
                    body = self._get_default_mail_body(mail_template, mail_lang, move)
                    subject = self._get_default_mail_subject(mail_template, mail_lang, move)

                    self._send_mail(
                        mail_template,
                        mail_lang,
                        move,
                        body=body,
                        subject=subject,
                        email_from=email_from,
                        subtype_id=subtype.id,
                        partner_ids=partners.ids,
                        attachment_ids=list(attachment_ids),
                    )
            self.mode = 'done'

        self.env.ref('account.ir_cron_account_move_send')._trigger()

        return {'type': 'ir.actions.act_window_close'}

    def action_save_as_template(self):
        self.ensure_one()

        model = self.env['ir.model']._get('account.move')
        template_name = _("Invoice: %s", tools.ustr(self.mail_subject))
        attachment_ids = [attachment_vals['id'] for attachment_vals in self.mail_attachments_widget]

        self.mail_template_id = self.env['mail.template'].create({
            'name': template_name,
            'subject': self.mail_subject,
            'body_html': self.mail_body,
            'model_id': model.id,
            'attachment_ids': [Command.set(attachment_ids)],
            'use_default_to': True,
        })

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': self._name,
            'target': 'new',
            'context': self._context,
        }
