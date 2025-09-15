from odoo import api, fields, models
from odoo.tools.misc import get_lang


class AccountMoveSendWizard(models.TransientModel):
    """Wizard that handles the sending a single invoice."""
    _name = 'account.move.send.wizard'
    _inherit = ['account.move.send']
    _description = "Account Move Send Wizard"

    move_id = fields.Many2one(comodel_name='account.move', required=True)
    company_id = fields.Many2one(comodel_name='res.company', related='move_id.company_id')
    alerts = fields.Json(compute='_compute_alerts')
    sending_methods = fields.Json(
        compute='_compute_sending_methods',
        inverse='_inverse_sending_methods',
    )
    sending_method_checkboxes = fields.Json(
        compute='_compute_sending_method_checkboxes',
        precompute=True,
        readonly=False,
        store=True,
    )
    extra_edis = fields.Json(
        compute='_compute_extra_edis',
        inverse='_inverse_extra_edis',
    )
    extra_edi_checkboxes = fields.Json(
        compute='_compute_extra_edi_checkboxes',
        precompute=True,
        readonly=False,
        store=True,
    )
    invoice_edi_format = fields.Selection(
        selection=lambda self: self.env['res.partner']._fields['invoice_edi_format'].selection,
        compute='_compute_invoice_edi_format',
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
    is_download_only = fields.Boolean(compute='_compute_is_download_only')

    # MAIL
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
        string="To",
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

    @api.depends('sending_methods', 'extra_edis')
    def _compute_alerts(self):
        for wizard in self:
            move_data = {
                wizard.move_id: {
                    'sending_methods': set(wizard.sending_methods or []) or {},
                    'invoice_edi_format': wizard.invoice_edi_format,
                    'extra_edis': set(wizard.extra_edis or []) or {},
                }
            }
            wizard.alerts = self._get_alerts(wizard.move_id, move_data)

    @api.depends('sending_method_checkboxes')
    def _compute_sending_methods(self):
        for wizard in self:
            wizard.sending_methods = self._get_selected_checkboxes(wizard.sending_method_checkboxes)

    def _inverse_sending_methods(self):
        for wizard in self:
            wizard.sending_method_checkboxes = {method_key: {'checked': True} for method_key in wizard.sending_methods or []}

    @api.depends('move_id')
    def _compute_sending_method_checkboxes(self):
        """ Select one applicable sending method given the following priority
        1. preferred method set on partner,
        2. email,
        3. manual.
        """
        methods = self.env['ir.model.fields'].get_field_selection('res.partner', 'invoice_sending_method')
        for wizard in self:
            preferred_method = self._get_default_sending_method(wizard.move_id)
            need_fallback = not self._is_applicable_to_move(preferred_method, wizard.move_id, **self._get_sending_settings())
            fallback_method = need_fallback and 'email'
            wizard.sending_method_checkboxes = {
                method_key: {
                    'checked': method_key == preferred_method if not need_fallback else method_key == fallback_method,
                    'label': method_label,
                }
                for method_key, method_label in methods if self._is_applicable_to_company(method_key, wizard.company_id)
            }

    @api.depends('extra_edi_checkboxes')
    def _compute_extra_edis(self):
        for wizard in self:
            wizard.extra_edis = self._get_selected_checkboxes(wizard.extra_edi_checkboxes)

    def _inverse_extra_edis(self):
        for wizard in self:
            wizard.extra_edi_checkboxes = {method_key: {'checked': True} for method_key in wizard.extra_edis or []}

    @api.depends('move_id')
    def _compute_extra_edi_checkboxes(self):
        all_extra_edis = self._get_all_extra_edis()
        for wizard in self:
            wizard.extra_edi_checkboxes = {
                edi_key: {'checked': True, 'label': all_extra_edis[edi_key]['label'], 'help': all_extra_edis[edi_key].get('help')}
                for edi_key in self._get_default_extra_edis(wizard.move_id)
            }

    @api.depends('move_id', 'sending_methods')
    def _compute_invoice_edi_format(self):
        for wizard in self:
            wizard.invoice_edi_format = self._get_default_invoice_edi_format(wizard.move_id, sending_methods=set(wizard.sending_methods or []) or {})

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

    @api.depends('sending_methods')
    def _compute_is_download_only(self):
        for wizard in self:
            wizard.is_download_only = wizard.sending_methods == ['manual']

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
                wizard.mail_partner_ids = self._get_default_mail_partner_ids(wizard.move_id, wizard.mail_template_id, wizard.mail_lang)
            else:
                wizard.mail_subject = wizard.mail_body = None
                wizard.mail_partner_ids = commercial_partner if (commercial_partner := wizard.move_id.commercial_partner_id).email else None

    @api.depends('mail_template_id', 'sending_methods', 'invoice_edi_format', 'extra_edis')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            manual_attachments_data = [x for x in wizard.mail_attachments_widget or [] if x.get('manual')]
            wizard.mail_attachments_widget = (
                self._get_default_mail_attachments_widget(
                    wizard.move_id,
                    wizard.mail_template_id,
                    invoice_edi_format=wizard.invoice_edi_format,
                    extra_edis=set(wizard.extra_edis or []) or {},
                    pdf_report=wizard.pdf_report_id,
                )
                + manual_attachments_data
            )

    # -------------------------------------------------------------------------
    # CONSTRAINS
    # -------------------------------------------------------------------------

    @api.constrains('move_id')
    def _check_move_id_constrains(self):
        for wizard in self:
            self._check_move_constrains(wizard.move_id)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_selected_checkboxes(self, json_checkboxes):
        if not json_checkboxes:
            return []
        return [checkbox_key for checkbox_key, checkbox_vals in json_checkboxes.items() if checkbox_vals['checked']]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_sending_settings(self):
        self.ensure_one()
        send_settings = {
            'sending_methods': set(self.sending_methods or []) or {},
            'invoice_edi_format': self.invoice_edi_format,
            'extra_edis': set(self.extra_edis or []) or {},
            'pdf_report': self.pdf_report_id,
            'author_user_id': self.env.user.id,
            'author_partner_id': self.env.user.partner_id.id,
        }
        if self.sending_methods and 'email' in self.sending_methods:
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
        if (
            self.sending_methods
            and len(self.sending_methods) == 1
            and not self.move_id.partner_id.with_company(self.company_id).invoice_sending_method
        ):
            self.move_id.partner_id.with_company(self.company_id).sudo().invoice_sending_method = self.sending_methods[0]
        if not self.move_id.partner_id.invoice_template_pdf_report_id and self.pdf_report_id != self._get_default_pdf_report_id(self.move_id):
            self.move_id.partner_id.sudo().invoice_template_pdf_report_id = self.pdf_report_id

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
        if attachments and self.sending_methods and 'manual' in self.sending_methods:
            return self._action_download(attachments)
        else:
            return {'type': 'ir.actions.act_window_close'}
