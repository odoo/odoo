# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ServerActions(models.Model):
    """ Add email option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    @api.model
    def _get_states(self):
        res = super(ServerActions, self)._get_states()
        res.insert(0, ('email', 'Send Email'))
        return res

    email_from = fields.Char('From', related='template_id.email_from', readonly=True)
    email_to = fields.Char('To (Emails)', related='template_id.email_to', readonly=True)
    partner_to = fields.Char('To (Partners)', related='template_id.partner_to', readonly=True)
    subject = fields.Char('Subject', related='template_id.subject', readonly=True)
    body_html = fields.Html('Body', related='template_id.body_html', readonly=True)
    template_id = fields.Many2one(
        'mail.template', 'Email Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )

    @api.onchange('template_id')
    def on_change_template_id(self):
        """ Render the raw template in the server action fields. """
        if self.template_id and not self.template_id.email_from:
            raise UserError(_('Your template should define email_from'))

    @api.model
    def run_action_email(self, action, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not action.template_id or not self._context.get('active_id'):
            return False
        action.template_id.send_mail(self._context.get('active_id'), force_send=False, raise_exception=False)
        return False

    @api.model
    def _get_eval_context(self, action=None):
        """ Override the method giving the evaluation context but also the
        context used in all subsequent calls. Add the mail_notify_force_send
        key set to False in the context. This way all notification emails linked
        to the currently executed action will be set in the queue instead of
        sent directly. This will avoid possible break in transactions. """
        eval_context = super(ServerActions, self)._get_eval_context(action=action)
        # re-dictify, because eval_context['context'] is a frozendict
        ctx = dict(eval_context.get('context', {}))
        ctx['mail_notify_force_send'] = False
        eval_context['context'] = ctx
        return eval_context
