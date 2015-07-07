# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
# from openerp import tools
# from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp.exceptions import UserError, AccessError
from openerp import models, fields, api


class project_issue(models.Model):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority desc, create_date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _mail_post_access = 'read'

    def _get_default_partner(self):
        if 'default_project_id' in self.env.context:
            project = self.env['project.project'].browse(self.env.context['default_project_id'])
            if project and project.partner_id:
                self.partner_id = project.partner_id
        else:
            self.partner_id = False

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        return self.stage_find(self.env.context.get('default_project_id'), [('fold', '=', False)])

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        access_rights_uid = access_rights_uid or self.env.uid
        stage_obj = self.env['project.task.type']
        order = stage_obj._order
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
        stage_ids = stage_obj._search(search_domain, order=order, access_rights_uid=access_rights_uid)
        result = [(stage.id, stage.display_name) for stage in stage_obj.browse(stage_ids)]
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.sudo(access_rights_uid).browse(stage_ids):
            fold[stage.id] = stage.fold or False
        return result, fold

    @api.multi
    def _can_escalate(self):
        for issue in self:
            if issue.project_id.project_escalation_id and issue.analytic_account_id.type == 'contract':
                issue.can_escalate = True

    @api.depends('date_open', 'create_date')
    def _compute_day_open(self):
        if self.date_open:
            dt_create_date = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            dt_date_open = datetime.strptime(self.date_open, DEFAULT_SERVER_DATETIME_FORMAT)
            self.day_open = (dt_date_open - dt_create_date).total_seconds() / (24.0 * 3600)

    @api.depends('date_closed')
    def _compute_day_close(self):
        if self.date_closed:
            dt_create_date = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            dt_date_closed = datetime.strptime(self.date_closed, DEFAULT_SERVER_DATETIME_FORMAT)
            self.day_close = (dt_date_closed - dt_create_date).total_seconds() / (24.0 * 3600)

    @api.depends('date_open')
    def _compute_working_hours_open(self):
        if self.date_open:
            Calendar = self.pool['resource.calendar']
            dt_create_date = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            dt_date_open = datetime.strptime(self.date_open, DEFAULT_SERVER_DATETIME_FORMAT)

            self.working_hours_open = Calendar._interval_hours_get(self.env.cr, self.env.uid, None, dt_create_date, dt_date_open,
                                                                   timezone_from_uid=self.user_id.id or self.env.uid, resource_id=False,
                                                                   exclude_leaves=False, context=self.env.context)

    @api.depends('date_closed')
    def _compute_working_hours_close(self):
        if self.date_closed:
            Calendar = self.pool['resource.calendar']
            dt_create_date = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            dt_date_closed = datetime.strptime(self.date_closed, DEFAULT_SERVER_DATETIME_FORMAT)

            self.working_hours_close = Calendar._interval_hours_get(self.env.cr, self.env.uid, None, dt_create_date, dt_date_closed,
                                                                    timezone_from_uid=self.user_id.id or self.env.uid, resource_id=False,
                                                                    exclude_leaves=False, context=self.env.context)

    @api.depends('date_action_last')
    def _compute_inactivity_days(self):
        if self.date_action_last:
            inactivity_days = datetime.today() - datetime.strptime(self.date_action_last, DEFAULT_SERVER_DATETIME_FORMAT)
        elif self.date_last_stage_update:
            inactivity_days = datetime.today() - datetime.strptime(self.date_last_stage_update, DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            inactivity_days = datetime.today() - datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
        self.inactivity_days = inactivity_days.days

    @api.depends('date_open', 'date_closed')
    def _compute_day_since_creation(self):
        if self.create_date:
            dt_create_date = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            self.days_since_creation = (datetime.today() - dt_create_date).days

    id = fields.Integer('ID', readonly=True)
    active = fields.Boolean('Active', default=True)
    create_date = fields.Datetime('Creation Date', readonly=True, select=True)
    write_date = fields.Datetime('Update Date', readonly=True)
    name = fields.Char("Issue", required=True)
    days_since_creation = fields.Integer(compute=_compute_day_since_creation, string="Days since creation date",
                                         help="Difference in days between creation date and current date")
    date_deadline = fields.Date(string='Deadline')
    team_id = fields.Many2one('crm.team', oldname='section_id', string='Sales Team', index=True, help='Sales team to which Case belongs to.\
                         Define Responsible user and Email account for mail gateway.',
                              default=lambda self: self.env['crm.team']._get_default_team_id())
    partner_id = fields.Many2one('res.partner', 'Contact', index=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('crm.helpdesk'))
    description = fields.Text('Private Note')
    kanban_state = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], 'Kanban State',
                                    default="normal", track_visibility='onchange',
                                    help="A Issue's kanban state indicates special situations affecting it:\n"
                                    " * Normal is the default situation\n"
                                    " * Blocked indicates something is preventing the progress of this issue\n"
                                    " * Ready for next stage indicates the issue is ready to be pulled to the next stage",
                                    required=True)
    email_from = fields.Char('Email', help="These people will receive email.", index=True)
    email_cc = fields.Char('Watchers Emails', help="These email addresses will be added to the CC field of all inbound and outbound emails\
        for this record before being sent. Separate multiple email addresses with a comma")
    date_open = fields.Datetime('Assigned', readonly=True, index=True)
    # # Project Issue fields
    date_closed = fields.Datetime('Closed', readonly=True, index=True)
    date = fields.Datetime('Date')
    date_last_stage_update = fields.Datetime('Last Stage Update', index=True, default=lambda self: datetime.now())
    channel = fields.Char('Channel', help="Communication channel.")
    tag_ids = fields.Many2many('project.tags', string='Tags')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', index=True, default='0')
    stage_id = fields.Many2one('project.task.type', 'Stage', index=True, domain="[('project_ids', '=', project_id)]", copy=False,
                               default=lambda self: self._get_default_stage_id(), track_visibility="onchange")
    project_id = fields.Many2one('project.project', 'Project', index=True, track_visibility="onchange")
    duration = fields.Float('Duration')
    task_id = fields.Many2one('project.task', 'Task', domain="[('project_id','=',project_id)]",
                              help="You can link this issue to an existing task or directly create a new one from here")
    day_open = fields.Float(compute=_compute_day_open, string='Days to Assign', store=True)
    day_close = fields.Float(compute=_compute_day_close, string='Days to Close', store=True)
    user_id = fields.Many2one('res.users', 'Assigned to', select=True, default=lambda self: self.env.uid, track_visibility="onchange")
    working_hours_open = fields.Float(compute=_compute_working_hours_open, string='Working Hours to assign the Issue', store=True)
    working_hours_close = fields.Float(compute=_compute_working_hours_close, string='Working Hours to close the Issue', store=True)
    inactivity_days = fields.Integer(compute=_compute_inactivity_days, string='Days since last action',
                                     help="Difference in days between last action and current date")
    color = fields.Integer('Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    date_action_last = fields.Datetime('Last Action', readonly=True)
    date_action_next = fields.Datetime('Next Action', readonly=True)
    can_escalate = fields.Boolean(compute=_can_escalate, string='Can Escalate')

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    @api.one
    def copy(self, default={}):
        default = dict(default or {})
        default.update(name=_('%s (copy)') % (self.name or ""))
        return super(project_issue, self).copy(default=default)

    @api.model
    def create(self, vals):
        context = dict()
        if vals.get('project_id') and not self.env.context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        if 'stage_id' in vals:
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            if stage.fold:
                vals['date_closed'] = fields.datetime.now()
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        context['mail_create_nolog'] = True
        return super(project_issue, self.with_context(context)).create(vals)

    @api.one
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
            # self.onchange_stage_id()
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            if stage.fold:
                vals['date_closed'] = fields.datetime.now()
        # user_id change: update date_start
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        return super(project_issue, self).write(vals)

    @api.v7
    def on_change_project(self, cr, uid, ids, project_id, context=None):
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                return {'value': {'partner_id': project.partner_id.id}}
        return {'value': {'partner_id': False}}

    @api.v8
    @api.onchange('project_id')
    def on_change_project(self):
        if self.project_id and self.project_id.partner_id:
            self.partner_id = self.project_id.partner_id.id
        else:
            self.partner_id = False

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

    @api.model
    def get_empty_list_help(self, help):
        context = dict()
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_id'] = self.env.context.get('default_project_id')
        context['empty_list_help_document_name'] = _("issues")
        return super(project_issue, self.with_context(context)).get_empty_list_help(help)

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

    def stage_find(self, team_id, domain, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the issue:
            - team_id: if set, stages must belong to this team or
              be a default case
        """
        team_ids = []
        if team_id:
            team_ids.append(team_id)
        for task in self.ids:
            if task.project_id:
                team_ids.append(task.project_id.id)
        # OR all team_ids and OR with case_default
        search_domain = []
        if team_ids:
            search_domain += [('|')] * (len(team_ids)-1)
            for team_id in team_ids:
                search_domain.append(('project_ids', '=', team_id))
        search_domain += list(domain)
        # perform search, return the first found
        stage_records = self.env['project.task.type'].search(search_domain, order=order)
        if stage_records:
            return stage_records[0].id
        return False

    @api.multi
    def case_escalate(self):  # FIXME rename this method to issue_escalate
        for issue in self:
            data = {}
            esc_proj = issue.project_id.project_escalation_id
            if not esc_proj:
                raise UserError(_('You cannot escalate this issue.\nThe relevant Project has not configured the Escalation Project!'))
            data['project_id'] = esc_proj.id
            if esc_proj.user_id:
                data['user_id'] = esc_proj.user_id.id
            issue.write(data)
            if issue.task_id:
                issue.task_id.write({'project_id': esc_proj.id, 'user_id': False})
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
        return super(project_issue, self)._track_subtype(init_values)

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Override to get the reply_to of the parent project. """
        issues = self.browse(res_ids)
        project_ids = set([issue.project_id.id for issue in issues if issue.project_id])
        aliases = self.env['project.project'].message_get_reply_to(list(project_ids), default=default)
        return dict((issue.id, aliases.get(issue.project_id and issue.project_id.id or 0, False)) for issue in issues)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(project_issue, self).message_get_suggested_recipients()
        try:
            for issue in self:
                if issue.partner_id:
                    issue._message_add_suggested_recipient(recipients, partner=issue.partner_id, reason=_('Customer'))
                elif issue.email_from:
                    issue._message_add_suggested_recipient(recipients, email=issue.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        context = dict()
        context['state_to'] = 'draft'
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        if custom_values:
            defaults.update(custom_values)
        return super(project_issue, self.with_context(context)).message_new(msg, custom_values=defaults)

    @api.multi
    def message_post(self, subtype=None, **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        res = super(project_issue, self).message_post(**kwargs)
        if self.id and subtype:
            self.sudo().write({'date_action_last': fields.datetime.now()})
        return res.id


class project(models.Model):
    _inherit = "project.project"

    @api.model
    def _get_alias_models(self):
        return [('project.task', "Tasks"), ("project.issue", "Issues")]

    @api.one
    def _issue_count(self):
        self.issue_count = len(self.issue_ids)

    project_escalation_id = fields.Many2one('project.project', string='Project Escalation', help='If any issue is escalated from \
        the current Project, it will be listed under the project selected here.',
                                            states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]})
    issue_count = fields.Integer(compute=_issue_count, string="Issues")
    issue_ids = fields.One2many('project.issue', 'project_id', string="Issues", domain=[('stage_id.fold', '=', False)])

    @api.constrains('project_escalation_id')
    def _check_escalation(self):
        if self.project_escalation_id and self.project_escalation_id.id == self.id:
            raise Warning(_("Error! You cannot assign escalation to the same project!"))
        return True


class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    use_issues = fields.Boolean('Issues', help="Check this box to manage customer activities through this project")

    @api.v7
    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    @api.v8
    @api.onchange('template_id')
    def on_change_template(self):
        if self.template_id:
            res = super(account_analytic_account, self).on_change_template(template_id=self.template_id.id, date_start=self.date_start)
            if 'value' in res:
                self.use_issues = self.template.use_issues

    @api.model
    def _trigger_project_creation(self, vals):
        res = (vals.get('use_issues') and not 'project_creation_in_progress' in self.env.context)
        return super(account_analytic_account, self)._trigger_project_creation(vals) or res

    @api.one
    def unlink(self):
        project = self.env['project.project'].search([('analytic_account_id', 'in', self.ids)])
        if project.issue_count:
            raise UserError(_('Please remove existing issues in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink()


class project_project(models.Model):
    _inherit = 'project.project'

    label_issues = fields.Char('Use Issues as', help="Customize the issues label, for example to call them cases.", default="Issues")

    def _check_create_write_values(self, vals):
        """ Perform some check on values given to create or write. """
        # Handle use_tasks / use_issues: if only one is checked, alias should take the same model
        if vals.get('use_tasks') and not vals.get('use_issues'):
            vals['alias_model'] = 'project.task'
        elif vals.get('use_issues') and not vals.get('use_tasks'):
            vals['alias_model'] = 'project.issue'

    @api.onchange('use_issues', 'use_tasks')
    def on_change_use_tasks_or_issues(self):
        if self.use_tasks and not self.use_issues:
            self.alias_model = 'project.task'
        elif not self.use_tasks and self.use_issues:
            self.alias_model = 'project.issue'

    @api.model
    def create(self, vals):
        self._check_create_write_values(vals)
        return super(project_project, self).create(vals)

    @api.one
    def write(self, vals):
        self._check_create_write_values(vals)
        return super(project_project, self).write(vals)


class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.one
    def _issue_count(self):
        self.issue_count = self.env['project.issue'].search_count([('partner_id', '=', self.id)])

    """ Inherits partner and adds Issue information in the partner form """
    issue_count = fields.Integer(compute=_issue_count, string='# Issues')
