# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from datetime import datetime,date
from dateutil import relativedelta
import json
import time
from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp.exceptions import UserError, AccessError


class project_issue(osv.Model):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority desc, create_date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _mail_post_access = 'read'

    def _get_default_partner(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'default_project_id' in context:
            project = self.pool.get('project.project').browse(cr, uid, context['default_project_id'], context=context)
            if project and project.partner_id:
                return project.partner_id.id
        return False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        if context is None:
            context = {}
        default_project_id = context.get('default_project_id')
        if not default_project_id:
            return False
        return self.stage_find(cr, uid, [], default_project_id, [('fold', '=', False)], context=context)

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        if context is None:
            context = {}
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('project.task.type')
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context, add them to already fetched columns (ids)
        if 'default_project_id' in context:
            search_domain = ['|', ('project_ids', '=', context['default_project_id']), ('id', 'in', ids)]
        else:
            search_domain = [('id', 'in', ids)]
        # perform search
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

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

    def on_change_project(self, cr, uid, ids, project_id, context=None):
        values = {}
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                values['partner_id'] = project.partner_id.id
                values['email_from'] = project.partner_id.email
            values['stage_id'] = self.stage_find(cr, uid, [], project_id, [('fold', '=', False)], context=context)
        else:
            values['partner_id'] = False
            values['email_from'] = False
            values['stage_id'] = False
        return {'value': values}

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Issue', required=True),
        'active': fields.boolean('Active', required=False),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'days_since_creation': fields.function(_compute_day, string='Days since creation date', \
                                               multi='compute_day', type="integer", help="Difference in days between creation date and current date",
                                               groups='base.group_user'),
        'date_deadline': fields.date('Deadline'),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',\
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
                                         required=True),
        'email_from': fields.char('Email', size=128, help="These people will receive email.", select=1),
        'email_cc': fields.char('Watchers Emails', size=256, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'date_open': fields.datetime('Assigned', readonly=True, select=True),
        # Project Issue fields
        'date_closed': fields.datetime('Closed', readonly=True, select=True),
        'date': fields.datetime('Date'),
        'date_last_stage_update': fields.datetime('Last Stage Update', select=True),
        'channel': fields.char('Channel', help="Communication channel."),
        'tag_ids': fields.many2many('project.tags', string='Tags'),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', select=True),
        'stage_id': fields.many2one ('project.task.type', 'Stage',
                        track_visibility='onchange', select=True,
                        domain="[('project_ids', '=', project_id)]", copy=False),
        'project_id': fields.many2one('project.project', 'Project', track_visibility='onchange', select=True),
        'duration': fields.float('Duration'),
        'task_id': fields.many2one('project.task', 'Task', domain="[('project_id','=',project_id)]",
            help="You can link this issue to an existing task or directly create a new one from here"),
        'day_open': fields.function(_compute_day, string='Days to Assign',
                                    multi='compute_day', type="float",
                                    store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_open'], 10)},
                                    groups='base.group_user'),
        'day_close': fields.function(_compute_day, string='Days to Close',
                                     multi='compute_day', type="float",
                                     store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_closed'], 10)},
                                     groups='base.group_user'),
        'user_id': fields.many2one('res.users', 'Assigned to', required=False, select=1, track_visibility='onchange'),
        'working_hours_open': fields.function(_compute_day, string='Working Hours to assign the Issue',
                                              multi='compute_day', type="float",
                                              store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_open'], 10)},
                                              groups='base.group_user'),
        'working_hours_close': fields.function(_compute_day, string='Working Hours to close the Issue',
                                               multi='compute_day', type="float",
                                               store={'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['date_closed'], 10)},
                                               groups='base.group_user'),
        'inactivity_days': fields.function(_compute_day, string='Days since last action',
                                           multi='compute_day', type="integer", help="Difference in days between last action and current date",
                                           groups='base.group_user'),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'legend_blocked': fields.related("stage_id", "legend_blocked", type="char", string='Kanban Blocked Explanation'),
        'legend_done': fields.related("stage_id", "legend_done", type="char", string='Kanban Valid Explanation'),
        'legend_normal': fields.related("stage_id", "legend_normal", type="char", string='Kanban Ongoing Explanation'),
    }

    _defaults = {
        'active': 1,
        'team_id': lambda s, cr, uid, c: s.pool['crm.team']._get_default_team_id(cr, uid, context=c),
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool['res.users']._get_company(cr, uid, context=c),
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
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context)
            return {'value': {'email_from': partner.email}}
        return {'value': {'email_from': False}}

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

    def stage_find(self, cr, uid, cases, team_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the issue:
            - type: stage type must be the same or 'both'
            - team_id: if set, stages must belong to this team or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all team_ids
        team_ids = []
        if team_id:
            team_ids.append(team_id)
        for task in cases:
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
        stage_ids = self.pool.get('project.task.type').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'kanban_state' in init_values and record.kanban_state == 'blocked':
            return 'project_issue.mt_issue_blocked'
        elif 'kanban_state' in init_values and record.kanban_state == 'done':
            return 'project_issue.mt_issue_ready'
        elif 'user_id' in init_values and record.user_id:  # assigned -> new
            return 'project_issue.mt_issue_new'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:  # start stage -> new
            return 'project_issue.mt_issue_new'
        elif 'stage_id' in init_values:
            return 'project_issue.mt_issue_stage'
        return super(project_issue, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def _notification_group_recipients(self, cr, uid, ids, message, recipients, done_ids, group_data, context=None):
        """ Override the mail.thread method to handle project users and officers
        recipients. Indeed those will have specific action in their notification
        emails: creating tasks, assigning it. """
        group_project_user = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'project.group_project_user')
        group_user = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'base.group_user')
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_project_user in recipient.user_ids[0].groups_id.ids:
                group_data['group_project_user'] |= recipient
            elif not recipient.user_ids:
                group_data['partner'] |= recipient
            else:
                group_data['user'] |= recipient
            done_ids.add(recipient.id)
        return super(project_issue, self)._notification_group_recipients(cr, uid, ids, message, recipients, done_ids, group_data, context=context)

    def _notification_get_recipient_groups(self, cr, uid, ids, message, recipients, context=None):
        res = super(project_issue, self)._notification_get_recipient_groups(cr, uid, ids, message, recipients, context=context)

        new_action_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'project_issue.project_issue_categ_act0')
        take_action = self._notification_link_helper(cr, uid, ids, 'assign', context=context)
        new_action = self._notification_link_helper(cr, uid, ids, 'new', context=context, action_id=new_action_id)

        task_record = self.browse(cr, uid, ids[0], context=context)
        actions = []
        if not task_record.user_id:
            actions.append({'url': take_action, 'title': _('I take it')})
        else:
            actions.append({'url': new_action, 'title': _('New Issue')})

        res['group_project_user'] = {
            'actions': actions
        }
        return res

    @api.cr_uid_context
    def message_get_reply_to(self, cr, uid, ids, default=None, context=None):
        """ Override to get the reply_to of the parent project. """
        issues = self.browse(cr, SUPERUSER_ID, ids, context=context)
        project_ids = set([issue.project_id.id for issue in issues if issue.project_id])
        aliases = self.pool['project.project'].message_get_reply_to(cr, uid, list(project_ids), default=default, context=context)
        return dict((issue.id, aliases.get(issue.project_id and issue.project_id.id or 0, False)) for issue in issues)

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(project_issue, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        try:
            for issue in self.browse(cr, uid, ids, context=context):
                if issue.partner_id:
                    issue._message_add_suggested_recipient(recipients, partner=issue.partner_id, reason=_('Customer'))
                elif issue.email_from:
                    issue._message_add_suggested_recipient(recipients, email=issue.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    def email_split(self, cr, uid, ids, msg, context=None):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        issue_ids = self.browse(cr, uid, ids, context=context)
        aliases = [issue.project_id.alias_name for issue in issue_ids if issue.project_id]
        return filter(lambda x: x.split('@')[0] not in aliases, email_list)

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(context or {})
        create_context['default_user_id'] = False
        if custom_values is None:
            custom_values = {}
        context = dict(context or {}, state_to='draft')
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)

        res_id = super(project_issue, self).message_new(cr, uid, msg, custom_values=defaults, context=create_context)
        email_list = self.email_split(cr, uid, [res_id], msg, context=context)
        partner_ids = filter(None, self._find_partner_from_emails(cr, uid, [res_id], email_list, force_create=False, context=context))
        self.message_subscribe(cr, uid, [res_id], partner_ids, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Override to update the issue according to the email. """

        email_list = self.email_split(cr, uid, ids, msg, context=context)
        partner_ids = filter(None, self._find_partner_from_emails(cr, uid, ids, email_list, force_create=False, context=context))
        self.message_subscribe(cr, uid, ids, partner_ids, context=context)
        return super(project_issue, self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

    @api.cr_uid_ids_context
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, cr, uid, thread_id, subtype=None, context=None, **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        if context is None:
            context = {}
        res = super(project_issue, self).message_post(cr, uid, thread_id, subtype=subtype, context=context, **kwargs)
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
            project_id: Issue.search_count(cr,uid, [('project_id', '=', project_id), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], context=context)
            for project_id in ids
        }

    def _issue_needaction_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        res = dict.fromkeys(ids, 0)
        projects = Issue.read_group(cr, uid, [('project_id', 'in', ids), ('message_needaction', '=', True)], ['project_id'], ['project_id'], context=context)
        res.update({project['project_id'][0]: int(project['project_id_count']) for project in projects})
        return res

    _columns = {
        'issue_count': fields.function(_issue_count, type='integer', string="Issues",),
        'issue_ids': fields.one2many('project.issue', 'project_id', string="Issues",
                                    domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)]),
        'issue_needaction_count': fields.function(_issue_needaction_count, type='integer', string="Issues",),
    }

    @api.multi
    def write(self, vals):
        res = super(project, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a project does it on its issues, too
            issues = self.with_context(active_test=False).mapped('issue_ids')
            issues.write({'active': vals['active']})
        return res


class account_analytic_account(osv.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    _columns = {
        'use_issues': fields.boolean('Issues', help="Check this box to manage customer activities through this project"),
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

    def unlink(self, cr, uid, ids, context=None):
        proj_ids = self.pool['project.project'].search(cr, uid, [('analytic_account_id', 'in', ids)])
        has_issues = self.pool['project.issue'].search(cr, uid, [('project_id', 'in', proj_ids)], count=True, context=context)
        if has_issues:
            raise UserError(_('Please remove existing issues in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink(cr, uid, ids, context=context)


class project_project(osv.Model):
    _inherit = 'project.project'

    _columns = {
        'label_issues': fields.char('Use Issues as', help="Customize the issues label, for example to call them cases."),
    }

    _defaults = {
        'use_issues': True,
        'label_issues': 'Issues',
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
        partners = {id: self.search(cr, uid, [('id', 'child_of', ids)]) for id in ids}
        return {
            partner_id: Issue.search_count(cr, uid, [('partner_id', 'in', partners[partner_id])])
            for partner_id in partners.keys()
        }

    """ Inherits partner and adds Issue information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'issue_count': fields.function(_issue_count, string='# Issues', type='integer'),
    }
