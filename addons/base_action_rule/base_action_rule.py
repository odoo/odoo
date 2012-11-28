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

from datetime import datetime
from datetime import timedelta
import re
import time
from openerp import SUPERUSER_ID

from osv import fields, osv, orm
from tools.translate import _
from tools.safe_eval import safe_eval
from tools import ustr
import pooler
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
        """ Get State """
        return self.state_get(cr, uid, context=context)

    def state_get(self, cr, uid, context=None):
        """ Get State """
        return [('', ''), ('na','N/A (No previous state)')]

    def priority_get(self, cr, uid, context=None):
        """ Get Priority """
        return [('', '')]

    _columns = {
        'name':  fields.char('Rule Name', size=64, required=True),
        'model_id': fields.many2one('ir.model', 'Related Document Model', required=True, domain=[('osv_memory','=', False)]),
        'model': fields.related('model_id', 'model', type="char", size=256, string='Model'),
        'create_date': fields.datetime('Create Date', readonly=1),
        'active': fields.boolean('Active', help="If the active field is set to False,\
 it will allow you to hide the rule without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order \
when displaying a list of rules."),
        'trg_date_type':  fields.selection([
            ('none', 'None'),
            ('create', 'Creation Date'),
            ('write', 'Last Modified Date'),
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
        'trg_state_from': fields.selection(_state_get, 'and previously was', size=16),
        'trg_state_to': fields.selection(_state_get, 'Status changes to', size=16),

        'act_user_id': fields.many2one('res.users', 'Set Responsible to'),
        'act_state': fields.selection(_state_get, 'Set State to', size=16),
        'act_followers': fields.many2many("res.partner", string="Set Followers"),
        'regex_name': fields.char('Regex on Resource Name', size=128, help="Regular expression for matching name of the resource\
\ne.g.: 'urgent.*' will search for records having name starting with the string 'urgent'\
\nNote: This is case sensitive search."),
        'server_action_ids': fields.one2many('ir.actions.server', 'action_rule_id', 'Server Action', help="Define Server actions.\neg:Email Reminders, Call Object Service, etc.."), #TODO: set domain [('model_id','=',model_id)]
        'filter_id':fields.many2one('ir.filters', 'Postcondition Filter', required=False), #TODO: set domain [('model_id','=',model_id.model)]
        'filter_pre_id': fields.many2one('ir.filters', 'Precondition Filter', required=False),
        'last_run': fields.datetime('Last Run', readonly=1),
    }

    _defaults = {
        'active': True,
        'trg_date_type': 'none',
        'trg_date_range_type': 'day',
    }

    _order = 'sequence'


    def post_action(self, cr, uid, ids, model, precondition_ok=None, context=None):
        # Searching for action rules
        cr.execute("SELECT model.model, rule.id  FROM base_action_rule rule \
                        LEFT JOIN ir_model model on (model.id = rule.model_id) \
                        WHERE active and model = %s", (model,))
        res = cr.fetchall()
        # Check if any rule matching with current object
        for obj_name, rule_id in res:
            model_pool = self.pool.get(obj_name)
            # If the rule doesn't involve a time condition, run it immediately
            # Otherwise we let the scheduler run the action
            if self.browse(cr, uid, rule_id, context=context).trg_date_type == 'none':
                self._action(cr, uid, [rule_id], model_pool.browse(cr, uid, ids, context=context), precondition_ok=precondition_ok, context=context)
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
            #As it is a new record, we can assume that the precondition is true for every filter. 
            #(There is nothing before the create so no condition)
            precondition_ok = {}
            precondition_ok[new_id] = {}
            for action in self.browse(cr, uid, self.search(cr, uid, [], context=context), context=context):
                if action.filter_pre_id:
                    precondition_ok[new_id][action.id] = False
                else:
                    precondition_ok[new_id][action.id] = True
            if not context.get('action'):
                self.post_action(cr, uid, [new_id], model, precondition_ok=precondition_ok, context=context)
            return new_id
        return wrapper

    def _write(self, old_write, model, context=None):
        """
        Return a wrapper around `old_write` calling both `old_write` and
        `post_action`, in that order.
        """
        def wrapper(cr, uid, ids, vals, context=context):
            old_records = {}
            if context is None:
                context = {}
            if isinstance(ids, (str, int, long)):
                ids = [ids]
            model_pool = self.pool.get(model)
            # We check for the pre-filter. We must apply it before the write
            precondition_ok = {}
            for id in ids:
                precondition_ok[id] = {}
                for action in self.browse(cr, uid, self.search(cr, uid, [], context=context), context=context):
                    precondition_ok[id][action.id] = True
                    if action.filter_pre_id and action.model_id.model == action.filter_pre_id.model_id:
                        ctx = dict(context)
                        ctx.update(eval(action.filter_pre_id.context))
                        obj_ids = []
                        if self.pool.get(action.model_id.model)!=None:
                            obj_ids = self.pool.get(action.model_id.model).search(cr, uid, eval(action.filter_pre_id.domain), context=ctx)
                        precondition_ok[id][action.id] = id in obj_ids
            old_write(cr, uid, ids, vals, context=context)
            if not context.get('action'):
                self.post_action(cr, uid, ids, model, precondition_ok=precondition_ok, context=context)
            return True
        return wrapper

    def _register_hook(self, cr):
        """
        Wrap every `create` and `write` methods of the models specified by
        the rules (given by `ids`).
        """
        ids = self.search(cr,SUPERUSER_ID,[])
        return self._register_hook_(cr,SUPERUSER_ID,ids,context=None)

    def _register_hook_(self, cr, uid, ids, context=None):
        """
        Wrap every `create` and `write` methods of the models specified by
        the rules (given by `ids`).
        """
        reg_ids = []
        if not isinstance(ids, list):
            reg_ids.append(ids)
        else:
            reg_ids.extend(ids)
        for action_rule in self.browse(cr, uid, reg_ids, context=context):
            model = action_rule.model_id.model
            obj_pool = self.pool.get(model)
            if not hasattr(obj_pool, 'base_action_ruled'):
                obj_pool.create = self._create(obj_pool.create, model, context=None)
                obj_pool.write = self._write(obj_pool.write, model, context=None)
                obj_pool.base_action_ruled = True
        return True

    def create(self, cr, uid, vals, context=None):
        res_id = super(base_action_rule, self).create(cr, uid, vals, context=context)
        self._register_hook_(cr, uid, res_id,context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        super(base_action_rule, self).write(cr, uid, ids, vals, context=context)
        self._register_hook_(cr, uid, ids, context=context)
        return True

    def _check(self, cr, uid, automatic=False, use_new_cursor=False, \
                       context=None):
        """
        This Function is call by scheduler.
        """
        rule_ids = self.search(cr, uid, [], context=context)
        self._register_hook_(cr, uid, rule_ids, context=context)
        if context is None:
            context = {}
        for rule in self.browse(cr, uid, rule_ids, context=context):
            model = rule.model_id.model
            model_pool = self.pool.get(model)
            last_run = False
            if rule.last_run:
                last_run = get_datetime(rule.last_run)
            now = datetime.now()
            ctx = dict(context)            
            if rule.filter_id and rule.model_id.model == rule.filter_id.model_id:
                ctx.update(eval(rule.filter_id.context))
                obj_ids = model_pool.search(cr, uid, eval(rule.filter_id.domain), context=ctx)
            else:
                obj_ids = model_pool.search(cr, uid, [], context=ctx)
            for obj in model_pool.browse(cr, uid, obj_ids, context=ctx):
                # Calculate when this action should next occur for this object
                base = False
                if rule.trg_date_type=='create' and hasattr(obj, 'create_date'):
                    base = obj.create_date
                elif rule.trg_date_type=='write' and hasattr(obj, 'write_date'):
                    base = obj.write_date
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
                        try:
                            self._action(cr, uid, [rule.id], obj, context=ctx)
                            self.write(cr, uid, [rule.id], {'last_run': now}, context=context)
                        except Exception, e:
                            import traceback
                            print traceback.format_exc()
                        
                        

    def do_check(self, cr, uid, action, obj, precondition_ok=True, context=None):
        """ check Action """
        if context is None:
            context = {}
        ok = precondition_ok
        if action.filter_id and action.model_id.model == action.filter_id.model_id:
            ctx = dict(context)
            ctx.update(eval(action.filter_id.context))
            obj_ids = self.pool.get(action.model_id.model).search(cr, uid, eval(action.filter_id.domain), context=ctx)
            ok = ok and obj.id in obj_ids
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

    def do_action(self, cr, uid, action, obj, context=None):
        """ Do Action """
        if context is None:
            context = {}
        ctx = dict(context)
        model_obj = self.pool.get(action.model_id.model)
        action_server_obj = self.pool.get('ir.actions.server')
        if action.server_action_ids:
            ctx.update({'active_model': action.model_id.model, 'active_id':obj.id, 'active_ids':[obj.id]})
            action_server_obj.run(cr, uid, [x.id for x in action.server_action_ids], context=ctx)

        write = {}
        if hasattr(obj, 'user_id') and action.act_user_id:
            write['user_id'] = action.act_user_id.id
        if hasattr(obj, 'date_action_last'):
            write['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(obj, 'state') and action.act_state:
            write['state'] = action.act_state

        model_obj.write(cr, uid, [obj.id], write, context)
        if hasattr(obj, 'state') and hasattr(obj, 'message_post') and action.act_state:
            model_obj.message_post(cr, uid, [obj], _(action.act_state), context=context)
        
        if hasattr(obj, 'message_subscribe') and action.act_followers:
            exits_followers = [x.id for x in obj.message_follower_ids]
            new_followers = [x.id for x in action.act_followers if x.id not in exits_followers]
            if new_followers:
                model_obj.message_subscribe(cr, uid, [obj.id], new_followers, context=context)
        return True

    def _action(self, cr, uid, ids, objects, scrit=None, precondition_ok=None, context=None):
        """ Do Action """
        if context is None:
            context = {}
        context.update({'action': True})
        if not isinstance(objects, list):
            objects = [objects]
        for action in self.browse(cr, uid, ids, context=context):
            for obj in objects:
                ok = True
                if precondition_ok!=None:
                    ok = precondition_ok[obj.id][action.id]
                if self.do_check(cr, uid, action, obj, precondition_ok=ok, context=context):
                    self.do_action(cr, uid, action, obj, context=context)
        context.update({'action': False})
        return True

base_action_rule()

class actions_server(osv.osv):
    _inherit = 'ir.actions.server'
    _columns = {
        'action_rule_id': fields.many2one("base.action.rule", string="Action Rule")
    }
actions_server()

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
