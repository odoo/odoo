from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import get_lang


class AccountMoveSendWizard(models.TransientModel):
    """Wizard that handles the sending a single invoice."""
    _name = 'account.move.send.wizard'
    _inherit = ['account.move.send']
    _description = "Account Move Send Wizard"

    move_id = fields.Many2one(comodel_name='account.move', required=True)
    company_id = fields.Many2one(comodel_name='res.company', related='move_id.company_id')
    alerts = fields.Json(compute='_compute_alerts')
    sending_method = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['invoice_sending_method'].selection,
        string='Send',
        precompute=True,
        compute='_compute_sending_method',
        required=True,
        readonly=False,
        store=True,
    )
    available_methods = fields.Json(compute='_compute_available_methods')
    invoice_edi_format = fields.Selection(  # to override
        selection=lambda self: self.env['res.partner']._fields['invoice_edi_format'].selection,
        string='E-Invoice format',
        compute='_compute_invoice_edi_format',
        readonly=False,
        store=True,
    )
    display_invoice_edi_format = fields.Boolean(compute='_compute_display_invoice_edi_format')
    extra_edi_checkboxes = fields.Json(
        compute='_compute_extra_edi_checkboxes',
        readonly=False,
        store=True,
    )
    pdf_report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string="Invoice template",
        domain="[('is_invoice_report', '=', True)]",
        compute='_compute_pdf_report_id',
        readonly=False,
        store=True,
    )
    display_pdf_report_id = fields.Boolean(compute='_compute_display_pdf_report_id')
    mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Email template",
        domain="[('model', '=', 'account.move')]",
        compute='_compute_mail_template_id',
        readonly=False,
        store=True,
    )
    mail_lang = fields.Char(compute='_compute_mail_lang')
    mail_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Recipients",
        compute='_compute_mail_subject_body_partners',
        store=True,
        readonly=False,
    )
    mail_subject = fields.Char(
        string="Subject",
        compute='_compute_mail_subject_body_partners',
        store=True,
        readonly=False,
    )
    mail_body = fields.Html(
        string="Contents",
        sanitize_style=True,
        compute='_compute_mail_subject_body_partners',
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        compute='_compute_mail_attachments_widget',
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)
        if 'move_id' in fields_list and 'move_id' not in results:
            move_id = self._context.get('active_ids', [])[0]
            results['move_id'] = move_id
        return results

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id', 'sending_method', 'invoice_edi_format', 'extra_edi_checkboxes')
    def _compute_alerts(self):
        for wizard in self:
            extra_edi = self._get_checked_extra_edi(wizard.extra_edi_checkboxes)
            move_data = {wizard.move_id: {'sending_method': wizard.sending_method, 'invoice_edi_format': wizard.invoice_edi_format, 'extra_edi': extra_edi}}
            wizard.alerts = self._get_alerts(wizard.move_id, move_data)

    @api.depends('move_id')
    def _compute_sending_method(self):
        """ Finds the first applicable sending method given the following priority:
        1. preferred method set on partner,
        2. email,
        3. manual.
        """
        for wizard in self:
            preferred_method = wizard.move_id.partner_id.with_company(wizard.company_id).invoice_sending_method
            if self._is_applicable_to_move(preferred_method, wizard.move_id):
                wizard.sending_method = preferred_method
            elif self._is_applicable_to_move('email', wizard.move_id):
                wizard.sending_method = 'email'
            else:
                wizard.sending_method = 'manual'

    @api.depends('move_id')
    def _compute_available_methods(self):
        all_methods = list(dict(self.env['res.partner']._fields['invoice_sending_method'].selection))
        for wizard in self:
            wizard.available_methods = [method for method in all_methods if self._is_applicable_to_company(method, wizard.company_id)]

    @api.depends('move_id')
    def _compute_invoice_edi_format(self):
        for wizard in self:
            wizard.invoice_edi_format = self._get_default_invoice_edi_format(wizard.move_id)

    @api.depends('move_id')
    def _compute_display_invoice_edi_format(self):
        for wizard in self:
            # not a related because it will be extended in other modules
            wizard.display_invoice_edi_format = wizard.move_id.partner_id.display_invoice_edi_format

    @api.depends('move_id')
    def _compute_extra_edi_checkboxes(self):
        for wizard in self:
            wizard.extra_edi_checkboxes = self._get_default_extra_edi_checkboxes(wizard.move_id)

    @api.depends('move_id')
    def _compute_pdf_report_id(self):
        for wizard in self:
            wizard.pdf_report_id = self._get_default_pdf_report_id(wizard.move_id)

    @api.depends('move_id')
    def _compute_display_pdf_report_id(self):
        # show pdf template menu if there are more than 1 template available and there is at least one move that needs a pdf
        available_templates_count = self.env['ir.actions.report'].search_count([('is_invoice_report', '=', True)], limit=2)
        for wizard in self:
            wizard.display_pdf_report_id = available_templates_count > 1 and not wizard.move_id.invoice_pdf_report_id

    @api.depends('move_id')
    def _compute_mail_template_id(self):
        for wizard in self:
            wizard.mail_template_id = self._get_default_mail_template_id(wizard.move_id)

    @api.depends('mail_template_id')
    def _compute_mail_lang(self):
        for wizard in self:
            wizard.mail_lang = self._get_default_mail_lang(wizard.move_id, wizard.mail_template_id) if wizard.mail_template_id else get_lang(self.env).code

    @api.depends('mail_template_id', 'mail_lang')
    def _compute_mail_subject_body_partners(self):
        for wizard in self:
            if wizard.mail_template_id:
                wizard.mail_subject = self._get_default_mail_subject(wizard.move_id, wizard.mail_template_id, wizard.mail_lang)
                wizard.mail_body = self._get_default_mail_body(wizard.move_id, wizard.mail_template_id, wizard.mail_lang)
            else:
                wizard.mail_subject = wizard.mail_body = None
            wizard.mail_partner_ids = self._get_default_mail_partner_ids(wizard.move_id, wizard.mail_template_id, wizard.mail_lang) if wizard.mail_template_id else None

    @api.depends('mail_template_id', 'sending_method', 'invoice_edi_format', 'extra_edi_checkboxes')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            manual_attachments_data = [x for x in wizard.mail_attachments_widget or [] if x.get('manual')]
            extra_edi = self._get_checked_extra_edi(wizard.extra_edi_checkboxes)
            wizard.mail_attachments_widget = (
                    self._get_default_mail_attachments_widget(wizard.move_id, wizard.mail_template_id, invoice_edi_format=wizard.invoice_edi_format, extra_edi=extra_edi)
                    + manual_attachments_data
            )

    # -------------------------------------------------------------------------
    # CONSTRAINS
    # -------------------------------------------------------------------------

    @api.constrains('sending_method')
    def _check_sending_method_available(self):
        for wizard in self:
            if wizard.sending_method not in wizard.available_methods:
                raise ValidationError(_(
                    "The sending method %(sending_method)s is not available.",
                    sending_method=wizard.sending_method,
                ))

    @api.constrains('move_id')
    def _check_move_id_constrains(self):
        for wizard in self:
            self._check_move_constrains(wizard.move_id)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_sending_settings(self):
        self.ensure_one()
        send_settings = {
            'sending_method': self.sending_method,
            'invoice_edi_format': self.invoice_edi_format,
            'extra_edi': self._get_checked_extra_edi(self.extra_edi_checkboxes),
            'pdf_report': self.pdf_report_id,
            'author_user_id': self.env.user.partner_id.id,
            'author_partner_id': self.env.user.id,
        }
        if self.sending_method == 'email':
            send_settings.update({
                'mail_template': self.mail_template_id,
                'mail_lang': self.mail_lang,
                'mail_body': self.mail_body,
                'mail_subject': self.mail_subject,
                'mail_partner_ids': self.mail_partner_ids.ids,
                'mail_attachments_widget': self.mail_attachments_widget,
            })
        return send_settings

    def _update_preferred_settings(self):
        """If the partner's settings are not set, we use them as partner's default."""
        self.ensure_one()
        if not self.move_id.partner_id.with_company(self.company_id).invoice_sending_method:
            self.move_id.partner_id.with_company(self.company_id).invoice_sending_method = self.sending_method
        if not self.move_id.partner_id.with_company(self.company_id).invoice_edi_format:
            self.move_id.partner_id.with_company(self.company_id).invoice_edi_format = self.invoice_edi_format
        if not self.move_id.partner_id.invoice_template_pdf_report_id and self.pdf_report_id != self._get_default_pdf_report_id(self.move_id):
            self.move_id.partner_id.invoice_template_pdf_report_id = self.pdf_report_id

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _action_download(self, attachments):
        """ Download the PDF attachment, or a zip of attachments if there are more than one. """
        return {
            'type': 'ir.actions.act_url',
            'url': f'/account/download_invoice_attachments/{",".join(map(str, attachments.ids))}',
            'close': True,
        }

    def action_send_and_print(self, allow_fallback_pdf=False):
        """ Create invoice documents and send them."""
        self.ensure_one()
        if self.alerts:
            self._raise_danger_alerts(self.alerts)
        self._update_preferred_settings()
        attachments = self._generate_and_send_invoices(
            self.move_id,
            **self._get_sending_settings(),
            allow_fallback_pdf=allow_fallback_pdf,
        )
        if attachments and self.sending_method == 'manual':
            return self._action_download(attachments)
        else:
            return {'type': 'ir.actions.act_window_close'}
