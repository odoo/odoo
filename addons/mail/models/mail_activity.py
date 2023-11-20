# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz

from collections import defaultdict, Counter
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, exceptions, fields, models, _, Command
from odoo.osv import expression
from odoo.tools import is_html_empty
from odoo.tools.misc import clean_context, get_lang, groupby

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _name = 'mail.activity'
    _description = 'Activity'
    _order = 'date_deadline ASC, id ASC'
    _rec_name = 'summary'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'res_model_id' in fields and res.get('res_model'):
            res['res_model_id'] = self.env['ir.model']._get(res['res_model']).id
        return res

    @api.model
    def _default_activity_type(self):
        default_vals = self.default_get(['res_model_id', 'res_model'])
        if not default_vals.get('res_model_id'):
            return False

        current_model = self.env["ir.model"].sudo().browse(default_vals['res_model_id']).model
        return self._default_activity_type_for_model(current_model)

    @api.model
    def _default_activity_type_for_model(self, model):
        todo_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mail_activity_data_todo', raise_if_not_found=False)
        activity_type_todo = self.env['mail.activity.type'].browse(todo_id) if todo_id else self.env['mail.activity.type']
        if activity_type_todo and activity_type_todo.active and \
                (activity_type_todo.res_model == model or not activity_type_todo.res_model):
            return activity_type_todo
        activity_type_model = self.env['mail.activity.type'].search([('res_model', '=', model)], limit=1)
        if activity_type_model:
            return activity_type_model
        activity_type_generic = self.env['mail.activity.type'].search([('res_model', '=', False)], limit=1)
        return activity_type_generic

    # owner
    res_model_id = fields.Many2one(
        'ir.model', 'Document Model',
        index=True, ondelete='cascade', required=True)
    res_model = fields.Char(
        'Related Document Model',
        index=True, related='res_model_id.model', precompute=True, store=True, readonly=True)
    res_id = fields.Many2oneReference(string='Related Document ID', index=True, model_field='res_model')
    res_name = fields.Char(
        'Document Name', compute='_compute_res_name', compute_sudo=True, store=True,
        readonly=True)
    # activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity Type',
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]", ondelete='restrict',
        default=_default_activity_type)
    activity_category = fields.Selection(related='activity_type_id.category', readonly=True)
    activity_decoration = fields.Selection(related='activity_type_id.decoration_type', readonly=True)
    icon = fields.Char('Icon', related='activity_type_id.icon', readonly=True)
    summary = fields.Char('Summary')
    note = fields.Html('Note', sanitize_style=True)
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.context_today)
    date_done = fields.Date('Done Date', compute='_compute_date_done', store=True)
    automated = fields.Boolean(
        'Automated activity', readonly=True,
        help='Indicates this activity has been created automatically and not by any user.')
    # Attachments are linked to a document through model / res_id and to the activity through this field.
    attachment_ids = fields.Many2many(
        'ir.attachment', 'activity_attachment_rel',
        'activity_id', 'attachment_id',
        string='Attachments')
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True, ondelete='cascade')
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned'),
        ('done', 'Done')], 'State',
        compute='_compute_state')
    recommended_activity_type_id = fields.Many2one('mail.activity.type', string="Recommended Activity Type")
    previous_activity_type_id = fields.Many2one('mail.activity.type', string='Previous Activity Type', readonly=True)
    has_recommended_activities = fields.Boolean(
        'Next activities available',
        compute='_compute_has_recommended_activities') # technical field for UX purpose
    mail_template_ids = fields.Many2many(related='activity_type_id.mail_template_ids', readonly=True)
    chaining_type = fields.Selection(related='activity_type_id.chaining_type', readonly=True)
    # access
    can_write = fields.Boolean(compute='_compute_can_write') # used to hide buttons if the current user has no access
    active = fields.Boolean(default=True)

    _sql_constraints = [
        # Required on a Many2one reference field is not sufficient as actually
        # writing 0 is considered as a valid value, because this is an integer field.
        # We therefore need a specific constraint check.
        ('check_res_id_is_set',
         'CHECK(res_id IS NOT NULL AND res_id !=0 )',
         'Activities have to be linked to records with a not null res_id.')
    ]

    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(record.previous_activity_type_id.suggested_next_type_ids)

    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        for record in self:
            if record.previous_activity_type_id.triggered_next_type_id:
                record.activity_type_id = record.previous_activity_type_id.triggered_next_type_id

    @api.depends('active')
    def _compute_date_done(self):
        unarchived = self.filtered('active')
        unarchived.date_done = False
        # keep earliest archive date if multi archive
        toupdate = (self - unarchived).filtered(lambda act: not act.date_done)
        toupdate.date_done = fields.Datetime.now()

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = activity.res_model and \
                self.env[activity.res_model].browse(activity.res_id).display_name

    @api.depends('active', 'date_deadline')
    def _compute_state(self):
        for record in self.filtered(lambda activity: activity.date_deadline):
            tz = record.user_id.sudo().tz
            date_deadline = record.date_deadline
            record.state = 'done' if not record.active else self._compute_state_from_date(date_deadline, tz)

    @api.model
    def _compute_state_from_date(self, date_deadline, tz=False):
        date_deadline = fields.Date.from_string(date_deadline)
        today_default = date.today()
        today = today_default
        if tz:
            today_utc = pytz.utc.localize(datetime.utcnow())
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
            if self.activity_type_id.default_note:
                self.note = self.activity_type_id.default_note

    @api.model
    def _calculate_date_deadline(self, activity_type, force_base_date=None):
        """ Compute the activity deadline given its type, the force_base_date and the context.

        The deadline is computed by adding the activity type delay to a base date defined as:
        - the force_base_date
        - or the activity_previous_deadline context value if the activity type delay_from is
          previous_activity
        - or the current date

        :param activity_type: activity type
        :param date force_base_date: if set, this force the base date for computation
        """
        if force_base_date:
            # Date.context_today is correct because date_deadline is a Date and is meant to be
            # expressed in user TZ
            base = force_base_date
        elif activity_type.delay_from == 'previous_activity' and 'activity_previous_deadline' in self.env.context:
            base = fields.Date.from_string(self.env.context.get('activity_previous_deadline'))
        else:
            base = fields.Date.context_today(self)
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
        elif operation == 'read':
            # Not in the ACL otherwise it would break the custom _search method
            valid = self.sudo().filtered_domain([('user_id', '=', self.env.uid)])
        else:
            valid = self.env[self._name]
        return self._filter_access_rules_remaining(valid, operation, '_filter_access_rules')

    def _filter_access_rules_python(self, operation):
        # write / unlink: valid for creator / assigned
        if operation in ('write', 'unlink'):
            valid = super(MailActivity, self)._filter_access_rules_python(operation)
            if valid and valid == self:
                return self
        elif operation == 'read':
            valid = self.sudo().filtered_domain([('user_id', '=', self.env.uid)])
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
            # write / unlink: As unlinking a document bypasses access rights checks on related activities
            # this will not prevent people from deleting documents with activities
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
        raise an UserError if the assigned user has no access to the document.

        .. deprecated:: 17.0
            Deprecated method, we don't check access to the underlying records anymore
            as user can new see activities without having access to the underlying records.
        """
        for model, activity_data in self._classify_by_model().items():
            # group activities / user, in order to batch the check of ACLs
            per_user = dict()
            for activity in activity_data['activities'].filtered(lambda act: act.user_id):
                if activity.user_id not in per_user:
                    per_user[activity.user_id] = activity
                else:
                    per_user[activity.user_id] += activity
            for user, activities in per_user.items():
                RecordModel = self.env[model].with_user(user).with_context(
                    allowed_company_ids=user.company_ids.ids
                )
                try:
                    RecordModel.check_access_rights('read')
                except exceptions.AccessError:
                    raise exceptions.UserError(
                        _('Assigned user %s has no access to the document and is not able to handle this activity.',
                          user.display_name))
                else:
                    try:
                        target_records = self.env[model].browse(activities.mapped('res_id'))
                        target_records.check_access_rule('read')
                    except exceptions.AccessError:
                        raise exceptions.UserError(
                            _('Assigned user %s has no access to the document and is not able to handle this activity.',
                              user.display_name))

    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        activities = super(MailActivity, self).create(vals_list)

        # find partners related to responsible users, separate readable from unreadable
        if any(user != self.env.user for user in activities.user_id):
            user_partners = activities.user_id.partner_id
            readable_user_partners = user_partners._filter_access_rules_python('read')
        else:
            readable_user_partners = self.env.user.partner_id

        # when creating activities for other: send a notification to assigned user;
        if self.env.context.get('mail_activity_quick_update'):
            activities_to_notify = self.env['mail.activity']
        else:
            activities_to_notify = activities.filtered(lambda act: act.user_id != self.env.user)
        if activities_to_notify:
            to_sudo = activities_to_notify.filtered(lambda act: act.user_id.partner_id not in readable_user_partners)
            other = activities_to_notify - to_sudo
            to_sudo.sudo().action_notify()
            other.action_notify()

        # subscribe (batch by model and user to speedup)
        for model, activity_data in activities._classify_by_model().items():
            per_user = dict()
            for activity in activity_data['activities'].filtered(lambda act: act.user_id):
                if activity.user_id not in per_user:
                    per_user[activity.user_id] = [activity.res_id]
                else:
                    per_user[activity.user_id].append(activity.res_id)
            for user, res_ids in per_user.items():
                pids = user.partner_id.ids if user.partner_id in readable_user_partners else user.sudo().partner_id.ids
                self.env[model].browse(res_ids).message_subscribe(partner_ids=pids)

        # send notifications about activity creation
        todo_activities = activities.filtered(lambda act: act.date_deadline <= fields.Date.today())
        if todo_activities:
            self.env['bus.bus']._sendmany([
                (activity.user_id.partner_id, 'mail.activity/updated', {'activity_created': True})
                for activity in todo_activities
            ])
        return activities

    def write(self, values):
        if values.get('user_id'):
            user_changes = self.filtered(lambda activity: activity.user_id.id != values.get('user_id'))
            pre_responsibles = user_changes.mapped('user_id.partner_id')
        res = super(MailActivity, self).write(values)

        if values.get('user_id'):
            if values['user_id'] != self.env.uid:
                if not self.env.context.get('mail_activity_quick_update', False):
                    user_changes.action_notify()
            for activity in user_changes:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])

            # send bus notifications
            todo_activities = user_changes.filtered(lambda act: act.date_deadline <= fields.Date.today())
            if todo_activities:
                self.env['bus.bus']._sendmany([
                    [partner, 'mail.activity/updated', {'activity_created': True}]
                    for partner in todo_activities.user_id.partner_id
                ])
                self.env['bus.bus']._sendmany([
                    [partner, 'mail.activity/updated', {'activity_deleted': True}]
                    for partner in pre_responsibles
                ])
        return res

    def unlink(self):
        todo_activities = self.filtered(lambda act: act.date_deadline <= fields.Date.today())
        if todo_activities:
            self.env['bus.bus']._sendmany([
                [partner, 'mail.activity/updated', {'activity_deleted': True}]
                for partner in todo_activities.user_id.partner_id
            ])
        return super(MailActivity, self).unlink()

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """ Override that adds specific access rights of mail.activity, to remove
        ids uid could not see according to our custom rules. Please refer to
        _filter_access_rules_remaining for more details about those rules.

        The method is inspired by what has been done on mail.message. """

        # Rules do not apply to administrator
        if self.env.is_superuser():
            return super()._search(domain, offset, limit, order, access_rights_uid)

        # retrieve activities and their corresponding res_model, res_id
        self.flush_model(['res_model', 'res_id'])
        query = super()._search(domain, offset, limit, order, access_rights_uid)
        query_str, params = query.select(
            f'"{self._table}"."id"',
            f'"{self._table}"."res_model"',
            f'"{self._table}"."res_id"',
            f'"{self._table}"."user_id"',
        )
        self.env.cr.execute(query_str, params)
        rows = self.env.cr.fetchall()

        # group res_ids by model, and determine accessible records
        # Note: the user can read all activities assigned to him (see at the end of the method)
        model_ids = defaultdict(set)
        for __, res_model, res_id, user_id in rows:
            if user_id != self.env.uid:
                model_ids[res_model].add(res_id)

        allowed_ids = defaultdict(set)
        for res_model, res_ids in model_ids.items():
            records = self.env[res_model].with_user(access_rights_uid or self._uid).browse(res_ids)
            # fall back on related document access right checks. Use the same as defined for mail.thread
            # if available; otherwise fall back on read
            operation = getattr(records, '_mail_post_access', 'read')
            if records.check_access_rights(operation, raise_exception=False):
                allowed_ids[res_model] = set(records._filter_access_rules(operation)._ids)

        activities = self.browse(
            id_
            for id_, res_model, res_id, user_id in rows
            if user_id == self.env.uid or res_id in allowed_ids[res_model]
        )
        return activities._as_query(order)

    @api.depends('summary', 'activity_type_id')
    def _compute_display_name(self):
        for record in self:
            name = record.summary or record.activity_type_id.display_name
            record.display_name = name

    # ------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------

    def action_notify(self):
        if not self:
            return
        for activity in self:
            if activity.user_id.lang:
                # Send the notification in the assigned user's language
                activity = activity.with_context(lang=activity.user_id.lang)

            model_description = activity.env['ir.model']._get(activity.res_model).display_name
            body = activity.env['ir.qweb']._render(
                'mail.message_activity_assigned',
                {
                    'activity': activity,
                    'model_description': model_description,
                    'is_html_empty': is_html_empty,
                },
                minimal_qcontext=True
            )
            record = activity.env[activity.res_model].browse(activity.res_id)
            if activity.user_id:
                record.message_notify(
                    partner_ids=activity.user_id.partner_id.ids,
                    body=body,
                    record_name=activity.res_name,
                    model_description=model_description,
                    email_layout_xmlid='mail.mail_notification_layout',
                    subject=_('"%(activity_name)s: %(summary)s" assigned to you',
                              activity_name=activity.res_name,
                              summary=activity.summary or activity.activity_type_id.name),
                    subtitles=[_('Activity: %s', activity.activity_type_id.name),
                               _('Deadline: %s', activity.date_deadline.strftime(get_lang(activity.env).date_format))]
                )

    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback()

    def action_feedback(self, feedback=False, attachment_ids=None):
        messages, _next_activities = self.with_context(
            clean_context(self.env.context)
        )._action_done(feedback=feedback, attachment_ids=attachment_ids)
        return messages[0].id if messages else False

    def action_done_schedule_next(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback_schedule_next()

    def action_feedback_schedule_next(self, feedback=False, attachment_ids=None):
        ctx = dict(
            clean_context(self.env.context),
            default_previous_activity_type_id=self.activity_type_id.id,
            activity_previous_deadline=self.date_deadline,
            default_res_id=self.res_id,
            default_res_model=self.res_model,
        )
        _messages, next_activities = self._action_done(feedback=feedback, attachment_ids=attachment_ids)  # will unlink activity, dont access self after that
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

        for model, activity_data in self._classify_by_model().items():
            # Allow user without access to the record to "mark as done" activities assigned to them. At the end of the
            # method, the activity is unlinked or archived which ensure the user has enough right on the activities.
            records_sudo = self.env[model].sudo().browse(activity_data['record_ids'])
            for record_sudo, activity in zip(records_sudo, activity_data['activities']):
                # extract value to generate next activities
                if activity.chaining_type == 'trigger':
                    vals = activity.with_context(activity_previous_deadline=activity.date_deadline)._prepare_next_activity_values()
                    next_activities_values.append(vals)

                # post message on activity, before deleting it
                activity_message = record_sudo.message_post_with_source(
                    'mail.message_activity_done',
                    attachment_ids=attachment_ids,
                    author_id=self.env.user.partner_id.id,
                    render_values={
                        'activity': activity,
                        'feedback': feedback,
                        'display_assignee': activity.user_id != self.env.user
                    },
                    mail_activity_type_id=activity.activity_type_id.id,
                    subtype_xmlid='mail.mt_activities',
                )
                if activity.activity_type_id.keep_done:
                    attachment_ids = (attachment_ids or []) + activity_attachments.get(activity.id, [])
                    if attachment_ids:
                        activity.attachment_ids = attachment_ids

                # Moving the attachments in the message
                # TODO: Fix void res_id on attachment when you create an activity with an image
                # directly, see route /web_editor/attachment/add
                if activity_attachments[activity.id]:
                    message_attachments = self.env['ir.attachment'].browse(activity_attachments[activity.id])
                    if message_attachments:
                        message_attachments.write({
                            'res_id': activity_message.id,
                            'res_model': activity_message._name,
                        })
                        activity_message.attachment_ids = message_attachments
                messages += activity_message

        next_activities = self.env['mail.activity']
        if next_activities_values:
            next_activities = self.env['mail.activity'].create(next_activities_values)

        activity_to_keep = self.filtered('activity_type_id.keep_done')
        activity_to_keep.action_archive()
        (self - activity_to_keep).unlink()  # will unlink activity, dont access `self` after that

        return messages, next_activities

    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_open_document(self):
        """ Opens the related record based on the model and ID """
        self.ensure_one()
        return {
            'res_id': self.res_id,
            'res_model': self.res_model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }

    def activity_format(self):
        activities = self.read()
        self.mail_template_ids.fetch(['name'])
        self.attachment_ids.fetch(['name'])
        for record, activity in zip(self, activities):
            activity['mail_template_ids'] = [
                {'id': mail_template.id, 'name': mail_template.name}
                for mail_template in record.mail_template_ids
            ]
            activity['attachment_ids'] = [
                {'id': attachment.id, 'name': attachment.name}
                for attachment in record.attachment_ids
            ]
        return activities

    @api.model
    def get_activity_data(self, res_model, domain, limit=None, offset=0, fetch_done=False):
        """ Get aggregate data about records and their activities.

        The goal is to fetch and compute aggregated data about records and their
        activities to display them in the activity views and the chatter. For example,
        the activity view displays it as a table with columns and rows being respectively
        the activity_types and the activity_res_ids, and the grouped_activities being the
        table entries with the aggregated data.

        :param str res_model: model of the records to fetch
        :param list domain: record search domain
        :param int limit: maximum number of records to fetch
        :param int offset: offset of the first record to fetch
        :param bool fetch_done: determines if "done" activities are integrated in the
            aggregated data or not.
        :return dict: {'activity_types': dict of activity type info
                            {id: int, name: str, mail_template: list of {id:int, name:str},
                            keep_done: bool}
                       'activity_res_ids': list<int> of record id ordered by closest date
                            (deadline for ongoing activities, and done date for done activities)
                       'grouped_activities': dict<dict>
                            res_id -> activity_type_id -> aggregated info as:
                                count_by_state dict: mapping state to count (ex.: 'planned': 2)
                                ids list: activity ids for the res_id and activity_type_id
                                reporting_date str: aggregated date of the related activities as
                                    oldest deadline of ongoing activities if there are any
                                    or most recent date done of completed activities
                                state dict: aggregated state of the related activities
                                user_assigned_ids list: activity responsible id ordered
                                    by closest deadline of the related activities
                                attachments_info: dict with information about the attachments
                                    {'count': int, 'most_recent_id': int, 'most_recent_name': str}
                       }
        """
        user_tz = self.user_id.sudo().tz
        DocModel = self.env[res_model]
        Activity = self.env['mail.activity']

        # 1. Retrieve all ongoing and completed activities according to the parameters
        activity_types = self.env['mail.activity.type'].search([('res_model', 'in', (res_model, False))])
        fetch_done = fetch_done and activity_types.filtered('keep_done')
        activity_domain = [('res_model', '=', res_model)]
        is_filtered = domain or limit or offset
        if is_filtered:
            activity_domain.append(('res_id', 'in', DocModel._search(domain or [], offset, limit) if is_filtered else []))
        all_activities = Activity.with_context(active_test=not fetch_done).search(
            activity_domain, order='date_done DESC, date_deadline ASC')
        all_ongoing = all_activities.filtered('active')
        all_completed = all_activities.filtered(lambda act: not act.active)

        # 2. Get attachment of completed activities
        if all_completed:
            attachment_ids = all_completed.attachment_ids.ids
            attachments_by_id = {
                a['id']: a
                for a in self.env['ir.attachment'].search_read([['id', 'in', attachment_ids]], ['create_date', 'name'])
            } if attachment_ids else {}
        else:
            attachments_by_id = {}

        # 3. Group activities per records and activity type
        grouped_completed = {group: Activity.browse([v.id for v in values])
                             for group, values in groupby(all_completed, key=lambda a: (a.res_id, a.activity_type_id))}
        grouped_ongoing = {group: Activity.browse([v.id for v in values])
                           for group, values in groupby(all_ongoing, key=lambda a: (a.res_id, a.activity_type_id))}

        # 4. Filter out unreadable records
        res_id_type_tuples = grouped_ongoing.keys() | grouped_completed.keys()
        if not is_filtered:
            filtered = set(DocModel.search([('id', 'in', [r[0] for r in res_id_type_tuples])]).ids)
            res_id_type_tuples = list(filter(lambda r: r[0] in filtered, res_id_type_tuples))

        # 5. Format data
        res_id_to_date_done = {}
        res_id_to_deadline = {}
        grouped_activities = defaultdict(dict)
        for res_id_tuple in res_id_type_tuples:
            res_id, activity_type_id = res_id_tuple
            ongoing = grouped_ongoing.get(res_id_tuple, Activity)
            completed = grouped_completed.get(res_id_tuple, Activity)
            activities = ongoing | completed

            # As completed is sorted on date_done DESC, we take here the max date_done
            date_done = completed and completed[0].date_done
            # As ongoing is sorted on date_deadline ASC, we take here the min date_deadline
            date_deadline = ongoing and ongoing[0].date_deadline
            if date_deadline and (res_id not in res_id_to_deadline or date_deadline < res_id_to_deadline[res_id]):
                res_id_to_deadline[res_id] = date_deadline
            if date_done and (res_id not in res_id_to_date_done or date_done > res_id_to_date_done[res_id]):
                res_id_to_date_done[res_id] = date_done
            # As ongoing is sorted on date_deadline, we get assignees on activity with oldest deadline first
            user_assigned_ids = ongoing.user_id.ids
            attachments = [attachments_by_id[attach.id] for attach in completed.attachment_ids]
            grouped_activities[res_id][activity_type_id.id] = {
                'count_by_state': dict(Counter(
                    self._compute_state_from_date(act.date_deadline, user_tz) if act.active else 'done'
                    for act in activities)),
                'ids': activities.ids,
                'reporting_date': ongoing and date_deadline or date_done or None,
                'state': self._compute_state_from_date(date_deadline, user_tz) if ongoing else 'done',
                'user_assigned_ids': user_assigned_ids,
            }
            if attachments:
                most_recent_attachment = max(attachments, key=lambda a: (a['create_date'], a['id']))
                grouped_activities[res_id][activity_type_id.id]['attachments_info'] = {
                    'most_recent_id': most_recent_attachment['id'],
                    'most_recent_name': most_recent_attachment['name'],
                    'count': len(attachments),
                }

        # Get record ids ordered by oldest deadline (urgent one first)
        ongoing_res_ids = sorted(res_id_to_deadline, key=lambda item: res_id_to_deadline[item])
        # Get record ids with only completed activities ordered by date done reversed (most recently done first)
        completed_res_ids = [
            res_id for res_id in sorted(
                res_id_to_date_done, key=lambda item: res_id_to_date_done[item], reverse=True
            ) if res_id not in res_id_to_deadline
        ]
        return {
            'activity_res_ids': ongoing_res_ids + completed_res_ids,
            'activity_types': [
                {
                    'id': activity_type.id,
                    'keep_done': activity_type.keep_done,
                    'name': activity_type.name,
                    'template_ids': [
                        {'id': mail_template_id.id, 'name': mail_template_id.name}
                        for mail_template_id in activity_type.mail_template_ids
                    ],
                }
                for activity_type in activity_types
            ],
            'grouped_activities': grouped_activities,
        }

    # ----------------------------------------------------------------------
    # TOOLS
    # ----------------------------------------------------------------------

    def _classify_by_model(self):
        """ To ease batch computation of various activities related methods they
        are classified by model. Activities not linked to a valid record through
        res_model / res_id are ignored.

        :return dict: for each model having at least one activity in self, have
          a sub-dict containing
            * activities: activities related to that model;
            * record IDs: record linked to the activities of that model, in same
              order;
        """
        data_by_model = {}
        for activity in self.filtered(lambda act: act.res_model and act.res_id):
            if activity.res_model not in data_by_model:
                data_by_model[activity.res_model] = {
                    'activities': self.env['mail.activity'],
                    'record_ids': [],
                }
            data_by_model[activity.res_model]['activities'] += activity
            data_by_model[activity.res_model]['record_ids'].append(activity.res_id)
        return data_by_model

    def _prepare_next_activity_values(self):
        """ Prepare the next activity values based on the current activity record and applies _onchange methods
        :returns a dict of values for the new activity
        """
        self.ensure_one()
        vals = self.default_get(self.fields_get())

        vals.update({
            'previous_activity_type_id': self.activity_type_id.id,
            'res_id': self.res_id,
            'res_model': self.res_model,
            'res_model_id': self.env['ir.model']._get(self.res_model).id,
        })
        virtual_activity = self.new(vals)
        virtual_activity._onchange_previous_activity_type_id()
        virtual_activity._onchange_activity_type_id()
        return virtual_activity._convert_to_write(virtual_activity._cache)

    @api.autovacuum
    def _gc_delete_old_overdue_activities(self):
        """
        Delete old overdue activities
        - If the config_parameter is deleted or 0, the user doesn't want to run this gc routine
        - If the config_parameter is set to a negative number, it's an invalid value, we skip the gc routine
        - If the config_parameter is set to a positive number, we delete only overdue activities which deadline is older than X years
        """
        year_threshold = int(self.env['ir.config_parameter'].sudo().get_param('mail.activity.gc.delete_overdue_years', 0))
        if year_threshold == 0:
            _logger.warning("The ir.config_parameter 'mail.activity.gc.delete_overdue_years' is missing or set to 0. Skipping gc routine.")
            return
        if year_threshold < 0:
            _logger.warning("The ir.config_parameter 'mail.activity.gc.delete_overdue_years' is set to a negative number "
                            "which is invalid. Skipping gc routine.")
            return
        deadline_threshold_dt = datetime.now() - relativedelta(years=year_threshold)
        old_overdue_activities = self.env['mail.activity'].search([('date_deadline', '<', deadline_threshold_dt)], limit=10_000)
        old_overdue_activities.unlink()
