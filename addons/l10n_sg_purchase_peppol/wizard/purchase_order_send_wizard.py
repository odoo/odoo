from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class PurchaseOrderSendWizard(models.TransientModel):
    """Wizard that handles sending a single RFQ / PO, by email and/or by Peppol."""
    _name = 'purchase.order.send.wizard'
    _inherit = ['mail.composer.mixin']
    _description = "Send Purchase Order Wizard"

    order_id = fields.Many2one(comodel_name='purchase.order', required=True)
    company_id = fields.Many2one(comodel_name='res.company', related='order_id.company_id')
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

    # MAIL
    # Template: override mail.composer.mixin field
    template_id = fields.Many2one(domain="[('model', '=', 'purchase.order')]")
    # Language: override mail.composer.mixin field
    lang = fields.Char(compute='_compute_lang', precompute=False, compute_sudo=True)
    mail_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='purchase_order_send_wizard_res_partner_rel',
        string="To",
        compute='_compute_mail_partners',
        store=True,
        readonly=False,
    )
    mail_partner_cc_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='purchase_order_send_wizard_res_partner_cc_rel',
        string="Cc",
        compute='_compute_mail_partners',
        store=True,
        readonly=False,
    )
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Attachments",
        compute='_compute_attachment_ids',
        store=True,
        readonly=False,
    )
    model = fields.Char(default='purchase.order')  # needed for the `mail_composer_template_selector` widget

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_sending_methods(self):
        return {
            'email': self.env._("by Email"),
            'peppol': self.env._("by InvoiceNow (Peppol)"),
        }

    @api.model
    def _is_applicable_to_company(self, method, company):
        if method == 'peppol':
            return bool(company.peppol_can_send or company._get_active_peppol_parent_company())
        return True

    @api.model
    def _is_applicable_to_order(self, method, order):
        if method == 'peppol':
            return (
                self._is_applicable_to_company(method, order.company_id)
                and order.l10n_sg_peppol_can_send_order
                and order._l10n_sg_peppol_vendor_can_receive_order()
            )
        return True

    @api.model
    def _get_default_sending_methods(self, order):
        """ Peppol when the vendor can receive it, email otherwise. """
        return ['peppol'] if self._is_applicable_to_order('peppol', order) else ['email']

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        if not self.order_id.l10n_sg_peppol_can_send_order:
            return self.env._(" (Previously sent)")
        vendor = self.order_id._l10n_sg_peppol_get_vendor()
        if not vendor.routing_identifier:
            return self.env._(" (Missing InvoiceNow (Peppol) ID)")
        if not self.order_id._l10n_sg_peppol_vendor_can_receive_order():
            if vendor.peppol_verification_state == 'not_valid':
                return self.env._(" (Vendor not on InvoiceNow (Peppol))")
            return self.env._(" (Vendor cannot receive orders)")
        return ''

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields):
        # EXTENDS 'base'
        results = super().default_get(fields)
        if 'order_id' in fields and 'order_id' not in results:
            results['order_id'] = self.env.context.get('active_ids', [])[0]
        return results

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('sending_methods', 'mail_partner_ids', 'mail_partner_cc_ids')
    def _compute_alerts(self):
        for wizard in self:
            wizard.alerts = wizard._get_alerts()

    @api.depends('sending_method_checkboxes')
    def _compute_sending_methods(self):
        for wizard in self:
            wizard.sending_methods = self._get_selected_checkboxes(wizard.sending_method_checkboxes)

    def _inverse_sending_methods(self):
        for wizard in self:
            wizard.sending_method_checkboxes = {method_key: {'checked': True} for method_key in wizard.sending_methods or {}}

    @api.depends('order_id')
    def _compute_sending_method_checkboxes(self):
        for wizard in self:
            preferred_methods = self._get_default_sending_methods(wizard.order_id)
            checkboxes = {
                method_key: {
                    'checked': method_key in preferred_methods,
                    'label': method_label,
                }
                for method_key, method_label in self._get_sending_methods().items()
                if self._is_applicable_to_company(method_key, wizard.company_id)
            }
            if peppol_checkbox := checkboxes.get('peppol'):
                if addendum_disable_reason := wizard._get_peppol_checkbox_addendum_disable_reason():
                    peppol_checkbox.update({'readonly': True, 'checked': False})
                peppol_checkbox['label'] += addendum_disable_reason + wizard._get_peppol_checkbox_addendum_mode()
            wizard.sending_method_checkboxes = checkboxes

    def _get_peppol_checkbox_addendum_mode(self):
        self.ensure_one()
        company = self.company_id._get_active_peppol_parent_company() or self.company_id
        peppol_proxy_mode = company._get_peppol_edi_mode()
        if peppol_proxy_mode == 'test':
            return self.env._(" (Test)")
        if peppol_proxy_mode == 'demo':
            return self.env._(" (Demo)")
        return ''

    @api.depends('template_id')
    def _compute_lang(self):
        # OVERRIDE 'mail.composer.mixin'
        for wizard in self:
            if wizard.template_id:
                wizard.lang = wizard.template_id._render_lang(wizard.order_id.ids)[wizard.order_id.id]
            else:
                wizard.lang = get_lang(self.env).code

    @api.depends('template_id', 'lang')
    def _compute_subject(self):
        # OVERRIDE 'mail.composer.mixin'
        for wizard in self:
            wizard.subject = wizard._render_from_template('subject')

    @api.depends('template_id', 'lang')
    def _compute_body(self):
        # OVERRIDE 'mail.composer.mixin'
        for wizard in self:
            wizard.body = wizard._render_from_template('body_html')

    @api.depends('template_id', 'lang')
    def _compute_mail_partners(self):
        """ Similar to mail.compose.message in monorecord comment mode. """
        for wizard in self:
            if not wizard.template_id:
                wizard.mail_partner_ids = wizard.mail_partner_cc_ids = False
                continue
            rendered_values = wizard.template_id._generate_template(
                wizard.order_id.ids,
                {'email_cc', 'email_to', 'partner_to', 'partner_cc'},
                recipients_allow_suggested=True,
                find_or_create_partners=True,
            )[wizard.order_id.id]
            wizard.mail_partner_ids = rendered_values.get('partner_ids') or False
            wizard.mail_partner_cc_ids = rendered_values.get('partner_cc_ids') or False

    @api.depends('template_id')
    def _compute_attachment_ids(self):
        """ Similar to mail.compose.message in monorecord comment mode: attachments of the template and
        reports coming from report_template_ids, rendered on the order. """
        for wizard in self:
            if not wizard.template_id:
                wizard.attachment_ids = False
                continue
            rendered_values = wizard.template_id._generate_template(
                wizard.order_id.ids,
                {'attachment_ids', 'report_template_ids'},
            )[wizard.order_id.id]
            attachment_ids = rendered_values.get('attachment_ids') or []
            # Not attached to the order yet, this will be done when posting the message.
            if rendered_values.get('attachments'):
                attachment_ids += self.env['ir.attachment'].create([
                    {
                        'name': attach_fname,
                        'raw': attach_raw,
                        'res_model': 'mail.compose.message',
                        'res_id': 0,
                        'type': 'binary',
                    }
                    for attach_fname, attach_raw in rendered_values['attachments']
                ]).ids
            wizard.attachment_ids = attachment_ids

    @api.depends('sending_methods')
    def _compute_can_edit_body(self):
        # OVERRIDE 'mail.composer.mixin'
        for wizard in self:
            wizard.can_edit_body = bool(wizard.sending_methods and 'email' in wizard.sending_methods)

    @api.depends('model')  # Fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        # OVERRIDE 'mail.composer.mixin'
        self.render_model = 'purchase.order'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_selected_checkboxes(self, json_checkboxes):
        if not json_checkboxes:
            return []
        return [checkbox_key for checkbox_key, checkbox_vals in json_checkboxes.items() if checkbox_vals['checked']]

    def _render_from_template(self, field):
        self.ensure_one()
        if not self.template_id:
            return False
        return self.template_id.sudo().with_context(lang=self.lang)._render_field(
            field, self.order_id.ids,
        )[self.order_id.id]

    def _get_alerts(self):
        self.ensure_one()
        sending_methods = self.sending_methods or []
        alerts = {}
        if not sending_methods:
            alerts['l10n_sg_purchase_peppol_no_sending_method'] = {
                'level': 'danger',
                'message': self.env._("Select at least one sending method."),
            }
        if 'email' in sending_methods:
            partners_without_email = (self.mail_partner_ids | self.mail_partner_cc_ids).filtered(lambda p: not p.email)
            if not self.mail_partner_ids or partners_without_email:
                alerts['l10n_sg_purchase_peppol_missing_email'] = {
                    'level': 'danger',
                    'message': self.env._("Please add a recipient with an email address.")
                    if not self.mail_partner_ids
                    else self.env._(
                        "The following recipients have no email address: %(partners)s",
                        partners=', '.join(partners_without_email.mapped('display_name')),
                    ),
                }
        if 'peppol' in (self.sending_method_checkboxes or {}) and self.order_id.l10n_sg_peppol_can_send_order:
            vendor = self.order_id._l10n_sg_peppol_get_vendor()
            vendor_action = {
                'action_text': self.env._("View Vendor"),
                'action': vendor._get_records_action(name=self.env._("Vendor")),
            }
            if not vendor.routing_identifier:
                alerts['l10n_sg_purchase_peppol_vendor_missing_peppol_id'] = {
                    'level': 'info',
                    'message': self.env._(
                        "Set a Peppol EAS and Endpoint on %(vendor)s to send this order via InvoiceNow (Peppol).",
                        vendor=vendor.display_name,
                    ),
                    **vendor_action,
                }
            elif (
                vendor.peppol_verification_state in ('valid', 'not_valid_format')
                and not self.order_id._l10n_sg_peppol_vendor_can_receive_order()
            ):
                alerts['l10n_sg_purchase_peppol_vendor_cannot_receive_order'] = {
                    'level': 'warning',
                    'message': self.env._(
                        "%(vendor)s is on InvoiceNow (Peppol) but did not enable receiving orders.",
                        vendor=vendor.display_name,
                    ),
                    **vendor_action,
                }
        return alerts

    def _send_mail(self):
        """ Post the message on the order, as mail.compose.message does in monorecord comment mode. """
        self.ensure_one()
        order = self.order_id
        # Files uploaded in the wizard are linked to it; link them to the order like the composer ones.
        self.attachment_ids.filtered(lambda a: a.res_model == self._name).sudo().write({
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })
        template = self.template_id
        order.with_context(
            mark_rfq_as_sent=True,
            email_notification_allow_footer=True,
        ).message_post(
            body=self.body or '',
            subject=self.subject or '',
            partner_ids=self.mail_partner_ids.ids,
            partner_cc_ids=self.mail_partner_cc_ids.ids,
            attachment_ids=self.attachment_ids.ids,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid=template.email_layout_xmlid,
            email_add_signature=not template,
            force_footer=template.email_layout_force_footer,
            force_header=template.email_layout_force_header,
            force_email_lang=self.lang,
            mail_auto_delete=template.auto_delete,
            mail_server_id=template.mail_server_id.id,
            model_description=self.env.context.get('model_description'),
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_send(self):
        self.ensure_one()
        if danger_messages := [alert['message'] for alert in (self.alerts or {}).values() if alert.get('level') == 'danger']:
            raise UserError('\n'.join(danger_messages))
        sending_methods = self.sending_methods or []
        # Peppol first: if the Access Point refuses the document, nothing is sent by email either.
        if 'peppol' in sending_methods:
            if not self._is_applicable_to_order('peppol', self.order_id):
                raise UserError(self.env._("This order cannot be sent via InvoiceNow (Peppol)."))
            self.order_id._l10n_sg_peppol_send_order(raise_on_error=True)
        if 'email' in sending_methods:
            self._send_mail()
        return {'type': 'ir.actions.act_window_close'}
