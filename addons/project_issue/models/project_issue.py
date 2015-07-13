# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from openerp import api, fields, models
from openerp.exceptions import AccessError, UserError
from openerp.tools.translate import _


class ProjectIssue(models.Model):
    _name = "project.issue"
    _description = "Project Issue"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "priority desc, create_date desc"
    _mail_post_access = 'read'

    def _get_default_partner(self):
        if 'default_project_id' in self.env.context:
            project = self.env['project.project'].browse(self.env.context['default_project_id'])
            if project and project.partner_id:
                return project.partner_id.id
        return False

    name = fields.Char('Issue', required=True)
    active = fields.Boolean(default=True)
    create_date = fields.Datetime('Creation Date', readonly=True, index=True)
    write_date = fields.Datetime('Update Date', readonly=True)
    days_since_creation = fields.Integer(compute='_compute_days_since_creation', string='Days since creation date',
                                         help="Difference in days between creation date and current date")

    date_deadline = fields.Date('Deadline')
    team_id = fields.Many2one('crm.team', 'Sales Team', oldname='section_id', index=True, help="""Sales team to which Case belongs to.
                              Define Responsible user and Email account for mail gateway.""",
                              default=lambda self: self.env['crm.team']._get_default_team_id())
    partner_id = fields.Many2one('res.partner', 'Contact', index=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    description = fields.Text('Private Note')
    kanban_state = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], 'Kanban State',
                                    track_visibility='onchange',
                                    help="""A Issue's kanban state indicates special situations affecting it:\n
                                           * Normal is the default situation\n
                                           * Blocked indicates something is preventing the progress of this issue\n
                                           * Ready for next stage indicates the issue is ready to be pulled to the next stage""",
                                    required=True, default='normal')
    email_from = fields.Char('Email', help="These people will receive email.", index=True)
    email_cc = fields.Char('Watchers Emails', help="""These email addresses will be added to the CC field of all inbound
        and outbound emails for this record before being sent. Separate multiple email addresses with a comma""")
    date_open = fields.Datetime('Assigned', readonly=True, index=True)
    # Project Issue fields
    date_closed = fields.Datetime('Closed', readonly=True, index=True)
    date = fields.Datetime()
    date_last_stage_update = fields.Datetime('Last Stage Update', index=True, default=lambda self: datetime.now())
    channel = fields.Char(help="Communication channel.")
    tag_ids = fields.Many2many('project.tags', string='Tags')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', index=True, default='0')
    stage_id = fields.Many2one('project.task.type', 'Stage', track_visibility='onchange', index=True,
                               domain="[('project_ids', '=', project_id)]", copy=False,
                               default=lambda self: self.stage_find(self.env.context.get('default_project_id'), [('fold', '=', False)]))
    project_id = fields.Many2one('project.project', 'Project', track_visibility='onchange', index=True)
    duration = fields.Float()
    task_id = fields.Many2one('project.task', 'Task', domain="[('project_id','=',project_id)]",
                              help="You can link this issue to an existing task or directly create a new one from here")
    day_open = fields.Float(compute='_compute_day_open', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day_close', string='Days to Close', store=True)

    user_id = fields.Many2one('res.users', 'Assigned to', index=True, track_visibility='onchange', default=lambda self: self.env.user.id)
    working_hours_open = fields.Float(compute='_compute_working_hours_open', string='Working Hours to assign the Issue', store=True)
    working_hours_close = fields.Float(compute='_compute_working_hours_close', string='Working Hours to close the Issue', store=True)
    inactivity_days = fields.Integer(compute='_compute_day_inactivity_days', string='Days since last action',
                                     help="Difference in days between last action and current date")
    color = fields.Integer('Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    date_action_last = fields.Datetime('Last Action', readonly=True)
    date_action_next = fields.Datetime('Next Action', readonly=True)
    can_escalate = fields.Boolean(compute='_compute_can_escalate', string='Can Escalate')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        ProjectTaskType = self.env['project.task.type']
        order = ProjectTaskType._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('project_ids', 'in', project_id), ('fold', '=', False) if project_id: add project columns that are not folded
        search_domain = []
        if 'default_project_id' in self.env.context:
            search_domain += ['|', ('project_ids', '=', self.env.context['default_project_id']), ('id', 'in', self.ids)]
        else:
            search_domain += ['|', ('id', 'in', self.ids), ('case_default', '=', True)]
        # perform search
        project_task_types = ProjectTaskType.search(search_domain, order=order)
        result = project_task_types.name_get()
        fold = {project_task_type.id: project_task_type.fold for project_task_type in project_task_types}
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    @api.depends('date_closed', 'date_open')
    def _compute_days_since_creation(self):
        for issue in self.filtered('create_date'):
            dt_create_date = fields.Datetime.from_string(issue.create_date)
            issue.days_since_creation = (datetime.today() - dt_create_date).days

    @api.depends('date_open', 'date_closed')
    def _compute_day_open(self):
        for issue in self.filtered(lambda record: record.create_date and record.date_open):
            dt_create_date = fields.Datetime.from_string(issue.create_date)
            dt_date_open = fields.Datetime.from_string(issue.date_open)
            issue.day_open = (dt_date_open - dt_create_date).total_seconds() / (24.0 * 3600)

    @api.depends('date_closed', 'date_open')
    def _compute_day_close(self):
        for issue in self.filtered(lambda record: record.create_date and record.date_closed):
            dt_create_date = fields.Datetime.from_string(issue.create_date)
            dt_date_closed = fields.Datetime.from_string(issue.date_closed)
            issue.day_close = (dt_date_closed - dt_create_date).total_seconds() / (24.0 * 3600)

    @api.depends('date_open', 'date_closed')
    def _compute_working_hours_open(self):
        ResourceCalendar = self.env['resource.calendar']
        for issue in self.filtered(lambda record: record.create_date and record.date_open):
            dt_create_date = fields.Datetime.from_string(issue.create_date)
            dt_date_open = fields.Datetime.from_string(issue.date_open)
            issue.working_hours_open = ResourceCalendar._model.get_working_hours(self.env.cr, self.env.uid, None, dt_create_date, dt_date_open,
                                       compute_leaves=True, resource_id=False, default_interval=(8, 16), context=self.env.context)

    @api.depends('date_closed')
    def _compute_working_hours_close(self):
        ResourceCalendar = self.env['resource.calendar']
        for issue in self.filtered(lambda record: record.create_date and record.date_closed):
            dt_create_date = fields.Datetime.from_string(issue.create_date)
            dt_date_closed = fields.Datetime.from_string(issue.date_closed)
            issue.working_hours_close = ResourceCalendar._model.get_working_hours(self.env.cr, self.env.uid, None, dt_create_date, dt_date_closed,
                                        compute_leaves=True, resource_id=False, default_interval=(8, 16), context=self.env.context)

    @api.depends('date_open', 'create_date')
    def _compute_day_inactivity_days(self):
        for issue in self:
            if issue.date_action_last:
                inactivity_days = datetime.today() - fields.Datetime.from_string(issue.date_action_last)
            elif issue.date_last_stage_update:
                inactivity_days = datetime.today() - fields.Datetime.from_string(issue.date_last_stage_update)
            else:
                inactivity_days = datetime.today() - fields.Datetime.from_string(issue.create_date)
            issue.inactivity_days = inactivity_days.days

    @api.multi
    def _compute_can_escalate(self):
        for issue in self.filtered(lambda rec: rec.project_id.project_escalation_id.analytic_account_id.type == 'contract'):
            issue.can_escalate = True

    @api.multi
    def on_change_project(self, project_id):
        if project_id:
            project = self.env['project.project'].browse(project_id)
            if project and project.partner_id:
                return {'value': {'partner_id': project.partner_id.id}}
        return {'value': {'partner_id': False}}

    @api.onchange('task_id')
    def onchange_task_id(self):
        if self.task_id:
            self.user_id = self.task_id.user_id.id
        else:
            self.user_id = False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """ This function returns value of partner email address based on partner
            :param part: Partner's id
        """
        if self.partner_id:
            self.email_from = self.partner_id.email
        else:
            self.email_from = False

    @api.multi
    def copy_data(self, default={}):
        default.update(name=_('%s (copy)') % (self.name or ""))
        return super(ProjectIssue, self).copy_data(default)[0]

    @api.model
    def create(self, vals):
        context = dict()
        if vals.get('project_id') and not self.env.context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        if 'stage_id' in vals:
            vals.update(self.check_stage_id(vals.get('stage_id'))['value'])
        # context: no_log, because subtype already handle this
        context['mail_create_nolog'] = True
        return super(ProjectIssue, self.with_context(context)).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
            vals.update(self.check_stage_id(vals.get('stage_id'))['value'])
        # user_id change: update date_start
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        return super(ProjectIssue, self).write(vals)

    @api.model
    def get_empty_list_help(self, help):
        context = dict()
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_id'] = self.env.context.get('default_project_id')
        context['empty_list_help_document_name'] = _("issues")
        return super(ProjectIssue, self.with_context(context)).get_empty_list_help(help)

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

    def check_stage_id(self, stage_id):
        if not stage_id:
            return {'value': {}}
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type and project_task_type.fold:
            return {'value': {'date_closed': fields.datetime.now()}}
        return {'value': {'date_closed': False}}

    def stage_find(self, project_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the issue:
            - type: stage type must be the same or 'both'
            - project_id: if set, stages must belong to this project or
              be a default case
        """
        # collect all project_ids
        project_ids = []
        if project_id:
            project_ids.append(project_id)
        project_ids += set(map(lambda rec: rec.project_id.id, self.filtered(lambda rec: rec.project_id.id != project_id)))
        # OR all project_ids and OR with case_default
        search_domain = []
        if project_ids:
            search_domain += [('|')] * (len(project_ids)-1)
            search_domain += map(lambda project_id: ('project_ids', '=', project_id), project_ids)
        search_domain += list(domain)
        # perform search, return the first found
        project_task_type = self.env['project.task.type'].search(search_domain, order=order, limit=1)
        if project_task_type:
            return project_task_type.id
        return False

    @api.multi
    def case_escalate(self):  # FIXME rename this method to issue_escalate
        for issue in self:
            data = {}
            project_escalate = issue.project_id.project_escalation_id
            if not project_escalate:
                raise UserError(_('You cannot escalate this issue.\nThe relevant Project has not configured the Escalation Project!'))
            data['project_id'] = project_escalate.id
            if project_escalate.user_id:
                data['user_id'] = project_escalate.user_id.id
            issue.write(data)
            if issue.task_id:
                issue.task_id.write({'project_id': project_escalate.id, 'user_id': False})
        return True

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.multi
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

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Override to get the reply_to of the parent project. """
        issues = self.browse(res_ids)
        project_ids = set(map(lambda rec: rec.project_id.id, issues.filtered('project_id')))
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

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        if custom_values:
            defaults.update(custom_values)
        return super(ProjectIssue, self.with_context({'state_to': 'draft'})).message_new(msg, custom_values=defaults)

    @api.multi
    def message_post(self, subtype=None, **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        if self.ids and subtype:
            self.write({'date_action_last': fields.datetime.now()})
        return super(ProjectIssue, self).message_post(subtype=subtype, **kwargs).id
