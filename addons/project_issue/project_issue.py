 #-*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime

from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import html2plaintext
from openerp.tools.translate import _


class project_issue_version(osv.Model):
    _name = "project.issue.version"
    _order = "name desc"
    _columns = {
        'name': fields.char('Version Number', required=True),
        'active': fields.boolean('Active', required=False),
    }
    _defaults = {
        'active': 1,
    }

class project_issue(osv.Model):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority desc, create_date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _mail_post_access = 'read'
    _track = {
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'project_issue.mt_issue_new': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence <= 1,
            'project_issue.mt_issue_stage': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence > 1,
        },
        'user_id': {
            'project_issue.mt_issue_assigned': lambda self, cr, uid, obj, ctx=None: obj.user_id and obj.user_id.id,
        },
        'kanban_state': {
            'project_issue.mt_issue_blocked': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'blocked',
            'project_issue.mt_issue_ready': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'done',
        },
    }

    def _get_default_partner(self, cr, uid, context=None):
        project_id = self._get_default_project_id(cr, uid, context)
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                return project.partner_id.id
        return False

    def _get_default_project_id(self, cr, uid, context=None):
        """ Gives default project by checking if present in the context """
        return self._resolve_project_id_from_context(cr, uid, context=context)

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        project_id = self._get_default_project_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], project_id, [('fold', '=', False)], context=context)

    def _resolve_project_id_from_context(self, cr, uid, context=None):
        """ Returns ID of project based on the value of 'default_project_id'
            context key, or None if it cannot be resolved to a single
            project.
        """
        if context is None:
            context = {}
        if type(context.get('default_project_id')) in (int, long):
            return context.get('default_project_id')
        if isinstance(context.get('default_project_id'), basestring):
            project_name = context['default_project_id']
            project_ids = self.pool.get('project.project').name_search(cr, uid, name=project_name, context=context)
            if len(project_ids) == 1:
                return int(project_ids[0][0])
        return None

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('project.task.type')
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve section_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('project_ids', 'in', project_id), ('fold', '=', False) if project_id: add project columns that are not folded
        search_domain = []
        project_id = self._resolve_project_id_from_context(cr, uid, context=context)
        if project_id:
            search_domain += ['|', ('project_ids', '=', project_id)]
        search_domain += [('id', 'in', ids)]
        # perform search
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        Calendar = self.pool['resource.calendar']

        res = dict((res_id, {}) for res_id in ids)
        for issue in self.browse(cr, uid, ids, context=context):
            values = {
                'day_open': 0.0, 'day_close': 0.0,
                'working_hours_open': 0.0, 'working_hours_close': 0.0,
                'days_since_creation': 0.0, 'inactivity_days': 0.0,
            }
            # if the working hours on the project are not defined, use default ones (8 -> 12 and 13 -> 17 * 5), represented by None
            calendar_id = None
            if issue.project_id and issue.project_id.resource_calendar_id:
                calendar_id = issue.project_id.resource_calendar_id.id

            dt_create_date = datetime.strptime(issue.create_date, DEFAULT_SERVER_DATETIME_FORMAT)

            if issue.date_open:
                dt_date_open = datetime.strptime(issue.date_open, DEFAULT_SERVER_DATETIME_FORMAT)
                values['day_open'] = (dt_date_open - dt_create_date).total_seconds() / (24.0 * 3600)
                values['working_hours_open'] = Calendar._interval_hours_get(
                    cr, uid, calendar_id, dt_create_date, dt_date_open,
                    timezone_from_uid=issue.user_id.id or uid,
                    exclude_leaves=False, context=context)

            if issue.date_closed:
                dt_date_closed = datetime.strptime(issue.date_closed, DEFAULT_SERVER_DATETIME_FORMAT)
                values['day_close'] = (dt_date_closed - dt_create_date).total_seconds() / (24.0 * 3600)
                values['working_hours_close'] = Calendar._interval_hours_get(
                    cr, uid, calendar_id, dt_create_date, dt_date_closed,
                    timezone_from_uid=issue.user_id.id or uid,
                    exclude_leaves=False, context=context)

            days_since_creation = datetime.today() - dt_create_date
            values['days_since_creation'] = days_since_creation.days
            if issue.date_action_last:
                inactive_days = datetime.today() - datetime.strptime(issue.date_action_last, DEFAULT_SERVER_DATETIME_FORMAT)
            elif issue.date_last_stage_update:
                inactive_days = datetime.today() - datetime.strptime(issue.date_last_stage_update, DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                inactive_days = datetime.today() - datetime.strptime(issue.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
            values['inactivity_days'] = inactive_days.days

            # filter only required values
            for field in fields:
                res[issue.id][field] = values[field]

        return res

    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        task_pool = self.pool.get('project.task')
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            progress = 0.0
            if issue.task_id:
                progress = task_pool._hours_get(cr, uid, [issue.task_id.id], field_names, args, context=context)[issue.task_id.id]['progress']
            res[issue.id] = {'progress' : progress}
        return res

    def on_change_project(self, cr, uid, ids, project_id, context=None):
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                return {'value': {'partner_id': project.partner_id.id, 'email_from': project.partner_id.email}}
        return {}

    def _get_issue_task(self, cr, uid, ids, context=None):
        issues = []
        issue_pool = self.pool.get('project.issue')
        for task in self.pool.get('project.task').browse(cr, uid, ids, context=context):
            issues += issue_pool.search(cr, uid, [('task_id','=',task.id)])
        return issues

    def _get_issue_work(self, cr, uid, ids, context=None):
        issues = []
        issue_pool = self.pool.get('project.issue')
        for work in self.pool.get('project.task.work').browse(cr, uid, ids, context=context):
            if work.task_id:
                issues += issue_pool.search(cr, uid, [('task_id','=',work.task_id.id)])
        return issues

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Issue', required=True),
        'active': fields.boolean('Active', required=False),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'days_since_creation': fields.function(_compute_day, string='Days since creation date', \
                                               multi='compute_day', type="integer", help="Difference in days between creation date and current date"),
        'date_deadline': fields.date('Deadline'),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'),
        'partner_id': fields.many2one('res.partner', 'Contact', select=1),
        'company_id': fields.many2one('res.company', 'Company'),
        'description': fields.text('Private Note'),
        'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready for next stage')], 'Kanban State',
                                         track_visibility='onchange',
                                         help="A Issue's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this issue\n"
                                              " * Ready for next stage indicates the issue is ready to be pulled to the next stage",
                                         required=False),
        'email_from': fields.char('Email', size=128, help="These people will receive email.", select=1),
        'email_cc': fields.char('Watchers Emails', size=256, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'date_open': fields.datetime('Assigned', readonly=True, select=True),
        # Project Issue fields
        'date_closed': fields.datetime('Closed', readonly=True, select=True),
        'date': fields.datetime('Date'),
        'date_last_stage_update': fields.datetime('Last Stage Update', select=True),
        'channel': fields.char('Channel', help="Communication channel."),
        'categ_ids': fields.many2many('project.category', string='Tags'),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', select=True),
        'version_id': fields.many2one('project.issue.version', 'Version'),
        'stage_id': fields.many2one ('project.task.type', 'Stage',
                        track_visibility='onchange', select=True,
                        domain="[('project_ids', '=', project_id)]", copy=False),
        'project_id': fields.many2one('project.project', 'Project', track_visibility='onchange', select=True),
        'duration': fields.float('Duration'),
        'task_id': fields.many2one('project.task', 'Task', domain="[('project_id','=',project_id)]"),
        'day_open': fields.function(_compute_day, string='Days to Assign',
                                    multi='compute_day', type="float",
                                    store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_open'], 10)}),
        'day_close': fields.function(_compute_day, string='Days to Close',
                                     multi='compute_day', type="float",
                                     store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_closed'], 10)}),
        'user_id': fields.many2one('res.users', 'Assigned to', required=False, select=1, track_visibility='onchange'),
        'working_hours_open': fields.function(_compute_day, string='Working Hours to assign the Issue',
                                              multi='compute_day', type="float",
                                              store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_open'], 10)}),
        'working_hours_close': fields.function(_compute_day, string='Working Hours to close the Issue',
                                               multi='compute_day', type="float",
                                               store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_closed'], 10)}),
        'inactivity_days': fields.function(_compute_day, string='Days since last action',
                                           multi='compute_day', type="integer", help="Difference in days between last action and current date"),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'progress': fields.function(_hours_get, string='Progress (%)', multi='hours', group_operator="avg", help="Computed as: Time Spent / Total Time.",
            store = {
                'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['task_id'], 10),
                'project.task': (_get_issue_task, ['work_ids', 'remaining_hours', 'planned_hours', 'state', 'stage_id'], 10),
                'project.task.work': (_get_issue_work, ['hours'], 10),
            }),
    }

    _defaults = {
        'active': 1,
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': '0',
        'kanban_state': 'normal',
        'date_last_stage_update': fields.datetime.now,
        'user_id': lambda obj, cr, uid, context: uid,
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def copy(self, cr, uid, id, default=None, context=None):
        issue = self.read(cr, uid, [id], ['name'], context=context)[0]
        if not default:
            default = {}
        default = default.copy()
        default.update(name=_('%s (copy)') % (issue['name']))
        return super(project_issue, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, uid, vals, context=None):
        context = dict(context or {})
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        if vals.get('user_id') and not vals.get('date_open'):
            vals['date_open'] = fields.datetime.now()
        if 'stage_id' in vals:
            vals.update(self.onchange_stage_id(cr, uid, None, vals.get('stage_id'), context=context)['value'])

        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        return super(project_issue, self).create(cr, uid, vals, context=create_context)

    def write(self, cr, uid, ids, vals, context=None):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals.update(self.onchange_stage_id(cr, uid, ids, vals.get('stage_id'), context=context)['value'])
            vals['date_last_stage_update'] = fields.datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
        # user_id change: update date_open
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.datetime.now()

        return super(project_issue, self).write(cr, uid, ids, vals, context)

    def onchange_task_id(self, cr, uid, ids, task_id, context=None):
        if not task_id:
            return {'value': {}}
        task = self.pool.get('project.task').browse(cr, uid, task_id, context=context)
        return {'value': {'user_id': task.user_id.id, }}

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        """ This function returns value of partner email address based on partner
            :param part: Partner's id
        """
        result = {}
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context)
            result['email_from'] = partner.email
        return {'value': result}

    def get_empty_list_help(self, cr, uid, help, context=None):
        context = dict(context or {})
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_id'] = context.get('default_project_id')
        context['empty_list_help_document_name'] = _("issues")
        return super(project_issue, self).get_empty_list_help(cr, uid, help, context=context)

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

    def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):
        if not stage_id:
            return {'value': {}}
        stage = self.pool['project.task.type'].browse(cr, uid, stage_id, context=context)
        if stage.fold:
            return {'value': {'date_closed': fields.datetime.now()}}
        return {'value': {'date_closed': False}}

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the issue:
            - type: stage type must be the same or 'both'
            - section_id: if set, stages must belong to this section or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        for task in cases:
            if task.project_id:
                section_ids.append(task.project_id.id)
        # OR all section_ids and OR with case_default
        search_domain = []
        if section_ids:
            search_domain += [('|')] * (len(section_ids)-1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('project.task.type').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def case_escalate(self, cr, uid, ids, context=None):        # FIXME rename this method to issue_escalate
        for issue in self.browse(cr, uid, ids, context=context):
            data = {}
            esc_proj = issue.project_id.project_escalation_id
            if not esc_proj:
                raise osv.except_osv(_('Warning!'), _('You cannot escalate this issue.\nThe relevant Project has not configured the Escalation Project!'))

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

    def message_get_reply_to(self, cr, uid, ids, context=None):
        """ Override to get the reply_to of the parent project. """
        issues = self.browse(cr, SUPERUSER_ID, ids, context=context)
        project_ids = set([issue.project_id.id for issue in issues if issue.project_id])
        aliases = self.pool['project.project'].message_get_reply_to(cr, uid, list(project_ids), context=context)
        return dict((issue.id, aliases.get(issue.project_id and issue.project_id.id or 0, False)) for issue in issues)

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(project_issue, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        try:
            for issue in self.browse(cr, uid, ids, context=context):
                if issue.partner_id:
                    self._message_add_suggested_recipient(cr, uid, recipients, issue, partner=issue.partner_id, reason=_('Customer'))
                elif issue.email_from:
                    self._message_add_suggested_recipient(cr, uid, recipients, issue, email=issue.email_from, reason=_('Customer Email'))
        except (osv.except_osv, orm.except_orm):  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        context = dict(context or {}, state_to='draft')
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        defaults.update(custom_values)
        res_id = super(project_issue, self).message_new(cr, uid, msg, custom_values=defaults, context=context)
        return res_id

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification', subtype=None, parent_id=False, attachments=None, context=None, content_subtype='html', **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        if context is None:
            context = {}
        res = super(project_issue, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)
        if thread_id and subtype:
            self.write(cr, SUPERUSER_ID, thread_id, {'date_action_last': fields.datetime.now()}, context=context)
        return res


class project(osv.Model):
    _inherit = "project.project"

    def _get_alias_models(self, cr, uid, context=None):
        res = super(project, self)._get_alias_models(cr, uid, context=context)
        res.append(("project.issue", "Issues"))
        return res

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        return {
            project_id: Issue.search_count(cr,uid, [('project_id', '=', project_id), ('stage_id.fold', '=', False)], context=context)
            for project_id in ids
        }
    _columns = {
        'project_escalation_id': fields.many2one('project.project', 'Project Escalation',
            help='If any issue is escalated from the current Project, it will be listed under the project selected here.',
            states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]}),
        'issue_count': fields.function(_issue_count, type='integer', string="Issues",),
        'issue_ids': fields.one2many('project.issue', 'project_id',
                                     domain=[('stage_id.fold', '=', False)])
    }

    def _check_escalation(self, cr, uid, ids, context=None):
        project_obj = self.browse(cr, uid, ids[0], context=context)
        if project_obj.project_escalation_id:
            if project_obj.project_escalation_id.id == project_obj.id:
                return False
        return True

    _constraints = [
        (_check_escalation, 'Error! You cannot assign escalation to the same project!', ['project_escalation_id'])
    ]


class account_analytic_account(osv.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    _columns = {
        'use_issues': fields.boolean('Issues', help="Check this field if this project manages issues"),
    }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res = super(account_analytic_account, self)._trigger_project_creation(cr, uid, vals, context=context)
        return res or (vals.get('use_issues') and not 'project_creation_in_progress' in context)


class project_project(osv.Model):
    _inherit = 'project.project'

    _defaults = {
        'use_issues': True
    }

    def _check_create_write_values(self, cr, uid, vals, context=None):
        """ Perform some check on values given to create or write. """
        # Handle use_tasks / use_issues: if only one is checked, alias should take the same model
        if vals.get('use_tasks') and not vals.get('use_issues'):
            vals['alias_model'] = 'project.task'
        elif vals.get('use_issues') and not vals.get('use_tasks'):
            vals['alias_model'] = 'project.issue'

    def on_change_use_tasks_or_issues(self, cr, uid, ids, use_tasks, use_issues, context=None):
        values = {}
        if use_tasks and not use_issues:
            values['alias_model'] = 'project.task'
        elif not use_tasks and use_issues:
            values['alias_model'] = 'project.issue'
        return {'value': values}

    def create(self, cr, uid, vals, context=None):
        self._check_create_write_values(cr, uid, vals, context=context)
        return super(project_project, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._check_create_write_values(cr, uid, vals, context=context)
        return super(project_project, self).write(cr, uid, ids, vals, context=context)

class res_partner(osv.osv):
    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        return {
            partner_id: Issue.search_count(cr,uid, [('partner_id', '=', partner_id)])
            for partner_id in ids
        }
    
    """ Inherits partner and adds Issue information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'issue_count': fields.function(_issue_count, string='# Issues', type='integer'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
