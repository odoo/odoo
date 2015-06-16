# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp.exceptions import UserError


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
