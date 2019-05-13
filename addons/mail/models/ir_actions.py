# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ServerActions(models.Model):
    """ Add email option in server actions. """
    _name = 'ir.actions.server'
    _description = 'Server Action'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[
        ('email', 'Send Email'),
        ('followers', 'Add Followers'),
        ('next_activity', 'Create Next Activity'),
    ])
    # Followers
    partner_ids = fields.Many2many('res.partner', string='Add Followers')
    channel_ids = fields.Many2many('mail.channel', string='Add Channels')
    # Template
    template_id = fields.Many2one(
        'mail.template', 'Email Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )
    # Next Activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', model_id)]")
    activity_summary = fields.Char('Summary')
    activity_note = fields.Html('Note')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_user_type = fields.Selection([
        ('specific', 'Specific User'),
        ('generic', 'Generic User From Record')], default="specific", required=True,
        help="Use 'Specific User' to always assign the same user on the next activity. Use 'Generic User From Record' to specify the field name of the user to choose on the record.")
    activity_user_id = fields.Many2one('res.users', string='Responsible')
    activity_user_field_name = fields.Char('User field name', help="Technical name of the user on the record", default="user_id")

    @api.onchange('activity_date_deadline_range')
    def _onchange_activity_date_deadline_range(self):
        if self.activity_date_deadline_range < 0:
            raise UserError(_("The 'Due Date In' value can't be negative."))

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

    @api.constrains('state', 'model_id')
    def _check_activity_mixin(self):
        for action in self:
            if action.state == 'next_activity' and not issubclass(self.pool[action.model_id.model], self.pool['mail.thread']):
                raise ValidationError(_("A next activity can only be planned on models that use the chatter"))

    @api.model
    def run_action_followers_multi(self, action, eval_context=None):
        Model = self.env[action.model_name]
        if self.partner_ids or self.channel_ids and hasattr(Model, 'message_subscribe'):
            records = Model.browse(self._context.get('active_ids', self._context.get('active_id')))
            records.message_subscribe(self.partner_ids.ids, self.channel_ids.ids)
        return False

    @api.model
    def _is_recompute(self, action):
        """When an activity is set on update of a record,
        update might be triggered many times by recomputes.
        When need to know it to skip these steps.
        Except if the computed field is supposed to trigger the action
        """
        records = self.env[action.model_name].browse(
            self._context.get('active_ids', self._context.get('active_id')))
        old_values = action._context.get('old_values')
        if old_values:
            domain_post = action._context.get('domain_post')
            tracked_fields = []
            if domain_post:
                for leaf in domain_post:
                    if isinstance(leaf, (tuple, list)):
                        tracked_fields.append(leaf[0])
            fields_to_check = [field for record, field_names in old_values.items() for field in field_names if field not in tracked_fields]
            if fields_to_check:
                field = records._fields[fields_to_check[0]]
                # Pick an arbitrary field; if it is marked to be recomputed,
                # it means we are in an extraneous write triggered by the recompute.
                # In this case, we should not create a new activity.
                if records._recompute_check(field):
                    return True
        return False

    @api.model
    def run_action_email(self, action, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not action.template_id or not self._context.get('active_id') or self._is_recompute(action):
            return False
        # Clean context from default_type to avoid making attachment
        # with wrong values in subsequent operations
        cleaned_ctx = dict(self.env.context)
        cleaned_ctx.pop('default_type', None)
        cleaned_ctx.pop('default_parent_id', None)
        action.template_id.with_context(cleaned_ctx).send_mail(self._context.get('active_id'), force_send=False, raise_exception=False)
        return False

    @api.model
    def run_action_next_activity(self, action, eval_context=None):
        if not action.activity_type_id or not self._context.get('active_id') or self._is_recompute(action):
            return False

        records = self.env[action.model_name].browse(self._context.get('active_ids', self._context.get('active_id')))

        vals = {
            'summary': action.activity_summary or '',
            'note': action.activity_note or '',
            'activity_type_id': action.activity_type_id.id,
        }
        if action.activity_date_deadline_range > 0:
            vals['date_deadline'] = fields.Date.context_today(action) + relativedelta(**{action.activity_date_deadline_range_type: action.activity_date_deadline_range})
        for record in records:
            if action.activity_user_type == 'specific':
                user = action.activity_user_id
            elif action.activity_user_type == 'generic' and action.activity_user_field_name in record:
                user = record[action.activity_user_field_name]
            if user:
                vals['user_id'] = user.id
            record.activity_schedule(**vals)
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
