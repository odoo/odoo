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
from dateutil.relativedelta import relativedelta
import time
import logging

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hour': lambda interval: relativedelta(hours=interval),
    'day': lambda interval: relativedelta(days=interval),
    'month': lambda interval: relativedelta(months=interval),
    False: lambda interval: relativedelta(0),
}

def get_datetime(date_str):
    '''Return a datetime from a date string or a datetime string'''
    # complete date time if date_str contains only a date
    if ' ' not in date_str:
        date_str = date_str + " 00:00:00"
    return datetime.strptime(date_str, DEFAULT_SERVER_DATETIME_FORMAT)


class base_action_rule(osv.osv):
    """ Base Action Rules """

    _name = 'base.action.rule'
    _description = 'Action Rules'
    _order = 'sequence'

    _columns = {
        'name':  fields.char('Rule Name', required=True),
        'model_id': fields.many2one('ir.model', 'Related Document Model',
            required=True, domain=[('osv_memory', '=', False)]),
        'model': fields.related('model_id', 'model', type="char", string='Model'),
        'create_date': fields.datetime('Create Date', readonly=1),
        'active': fields.boolean('Active',
            help="When unchecked, the rule is hidden and will not be executed."),
        'sequence': fields.integer('Sequence',
            help="Gives the sequence order when displaying a list of rules."),
        'kind': fields.selection(
            [('on_create', 'On Creation'),
             ('on_write', 'On Update'),
             ('on_create_or_write', 'On Creation & Update'),
             ('on_time', 'Based on Timed Condition')],
            string='When to Run'),
        'trg_date_id': fields.many2one('ir.model.fields', string='Trigger Date',
            help="When should the condition be triggered. If present, will be checked by the scheduler. If empty, will be checked at creation and update.",
            domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]"),
        'trg_date_range': fields.integer('Delay after trigger date',
            help="Delay after the trigger date." \
            "You can put a negative number if you need a delay before the" \
            "trigger date, like sending a reminder 15 minutes before a meeting."),
        'trg_date_range_type': fields.selection([('minutes', 'Minutes'), ('hour', 'Hours'),
                                ('day', 'Days'), ('month', 'Months')], 'Delay type'),
        'trg_date_calendar_id': fields.many2one(
            'resource.calendar', 'Use Calendar',
            help='When calculating a day-based timed condition, it is possible to use a calendar to compute the date based on working days.',
            ondelete='set null',
        ),
        'act_user_id': fields.many2one('res.users', 'Set Responsible'),
        'act_followers': fields.many2many("res.partner", string="Add Followers"),
        'server_action_ids': fields.many2many('ir.actions.server', string='Server Actions',
            domain="[('model_id', '=', model_id)]",
            help="Examples: email reminders, call object service, etc."),
        'filter_pre_id': fields.many2one('ir.filters', string='Before Update Filter',
            ondelete='restrict',
            domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied before the update of the record."),
        'filter_id': fields.many2one('ir.filters', string='Filter',
            ondelete='restrict',
            domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied before executing the action rule."),
        'last_run': fields.datetime('Last Run', readonly=1, copy=False),
    }

    _defaults = {
        'active': True,
        'trg_date_range_type': 'day',
    }

    def onchange_kind(self, cr, uid, ids, kind, context=None):
        clear_fields = []
        if kind in ['on_create', 'on_create_or_write']:
            clear_fields = ['filter_pre_id', 'trg_date_id', 'trg_date_range', 'trg_date_range_type']
        elif kind in ['on_write', 'on_create_or_write']:
            clear_fields = ['trg_date_id', 'trg_date_range', 'trg_date_range_type']
        elif kind == 'on_time':
            clear_fields = ['filter_pre_id']
        return {'value': dict.fromkeys(clear_fields, False)}

    def _get_eval_context(self, cr, uid, context=None):
        """ Prepare the context used when evaluating python code
        :returns: dict -- evaluation context given to (safe_)eval """
        return {
            'time': time,
            'user': self.pool['res.users'].browse(cr, uid, uid, context=context),
        }

    def _filter(self, cr, uid, action, action_filter, record_ids, context=None):
        """ filter the list record_ids that satisfy the action filter """
        eval_context = self._get_eval_context(cr, uid, context=context)
        if record_ids and action_filter:
            assert action.model == action_filter.model_id, "Filter model different from action rule model"
            model = self.pool[action_filter.model_id]
            domain = [('id', 'in', record_ids)] + eval(action_filter.domain, eval_context)
            ctx = dict(context or {})
            ctx.update(eval(action_filter.context))
            record_ids = model.search(cr, uid, domain, context=ctx)
        return record_ids

    def _process(self, cr, uid, action, record_ids, context=None):
        """ process the given action on the records """
        model = self.pool[action.model_id.model]

        # modify records
        values = {}
        if 'date_action_last' in model._fields:
            values['date_action_last'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if action.act_user_id and 'user_id' in model._fields:
            values['user_id'] = action.act_user_id.id
        if values:
            model.write(cr, uid, record_ids, values, context=context)

        if action.act_followers and hasattr(model, 'message_subscribe'):
            follower_ids = map(int, action.act_followers)
            model.message_subscribe(cr, uid, record_ids, follower_ids, context=context)

        # execute server actions
        if action.server_action_ids:
            server_action_ids = map(int, action.server_action_ids)
            for record in model.browse(cr, uid, record_ids, context):
                action_server_obj = self.pool.get('ir.actions.server')
                ctx = dict(context, active_model=model._name, active_ids=[record.id], active_id=record.id)
                action_server_obj.run(cr, uid, server_action_ids, context=ctx)

        return True

    def _register_hook(self, cr, ids=None):
        """ Wrap the methods `create` and `write` of the models specified by
            the rules given by `ids` (or all existing rules if `ids` is `None`.)
        """
        #
        # Note: the patched methods create and write must be defined inside
        # another function, otherwise their closure may be wrong. For instance,
        # the function create refers to the outer variable 'create', which you
        # expect to be bound to create itself. But that expectation is wrong if
        # create is defined inside a loop; in that case, the variable 'create'
        # is bound to the last function defined by the loop.
        #

        def make_create():
            """ instanciate a create method that processes action rules """
            def create(self, cr, uid, vals, context=None, **kwargs):
                # avoid loops or cascading actions
                if context and context.get('action'):
                    return create.origin(self, cr, uid, vals, context=context)

                # call original method with a modified context
                context = dict(context or {}, action=True)
                new_id = create.origin(self, cr, uid, vals, context=context, **kwargs)

                # as it is a new record, we do not consider the actions that have a prefilter
                action_model = self.pool.get('base.action.rule')
                action_dom = [('model', '=', self._name),
                              ('kind', 'in', ['on_create', 'on_create_or_write'])]
                action_ids = action_model.search(cr, uid, action_dom, context=dict(context, active_test=True))

                # check postconditions, and execute actions on the records that satisfy them
                for action in action_model.browse(cr, uid, action_ids, context=context):
                    if action_model._filter(cr, uid, action, action.filter_id, [new_id], context=context):
                        action_model._process(cr, uid, action, [new_id], context=context)
                return new_id

            return create

        def make_write():
            """ instanciate a write method that processes action rules """
            def write(self, cr, uid, ids, vals, context=None, **kwargs):
                # avoid loops or cascading actions
                if context and context.get('action'):
                    return write.origin(self, cr, uid, ids, vals, context=context)

                # modify context
                context = dict(context or {}, action=True)
                ids = [ids] if isinstance(ids, (int, long, str)) else ids

                # retrieve the action rules to possibly execute
                action_model = self.pool.get('base.action.rule')
                action_dom = [('model', '=', self._name),
                              ('kind', 'in', ['on_write', 'on_create_or_write'])]
                action_ids = action_model.search(cr, uid, action_dom, context=context)
                actions = action_model.browse(cr, uid, action_ids, context=context)

                # check preconditions
                pre_ids = {}
                for action in actions:
                    pre_ids[action] = action_model._filter(cr, uid, action, action.filter_pre_id, ids, context=context)

                # call original method
                write.origin(self, cr, uid, ids, vals, context=context, **kwargs)

                # check postconditions, and execute actions on the records that satisfy them
                for action in actions:
                    post_ids = action_model._filter(cr, uid, action, action.filter_id, pre_ids[action], context=context)
                    if post_ids:
                        action_model._process(cr, uid, action, post_ids, context=context)
                return True

            return write

        updated = False
        if ids is None:
            ids = self.search(cr, SUPERUSER_ID, [])
        for action_rule in self.browse(cr, SUPERUSER_ID, ids):
            model = action_rule.model_id.model
            model_obj = self.pool.get(model)
            if model_obj and not hasattr(model_obj, 'base_action_ruled'):
                # monkey-patch methods create and write
                model_obj._patch_method('create', make_create())
                model_obj._patch_method('write', make_write())
                model_obj.base_action_ruled = True
                updated = True

        return updated

    def _update_cron(self, cr, uid, context=None):
        try:
            cron = self.pool['ir.model.data'].get_object(
                cr, uid, 'base_action_rule', 'ir_cron_crm_action', context=context)
        except ValueError:
            return False

        return cron.toggle(model=self._name, domain=[('kind', '=', 'on_time')])

    def create(self, cr, uid, vals, context=None):
        res_id = super(base_action_rule, self).create(cr, uid, vals, context=context)
        if self._register_hook(cr, [res_id]):
            openerp.modules.registry.RegistryManager.signal_registry_change(cr.dbname)
        self._update_cron(cr, uid, context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        super(base_action_rule, self).write(cr, uid, ids, vals, context=context)
        if self._register_hook(cr, ids):
            openerp.modules.registry.RegistryManager.signal_registry_change(cr.dbname)
        self._update_cron(cr, uid, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        res = super(base_action_rule, self).unlink(cr, uid, ids, context=context)
        self._update_cron(cr, uid, context=context)
        return res

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        data = {'model': False, 'filter_pre_id': False, 'filter_id': False}
        if model_id:
            model = self.pool.get('ir.model').browse(cr, uid, model_id, context=context)
            data.update({'model': model.model})
        return {'value': data}

    def _check_delay(self, cr, uid, action, record, record_dt, context=None):
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day':
            start_dt = get_datetime(record_dt)
            action_dt = self.pool['resource.calendar'].schedule_days_get_date(
                cr, uid, action.trg_date_calendar_id.id, action.trg_date_range,
                day_date=start_dt, compute_leaves=True, context=context
            )
        else:
            delay = DATE_RANGE_FUNCTION[action.trg_date_range_type](action.trg_date_range)
            action_dt = get_datetime(record_dt) + delay
        return action_dt

    def _check(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """ This Function is called by scheduler. """
        context = context or {}
        # retrieve all the action rules to run based on a timed condition
        action_dom = [('kind', '=', 'on_time')]
        action_ids = self.search(cr, uid, action_dom, context=dict(context, active_test=True))
        eval_context = self._get_eval_context(cr, uid, context=context)
        for action in self.browse(cr, uid, action_ids, context=context):
            now = datetime.now()
            if action.last_run:
                last_run = get_datetime(action.last_run)
            else:
                last_run = datetime.utcfromtimestamp(0)

            # retrieve all the records that satisfy the action's condition
            model = self.pool[action.model_id.model]
            domain = []
            ctx = dict(context)
            if action.filter_id:
                domain = eval(action.filter_id.domain, eval_context)
                ctx.update(eval(action.filter_id.context))
                if 'lang' not in ctx:
                    # Filters might be language-sensitive, attempt to reuse creator lang
                    # as we are usually running this as super-user in background
                    [filter_meta] = action.filter_id.get_metadata()
                    user_id = filter_meta['write_uid'] and filter_meta['write_uid'][0] or \
                                    filter_meta['create_uid'][0]
                    ctx['lang'] = self.pool['res.users'].browse(cr, uid, user_id).lang
            record_ids = model.search(cr, uid, domain, context=ctx)

            # determine when action should occur for the records
            date_field = action.trg_date_id.name
            if date_field == 'date_action_last' and 'create_date' in model._fields:
                get_record_dt = lambda record: record[date_field] or record.create_date
            else:
                get_record_dt = lambda record: record[date_field]

            # process action on the records that should be executed
            for record in model.browse(cr, uid, record_ids, context=context):
                record_dt = get_record_dt(record)
                if not record_dt:
                    continue
                action_dt = self._check_delay(cr, uid, action, record, record_dt, context=context)
                if last_run <= action_dt < now:
                    try:
                        context = dict(context or {}, action=True)
                        self._process(cr, uid, action, [record.id], context=context)
                    except Exception:
                        import traceback
                        _logger.error(traceback.format_exc())

            action.write({'last_run': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

            if automatic:
                # auto-commit for batch processing
                cr.commit()
