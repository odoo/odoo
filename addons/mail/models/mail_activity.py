# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model_id field should be used. """
    _name = 'mail.activity.type'
    _description = 'Activity Type'
    _rec_name = 'name'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    summary = fields.Char('Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    days = fields.Integer(
        '# Days', default=0,
        help='Number of days before executing the action. It allows to plan the action deadline.')
    icon = fields.Char('Icon', help="Font awesome icon e.g. fa-tasks")
    res_model_id = fields.Many2one(
        'ir.model', 'Model', index=True,
        help='Specify a model if the activity should be specific to a model'
             'and not available when managing activities for other models.')
    next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id', 'recommended_id',
        string='Recommended Next Activities')
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id', 'activity_id',
        string='Preceding Activities')

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
        'ir.model', 'Related Document Model',
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
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]")
    icon = fields.Char('Icon', related='activity_type_id.icon')
    summary = fields.Char('Summary')
    note = fields.Html('Note')
    feedback = fields.Html('Feedback')
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.today)
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], 'State',
        compute='_compute_state')
    recommended_activity_type_id = fields.Many2one('mail.activity.type', string="Recommended Activity Type")
    previous_activity_type_id = fields.Many2one('mail.activity.type', string='Previous Activity Type')
    has_recommended_activities = fields.Boolean(
        'Next activities available',
        compute='_compute_has_recommended_activities',
        help='Technical field for UX purpose')

    @api.multi
    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(record.previous_activity_type_id.next_type_ids)

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = self.env[activity.res_model].browse(activity.res_id).name_get()[0][1]

    @api.depends('date_deadline')
    def _compute_state(self):
        today = date.today()
        for record in self.filtered(lambda activity: activity.date_deadline):
            date_deadline = fields.Date.from_string(record.date_deadline)
            diff = (date_deadline - today)
            if diff.days == 0:
                record.state = 'today'
            elif diff.days < 0:
                record.state = 'overdue'
            else:
                record.state = 'planned'

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        if self.activity_type_id:
            self.summary = self.activity_type_id.summary
            self.date_deadline = (datetime.now() + timedelta(days=self.activity_type_id.days))

    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        if self.previous_activity_type_id.next_type_ids:
            self.recommended_activity_type_id = self.previous_activity_type_id.next_type_ids[0]

    @api.onchange('recommended_activity_type_id')
    def _onchange_recommended_activity_type_id(self):
        self.activity_type_id = self.recommended_activity_type_id

    @api.model
    def create(self, values):
        activity = super(MailActivity, self).create(values)
        self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])
        return activity

    @api.multi
    def write(self, values):
        res = super(MailActivity, self).write(values)
        if values.get('user_id'):
            for activity in self:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])
        return res

    @api.multi
    def check_access_rule(self, operation):
        """ Override access rule on activities so that the following heuristic
        is performed """
        if self._uid == SUPERUSER_ID:
            super(MailActivity, self).check_access_rule(operation)
            return

        from collections import defaultdict

        self._cr.execute("""SELECT DISTINCT id, res_model, res_id FROM "%s" WHERE id = ANY (%%s)""" % self._table, (self.ids,))       
        models = defaultdict()
        for act_id, doc_model, doc_id in self._cr.fetchall():
            models.setdefault(doc_model, defaultdict()).setdefault(doc_id, list()).append(act_id)

        validated = self.env['mail.activity']
        related_operation = 'read' if operation == 'read' else 'write'
        for model, doc_to_activities in models.iteritems():
            self.env[model].check_access_rights(related_operation)
            self.env[model].browse(doc_to_activities.keys()).check_access_rule(related_operation)
            validated |= validated.browse([activity_id for activity_ids_list in doc_to_activities.values() for activity_id in activity_ids_list])

        super(MailActivity, (self - validated)).check_access_rule(operation)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # Rules do not apply to administrator
        if self._uid == SUPERUSER_ID:
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

        self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, partner_rel.res_partner_id, channel_partner.channel_id as channel_id
            FROM "%s" m
            LEFT JOIN "mail_message_res_partner_rel" partner_rel
            ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = (%%s)
            LEFT JOIN "mail_message_mail_channel_rel" channel_rel
            ON channel_rel.mail_message_id = m.id
            LEFT JOIN "mail_channel" channel
            ON channel.id = channel_rel.mail_channel_id
            LEFT JOIN "mail_channel_partner" channel_partner
            ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = (%%s)
            WHERE m.id = ANY (%%s)""" % self._table, (pid, pid, ids,))



    @api.multi
    def action_done(self, feedback=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]

        self.unlink()
        return message.ids and message.ids[0] or False

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}


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
    use it."""
    _name = 'mail.activity.mixin'
    _description = 'Activity Mixin'

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        domain=lambda self: [('res_model', '=', self._name)])
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='State',
        compute='_compute_activity_state',
        help='Status based on activities\nOverdue: Due date is already passed\n'
             'Today: Activity date is today\nPlanned: Future activities.')
    activity_user_id = fields.Many2one(
        'res.users', 'Responsible',
        related='activity_ids.user_id',
        search='_search_activity_user_id')
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id',
        search='_search_activity_type_id')
    activity_date_deadline = fields.Date(
        'Next Activity Deadline', related='activity_ids.date_deadline',
        readonly=True, store=True)  # store to enable ordering + search
    activity_summary = fields.Char(
        'Next Activity Summary', related='activity_ids.summary',
        search='_search_activity_summary')

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
    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result
