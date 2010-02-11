# -*- coding: utf-8 -*-
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

import time
import re
import os
import base64
import tools
import mx.DateTime

from tools.translate import _
from osv import fields 
from osv import osv 
from osv import orm
from osv.orm import except_orm

MAX_LEVEL = 15
AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

AVAILABLE_PRIORITIES = [
    ('5','Lowest'),
    ('4','Low'),
    ('3','Normal'),
    ('2','High'),
    ('1','Highest')
]

icon_lst = {
    'form':'STOCK_NEW',
    'tree':'STOCK_JUSTIFY_FILL',
    'calendar':'STOCK_SELECT_COLOR'
}

class crm_case_section(osv.osv):
    _name = "crm.case.section"
    _description = "Case Section"
    _order = "name"
    _columns = {
        'name': fields.char('Case Section',size=64, required=True, translate=True),
        'code': fields.char('Section Code',size=8),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the case section without removing it."),
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"),
        'user_id': fields.many2one('res.users', 'Responsible User'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by Open ERP about cases in this section"),
        'parent_id': fields.many2one('crm.case.section', 'Parent Section'),
        'child_ids': fields.one2many('crm.case.section', 'parent_id', 'Child Sections'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'allow_unlink': lambda *a: 1,
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the section must be unique !')
    ]
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from crm_case_section where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive sections.', ['parent_id'])
    ]
    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res
crm_case_section()

class crm_case_categ(osv.osv):
    _name = "crm.case.categ"
    _description = "Category of case"

    _columns = {
        'name': fields.char('Case Category Name', size=64, required=True, translate=True),
        'probability': fields.float('Probability (%)', required=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
        'object_id': fields.many2one('ir.model','Object Name'),        
    }
    def _find_object_id(self, cr, uid, context=None):
        object_id = context and context.get('object_id', False) or False
        ids =self.pool.get('ir.model').search(cr, uid, [('model', '=', object_id)])
        return ids and ids[0] 
    _defaults = {
        'probability': lambda *args: 0.0,
        'object_id' : _find_object_id
    }
#               
crm_case_categ()

class crm_case_resource_type(osv.osv):
    _name = "crm.case.resource.type"
    _description = "Resource Type of case"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Case Resource Type', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
        'object_id': fields.many2one('ir.model','Object Name'),        
    }
    def _find_object_id(self, cr, uid, context=None):
        object_id = context and context.get('object_id', False) or False
        ids =self.pool.get('ir.model').search(cr, uid, [('model', '=', object_id)])
        return ids and ids[0] 
    _defaults = {
        'object_id' : _find_object_id
    }    
crm_case_resource_type()


class crm_case_stage(osv.osv):
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"
    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case stages."),
        'object_id': fields.many2one('ir.model','Object Name'),
    }
    def _find_object_id(self, cr, uid, context=None):
        object_id = context and context.get('object_id', False) or False
        ids =self.pool.get('ir.model').search(cr, uid, [('model', '=', object_id)])
        return ids and ids[0]     
    _defaults = {
        'sequence': lambda *args: 1,
        'object_id' : _find_object_id
    }
    
crm_case_stage()


class crm_case_rule(osv.osv):
    _name = "crm.case.rule"
    _description = "Case Rule"
    _columns = {
        'name': fields.char('Rule Name',size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the case rule without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case rules."),

        'trg_state_from': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Case State', size=16),
        'trg_state_to': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Button Pressed', size=16),

        'trg_date_type':  fields.selection([
            ('none','None'),
            ('create','Creation Date'),
            ('action_last','Last Action Date'),
            ('deadline','Deadline'),
            ('date','Date'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date',help="Delay After Trigger Date, specifies you can put a negative number " \
                                                             "if you need a delay before the trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'),('hour','Hours'),('day','Days'),('month','Months')], 'Delay type'),

        'trg_section_id': fields.many2one('crm.case.section', 'Section'),
    
#        'trg_categ_id':  fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',trg_section_id)]"),
        'trg_user_id':  fields.many2one('res.users', 'Responsible'),

        'trg_partner_id': fields.many2one('res.partner', 'Partner'),
        'trg_partner_categ_id': fields.many2one('res.partner.category', 'Partner Category'),

        'trg_priority_from': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Minimum Priority'),
        'trg_priority_to': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Maximim Priority'),
        'trg_max_history': fields.integer('Maximum Communication History'),

        'act_method': fields.char('Call Object Method', size=64),
        'act_state': fields.selection([('','')]+AVAILABLE_STATES, 'Set state to', size=16),
        'act_section_id': fields.many2one('crm.case.section', 'Set section to'),
        'act_user_id': fields.many2one('res.users', 'Set responsible to'),
        'act_priority': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Set priority to'),
        'act_email_cc': fields.char('Add watchers (Cc)', size=250, help="These people will receive a copy of the future communication between partner and users by email"),

        'act_remind_partner': fields.boolean('Remind Partner', help="Check this if you want the rule to send a reminder by email to the partner."),
        'act_remind_user': fields.boolean('Remind responsible', help="Check this if you want the rule to send a reminder by email to the user."),
        'act_remind_attach': fields.boolean('Remind with attachment', help="Check this if you want that all documents attached to the case be attached to the reminder email sent."),

        'act_mail_to_user': fields.boolean('Mail to responsible',help="Check this if you want the rule to send an email to the responsible person."),
        'act_mail_to_partner': fields.boolean('Mail to partner',help="Check this if you want the rule to send an email to the partner."),
        'act_mail_to_watchers': fields.boolean('Mail to watchers (CC)',help="Check this if you want the rule to mark CC(mail to any other person defined in actions)."),
        'act_mail_to_email': fields.char('Mail to these emails', size=128,help="Email-id of the persons whom mail is to be sent"),
        'act_mail_body': fields.text('Mail body',help="Content of mail"),
        'regex_name' : fields.char('Regular Expression on Case Name', size=128),
        'regex_history' : fields.char('Regular Expression on Case History', size=128),
        'server_action_id' : fields.many2one('ir.actions.server','Server Action',help="Describes the action name." \
                                                    "eg:on which object which ation to be taken on basis of which condition"),
    }
    _defaults = {
        'active': lambda *a: 1,
        'trg_date_type': lambda *a: 'none',
        'trg_date_range_type': lambda *a: 'day',
        'act_mail_to_user': lambda *a: 0,
        'act_remind_partner': lambda *a: 0,
        'act_remind_user': lambda *a: 0,
        'act_mail_to_partner': lambda *a: 0,
        'act_mail_to_watchers': lambda *a: 0,
    }
    _order = 'sequence'

    def _check(self, cr, uid, ids=False, context={}):
        '''
        Function called by the scheduler to process cases for date actions
        Only works on not done and cancelled cases
        '''
        cr.execute('select * from crm_case \
                where (date_action_last<%s or date_action_last is null) \
                and (date_action_next<=%s or date_action_next is null) \
                and state not in (\'cancel\',\'done\')',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                    time.strftime('%Y-%m-%d %H:%M:%S')))
        ids2 = map(lambda x: x[0], cr.fetchall() or [])
        case_obj = self.pool.get('crm.case')
        cases = case_obj.browse(cr, uid, ids2, context)
        return case_obj._action(cr, uid, cases, False, context=context)


    def _check_mail(self, cr, uid, ids, context=None):
        caseobj = self.pool.get('crm.case')
        emptycase = orm.browse_null()
        for rule in self.browse(cr, uid, ids):
            if rule.act_mail_body:
                try:
                    caseobj.format_mail(emptycase, rule.act_mail_body)
                except (ValueError, KeyError, TypeError):
                    return False
        return True

    _constraints = [
        (_check_mail, 'Error: The mail is not well formated', ['act_mail_body']),
    ]

crm_case_rule()

def _links_get(self, cr, uid, context={}):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]


class crm_case(osv.osv):
    _name = "crm.case"
    _description = "Case"

    def _email_last(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for case in self.browse(cursor, user, ids):
            if case.history_line:
                res[case.id] = case.history_line[0].description
            else:
                res[case.id] = False
        return res

    def copy(self, cr, uid, id, default=None, context={}):
        if not default: default = {}
        default.update( {'state':'draft', 'id':False})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    def _get_log_ids(self, cr, uid, ids, field_names, arg, context={}):
        result = {}
        history_obj = False
        model_obj = self.pool.get('ir.model')
        if 'history_line' in field_names:
            history_obj = self.pool.get('crm.case.history')
            name = 'history_line'
        if 'log_ids' in field_names:
            history_obj = self.pool.get('crm.case.log')
            name = 'log_ids'
        if not history_obj:
            return result
        for case in self.browse(cr, uid, ids, context):
            model_ids = model_obj.search(cr, uid, [('model','=',case._name)])
            history_ids = history_obj.search(cr, uid, [('model_id','=',model_ids[0]),('res_id','=',case.id)])             
            if history_ids:
                result[case.id] = {name:history_ids}
            else:
                result[case.id] = {name:[]}         
        return result

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Description', size=1024, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the case without removing it."),
        'description': fields.text('Your action'),
        'section_id': fields.many2one('crm.case.section', 'Section', select=True, help='Section to which Case belongs to. Define Responsible user and Email account for mail gateway.'),
        'email_from': fields.char('Partner Email', size=128, help="These people will receive email."),
        'email_cc': fields.char('Watchers Emails', size=252 , help="These people will receive a copy of the future" \
                                                                    " communication between partner and users by email"),
        'email_last': fields.function(_email_last, method=True,
            string='Latest E-Mail', type='text'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"),
        'date': fields.datetime('Date'),
        'create_date': fields.datetime('Created' ,readonly=True),
        'date_deadline': fields.datetime('Deadline'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'history_line': fields.function(_get_log_ids, method=True, type='one2many', multi="history_line", relation="crm.case.history", string="Communication"),
        'log_ids': fields.function(_get_log_ids, method=True, type='one2many', multi="log_ids", relation="crm.case.log", string="Logs History"),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),

        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'company_id': fields.many2one('res.company','Company'),
    }
    def _get_default_partner_address(self, cr, uid, context):
        if not context.get('portal',False):
            return False
        return self.pool.get('res.users').browse(cr, uid, uid, context).address_id.id
    def _get_default_partner(self, cr, uid, context):
        if not context.get('portal',False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if not user.address_id:
            return False
        return user.address_id.partner_id.id
    def _get_default_email(self, cr, uid, context):
        if not context.get('portal',False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if not user.address_id:
            return False
        return user.address_id.email
    def _get_default_user(self, cr, uid, context):
        if context.get('portal', False):
            return False
        return uid

    def _get_section(self, cr, uid, context):
       user = self.pool.get('res.users').browse(cr, uid, uid,context=context)
       return user.context_section_id

    _defaults = {
        'active': lambda *a: 1,
        'user_id': _get_default_user,
        'partner_id': _get_default_partner,
        'partner_address_id': _get_default_partner_address,
        'email_from': _get_default_email,
        'state': lambda *a: 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'section_id': _get_section,
    }
    _order = 'date_deadline desc, date desc,id desc'

    def unlink(self, cr, uid, ids, context={}):
        for case in self.browse(cr, uid, ids, context):
            if (not case.section_id.allow_unlink) and (case.state <> 'draft'):
                raise osv.except_osv(_('Warning !'),
                    _('You can not delete this case. You should better cancel it.'))
        return super(crm_case, self).unlink(cr, uid, ids, context)

    def stage_next(self, cr, uid, ids, context={}):
        ok = False
        sid = self.pool.get('crm.case.stage').search(cr, uid, [('object_id.model', '=', self._name)], context=context)
        s = {}
        previous = {}
        for stage in self.pool.get('crm.case.stage').browse(cr, uid, sid, context=context):
            section = stage.section_id.id or False
            s.setdefault(section, {})
            s[section][previous.get(section, False)] = stage.id
            previous[section] = stage.id

        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            if section in s:
                st = case.stage_id.id  or False
                if st in s[section]:
                    self.write(cr, uid, [case.id], {'stage_id': s[section][st]})

        return True

    def onchange_categ_id(self, cr, uid, ids, categ, context={}):
        if not categ:
            return {'value':{}}
        cat = self.pool.get('crm.case.categ').browse(cr, uid, categ, context).probability
        return {'value':{'probability':cat}}

    def onchange_case_id(self, cr, uid, ids, case_id, name, partner_id, context={}):
        if not case_id:
            return {}
        case = self.browse(cr, uid, case_id, context=context)
        value = {}
        if not name:
            value['name'] = case.name
        if (not partner_id) and case.partner_id:
            value['partner_id'] = case.partner_id.id
            if case.partner_address_id:
                value['partner_address_id'] = case.partner_address_id.id
            if case.email_from:
                value['email_from'] = case.email_from
        return {'value': value}

    def _action(self, cr, uid, cases, state_to, scrit=None, context={}):
        if not scrit:
            scrit = []
        action_ids = self.pool.get('crm.case.rule').search(cr, uid, scrit)
        level = MAX_LEVEL
        while len(action_ids) and level:
            newactions = []
            actions = self.pool.get('crm.case.rule').browse(cr, uid, action_ids, context)
            for case in cases:
                for action in actions:
                    ok = True
                    ok = ok and (not action.trg_state_from or action.trg_state_from==case.state)
                    ok = ok and (not action.trg_state_to or action.trg_state_to==state_to)
                    ok = ok and (not action.trg_section_id or action.trg_section_id.id==case.section_id.id)
                    ok = ok and (not action.trg_categ_id or action.trg_categ_id.id==case.categ_id.id)
                    ok = ok and (not action.trg_user_id.id or action.trg_user_id.id==case.user_id.id)
                    ok = ok and (not action.trg_partner_id.id or action.trg_partner_id.id==case.partner_id.id)
                    ok = ok and (not action.trg_max_history or action.trg_max_history<=(len(case.history_line)+1))
                    ok = ok and (
                        not action.trg_partner_categ_id.id or
                        (
                            case.partner_id.id and
                            (action.trg_partner_categ_id.id in map(lambda x: x.id, case.partner_id.category_id or []))
                        )
                    )
                    ok = ok and (not action.trg_priority_from or action.trg_priority_from>=case.priority)
                    ok = ok and (not action.trg_priority_to or action.trg_priority_to<=case.priority)

                    reg_name = action.regex_name
                    result_name = True
                    if reg_name:
                        ptrn = re.compile(str(reg_name))
                        _result = ptrn.search(str(case.name))
                        if not _result:
                            result_name = False
                    regex_n = not reg_name or result_name
                    ok = ok and regex_n

                    reg_history = action.regex_history
                    result_history = True
                    if reg_history:
                        ptrn = re.compile(str(reg_history))
                        if case.history_line:
                            _result = ptrn.search(str(case.history_line[0].description))
                            if not _result:
                                result_history = False
                    regex_h = not reg_history or result_history
                    ok = ok and regex_h

                    if not ok:
                        continue

                    base = False
                    if action.trg_date_type=='create':
                        base = mx.DateTime.strptime(case.create_date[:19], '%Y-%m-%d %H:%M:%S')
                    elif action.trg_date_type=='action_last':
                        if case.date_action_last:
                            base = mx.DateTime.strptime(case.date_action_last, '%Y-%m-%d %H:%M:%S')
                        else:
                            base = mx.DateTime.strptime(case.create_date[:19], '%Y-%m-%d %H:%M:%S')
                    elif action.trg_date_type=='deadline' and case.date_deadline:
                        base = mx.DateTime.strptime(case.date_deadline, '%Y-%m-%d %H:%M:%S')
                    elif action.trg_date_type=='date' and case.date:
                        base = mx.DateTime.strptime(case.date, '%Y-%m-%d %H:%M:%S')
                    if base:
                        fnct = {
                            'minutes': lambda interval: mx.DateTime.RelativeDateTime(minutes=interval),
                            'day': lambda interval: mx.DateTime.RelativeDateTime(days=interval),
                            'hour': lambda interval: mx.DateTime.RelativeDateTime(hours=interval),
                            'month': lambda interval: mx.DateTime.RelativeDateTime(months=interval),
                        }
                        d = base + fnct[action.trg_date_range_type](action.trg_date_range)
                        dt = d.strftime('%Y-%m-%d %H:%M:%S')
                        ok = (dt <= time.strftime('%Y-%m-%d %H:%M:%S')) and \
                                ((not case.date_action_next) or \
                                (dt >= case.date_action_next and \
                                case.date_action_last < case.date_action_next))
                        if not ok:
                            if not case.date_action_next or dt < case.date_action_next:
                                case.date_action_next = dt
                                self.write(cr, uid, [case.id], {'date_action_next': dt}, context)

                    else:
                        ok = action.trg_date_type=='none'

                    if ok:
                        if action.server_action_id:
                            context.update({'active_id':case.id,'active_ids':[case.id]})
                            self.pool.get('ir.actions.server').run(cr, uid, [action.server_action_id.id], context)
                        write = {}
                        if action.act_state:
                            case.state = action.act_state
                            write['state'] = action.act_state
                        if action.act_section_id:
                            case.section_id = action.act_section_id
                            write['section_id'] = action.act_section_id.id
                        if action.act_user_id:
                            case.user_id = action.act_user_id
                            write['user_id'] = action.act_user_id.id
                        if action.act_priority:
                            case.priority = action.act_priority
                            write['priority'] = action.act_priority
                        if action.act_email_cc:
                            if '@' in (case.email_cc or ''):
                                emails = case.email_cc.split(",")
                                if  action.act_email_cc not in emails:# and '<'+str(action.act_email_cc)+">" not in emails:
                                    write['email_cc'] = case.email_cc+','+action.act_email_cc
                            else:
                                write['email_cc'] = action.act_email_cc
                        write['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        self.write(cr, uid, [case.id], write, context)
                        caseobj = self.pool.get('crm.case')
                        if action.act_remind_user:
                            caseobj.remind_user(cr, uid, [case.id], context, attach=action.act_remind_attach)
                        if action.act_remind_partner:
                            caseobj.remind_partner(cr, uid, [case.id], context, attach=action.act_remind_attach)
                        if action.act_method:
                            getattr(caseobj, 'act_method')(cr, uid, [case.id], action, context)
                        emails = []
                        if action.act_mail_to_user:
                            if case.user_id and case.user_id.address_id:
                                emails.append(case.user_id.address_id.email)
                        if action.act_mail_to_partner:
                            emails.append(case.email_from)
                        if action.act_mail_to_watchers:
                            emails += (action.act_email_cc or '').split(',')
                        if action.act_mail_to_email:
                            emails += (action.act_mail_to_email or '').split(',')
                        emails = filter(None, emails)
                        if len(emails) and action.act_mail_body:
                            emails = list(set(emails))
                            self.email_send(cr, uid, case, emails, action.act_mail_body)
                        break
            action_ids = newactions
            level -= 1
        return True

    def format_body(self, body):
        return body and tools.ustr(body.encode('ascii', 'replace')) or ''

    def format_mail(self, case, body):
        data = {
            'case_id': case.id,
            'case_subject': case.name,
            'case_date': case.date,
            'case_description': case.description,

            'case_user': (case.user_id and case.user_id.name) or '/',
            'case_user_email': (case.user_id and case.user_id.address_id and case.user_id.address_id.email) or '/',
            'case_user_phone': (case.user_id and case.user_id.address_id and case.user_id.address_id.phone) or '/',

            'email_from': case.email_from,
            'partner': (case.partner_id and case.partner_id.name) or '/',
            'partner_email': (case.partner_address_id and case.partner_address_id.email) or '/',
        }
        return self.format_body(body % data)


    def __history(self, cr, uid, cases, keyword, history=False, email=False, details=None, context={}):
        model_obj = self.pool.get('ir.model')        
        for case in cases:
            model_ids = model_obj.search(cr, uid, [('model','=',case._name)])            
            data = {
                'name': keyword,                
                'user_id': uid,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model_id' : model_ids and model_ids[0] or False,
                'res_id': case.id,
                'section_id': case.section_id.id
            }
            obj = self.pool.get('crm.case.log')
            if history and case.description:
                obj = self.pool.get('crm.case.history')
                data['description'] = details or case.description
                data['email'] = email or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or False
            res = obj.create(cr, uid, data, context)            
        return True
    _history = __history

    def create(self, cr, uid, *args, **argv):
        res = super(crm_case, self).create(cr, uid, *args, **argv)
        cases = self.browse(cr, uid, [res])
        cases[0].state # to fill the browse record cache
        self._action(cr,uid, cases, 'draft')
        return res

    def remind_partner(self, cr, uid, ids, context={}, attach=False):
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context={}, attach=False, 
            destination=True):
        for case in self.browse(cr, uid, ids):
            if not case.section_id.reply_to:
                raise osv.except_osv(_('Error!'), ("Reply To is not specified in Section"))
            if not case.email_from:
                raise osv.except_osv(_('Error!'), ("Partner Email is not specified in Case"))
            if case.section_id.reply_to and case.email_from:
                src = case.email_from
                dest = case.section_id.reply_to
                body = case.email_last or case.description
                if not destination:
                    src, dest = dest, src
                    if case.user_id.signature:
                        body += '\n\n%s' % (case.user_id.signature or '')
                dest = [dest]

                attach_to_send = None

                if attach:
                    attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', 'crm.case'), ('res_id', '=', case.id)])
                    attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname','datas'])
                    attach_to_send = map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send)

                # Send an email
                flag = tools.email_send(
                    src,
                    dest,
                    "Reminder: [%s] %s" % (str(case.id), case.name, ),
                    self.format_body(body),
                    reply_to=case.section_id.reply_to,
                    openobject_id=str(case.id),
                    attach=attach_to_send
                )
                if flag:
                    raise osv.except_osv(_('Email!'),("Email Successfully Sent"))
                else:
                    raise osv.except_osv(_('Email Fail!'),("Email is not sent successfully"))
        return True

    def add_reply(self, cursor, user, ids, context=None):
        for case in self.browse(cursor, user, ids, context=context):
            if case.email_last:
                description = email_last
                self.write(cursor, user, case.id, {
                    'description': '> ' + description.replace('\n','\n> '),
                    }, context=context)
        return True

    def case_log(self, cr, uid, ids,context={}, email=False, *args):
        cases = self.browse(cr, uid, ids)
        self.__history(cr, uid, cases, _('Historize'), history=True, email=email)
        return self.write(cr, uid, ids, {'description': False, 'som': False,
            'canal_id': False})

    def case_log_reply(self, cr, uid, ids, context={}, email=False, *args):
        cases = self.browse(cr, uid, ids)
        for case in cases:
            if not case.email_from:
                raise osv.except_osv(_('Error!'),
                        _('You must put a Partner eMail to use this action!'))
            if not case.user_id:
                raise osv.except_osv(_('Error!'),
                        _('You must define a responsible user for this case in order to use this action!'))
            if not case.description:
                raise osv.except_osv(_('Error!'),
                        _('Can not send mail with empty body,you should have description in the body'))
        self.__history(cr, uid, cases, _('Send'), history=True, email=False)
        for case in cases:
            self.write(cr, uid, [case.id], {
                'description': False,
                'som': False,
                'canal_id': False,
                })
            emails = [case.email_from] + (case.email_cc or '').split(',')
            emails = filter(None, emails)
            body = case.description or ''
            if case.user_id.signature:
                body += '\n\n%s' % (case.user_id.signature)

            emailfrom = case.user_id.address_id and case.user_id.address_id.email or False
            if not emailfrom:
                raise osv.except_osv(_('Error!'),
                        _("No E-Mail ID Found for your Company address!"))

            tools.email_send(
                emailfrom,
                emails,
                '['+str(case.id)+'] '+case.name,
                self.format_body(body),
                reply_to=case.section_id.reply_to,
                openobject_id=str(case.id)
            )
        return True

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        if not part:
            return {'value':{'partner_address_id': False, 
                            'email_from': False,
                            'partner_name2': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
        data = {'partner_address_id': addr['contact']}
        data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value':data}

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        data = {}
        if not add:
            return {'value': {'email_from': False, 'partner_name2': False}}
        address= self.pool.get('res.partner.address').browse(cr, uid, add)
        data['email_from'] = address.email
        data['partner_name2'] = address.name or ''
        return {'value': data}

    def case_close(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__history(cr, uid, cases, _('Close'))
        self.write(cr, uid, ids, {'state':'done', 'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
        #
        # We use the cache of cases to keep the old case state
        #
        self._action(cr,uid, cases, 'done')
        return True

    def case_escalate(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        for case in cases:
            data = {'active':True, 'user_id': False}
            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.user_id:
                    data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error !'), _('You can not escalate this case.\nYou are already at the top level.'))
            self.write(cr, uid, ids, data)
        cases = self.browse(cr, uid, ids)
        self.__history(cr, uid, cases, _('Escalate'))
        self._action(cr, uid, cases, 'escalate')
        return True


    def case_open(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        self.__history(cr, uid, cases, _('Open'))
        for case in cases:
            data = {'state':'open', 'active':True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, ids, data)
        self._action(cr,uid, cases, 'open')
        return True


    def case_cancel(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__history(cr, uid, cases, _('Cancel'))
        self.write(cr, uid, ids, {'state':'cancel', 'active':True})
        self._action(cr,uid, cases, 'cancel')
        return True

    def case_pending(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__history(cr, uid, cases, _('Pending'))
        self.write(cr, uid, ids, {'state':'pending', 'active':True})
        self._action(cr,uid, cases, 'pending')
        return True

    def case_reset(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__history(cr, uid, cases, _('Draft'))
        self.write(cr, uid, ids, {'state':'draft', 'active':True})
        self._action(cr, uid, cases, 'draft')
        return True
crm_case()


class crm_case_log(osv.osv):
    _name = "crm.case.log"
    _description = "Case Communication History"
    _order = "id desc"
    _columns = {
        'name': fields.char('Status', size=64),
        'som': fields.many2one('res.partner.som', 'State of Mind'),
        'date': fields.datetime('Date'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel'),
        'section_id': fields.many2one('crm.case.section', 'Section'),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'model_id': fields.many2one('ir.model', "Model"),
        'res_id': fields.integer('Resource ID'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
crm_case_log()

class crm_case_history(osv.osv):
    _name = "crm.case.history"
    _description = "Case history"
    _order = "id desc"
    _inherits = {'crm.case.log':"log_id"}    

    def _note_get(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for hist in self.browse(cursor, user, ids, context or {}):
            res[hist.id] = (hist.email or '/') + ' (' + str(hist.date) + ')\n'
            res[hist.id] += (hist.description or '')
        return res
    _columns = {
        'description': fields.text('Description'),
        'note': fields.function(_note_get, method=True, string="Description", type="text"),
        'email': fields.char('Email', size=84),
        'log_id': fields.many2one('crm.case.log','Log',ondelete='cascade'),
    }
crm_case_history()

class crm_email_add_cc_wizard(osv.osv_memory):
    _name = "crm.email.add.cc"
    _description = "Email Add CC"
    _columns = {
        'name': fields.selection([('user','User'),('partner','Partner'),('email','Email Address')], 'Send to', required=True),
        'user_id': fields.many2one('res.users',"User"),
        'partner_id': fields.many2one('res.partner',"Partner"),
        'email': fields.char('Email', size=32),
        'subject': fields.char('Subject', size=32),
    }

    def change_email(self, cr, uid, ids, user, partner):
        if (not partner and not user):
            return {'value':{'email': False}}
        email = False
        if partner:
            addr = self.pool.get('res.partner').address_get(cr, uid, [partner], ['contact'])
            if addr:
                email = self.pool.get('res.partner.address').read(cr, uid,addr['contact'] , ['email'])['email']
        elif user:
            addr = self.pool.get('res.users').read(cr, uid, user, ['address_id'])['address_id']
            if addr:
                email = self.pool.get('res.partner.address').read(cr, uid,addr[0] , ['email'])['email']
        return {'value':{'email': email}}


    def add_cc(self, cr, uid, ids, context={}):
        data = self.read(cr, uid, ids[0])
        email = data['email']
        subject = data['subject']

        if not context:
            return {}
        history_line = self.pool.get('crm.case.history').browse(cr, uid, context['active_id'])
        model = history_line.log_id.model_id.model
        model_pool = self.pool.get(model)
        case = model_pool.browse(cr, uid, history_line.log_id.res_id)
        body = history_line.description.replace('\n','\n> ')
        flag = tools.email_send(
            case.user_id.address_id.email,
            [case.email_from],
            subject or '['+str(case.id)+'] '+case.name,
            model_pool.format_body(body),
            email_cc = [email],
            openobject_id=str(case.id),
            subtype="html"
        )
        if flag:
            model_pool.write(cr, uid, case.id, {'email_cc' : case.email_cc and case.email_cc +','+ email or email})
        else:
            raise osv.except_osv(_('Email Fail!'),("Lastest Email is not sent successfully"))
        return {}

crm_email_add_cc_wizard()

def _section_get(self, cr, uid, context={}):
    obj = self.pool.get('crm.case.section')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['id','name'], context)
    res = [(str(r['id']),r['name']) for r in res]
    return res

class users(osv.osv):
    _inherit = 'res.users'
    _description = "Users"
    _columns = {
        'context_section_id': fields.many2one('crm.case.section', 'Sales Section'),
    }
users()



