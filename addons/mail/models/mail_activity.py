# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
import pytz

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression

from odoo.tools.misc import clean_context
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

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
    summary = fields.Char('Default Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    create_uid = fields.Many2one('res.users', index=True)
    delay_count = fields.Integer(
        'Scheduled Date', default=0,
        help='Number of days/week/month before executing the action. It allows to plan the action deadline.')
    delay_unit = fields.Selection([
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('months', 'months')], string="Delay units", help="Unit of delay", required=True, default='days')
    delay_label = fields.Char(compute='_compute_delay_label')
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
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]", ondelete='restrict')
    force_next = fields.Boolean("Trigger Next Activity", default=False)
    next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id', 'recommended_id',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]",
        string='Recommended Next Activities')
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id', 'activity_id',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]",
        string='Preceding Activities')
    category = fields.Selection([
        ('default', 'None'), ('upload_file', 'Upload Document')
    ], default='default', string='Action to Perform',
        help='Actions may trigger specific behavior like opening calendar view or automatically mark as done when a document is uploaded')
    mail_template_ids = fields.Many2many('mail.template', string='Email templates')
    default_user_id = fields.Many2one("res.users", string="Default User")
    default_description = fields.Html(string="Default Description", translate=True)

    #Fields for display purpose only
    initial_res_model_id = fields.Many2one('ir.model', 'Initial model', compute="_compute_initial_res_model_id", store=False,
            help='Technical field to keep track of the model at the start of editing to support UX related behaviour')
    res_model_change = fields.Boolean(string="Model has change", help="Technical field for UX related behaviour", default=False, store=False)

    @api.onchange('res_model_id')
    def _onchange_res_model_id(self):
        self.mail_template_ids = self.mail_template_ids.filtered(lambda template: template.model_id == self.res_model_id)
        self.res_model_change = self.initial_res_model_id and self.initial_res_model_id != self.res_model_id

    def _compute_initial_res_model_id(self):
        for activity_type in self:
            activity_type.initial_res_model_id = activity_type.res_model_id

    @api.depends('delay_unit', 'delay_count')
    def _compute_delay_label(self):
        selection_description_values = {
            e[0]: e[1] for e in self._fields['delay_unit']._description_selection(self.env)}
        for activity_type in self:
            unit = selection_description_values[activity_type.delay_unit]
            activity_type.delay_label = '%s %s' % (activity_type.delay_count, unit)


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

    @api.model
    def _default_activity_type_id(self):
        ActivityType = self.env["mail.activity.type"]
        activity_type_todo = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        default_vals = self.default_get(['res_model_id', 'res_model'])
        if not default_vals.get('res_model_id'):
            return ActivityType
        current_model_id = default_vals['res_model_id']
        if activity_type_todo and activity_type_todo.active and (activity_type_todo.res_model_id.id == current_model_id or not activity_type_todo.res_model_id):
            return activity_type_todo
        activity_type_model = ActivityType.search([('res_model_id', '=', current_model_id)], limit=1)
        if activity_type_model:
            return activity_type_model
        activity_type_generic = ActivityType.search([('res_model_id','=', False)], limit=1)
        return activity_type_generic

    # owner
    res_model_id = fields.Many2one(
        'ir.model', 'Document Model',
        index=True, ondelete='cascade', required=True)
    res_model = fields.Char(
        'Related Document Model',
        index=True, related='res_model_id.model', compute_sudo=True, store=True, readonly=True)
    res_id = fields.Many2oneReference(string='Related Document ID', index=True, required=True, model_field='res_model')
    res_name = fields.Char(
        'Document Name', compute='_compute_res_name', compute_sudo=True, store=True,
        help="Display name of the related document.", readonly=True)
    # activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity Type',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]", ondelete='restrict',
        default=_default_activity_type_id)
    activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
    activity_decoration = fields.Selection(related='activity_type_id.decoration_type', readonly=True)
    icon = fields.Char('Icon', related='activity_type_id.icon', readonly=True)
    summary = fields.Char('Summary')
    note = fields.Html('Note', sanitize_style=True)
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.context_today)
    automated = fields.Boolean(
        'Automated activity', readonly=True,
        help='Indicates this activity has been created automatically and not by any user.')
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
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
    mail_template_ids = fields.Many2many(related='activity_type_id.mail_template_ids', readonly=True)
    force_next = fields.Boolean(related='activity_type_id.force_next', readonly=True)
    # access
    can_write = fields.Boolean(compute='_compute_can_write', help='Technical field to hide buttons if the current user has no access.')

    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(record.previous_activity_type_id.next_type_ids)

    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        for record in self:
            if record.previous_activity_type_id.default_next_type_id:
                record.activity_type_id = record.previous_activity_type_id.default_next_type_id

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = activity.res_model and \
                self.env[activity.res_model].browse(activity.res_id).display_name

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

    @api.depends('res_model', 'res_id', 'user_id')
    def _compute_can_write(self):
        valid_records = self._filter_access_rules('write')
        for record in self:
            record.can_write = record in valid_records

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        if self.activity_type_id:
            if self.activity_type_id.summary:
                self.summary = self.activity_type_id.summary
            self.date_deadline = self._calculate_date_deadline(self.activity_type_id)
            self.user_id = self.activity_type_id.default_user_id or self.env.user
            if self.activity_type_id.default_description:
                self.note = self.activity_type_id.default_description

    def _calculate_date_deadline(self, activity_type):
        # Date.context_today is correct because date_deadline is a Date and is meant to be
        # expressed in user TZ
        base = fields.Date.context_today(self)
        if activity_type.delay_from == 'previous_activity' and 'activity_previous_deadline' in self.env.context:
            base = fields.Date.from_string(self.env.context.get('activity_previous_deadline'))
        return base + relativedelta(**{activity_type.delay_unit: activity_type.delay_count})

    @api.onchange('recommended_activity_type_id')
    def _onchange_recommended_activity_type_id(self):
        if self.recommended_activity_type_id:
            self.activity_type_id = self.recommended_activity_type_id

    def _filter_access_rules(self, operation):
        # write / unlink: valid for creator / assigned
        if operation in ('write', 'unlink'):
            valid = super(MailActivity, self)._filter_access_rules(operation)
            if valid and valid == self:
                return self
        else:
            valid = self.env[self._name]
        return self._filter_access_rules_remaining(valid, operation, '_filter_access_rules')

    def _filter_access_rules_python(self, operation):
        # write / unlink: valid for creator / assigned
        if operation in ('write', 'unlink'):
            valid = super(MailActivity, self)._filter_access_rules_python(operation)
            if valid and valid == self:
                return self
        else:
            valid = self.env[self._name]
        return self._filter_access_rules_remaining(valid, operation, '_filter_access_rules_python')

    def _filter_access_rules_remaining(self, valid, operation, filter_access_rules_method):
        """ Return the subset of ``self`` for which ``operation`` is allowed.
        A custom implementation is done on activities as this document has some
        access rules and is based on related document for activities that are
        not covered by those rules.

        Access on activities are the following :

          * create: (``mail_post_access`` or write) right on related documents;
          * read: read rights on related documents;
          * write: access rule OR
                   (``mail_post_access`` or write) rights on related documents);
          * unlink: access rule OR
                    (``mail_post_access`` or write) rights on related documents);
        """
        # compute remaining for hand-tailored rules
        remaining = self - valid
        remaining_sudo = remaining.sudo()

        # fall back on related document access right checks. Use the same as defined for mail.thread
        # if available; otherwise fall back on read for read, write for other operations.
        activity_to_documents = dict()
        for activity in remaining_sudo:
            # write / unlink: if not updating self or assigned, limit to automated activities to avoid
            # updating other people's activities. As unlinking a document bypasses access rights checks
            # on related activities this will not prevent people from deleting documents with activities
            # create / read: just check rights on related document
            activity_to_documents.setdefault(activity.res_model, list()).append(activity.res_id)
        for doc_model, doc_ids in activity_to_documents.items():
            if hasattr(self.env[doc_model], '_mail_post_access'):
                doc_operation = self.env[doc_model]._mail_post_access
            elif operation == 'read':
                doc_operation = 'read'
            else:
                doc_operation = 'write'
            right = self.env[doc_model].check_access_rights(doc_operation, raise_exception=False)
            if right:
                valid_doc_ids = getattr(self.env[doc_model].browse(doc_ids), filter_access_rules_method)(doc_operation)
                valid += remaining.filtered(lambda activity: activity.res_model == doc_model and activity.res_id in valid_doc_ids.ids)

        return valid

    def _check_access_assignation(self):
        """ Check assigned user (user_id field) has access to the document. Purpose
        is to allow assigned user to handle their activities. For that purpose
        assigned user should be able to at least read the document. We therefore
        raise an UserError if the assigned user has no access to the document. """
        for activity in self:
            model = self.env[activity.res_model].with_user(activity.user_id).with_context(allowed_company_ids=activity.user_id.company_ids.ids)
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

    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    @api.model
    def create(self, values):
        activity = super(MailActivity, self).create(values)
        need_sudo = False
        try:  # in multicompany, reading the partner might break
            partner_id = activity.user_id.partner_id.id
        except exceptions.AccessError:
            need_sudo = True
            partner_id = activity.user_id.sudo().partner_id.id

        # send a notification to assigned user; in case of manually done activity also check
        # target has rights on document otherwise we prevent its creation. Automated activities
        # are checked since they are integrated into business flows that should not crash.
        if activity.user_id != self.env.user:
            if not activity.automated:
                activity._check_access_assignation()
            if not self.env.context.get('mail_activity_quick_update', False):
                if need_sudo:
                    activity.sudo().action_notify()
                else:
                    activity.action_notify()

        self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[partner_id])
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                {'type': 'activity_updated', 'activity_created': True})
        return activity

    def write(self, values):
        if values.get('user_id'):
            user_changes = self.filtered(lambda activity: activity.user_id.id != values.get('user_id'))
            pre_responsibles = user_changes.mapped('user_id.partner_id')
        res = super(MailActivity, self).write(values)

        if values.get('user_id'):
            if values['user_id'] != self.env.uid:
                to_check = user_changes.filtered(lambda act: not act.automated)
                to_check._check_access_assignation()
                if not self.env.context.get('mail_activity_quick_update', False):
                    user_changes.action_notify()
            for activity in user_changes:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])
                if activity.date_deadline <= fields.Date.today():
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                        {'type': 'activity_updated', 'activity_created': True})
            for activity in user_changes:
                if activity.date_deadline <= fields.Date.today():
                    for partner in pre_responsibles:
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner', partner.id),
                            {'type': 'activity_updated', 'activity_deleted': True})
        return res

    def unlink(self):
        for activity in self:
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(MailActivity, self).unlink()

    def name_get(self):
        res = []
        for record in self:
            name = record.summary or record.activity_type_id.display_name
            res.append((record.id, name))
        return res

    # ------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------

    def action_notify(self):
        if not self:
            return
        original_context = self.env.context
        body_template = self.env.ref('mail.message_activity_assigned')
        for activity in self:
            if activity.user_id.lang:
                # Send the notification in the assigned user's language
                self = self.with_context(lang=activity.user_id.lang)
                body_template = body_template.with_context(lang=activity.user_id.lang)
                activity = activity.with_context(lang=activity.user_id.lang)
            model_description = self.env['ir.model']._get(activity.res_model).display_name
            body = body_template._render(
                dict(
                    activity=activity,
                    model_description=model_description,
                    access_link=self.env['mail.thread']._notify_get_action_link('view', model=activity.res_model, res_id=activity.res_id),
                ),
                engine='ir.qweb',
                minimal_qcontext=True
            )
            record = self.env[activity.res_model].browse(activity.res_id)
            if activity.user_id:
                record.message_notify(
                    partner_ids=activity.user_id.partner_id.ids,
                    body=body,
                    subject=_('%(activity_name)s: %(summary)s assigned to you',
                        activity_name=activity.res_name,
                        summary=activity.summary or activity.activity_type_id.name),
                    record_name=activity.res_name,
                    model_description=model_description,
                    email_layout_xmlid='mail.mail_notification_light',
                )
            body_template = body_template.with_context(original_context)
            self = self.with_context(original_context)

    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        messages, next_activities = self._action_done()
        return messages.ids and messages.ids[0] or False

    def action_feedback(self, feedback=False, attachment_ids=None):
        self = self.with_context(clean_context(self.env.context))
        messages, next_activities = self._action_done(feedback=feedback, attachment_ids=attachment_ids)
        return messages.ids and messages.ids[0] or False

    def action_done_schedule_next(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback_schedule_next()

    def action_feedback_schedule_next(self, feedback=False):
        ctx = dict(
            clean_context(self.env.context),
            default_previous_activity_type_id=self.activity_type_id.id,
            activity_previous_deadline=self.date_deadline,
            default_res_id=self.res_id,
            default_res_model=self.res_model,
        )
        messages, next_activities = self._action_done(feedback=feedback)  # will unlink activity, dont access self after that
        if next_activities:
            return False
        return {
            'name': _('Schedule an Activity'),
            'context': ctx,
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def _action_done(self, feedback=False, attachment_ids=None):
        """ Private implementation of marking activity as done: posting a message, deleting activity
            (since done), and eventually create the automatical next activity (depending on config).
            :param feedback: optional feedback from user when marking activity as done
            :param attachment_ids: list of ir.attachment ids to attach to the posted mail.message
            :returns (messages, activities) where
                - messages is a recordset of posted mail.message
                - activities is a recordset of mail.activity of forced automically created activities
        """
        # marking as 'done'
        messages = self.env['mail.message']
        next_activities_values = []

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
            # extract value to generate next activities
            if activity.force_next:
                Activity = self.env['mail.activity'].with_context(activity_previous_deadline=activity.date_deadline)  # context key is required in the onchange to set deadline
                vals = Activity.default_get(Activity.fields_get())

                vals.update({
                    'previous_activity_type_id': activity.activity_type_id.id,
                    'res_id': activity.res_id,
                    'res_model': activity.res_model,
                    'res_model_id': self.env['ir.model']._get(activity.res_model).id,
                })
                virtual_activity = Activity.new(vals)
                virtual_activity._onchange_previous_activity_type_id()
                virtual_activity._onchange_activity_type_id()
                next_activities_values.append(virtual_activity._convert_to_write(virtual_activity._cache))

            # post message on activity, before deleting it
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={
                    'activity': activity,
                    'feedback': feedback,
                    'display_assignee': activity.user_id != self.env.user
                },
                subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                mail_activity_type_id=activity.activity_type_id.id,
                attachment_ids=[(4, attachment_id) for attachment_id in attachment_ids] if attachment_ids else [],
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
            messages |= activity_message

        next_activities = self.env['mail.activity'].create(next_activities_values)
        self.unlink()  # will unlink activity, dont access `self` after that

        return messages, next_activities

    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

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
        res_id_to_deadline = {}
        activity_data = defaultdict(dict)
        for group in grouped_activities:
            res_id = group['res_id']
            activity_type_id = (group.get('activity_type_id') or (False, False))[0]
            res_id_to_deadline[res_id] = group['date_deadline'] if (res_id not in res_id_to_deadline or group['date_deadline'] < res_id_to_deadline[res_id]) else res_id_to_deadline[res_id]
            state = self._compute_state_from_date(group['date_deadline'], self.user_id.sudo().tz)
            activity_data[res_id][activity_type_id] = {
                'count': group['__count'],
                'ids': group['ids'],
                'state': state,
                'o_closest_deadline': group['date_deadline'],
            }
        activity_type_infos = []
        activity_type_ids = self.env['mail.activity.type'].search(['|', ('res_model_id.model', '=', res_model), ('res_model_id', '=', False)])
        for elem in sorted(activity_type_ids, key=lambda item: item.sequence):
            mail_template_info = []
            for mail_template_id in elem.mail_template_ids:
                mail_template_info.append({"id": mail_template_id.id, "name": mail_template_id.name})
            activity_type_infos.append([elem.id, elem.name, mail_template_info])

        return {
            'activity_types': activity_type_infos,
            'activity_res_ids': sorted(res_id_to_deadline, key=lambda item: res_id_to_deadline[item]),
            'grouped_activities': activity_data,
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
    Just include field activity_ids in the div.oe-chatter to use it.

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

    def _default_activity_type(self):
        """Define a default fallback activity type when requested xml id wasn't found.

        Can be overriden to specify the default activity type of a model.
        It is only called in in activity_schedule() for now.
        """
        return self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False) \
            or self.env['mail.activity.type'].search([('res_model', '=', self._name)], limit=1) \
            or self.env['mail.activity.type'].search([('res_model_id', '=', False)], limit=1)

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user",)
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
    activity_type_icon = fields.Char('Activity Type Icon', related='activity_ids.icon')
    activity_date_deadline = fields.Date(
        'Next Activity Deadline',
        compute='_compute_activity_date_deadline', search='_search_activity_date_deadline',
        compute_sudo=False, readonly=True, store=False,
        groups="base.group_user")
    my_activity_date_deadline = fields.Date(
        'My Activity Deadline',
        compute='_compute_my_activity_date_deadline', search='_search_my_activity_date_deadline',
        compute_sudo=False, readonly=True, groups="base.group_user")
    activity_summary = fields.Char(
        'Next Activity Summary',
        related='activity_ids.summary', readonly=False,
        search='_search_activity_summary',
        groups="base.group_user",)
    activity_exception_decoration = fields.Selection([
        ('warning', 'Alert'),
        ('danger', 'Error')],
        compute='_compute_activity_exception_type',
        search='_search_activity_exception_decoration',
        help="Type of the exception activity on record.")
    activity_exception_icon = fields.Char('Icon', help="Icon to indicate an exception activity.",
        compute='_compute_activity_exception_type')

    @api.depends('activity_ids.activity_type_id.decoration_type', 'activity_ids.activity_type_id.icon')
    def _compute_activity_exception_type(self):
        # prefetch all activity types for all activities, this will avoid any query in loops
        self.mapped('activity_ids.activity_type_id.decoration_type')

        for record in self:
            activity_type_ids = record.activity_ids.mapped('activity_type_id')
            exception_activity_type_id = False
            for activity_type_id in activity_type_ids:
                if activity_type_id.decoration_type == 'danger':
                    exception_activity_type_id = activity_type_id
                    break
                if activity_type_id.decoration_type == 'warning':
                    exception_activity_type_id = activity_type_id
            record.activity_exception_decoration = exception_activity_type_id and exception_activity_type_id.decoration_type
            record.activity_exception_icon = exception_activity_type_id and exception_activity_type_id.icon

    def _search_activity_exception_decoration(self, operator, operand):
        return [('activity_ids.activity_type_id.decoration_type', operator, operand)]

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
            else:
                record.activity_state = False

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

    @api.depends('activity_ids.date_deadline', 'activity_ids.user_id')
    @api.depends_context('uid')
    def _compute_my_activity_date_deadline(self):
        for record in self:
            record.my_activity_date_deadline = next((
                activity.date_deadline
                for activity in record.activity_ids
                if activity.user_id.id == record.env.uid
            ), False)

    def _search_my_activity_date_deadline(self, operator, operand):
        activity_ids = self.env['mail.activity']._search([
            ('date_deadline', operator, operand),
            ('res_model', '=', self._name),
            ('user_id', '=', self.env.user.id)
        ])
        return [('activity_ids', 'in', activity_ids)]

    def write(self, vals):
        # Delete activities of archived record.
        if 'active' in vals and vals['active'] is False:
            self.env['mail.activity'].sudo().search(
                [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
            ).unlink()
        return super(MailActivityMixin, self).write(vals)

    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result

    def _read_progress_bar(self, domain, group_by, progress_bar):
        group_by_fname = group_by.partition(':')[0]
        if not (progress_bar['field'] == 'activity_state' and self._fields[group_by_fname].store):
            return super()._read_progress_bar(domain, group_by, progress_bar)

        # optimization for 'activity_state'

        # explicitly check access rights, since we bypass the ORM
        self.check_access_rights('read')
        self._flush_search(domain, fields=[group_by_fname], order='id')
        self.env['mail.activity'].flush(['res_model', 'res_id', 'user_id', 'date_deadline'])

        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        gb = group_by.partition(':')[0]
        annotated_groupbys = [
            self._read_group_process_groupby(gb, query)
            for gb in [group_by, 'activity_state']
        ]
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}
        for gb in annotated_groupbys:
            if gb['field'] == 'activity_state':
                gb['qualified_field'] = '"_last_activity_state"."activity_state"'
        groupby_terms, orderby_terms = self._read_group_prepare('activity_state', [], annotated_groupbys, query)
        select_terms = [
            '%s as "%s"' % (gb['qualified_field'], gb['groupby'])
            for gb in annotated_groupbys
        ]
        from_clause, where_clause, where_params = query.get_sql()
        tz = self._context.get('tz') or self.env.user.tz or 'UTC'
        select_query = """
            SELECT 1 AS id, count(*) AS "__count", {fields}
            FROM {from_clause}
            JOIN (
                SELECT res_id,
                CASE
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) > 0 THEN 'planned'
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) < 0 THEN 'overdue'
                    WHEN min(date_deadline - (now() AT TIME ZONE COALESCE(res_partner.tz, %s))::date) = 0 THEN 'today'
                    ELSE null
                END AS activity_state
                FROM mail_activity
                JOIN res_users ON (res_users.id = mail_activity.user_id)
                JOIN res_partner ON (res_partner.id = res_users.partner_id)
                WHERE res_model = '{model}'
                GROUP BY res_id
            ) AS "_last_activity_state" ON ("{table}".id = "_last_activity_state".res_id)
            WHERE {where_clause}
            GROUP BY {group_by}
        """.format(
            fields=', '.join(select_terms),
            from_clause=from_clause,
            model=self._name,
            table=self._table,
            where_clause=where_clause or '1=1',
            group_by=', '.join(groupby_terms),
        )
        self.env.cr.execute(select_query, [tz] * 3 + where_params)
        fetched_data = self.env.cr.dictfetchall()
        self._read_group_resolve_many2one_fields(fetched_data, annotated_groupbys)
        data = [
            {key: self._read_group_prepare_data(key, val, groupby_dict)
             for key, val in row.items()}
            for row in fetched_data
        ]
        return [
            self._read_group_format_result(vals, annotated_groupbys, [group_by], domain)
            for vals in data
        ]

    def toggle_active(self):
        """ Before archiving the record we should also remove its ongoing
        activities. Otherwise they stay in the systray and concerning archived
        records it makes no sense. """
        record_to_deactivate = self.filtered(lambda rec: rec[rec._active_name])
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

    def activity_search(self, act_type_xmlids='', user_id=None, additional_domain=None):
        """ Search automated activities on current record set, given a list of activity
        types xml IDs. It is useful when dealing with specific types involved in automatic
        activities management.

        :param act_type_xmlids: list of activity types xml IDs
        :param user_id: if set, restrict to activities of that user_id;
        :param additional_domain: if set, filter on that domain;
        """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [type_id for type_id in (Data.xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids) if type_id]
        if not any(activity_types_ids):
            return False

        domain = [
            '&', '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('automated', '=', True),
            ('activity_type_id', 'in', activity_types_ids)
        ]

        if user_id:
            domain = expression.AND([domain, [('user_id', '=', user_id)]])
        if additional_domain:
            domain = expression.AND([domain, additional_domain])

        return self.env['mail.activity'].search(domain)

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
            activity_type = self.env.ref(act_type_xmlid, raise_if_not_found=False) or self._default_activity_type()
        else:
            activity_type_id = act_values.get('activity_type_id', False)
            activity_type = activity_type_id and self.env['mail.activity.type'].sudo().browse(activity_type_id)

        model_id = self.env['ir.model']._get(self._name).id
        activities = self.env['mail.activity']
        for record in self:
            create_vals = {
                'activity_type_id': activity_type and activity_type.id,
                'summary': summary or activity_type.summary,
                'automated': True,
                'note': note or activity_type.default_description,
                'date_deadline': date_deadline,
                'res_model_id': model_id,
                'res_id': record.id,
                'user_id': act_values.get('user_id') or activity_type.default_user_id.id or self.env.uid
            }
            create_vals.update(act_values)
            activities |= self.env['mail.activity'].create(create_vals)
        return activities

    def _activity_schedule_with_view(self, act_type_xmlid='', date_deadline=None, summary='', views_or_xmlid='', render_context=None, **act_values):
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
        if isinstance(views_or_xmlid, str):
            views = self.env.ref(views_or_xmlid, raise_if_not_found=False)
        else:
            views = views_or_xmlid
        if not views:
            return
        activities = self.env['mail.activity']
        for record in self:
            render_context['object'] = record
            note = views._render(render_context, engine='ir.qweb', minimal_qcontext=True)
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
        activity_types_ids = [Data.xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        activities = self.activity_search(act_type_xmlids, user_id=user_id)
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
        activity_types_ids = [Data.xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        activities = self.activity_search(act_type_xmlids, user_id=user_id)
        if activities:
            activities.action_feedback(feedback=feedback)
        return True

    def activity_unlink(self, act_type_xmlids, user_id=None):
        """ Unlink activities, limiting to some activity types and optionally
        to a given user. """
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        Data = self.env['ir.model.data'].sudo()
        activity_types_ids = [Data.xmlid_to_res_id(xmlid, raise_if_not_found=False) for xmlid in act_type_xmlids]
        activity_types_ids = [act_type_id for act_type_id in activity_types_ids if act_type_id]
        if not any(activity_types_ids):
            return False
        self.activity_search(act_type_xmlids, user_id=user_id).unlink()
        return True
