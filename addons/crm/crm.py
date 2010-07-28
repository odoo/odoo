# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import tools
from osv import fields,osv,orm

import mx.DateTime
import base64
from tools.translate import _

MAX_LEVEL = 15
AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancel'),
    ('done', 'Close'),
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
    _columns = {
        'name': fields.char('Case Section',size=64, required=True, translate=True),
        'code': fields.char('Section Code',size=8),
        'active': fields.boolean('Active'),
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"),
        'sequence': fields.integer('Sequence'),
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
            cr.execute('SELECT DISTINCT parent_id FROM crm_case_section '\
                       'WHERE id IN %s',
                       (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive sections.', ['parent_id'])
    ]

    # Mainly used by the wizard
    def menu_create_data(self, cr, uid, data, menu_lst, context):
        menus = {}
        menus[0] = data['menu_parent_id']
        section = self.browse(cr, uid, data['section_id'], context)
        for (index, mname, mdomain, latest, view_mode) in menu_lst:
            view_mode = data['menu'+str(index)+'_option']
            if view_mode=='no':
                menus[index] = data['menu_parent_id']
                continue
            icon = icon_lst.get(view_mode.split(',')[0], 'STOCK_JUSTIFY_FILL')
            menu_id=self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': data['menu'+str(index)],
                'parent_id': menus[latest],
                'icon': icon
            })
            menus[index] = menu_id
            action_id = self.pool.get('ir.actions.act_window').create(cr,uid, {
                'name': data['menu'+str(index)],
                'res_model': 'crm.case',
                'domain': mdomain.replace('SECTION_ID', str(data['section_id'])),
                'view_type': 'form',
                'view_mode': view_mode,
            })
            seq = 0
            for mode in view_mode.split(','):
                self.pool.get('ir.actions.act_window.view').create(cr, uid, {
                    'sequence': seq,
                    'view_id': data['view_'+mode],
                    'view_mode': mode,
                    'act_window_id': action_id,
                    'multi': True
                })
                seq+=1
            self.pool.get('ir.values').create(cr, uid, {
                'name': data['menu'+str(index)],
                'key2': 'tree_but_open',
                'model': 'ir.ui.menu',
                'res_id': menu_id,
                'value': 'ir.actions.act_window,%d'%action_id,
                'object': True
            })
        return True

    #
    # Used when called from .XML file
    #
    def menu_create(self, cr, uid, ids, name, menu_parent_id=False, context={}):
        menus = {}
        menus[-1] = menu_parent_id
        for section in self.browse(cr, uid, ids, context):
            for (index, mname, mdomain, latest) in [
                (0,'',"[('section_id','=',"+str(section.id)+")]", -1),
                (1,'My ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid)]", 0),
                (2,'My Unclosed ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','<>','cancel'), ('state','<>','done')]", 1),
                (5,'My Open ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','open')]", 2),
                (6,'My Pending ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','pending')]", 2),
                (7,'My Draft ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','draft')]", 2),

                (3,'My Late ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('date_deadline','<=',time.strftime('%Y-%m-%d')), ('state','<>','cancel'), ('state','<>','done')]", 1),
                (4,'My Canceled ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','cancel')]", 1),
                (8,'All ',"[('section_id','=',"+str(section.id)+"),]", 0),
                (9,'Unassigned ',"[('section_id','=',"+str(section.id)+"),('user_id','=',False)]", 8),
                (10,'Late ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('date_deadline','<=',time.strftime('%Y-%m-%d')), ('state','<>','cancel'), ('state','<>','done')]", 8),
                (11,'Canceled ',"[('section_id','=',"+str(section.id)+"),('state','=','cancel')]", 8),
                (12,'Unclosed ',"[('section_id','=',"+str(section.id)+"),('state','<>','cancel'), ('state','<>','done')]", 8),
                (13,'Open ',"[('section_id','=',"+str(section.id)+"),('state','=','open')]", 12),
                (14,'Pending ',"[('section_id','=',"+str(section.id)+"),('state','=','pending')]", 12),
                (15,'Draft ',"[('section_id','=',"+str(section.id)+"),('state','=','draft')]", 12),
                (16,'Unassigned ',"[('section_id','=',"+str(section.id)+"),('user_id','=',False),('state','<>','cancel'),('state','<>','done')]", 12),
            ]:
                view_mode = 'tree,form'
                icon = 'STOCK_JUSTIFY_FILL'
                if index==0:
                    view_mode = 'form,tree'
                    icon = 'STOCK_NEW'
                menu_id=self.pool.get('ir.ui.menu').create(cr, uid, {
                    'name': mname+name,
                    'parent_id': menus[latest],
                    'icon': icon
                })
                menus[index] = menu_id
                action_id = self.pool.get('ir.actions.act_window').create(cr,uid, {
                    'name': mname+name+' Cases',
                    'res_model': 'crm.case',
                    'domain': mdomain,
                    'view_type': 'form',
                    'view_mode': view_mode,
                })
                self.pool.get('ir.values').create(cr, uid, {
                    'name': 'Open Cases',
                    'key2': 'tree_but_open',
                    'model': 'ir.ui.menu',
                    'res_id': menu_id,
                    'value': 'ir.actions.act_window,%d'%action_id,
                    'object': True
                })
        return True

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
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_case_categ()

class crm_case_rule(osv.osv):
    _name = "crm.case.rule"
    _description = "Case Rule"
    _columns = {
        'name': fields.char('Rule Name',size=64, required=True),
        'active': fields.boolean('Active'),
        'sequence': fields.integer('Sequence'),

        'trg_state_from': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Case State', size=16),
        'trg_state_to': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Button Pressed', size=16),

        'trg_date_type':  fields.selection([
            ('none','None'),
            ('create','Creation Date'),
            ('action_last','Last Action Date'),
            ('deadline','Deadline'),
            ('date','Date'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date'),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'),('hour','Hours'),('day','Days'),('month','Months')], 'Delay type'),

        'trg_section_id': fields.many2one('crm.case.section', 'Section'),
        'trg_categ_id':  fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',trg_section_id)]"),
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
        'act_email_cc': fields.char('Add watchers (Cc)', size=250, help="These people will receive a copy of the futur communication between partner and users by email"),

        'act_remind_partner': fields.boolean('Remind Partner', help="Check this if you want the rule to send a reminder by email to the partner."),
        'act_remind_user': fields.boolean('Remind responsible', help="Check this if you want the rule to send a reminder by email to the user."),
        'act_remind_attach': fields.boolean('Remind with attachment', help="Check this if you want that all documents attached to the case be attached to the reminder email sent."),

        'act_mail_to_user': fields.boolean('Mail to responsible'),
        'act_mail_to_partner': fields.boolean('Mail to partner'),
        'act_mail_to_watchers': fields.boolean('Mail to watchers (Cc)'),
        'act_mail_to_email': fields.char('Mail to these emails', size=128),
        'act_mail_body': fields.text('Mail body')
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
        default.update( {'state':'draft', 'id':False, 'history_line':[],'log_ids':[]})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Description',size=64,required=True),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'active': fields.boolean('Active'),
        'description': fields.text('Your action'),
        'section_id': fields.many2one('crm.case.section', 'Section', required=True, select=True),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id)]"),
        'planned_revenue': fields.float('Planned Revenue'),
        'planned_cost': fields.float('Planned Costs'),
        'probability': fields.float('Probability (%)'),
        'email_from': fields.char('Partner Email', size=128),
        'email_cc': fields.char('Watchers Emails', size=252),
        'email_last': fields.function(_email_last, method=True,
            string='Latest E-Mail', type='text'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"),
        'som': fields.many2one('res.partner.som', 'State of Mind'),
        'date': fields.datetime('Date'),
        'create_date': fields.datetime('Created' ,readonly=True),
        'date_deadline': fields.datetime('Deadline'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'canal_id': fields.many2one('res.partner.canal', 'Channel'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'history_line': fields.one2many('crm.case.history', 'case_id', 'Communication', readonly=1),
        'log_ids': fields.one2many('crm.case.log', 'case_id', 'Logs History', readonly=1),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'ref' : fields.reference('Reference', selection=_links_get, size=128),
        'ref2' : fields.reference('Reference 2', selection=_links_get, size=128),

        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
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
    _defaults = {
        'active': lambda *a: 1,
        'user_id': _get_default_user,
        'partner_id': _get_default_partner,
        'partner_address_id': _get_default_partner_address,
        'email_from': _get_default_email,
        'state': lambda *a: 'draft',
        'priority': lambda *a: AVAILABLE_PRIORITIES[2][0],
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    _order = 'priority, date_deadline desc, date desc,id desc'

    def unlink(self, cr, uid, ids, context={}):
        for case in self.browse(cr, uid, ids, context):
            if (not case.section_id.allow_unlink) and (case.state <> 'draft'):
                raise osv.except_osv(_('Warning !'),
                    _('You can not delete this case. You should better cancel it.'))
        return super(crm_case, self).unlink(cr, uid, ids, context)

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
        return (body or u'').encode('utf8', 'replace')

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

    def email_send(self, cr, uid, case, emails, body, context={}):
        body = self.format_mail(case, body)
        if case.user_id and case.user_id.address_id and case.user_id.address_id.email:
            emailfrom = case.user_id.address_id.email
        else:
            emailfrom = case.section_id.reply_to
        name = '[%d] %s' % (case.id, case.name.encode('utf8'))
        reply_to = case.section_id.reply_to or False
        if reply_to: reply_to = reply_to.encode('utf8')
        if not emailfrom:
            raise osv.except_osv(_('Error!'),
                    _("No E-Mail ID Found for your Company address or missing reply address in section!"))
        tools.email_send(emailfrom, emails, name, body, reply_to=reply_to, tinycrm=str(case.id))
        return True
    def __log(self, cr, uid, cases, keyword, context={}):
        if not self.pool.get('res.partner.event.type').check(cr, uid, 'crm_case_'+keyword):
            return False
        for case in cases:
            if case.partner_id:
                translated_keyword = keyword
                if 'translated_keyword' in context:
                    translated_keyword = context['translated_keyword']
                name = _('Case') +  ' ' + translated_keyword + ': ' + case.name
                if isinstance(name, str):
                    name = unicode(name, 'utf-8')
                if len(name) > 64:
                    name = name[:61] + '...'
                self.pool.get('res.partner.event').create(cr, uid, {
                    'name': name,
                    'som':(case.som or False) and case.som.id,
                    'description':case.description,
                    'partner_id':case.partner_id.id,
                    'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                    'canal_id':(case.canal_id or False) and case.canal_id.id,
                    'user_id':uid,
                    'document': 'crm.case,%i' % case.id,
                })
        return True

    def __history(self, cr, uid, cases, keyword, history=False, email=False, context={}):
        for case in cases:
            data = {
                'name': keyword,
                'som': case.som.id,
                'canal_id': case.canal_id.id,
                'user_id': uid,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'case_id': case.id,
                'section_id': case.section_id.id
            }
            obj = self.pool.get('crm.case.log')
            if history and case.description:
                obj = self.pool.get('crm.case.history')
                data['description'] = case.description
                data['email'] = email or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or False
            obj.create(cr, uid, data, context)
        return True
    _history = __history

    def create(self, cr, uid, *args, **argv):
        res = super(crm_case, self).create(cr, uid, *args, **argv)
        cases = self.browse(cr, uid, [res])
        cases[0].state # to fill the browse record cache
        self.__log(cr,uid, cases, 'draft', context={'translated_keyword': _('draft')})
        self._action(cr,uid, cases, 'draft')
        return res

    def remind_partner(self, cr, uid, ids, context={}, attach=False):
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context={}, attach=False,
            destination=True):
        for case in self.browse(cr, uid, ids):
            if case.section_id.reply_to and case.email_from:
                src = case.email_from
                
                if not src:
                    raise osv.except_osv(_('Error!'),
                        _("No E-Mail ID Found for the Responsible Partner or missing reply address in section!"))
                    
                dest = case.section_id.reply_to
                body = case.email_last or case.description
                if not destination:
                    src,dest = dest,src
                    if case.user_id.signature:
                        if body:
                            body += '\n\n%s' % (case.user_id.signature)
                        else:
                            body = '\n\n%s' % (case.user_id.signature)
                dest = [dest]

                attach_to_send = None

                if attach:
                    attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', 'crm.case'), ('res_id', '=', case.id)])
                    attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname','datas'])
                    attach_to_send = map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send)
                
                # Send an email
                tools.email_send(
                    src,
                    dest,
                    "Reminder: [%s] %s" % (str(case.id), case.name, ),
                    self.format_body(body),
                    reply_to=case.section_id.reply_to,
                    tinycrm=str(case.id),
                    attach=attach_to_send
                )

        return True

    def add_reply(self, cursor, user, ids, context=None):
        for case in self.browse(cursor, user, ids, context=context):
            if case.history_line:
                description = case.history_line[0].description
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
                tinycrm=str(case.id)
            )
        return True

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        if not part:
            return {'value':{'partner_address_id': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
        data = {'partner_address_id':addr['contact']}
        if addr['contact'] and not email:
            data['email_from'] = self.pool.get('res.partner.address').browse(cr, uid, addr['contact']).email
        return {'value':data}

    def onchange_categ_id(self, cr, uid, ids, categ, context={}):
        if not categ:
            return {'value':{}}
        cat = self.pool.get('crm.case.categ').browse(cr, uid, categ, context).probability
        return {'value':{'probability':cat}}


    def onchange_partner_address_id(self, cr, uid, ids, part, email=False):
        if not part:
            return {'value':{}}
        data = {}
        if not email:
            data['email_from'] = self.pool.get('res.partner.address').browse(cr, uid, part).email
        return {'value':data}

    def case_close(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__log(cr,uid, cases, 'done', context={'translated_keyword': _('done')})
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
        self.__log(cr, uid, cases, 'open', context={'translated_keyword': _('open')})
        self.__history(cr, uid, cases, _('Open'))
        for case in cases:
            data = {'state':'open', 'active':True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, ids, data)
        self._action(cr,uid, cases, 'open')
        return True

    def emails_get(self, cr, uid, id, context={}):
        case = self.browse(cr, uid, id)
        return ((case.user_id and case.user_id.address_id and case.user_id.address_id.email) or False, case.email_from, case.email_cc, case.priority)

    def case_cancel(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__log(cr, uid, cases, 'cancel', context={'translated_keyword': _('cancel')})
        self.__history(cr, uid, cases, _('Cancel'))
        self.write(cr, uid, ids, {'state':'cancel', 'active':True})
        self._action(cr,uid, cases, 'cancel')
        return True

    def case_pending(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__log(cr, uid, cases, 'pending', context={'translated_keyword': _('draft')})
        self.__history(cr, uid, cases, _('Pending'))
        self.write(cr, uid, ids, {'state':'pending', 'active':True})
        self._action(cr,uid, cases, 'pending')
        return True

    def case_reset(self, cr, uid, ids, *args):
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self.__log(cr, uid, cases, 'draft', context={'translated_keyword': _('draft')})
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
        'name': fields.char('Action', size=64),
        'som': fields.many2one('res.partner.som', 'State of Mind'),
        'date': fields.datetime('Date'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel'),
        'section_id': fields.many2one('crm.case.section', 'Section'),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'case_id': fields.many2one('crm.case', 'Case', required=True, ondelete='cascade')
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

    def create(self, cr, user, vals, context=None):
        if vals.has_key('case_id') and vals['case_id']:
            case_obj = self.pool.get('crm.case')
            cases = case_obj.browse(cr, user, [vals['case_id']])
            case_obj._action(cr, user, cases, '')
        return super(crm_case_history, self).create(cr, user, vals, context)

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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

