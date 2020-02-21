# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
import pytz

from odoo import api, exceptions, fields, models, _

from odoo.tools import pycompat
from odoo.tools.misc import clean_context

_logger = logging.getLogger(__name__)


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model_id field should be used. """
    _name = 'mail.activity.type'
    _description = 'Activity Type'
    _rec_name = 'name'
    _order = 'sequence, id'

    @api.model
    def default_get(self, fields):
        if not self.env.context.get('default_res_model_id') and self.env.context.get('default_res_model'):
            self = self.with_context(
                default_res_model_id=self.env['ir.model']._get(self.env.context.get('default_res_model'))
            )
        return super(MailActivityType, self).default_get(fields)

    name = fields.Char('Name', required=True, translate=True)
    summary = fields.Char('Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    delay_count = fields.Integer(
        'After', default=0, oldname='days',
        help='Number of days/week/month before executing the action. It allows to plan the action deadline.')
    delay_unit = fields.Selection([
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('months', 'months')], string="Delay units", help="Unit of delay", required=True, default='days')
    delay_from = fields.Selection([
        ('current_date', 'after validation date'),
        ('previous_activity', 'after previous activity deadline')], string="Delay Type", help="Type of delay", required=True, default='previous_activity')
    icon = fields.Char('Icon', help="Font awesome icon e.g. fa-tasks")
    decoration_type = fields.Selection([
        ('warning', 'Alert'),
        ('danger', 'Error')], string="Decoration Type",
        help="Change the background color of the related activities of this type.")
    res_model_id = fields.Many2one(
        'ir.model', 'Model', index=True,
        domain=['&', ('is_mail_thread', '=', True), ('transient', '=', False)],
        help='Specify a model if the activity should be specific to a model'
             ' and not available when managing activities for other models.')
    default_next_type_id = fields.Many2one('mail.activity.type', 'Default Next Activity',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]")
    force_next = fields.Boolean("Auto Schedule Next Activity", default=False)
    next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id', 'recommended_id',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]",
        string='Recommended Next Activities')
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id', 'activity_id',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]",
        string='Preceding Activities')
    category = fields.Selection([
        ('default', 'Other')], default='default',
        string='Category',
        help='Categories may trigger specific behavior like opening calendar view')
    mail_template_ids = fields.Many2many('mail.template', string='Mails templates')

    #Fields for display purpose only
    initial_res_model_id = fields.Many2one('ir.model', 'Initial model', compute="_compute_initial_res_model_id", store=False,
            help='Technical field to keep trace of the model at the beginning of the edition for UX related behaviour')
    res_model_change = fields.Boolean(string="Model has change", help="Technical field for UX related behaviour", default=False, store=False)

    @api.onchange('res_model_id')
    def _onchange_res_model_id(self):
        self.mail_template_ids = self.mail_template_ids.filtered(lambda template: template.model_id == self.res_model_id)
        self.res_model_change = self.initial_res_model_id and self.initial_res_model_id != self.res_model_id

    def _compute_initial_res_model_id(self):
        for activity_type in self:
            activity_type.initial_res_model_id = activity_type.res_model_id


class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _name = 'mail.activity'
    _description = 'Activity'
    _order = 'date_deadline ASC'
    _rec_name = 'summary'

    @api.model
    def default_get(self, fields):
        res = super(MailActivity, self).default_get(fields)
        if not fields or 'res_model_id' in fields and res.get('res_model'):
            res['res_model_id'] = self.env['ir.model']._get(res['res_model']).id
        return res

    # owner
    res_id = fields.Integer('Related Document ID', index=True, required=True)
    res_model_id = fields.Many2one(
        'ir.model', 'Document Model',
        index=True, ondelete='cascade', required=True)
    res_model = fields.Char(
        'Related Document Model',
        index=True, related='res_model_id.model', store=True, readonly=True)
    res_name = fields.Char(
        'Document Name', compute='_compute_res_name', store=True,
        help="Display name of the related document.", readonly=True)
    # activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]", ondelete='restrict')
    activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
    activity_decoration = fields.Selection(related='activity_type_id.decoration_type', readonly=True)
    icon = fields.Char('Icon', related='activity_type_id.icon', readonly=True)
    summary = fields.Char('Summary')
    note = fields.Html('Note')
    feedback = fields.Html('Feedback')
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.context_today)
    automated = fields.Boolean(
        'Automated activity', readonly=True,
        help='Indicates this activity has been created automatically and not by any user.')
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    create_user_id = fields.Many2one(
        'res.users', 'Creator',
        default=lambda self: self.env.user,
        index=True)
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], 'State',
        compute='_compute_state')
    recommended_activity_type_id = fields.Many2one('mail.activity.type', string="Recommended Activity Type")
    previous_activity_type_id = fields.Many2one('mail.activity.type', string='Previous Activity Type', readonly=True)
    has_recommended_activities = fields.Boolean(
        'Next activities available',
        compute='_compute_has_recommended_activities',
        help='Technical field for UX purpose')
    mail_template_ids = fields.Many2many(related='activity_type_id.mail_template_ids', readonly=False)
    force_next = fields.Boolean(related='activity_type_id.force_next', readonly=False)

    @api.multi
    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(record.previous_activity_type_id.next_type_ids)

    @api.multi
    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        for record in self:
            if record.previous_activity_type_id.default_next_type_id:
                record.activity_type_id = record.previous_activity_type_id.default_next_type_id

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = self.env[activity.res_model].browse(activity.res_id).name_get()[0][1]

    @api.depends('date_deadline')
    def _compute_state(self):
        for record in self.filtered(lambda activity: activity.date_deadline):
            tz = record.user_id.sudo().tz
            date_deadline = record.date_deadline
            record.state = self._compute_state_from_date(date_deadline, tz)

    @api.model
    def _compute_state_from_date(self, date_deadline, tz=False):
        date_deadline = fields.Date.from_string(date_deadline)
        today_default = date.today()
        today = today_default
        if tz:
            today_utc = pytz.UTC.localize(datetime.utcnow())
            today_tz = today_utc.astimezone(pytz.timezone(tz))
            today = date(year=today_tz.year, month=today_tz.month, day=today_tz.day)
        diff = (date_deadline - today)
        if diff.days == 0:
            return 'today'
        elif diff.days < 0:
            return 'overdue'
        else:
            return 'planned'

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        if self.activity_type_id:
            self.summary = self.activity_type_id.summary
            # Date.context_today is correct because date_deadline is a Date and is meant to be
            # expressed in user TZ
            base = fields.Date.context_today(self)
            if self.activity_type_id.delay_from == 'previous_activity' and 'activity_previous_deadline' in self.env.context:
                base = fields.Date.from_string(self.env.context.get('activity_previous_deadline'))
            self.date_deadline = base + relativedelta(**{self.activity_type_id.delay_unit: self.activity_type_id.delay_count})

    @api.onchange('recommended_activity_type_id')
    def _onchange_recommended_activity_type_id(self):
        if self.recommended_activity_type_id:
            self.activity_type_id = self.recommended_activity_type_id

    @api.multi
    def _check_access(self, operation):
        """ Rule to access activities

         * create: check write rights on related document;
         * write: rule OR write rights on document;
         * unlink: rule OR write rights on document;
        """
        self.check_access_rights(operation, raise_exception=True)  # will raise an AccessError

        if operation in ('write', 'unlink'):
            try:
                self.check_access_rule(operation)
            except exceptions.AccessError:
                pass
            else:
                return
        doc_operation = 'read' if operation == 'read' else 'write'
        activity_to_documents = dict()
        for activity in self.sudo():
            activity_to_documents.setdefault(activity.res_model, list()).append(activity.res_id)
        for model, res_ids in activity_to_documents.items():
            self.env[model].check_access_rights(doc_operation, raise_exception=True)
            try:
                self.env[model].browse(res_ids).check_access_rule(doc_operation)
            except exceptions.AccessError:
                raise exceptions.AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % (self._description, operation)
                    + ' - ({} {}, {} {})'.format(_('Records:'), res_ids[:6], _('User:'), self._uid)
                )

    @api.multi
    def _check_access_assignation(self):
        """ Check assigned user (user_id field) has access to the document. Purpose
        is to allow assigned user to handle their activities. For that purpose
        assigned user should be able to at least read the document. We therefore
        raise an UserError if the assigned user has no access to the document. """
        for activity in self:
            model = self.env[activity.res_model].sudo(activity.user_id.id)
            try:
                model.check_access_rights('read')
            except exceptions.AccessError:
                raise exceptions.UserError(
                    _('Assigned user %s has no access to the document and is not able to handle this activity.') %
                    activity.user_id.display_name)
            else:
                try:
                    target_user = activity.user_id
                    target_record = self.env[activity.res_model].browse(activity.res_id)
                    if hasattr(target_record, 'company_id') and (
                        target_record.company_id != target_user.company_id and (
                            len(target_user.sudo().company_ids) > 1)):
                        return  # in that case we skip the check, assuming it would fail because of the company
                    model.browse(activity.res_id).check_access_rule('read')
                except exceptions.AccessError:
                    raise exceptions.UserError(
                        _('Assigned user %s has no access to the document and is not able to handle this activity.') %
                        activity.user_id.display_name)

    @api.model
    def create(self, values):
        # already compute default values to be sure those are computed using the current user
        values_w_defaults = self.default_get(self._fields.keys())
        values_w_defaults.update(values)

        # continue as sudo because activities are somewhat protected
        activity = super(MailActivity, self.sudo()).create(values_w_defaults)
        activity_user = activity.sudo(self.env.user)
        activity_user._check_access('create')
        need_sudo = False
        try:  # in multicompany, reading the partner might break
            partner_id = activity_user.user_id.partner_id.id
        except exceptions.AccessError:
            need_sudo = True
            partner_id = activity_user.user_id.sudo().partner_id.id

        # send a notification to assigned user; in case of manually done activity also check
        # target has rights on document otherwise we prevent its creation. Automated activities
        # are checked since they are integrated into business flows that should not crash.
        if activity_user.user_id != self.env.user:
            if not activity_user.automated:
                activity_user._check_access_assignation()
            if not self.env.context.get('mail_activity_quick_update', False):
                if need_sudo:
                    activity_user.sudo().action_notify()
                else:
                    activity_user.action_notify()

        self.env[activity_user.res_model].browse(activity_user.res_id).message_subscribe(partner_ids=[partner_id])
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                {'type': 'activity_updated', 'activity_created': True})
        return activity_user

    @api.multi
    def write(self, values):
        self._check_access('write')
        if values.get('user_id'):
            pre_responsibles = self.mapped('user_id.partner_id')
        res = super(MailActivity, self.sudo()).write(values)

        if values.get('user_id'):
            if values['user_id'] != self.env.uid:
                to_check = self.filtered(lambda act: not act.automated)
                to_check._check_access_assignation()
                if not self.env.context.get('mail_activity_quick_update', False):
                    self.action_notify()
            for activity in self:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])
                if activity.date_deadline <= fields.Date.today():
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                        {'type': 'activity_updated', 'activity_created': True})
            for activity in self:
                if activity.date_deadline <= fields.Date.today():
                    for partner in pre_responsibles:
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner', partner.id),
                            {'type': 'activity_updated', 'activity_deleted': True})
        return res

    @api.multi
    def unlink(self):
        self._check_access('unlink')
        for activity in self:
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(MailActivity, self.sudo()).unlink()

    @api.multi
    def action_notify(self):
        body_template = self.env.ref('mail.message_activity_assigned')
        for activity in self:
            model_description = self.env['ir.model']._get(activity.res_model).display_name
            body = body_template.render(
                dict(activity=activity, model_description=model_description),
                engine='ir.qweb',
                minimal_qcontext=True
            )
            self.env['mail.thread'].message_notify(
                partner_ids=activity.user_id.partner_id.ids,
                body=body,
                subject=_('%s: %s assigned to you') % (activity.res_name, activity.summary or activity.activity_type_id.name),
                record_name=activity.res_name,
                model_description=model_description,
                notif_layout='mail.mail_notification_light'
            )

    @api.multi
    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback()

    def action_feedback(self, feedback=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))

        # Search for all attachments linked to the activities we are about to unlink. This way, we
        # can link them to the message posted and prevent their deletion.
        attachments = self.env['ir.attachment'].search_read([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ], ['id', 'res_id'])

        activity_attachments = defaultdict(list)
        for attachment in attachments:
            activity_id = attachment['res_id']
            activity_attachments[activity_id].append(attachment['id'])

        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                mail_activity_type_id=activity.activity_type_id.id,
            )

            # Moving the attachments in the message
            # TODO: Fix void res_id on attachment when you create an activity with an image
            # directly, see route /web_editor/attachment/add
            activity_message = record.message_ids[0]
            message_attachments = self.env['ir.attachment'].browse(activity_attachments[activity.id])
            if message_attachments:
                message_attachments.write({
                    'res_id': activity_message.id,
                    'res_model': activity_message._name,
                })
                activity_message.attachment_ids = message_attachments
            message |= activity_message

        self.unlink()
        return message.ids and message.ids[0] or False

    def action_done_schedule_next(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback_schedule_next()

    @api.multi
    def action_feedback_schedule_next(self, feedback=False):
        ctx = dict(
                    clean_context(self.env.context),
                    default_previous_activity_type_id=self.activity_type_id.id,
                    activity_previous_deadline=self.date_deadline,
                    default_res_id=self.res_id,
                    default_res_model=self.res_model,
                )
        force_next = self.force_next
        self.action_feedback(feedback)  # will unlink activity, dont access self after that
        if force_next:
            Activity = self.env['mail.activity'].with_context(ctx)
            res = Activity.new(Activity.default_get(Activity.fields_get()))
            res._onchange_previous_activity_type_id()
            res._onchange_activity_type_id()
            Activity.create(res._convert_to_write(res._cache))
            return False
        else:
            return {
                'name': _('Schedule an Activity'),
                'context': ctx,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.activity',
                'views': [(False, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def activity_format(self):
        activities = self.read()
        mail_template_ids = set([template_id for activity in activities for template_id in activity["mail_template_ids"]])
        mail_template_info = self.env["mail.template"].browse(mail_template_ids).read(['id', 'name'])
        mail_template_dict = dict([(mail_template['id'], mail_template) for mail_template in mail_template_info])
        for activity in activities:
            activity['mail_template_ids'] = [mail_template_dict[mail_template_id] for mail_template_id in activity['mail_template_ids']]
        return activities

    @api.model
    def get_activity_data(self, res_model, domain):
        activity_domain = [('res_model', '=', res_model)]
        if domain:
            res = self.env[res_model].search(domain)
            activity_domain.append(('res_id', 'in', res.ids))
        grouped_activities = self.env['mail.activity'].read_group(
            activity_domain,
            ['res_id', 'activity_type_id', 'ids:array_agg(id)', 'date_deadline:min(date_deadline)'],
            ['res_id', 'activity_type_id'],
            lazy=False)
        # filter out unreadable records
        if not domain:
            res_ids = tuple(a['res_id'] for a in grouped_activities)
            res = self.env[res_model].search([('id', 'in', res_ids)])
            grouped_activities = [a for a in grouped_activities if a['res_id'] in res.ids]
        activity_type_ids = self.env['mail.activity.type']
        res_id_to_deadline = {}
        activity_data = defaultdict(dict)
        for group in grouped_activities:
            res_id = group['res_id']
            activity_type_id = group['activity_type_id'][0]
            activity_type_ids |= self.env['mail.activity.type'].browse(activity_type_id)  # we will get the name when reading mail_template_ids
            res_id_to_deadline[res_id] = group['date_deadline'] if (res_id not in res_id_to_deadline or group['date_deadline'] < res_id_to_deadline[res_id]) else res_id_to_deadline[res_id]
            state = self._compute_state_from_date(group['date_deadline'], self.user_id.sudo().tz)
            activity_data[res_id][activity_type_id] = {
                'count': group['__count'],
                'ids': group['ids'],
                'state': state,
                'o_closest_deadline': group['date_deadline'],
            }
        res_ids_sorted = sorted(res_id_to_deadline, key=lambda item: res_id_to_deadline[item])
        res_id_to_name = dict(self.env[res_model].browse(res_ids_sorted).name_get())
        activity_type_infos = []
        for elem in sorted(activity_type_ids, key=lambda item: item.sequence):
            mail_template_info = []
            for mail_template_id in elem.mail_template_ids:
                mail_template_info.append({"id": mail_template_id.id, "name": mail_template_id.name})
            activity_type_infos.append([elem.id, elem.name, mail_template_info])

        return {
            'activity_types': activity_type_infos,
            'res_ids': [(rid, res_id_to_name[rid]) for rid in res_ids_sorted],
            'grouped_activities': activity_data,
            'model': res_model,
        }


class MailActivityMixin(models.AbstractModel):
    """ Mail Activity Mixin is a mixin class to use if you want to add activities
    management on a model. It works like the mail.thread mixin. It defines
    an activity_ids one2many field toward activities using res_id and res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in the
    Chatter widget although it is a separate widget. It displays activities linked
    to the current record and allow to schedule, edit and mark done activities.
    Use widget="mail_activity" on activity_ids field in form view to use it.

    There is also a kanban widget defined. It defines a small widget to integrate
    in kanban vignettes. It allow to manage activities directly from the kanban
    view. Use widget="kanban_activity" on activitiy_ids field in kanban view to
    use it.

    Some context keys allow to control the mixin behavior. Use those in some
    specific cases like import

     * ``mail_activity_automation_skip``: skip activities automation; it means
       no automated activities will be generated, updated or unlinked, allowing
       to save computation and avoid generating unwanted activities;
    """
    _name = 'mail.activity.mixin'
    _description = 'Activity Mixin'

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user",
        domain=lambda self: [('res_model', '=', self._name)])
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='Activity State',
        compute='_compute_activity_state',
        groups="base.group_user",
        help='Status based on activities\nOverdue: Due date is already passed\n'
             'Today: Activity date is today\nPlanned: Future activities.')
    activity_user_id = fields.Many2one(
        'res.users', 'Responsible User',
        related='activity_ids.user_id', readonly=False,
        search='_search_activity_user_id',
        groups="base.group_user")
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id', readonly=False,
        search='_search_activity_type_id',
        groups="base.group_user")
    activity_date_deadline = fields.Date(
        'Next Activity Deadline',
        compute='_compute_activity_date_deadline', search='_search_activity_date_deadline',
        readonly=True, store=False,
        groups="base.group_user")
    activity_summary = fields.Char(
        'Next Activity Summary',
        related='activity_ids.summary', readonly=False,
        search='_search_activity_summary',
        groups="base.group_user",)

    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        for record in self:
            states = record.activity_ids.mapped('state')
            if 'overdue' in states:
                record.activity_state = 'overdue'
            elif 'today' in states:
                record.activity_state = 'today'
            elif 'planned' in states:
                record.activity_state = 'planned'

    @api.depends('activity_ids.date_deadline')
    def _compute_activity_date_deadline(self):
        for record in self:
            record.activity_date_deadline = record.activity_ids[:1].date_deadline

    def _search_activity_date_deadline(self, operator, operand):
        if operator == '=' and not operand:
            return [('activity_ids', '=', False)]
        return [('activity_ids.date_deadline', operator, operand)]

    @api.model
    def _search_activity_user_id(self, operator, operand):
        return [('activity_ids.user_id', operator, operand)]

    @api.model
    def _search_activity_type_id(self, operator, operand):
        return [('activity_ids.activity_type_id', operator, operand)]

    @api.model
    def _search_activity_summary(self, operator, operand):
        return [('activity_ids.summary', operator, operand)]

    @api.multi
    def write(self, vals):
        # Delete activities of archived record.
        if 'active' in vals and vals['active'] is False:
            self.env['mail.activity'].sudo().search(
                [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
            ).unlink()
        return super(MailActivityMixin, self).write(vals)

    @api.multi
    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result

    @api.multi
    def toggle_active(self):
        """ Before archiving the record we should also remove its ongoing
        activities. Otherwise they stay in the systray and concerning archived
        records it makes no sense. """
        record_to_deactivate = self.filtered(lambda rec: rec.active)
        if record_to_deactivate:
            # use a sudo to bypass every access rights; all activities should be removed
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', 'in', record_to_deactivate.ids)
            ]).unlink()
        return super(MailActivityMixin, self).toggle_active()

    def activity_send_mail(self, template_id):
        """ Automatically send an email based on the given mail.template, given
        its ID. """
        template = self.env['mail.template'].browse(template_id).exists()
        if not template:
            return False
        for record in self.with_context(mail_post_autofollow=True):
            record.message_post_with_template(
                template_id,
                composition_mode='comment'
            )
        return True

    def activity_schedule(self, act_type_xmlid='', date_deadline=None, summary='', note='', **act_values):
        """ Schedule an activity on each record of the current record set.
        This method allow to provide as parameter act_type_xmlid. This is an
        xml_id of activity type instead of directly giving an activity_type_id.
        It is useful to avoid having various "env.ref" in the code and allow
        to let the mixin handle access rights.

        :param date_deadline: the day the activity must be scheduled on
        the timezone of the user must be considered to set the correct deadline
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        if not date_deadline:
            date_deadline = fields.Date.context_today(self)
        if isinstance(date_deadline, datetime):
            _logger.warning("Scheduled deadline should be a date (got %s)", date_deadline)
        if act_type_xmlid:
            activity_type = self.sudo().env.ref(act_type_xmlid)
        else:
            activity_type = self.env['mail.activity.type'].sudo().browse(act_values['activity_type_id'])

        model_id = self.env['ir.model']._get(self._name).id
        activities = self.env['mail.activity']
        for record in self:
            create_vals = {
                'activity_type_id': activity_type.id,
                'summary': summary or activity_type.summary,
                'automated': True,
                'note': note,
                'date_deadline': date_deadline,
                'res_model_id': model_id,
                'res_id': record.id,
            }
            create_vals.update(act_values)
            activities |= self.env['mail.activity'].create(create_vals)
        return activities

    def activity_schedule_with_view(self, act_type_xmlid='', date_deadline=None, summary='', views_or_xmlid='', render_context=None, **act_values):
        """ Helper method: Schedule an activity on each record of the current record set.
        This method allow to the same mecanism as `activity_schedule`, but provide
        2 additionnal parameters:
        :param views_or_xmlid: record of ir.ui.view or string representing the xmlid
            of the qweb template to render
        :type views_or_xmlid: string or recordset
        :param render_context: the values required to render the given qweb template
        :type render_context: dict
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        render_context = render_context or dict()
        if isinstance(views_or_xmlid, pycompat.string_types):
            views = self.env.ref(views_or_xmlid, raise_if_not_found=False)
        else:
            views = views_or_xmlid
        if not views:
            return
        activities = self.env['mail.activity']
        for record in self:
            render_context['object'] = record
            note = views.render(render_context, engine='ir.qweb', minimal_qcontext=True)
            activities |= record.activity_schedule(act_type_xmlid=act_type_xmlid, date_deadline=date_deadline, summary=summary, note=note, **act_values)
        return activities

    def activity_reschedule(self, act_type_xmlids, user_id=None, date_deadline=None, new_user_id=None):
        """ Reschedule some automated activities. Activities to reschedule are
        selected based on type xml ids and optionally by user. Purpose is to be
        able to

         * update the deadline to date_deadline;
         * update the responsible to new_user_id;
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data.xmlid_to_res_id(xmlid) for xmlid in act_type_xmlids]
        domain = [
            '&', '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('automated', '=', True),
            ('activity_type_id', 'in', activity_types_ids)
        ]
        if user_id:
            domain = ['&'] + domain + [('user_id', '=', user_id)]
        activities = self.env['mail.activity'].search(domain)
        if activities:
            write_vals = {}
            if date_deadline:
                write_vals['date_deadline'] = date_deadline
            if new_user_id:
                write_vals['user_id'] = new_user_id
            activities.write(write_vals)
        return activities

    def activity_feedback(self, act_type_xmlids, user_id=None, feedback=None):
        """ Set activities as done, limiting to some activity types and
        optionally to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data.xmlid_to_res_id(xmlid) for xmlid in act_type_xmlids]
        domain = [
            '&', '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('automated', '=', True),
            ('activity_type_id', 'in', activity_types_ids)
        ]
        if user_id:
            domain = ['&'] + domain + [('user_id', '=', user_id)]
        activities = self.env['mail.activity'].search(domain)
        if activities:
            activities.action_feedback(feedback=feedback)
        return True

    def activity_unlink(self, act_type_xmlids, user_id=None):
        """ Unlink activities, limiting to some activity types and optionally
        to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data.xmlid_to_res_id(xmlid) for xmlid in act_type_xmlids]
        domain = [
            '&', '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('automated', '=', True),
            ('activity_type_id', 'in', activity_types_ids)
        ]
        if user_id:
            domain = ['&'] + domain + [('user_id', '=', user_id)]
        self.env['mail.activity'].search(domain).unlink()
        return True
