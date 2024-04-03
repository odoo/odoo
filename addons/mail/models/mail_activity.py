# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, exceptions, fields, models, _, Command
from odoo.osv import expression
from odoo.tools import is_html_empty
from odoo.tools.misc import clean_context, get_lang


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
        res = super(MailActivity, self).default_get(fields)
        if not fields or 'res_model_id' in fields and res.get('res_model'):
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
        index=True, related='res_model_id.model', compute_sudo=True, store=True, readonly=True)
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
        compute='_compute_has_recommended_activities') # technical field for UX purpose
    mail_template_ids = fields.Many2many(related='activity_type_id.mail_template_ids', readonly=True)
    chaining_type = fields.Selection(related='activity_type_id.chaining_type', readonly=True)
    # access
    can_write = fields.Boolean(compute='_compute_can_write') # used to hide buttons if the current user has no access

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
        # in case of manually done activity also check target has rights on document
        # otherwise we prevent its creation. Automated activities are checked since
        # they are integrated into business flows that should not crash.
        if self.env.context.get('mail_activity_quick_update'):
            activities_to_notify = self.env['mail.activity']
        else:
            activities_to_notify = activities.filtered(lambda act: act.user_id != self.env.user)
        activities_to_notify.filtered(lambda act: not act.automated)._check_access_assignation()
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

    def read(self, fields=None, load='_classic_read'):
        """ When reading specific fields, read calls _read that manually applies ir rules
        (_apply_ir_rules), instead of calling check_access_rule.

        Meaning that our custom rules enforcing from '_filter_access_rules' and
        '_filter_access_rules_python' are bypassed in that case.
        To make sure we apply our custom security rules, we force a call to 'check_access_rule'. """

        self.check_access_rule('read')
        return super(MailActivity, self).read(fields=fields, load=load)

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
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.activity, to remove
        ids uid could not see according to our custom rules. Please refer to
        _filter_access_rules_remaining for more details about those rules.

        The method is inspired by what has been done on mail.message. """

        # Rules do not apply to administrator
        if self.env.is_superuser():
            return super(MailActivity, self)._search(
                args, offset=offset, limit=limit, order=order,
                count=count, access_rights_uid=access_rights_uid)
        # Perform a super with count as False, to have the ids, not a counter
        ids = super(MailActivity, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        # check read access rights before checking the actual rules on the given ids
        super(MailActivity, self.with_user(access_rights_uid or self._uid)).check_access_rights('read')

        self.flush_model(['res_model', 'res_id'])
        activities_to_check = []
        for sub_ids in self._cr.split_for_in_conditions(ids):
            self._cr.execute("""
                SELECT DISTINCT activity.id, activity.res_model, activity.res_id
                FROM "%s" activity
                WHERE activity.id = ANY (%%(ids)s) AND activity.res_id != 0""" % self._table, dict(ids=list(sub_ids)))
            activities_to_check += self._cr.dictfetchall()

        activity_to_documents = {}
        for activity in activities_to_check:
            activity_to_documents.setdefault(activity['res_model'], set()).add(activity['res_id'])

        allowed_ids = set()
        for doc_model, doc_ids in activity_to_documents.items():
            # fall back on related document access right checks. Use the same as defined for mail.thread
            # if available; otherwise fall back on read
            if hasattr(self.env[doc_model], '_mail_post_access'):
                doc_operation = self.env[doc_model]._mail_post_access
            else:
                doc_operation = 'read'
            DocumentModel = self.env[doc_model].with_user(access_rights_uid or self._uid)
            right = DocumentModel.check_access_rights(doc_operation, raise_exception=False)
            if right:
                valid_docs = DocumentModel.browse(doc_ids)._filter_access_rules(doc_operation)
                valid_doc_ids = set(valid_docs.ids)
                allowed_ids.update(
                    activity['id'] for activity in activities_to_check
                    if activity['res_model'] == doc_model and activity['res_id'] in valid_doc_ids)

        if count:
            return len(allowed_ids)
        else:
            # re-construct a list based on ids, because 'allowed_ids' does not keep the original order
            id_list = [id for id in ids if id in allowed_ids]
            return id_list

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ The base _read_group_raw method implementation computes a where based on a given domain
        (_where_calc) and manually applies ir rules (_apply_ir_rules).

        Meaning that our custom rules enforcing from '_filter_access_rules' and
        '_filter_access_rules_python' are bypassed in that case.

        This overrides re-uses the _search implementation to force the read group domain to allowed
        ids only, that are computed based on our custom rules (see _filter_access_rules_remaining
        for more details). """

        # Rules do not apply to administrator
        if not self.env.is_superuser():
            allowed_ids = self._search(domain, count=False)
            if allowed_ids:
                domain = expression.AND([domain, [('id', 'in', allowed_ids)]])
            else:
                # force void result if no allowed ids found
                domain = expression.AND([domain, [(0, '=', 1)]])

        return super(MailActivity, self)._read_group_raw(
            domain=domain, fields=fields, groupby=groupby, offset=offset,
            limit=limit, orderby=orderby, lazy=lazy,
        )

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
            records = self.env[model].browse(activity_data['record_ids'])
            for record, activity in zip(records, activity_data['activities']):
                # extract value to generate next activities
                if activity.chaining_type == 'trigger':
                    vals = activity.with_context(activity_previous_deadline=activity.date_deadline)._prepare_next_activity_values()
                    next_activities_values.append(vals)

                # post message on activity, before deleting it
                activity_message = record.message_post_with_view(
                    'mail.message_activity_done',
                    values={
                        'activity': activity,
                        'feedback': feedback,
                        'display_assignee': activity.user_id != self.env.user
                    },
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                    attachment_ids=[Command.link(attachment_id) for attachment_id in attachment_ids] if attachment_ids else [],
                )

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

        self.unlink()  # will unlink activity, dont access `self` after that

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
        activity_type_ids = self.env['mail.activity.type'].search(
            ['|', ('res_model', '=', res_model), ('res_model', '=', False)])
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
