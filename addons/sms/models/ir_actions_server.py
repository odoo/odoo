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
    ], ondelete={'sms': 'cascade'})
    # SMS
    sms_template_id = fields.Many2one(
        'sms.template', 'SMS Template',
        compute='_compute_sms_template_id',
        ondelete='set null', readonly=False, store=True,
        domain="[('model_id', '=', model_id)]",
    )
    sms_method = fields.Selection(
        selection=[('sms', 'SMS'), ('comment', 'Post as Message'), ('note', 'Post as Note')],
        string='Send as (SMS)',
        compute='_compute_sms_method',
        readonly=False, store=True,
        help='Choose method for SMS sending:\nSMS: mass SMS\nPost as Message: log on document\nPost as Note: mass SMS with archives')

    @api.depends('model_id', 'state')
    def _compute_sms_template_id(self):
        to_reset = self.filtered(
            lambda act: act.state != 'sms' or \
                        (act.model_id != act.sms_template_id.model_id)
        )
        if to_reset:
            to_reset.sms_template_id = False

    @api.depends('state')
    def _compute_sms_method(self):
        to_reset = self.filtered(lambda act: act.state != 'sms')
        if to_reset:
            to_reset.sms_method = False
        other = self - to_reset
        if other:
            other.sms_method = 'sms'

    def _check_model_coherency(self):
        super()._check_model_coherency()
        for action in self:
            if action.state == 'sms' and (action.model_id.transient or not action.model_id.is_mail_thread):
                raise ValidationError(_("Sending SMS can only be done on a mail.thread or a transient model"))

    def _run_action_sms_multi(self, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not self.sms_template_id or self._is_recompute():
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False

        composer = self.env['sms.composer'].with_context(
            default_res_model=records._name,
            default_res_ids=records.ids,
            default_composition_mode='comment' if self.sms_method == 'comment' else 'mass',
            default_template_id=self.sms_template_id.id,
            default_mass_keep_log=self.sms_method == 'note',
        ).create({})
        composer.action_send_sms()
        return False
