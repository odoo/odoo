# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError
from odoo.tools.safe_eval import safe_eval


class ProjectIssue(models.Model):
    _name = "project.issue"
    _description = "Project Issue"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "priority desc, create_date desc"
    _mail_post_access = 'read'

    @api.model
    def _get_default_stage_id(self):
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, [('fold', '=', False)])

    name = fields.Char(string='Issue', required=True)
    active = fields.Boolean(default=True)
    days_since_creation = fields.Integer(compute='_compute_inactivity_days', string='Days since creation date',
                                         help="Difference in days between creation date and current date")
    date_deadline = fields.Date(string='Deadline')
    partner_id = fields.Many2one('res.partner', string='Contact', index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    description = fields.Text('Private Note')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('blocked', 'Red'),
        ('done', 'Green')], string='Kanban State',
        copy=False, default='normal', required=True, track_visibility='onchange',
        help="An Issue's kanban state indicates special situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the progress of this issue\n"
             " * Green indicates the issue is ready to be pulled to the next stage")
    email_from = fields.Char(string='Email', help="These people will receive email.", index=True)
    email_cc = fields.Char(string='Watchers Emails', help="""These email addresses will be added to the CC field of all inbound
        and outbound emails for this record before being sent. Separate multiple email addresses with a comma""")
    date_open = fields.Datetime(string='Assigned', readonly=True, index=True)
    date_closed = fields.Datetime(string='Closed', readonly=True, index=True)
    date = fields.Datetime('Date')
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, default=fields.Datetime.now)
    channel = fields.Char(string='Channel', help="Communication channel.")  # TDE note: is it still used somewhere ?
    tag_ids = fields.Many2many('project.tags', string='Tags')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', index=True, default='0')
    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                               domain="[('project_ids', '=', project_id)]", copy=False,
                               group_expand='_read_group_stage_ids',
                               default=_get_default_stage_id)
    project_id = fields.Many2one('project.project', string='Project', track_visibility='onchange', index=True)
    duration = fields.Float('Duration')
    task_id = fields.Many2one('project.task', string='Task', domain="[('project_id','=',project_id)]",
                              help="You can link this issue to an existing task or directly create a new one from here")
    day_open = fields.Float(compute='_compute_day', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day', string='Days to Close', store=True)

    user_id = fields.Many2one('res.users', string='Assigned to', index=True, track_visibility='onchange', default=lambda self: self.env.uid)
    working_hours_open = fields.Float(compute='_compute_day', string='Working Hours to assign the Issue', store=True)
    working_hours_close = fields.Float(compute='_compute_day', string='Working Hours to close the Issue', store=True)
    inactivity_days = fields.Integer(compute='_compute_inactivity_days', string='Days since last action',
                                     help="Difference in days between last action and current date")
    color = fields.Integer('Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    legend_blocked = fields.Char(related="stage_id.legend_blocked", string='Kanban Blocked Explanation', readonly=True)
    legend_done = fields.Char(related="stage_id.legend_done", string='Kanban Valid Explanation', readonly=True)
    legend_normal = fields.Char(related="stage_id.legend_normal", string='Kanban Ongoing Explanation', readonly=True)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        # retrieve project_id from the context, add them to already fetched columns (ids)
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain
        # perform search
        return stages.search(search_domain, order=order)

    @api.multi
    @api.depends('create_date', 'date_closed', 'date_open')
    def _compute_day(self):
        for issue in self:
            dt_create_date = fields.Datetime.from_string(issue.create_date)

            if issue.date_open:
                dt_date_open = fields.Datetime.from_string(issue.date_open)
                issue.day_open = (dt_date_open - dt_create_date).total_seconds() / (24.0 * 3600)
                if issue.project_id.resource_calendar_id:
                    issue.working_hours_open = issue.project_id.resource_calendar_id.get_work_hours_count(
                        dt_create_date, dt_date_open,
                        compute_leaves=True, resource_id=False)
                else:
                    issue.working_hours_open = 0

            if issue.date_closed:
                dt_date_closed = fields.Datetime.from_string(issue.date_closed)
                issue.day_close = (dt_date_closed - dt_create_date).total_seconds() / (24.0 * 3600)
                if issue.project_id.resource_calendar_id:
                    issue.working_hours_close = issue.project_id.resource_calendar_id.get_work_hours_count(
                        dt_create_date, dt_date_closed,
                        compute_leaves=True, resource_id=False)
                else:
                    issue.working_hours_close = 0

    @api.multi
    @api.depends('create_date', 'date_action_last', 'date_last_stage_update')
    def _compute_inactivity_days(self):
        current_datetime = fields.Datetime.from_string(fields.Datetime.now())
        for issue in self:
            dt_create_date = fields.Datetime.from_string(issue.create_date) or current_datetime
            issue.days_since_creation = (current_datetime - dt_create_date).days

            if issue.date_action_last:
                issue.inactivity_days = (current_datetime - fields.Datetime.from_string(issue.date_action_last)).days
            elif issue.date_last_stage_update:
                issue.inactivity_days = (current_datetime - fields.Datetime.from_string(issue.date_last_stage_update)).days
            else:
                issue.inactivity_days = (current_datetime - dt_create_date).days

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ This function sets partner email address based on partner
        """
        self.email_from = self.partner_id.email

    @api.onchange('project_id')
    def _onchange_project_id(self):
        default_partner_id = self.env.context.get('default_partner_id')
        default_partner = self.env['res.partner'].browse(default_partner_id) if default_partner_id else self.env['res.partner']
        if self.project_id:
            if not self.partner_id and not self.email_from:
                self.partner_id = self.project_id.partner_id.id
                self.email_from = self.project_id.partner_id.email
            self.stage_id = self.stage_find(self.project_id.id, [('fold', '=', False)])
        else:
            self.partner_id = default_partner
            self.email_from = default_partner.email
            self.stage_id = False

    @api.onchange('task_id')
    def _onchange_task_id(self):
        self.user_id = self.task_id.user_id

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update(name=_('%s (copy)') % (self.name))
        return super(ProjectIssue, self).copy(default=default)

    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        if vals.get('project_id') and not self.env.context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        if vals.get('user_id') and not vals.get('date_open'):
            vals['date_open'] = fields.Datetime.now()
        if 'stage_id' in vals:
            vals.update(self.update_date_closed(vals['stage_id']))

        # context: no_log, because subtype already handle this
        context['mail_create_nolog'] = True
        return super(ProjectIssue, self.with_context(context)).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals.update(self.update_date_closed(vals['stage_id']))
            vals['date_last_stage_update'] = fields.Datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
        # user_id change: update date_open
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()
        return super(ProjectIssue, self).write(vals)

    @api.model
    def get_empty_list_help(self, help):
        return super(ProjectIssue, self.with_context(
            empty_list_help_model='project.project',
            empty_list_help_id=self.env.context.get('default_project_id'),
            empty_list_help_document_name=_("issues")
        )).get_empty_list_help(help)

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

    def update_date_closed(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold:
            return {'date_closed': fields.Datetime.now()}
        return {'date_closed': False}

    def stage_find(self, project_id, domain=None, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the issue:
            - project_id: if set, stages must belong to this project or
              be a default case
        """
        search_domain = list(domain) if domain else []
        if project_id:
            search_domain += [('project_ids', '=', project_id)]
        project_task_type = self.env['project.task.type'].search(search_domain, order=order, limit=1)
        return project_task_type.id

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.multi
    def _track_template(self, tracking):
        self.ensure_one()
        res = super(ProjectIssue, self)._track_template(tracking)
        changes, dummy = tracking[self.id]
        if 'stage_id' in changes and self.stage_id.mail_template_id:
            res['stage_id'] = (self.stage_id.mail_template_id, {'composition_mode': 'mass_mail'})
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return 'project_issue.mt_issue_blocked'
        elif 'kanban_state' in init_values and self.kanban_state == 'done':
            return 'project_issue.mt_issue_ready'
        elif 'user_id' in init_values and self.user_id:  # assigned -> new
            return 'project_issue.mt_issue_new'
        elif 'stage_id' in init_values and self.stage_id and self.stage_id.sequence <= 1:  # start stage -> new
            return 'project_issue.mt_issue_new'
        elif 'stage_id' in init_values:
            return 'project_issue.mt_issue_stage'
        return super(ProjectIssue, self)._track_subtype(init_values)

    @api.multi
    def _notification_recipients(self, message, groups):
        """
        """
        groups = super(ProjectIssue, self)._notification_recipients(message, groups)

        self.ensure_one()
        if not self.user_id:
            take_action = self._notification_link_helper('assign')
            project_actions = [{'url': take_action, 'title': _('I take it')}]
        else:
            project_actions = []

        new_group = (
            'group_project_user', lambda partner: bool(partner.user_ids) and any(user.has_group('project.group_project_user') for user in partner.user_ids), {
                'actions': project_actions,
            })

        return [new_group] + groups

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Override to get the reply_to of the parent project. """
        issues = self.browse(res_ids)
        project_ids = set(issues.mapped('project_id').ids)
        aliases = self.env['project.project'].message_get_reply_to(list(project_ids), default=default)
        return dict((issue.id, aliases.get(issue.project_id and issue.project_id.id or 0, False)) for issue in issues)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(ProjectIssue, self).message_get_suggested_recipients()
        try:
            for issue in self:
                if issue.partner_id:
                    issue._message_add_suggested_recipient(recipients, partner=issue.partner_id, reason=_('Customer'))
                elif issue.email_from:
                    issue._message_add_suggested_recipient(recipients, email=issue.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    @api.multi
    def email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        return filter(lambda x: x.split('@')[0] not in self.mapped('project_id.alias_name'), email_list)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_id'] = False
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        if custom_values:
            defaults.update(custom_values)

        issue = super(ProjectIssue, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        email_list = issue.email_split(msg)
        partner_ids = filter(None, issue._find_partner_from_emails(email_list))
        issue.message_subscribe(partner_ids)
        return issue

    @api.multi
    def message_update(self, msg, update_vals=None):
        """ Override to update the issue according to the email. """
        email_list = self.email_split(msg)
        partner_ids = filter(None, self._find_partner_from_emails(email_list))
        self.message_subscribe(partner_ids)
        return super(ProjectIssue, self).message_update(msg, update_vals=update_vals)

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, subtype=None, **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        self.ensure_one()
        mail_message = super(ProjectIssue, self).message_post(subtype=subtype, **kwargs)
        if subtype:
            self.sudo().write({'date_action_last': fields.Datetime.now()})
        return mail_message

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(ProjectIssue, self).message_get_email_values(notif_mail=notif_mail)
        headers = {}
        if res.get('headers'):
            try:
                headers.update(safe_eval(res['headers']))
            except Exception:
                pass
        if self.project_id:
            current_objects = filter(None, headers.get('X-Odoo-Objects', '').split(','))
            current_objects.insert(0, 'project.project-%s, ' % self.project_id.id)
            headers['X-Odoo-Objects'] = ','.join(current_objects)
        if self.tag_ids:
            headers['X-Odoo-Tags'] = ','.join(self.tag_ids.mapped('name'))
        res['headers'] = repr(headers)
        return res
