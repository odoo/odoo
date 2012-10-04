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
        return [('', '')]

    def priority_get(self, cr, uid, context=None):
        """ Get Priority """
        return [('', '')]

    _columns = {
        'name':  fields.char('Rule Name', size=64, required=True),
        'model_id': fields.many2one('ir.model', 'Related Document Model', required=True, domain=[('osv_memory','=', False)]),
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

        'act_user_id': fields.many2one('res.users', 'Set Responsible to'),
        'act_state': fields.selection(_state_get, 'Set State to', size=16),
        'act_followers': fields.many2many("res.partner", string="Set Followers"),
        'regex_name': fields.char('Regex on Resource Name', size=128, help="Regular expression for matching name of the resource\
\ne.g.: 'urgent.*' will search for records having name starting with the string 'urgent'\
\nNote: This is case sensitive search."),
        'server_action_id': fields.many2one('ir.actions.server', 'Server Action', help="Describes the action name.\neg:on which object which action to be taken on basis of which condition"),
        'filter_id':fields.many2one('ir.filters', 'Filter', required=False), #TODO: set domain [('model_id','=',model)]
        'last_run': fields.datetime('Last Run', readonly=1),
    }

    _defaults = {
        'active': lambda *a: True,
        'trg_date_type': lambda *a: 'none',
        'trg_date_range_type': lambda *a: 'day',
    }

    _order = 'sequence'


    def post_action(self, cr, uid, ids, model, context=None):
        # Searching for action rules
        cr.execute("SELECT model.model, rule.id  FROM base_action_rule rule \
                        LEFT JOIN ir_model model on (model.id = rule.model_id) \
                        WHERE active and model = %s", (model,))
        res = cr.fetchall()
        # Check if any rule matching with current object
        for obj_name, rule_id in res:
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

    def do_check(self, cr, uid, action, obj, context=None):
        """ check Action """
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
        """ Do Action """
        if context is None:
            context = {}

        if action.server_action_id:
            context.update({'active_id':obj.id, 'active_ids':[obj.id]})
            self.pool.get('ir.actions.server').run(cr, uid, [action.server_action_id.id], context)

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
            model_obj.message_subscribe(cr, uid, [obj.id], [x.id for x in action.act_followers], context=context)
        return True

    def _action(self, cr, uid, ids, objects, scrit=None, context=None):
        """ Do Action """
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
