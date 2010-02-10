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
import mx.DateTime
import re

import tools
from osv import fields, osv, orm
from osv.orm import except_orm
from tools.translate import _

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

class base_action_rule(osv.osv):
    _name = 'base.action.rule'
    _description = 'Action Rules'
    
    def _get_max_level(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for check in self.browse(cr, uid, ids):
            if check.rule_lines and len(check.rule_lines) < 15:
                res[check.id] = len(check.rule_lines)
            elif len(check.rule_lines) > 15:
                raise osv.except_osv(_('Error !'), _('Max Level exceeded.'))
            else:
                res[check.id] = 0
        return res
    
    _columns = {
        'name': fields.many2one('ir.model', 'Model', required=True, states={'activate': [('readonly', True)]}),
        'max_level': fields.function(_get_max_level, method=True, string='Max Level', 
                    type='integer', store=True, help='Specifies maximum rule lines can be entered.'),
        'rule_lines': fields.one2many('base.action.rule.line','rule_id','Rule Lines', states={'activate': [('readonly', True)]}),
        'create_date': fields.datetime('Create Date', readonly=1),
        'state': fields.selection([('activate','Activated'),('deactivate','Deactivated')],'State',readonly=1)
    }
    
    _defaults = {
        'state': lambda *a: 'deactivate',
    }
    
    def button_activate_rule(self, cr, uid, ids, context=None):
        check = all(rule.rule_lines for rule in self.browse(cr, uid, ids))
        if not check:
            raise osv.except_osv(_('Error !'), _('Rule Lines are empty ! Cannot activate the Rule(s).'))
        cronobj = self.pool.get('ir.cron')
        cronids = cronobj.search(cr,uid,[('model','=','base.action.rule'),('active','=',False)])
        if cronids:
            cronobj.write(cr, uid, cronids, {'active': True})
        self.write(cr, uid, ids, {'state': 'activate'})
        return True
    
    def button_deactivate_rule(self, cr, uid, ids, context=None):
        checkids = self.pool.get('base.action.rule').search(cr, uid, [])
        cronobj = self.pool.get('ir.cron')
        cronids = cronobj.search(cr,uid,[('model','=','base.action.rule'),('active','=',True)])
        self.write(cr, uid, ids, {'state': 'deactivate'})
        if cronids and all(rule.state == 'deactivate' for rule in self.browse(cr, uid, checkids)):
            cronobj.write(cr, uid, cronids, {'active': False})
        return True
    
    def remind_partner(self, cr, uid, ids, context={}, attach=False):
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context={}, attach=False, destination=True):
        ruleline_obj = self.pool.get('base.action.rule.line')
        for rule in self.browse(cr, uid, ids):
            for action in rule.rule_lines:
                if not action.act_remind_user:
                    raise osv.except_osv(_('Warning!'), ("Remind Responsible should be active."))
                if action.trg_user_id and action.trg_user_id.address_id and not action.trg_user_id.address_id.email:
                    raise osv.except_osv(_('Error!'), ("User Email is not specified."))
                if action.trg_user_id and action.trg_user_id.address_id and action.trg_user_id.address_id.email:
                    src = action.trg_user_id.address_id.email
                    dest = action.act_reply_to
                    body = action.act_mail_body
                    if not destination:
                        src, dest = dest, src
                        if action.trg_user_id.signature:
                            body += '\n\n%s' % (action.trg_user_id.signature or '')
                    dest = [dest]
    
                    attach_to_send = None
    
                    if attach:
                        attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', rule.name.model), ('res_id', '=', rule.name.id)])
                        attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname','datas'])
                        attach_to_send = map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send)
    
                    # Send an email
                    flag = tools.email_send(
                        src,
                        dest,
                        "Reminder: [%s] %s" % (str(rule.name.id), rule.name.model, ),
                        ruleline_obj.format_body(body),
                        reply_to=action.act_reply_to,
                        openobject_id=str(rule.name.id),
                        attach=attach_to_send
                    )
                    if flag:
                        raise except_orm(_('Email!'),
                                _("Email Successfully Sent by %s") % action.trg_user_id.name)
                    else:
                        raise except_orm(_('Email!'),
                                _("Email is not sent Successfully for %s") % action.trg_user_id.name)
        return True
    
    def _check(self, cr, uid, ids=False, context={}):
        '''
        Function called by the scheduler to process models
        '''
        ruleobj = self.pool.get('base.action.rule')
        ids = ruleobj.search(cr, uid, [('state','=','activate')])
        rules = ruleobj.browse(cr, uid, ids, context) 
        return ruleobj._action(cr, uid, rules, False, context=context)
    
    def _action(self, cr, uid, rules, state_to, scrit=None, context={}):
        if not scrit:
            scrit = []
        history = []
        history_obj = self.pool.get('base.action.rule.history')
        cr.execute("select nextcall from ir_cron where model='base.action.rule'")
        action_next = cr.fetchone()[0]
        if rules:
            cr.execute('select id, rule_id, res_id, date_action_last, date_action_next' \
                       ' from base_action_rule_history where rule_id in (%s)' %(','.join(map(lambda x: "'"+str(x.id)+"'",rules))))
            history = cr.fetchall()
            checkids = map(lambda x: x[1], history or [])
            if not len(history) or len(history) < len(rules):
                for rule in rules:
                    if rule.id not in checkids:
                        lastDate = mx.DateTime.strptime(rule.create_date[:19], '%Y-%m-%d %H:%M:%S')
                        history_obj.create(cr, uid, {'rule_id': rule.id, 'res_id': rule.name.id, 'date_action_last': lastDate, 'date_action_next': action_next})
        for rule in rules:
            obj = self.pool.get(rule.name.model)
            rec_ids = obj.search(cr, uid, [])
            for action in rule.rule_lines:
                for data in obj.browse(cr, uid, rec_ids):
                    ok = True
                    ok = ok and (not action.trg_state_from or action.trg_state_from==data.state)
                    ok = ok and (not action.trg_state_to or action.trg_state_to==state_to)
                    ok = ok and (not action.trg_user_id.id or action.trg_user_id.id==data.user_id.id)
                    ok = ok and (not action.trg_partner_id.id or action.trg_partner_id.id==data.partner_id.id)
                    ok = ok and (
                        not action.trg_partner_categ_id.id or
                        (
                            data.partner_id.id and
                            (action.trg_partner_categ_id.id in map(lambda x: x.id, data.partner_id.category_id or []))
                        )
                    )
                    ok = ok and (not action.trg_priority_from or action.trg_priority_from>=data.priority)
                    ok = ok and (not action.trg_priority_to or action.trg_priority_to<=data.priority)

                    reg_name = action.regex_name
                    result_name = True
                    if reg_name:
                        ptrn = re.compile(str(reg_name))
                        _result = ptrn.search(str(data.name))
                        if not _result:
                            result_name = False
                    regex_n = not reg_name or result_name
                    ok = ok and regex_n
                    
                    if not ok:
                        continue
                    
                    base = False
                    if action.trg_date_type=='create':
                        base = mx.DateTime.strptime(data.create_date[:19], '%Y-%m-%d %H:%M:%S')
                    elif action.trg_date_type=='action_last':
                        for hist in history:
                            if hist[3]:
                                base = hist[4]
                            else:
                                base = mx.DateTime.strptime(data.create_date[:19], '%Y-%m-%d %H:%M:%S')
                    elif action.trg_date_type=='date' and data.date:
                        base = mx.DateTime.strptime(data.date, '%Y-%m-%d %H:%M:%S')
                    if base:
                        fnct = {
                            'minutes': lambda interval: mx.DateTime.RelativeDateTime(minutes=interval),
                            'day': lambda interval: mx.DateTime.RelativeDateTime(days=interval),
                            'hour': lambda interval: mx.DateTime.RelativeDateTime(hours=interval),
                            'month': lambda interval: mx.DateTime.RelativeDateTime(months=interval),
                        }
                        d = base + fnct[action.trg_date_range_type](action.trg_date_range)
                        dt = d.strftime('%Y-%m-%d %H:%M:%S')
                        for hist in history:
                            ok = (dt <= time.strftime('%Y-%m-%d %H:%M:%S')) and \
                                    ((not hist[4]) or \
                                    (dt >= hist[4] and \
                                    hist[3] < hist[4]))
                            if not ok:
                                if not hist[4] or dt < hist[4]:
                                    history_obj.write(cr, uid, [hist[0]], {'date_action_next': dt}, context)

                    else:
                        ok = action.trg_date_type=='none'

                    if ok:
                        if action.server_action_id:
                            context.update({'active_id': data.id,'active_ids': [data.id]})
                            self.pool.get('ir.actions.server').run(cr, uid, [action.server_action_id.id], context)
                        write = {}
                        if action.act_state:
                            data.state = action.act_state
                            write['state'] = action.act_state
                        if action.act_user_id:
                            data.user_id = action.act_user_id
                            write['user_id'] = action.act_user_id.id
                        if action.act_priority:
                            data.priority = action.act_priority
                            write['priority'] = action.act_priority
                        if action.act_email_cc:
                            if '@' in (data.email_cc or ''):
                                emails = data.email_cc.split(",")
                                if  action.act_email_cc not in emails:# and '<'+str(action.act_email_cc)+">" not in emails:
                                    write['email_cc'] = data.email_cc+','+action.act_email_cc
                            else:
                                write['email_cc'] = action.act_email_cc
                        obj.write(cr, uid, [data.id], write, context)
                        if action.act_remind_user:
                            self.remind_user(cr, uid, [rule.id], context, attach=action.act_remind_attach)
                        if action.act_remind_partner:
                            self.remind_partner(cr, uid, [rule.id], context, attach=action.act_remind_attach)
                        emails = []
                        if action.act_mail_to_user:
                            if data.user_id and data.user_id.address_id:
                                emails.append(data.user_id.address_id.email)
                        if action.act_mail_to_partner:
                            emails.append(data.email_from)
                        if action.act_mail_to_watchers:
                            emails += (action.act_email_cc or '').split(',')
                        if action.act_mail_to_email:
                            emails += (action.act_mail_to_email or '').split(',')
                        emails = filter(None, emails)
                        if len(emails) and action.act_mail_body:
                            emails = list(set(emails))
                            obj.email_send(cr, uid, data, emails, action.act_mail_body)
                for hist in history:
                    if hist[3]:
                        base = hist[4]
                    history_obj.write(cr, uid, [hist[0]], {'date_action_last': base, 'date_action_next': action_next})
        return True

base_action_rule()

class base_action_rule_line(osv.osv):
    _name = 'base.action.rule.line'
    _description = 'Action Rule Lines'
    _columns = {
        'name': fields.char('Rule Name',size=64, required=True),
        'rule_id': fields.many2one('base.action.rule','Rule'),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the case rule without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of case rules."),

        'trg_state_from': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'State', size=16),
        'trg_state_to': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Button Pressed', size=16),

        'trg_date_type':  fields.selection([
            ('none','None'),
            ('create','Creation Date'),
            ('action_last','Last Action Date'),
            ('date','Date'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date',help="Delay After Trigger Date, specifies you can put a negative number " \
                                                             "if you need a delay before the trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'),('hour','Hours'),('day','Days'),('month','Months')], 'Delay type'),

        
        'trg_user_id':  fields.many2one('res.users', 'Responsible'),

        'trg_partner_id': fields.many2one('res.partner', 'Partner'),
        'trg_partner_categ_id': fields.many2one('res.partner.category', 'Partner Category'),

        'trg_priority_from': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Minimum Priority'),
        'trg_priority_to': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Maximum Priority'),
        'act_method': fields.char('Call Object Method', size=64),
        'act_state': fields.selection([('','')]+AVAILABLE_STATES, 'Set state to', size=16),
        'act_user_id': fields.many2one('res.users', 'Set responsible to'),
        'act_priority': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Set priority to'),
        'act_email_cc': fields.char('Add watchers (Cc)', size=250, help="These people will receive a copy of the future communication between partner and users by email"),

        'act_remind_partner': fields.boolean('Remind Partner', help="Check this if you want the rule to send a reminder by email to the partner."),
        'act_remind_user': fields.boolean('Remind responsible', help="Check this if you want the rule to send a reminder by email to the user."),
        'act_reply_to': fields.char('Reply-To', size=64),
        'act_remind_attach': fields.boolean('Remind with attachment', help="Check this if you want that all documents attached to the case be attached to the reminder email sent."),

        'act_mail_to_user': fields.boolean('Mail to responsible',help="Check this if you want the rule to send an email to the responsible person."),
        'act_mail_to_partner': fields.boolean('Mail to partner',help="Check this if you want the rule to send an email to the partner."),
        'act_mail_to_watchers': fields.boolean('Mail to watchers (CC)',help="Check this if you want the rule to mark CC(mail to any other person defined in actions)."),
        'act_mail_to_email': fields.char('Mail to these emails', size=128,help="Email-id of the persons whom mail is to be sent"),
        'act_mail_body': fields.text('Mail body',help="Content of mail"),
        'regex_name': fields.char('Regular Expression on Model Name', size=128),
        'server_action_id': fields.many2one('ir.actions.server','Server Action',help="Describes the action name." \
                                                    "eg:on which object which action to be taken on basis of which condition"),
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
    
    def _check_mail(self, cr, uid, ids, context=None):
        emptycase = orm.browse_null()
        for rule in self.browse(cr, uid, ids):
            if rule.act_mail_body:
                try:
                    self.format_mail(emptycase, rule.act_mail_body)
                except (ValueError, KeyError, TypeError):
                    return False
        return True
    
    _constraints = [
        (_check_mail, 'Error: The mail is not well formated', ['act_mail_body']),
    ]
    
base_action_rule_line()

class base_action_rule_history(osv.osv):
    _name = 'base.action.rule.history'
    _description = 'Action Rule History'
    _columns = {
        'rule_id': fields.many2one('base.action.rule','Rule', required=True, readonly=1),
        'name': fields.related('rule_id', 'name', type='many2one', relation='ir.model', string='Model', readonly=1),
        'res_id': fields.integer('Resource ID', readonly=1),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),  
    }
    
base_action_rule_history()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
