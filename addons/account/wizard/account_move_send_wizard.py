import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.addons.mail.tools.parser import parse_res_ids


def _reopen(self, res_id, model, context=None):
    # save original model in context, because selecting the list of available
    # templates requires a model in context
    context = dict(context or {}, default_model=model)
    return {
        'name': _('Compose Email'),
        'type': 'ir.actions.act_window',
        'view_mode': 'form',
        'res_id': res_id,
        'res_model': self._name,
        'target': 'new',
        'context': context,
    }


class AccountMoveSendWizard(models.TransientModel):
    """Wizard that handles the sending a single invoice."""
    _inherit = ['account.move.send', 'mail.composer.mixin']
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
        string="Invoice report",
        domain="[('id', 'in', available_pdf_report_ids)]",
        compute='_compute_pdf_report_id',
        readonly=False,
        store=True,
    )
    available_pdf_report_ids = fields.One2many(
        comodel_name='ir.actions.report',
        compute="_compute_available_pdf_report_ids",
    )

    display_pdf_report_id = fields.Boolean(compute='_compute_display_pdf_report_id')

    # MAIL
    # Template: override mail.composer.mixin field
    template_id = fields.Many2one(
        domain="[('model', '=', 'account.move')]",
        compute='_compute_template_id',
        readonly=False,
        store=True,
    )
    # Language: override mail.composer.mixin field
    lang = fields.Char(compute='_compute_lang', precompute=False)
    mail_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string="To",
        compute='_compute_mail_partners',
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        compute='_compute_mail_attachments_widget',
        store=True,
        readonly=False,
    )

    model = fields.Char('Related Document Model', compute='_compute_model', readonly=False, store=True)
    res_ids = fields.Text('Related Document IDs', compute='_compute_res_ids', readonly=False, store=True)
    template_name = fields.Char('Template Name')

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
                    'sending_methods': wizard.sending_methods or {},
                    'invoice_edi_format': wizard.invoice_edi_format,
                    'extra_edis': wizard.extra_edis or {},
                }
            }
            wizard.alerts = self._get_alerts(wizard.move_id, move_data)

    @api.depends('sending_method_checkboxes')
    def _compute_sending_methods(self):
        for wizard in self:
            wizard.sending_methods = self._get_selected_checkboxes(wizard.sending_method_checkboxes)

    def _inverse_sending_methods(self):
        for wizard in self:
            wizard.sending_method_checkboxes = {method_key: {'checked': True} for method_key in wizard.sending_methods or {}}

    @api.depends('move_id')
    def _compute_sending_method_checkboxes(self):
        """ Select one applicable sending method given the following priority
        1. preferred method set on partner,
        2. email,
        """
        methods = self.env['ir.model.fields'].get_field_selection('res.partner', 'invoice_sending_method')
        for wizard in self:
            preferred_methods = self._get_default_sending_method(wizard.move_id)
            need_fallback = not any([self._is_applicable_to_move(preferred_method, wizard.move_id) for preferred_method in preferred_methods])
            fallback_method = need_fallback and ('email' if self._is_applicable_to_move('email', wizard.move_id) else False)
            wizard.sending_method_checkboxes = {
                method_key: {
                    'checked': method_key in preferred_methods if not need_fallback else method_key == fallback_method,
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
            wizard.extra_edi_checkboxes = {method_key: {'checked': True} for method_key in wizard.extra_edis or {}}

    @api.depends('move_id')
    def _compute_extra_edi_checkboxes(self):
        all_extra_edis = self._get_all_extra_edis()
        for wizard in self:
            wizard.extra_edi_checkboxes = {
                edi_key: {'checked': True, 'label': all_extra_edis[edi_key]['label'], 'help': all_extra_edis[edi_key].get('help')}
                for edi_key in self._get_default_extra_edis(wizard.move_id)
            }

    def _compute_invoice_edi_format(self):
        for wizard in self:
            wizard.invoice_edi_format = self._get_default_invoice_edi_format(wizard.move_id)

    @api.depends('move_id')
    def _compute_pdf_report_id(self):
        for wizard in self:
            wizard.pdf_report_id = self._get_default_pdf_report_id(wizard.move_id)

    @api.depends('move_id')
    def _compute_available_pdf_report_ids(self):
        available_reports = self.env['ir.actions.report'].get_available(self.move_id)

        for wizard in self:
            wizard.available_pdf_report_ids = available_reports

    @api.depends('move_id')
    def _compute_display_pdf_report_id(self):
        # show pdf template menu if there are more than 1 template available and there is at least one move that needs a pdf
        for wizard in self:
            wizard.display_pdf_report_id = len(wizard.available_pdf_report_ids) > 1 and not wizard.move_id.invoice_pdf_report_id

    @api.depends('move_id')
    def _compute_template_id(self):
        for wizard in self:
            wizard.template_id = self._get_default_mail_template_id(wizard.move_id)

    # Overrides of mail.composer.mixin
    @api.depends('template_id')
    def _compute_lang(self):
        for wizard in self:
            wizard.lang = self._get_default_mail_lang(wizard.move_id, wizard.template_id) if wizard.template_id else get_lang(self.env).code

    @api.depends('template_id', 'lang')
    def _compute_mail_partners(self):
        for wizard in self:
            wizard.mail_partner_ids = None

            if wizard.template_id:
                wizard.mail_partner_ids = self._get_default_mail_partner_ids(wizard.move_id, wizard.template_id, wizard.lang)

    # Overrides of mail.composer.mixin
    @api.depends('template_id', 'lang')
    def _compute_subject(self):
        for wizard in self:
            wizard.subject = None

            if wizard.template_id:
                wizard.subject = self._get_default_mail_subject(wizard.move_id, wizard.template_id, wizard.lang)

    # Overrides of mail.composer.mixin
    @api.depends('template_id', 'lang')
    def _compute_body(self):
        for wizard in self:
            wizard.body = None

            if wizard.template_id:
                wizard.body = self._get_default_mail_body(wizard.move_id, wizard.template_id, wizard.lang)

    @api.depends('template_id', 'sending_methods', 'extra_edis')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            manual_attachments_data = [x for x in wizard.mail_attachments_widget or [] if x.get('manual')]
            wizard.mail_attachments_widget = (
                self._get_default_mail_attachments_widget(
                    wizard.move_id,
                    wizard.template_id,
                    extra_edis=wizard.extra_edis or {},
                    pdf_report=wizard.pdf_report_id,
                )
                + manual_attachments_data
            )

    @api.depends('template_id')
    def _compute_res_ids(self):
        for wizard in self.filtered(lambda wizard: not wizard.res_ids):
            context = self.env.context
            active_res_ids = parse_res_ids(context.get('active_ids'), self.env)

            if active_res_ids and len(active_res_ids) <= 500:
                wizard.res_ids = f"{context['active_ids']}"
            elif not active_res_ids and context.get('active_id'):
                wizard.res_ids = f"{[context['active_id']]}"

    @api.depends('template_id')
    def _compute_model(self):
        for wizard in self:
            wizard.model = self.env.context.get('active_model')

    @api.depends('sending_methods')
    def _compute_can_edit_body(self):
        for record in self:
            record.can_edit_body = record.sending_methods and 'email' in record.sending_methods

    # Overrides of mail.composer.mixin
    @api.depends('model')  # Fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'account.move'

    def open_template_creation_wizard(self):
        """ hit save as template button: opens a wizard that prompts for the template's subject.
            `create_mail_template` is called when saving the new wizard. """

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('mail.mail_compose_message_view_form_template_save').id,
            'name': _('Create a Mail Template'),
            'res_model': 'account.move.send.wizard',
            'context': {'dialog_size': 'medium'},
            'target': 'new',
            'res_id': self.id,
        }

    def create_mail_template(self):
        """ creates a mail template with the current mail composer's fields """
        self.ensure_one()
        if not self.model or not self.model in self.env:
            raise UserError(_('Template creation from composer requires a valid model.'))
        model_id = self.env['ir.model']._get_id(self.model)
        values = {
            'name': self.template_name or self.subject,
            'subject': self.subject,
            'body_html': self.body,
            'model_id': model_id,
            'use_default_to': True,
            'user_id': self.env.uid,
        }
        template = self.env['mail.template'].create(values)

        # generate the saved template
        self.write({'template_id': template.id})
        return _reopen(self, self.id, self.model, context={**self.env.context, 'dialog_size': 'large'})

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
            return {}
        return [checkbox_key for checkbox_key, checkbox_vals in json_checkboxes.items() if checkbox_vals['checked']]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_sending_settings(self):
        self.ensure_one()
        send_settings = {
            'sending_methods': self.sending_methods or [],
            'invoice_edi_format': self.invoice_edi_format,
            'extra_edis': self.extra_edis or [],
            'pdf_report': self.pdf_report_id,
            'author_user_id': self.env.user.partner_id.id,
            'author_partner_id': self.env.user.id,
        }
        if self.sending_methods and 'email' in self.sending_methods:
            send_settings.update({
                'mail_template': self.template_id,
                'mail_lang': self.lang,
                'mail_body': self.body,
                'mail_subject': self.subject,
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
            self.move_id.partner_id.with_company(self.company_id).invoice_sending_method = self.sending_methods[0]
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
        if attachments and self.sending_methods and 'manual' in self.sending_methods:
            return self._action_download(attachments)
        else:
            return {'type': 'ir.actions.act_window_close'}
