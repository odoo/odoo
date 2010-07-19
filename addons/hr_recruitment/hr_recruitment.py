# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from crm import crm
import tools
import collections
import binascii
import tools
from tools.translate import _

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('open', 'In Progress'),
    ('cancel', 'Refused'),
    ('done', 'Hired'),
    ('pending', 'Pending')
]

AVAILABLE_PRIORITIES = [
    ('5', 'Not Good'),
    ('4', 'On Average'),
    ('3', 'Good'),
    ('2', 'Very Good'),
    ('1', 'Excellent')
]

class hr_recruitment_stage(osv.osv):
    """ Stage of HR Recruitment """

    _name = "hr.recruitment.stage"
    _description = "Stage of Recruitment"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of stages."),
        'requirements': fields.text('Requirements')
    }
    _defaults = {
        'sequence': 1,
    }
hr_recruitment_stage()

class hr_applicant(osv.osv, crm.crm_case):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "id desc"
    _inherit = ['mailgate.thread']
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the case without removing it."),
        'description': fields.text('Description'),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'email_cc': fields.text('Watchers Emails', size=252 , help="Every email sent or received  for the related record will be forwarded to these addresses(Comma-separated)"),
        'probability': fields.float('Probability'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Update Date' , readonly=True),
#        'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
#                         domain="[('section_id','=',section_id),\
#                        ('object_id.model', '=', 'crm.opportunity')]"),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage', \
                         domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.opportunity')]"),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        # Applicant Columns
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed': fields.float('Proposed Salary', help="Salary Proposed by the Organisation"),
        'salary_expected': fields.float('Expected Salary', help="Salary Expected by Applicant"),
        'availability': fields.integer('Availability (Days)'),
        'partner_name': fields.char("Applicant's Name", size=64),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]"),
        'department_id':fields.many2one('hr.department', 'Department'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'survey' : fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response' : fields.integer("Response"),
        'reference': fields.char('Reference', size=128),
    }

    def _get_stage(self, cr, uid, context=None):
        if context is None:
            context = {}
        ids = self.pool.get('hr.recruitment.stage').search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'active': lambda *a: 1,
        'stage_id': _get_stage,
        'user_id':  lambda self, cr, uid, context: uid,
#        'user_id': crm.crm_case._get_default_user,
        'email_from': crm.crm_case. _get_default_email,
        'state': lambda *a: 'draft',
        'section_id': crm.crm_case. _get_section,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

    def onchange_job(self,cr, uid, ids, job, context={}):
        result = {}
        if job:
            job_obj = self.pool.get('hr.job')
            result['department_id'] = job_obj.browse(cr, uid, job).department_id.id
            return {'value': result}
        return {'value': {'department_id': []}}

    def stage_previous(self, cr, uid, ids, context=None):
        """This function computes previous stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = self.pool.get('hr.recruitment.stage').search(cr, uid, [])
            if st and stage_ids.index(st):
                self.write(cr, uid, [case.id], {'stage_id': stage_ids[stage_ids.index(st)-1]})
        return True

    def stage_next(self, cr, uid, ids, context=None):
        """This function computes next stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = self.pool.get('hr.recruitment.stage').search(cr, uid, [])
            if st and len(stage_ids) != stage_ids.index(st)+1:
                self.write(cr, uid, [case.id], {'stage_id': stage_ids[stage_ids.index(st)+1]})
        return True

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Opportunity to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Meeting view
        """
        value = {}
        for opp in self.browse(cr, uid, ids):
            data_obj = self.pool.get('ir.model.data')

            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            context = {
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',
                'default_name': opp.name
            }
            value = {
                'name': ('Meetings'),
                'domain': "[('user_id','=',%s)]" % (uid),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1, 'calendar'), (id2, 'form'), (id3, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id'],
                'nodestroy': True
            }
        return value

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for print survey form.
        """
        if not context:
            context = {}
        record = self.browse(cr, uid, ids, context)
        record = record and record[0]
        context.update({'survey_id': record.survey.id, 'response_id' : [record.response], 'response_no':0, })
        value = self.pool.get("survey").action_print_survey(cr, uid, ids, context)
        return value

    def message_new(self, cr, uid, msg, context):
        """
        Automatically calls when new email message arrives
        
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        """

        mailgate_pool = self.pool.get('email.server.tools')

        subject = msg.get('subject')
        body = msg.get('body')
        msg_from = msg.get('from')
        priority = msg.get('priority')
        
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if msg.get('priority', False):
            vals['priority'] = priority
        
        res = mailgate_pool.get_partner(cr, uid, msg.get('from'))
        if res:
            vals.update(res)
        res = self.create(cr, uid, vals, context)
        
        message = _('A Job Request created') + " '" + subject + "' " + _("from Mailgate.")
        self.log(cr, uid, res, message)
        
        attachents = msg.get('attachments', [])
        for attactment in attachents or []:
            data_attach = {
                'name': attactment,
                'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                'datas_fname': attactment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            self.pool.get('ir.attachment').create(cr, uid, data_attach)

        return res

    def message_update(self, cr, uid, ids, vals={}, msg="", default_act='pending', context={}):
        """ 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of update mail’s IDs 
        """
        
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        
        msg_from = msg['from']
        vals.update({
            'description': msg['body']
        })
        if msg.get('priority', False):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = { }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower(), False):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        
        vals.update(vls)
        res = self.write(cr, uid, ids, vals)
        return res

    def msg_send(self, cr, uid, id, *args, **argv):

        """ Send The Message
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of email’s IDs
            @param *args: Return Tuple Value
            @param **args: Return Dictionary of Keyword Value
        """
        return True
    
    def case_open(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        res = super(hr_applicant, self).case_open(cr, uid, ids, *args)
        for (id, name) in self.name_get(cr, uid, ids):
            message = _('Job request for') + " '" + name + "' "+ _("is Open.")
            self.log(cr, uid, id, message)
        return res

    def case_close(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        res = super(hr_applicant, self).case_close(cr, uid, ids, *args)
        for (id, name) in self.name_get(cr, uid, ids):
            message = _('Applicant ') + " '" + name + "' "+ _("is Hired.")
            self.log(cr, uid, id, message)
        return res

hr_applicant()

class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _columns = {
        'survey_id': fields.many2one('survey', 'Survey'),
    }

hr_job()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
