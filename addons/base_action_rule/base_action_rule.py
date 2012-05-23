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

from osv import fields, osv, orm
from tools.translate import _
from datetime import datetime
from datetime import timedelta
from tools.safe_eval import safe_eval
from tools import ustr
import pooler
import re
import time
import tools


def get_datetime(date_field):
    '''Return a datetime from a date string or a datetime string'''
    #complete date time if date_field contains only a date
    date_split = date_field.split(' ')
    if len(date_split) == 1:
        date_field = date_split[0] + " 00:00:00"
   
    return datetime.strptime(date_field[:19], '%Y-%m-%d %H:%M:%S')


class base_action_rule(osv.osv):
    """ Base Action Rules """

    _name = 'base.action.rule'
    _description = 'Action Rules'

    def _state_get(self, cr, uid, context=None):
        """ Get State
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """
        return self.state_get(cr, uid, context=context)

    def state_get(self, cr, uid, context=None):
        """ Get State
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """
        return [('', '')]

    def priority_get(self, cr, uid, context=None):
        """ Get Priority
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """
        return [('', '')]

    _columns = {
        'name':  fields.char('Rule Name', size=64, required=True),
        'model_id': fields.many2one('ir.model', 'Object', required=True),
        'create_date': fields.datetime('Create Date', readonly=1),
        'active': fields.boolean('Active', help="If the active field is set to False,\
 it will allow you to hide the rule without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order \
when displaying a list of rules."),
        'trg_date_type':  fields.selection([
            ('none', 'None'),
            ('create', 'Creation Date'),
            ('action_last', 'Last Action Date'),
            ('date', 'Date'),
            ('deadline', 'Deadline'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date', \
                                         help="Delay After Trigger Date,\
specifies you can put a negative number. If you need a delay before the \
trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'), ('hour', 'Hours'), \
                                ('day', 'Days'), ('month', 'Months')], 'Delay type'),
        'trg_user_id':  fields.many2one('res.users', 'Responsible'),
        'trg_partner_id': fields.many2one('res.partner', 'Partner'),
        'trg_partner_categ_id': fields.many2one('res.partner.category', 'Partner Category'),
        'trg_state_from': fields.selection(_state_get, 'Status', size=16),
        'trg_state_to': fields.selection(_state_get, 'Button Pressed', size=16),

        'act_method': fields.char('Call Object Method', size=64),
        'act_user_id': fields.many2one('res.users', 'Set Responsible to'),
        'act_state': fields.selection(_state_get, 'Set State to', size=16),
        'act_email_cc': fields.char('Add Watchers (Cc)', size=250, help="\
These people will receive a copy of the future communication between partner \
and users by email"),
        'act_remind_partner': fields.boolean('Remind Partner', help="Check \
this if you want the rule to send a reminder by email to the partner."),
        'act_remind_user': fields.boolean('Remind Responsible', help="Check \
this if you want the rule to send a reminder by email to the user."),
        'act_reply_to': fields.char('Reply-To', size=64),
        'act_remind_attach': fields.boolean('Remind with Attachment', help="Check this if you want that all documents attached to the object be attached to the reminder email sent."),
        'act_mail_to_user': fields.boolean('Mail to Responsible', help="Check\
 this if you want the rule to send an email to the responsible person."),
        'act_mail_to_watchers': fields.boolean('Mail to Watchers (CC)',
                                                help="Check this if you want \
the rule to mark CC(mail to any other person defined in actions)."),
        'act_mail_to_email': fields.char('Mail to these Emails', size=128, \
        help="Email-id of the persons whom mail is to be sent"),
        'act_mail_body': fields.text('Mail body', help="Content of mail"),
        'regex_name': fields.char('Regex on Resource Name', size=128, help="Regular expression for matching name of the resource\
\ne.g.: 'urgent.*' will search for records having name starting with the string 'urgent'\
\nNote: This is case sensitive search."),
        'server_action_id': fields.many2one('ir.actions.server', 'Server Action', help="Describes the action name.\neg:on which object which action to be taken on basis of which condition"),
        'filter_id':fields.many2one('ir.filters', 'Filter', required=False),
        'act_email_from' : fields.char('Email From', size=64, required=False,
                help="Use a python expression to specify the right field on which one than we will use for the 'From' field of the header"),
        'act_email_to' : fields.char('Email To', size=64, required=False,
                                     help="Use a python expression to specify the right field on which one than we will use for the 'To' field of the header"),
        'last_run': fields.datetime('Last Run', readonly=1),
    }

    _defaults = {
        'active': lambda *a: True,
        'trg_date_type': lambda *a: 'none',
        'trg_date_range_type': lambda *a: 'day',
        'act_mail_to_user': lambda *a: 0,
        'act_remind_partner': lambda *a: 0,
        'act_remind_user': lambda *a: 0,
        'act_mail_to_watchers': lambda *a: 0,
    }

    _order = 'sequence'

    def onchange_model_id(self, cr, uid, ids, name):
        #This is not a good solution as it will affect the domain only on onchange
        res = {'domain':{'filter_id':[]}}
        if name:
            model_name = self.pool.get('ir.model').read(cr, uid, [name], ['model'])
            if model_name:
                mod_name = model_name[0]['model']
                res['domain'] = {'filter_id': [('model_id','=',mod_name)]}
        else:
            res['value'] = {'filter_id':False}
        return res

    def post_action(self, cr, uid, ids, model, context=None):
        # Searching for action rules
        cr.execute("SELECT model.model, rule.id  FROM base_action_rule rule \
                        LEFT JOIN ir_model model on (model.id = rule.model_id) \
                        WHERE active")
        res = cr.fetchall()
        # Check if any rule matching with current object
        for obj_name, rule_id in res:
            if not (model == obj_name):
                continue # TODO add this condition in the WHERE clause above.
            else:
                obj = self.pool.get(obj_name)
                # If the rule doesn't involve a time condition, run it immediately
                # Otherwise we let the scheduler run the action
                if self.browse(cr, uid, rule_id, context=context).trg_date_type == 'none':
                    self._action(cr, uid, [rule_id], obj.browse(cr, uid, ids, context=context), context=context)
        return True

    def _create(self, old_create, model, context=None):
        """
        Return a wrapper around `old_create` calling both `old_create` and
        `post_action`, in that order.
        """
        def wrapper(cr, uid, vals, context=context):
            if context is None:
                context = {}
            new_id = old_create(cr, uid, vals, context=context)
            if not context.get('action'):
                self.post_action(cr, uid, [new_id], model, context=context)
            return new_id
        return wrapper
    
    def _write(self, old_write, model, context=None):
        """
        Return a wrapper around `old_write` calling both `old_write` and
        `post_action`, in that order.
        """
        def wrapper(cr, uid, ids, vals, context=context):
            if context is None:
                context = {}
            if isinstance(ids, (str, int, long)):
                ids = [ids]
            old_write(cr, uid, ids, vals, context=context)
            if not context.get('action'):
                self.post_action(cr, uid, ids, model, context=context)
            return True
        return wrapper

    def _register_hook(self, cr, uid, ids, context=None):
        """
        Wrap every `create` and `write` methods of the models specified by
        the rules (given by `ids`).
        """
        for action_rule in self.browse(cr, uid, ids, context=context):
            model = action_rule.model_id.model
            obj_pool = self.pool.get(model)
            if not hasattr(obj_pool, 'base_action_ruled'):
                obj_pool.create = self._create(obj_pool.create, model, context=context)
                obj_pool.write = self._write(obj_pool.write, model, context=context)
                obj_pool.base_action_ruled = True

        return True

    def create(self, cr, uid, vals, context=None):
        res_id = super(base_action_rule, self).create(cr, uid, vals, context=context)
        self._register_hook(cr, uid, [res_id], context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        super(base_action_rule, self).write(cr, uid, ids, vals, context=context)
        self._register_hook(cr, uid, ids, context=context)
        return True

    def _check(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        """
        This Function is call by scheduler.
        """
        rule_pool = self.pool.get('base.action.rule')
        rule_ids = rule_pool.search(cr, uid, [], context=context)
        self._register_hook(cr, uid, rule_ids, context=context)

        rules = self.browse(cr, uid, rule_ids, context=context)
        for rule in rules:
            model = rule.model_id.model
            model_pool = self.pool.get(model)
            last_run = False
            if rule.last_run:
                last_run = get_datetime(rule.last_run)
            now = datetime.now()
            for obj_id in model_pool.search(cr, uid, [], context=context):
                obj = model_pool.browse(cr, uid, obj_id, context=context)
                # Calculate when this action should next occur for this object
                base = False
                if rule.trg_date_type=='create' and hasattr(obj, 'create_date'):
                    base = obj.create_date
                elif (rule.trg_date_type=='action_last'
                        and hasattr(obj, 'create_date')):
                    if hasattr(obj, 'date_action_last') and obj.date_action_last:
                        base = obj.date_action_last
                    else:
                        base = obj.create_date
                elif (rule.trg_date_type=='deadline'
                        and hasattr(obj, 'date_deadline')
                        and obj.date_deadline):
                    base = obj.date_deadline
                elif (rule.trg_date_type=='date'
                        and hasattr(obj, 'date')
                        and obj.date):
                    base = obj.date
                if base:
                    fnct = {
                        'minutes': lambda interval: timedelta(minutes=interval),
                        'day': lambda interval: timedelta(days=interval),
                        'hour': lambda interval: timedelta(hours=interval),
                        'month': lambda interval: timedelta(months=interval),
                    }
                    base = get_datetime(base)
                    delay = fnct[rule.trg_date_range_type](rule.trg_date_range)
                    action_date = base + delay
                    if (not last_run or (last_run <= action_date < now)):
                        self._action(cr, uid, [rule.id], [obj], context=context)
            rule_pool.write(cr, uid, [rule.id], {'last_run': now},
                            context=context)

    def format_body(self, body):
        """ Foramat Action rule's body
            @param self: The object pointer """
        return body and tools.ustr(body) or ''

    def format_mail(self, obj, body):
        data = {
            'object_id': obj.id,
            'object_subject': hasattr(obj, 'name') and obj.name or False,
            'object_date': hasattr(obj, 'date') and obj.date or False,
            'object_description': hasattr(obj, 'description') and obj.description or False,
            'object_user': hasattr(obj, 'user_id') and (obj.user_id and obj.user_id.name) or '/',
            'object_user_email': hasattr(obj, 'user_id') and (obj.user_id and \
                                     obj.user_id.user_email) or '/',
            'object_user_phone': hasattr(obj, 'partner_address_id') and (obj.partner_address_id and \
                                     obj.partner_address_id.phone) or '/',
            'partner': hasattr(obj, 'partner_id') and (obj.partner_id and obj.partner_id.name) or '/',
            'partner_email': hasattr(obj, 'partner_address_id') and (obj.partner_address_id and\
                                         obj.partner_address_id.email) or '/',
        }
        return self.format_body(body % data)

    def email_send(self, cr, uid, obj, emails, body, emailfrom=None, context=None):
        """ send email
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param email: pass the emails
            @param emailfrom: Pass name the email From else False
            @param context: A standard dictionary for contextual values """

        if not emailfrom:
            emailfrom = tools.config.get('email_from', False)

        if context is None:
            context = {}

        mail_message = self.pool.get('mail.message')
        body = self.format_mail(obj, body)
        if not emailfrom:
            if hasattr(obj, 'user_id') and obj.user_id and obj.user_id.user_email:
                emailfrom = obj.user_id.user_email

        name = '[%d] %s' % (obj.id, tools.ustr(obj.name))
        emailfrom = tools.ustr(emailfrom)
        reply_to = emailfrom
        if not emailfrom:
            raise osv.except_osv(_('Error!'),
                    _("No E-Mail ID Found for your Company address!"))
        return mail_message.schedule_with_attach(cr, uid, emailfrom, emails, name, body, model='base.action.rule', reply_to=reply_to, res_id=obj.id)


    def do_check(self, cr, uid, action, obj, context=None):
        """ check Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values """
        if context is None:
            context = {}
        ok = True
        if action.filter_id:
            if action.model_id.model == action.filter_id.model_id:
                context.update(eval(action.filter_id.context))
                obj_ids = obj._table.search(cr, uid, eval(action.filter_id.domain), context=context)
                if not obj.id in obj_ids:
                    ok = False
            else:
                ok = False
        if getattr(obj, 'user_id', False):
            ok = ok and (not action.trg_user_id.id or action.trg_user_id.id==obj.user_id.id)
        if getattr(obj, 'partner_id', False):
            ok = ok and (not action.trg_partner_id.id or action.trg_partner_id.id==obj.partner_id.id)
            ok = ok and (
                not action.trg_partner_categ_id.id or
                (
                    obj.partner_id.id and
                    (action.trg_partner_categ_id.id in map(lambda x: x.id, obj.partner_id.category_id or []))
                )
            )
        state_to = context.get('state_to', False)
        state = getattr(obj, 'state', False)
        if state:
            ok = ok and (not action.trg_state_from or action.trg_state_from==state)
        if state_to:
            ok = ok and (not action.trg_state_to or action.trg_state_to==state_to)
        elif action.trg_state_to:
            ok = False
        reg_name = action.regex_name
        result_name = True
        if reg_name:
            ptrn = re.compile(ustr(reg_name))
            _result = ptrn.search(ustr(obj.name))
            if not _result:
                result_name = False
        regex_n = not reg_name or result_name
        ok = ok and regex_n
        return ok

    def do_action(self, cr, uid, action, model_obj, obj, context=None):
        """ Do Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param action: pass action
            @param model_obj: pass Model object
            @param context: A standard dictionary for contextual values """
        if context is None:
            context = {}

        if action.server_action_id:
            context.update({'active_id':obj.id, 'active_ids':[obj.id]})
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
            if obj.user_id:
                emails.append(obj.user_id.user_email)

        if action.act_mail_to_watchers:
            emails += (action.act_email_cc or '').split(',')
        if action.act_mail_to_email:
            emails += (action.act_mail_to_email or '').split(',')

        locals_for_emails = {
            'user' : self.pool.get('res.users').browse(cr, uid, uid, context=context),
            'obj' : obj,
        }

        if action.act_email_to:
            emails.append(safe_eval(action.act_email_to, {}, locals_for_emails))

        emails = filter(None, emails)
        if len(emails) and action.act_mail_body:
            emails = list(set(emails))
            email_from = safe_eval(action.act_email_from, {}, locals_for_emails)

            def to_email(text):
                return re.findall(r'([^ ,<@]+@[^> ,]+)', text or '')
            emails = to_email(','.join(filter(None, emails)))
            email_froms = to_email(email_from)
            if email_froms:
                self.email_send(cr, uid, obj, emails, action.act_mail_body, emailfrom=email_froms[0])
        return True

    def _action(self, cr, uid, ids, objects, scrit=None, context=None):
        """ Do Action
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Basic Action Rule’s IDs,
            @param objects: pass objects
            @param context: A standard dictionary for contextual values """
        if context is None:
            context = {}

        context.update({'action': True})
        if not scrit:
            scrit = []

        for action in self.browse(cr, uid, ids, context=context):
            for obj in objects:
                if self.do_check(cr, uid, action, obj, context=context):
                    model_obj = self.pool.get(action.model_id.model)
                    self.do_action(cr, uid, action, model_obj, obj, context=context)

        context.update({'action': False})
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
        for rule in self.browse(cr, uid, ids, context=context):
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


class ir_cron(osv.osv):
    _inherit = 'ir.cron'
    _init_done = False

    def _poolJobs(self, db_name, check=False):
        if not self._init_done:
            self._init_done = True
            try:
                db = pooler.get_db(db_name)
            except:
                return False
            cr = db.cursor()
            try:
                next = datetime.now().strftime('%Y-%m-%d %H:00:00')
                # Putting nextcall always less than current time in order to call it every time
                cr.execute('UPDATE ir_cron set nextcall = \'%s\' where numbercall<>0 and active and model=\'base.action.rule\' ' % (next))
            finally:
                cr.commit()
                cr.close()

        super(ir_cron, self)._poolJobs(db_name, check=check)

ir_cron()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
