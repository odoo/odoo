# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class IrActionsServer(models.Model):
    """ Add SMS option in server actions. """
    _inherit = 'ir.actions.server'

    state = fields.Selection(selection_add=[
        ('sms', 'Send SMS'), ('followers',),
    ], ondelete={'sms': 'cascade'})
    # SMS
    sms_template_id = fields.Many2one(
        'sms.template', 'SMS Template',
        compute='_compute_sms_template_id',
        ondelete='set null', readonly=False, store=True,
        domain="[('model_id', '=', model_id)]",
    )
    sms_method = fields.Selection(
        selection=[('sms', 'SMS (without note)'), ('comment', 'SMS (with note)'), ('note', 'Note only')],
        string='Send SMS As',
        compute='_compute_sms_method',
        readonly=False, store=True)

    def _name_depends(self):
        return [*super()._name_depends(), "sms_template_id"]

    def _generate_action_name(self):
        self.ensure_one()
        if self.state == 'sms' and self.sms_template_id:
            return _('Send %(template_name)s', template_name=self.sms_template_id.name)
        return super()._generate_action_name()

    @api.depends('state')
    def _compute_available_model_ids(self):
        mail_thread_based = self.filtered(lambda action: action.state == 'sms')
        if mail_thread_based:
            mail_models = self.env['ir.model'].search([('is_mail_thread', '=', True), ('transient', '=', False)])
            for action in mail_thread_based:
                action.available_model_ids = mail_models.ids
        super(IrActionsServer, self - mail_thread_based)._compute_available_model_ids()

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

    @api.model
    def _warning_depends(self):
        return super()._warning_depends() + [
            'model_id',
            'state',
            'sms_template_id',
        ]

    def _get_warning_messages(self):
        self.ensure_one()
        warnings = super()._get_warning_messages()

        if self.state == 'sms':
            if self.model_id.transient or not self.model_id.is_mail_thread:
                warnings.append(_("Sending SMS can only be done on a not transient mail.thread model"))

            if self.sms_template_id and self.sms_template_id.model_id != self.model_id:
                warnings.append(
                    _('SMS template model of %(action_name)s does not match action model.',
                      action_name=self.name
                     )
                )

        return warnings

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
