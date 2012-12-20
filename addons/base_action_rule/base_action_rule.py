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
import time
import logging

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

DATE_TYPE_TO_FIELD = {
    'create': 'create_date',
    'write': 'write_date',
    'action_last': 'date_action_last',
    'date': 'date',
    'deadline': 'date_deadline',
}

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: timedelta(minutes=interval),
    'hour': lambda interval: timedelta(hours=interval),
    'day': lambda interval: timedelta(days=interval),
    'month': lambda interval: timedelta(months=interval),
    False: lambda interval: timedelta(0),
}

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

    _columns = {
        'name':  fields.char('Rule Name', size=64, required=True),
        'model_id': fields.many2one('ir.model', 'Related Document Model',
            required=True, domain=[('osv_memory', '=', False)]),
        'model': fields.related('model_id', 'model', type="char", size=256, string='Model'),
        'create_date': fields.datetime('Create Date', readonly=1),
        'active': fields.boolean('Active',
            help="When unchecked, the rule is hidden and will not be executed."),
        'sequence': fields.integer('Sequence',
            help="Gives the sequence order when displaying a list of rules."),
        'trg_date_type':  fields.selection([
            ('none', 'None'),
            ('create', 'Creation Date'),
            ('write', 'Last Modified Date'),
            ('action_last', 'Last Action Date'),
            ('date', 'Date'),
            ('deadline', 'Deadline'),
            ], 'Trigger Date', size=16),
        'trg_date_range': fields.integer('Delay after trigger date',
            help="Delay after the trigger date." \
            "You can put a negative number if you need a delay before the" \
            "trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'), ('hour', 'Hours'),
                                ('day', 'Days'), ('month', 'Months')], 'Delay type'),
        'act_user_id': fields.many2one('res.users', 'Set Responsible to'),
        'act_state': fields.selection(_state_get, 'Set State to', size=16),
        'act_followers': fields.many2many("res.partner", string="Set Followers"),
        'server_action_ids': fields.many2many('ir.actions.server',
            domain="[('model_id', '=', model_id)]",
            string='Server Action',
            help="Example: email reminders, call object service, etc."),
        'filter_pre_id': fields.many2one('ir.filters', string='Before Filter',
            ondelete='restrict',
            domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied before the update of the record."),
        'filter_id': fields.many2one('ir.filters', string='After Filter',
            ondelete='restrict',
            domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied after the update of the record."),
        'last_run': fields.datetime('Last Run', readonly=1),
    }

    _defaults = {
        'active': True,
        'trg_date_type': 'none',
        'trg_date_range_type': 'day',
    }

    _order = 'sequence'

    def _filter(self, cr, uid, action_filter, record_ids=None, context=None):
        """ filter the list record_ids that satisfy the action_filter """
        if record_ids and action_filter:
            model = self.pool.get(action_filter.model_id)
            domain = [('id', 'in', record_ids)] + eval(action_filter.domain)
            ctx = dict(context or {})
            ctx.update(eval(action_filter.context))
            record_ids = model.search(cr, uid, domain, context=ctx)
        return record_ids

    def _process(self, cr, uid, action, record_ids, context=None):
        """ process the given action on the records """
        # IMPORTANT: add 'action':True in the context to avoid cascading actions
        context = dict(context or {}, action=True)

        # execute server actions
        model = self.pool.get(action.model_id.model)
        if action.server_action_ids:
            server_action_ids = map(int, action.server_action_ids)
            for record in model.browse(cr, uid, record_ids, context):
                action_server_obj = self.pool.get('ir.actions.server')
                ctx = dict(context, active_model=model._name, active_ids=[record.id], active_id=record.id)
                action_server_obj.run(cr, uid, server_action_ids, context=ctx)

        # modify records
        values = {}
        if action.act_user_id and 'user_id' in model._all_columns:
            values['user_id'] = action.act_user_id.id
        if 'date_action_last' in model._all_columns:
            values['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        if action.act_state and 'state' in model._all_columns:
            values['state'] = action.act_state

        if values:
            model.write(cr, uid, record_ids, values, context=context)
        if values.get('state') and hasattr(model, 'message_post'):
            model.message_post(cr, uid, record_ids, _(action.act_state), context=context)
        if action.act_followers and hasattr(model, 'message_subscribe'):
            model.message_subscribe(cr, uid, record_ids, map(int, action.act_followers), context=context)

        return True

    def _wrap_create(self, old_create, model):
        """ Return a wrapper around `old_create` calling both `old_create` and
            `_process`, in that order.
        """
        def wrapper(cr, uid, vals, context=None):
            new_id = old_create(cr, uid, vals, context=context)
            if not (context and context.get('action')):
                # as it is a new record, we do not consider the actions that have a prefilter
                action_dom = [('model', '=', model), ('trg_date_type', 'in', ('none', False)), ('filter_pre_id', '=', False)]
                action_ids = self.search(cr, uid, action_dom, context=context)
                # check postconditions, and execute actions on the records that satisfy them
                for action in self.browse(cr, uid, action_ids, context=context):
                    if self._filter(cr, uid, action.filter_id, [new_id], context=context):
                        self._process(cr, uid, action, [new_id], context=context)
            return new_id

        return wrapper

    def _wrap_write(self, old_write, model):
        """ Return a wrapper around `old_write` calling both `old_write` and
            `_process`, in that order.
        """
        def wrapper(cr, uid, ids, vals, context=None):
            if context and context.get('action'):
                return old_write(cr, uid, ids, vals, context=context)

            ids = [ids] if isinstance(ids, (int, long, str)) else ids
            # retrieve the action rules to possibly execute
            action_dom = [('model', '=', model), ('trg_date_type', 'in', ('none', False))]
            action_ids = self.search(cr, uid, action_dom, context=context)
            actions = self.browse(cr, uid, action_ids, context=context)
            # check preconditions
            pre_ids = {}
            for action in actions:
                pre_ids[action] = self._filter(cr, uid, action.filter_pre_id, ids, context=context)
            # execute write
            old_write(cr, uid, ids, vals, context=context)
            # check postconditions, and execute actions on the records that satisfy them
            for action in actions:
                post_ids = self._filter(cr, uid, action.filter_id, pre_ids[action], context=context)
                if post_ids:
                    self._process(cr, uid, action, post_ids, context=context)
            return True

        return wrapper

    def _register_hook(self, cr, ids=None):
        """ Wrap the methods `create` and `write` of the models specified by
            the rules given by `ids` (or all existing rules if `ids` is `Ǹone`.)
        """
        if ids is None:
            ids = self.search(cr, SUPERUSER_ID, [])
        for action_rule in self.browse(cr, SUPERUSER_ID, ids):
            model = action_rule.model_id.model
            model_obj = self.pool.get(model)
            if not hasattr(model_obj, 'base_action_ruled'):
                model_obj.create = self._wrap_create(model_obj.create, model)
                model_obj.write = self._wrap_write(model_obj.write, model)
                model_obj.base_action_ruled = True
        return True

    def create(self, cr, uid, vals, context=None):
        res_id = super(base_action_rule, self).create(cr, uid, vals, context=context)
        self._register_hook(cr, [res_id])
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        super(base_action_rule, self).write(cr, uid, ids, vals, context=context)
        self._register_hook(cr, ids)
        return True

    def _check(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """ This Function is called by scheduler. """
        context = context or {}
        # retrieve all the action rules that have a trg_date_type and no precondition
        action_dom = [('trg_date_type', 'not in', ('none', False)), ('filter_pre_id', '=', False)]
        action_ids = self.search(cr, uid, action_dom, context=context)
        for action in self.browse(cr, uid, action_ids, context=context):
            now = datetime.now()
            last_run = get_datetime(action.last_run) if action.last_run else False

            # retrieve all the records that satisfy the action's condition
            model = self.pool.get(action.model_id.model)
            domain = []
            ctx = dict(context)
            if action.filter_id:
                domain = eval(action.filter_id.domain)
                ctx.update(eval(action.filter_id.context))
            record_ids = model.search(cr, uid, domain, context=ctx)

            # determine when action should occur for the records
            date_field = DATE_TYPE_TO_FIELD.get(action.trg_date_type)
            if date_field not in model._all_columns:
                continue
            delay = DATE_RANGE_FUNCTION[action.trg_date_range_type](action.trg_date_range)

            # process action on the records that should be executed
            for record in model.browse(cr, uid, record_ids, context=context):
                action_dt = get_datetime(record[date_field]) + delay
                if last_run and (last_run <= action_dt < now) or (action_dt < now):
                    try:
                        self._process(cr, uid, action, [record.id], context=context)
                    except Exception:
                        import traceback
                        _logger.error(traceback.format_exc())

            action.write({'last_run': now})
