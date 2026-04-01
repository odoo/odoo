# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class IrActionsServer(models.Model):
    """ Add mail.thread related options in server actions. """
    _name = 'ir.actions.server'
    _description = 'Server Action'
    _inherit = ['ir.actions.server', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    model_id = fields.Many2one(tracking=True)
    crud_model_id = fields.Many2one(tracking=True)
    link_field_id = fields.Many2one(tracking=True)
    update_path = fields.Char(tracking=True)
    value = fields.Text(tracking=True)
    evaluation_type = fields.Selection(tracking=True)
    webhook_url = fields.Char(tracking=True)

    state = fields.Selection(
        tracking=True,
        selection_add=[
            ('next_activity', 'Create Activity'),
            ('mail_post', 'Send Email'),
            ('followers', 'Add Followers'),
            ('remove_followers', 'Remove Followers'),
            ('code',),
        ],
        ondelete={'mail_post': 'cascade',
                  'followers': 'cascade',
                  'remove_followers': 'cascade',
                  'next_activity': 'cascade',
        }
    )
    # Followers
    followers_type = fields.Selection(
        selection=[
            ('specific', 'Specific Followers'),
            ('generic', 'Dynamic Followers'),
        ],
        help="""
            - Specific Followers: select specific contacts to add/remove from record's followers.
            - Dynamic Followers: all contacts of the chosen record's field will be added/removed from followers.
        """,
        string='Followers Type',
        compute='_compute_followers_type',
        readonly=False, store=True
    )
    followers_partner_field_name = fields.Char(
        string='Followers Field',
        compute='_compute_followers_info',
        readonly=False, store=True
    )
    partner_ids = fields.Many2many('res.partner', compute='_compute_followers_info', readonly=False, store=True)

    # Message Post / Email
    template_id = fields.Many2one(
        'mail.template', 'Email Template',
        domain="[('model_id', '=', model_id)]",
        compute='_compute_template_id',
        ondelete='set null', readonly=False, store=True,
    )
    # Message post
    mail_post_autofollow = fields.Boolean(
        'Subscribe Recipients', compute='_compute_mail_post_autofollow',
        readonly=False, store=True)
    mail_post_method = fields.Selection(
        selection=[('email', 'Email'), ('comment', 'Message'), ('note', 'Note')],
        string='Send Email As',
        compute='_compute_mail_post_method',
        readonly=False, store=True)

    # Next Activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity Type',
        domain="['|', ('res_model', '=', False), ('res_model', '=', model_name)]",
        compute='_compute_activity_info', readonly=False, store=True,
        ondelete='restrict')
    activity_summary = fields.Char(
        'Title',
        compute='_compute_activity_info', readonly=False, store=True)
    activity_note = fields.Html(
        'Note',
        compute='_compute_activity_info', readonly=False, store=True)
    activity_date_deadline_range = fields.Integer(
        string='Due Date In',
        compute='_compute_activity_info', readonly=False, store=True)
    activity_date_deadline_range_type = fields.Selection(
        [('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        string='Due type',
        compute='_compute_activity_info', readonly=False, store=True)
    activity_user_type = fields.Selection(
        [('specific', 'Specific User'),
         ('generic', 'Dynamic User (based on record)')],
         string='User Type',
        compute='_compute_activity_info', readonly=False, store=True,
        help="Use 'Specific User' to always assign the same user on the next activity. Use 'Dynamic User' to specify the field name of the user to choose on the record.")
    activity_user_id = fields.Many2one(
        'res.users', string='Responsible',
        compute='_compute_activity_user_info', readonly=False, store=True)
    activity_user_field_name = fields.Char(
        'User Field',
        compute='_compute_activity_user_info', readonly=False, store=True)

    def _name_depends(self):
        return [*super()._name_depends(), "template_id", "activity_type_id"]

    def _generate_action_name(self):
        self.ensure_one()
        if self.state == 'mail_post' and self.template_id:
            return _('Send %(template_name)s', template_name=self.template_id.name)
        if self.state == 'next_activity' and self.activity_type_id:
            return _('Create %(activity_name)s', activity_name=self.activity_type_id.name)
        return super()._generate_action_name()

    @api.depends('state')
    def _compute_available_model_ids(self):
        mail_thread_based = self.filtered(
            lambda action: action.state in {'mail_post', 'followers', 'remove_followers', 'next_activity'}
        )
        if mail_thread_based:
            mail_models = self.env['ir.model'].search([('is_mail_thread', '=', True), ('transient', '=', False)])
            for action in mail_thread_based:
                action.available_model_ids = mail_models.ids
        super(IrActionsServer, self - mail_thread_based)._compute_available_model_ids()

    @api.depends('model_id', 'state')
    def _compute_template_id(self):
        to_reset = self.filtered(
            lambda act: act.state != 'mail_post' or \
                        (act.model_id != act.template_id.model_id)
        )
        if to_reset:
            to_reset.template_id = False

    @api.depends('state', 'mail_post_method')
    def _compute_mail_post_autofollow(self):
        to_reset = self.filtered(lambda act: act.state != 'mail_post' or act.mail_post_method == 'email')
        if to_reset:
            to_reset.mail_post_autofollow = False
        other = self - to_reset
        if other:
            other.mail_post_autofollow = True

    @api.depends('state')
    def _compute_mail_post_method(self):
        to_reset = self.filtered(lambda act: act.state != 'mail_post')
        if to_reset:
            to_reset.mail_post_method = False
        other = self - to_reset
        if other:
            other.mail_post_method = 'comment'

    @api.depends('model_id', 'state')
    def _compute_followers_type(self):
        to_reset = self.filtered(lambda act: not act.model_id or act.state not in ['followers', 'remove_followers'])
        to_reset.followers_type = False
        to_default = (self - to_reset).filtered(lambda act: not act.followers_type)
        to_default.followers_type = 'specific'

    @api.depends('followers_type')
    def _compute_followers_info(self):
        for action in self:
            if action.followers_type == 'specific':
                action.followers_partner_field_name = False
            elif action.followers_type == 'generic':
                action.partner_ids = False
                IrModelFields = self.env['ir.model.fields']
                domain = [('model', '=', action.model_id.model), ("relation", "=", "res.partner")]
                action.followers_partner_field_name = (
                    IrModelFields.search([*domain, ("name", "=", "partner_id")], limit=1)
                    or IrModelFields.search(domain, limit=1)
                ).name
            else:
                action.partner_ids = False
                action.followers_partner_field_name = False

    @api.depends('model_id', 'state')
    def _compute_activity_info(self):
        to_reset = self.filtered(lambda act: not act.model_id or act.state != 'next_activity')
        if to_reset:
            to_reset.activity_type_id = False
            to_reset.activity_summary = False
            to_reset.activity_note = False
            to_reset.activity_date_deadline_range = False
            to_reset.activity_date_deadline_range_type = False
            to_reset.activity_user_type = False
        for action in (self - to_reset):
            if action.activity_type_id.res_model and action.model_id.model != action.activity_type_id.res_model:
                action.activity_type_id = False
            if not action.activity_summary:
                action.activity_summary = action.activity_type_id.summary
            if not action.activity_date_deadline_range_type:
                action.activity_date_deadline_range_type = 'days'
            if not action.activity_user_type:
                action.activity_user_type = 'specific'

    @api.depends('model_id', 'activity_user_type')
    def _compute_activity_user_info(self):
        to_compute = self.filtered("activity_user_type")
        (self - to_compute).activity_user_id = False
        (self - to_compute).activity_user_field_name = False
        for action in to_compute:
            if action.activity_user_type == 'specific':
                action.activity_user_field_name = False
            else:
                action.activity_user_id = False
                IrModelFields = self.env['ir.model.fields']
                domain = [('model', '=', action.model_id.model), ("relation", "=", "res.users")]
                action.activity_user_field_name = (
                    IrModelFields.search([*domain, ("name", "=", "user_id")], limit=1)
                    or IrModelFields.search(domain, limit=1)
                ).name

    @api.model
    def _warning_depends(self):
        return super()._warning_depends() + [
            'activity_date_deadline_range',
            'model_id',
            'template_id',
            'state',
            'followers_type',
            'followers_partner_field_name',
            'activity_user_type',
            'activity_user_field_name',
        ]

    def _get_warning_messages(self):
        warnings = super()._get_warning_messages()

        if self.activity_date_deadline_range < 0:
            warnings.append(_("The 'Due Date In' value can't be negative."))

        if self.state == 'mail_post' and self.template_id and self.template_id.model_id != self.model_id:
            warnings.append(_("Mail template model of $(action_name)s does not match action model.", action_name=self.name))

        if self.state in {'mail_post', 'followers', 'remove_followers', 'next_activity'} and self.model_id.transient:
            warnings.append(_("This action cannot be done on transient models."))

        if (
            (self.state in {"followers", "remove_followers"}
            or (self.state == "mail_post" and self.mail_post_method != "email"))
            and not self.model_id.is_mail_thread
        ):
            warnings.append(_("This action can only be done on a mail thread models"))

        if self.state == 'next_activity' and not self.model_id.is_mail_activity:
            warnings.append(_("A next activity can only be planned on models that use activities."))

        if self.state in ('followers', 'remove_followers') and self.followers_type == 'generic' and self.followers_partner_field_name:
            fields, field_chain_str = self._get_relation_chain("followers_partner_field_name")
            if fields and fields[-1].comodel_name != "res.partner":
                warnings.append(_(
                    "The field '%(field_chain_str)s' is not a partner field.",
                    field_chain_str=field_chain_str,
                ))

        if self.state == 'next_activity' and self.activity_user_type == 'generic' and self.activity_user_field_name:
            fields, field_chain_str = self._get_relation_chain("activity_user_field_name")
            if fields and fields[-1].comodel_name != "res.users":
                warnings.append(_(
                    "The field '%(field_chain_str)s' is not a user field.",
                    field_chain_str=field_chain_str,
                ))

        return warnings

    def _run_action_followers_multi(self, eval_context=None):
        Model = self.env[self.model_name]
        if hasattr(Model, 'message_subscribe'):
            records = Model.browse(self.env.context.get('active_ids', self.env.context.get('active_id')))
            if self.followers_type == 'specific':
                partner_ids = self.partner_ids
            else:
                followers_field = self.followers_partner_field_name
                partner_ids = records.mapped(followers_field)
            records.message_subscribe(partner_ids=partner_ids.ids)
        return False

    def _run_action_remove_followers_multi(self, eval_context=None):
        Model = self.env[self.model_name]
        if hasattr(Model, 'message_unsubscribe'):
            records = Model.browse(self.env.context.get('active_ids', self.env.context.get('active_id')))
            if self.followers_type == 'specific':
                partner_ids = self.partner_ids
            else:
                followers_field = self.followers_partner_field_name
                partner_ids = records.mapped(followers_field)
            records.message_unsubscribe(partner_ids=partner_ids.ids)
        return False

    def _is_recompute(self):
        """When an activity is set on update of a record,
        update might be triggered many times by recomputes.
        When need to know it to skip these steps.
        Except if the computed field is supposed to trigger the action
        """
        records = self.env[self.model_name].browse(
            self.env.context.get('active_ids', self.env.context.get('active_id')))
        old_values = self.env.context.get('old_values')
        if old_values:
            domain_post = self.env.context.get('domain_post')
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
                if records & self.env.records_to_compute(field):
                    return True
        return False

    def _run_action_mail_post_multi(self, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not self.template_id or (not self.env.context.get('active_ids') and not self.env.context.get('active_id')) or self._is_recompute():
            return False
        res_ids = self.env.context.get('active_ids', [self.env.context.get('active_id')])

        # Clean context from default_type to avoid making attachment
        # with wrong values in subsequent operations
        cleaned_ctx = dict(self.env.context)
        cleaned_ctx.pop('default_type', None)
        cleaned_ctx.pop('default_parent_id', None)
        cleaned_ctx['mail_post_autofollow_author_skip'] = True  # do not subscribe random people to records
        cleaned_ctx['mail_post_autofollow'] = self.mail_post_autofollow

        if self.mail_post_method in ('comment', 'note'):
            records = self.env[self.model_name].with_context(cleaned_ctx).browse(res_ids)
            message_type = 'auto_comment' if self.state == 'mail_post' else 'notification'
            if self.mail_post_method == 'comment':
                subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
            else:
                subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
            records.message_post_with_source(
                self.template_id,
                message_type=message_type,
                subtype_id=subtype_id,
            )
        else:
            template = self.template_id.with_context(cleaned_ctx)
            for res_id in res_ids:
                template.send_mail(
                    res_id,
                    force_send=False,
                    raise_exception=False
                )
        return False

    def _run_action_next_activity(self, eval_context=None):
        if not self.activity_type_id or not self.env.context.get('active_id') or self._is_recompute():
            return False

        records = self.env[self.model_name].browse(self.env.context.get('active_ids', self.env.context.get('active_id')))

        vals = {
            'summary': self.activity_summary or '',
            'note': self.activity_note or '',
            'activity_type_id': self.activity_type_id.id,
        }
        if self.activity_date_deadline_range > 0:
            vals['date_deadline'] = fields.Date.context_today(self) + relativedelta(**{
                self.activity_date_deadline_range_type or 'days': self.activity_date_deadline_range})
        for record in records:
            user = False
            if self.activity_user_type == 'specific':
                user = self.activity_user_id
            elif self.activity_user_type == 'generic' and self.activity_user_field_name in record:
                user = record[self.activity_user_field_name]
            if user:
                # if x2m field, assign to the first user found
                # (same behavior as Field.traverse_related)
                vals['user_id'] = user.ids[0]
            record.activity_schedule(**vals)
        return False

    @api.model
    def _get_eval_context(self, action=None):
        """ Override the method giving the evaluation context but also the
        context used in all subsequent calls. Add the mail_notify_force_send
        key set to False in the context. This way all notification emails linked
        to the currently executed action will be set in the queue instead of
        sent directly. This will avoid possible break in transactions. """
        return super(IrActionsServer, self.with_context(mail_notify_force_send=False))._get_eval_context(action=action)
