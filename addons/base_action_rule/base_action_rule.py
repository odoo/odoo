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

class base_action_rule(osv.osv):
    """ Base Action Rules """

    _name = 'base.action.rule'
    _description = 'Action Rules'
    
    def _state_get(self, cr, uid, context={}):
        """ Get State
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """

        return self.state_get(cr, uid, context=context)

   
    def state_get(self, cr, uid, context={}):
        """ Get State
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """

        return [('','')]
  
    _columns = {
        'name': fields.many2one('ir.model', 'Model', required=True),
        'max_level': fields.integer('Max Level', help='Specifies maximum level.'),
        'create_date': fields.datetime('Create Date', readonly=1),
        'active': fields.boolean('Active', help="If the active field is set to true,\
                     it will allow you to hide the rule without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when\
                     displaying a list of rules."),
        'trg_date_type':  fields.selection([
            ('none','None'),
            ('create','Creation Date'),
            ('action_last','Last Action Date'),
            ('date','Date'),
            ('deadline', 'Deadline'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date',help="Delay After Trigger Date,\
                             specifies you can put a negative number " \
                             "if you need a delay before the trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'),('hour','Hours'),\
                                ('day','Days'),('month','Months')], 'Delay type'),


        'trg_user_id':  fields.many2one('res.users', 'Responsible'),

        'trg_partner_id': fields.many2one('res.partner', 'Partner'),
        'trg_partner_categ_id': fields.many2one('res.partner.category', 'Partner Category'),
        'trg_state_from': fields.selection(_state_get, 'State', size=16),
        'trg_state_to': fields.selection(_state_get, 'Button Pressed', size=16),

        'act_method': fields.char('Call Object Method', size=64),
        'act_user_id': fields.many2one('res.users', 'Set responsible to'),
        'act_state': fields.selection(_state_get, 'Set state to', size=16),
        'act_email_cc': fields.char('Add watchers (Cc)', size=250, help="These people\
                         will receive a copy of the future communication between partner and users by email"),

        'act_remind_partner': fields.boolean('Remind Partner', help="Check this if\
                         you want the rule to send a reminder by email to the partner."),
        'act_remind_user': fields.boolean('Remind responsible', help="Check this if \
                        you want the rule to send a reminder by email to the user."),
        'act_reply_to': fields.char('Reply-To', size=64),
        'act_remind_attach': fields.boolean('Remind with attachment', help="Check this if\
                         you want that all documents attached to the object be attached \
                        to the reminder email sent."),

        'act_mail_to_user': fields.boolean('Mail to responsible',help="Check this if \
                            you want the rule to send an email to the responsible person."),
        'act_mail_to_watchers': fields.boolean('Mail to watchers (CC)',help="Check this\
                                 if you want the rule to mark CC(mail to any other person\
                                  defined in actions)."),
        'act_mail_to_email': fields.char('Mail to these emails', size=128,help="Email-id \
                                of the persons whom mail is to be sent"),
        'act_mail_body': fields.text('Mail body',help="Content of mail"),
        'regex_name': fields.char('Regular Expression on Model Name', size=128),
        'server_action_id': fields.many2one('ir.actions.server','Server Action',help="Describes the\
                                 action name." \
                                "eg:on which object which action to be taken on basis of which condition"),
        'domain':fields.char('Domain', size=124, required=False, readonly=False),
    }

    _defaults = {
        'active': lambda *a: True,
        'max_level': lambda *a: 15,
        'trg_date_type': lambda *a: 'none',
        'trg_date_range_type': lambda *a: 'day',
        'act_mail_to_user': lambda *a: 0,
        'act_remind_partner': lambda *a: 0,
        'act_remind_user': lambda *a: 0,
        'act_mail_to_watchers': lambda *a: 0,
        'domain': lambda *a: '[]'
    }
    
    _order = 'sequence'
    
    def format_body(self, body):
        """ Foramat Action rule's body
            @param self: The object pointer """

        return body and tools.ustr(body) or ''

    def format_mail(self, obj, body):
        """ Foramat Mail
            @param self: The object pointer """
        data = {
            'object_id': obj.id,
            'object_subject': hasattr(obj, 'name') and obj.name or False,
            'object_date': hasattr(obj, 'date') and obj.date or False,
            'object_description': hasattr(obj, 'description') and obj.description or False,
            'object_user': hasattr(obj, 'user_id') and (obj.user_id and obj.user_id.name) or '/',
            'object_user_email': hasattr(obj, 'user_id') and (obj.user_id and \
                                    obj.user_id.address_id and obj.user_id.address_id.email) or '/',
            'object_user_phone': hasattr(obj, 'user_id') and (obj.user_id and\
                                     obj.user_id.address_id and obj.user_id.address_id.phone) or '/',
            'partner': hasattr(obj, 'partner_id') and (obj.partner_id and obj.partner_id.name) or '/',
            'partner_email': hasattr(obj, 'partner_address_id') and (obj.partner_address_id and\
                                         obj.partner_address_id.email) or '/',
        }
        return self.format_body(body % data)

    def email_send(self, cr, uid, obj, emails, body, emailfrom=tools.config.get('email_from',False), context={}):
        """ send email
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param email: pass the emails
            @param emailfrom: Pass name the email From else False
            @param context: A standard dictionary for contextual values """

        body = self.format_mail(obj, body)
        if not emailfrom:
            if hasattr(obj, 'user_id')  and obj.user_id and obj.user_id.address_id and\
                        obj.user_id.address_id.email:
                emailfrom = obj.user_id.address_id.email

        name = '[%d] %s' % (obj.id, tools.ustr(obj.name))
        emailfrom = tools.ustr(emailfrom)
        reply_to = emailfrom
        if not emailfrom:
            raise osv.except_osv(_('Error!'),
                    _("No E-Mail ID Found for your Company address!"))
        return tools.email_send(emailfrom, emails, name, body, reply_to=reply_to, openobject_id=str(obj.id))


    def do_check(self, cr, uid, action, obj, context={}):
        """ check Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """

        ok = True
        if eval(action.domain):
            obj_ids = obj._table.search(cr, uid, eval(action.domain), context=context)
            if not obj.id in obj_ids:
                ok = False
        if hasattr(obj, 'user_id'):
            ok = ok and (not action.trg_user_id.id or action.trg_user_id.id==obj.user_id.id)
        if hasattr(obj, 'partner_id'):
            ok = ok and (not action.trg_partner_id.id or action.trg_partner_id.id==obj.partner_id.id)
            ok = ok and (
                not action.trg_partner_categ_id.id or
                (
                    obj.partner_id.id and
                    (action.trg_partner_categ_id.id in map(lambda x: x.id, obj.partner_id.category_id or []))
                )
            )
        state_to = context.get('state_to', False)
        if hasattr(obj, 'state'):
            ok = ok and (not action.trg_state_from or action.trg_state_from==obj.state)
        if state_to:
            ok = ok and (not action.trg_state_to or action.trg_state_to==state_to)

        reg_name = action.regex_name
        result_name = True
        if reg_name:
            ptrn = re.compile(str(reg_name))
            _result = ptrn.search(str(obj.name))
            if not _result:
                result_name = False
        regex_n = not reg_name or result_name
        ok = ok and regex_n
        return ok

    def do_action(self, cr, uid, action, model_obj, obj, context={}):
        """ Do Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param action: pass action
            @param model_obj: pass Model object
            @param context: A standard dictionary for contextual values """

        if action.server_action_id:
            context.update({'active_id':obj.id,'active_ids':[obj.id]})
            self.pool.get('ir.actions.server').run(cr, uid, [action.server_action_id.id], context)
        write = {}
        if hasattr(obj, 'user_id') and action.act_user_id:
            obj.user_id = action.act_user_id
            write['user_id'] = action.act_user_id.id
        if hasattr(obj, 'date_action_last'):
            write['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(obj, 'state') and action.act_state:
            obj.state = action.act_state
            write['state'] = action.act_state

        if hasattr(obj, 'categ_id') and action.act_categ_id:
            obj.categ_id = action.act_categ_id
            write['categ_id'] = action.act_categ_id.id

        model_obj.write(cr, uid, [obj.id], write, context)

        if hasattr(model_obj, 'remind_user') and action.act_remind_user:
            model_obj.remind_user(cr, uid, [obj.id], context, attach=action.act_remind_attach)
        if hasattr(model_obj, 'remind_partner') and action.act_remind_partner:
            model_obj.remind_partner(cr, uid, [obj.id], context, attach=action.act_remind_attach)
        if action.act_method:
            getattr(model_obj, 'act_method')(cr, uid, [obj.id], action, context)
        emails = []
        if hasattr(obj, 'user_id') and action.act_mail_to_user:
            if obj.user_id and obj.user_id.address_id:
                emails.append(obj.user_id.address_id.email)

        if action.act_mail_to_watchers:
            emails += (action.act_email_cc or '').split(',')
        if action.act_mail_to_email:
            emails += (action.act_mail_to_email or '').split(',')
        emails = filter(None, emails)
        if len(emails) and action.act_mail_body:
            emails = list(set(emails))
            self.email_send(cr, uid, obj, emails, action.act_mail_body)
        return True

    def _action(self, cr, uid, ids, objects, scrit=None, context={}):
        """ Do Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Basic Action Rule’s IDs,
            @param objects: pass objects
            @param context: A standard dictionary for contextual values """
        if not scrit:
            scrit = []
        cr.execute("select id from base_action_rule order by sequence")
        rule_ids = map(lambda x: x[0], cr.fetchall())
        for action in self.browse(cr, uid, rule_ids):
            level = action.max_level
            if not level:
                break
            model_obj = self.pool.get(action.name.model)
            for obj in objects:
                ok = self.do_check(cr, uid, action, obj, context=context)
                if not ok:
                    continue

                base = False
                if hasattr(obj, 'create_date') and action.trg_date_type=='create':
                    base = mx.DateTime.strptime(obj.create_date[:19], '%Y-%m-%d %H:%M:%S')
                elif hasattr(obj, 'create_date') and action.trg_date_type=='action_last':
                    if hasattr(obj, 'date_action_last') and obj.date_action_last:
                        base = mx.DateTime.strptime(obj.date_action_last, '%Y-%m-%d %H:%M:%S')
                    else:
                        base = mx.DateTime.strptime(obj.create_date[:19], '%Y-%m-%d %H:%M:%S')
                elif hasattr(obj, 'date_deadline') and action.trg_date_type=='deadline' \
                                and obj.date_deadline:
                    base = mx.DateTime.strptime(obj.date_deadline, '%Y-%m-%d %H:%M:%S')
                elif hasattr(obj, 'date') and action.trg_date_type=='date' and obj.date:
                    base = mx.DateTime.strptime(obj.date, '%Y-%m-%d %H:%M:%S')
                if base:
                    fnct = {
                        'minutes': lambda interval: mx.DateTime.RelativeDateTime(minutes=interval),
                        'day': lambda interval: mx.DateTime.RelativeDateTime(days=interval),
                        'hour': lambda interval: mx.DateTime.RelativeDateTime(hours=interval),
                        'month': lambda interval: mx.DateTime.RelativeDateTime(months=interval),
                    }
                    d = base + fnct[action.trg_date_range_type](action.trg_date_range)
                    dt = d.strftime('%Y-%m-%d %H:%M:%S')
                    ok = False
                    if hasattr(obj, 'date_action_last') and hasattr(obj, 'date_action_next'):
                        ok = (dt <= time.strftime('%Y-%m-%d %H:%M:%S')) and \
                                ((not obj.date_action_next) or \
                                (dt >= obj.date_action_next and \
                                obj.date_action_last < obj.date_action_next))
                        if not ok:
                            if not obj.date_action_next or dt < obj.date_action_next:
                                obj.date_action_next = dt
                                model_obj.write(cr, uid, [obj.id], {'date_action_next': dt}, context)
                else:
                    ok = action.trg_date_type=='none'
                if ok:
                    self.do_action(cr, uid, action, model_obj, obj, context)
                    break
            level -= 1
        return True

    def _check_mail(self, cr, uid, ids, context=None):
        """ Check Mail
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Action Rule’s IDs
            @param context: A standard dictionary for contextual values """

        empty = orm.browse_null()
        rule_obj = self.pool.get('base.action.rule')
        for rule in self.browse(cr, uid, ids):
            if rule.act_mail_body:
                try:
                    rule_obj.format_mail(empty, rule.act_mail_body)
                except (ValueError, KeyError, TypeError):
                    return False
        return True

    _constraints = [
        (_check_mail, 'Error: The mail is not well formated', ['act_mail_body']),
    ]

base_action_rule()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
