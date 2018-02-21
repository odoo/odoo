# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ServerActions(models.Model):
    """ Add email option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[
        ('email', 'Send Email'),
        ('followers', 'Add Followers')
    ])
    # Followers
    partner_ids = fields.Many2many('res.partner', string='Add Followers')
    channel_ids = fields.Many2many('mail.channel', string='Add Channels')
    # Template
    template_id = fields.Many2one(
        'mail.template', 'Email Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )

    @api.onchange('template_id')
    def on_change_template_id(self):
        """ Render the raw template in the server action fields. """
        if self.template_id and not self.template_id.email_from:
            raise UserError(_('Your template should define email_from'))

    @api.constrains('state', 'model_id')
    def _check_mail_thread(self):
        for action in self:
            if action.state == 'followers' and not action.model_id.is_mail_thread:
                raise ValidationError(_("Add Followers can only be done on a mail thread model"))

    @api.model
    def run_action_followers_multi(self, action, eval_context=None):
        Model = self.env[action.model_id.model]
        if self.partner_ids or self.channel_ids and hasattr(Model, 'message_subscribe'):
            records = Model.browse(self._context.get('active_ids', self._context.get('active_id')))
            records.message_subscribe(self.partner_ids.ids, self.channel_ids.ids, force=False)
        return False

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
        ctx = dict(eval_context['env'].context)
        ctx['mail_notify_force_send'] = False
        eval_context['env'].context = ctx
        return eval_context
