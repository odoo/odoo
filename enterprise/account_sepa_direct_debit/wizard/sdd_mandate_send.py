from odoo import _, api, fields, models


class SDDMandateSend(models.TransientModel):
    _inherit = 'mail.composer.mixin'
    _name = 'sdd.mandate.send'
    _description = "SDD Mandate Send"

    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id', store=True)
    mandate_id = fields.Many2one(comodel_name='sdd.mandate', readonly=True)
    partner_id = fields.Many2one(related='mandate_id.partner_id', readonly=True)

    # == PRINT ==
    checkbox_download = fields.Boolean(
        string="Download",
        default=False,
    )

    # == MAIL ==
    checkbox_send_mail = fields.Boolean(
        string="Email",
        default=True,
    )
    warnings = fields.Json(compute='_compute_warnings')
    template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Email template",
        domain="[('model', '=', 'sdd.mandate.send')]",
    )
    author_id = fields.Many2one(
        comodel_name='res.partner',
        string="Author",
        index=True,
        ondelete='set null',
        default=lambda self: self.env.user.partner_id,
    )
    recipient_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('mandate_id')
    def _compute_recipient_ids(self):
        for wizard in self:
            wizard.recipient_ids = wizard.partner_id | wizard.mandate_id.message_partner_ids - wizard.author_id

    @api.depends('mandate_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.mandate_id.company_id.id

    @api.depends('mandate_id', 'checkbox_send_mail')
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}
            partners_without_mail = wizard.mandate_id.filtered(lambda x: not x.partner_id.email).partner_id
            if wizard.checkbox_send_mail and partners_without_mail:
                warnings['account_missing_email'] = {
                    'message': _("Partner should have an email address."),
                    'action_text': _("View Partner(s)"),
                    'action': partners_without_mail._get_records_action(name=_("Check Partner(s) Email(s)"))
                }

            wizard.warnings = warnings

    @api.depends('mandate_id', 'template_id')
    def _compute_subject(self):
        # OVERRIDES mail
        for wizard in self.filtered('template_id'):
            wizard.subject = wizard.template_id._render_field(
                'subject',
                [wizard.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.id]

    @api.depends('mandate_id', 'template_id')
    def _compute_body(self):
        # OVERRIDES mail
        for wizard in self.filtered('template_id'):
            wizard.body = wizard.template_id._render_field(
                'body_html',
                [wizard.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.id]

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _prepare_mandate_pdf(self):
        self.ensure_one()
        mandate = self.mandate_id
        pdf_report = self.env.ref('account_sepa_direct_debit.sdd_mandate_form_report_main')
        content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
            pdf_report.report_name,
            res_ids=mandate.ids,
        )
        return {
            'name': f"{self.partner_id.name.replace(' ', '_')}_sdd_mandate_form_{mandate.name}.pdf",
            'raw': content,
            'mimetype': 'application/pdf',
            'res_model': 'sdd.mandate',
            'res_id': mandate.id,
            'res_field': 'mandate_pdf_file',  # Binary field
            }

    def _send_mail(self, mandate_pdf):
        self.ensure_one()
        self.mandate_id.message_post(
            author_id=(self.env.company.partner_id or self.author_id).id,
            body=self.body,
            message_type='comment',
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
            attachment_ids=mandate_pdf.ids,
        )

    def action_send_and_print(self):
        self.ensure_one()
        mandate = self.mandate_id
        mandate.is_sent = True

        # Generate mandate document.
        pdf_data = self._prepare_mandate_pdf()

        # note: Binary is used for security reason
        attachment = self.env['ir.attachment'].create(pdf_data)
        attachment.register_as_main_attachment(force=True)

        # Send mail
        if self.checkbox_send_mail:
            self._send_mail(attachment)

        # Download PDF
        if self.checkbox_download:
            return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
            'close': True,
        }

        return {'type': 'ir.actions.act_window_close'}
