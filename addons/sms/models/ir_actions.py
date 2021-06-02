# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ServerActions(models.Model):
    """ Add SMS option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[
        ('sms', 'Send SMS Text Message'),
    ])
    # SMS
    sms_template_id = fields.Many2one(
        'sms.template', 'SMS Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )
    sms_mass_keep_log = fields.Boolean('Log a note', default=True)

    @api.constrains('state', 'model_id')
    def _check_sms_capability(self):
        for action in self:
            if action.state == 'sms' and not action.model_id.is_mail_thread:
                raise ValidationError(_("Sending SMS can only be done on a mail.thread model"))

    @api.model
    def run_action_sms_multi(self, action, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not action.sms_template_id or self._is_recompute(action):
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False

        composer = self.env['sms.composer'].with_context(
            default_res_model=records._name,
            default_res_ids=records.ids,
            default_composition_mode='mass',
            default_template_id=action.sms_template_id.id,
            default_mass_keep_log=action.sms_mass_keep_log,
        ).create({})
        composer.action_send_sms()
        return False
