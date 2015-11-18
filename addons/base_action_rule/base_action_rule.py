# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
import datetime as DT
import dateutil
import time
import logging

import openerp
from openerp import SUPERUSER_ID
from openerp.modules.registry import RegistryManager
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
            required=True, domain=[('transient', '=', False)]),
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
             ('on_unlink', 'On Deletion'),
             ('on_change', 'Based on Form Modification'),
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
        'filter_pre_id': fields.many2one(
            'ir.filters', string='Before Update Filter',
            ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied before the update of the record."),
        'filter_pre_domain': fields.char(string='Before Update Domain', help="If present, this condition must be satisfied before the update of the record."),
        'filter_id': fields.many2one(
            'ir.filters', string='Filter',
            ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
            help="If present, this condition must be satisfied before executing the action rule."),
        'filter_domain': fields.char(string='Domain', help="If present, this condition must be satisfied before executing the action rule."),
        'last_run': fields.datetime('Last Run', readonly=1, copy=False),
        'on_change_fields': fields.char(string="On Change Fields Trigger",
            help="Comma-separated list of field names that triggers the onchange."),
    }

    # which fields have an impact on the registry
    CRITICAL_FIELDS = ['model_id', 'active', 'kind', 'on_change_fields']

    _defaults = {
        'active': True,
        'trg_date_range_type': 'day',
    }

    def onchange_kind(self, cr, uid, ids, kind, context=None):
        clear_fields = []
        if kind in ['on_create', 'on_create_or_write', 'on_unlink']:
            clear_fields = ['filter_pre_id', 'filter_pre_domain', 'trg_date_id', 'trg_date_range', 'trg_date_range_type']
        elif kind in ['on_write', 'on_create_or_write']:
            clear_fields = ['trg_date_id', 'trg_date_range', 'trg_date_range_type']
        elif kind == 'on_time':
            clear_fields = ['filter_pre_id', 'filter_pre_domain']
        return {'value': dict.fromkeys(clear_fields, False)}

    def onchange_filter_pre_id(self, cr, uid, ids, filter_pre_id, context=None):
        ir_filter = self.pool['ir.filters'].browse(cr, uid, filter_pre_id, context=context)
        return {'value': {'filter_pre_domain': ir_filter.domain}}

    def onchange_filter_id(self, cr, uid, ids, filter_id, context=None):
        ir_filter = self.pool['ir.filters'].browse(cr, uid, filter_id, context=context)
        return {'value': {'filter_domain': ir_filter.domain}}

    @openerp.api.model
    def _get_actions(self, records, kinds):
        """ Return the actions of the given kinds for records' model. The
        returned actions' context contain an object to manage processing.
        """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [('model', '=', records._name), ('kind', 'in', kinds)]
        actions = self.with_context(active_test=True).search(domain)
        return actions.with_env(self.env)

    @openerp.api.model
    def _get_eval_context(self):
        """ Prepare the context used when evaluating python code
        :returns: dict -- evaluation context given to (safe_)eval """
        return {
            'datetime': DT,
            'dateutil': dateutil,
            'time': time,
            'uid': self.env.uid,
            'user': self.env.user,
        }

    @openerp.api.model
    def _filter_pre(self, records):
        """ Filter the records that satisfy the precondition of action ``self``. """
        if self.filter_pre_id and records:
            eval_context = self._get_eval_context()
            domain = [('id', 'in', records.ids)] + eval(self.filter_pre_id.domain, eval_context)
            ctx = eval(self.filter_pre_id.context)
            return records.with_context(**ctx).search(domain).with_env(records.env)
        elif self.filter_pre_domain and records:
            eval_context = self._get_eval_context()
            domain = [('id', 'in', records.ids)] + eval(self.filter_pre_domain, eval_context)
            return records.search(domain)
        else:
            return records

    @openerp.api.model
    def _filter_post(self, records):
        """ Filter the records that satisfy the postcondition of action ``self``. """
        if self.filter_id and records:
            eval_context = self._get_eval_context()
            domain = [('id', 'in', records.ids)] + eval(self.filter_id.domain, eval_context)
            ctx = eval(self.filter_id.context)
            return records.with_context(**ctx).search(domain).with_env(records.env)
        elif self.filter_domain and records:
            eval_context = self._get_eval_context()
            domain = [('id', 'in', records.ids)] + eval(self.filter_domain, eval_context)
            return records.search(domain)
        else:
            return records

    @openerp.api.multi
    def _process(self, records):
        """ Process action ``self`` on the ``records`` that have not been done yet. """
        # filter out the records on which self has already been done, then mark
        # remaining records as done (to avoid recursive processing)
        action_done = self._context['__action_done']
        records -= action_done.setdefault(self, records.browse())
        if not records:
            return
        action_done[self] |= records

        # modify records
        values = {}
        if 'date_action_last' in records._fields:
            values['date_action_last'] = openerp.fields.Datetime.now()
        if self.act_user_id and 'user_id' in records._fields:
            values['user_id'] = self.act_user_id.id
        if values:
            records.write(values)

        # subscribe followers
        if self.act_followers and hasattr(records, 'message_subscribe'):
            records.message_subscribe(self.act_followers.ids)

        # execute server actions
        if self.server_action_ids:
            for record in records:
                ctx = {'active_model': record._name, 'active_ids': record.ids, 'active_id': record.id}
                self.server_action_ids.with_context(**ctx).run()

    def _register_hook(self, cr):
        """ Patch models that should trigger action rules based on creation,
        modification, deletion of records and form onchanges.
        """
        #
        # Note: the patched methods must be defined inside another function,
        # otherwise their closure may be wrong. For instance, the function
        # create refers to the outer variable 'create', which you expect to be
        # bound to create itself. But that expectation is wrong if create is
        # defined inside a loop; in that case, the variable 'create' is bound to
        # the last function defined by the loop.
        #

        def make_create():
            """ Instanciate a create method that processes action rules. """
            @openerp.api.model
            def create(self, vals):
                # retrieve the action rules to possibly execute
                actions = self.env['base.action.rule']._get_actions(self, ['on_create', 'on_create_or_write'])

                # call original method
                record = create.origin(self.with_env(actions.env), vals)

                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=None):
                    action._process(action._filter_post(record))

                return record.with_env(self.env)

            return create

        def make_write():
            """ Instanciate a _write method that processes action rules. """
            #
            # Note: we patch method _write() instead of write() in order to
            # catch updates made by field recomputations.
            #
            @openerp.api.multi
            def _write(self, vals):
                # retrieve the action rules to possibly execute
                actions = self.env['base.action.rule']._get_actions(self, ['on_write', 'on_create_or_write'])
                records = self.with_env(actions.env)

                # check preconditions on records
                pre = {action: action._filter_pre(records) for action in actions}

                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in records.read(list(vals))
                }

                # call original method
                _write.origin(records, vals)

                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    action._process(action._filter_post(pre[action]))
                return True

            return _write

        def make_unlink():
            """ Instanciate an unlink method that processes action rules. """
            @openerp.api.multi
            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                actions = self.env['base.action.rule']._get_actions(self, ['on_unlink'])
                records = self.with_env(actions.env)

                # check conditions, and execute actions on the records that satisfy them
                for action in actions:
                    action._process(action._filter_post(pre[action]))

                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(action_rule_id):
            """ Instanciate an onchange method for the given action rule. """
            def base_action_rule_onchange(self):
                action_rule = self.env['base.action.rule'].browse(action_rule_id)
                server_actions = action_rule.server_action_ids.with_context(active_model=self._name, onchange_self=self)
                result = {}
                for server_action in server_actions:
                    res = server_action.run()
                    if res and 'value' in res:
                        res['value'].pop('id', None)
                        self.update(self._convert_to_cache(res['value'], validate=False))
                    if res and 'domain' in res:
                        result.setdefault('domain', {}).update(res['domain'])
                    if res and 'warning' in res:
                        result['warning'] = res['warning']
                return result

            return base_action_rule_onchange

        patched_models = defaultdict(set)
        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                model._patch_method(name, method)

        # retrieve all actions, and patch their corresponding model
        ids = self.search(cr, SUPERUSER_ID, [])
        for action_rule in self.browse(cr, SUPERUSER_ID, ids):
            model = action_rule.model_id.model
            model_obj = self.pool.get(model)
            if not model_obj:
                continue

            if action_rule.kind == 'on_create':
                patch(model_obj, 'create', make_create())

            elif action_rule.kind == 'on_create_or_write':
                patch(model_obj, 'create', make_create())
                patch(model_obj, '_write', make_write())

            elif action_rule.kind == 'on_write':
                patch(model_obj, '_write', make_write())

            elif action_rule.kind == 'on_unlink':
                patch(model_obj, 'unlink', make_unlink())

            elif action_rule.kind == 'on_change':
                # register an onchange method for the action_rule
                method = make_onchange(action_rule.id)
                for field_name in action_rule.on_change_fields.split(","):
                    field_name = field_name.strip()
                    model_obj._onchange_methods[field_name].append(method)

    def _update_cron(self, cr, uid, context=None):
        """ Activate the cron job depending on whether there exists action rules
        based on time conditions. """
        try:
            cron = self.pool['ir.model.data'].get_object(
                cr, uid, 'base_action_rule', 'ir_cron_crm_action', context=context)
        except ValueError:
            return False

        return cron.toggle(model=self._name, domain=[('kind', '=', 'on_time')])

    def _update_registry(self, cr, uid, context=None):
        """ Update the registry after a modification on action rules. """
        if self.pool.ready:
            # for the sake of simplicity, simply force the registry to reload
            cr.commit()
            openerp.api.Environment.reset()
            RegistryManager.new(cr.dbname)
            RegistryManager.signal_registry_change(cr.dbname)

    def create(self, cr, uid, vals, context=None):
        res_id = super(base_action_rule, self).create(cr, uid, vals, context=context)
        self._update_cron(cr, uid, context=context)
        self._update_registry(cr, uid, context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        super(base_action_rule, self).write(cr, uid, ids, vals, context=context)
        if set(vals) & set(self.CRITICAL_FIELDS):
            self._update_cron(cr, uid, context=context)
            self._update_registry(cr, uid, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        res = super(base_action_rule, self).unlink(cr, uid, ids, context=context)
        self._update_cron(cr, uid, context=context)
        self._update_registry(cr, uid, context=context)
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
            if action.filter_domain is not False:
                domain = eval(action.filter_domain, eval_context)
            elif action.filter_id:
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
