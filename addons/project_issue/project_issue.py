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

from openerp.addons.base_status.base_stage import base_stage
from openerp.addons.project.project import _TASK_STATE
from openerp.addons.crm import crm
from datetime import datetime
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
import binascii
import time
from openerp import tools
from openerp.tools import html2plaintext

class project_issue_version(osv.osv):
    _name = "project.issue.version"
    _order = "name desc"
    _columns = {
        'name': fields.char('Version Number', size=32, required=True),
        'active': fields.boolean('Active', required=False),
    }
    _defaults = {
        'active': 1,
    }
project_issue_version()

class project_issue(base_stage, osv.osv):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority, create_date desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'state': {
            'project_issue.mt_issue_new': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['new', 'draft'],
            'project_issue.mt_issue_closed': lambda self, cr, uid, obj, ctx=None:  obj['state'] == 'done',
            'project_issue.mt_issue_started': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'open',
        },
        'stage_id': {
            'project_issue.mt_issue_stage': lambda self, cr, uid, obj, ctx=None: obj['state'] not in ['new', 'draft', 'done', 'open'],
        },
        'kanban_state': {
            'project_issue.mt_issue_blocked': lambda self, cr, uid, obj, ctx=None: obj['kanban_state'] == 'blocked',
        },
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')

        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        return super(project_issue, self).create(cr, uid, vals, context=create_context)

    def _get_default_partner(self, cr, uid, context=None):
        """ Override of base_stage to add project specific behavior """
        project_id = self._get_default_project_id(cr, uid, context)
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                return project.partner_id.id
        return super(project_issue, self)._get_default_partner(cr, uid, context=context)

    def _get_default_project_id(self, cr, uid, context=None):
        """ Gives default project by checking if present in the context """
        return self._resolve_project_id_from_context(cr, uid, context=context)

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        project_id = self._get_default_project_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], project_id, [('state', '=', 'draft')], context=context)

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
        cal_obj = self.pool.get('resource.calendar')
        res_obj = self.pool.get('resource.resource')

        res = {}
        for issue in self.browse(cr, uid, ids, context=context):

            # if the working hours on the project are not defined, use default ones (8 -> 12 and 13 -> 17 * 5), represented by None
            if not issue.project_id or not issue.project_id.resource_calendar_id:
                working_hours = None
            else:
                working_hours = issue.project_id.resource_calendar_id.id

            res[issue.id] = {}
            for field in fields:
                duration = 0
                ans = False
                hours = 0

                date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                if field in ['working_hours_open','day_open']:
                    if issue.date_open:
                        date_open = datetime.strptime(issue.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                        date_until = issue.date_open
                        #Calculating no. of working hours to open the issue
                        hours = cal_obj._interval_hours_get(cr, uid, working_hours,
                                                           date_create,
                                                           date_open,
                                                           timezone_from_uid=issue.user_id.id or uid,
                                                           exclude_leaves=False,
                                                           context=context)
                elif field in ['working_hours_close','day_close']:
                    if issue.date_closed:
                        date_close = datetime.strptime(issue.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = issue.date_closed
                        ans = date_close - date_create
                        #Calculating no. of working hours to close the issue
                        hours = cal_obj._interval_hours_get(cr, uid, working_hours,
                                                           date_create,
                                                           date_close,
                                                           timezone_from_uid=issue.user_id.id or uid,
                                                           exclude_leaves=False,
                                                           context=context)
                elif field in ['days_since_creation']:
                    if issue.create_date:
                        days_since_creation = datetime.today() - datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        res[issue.id][field] = days_since_creation.days
                    continue

                elif field in ['inactivity_days']:
                    res[issue.id][field] = 0
                    if issue.date_action_last:
                        inactive_days = datetime.today() - datetime.strptime(issue.date_action_last, '%Y-%m-%d %H:%M:%S')
                        res[issue.id][field] = inactive_days.days
                    continue
                if ans:
                    resource_id = False
                    if issue.user_id:
                        resource_ids = res_obj.search(cr, uid, [('user_id','=',issue.user_id.id)])
                        if resource_ids and len(resource_ids):
                            resource_id = resource_ids[0]
                    duration = float(ans.days) + float(ans.seconds)/(24*3600)

                if field in ['working_hours_open','working_hours_close']:
                    res[issue.id][field] = hours
                elif field in ['day_open','day_close']:
                    res[issue.id][field] = duration

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
                return {'value': {'partner_id': project.partner_id.id}}
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
        'name': fields.char('Issue', size=128, required=True),
        'active': fields.boolean('Active', required=False),
        'create_date': fields.datetime('Creation Date', readonly=True,select=True),
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
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=_TASK_STATE, string="Status", readonly=True, select=True,
                help='The status is set to \'Draft\', when a case is created.\
                      If the case is in progress the status is set to \'Open\'.\
                      When the case is over, the status is set to \'Done\'.\
                      If the case needs to be reviewed then the status is \
                      set to \'Pending\'.'),
        'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready for next stage')], 'Kanban State',
                                         track_visibility='onchange',
                                         help="A Issue's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this issue\n"
                                              " * Ready for next stage indicates the issue is ready to be pulled to the next stage",
                                         readonly=True, required=False),
        'email_from': fields.char('Email', size=128, help="These people will receive email.", select=1),
        'email_cc': fields.char('Watchers Emails', size=256, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'date_open': fields.datetime('Opened', readonly=True,select=True),
        # Project Issue fields
        'date_closed': fields.datetime('Closed', readonly=True,select=True),
        'date': fields.datetime('Date'),
        'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel."),
        'categ_ids': fields.many2many('project.category', string='Tags'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True),
        'version_id': fields.many2one('project.issue.version', 'Version'),
        'stage_id': fields.many2one ('project.task.type', 'Stage',
                        track_visibility='onchange', select=True,
                        domain="['&', ('fold', '=', False), ('project_ids', '=', project_id)]"),
        'project_id': fields.many2one('project.project', 'Project', track_visibility='onchange', select=True),
        'duration': fields.float('Duration'),
        'task_id': fields.many2one('project.task', 'Task', domain="[('project_id','=',project_id)]"),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='compute_day', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='compute_day', type="float", store=True),
        'user_id': fields.many2one('res.users', 'Assigned to', required=False, select=1, track_visibility='onchange'),
        'working_hours_open': fields.function(_compute_day, string='Working Hours to Open the Issue', \
                                multi='compute_day', type="float", store=True),
        'working_hours_close': fields.function(_compute_day, string='Working Hours to Close the Issue', \
                                multi='compute_day', type="float", store=True),
        'inactivity_days': fields.function(_compute_day, string='Days since last action', \
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
        'partner_id': lambda s, cr, uid, c: s._get_default_partner(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': crm.AVAILABLE_PRIORITIES[2][0],
        'kanban_state': 'normal',
        'user_id': lambda obj, cr, uid, context: uid,
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def set_priority(self, cr, uid, ids, priority, *args):
        """Set lead priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set lead priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set lead priority to normal
        """
        return self.set_priority(cr, uid, ids, '3')

    def convert_issue_task(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        case_obj = self.pool.get('project.issue')
        data_obj = self.pool.get('ir.model.data')
        task_obj = self.pool.get('project.task')

        result = data_obj._get_id(cr, uid, 'project', 'view_task_search_form')
        res = data_obj.read(cr, uid, result, ['res_id'])
        id2 = data_obj._get_id(cr, uid, 'project', 'view_task_form2')
        id3 = data_obj._get_id(cr, uid, 'project', 'view_task_tree2')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        for bug in case_obj.browse(cr, uid, ids, context=context):
            new_task_id = task_obj.create(cr, uid, {
                'name': bug.name,
                'partner_id': bug.partner_id.id,
                'description':bug.description,
                'date_deadline': bug.date,
                'project_id': bug.project_id.id,
                # priority must be in ['0','1','2','3','4'], while bug.priority is in ['1','2','3','4','5']
                'priority': str(int(bug.priority) - 1),
                'user_id': bug.user_id.id,
                'planned_hours': 0.0,
            })
            vals = {
                'task_id': new_task_id,
                'stage_id': self.stage_find(cr, uid, [bug], bug.project_id.id, [('state', '=', 'pending')], context=context),
            }
            message = _("Project issue <b>converted</b> to task.")
            self.message_post(cr, uid, [bug.id], body=message, context=context)
            case_obj.write(cr, uid, [bug.id], vals, context=context)

        return  {
            'name': _('Tasks'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'project.task',
            'res_id': int(new_task_id),
            'view_id': False,
            'views': [(id2,'form'),(id3,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id'],
            'nodestroy': True
        }

    def copy(self, cr, uid, id, default=None, context=None):
        issue = self.read(cr, uid, id, ['name'], context=context)
        if not default:
            default = {}
        default = default.copy()
        default.update(name=_('%s (copy)') % (issue['name']))
        return super(project_issue, self).copy(cr, uid, id, default=default,
                context=context)

    def write(self, cr, uid, ids, vals, context=None):
    
        #Update last action date every time the user changes the stage
        if 'stage_id' in vals:
            vals['date_action_last'] = time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            if 'kanban_state' not in vals:
                vals.update(kanban_state='normal')
            state = self.pool.get('project.task.type').browse(cr, uid, vals['stage_id'], context=context).state
            for issue in self.browse(cr, uid, ids, context=context):
                # Change from draft to not draft EXCEPT cancelled: The issue has been opened -> set the opening date
                if issue.state == 'draft' and state not in ('draft', 'cancelled'):
                    vals['date_open'] = time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
                # Change from not done to done: The issue has been closed -> set the closing date
                if issue.state != 'done' and state == 'done':
                    vals['date_closed'] = time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        return super(project_issue, self).write(cr, uid, ids, vals, context)

    def onchange_task_id(self, cr, uid, ids, task_id, context=None):
        if not task_id:
            return {'value': {}}
        task = self.pool.get('project.task').browse(cr, uid, task_id, context=context)
        return {'value': {'user_id': task.user_id.id, }}

    def case_reset(self, cr, uid, ids, context=None):
        """Resets case as draft
        """
        res = super(project_issue, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'date_open': False, 'date_closed': False})
        return res

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

    def set_kanban_state_blocked(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'kanban_state': 'blocked'}, context=context)

    def set_kanban_state_normal(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'kanban_state': 'normal'}, context=context)

    def set_kanban_state_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'kanban_state': 'done'}, context=context)

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

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        self.case_set(cr, uid, ids, 'cancelled', {'active': True}, context=context)
        return True

    def case_escalate(self, cr, uid, ids, context=None):
        cases = self.browse(cr, uid, ids)
        for case in cases:
            data = {}
            if case.project_id.project_escalation_id:
                data['project_id'] = case.project_id.project_escalation_id.id
                if case.project_id.project_escalation_id.user_id:
                    data['user_id'] = case.project_id.project_escalation_id.user_id.id
                if case.task_id:
                    self.pool.get('project.task').write(cr, uid, [case.task_id.id], {'project_id': data['project_id'], 'user_id': False})
            else:
                raise osv.except_osv(_('Warning!'), _('You cannot escalate this issue.\nThe relevant Project has not configured the Escalation Project!'))
            self.case_set(cr, uid, ids, 'draft', data, context=context)
        return True

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_get_reply_to(self, cr, uid, ids, context=None):
        """ Override to get the reply_to of the parent project. """
        return [issue.project_id.message_get_reply_to()[0] if issue.project_id else False
                    for issue in self.browse(cr, uid, ids, context=context)]

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
        if context is None:
            context = {}
        context['state_to'] = 'draft'

        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''

        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        defaults.update(custom_values)
        res_id = super(project_issue, self).message_new(cr, uid, msg, custom_values=defaults, context=context)
        return res_id

    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification', subtype=None, parent_id=False, attachments=None, context=None, content_subtype='html', **kwargs):
        """ Overrides mail_thread message_post so that we can set the date of last action field when
            a new message is posted on the issue.
        """
        if context is None:
            context = {}
        
        res = super(project_issue, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)
        
        if thread_id:
            self.write(cr, uid, thread_id, {'date_action_last': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)    
        
        return res   

class project(osv.osv):
    _inherit = "project.project"

    def _get_alias_models(self, cr, uid, context=None):
        return [('project.task', "Tasks"), ("project.issue", "Issues")]

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        issue_ids = self.pool.get('project.issue').search(cr, uid, [('project_id', 'in', ids)])
        for issue in self.pool.get('project.issue').browse(cr, uid, issue_ids, context):
            if issue.state not in ('done', 'cancelled'):
                res[issue.project_id.id] += 1
        return res

    _columns = {
        'project_escalation_id' : fields.many2one('project.project','Project Escalation', help='If any issue is escalated from the current Project, it will be listed under the project selected here.', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'issue_count': fields.function(_issue_count, type='integer', string="Unclosed Issues"),
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

project()

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    _columns = {
        'use_issues' : fields.boolean('Issues', help="Check this field if this project manages issues"),
    }

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        if context is None: context = {}
        res = super(account_analytic_account, self)._trigger_project_creation(cr, uid, vals, context=context)
        return res or (vals.get('use_issues') and not 'project_creation_in_progress' in context)

account_analytic_account()

class project_project(osv.osv):
    _inherit = 'project.project'
    _defaults = {
        'use_issues': True
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
