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

from base_status.base_stage import base_stage
from crm import crm
from datetime import datetime
from osv import fields,osv
from tools.translate import _
import binascii
import time
import tools

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

_ISSUE_STATE= [('draft', 'New'), ('open', 'In Progress'), ('cancel', 'Cancelled'), ('done', 'Done'),('pending', 'Pending')]

class project_issue(base_stage, osv.osv):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority, create_date desc"
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _mail_compose_message = True

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
            search_domain += ['|', '&', ('project_ids', '=', project_id), ('fold', '=', False)]
        search_domain += ['|', ('id', 'in', ids), '&', ('case_default', '=', True), ('fold', '=', False)]
        # perform search
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

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
                        if issue.project_id.resource_calendar_id:
                            hours = cal_obj.interval_hours_get(cr, uid, issue.project_id.resource_calendar_id.id,
                                                           date_create,
                                                           date_open)
                elif field in ['working_hours_close','day_close']:
                    if issue.date_closed:
                        date_close = datetime.strptime(issue.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = issue.date_closed
                        ans = date_close - date_create
                        #Calculating no. of working hours to close the issue
                        if issue.project_id.resource_calendar_id:
                            hours = cal_obj.interval_hours_get(cr, uid, issue.project_id.resource_calendar_id.id,
                               date_create,
                               date_close)
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
                    duration = float(ans.days)
                    if issue.project_id and issue.project_id.resource_calendar_id:
                        duration = float(ans.days) * 24

                        new_dates = cal_obj.interval_min_get(cr, uid,
                                                             issue.project_id.resource_calendar_id.id,
                                                             date_create,
                                                             duration, resource=resource_id)
                        no_days = []
                        date_until = datetime.strptime(date_until, '%Y-%m-%d %H:%M:%S')
                        for in_time, out_time in new_dates:
                            if in_time.date not in no_days:
                                no_days.append(in_time.date)
                            if out_time > date_until:
                                break
                        duration = len(no_days)

                if field in ['working_hours_open','working_hours_close']:
                    res[issue.id][field] = hours
                else:
                    res[issue.id][field] = abs(float(duration))

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
        'partner_id': fields.many2one('res.partner', 'Partner', select=1),
        'company_id': fields.many2one('res.company', 'Company'),
        'description': fields.text('Description'),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=_ISSUE_STATE, string="State", readonly=True,
                help='The state is set to \'Draft\', when a case is created.\
                      If the case is in progress the state is set to \'Open\'.\
                      When the case is over, the state is set to \'Done\'.\
                      If the case needs to be reviewed then the state is \
                      set to \'Pending\'.'),
        'email_from': fields.char('Email', size=128, help="These people will receive email.", select=1),
        'email_cc': fields.char('Watchers Emails', size=256, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'date_open': fields.datetime('Opened', readonly=True,select=True),
        # Project Issue fields
        'date_closed': fields.datetime('Closed', readonly=True,select=True),
        'date': fields.datetime('Date'),
        'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel."),
        'categ_ids': fields.many2many('project.category', string='Categories'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True),
        'version_id': fields.many2one('project.issue.version', 'Version'),
        'stage_id': fields.many2one ('project.task.type', 'Stage',
                        domain="['|', ('project_ids', '=', project_id), ('case_default', '=', True)]"),
        'project_id':fields.many2one('project.project', 'Project'),
        'duration': fields.float('Duration'),
        'task_id': fields.many2one('project.task', 'Task', domain="[('project_id','=',project_id)]"),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='compute_day', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='compute_day', type="float", store=True),
        'user_id': fields.many2one('res.users', 'Assigned to', required=False, select=1),
        'working_hours_open': fields.function(_compute_day, string='Working Hours to Open the Issue', \
                                multi='compute_day', type="float", store=True),
        'working_hours_close': fields.function(_compute_day, string='Working Hours to Close the Issue', \
                                multi='compute_day', type="float", store=True),
        'inactivity_days': fields.function(_compute_day, string='Days since last action', \
                                multi='compute_day', type="integer", help="Difference in days between last action and current date"),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'user_email', type='char', string='User Email', readonly=True),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'progress': fields.function(_hours_get, string='Progress (%)', multi='hours', group_operator="avg", help="Computed as: Time Spent / Total Time.",
            store = {
                'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['task_id'], 10),
                'project.task': (_get_issue_task, ['progress'], 10),
                'project.task.work': (_get_issue_work, ['hours'], 10),
            }),
    }

    def on_change_project(self, cr, uid, ids, project_id, context=None):
        return {}

    _defaults = {
        'active': 1,
        'partner_id': lambda s, cr, uid, c: s._get_default_partner(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'state': 'draft',
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': crm.AVAILABLE_PRIORITIES[2][0],
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
                'state':'pending'
            }
            self.convert_to_task_send_note(cr, uid, [bug.id], context=context)
            case_obj.write(cr, uid, [bug.id], vals, context=context)
            self.case_pending_send_note(cr, uid, [bug.id], context=context)

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
        default['name'] = issue['name'] + _(' (copy)')
        return super(project_issue, self).copy(cr, uid, id, default=default,
                context=context)

    def write(self, cr, uid, ids, vals, context=None):
        #Update last action date every time the user change the stage, the state or send a new email
        logged_fields = ['stage_id', 'state', 'message_ids']
        if any([field in vals for field in logged_fields]):
            vals['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return super(project_issue, self).write(cr, uid, ids, vals, context)

    def onchange_task_id(self, cr, uid, ids, task_id, context=None):
        result = {}
        if not task_id:
            return {'value':{}}
        task = self.pool.get('project.task').browse(cr, uid, task_id, context=context)
        return {'value':{'user_id': task.user_id.id,}}

    def case_reset(self, cr, uid, ids, context=None):
        """Resets case as draft
        """
        res = super(project_issue, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'date_open': False, 'date_closed': False})
        return res
    
    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):
        if context is None:
            context = {}
        if not stage_id:
            return {'value':{}}
        stage = self.pool.get('project.task.type').browse(cr, uid, stage_id, context)
        if stage.state == "draft":
            return {'value':{'active': True,'date_open': False, 'date_closed': False}}
        if stage.state == "open":
            cases = self.browse(cr, uid, ids, context=context)
            data = {'active': True}
            for case in cases:
                if case.stage_id and case.stage_id.state == 'draft':
                    data['date_open'] = fields.datetime.now()
                if not case.user_id:
                    data['user_id'] = uid
            return {'value':data}
        return {'value':{}}

    def create(self, cr, uid, vals, context=None):
        obj_id = super(project_issue, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    # -------------------------------------------------------
    # Stage management
    # -------------------------------------------------------

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
            search_domain += [('|')] * len(section_ids)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain.append(('case_default', '=', True))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('project.task.type').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        self.case_set(cr, uid, ids, 'cancelled', {'active': True}, context=context)
        self.case_cancel_send_note(cr, uid, ids, context=context)
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
                raise osv.except_osv(_('Warning !'), _('You cannot escalate this issue.\nThe relevant Project has not configured the Escalation Project!'))
            self.case_set(cr, uid, ids, 'draft', data, context=context)
            self.case_escalate_send_note(cr, uid, [case.id], context=context)
        return True

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None: custom_values = {}
        if context is None: context = {}
        context['state_to'] = 'draft'

        custom_values.update({
            'name':  msg.get('subject') or _("No Subject"),
            'description': msg.get('body_text'),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
        })
        if  msg.get('priority'):
            custom_values['priority'] =  msg.get('priority')
        custom_values.update(self.message_partner_by_email(cr, uid, msg.get('from'), context=context))

        res_id = super(project_issue, self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        # self.convert_to_bug(cr, uid, [res_id], context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if update_vals is None: update_vals = {}

        # Update doc values according to the message
        update_vals['description'] = msg.get('body_text', '')
        if msg.get('priority'):
            update_vals['priority'] = msg.get('priority')
        # Parse 'body_text' to find values to update
        maps = {
            'cost': 'planned_cost',
            'revenue': 'planned_revenue',
            'probability': 'probability',
        }
        for line in msg.get('body_text', '').split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower(), False):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()

        return super(project_issue, self).message_update(cr, uid, ids, update_vals=update_vals, context=context)

    # -------------------------------------------------------
    # OpenChatter methods and notifications
    # -------------------------------------------------------

    def message_get_subscribers(self, cr, uid, ids, context=None):
        """ Override to add responsible user. """
        user_ids = super(project_issue, self).message_get_subscribers(cr, uid, ids, context=context)
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id and not obj.user_id.id in user_ids:
                user_ids.append(obj.user_id.id)
        return user_ids

    def stage_set_send_note(self, cr, uid, ids, stage_id, context=None):
        """ Override of the (void) default notification method. """
        stage_name = self.pool.get('project.task.type').name_get(cr, uid, [stage_id], context=context)[0][1]
        return self.message_append_note(cr, uid, ids, body= _("Stage changed to <b>%s</b>.") % (stage_name), context=context)

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        """ Override of default prefix for notifications. """
        return 'Project issue'

    def convert_to_task_send_note(self, cr, uid, ids, context=None):
        message = _("Project issue has been <b>converted</b> into task.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def create_send_note(self, cr, uid, ids, context=None):
        message = _("Project issue has been <b>created</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def case_escalate_send_note(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.project_id:
                message = _("has been <b>escalated</b> to <em>'%s'</em>.") % (obj.project_id.name)
                obj.message_append_note(body=message, context=context)
            else:
                message = _("has been <b>escalated</b>.")
                obj.message_append_note(body=message, context=context)
        return True

project_issue()

class project(osv.osv):
    _inherit = "project.project"

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        issue_ids = self.pool.get('project.issue').search(cr, uid, [('project_id', 'in', ids)])
        for issue in self.pool.get('project.issue').browse(cr, uid, issue_ids, context):
            res[issue.project_id.id] += 1
        return res

    _columns = {
        'project_escalation_id' : fields.many2one('project.project','Project Escalation', help='If any issue is escalated from the current Project, it will be listed under the project selected here.', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'reply_to' : fields.char('Reply-To Email Address', size=256),
        'issue_count': fields.function(_issue_count, type='integer'),
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
        'use_issues' : fields.boolean('Issues Tracking', help="Check this field if this project manages issues"),
    }

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        res = super(account_analytic_account, self)._trigger_project_creation(cr, uid, vals, context=context)
        return res or vals.get('use_issues')

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
