# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.mail.wizard.mail_compose_message import _reopen


class AccountInvoiceSend(models.TransientModel):
    _name = 'account.invoice.send'
    _inherits = {'mail.compose.message':'composer_id'}
    _description = 'Account Invoice Send'

    is_email = fields.Boolean('Email', default=lambda self: self.env.user.company_id.invoice_is_email)
    invoice_without_email = fields.Text(compute='_compute_invoice_without_email', string='invoice(s) that will not be sent')
    is_print = fields.Boolean('Print', default=lambda self: self.env.user.company_id.invoice_is_print)
    printed = fields.Boolean('Is Printed', default=False)
    invoice_ids = fields.Many2many('account.invoice', 'account_invoice_account_invoice_send_rel', string='Invoices')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'account.invoice')]"
        )

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceSend, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'comment' if len(res_ids) == 1 else 'mass_mail',
        })
        res.update({
            'invoice_ids': res_ids,
            'composer_id': composer.id,
        })
        return res

    @api.multi
    @api.onchange('invoice_ids')
    def _compute_composition_mode(self):
        for wizard in self:
            wizard.composition_mode = 'comment' if len(wizard.invoice_ids) == 1  else 'mass_mail'

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.composer_id:
            self.composer_id.template_id = self.template_id.id
            self.composer_id.onchange_template_id_wrapper()

    @api.onchange('is_email')
    def _compute_invoice_without_email(self):
        for wizard in self:
            if wizard.is_email and len(wizard.invoice_ids) > 1:
                invoices = self.env['account.invoice'].search([
                    ('id', 'in', self.env.context.get('active_ids')),
                    ('partner_id.email', '=', False)
                ])
                if invoices:
                    wizard.invoice_without_email = "%s\n%s" % (
                        _("The following invoice(s) will not be sent by email, because the customers don't have email address."),
                        "\n".join([i.reference for i in invoices])
                        )
                else:
                    wizard.invoice_without_email = False

    @api.multi
    def _send_email(self):
        if self.is_email:
            self.composer_id.send_mail()
            if self.env.context.get('mark_invoice_as_sent'):
                self.mapped('invoice_ids').write({'sent': True})

    @api.multi
    def _print_document(self):
        """ to override for each type of models that will use this composer."""
        self.ensure_one()
        action = self.invoice_ids.invoice_print()
        action.update({'close_on_report_download': True})
        return action

    @api.multi
    def send_and_print_action(self):
        self.ensure_one()
        # Send the mails in the correct language by splitting the ids per lang.
        # This should ideally be fixed in mail_compose_message, so when a fix is made there this whole commit should be reverted.
        # basically self.body (which could be manually edited) extracts self.template_id,
        # which is then not translated for each customer.
        if self.composition_mode == 'mass_mail' and self.template_id:
            active_ids = self.env.context.get('active_ids', self.res_id)
            active_records = self.env[self.model].browse(active_ids)
            langs = active_records.mapped('partner_id.lang')
            default_lang = self.env.context.get('lang', 'en_US')
            for lang in (set(langs) or [default_lang]):
                active_ids_lang = active_records.filtered(lambda r: r.partner_id.lang == lang).ids
                self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
                self_lang.onchange_template_id()
                self_lang._send_email()
        else:
            self._send_email()
        if self.is_print:
            return self._print_document()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def save_as_template(self):
        self.ensure_one()
        self.composer_id.save_as_template()
        self.template_id = self.composer_id.template_id.id
        action = _reopen(self, self.id, self.model, context=self._context)
        action.update({'name': _('Send Invoice')})
        return action
