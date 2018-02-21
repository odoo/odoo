# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import time
import traceback
from collections import defaultdict

import dateutil
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hour': lambda interval: relativedelta(hours=interval),
    'day': lambda interval: relativedelta(days=interval),
    'month': lambda interval: relativedelta(months=interval),
    False: lambda interval: relativedelta(0),
}


class BaseActionRule(models.Model):
    """ Base Action Rules """

    _name = 'base.action.rule'
    _description = 'Action Rules'
    _order = 'sequence'

    name = fields.Char(string='Rule Name', required=True)
    model_id = fields.Many2one('ir.model', string='Related Document Model', required=True, domain=[('transient', '=', False)])
    model = fields.Char(related='model_id.model', readonly=True)
    active = fields.Boolean(default=True, help="When unchecked, the rule is hidden and will not be executed.")
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of rules.")
    kind = fields.Selection([('on_create', 'On Creation'),
                             ('on_write', 'On Update'),
                             ('on_create_or_write', 'On Creation & Update'),
                             ('on_unlink', 'On Deletion'),
                             ('on_change', 'Based on Form Modification'),
                             ('on_time', 'Based on Timed Condition')], string='When to Run', required=True)
    trg_date_id = fields.Many2one('ir.model.fields', string='Trigger Date',
                                  help="""When should the condition be triggered.
                                  If present, will be checked by the scheduler. If empty, will be checked at creation and update.""",
                                  domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]")
    trg_date_range = fields.Integer(string='Delay after trigger date',
                                    help="""Delay after the trigger date.
                                    You can put a negative number if you need a delay before the
                                    trigger date, like sending a reminder 15 minutes before a meeting.""")
    trg_date_range_type = fields.Selection([('minutes', 'Minutes'), ('hour', 'Hours'), ('day', 'Days'), ('month', 'Months')],
                                           string='Delay type', default='day')
    trg_date_calendar_id = fields.Many2one("resource.calendar", string='Use Calendar',
                                            help="When calculating a day-based timed condition, it is possible to use a calendar to compute the date based on working days.")
    act_user_id = fields.Many2one('res.users', string='Set Responsible')
    act_followers = fields.Many2many("res.partner", string="Add Followers")
    server_action_ids = fields.Many2many('ir.actions.server', string='Server Actions', domain="[('model_id', '=', model_id)]",
                                         help="Examples: email reminders, call object service, etc.")
    filter_pre_id = fields.Many2one("ir.filters", string='Before Update Filter', ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
                                    help="If present, this condition must be satisfied before the update of the record.")
    filter_pre_domain = fields.Char(string='Before Update Domain',
                                    help="If present, this condition must be satisfied before the update of the record.")
    filter_id = fields.Many2one("ir.filters", string='Filter', ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
                                help="If present, this condition must be satisfied before executing the action rule.")
    filter_domain = fields.Char(string='Domain', help="If present, this condition must be satisfied before executing the action rule.")
    last_run = fields.Datetime(readonly=True, copy=False)
    on_change_fields = fields.Char(string="On Change Fields Trigger", help="Comma-separated list of field names that triggers the onchange.")

    # which fields have an impact on the registry
    CRITICAL_FIELDS = ['model_id', 'active', 'kind', 'on_change_fields']

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.filter_pre_id = self.filter_id = False

    @api.onchange('kind')
    def onchange_kind(self):
        if self.kind in ['on_create', 'on_create_or_write', 'on_unlink']:
            self.filter_pre_id = self.filter_pre_domain = self.trg_date_id = self.trg_date_range = self.trg_date_range_type = False
        elif self.kind in ['on_write', 'on_create_or_write']:
            self.trg_date_id = self.trg_date_range = self.trg_date_range_type = False
        elif self.kind == 'on_time':
            self.filter_pre_id = self.filter_pre_domain = False

    @api.onchange('filter_pre_id')
    def onchange_filter_pre_id(self):
        self.filter_pre_domain = self.filter_pre_id.domain

    @api.onchange('filter_id')
    def onchange_filter_id(self):
        self.filter_domain = self.filter_id.domain

    @api.model
    def create(self, vals):
        base_action_rule = super(BaseActionRule, self).create(vals)
        self._update_cron()
        self._update_registry()
        return base_action_rule

    @api.multi
    def write(self, vals):
        res = super(BaseActionRule, self).write(vals)
        if set(vals).intersection(self.CRITICAL_FIELDS):
            self._update_cron()
            self._update_registry()
        return res

    @api.multi
    def unlink(self):
        res = super(BaseActionRule, self).unlink()
        self._update_cron()
        self._update_registry()
        return res

    def _update_cron(self):
        """ Activate the cron job depending on whether there exists action rules
            based on time conditions.
        """
        cron = self.env.ref('base_action_rule.ir_cron_crm_action', raise_if_not_found=False)
        return cron and cron.toggle(model=self._name, domain=[('kind', '=', 'on_time')])

    def _update_registry(self):
        """ Update the registry after a modification on action rules. """
        if self.env.registry.ready and not self.env.context.get('import_file'):
            # for the sake of simplicity, simply force the registry to reload
            self._cr.commit()
            self.env.reset()
            registry = Registry.new(self._cr.dbname)
            registry.signal_registry_change()

    def _get_actions(self, records, kinds):
        """ Return the actions of the given kinds for records' model. The
            returned actions' context contain an object to manage processing.
        """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [('model', '=', records._name), ('kind', 'in', kinds)]
        actions = self.with_context(active_test=True).search(domain)
        return actions.with_env(self.env)

    def _get_eval_context(self):
        """ Prepare the context used when evaluating python code
            :returns: dict -- evaluation context given to safe_eval
        """
        return {
            'datetime': datetime,
            'dateutil': dateutil,
            'time': time,
            'uid': self.env.uid,
            'user': self.env.user,
        }

    def _filter_pre(self, records):
        """ Filter the records that satisfy the precondition of action ``self``. """
        if self.filter_pre_id and records:
            domain = [('id', 'in', records.ids)] + safe_eval(self.filter_pre_id.domain, self._get_eval_context())
            ctx = safe_eval(self.filter_pre_id.context)
            return records.with_context(**ctx).search(domain).with_env(records.env)
        elif self.filter_pre_domain and records:
            domain = [('id', 'in', records.ids)] + safe_eval(self.filter_pre_domain, self._get_eval_context())
            return records.search(domain)
        else:
            return records

    def _filter_post(self, records):
        """ Filter the records that satisfy the postcondition of action ``self``. """
        if self.filter_id and records:
            domain = [('id', 'in', records.ids)] + safe_eval(self.filter_id.domain, self._get_eval_context())
            ctx = safe_eval(self.filter_id.context)
            return records.with_context(**ctx).search(domain).with_env(records.env)
        elif self.filter_domain and records:
            domain = [('id', 'in', records.ids)] + safe_eval(self.filter_domain, self._get_eval_context())
            return records.search(domain)
        else:
            return records

    def _process(self, records):
        """ Process action ``self`` on the ``records`` that have not been done yet. """
        # filter out the records on which self has already been done
        action_done = self._context['__action_done']
        records_done = action_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        # mark the remaining records as done (to avoid recursive processing)
        action_done = dict(action_done)
        action_done[self] = records_done + records
        self = self.with_context(__action_done=action_done)
        records = records.with_context(__action_done=action_done)

        # modify records
        values = {}
        if 'date_action_last' in records._fields:
            values['date_action_last'] = fields.Datetime.now()
        if self.act_user_id and 'user_id' in records._fields:
            values['user_id'] = self.act_user_id.id
        if values:
            records.write(values)

        # subscribe followers
        if self.act_followers and hasattr(records, 'message_subscribe'):
            followers = self.env['mail.followers'].sudo().search(
                [('res_model', '=', records._name),
                 ('res_id', 'in', records.ids),
                 ('partner_id', 'in', self.act_followers.ids),
                 ]
            )
            if not len(followers) == len(self.act_followers):
                records.message_subscribe(self.act_followers.ids)

        # execute server actions
        if self.server_action_ids:
            for record in records:
                ctx = {'active_model': record._name, 'active_ids': record.ids, 'active_id': record.id}
                self.server_action_ids.with_context(**ctx).run()

    @api.model_cr
    def _register_hook(self):
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
            @api.model
            def create(self, vals, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['base.action.rule']._get_actions(self, ['on_create', 'on_create_or_write'])
                # call original method
                record = create.origin(self.with_env(actions.env), vals, **kw)
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
            @api.multi
            def _write(self, vals, **kw):
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
                _write.origin(records, vals, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    action._process(action._filter_post(pre[action]))
                return True

            return _write

        def make_unlink():
            """ Instanciate an unlink method that processes action rules. """
            @api.multi
            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                actions = self.env['base.action.rule']._get_actions(self, ['on_unlink'])
                records = self.with_env(actions.env)
                # check conditions, and execute actions on the records that satisfy them
                for action in actions:
                    action._process(action._filter_post(records))
                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(action_rule_id):
            """ Instanciate an onchange method for the given action rule. """
            def base_action_rule_onchange(self):
                action_rule = self.env['base.action.rule'].browse(action_rule_id)
                result = {}
                for server_action in action_rule.server_action_ids.with_context(active_model=self._name, onchange_self=self):
                    res = server_action.run()
                    if res:
                        if 'value' in res:
                            res['value'].pop('id', None)
                            self.update({key: val for key, val in res['value'].iteritems() if key in self._fields})
                        if 'domain' in res:
                            result.setdefault('domain', {}).update(res['domain'])
                        if 'warning' in res:
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
        for action_rule in self.with_context({}).search([]):
            Model = self.env.get(action_rule.model)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning("Action rule with ID %d depends on model %s" %
                                (action_rule.id,
                                 action_rule.model))
                continue

            if action_rule.kind == 'on_create':
                patch(Model, 'create', make_create())

            elif action_rule.kind == 'on_create_or_write':
                patch(Model, 'create', make_create())
                patch(Model, '_write', make_write())

            elif action_rule.kind == 'on_write':
                patch(Model, '_write', make_write())

            elif action_rule.kind == 'on_unlink':
                patch(Model, 'unlink', make_unlink())

            elif action_rule.kind == 'on_change':
                # register an onchange method for the action_rule
                method = make_onchange(action_rule.id)
                for field_name in action_rule.on_change_fields.split(","):
                    Model._onchange_methods[field_name.strip()].append(method)

    @api.model
    def _check_delay(self, action, record, record_dt):
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day':
            return action.trg_date_calendar_id.schedule_days_get_date(
                action.trg_date_range,
                day_date=fields.Datetime.from_string(record_dt),
                compute_leaves=True,
            )[0]
        else:
            delay = DATE_RANGE_FUNCTION[action.trg_date_range_type](action.trg_date_range)
            return fields.Datetime.from_string(record_dt) + delay

    @api.model
    def _check(self, automatic=False, use_new_cursor=False):
        """ This Function is called by scheduler. """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})

        # retrieve all the action rules to run based on a timed condition
        eval_context = self._get_eval_context()
        for action in self.with_context(active_test=True).search([('kind', '=', 'on_time')]):
            last_run = fields.Datetime.from_string(action.last_run) or datetime.datetime.utcfromtimestamp(0)

            # retrieve all the records that satisfy the action's condition
            domain = []
            context = dict(self._context)
            if action.filter_domain:
                domain = safe_eval(action.filter_domain, eval_context)
            elif action.filter_id:
                domain = safe_eval(action.filter_id.domain, eval_context)
                context.update(safe_eval(action.filter_id.context))
                if 'lang' not in context:
                    # Filters might be language-sensitive, attempt to reuse creator lang
                    # as we are usually running this as super-user in background
                    filter_meta = action.filter_id.get_metadata()[0]
                    user_id = (filter_meta['write_uid'] or filter_meta['create_uid'])[0]
                    context['lang'] = self.env['res.users'].browse(user_id).lang
            records = self.env[action.model].with_context(context).search(domain)

            # determine when action should occur for the records
            if action.trg_date_id.name == 'date_action_last' and 'create_date' in records._fields:
                get_record_dt = lambda record: record[action.trg_date_id.name] or record.create_date
            else:
                get_record_dt = lambda record: record[action.trg_date_id.name]

            # process action on the records that should be executed
            now = datetime.datetime.now()
            for record in records:
                record_dt = get_record_dt(record)
                if not record_dt:
                    continue
                action_dt = self._check_delay(action, record, record_dt)
                if last_run <= action_dt < now:
                    try:
                        action._process(record)
                    except Exception:
                        _logger.error(traceback.format_exc())

            action.write({'last_run': fields.Datetime.now()})

            if automatic:
                # auto-commit for batch processing
                self._cr.commit()
