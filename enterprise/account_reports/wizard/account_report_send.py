from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class AccountReportSend(models.TransientModel):
    _name = 'account.report.send'
    _description = "Account Report Send"

    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        compute='_compute_partner_ids',
    )
    mode = fields.Selection(
        selection=[
            ('single', "Single Recipient"),
            ('multi', "Multiple Recipients"),
        ],
        compute='_compute_mode',
        readonly=False,
        store=True,
    )

    # == PRINT ==
    enable_download = fields.Boolean()
    checkbox_download = fields.Boolean(string="Download")

    # == MAIL ==
    enable_send_mail = fields.Boolean(default=True)
    checkbox_send_mail = fields.Boolean(string="Email", default=True)

    display_mail_composer = fields.Boolean(compute='_compute_send_mail_extra_fields')
    warnings = fields.Json(compute='_compute_warnings')
    send_mail_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields')
    mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Email template",
        domain="[('model', '=', 'res.partner')]",
    )

    account_report_id = fields.Many2one(
        comodel_name='account.report',
        string="Report",
    )
    report_options = fields.Json()

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

        context_options = self._context.get('default_report_options', {})
        if 'account_report_id' in fields_list and 'account_report_id' not in results:
            report_id = context_options.get('report_id', False)
            results['account_report_id'] = report_id
            results['report_options'] = context_options

        return results

    @api.model
    def _get_mail_field_value(self, partner, mail_template, mail_lang, field, **kwargs):
        if not mail_template:
            return
        return mail_template\
            .with_context(lang=mail_lang)\
            ._render_field(field, partner.ids, **kwargs)[partner._origin.id]

    def _get_default_mail_attachments_widget(self, partner, mail_template):
        return self._get_placeholder_mail_attachments_data(partner) \
            + self._get_mail_template_attachments_data(mail_template)

    def _get_wizard_values(self):
        self.ensure_one()
        options = self.report_options
        if not options.get('partner_ids', []):
            options['partner_ids'] = self.partner_ids.ids
        return {
            'mail_template_id': self.mail_template_id.id,
            'checkbox_download': self.checkbox_download,
            'checkbox_send_mail': self.checkbox_send_mail,
            'report_options': options,
        }

    def _get_placeholder_mail_attachments_data(self, partner):
        """ Returns all the placeholder data.
        Should be extended to add placeholder based on the checkboxes.
        :param: partner:       The partner for which this report is generated.
        :returns: A list of dictionary for each placeholder.
        * id:               str: The (fake) id of the attachment, this is needed in rendering in t-key.
        * name:             str: The name of the attachment.
        * mimetype:         str: The mimetype of the attachment.
        * placeholder       bool: Should be true to prevent download / deletion.
        """
        self.ensure_one()
        filename = f"{partner.name} - {self.account_report_id.get_default_report_filename(self.report_options, 'pdf')}"
        return [{
            'id': f'placeholder_{filename}',
            'name': filename,
            'mimetype': 'application/pdf',
            'placeholder': True,
        }]

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

    @api.depends('partner_ids')
    def _compute_mode(self):
        for wizard in self:
            wizard.mode = 'single' if len(wizard.partner_ids) == 1 else 'multi'

    @api.depends('checkbox_send_mail')
    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == 'single'
            partners_without_mail_data = wizard.mail_partner_ids.filtered(lambda x: not x.email)
            wizard.send_mail_readonly = partners_without_mail_data == wizard.mail_partner_ids

    @api.depends('mail_partner_ids', 'checkbox_send_mail', 'send_mail_readonly')
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}

            partners_without_mail = wizard.mail_partner_ids.filtered(lambda x: not x.email)
            if wizard.send_mail_readonly or (wizard.checkbox_send_mail and partners_without_mail):
                warnings['account_missing_email'] = {
                    'message': _("Partner(s) should have an email address."),
                    'action_text': _("View Partner(s)"),
                    'action': partners_without_mail._get_records_action(name=_("Check Partner(s) Email(s)"))
                }

            wizard.warnings = warnings

    @api.depends('partner_ids')
    def _compute_mail_lang(self):
        for wizard in self:
            if wizard.mode == 'single':
                wizard.mail_lang = wizard.partner_ids.lang
            else:
                wizard.mail_lang = get_lang(self.env).code

    @api.depends('account_report_id', 'report_options')
    def _compute_partner_ids(self):
        for wizard in self:
            wizard.partner_ids = wizard.account_report_id._get_report_send_recipients(wizard.report_options)

    @api.depends('account_report_id', 'report_options', 'mail_template_id')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            wizard.mail_partner_ids = wizard.partner_ids

    @api.depends('mail_template_id', 'mail_lang', 'mode')
    def _compute_mail_subject_body(self):
        for wizard in self:
            if wizard.mode == 'single' and wizard.mail_template_id:
                wizard.mail_subject = self._get_mail_field_value(wizard.mail_partner_ids, wizard.mail_template_id, wizard.mail_lang, 'subject')
                wizard.mail_body = self._get_mail_field_value(wizard.mail_partner_ids, wizard.mail_template_id, wizard.mail_lang, 'body_html', options={'post_process': True})
            else:
                wizard.mail_subject = wizard.mail_body = None

    @api.depends('mail_template_id', 'mode')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mode == 'single':
                wizard.mail_attachments_widget = wizard._get_default_mail_attachments_widget(wizard.mail_partner_ids, wizard.mail_template_id)
            else:
                wizard.mail_attachments_widget = []

    @api.model
    def _action_download(self, attachments):
        """ Download the PDF attachment, or a zip of attachments if there are more than one. """
        return {
            'type': 'ir.actions.act_url',
            'url': f'/account_reports/download_attachments/{",".join(map(str, attachments.ids))}',
            'close': True,
        }

    def _process_send_and_print(self, report, options, recipient_partner_ids=None, wizard=None):
        """ Generate a report for one partner based on the options (send_and_print_values stored on the report).
        :param options: dict of report options (should contain one partner id in options['partner_ids'])
        :param recipient_partner_ids: list of partner ids that will receive the mail message.
        :param wizard: account.report.send wizard if exists. Indicates if sending by cron.
        """
        wizard_vals = report.send_and_print_values if not wizard else wizard._get_wizard_values()
        to_email = wizard_vals['checkbox_send_mail']
        to_download = wizard_vals['checkbox_download']

        mail_template_id = self.env['mail.template'].browse(wizard_vals['mail_template_id'])
        if wizard:
            attachments_ids = [att['id'] for att in wizard.mail_attachments_widget or [] if not att['placeholder']]
        else:
            attachments_ids = mail_template_id.attachment_ids.ids

        options['unfold_all'] = True

        partner_ids = options.get('partner_ids', [])
        partners = self.env['res.partner'].browse(partner_ids)
        if not recipient_partner_ids:
            recipient_partner_ids = partners.filtered('email').ids

        email_from = mail_template_id._render_field('email_from', partner_ids) if mail_template_id else {}
        downloadable_attachments = self.env['ir.attachment']

        for partner in partners:
            options['partner_ids'] = partner.ids
            report_attachment = partner._get_partner_account_report_attachment(report, options)

            if to_email and recipient_partner_ids:
                if wizard and wizard.mode == 'single':
                    subject = self.mail_subject
                    body = self.mail_body
                else:
                    subject = self._get_mail_field_value(partner, mail_template_id, partner.lang, 'subject')
                    body = self._get_mail_field_value(partner, mail_template_id, partner.lang, 'body_html', options={'post_process': True})

                partner.message_post(
                    body=body,
                    subject=subject,
                    email_from=email_from.get(partner.id),
                    partner_ids=recipient_partner_ids,
                    attachment_ids=attachments_ids + report_attachment.ids,
                    email_add_signature=False,
                )

            if to_download:
                downloadable_attachments += report_attachment

        if downloadable_attachments:
            return self._action_download(downloadable_attachments)

    def action_send_and_print(self, force_synchronous=False):
        """ Create the documents and send them to the end customers.
        If we are sending multiple statements and not downloading them we will process the moves asynchronously.
        :param force_synchronous:   Flag indicating if the method should be done synchronously.
        """
        self.ensure_one()

        if self.mode == 'multi' and self.checkbox_send_mail and not self.mail_template_id:
            raise UserError(_('Please select a mail template to send multiple statements.'))

        force_synchronous = force_synchronous or self.checkbox_download
        process_later = self.mode == 'multi' and not force_synchronous
        if process_later:
            # Set sending information on report
            if self.account_report_id.send_and_print_values:
                raise UserError(_('There are currently reports waiting to be sent, please try again later.'))

            self.account_report_id.send_and_print_values = self._get_wizard_values()

            self.env.ref('account_reports.ir_cron_account_report_send')._trigger()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'title': _('Sending statements'),
                    'message': _('Statements are being sent in the background.'),
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        options = {
            **self.report_options,
            'partner_ids': self.partner_ids.ids,
        }
        return self._process_send_and_print(
            report=self.account_report_id,
            options=options,
            recipient_partner_ids=self.mail_partner_ids.ids,
            wizard=self,
        )
