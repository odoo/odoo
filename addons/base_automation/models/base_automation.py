# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import traceback
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: relativedelta(minutes=interval),
    'hour': lambda interval: relativedelta(hours=interval),
    'day': lambda interval: relativedelta(days=interval),
    'month': lambda interval: relativedelta(months=interval),
    False: lambda interval: relativedelta(0),
}

DATE_RANGE_FACTOR = {
    'minutes': 1,
    'hour': 60,
    'day': 24 * 60,
    'month': 30 * 24 * 60,
    False: 0,
}


class BaseAutomation(models.Model):
    _name = 'base.automation'
    _description = 'Automated Action'
    _order = 'sequence'

    action_server_id = fields.Many2one(
        'ir.actions.server', 'Server Actions',
        domain="[('model_id', '=', model_id)]",
        delegate=True, required=True, ondelete='restrict')
    active = fields.Boolean(default=True, help="When unchecked, the rule is hidden and will not be executed.")
    trigger = fields.Selection([
        ('on_create', 'On Creation'),
        ('on_write', 'On Update'),
        ('on_create_or_write', 'On Creation & Update'),
        ('on_unlink', 'On Deletion'),
        ('on_change', 'Based on Form Modification'),
        ('on_time', 'Based on Timed Condition')
        ], string='Trigger', required=True)
    trg_date_id = fields.Many2one('ir.model.fields', string='Trigger Date',
                                  help="""When should the condition be triggered.
                                  If present, will be checked by the scheduler. If empty, will be checked at creation and update.""",
                                  domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]")
    trg_date_range = fields.Integer(string='Delay after trigger date',
                                    help="""Delay after the trigger date.
                                    You can put a negative number if you need a delay before the
                                    trigger date, like sending a reminder 15 minutes before a meeting.""")
    trg_date_range_type = fields.Selection([('minutes', 'Minutes'), ('hour', 'Hours'), ('day', 'Days'), ('month', 'Months')],
                                           string='Delay type', default='hour')
    trg_date_calendar_id = fields.Many2one("resource.calendar", string='Use Calendar',
                                            help="When calculating a day-based timed condition, it is possible to use a calendar to compute the date based on working days.")
    filter_pre_domain = fields.Char(string='Before Update Domain',
                                    help="If present, this condition must be satisfied before the update of the record.")
    filter_domain = fields.Char(string='Apply on', help="If present, this condition must be satisfied before executing the action rule.")
    last_run = fields.Datetime(readonly=True, copy=False)
    on_change_field_ids = fields.Many2many(
        "ir.model.fields",
        relation="base_automation_onchange_fields_rel",
        string="On Change Fields Trigger",
        help="Fields that trigger the onchange.",
    )
    trigger_field_ids = fields.Many2many('ir.model.fields', string='Trigger Fields',
                                        help="The action will be triggered if and only if one of these fields is updated."
                                             "If empty, all fields are watched.")
    least_delay_msg = fields.Char(compute='_compute_least_delay_msg')

    # which fields have an impact on the registry and the cron
    CRITICAL_FIELDS = ['model_id', 'active', 'trigger', 'on_change_field_ids']
    RANGE_FIELDS = ['trg_date_range', 'trg_date_range_type']

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.model_name = self.model_id.model

    @api.onchange('trigger')
    def onchange_trigger(self):
        if self.trigger in ['on_create', 'on_create_or_write', 'on_unlink']:
            self.filter_pre_domain = self.trg_date_id = self.trg_date_range = self.trg_date_range_type = False
        elif self.trigger in ['on_write', 'on_create_or_write']:
            self.trg_date_id = self.trg_date_range = self.trg_date_range_type = False
        elif self.trigger == 'on_time':
            self.filter_pre_domain = False
            self.trg_date_range_type = 'hour'

    @api.onchange('trigger', 'state')
    def _onchange_state(self):
        if self.trigger == 'on_change' and self.state != 'code':
            ff = self.fields_get(['trigger', 'state'])
            return {'warning': {
                'title': _("Warning"),
                'message': _("The \"%(trigger_value)s\" %(trigger_label)s can only be used with the \"%(state_value)s\" action type") % {
                    'trigger_value': dict(ff['trigger']['selection'])['on_change'],
                    'trigger_label': ff['trigger']['string'],
                    'state_value': dict(ff['state']['selection'])['code'],
                }
            }}

        MAIL_STATES = ('email', 'followers', 'next_activity')
        if self.trigger == 'on_unlink' and self.state in MAIL_STATES:
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "You cannot send an email, add followers or create an activity "
                    "for a deleted record.  It simply does not work."
                ),
            }}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['usage'] = 'base_automation'
        base_automations = super(BaseAutomation, self).create(vals_list)
        self._update_cron()
        self._update_registry()
        return base_automations

    def write(self, vals):
        res = super(BaseAutomation, self).write(vals)
        if set(vals).intersection(self.CRITICAL_FIELDS):
            self._update_cron()
            self._update_registry()
        elif set(vals).intersection(self.RANGE_FIELDS):
            self._update_cron()
        return res

    def unlink(self):
        res = super(BaseAutomation, self).unlink()
        self._update_cron()
        self._update_registry()
        return res

    def _update_cron(self):
        """ Activate the cron job depending on whether there exists action rules
            based on time conditions.  Also update its frequency according to
            the smallest action delay, or restore the default 4 hours if there
            is no time based action.
        """
        cron = self.env.ref('base_automation.ir_cron_data_base_automation_check', raise_if_not_found=False)
        if cron:
            actions = self.with_context(active_test=True).search([('trigger', '=', 'on_time')])
            cron.try_write({
                'active': bool(actions),
                'interval_type': 'minutes',
                'interval_number': self._get_cron_interval(actions),
            })

    def _update_registry(self):
        """ Update the registry after a modification on action rules. """
        if self.env.registry.ready and not self.env.context.get('import_file'):
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _get_actions(self, records, triggers):
        """ Return the actions of the given triggers for records' model. The
            returned actions' context contain an object to manage processing.
        """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [('model_name', '=', records._name), ('trigger', 'in', triggers)]
        actions = self.with_context(active_test=True).sudo().search(domain)
        return actions.with_env(self.env)

    def _get_eval_context(self):
        """ Prepare the context used when evaluating python code
            :returns: dict -- evaluation context given to safe_eval
        """
        return {
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'time': safe_eval.time,
            'uid': self.env.uid,
            'user': self.env.user,
        }

    def _get_cron_interval(self, actions=None):
        """ Return the expected time interval used by the cron, in minutes. """
        def get_delay(rec):
            return rec.trg_date_range * DATE_RANGE_FACTOR[rec.trg_date_range_type]

        if actions is None:
            actions = self.with_context(active_test=True).search([('trigger', '=', 'on_time')])

        # Minimum 1 minute, maximum 4 hours, 10% tolerance
        delay = min(actions.mapped(get_delay), default=0)
        return min(max(1, delay // 10), 4 * 60) if delay else 4 * 60

    def _compute_least_delay_msg(self):
        msg = _("Note that this action can be trigged up to %d minutes after its schedule.")
        self.least_delay_msg = msg % self._get_cron_interval()

    def _filter_pre(self, records):
        """ Filter the records that satisfy the precondition of action ``self``. """
        self_sudo = self.sudo()
        if self_sudo.filter_pre_domain and records:
            domain = safe_eval.safe_eval(self_sudo.filter_pre_domain, self._get_eval_context())
            return records.sudo().filtered_domain(domain).with_env(records.env)
        else:
            return records

    def _filter_post(self, records):
        return self._filter_post_export_domain(records)[0]

    def _filter_post_export_domain(self, records):
        """ Filter the records that satisfy the postcondition of action ``self``. """
        self_sudo = self.sudo()
        if self_sudo.filter_domain and records:
            domain = safe_eval.safe_eval(self_sudo.filter_domain, self._get_eval_context())
            return records.sudo().filtered_domain(domain).with_env(records.env), domain
        else:
            return records, None

    @api.model
    def _add_postmortem_action(self, e):
        if self.user_has_groups('base.group_user'):
            e.context = {}
            e.context['exception_class'] = 'base_automation'
            e.context['base_automation'] = {
                'id': self.id,
                'name': self.sudo().name,
            }

    def _process(self, records, domain_post=None):
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
        if values:
            records.write(values)

        # execute server actions
        action_server = self.action_server_id
        if action_server:
            for record in records:
                # we process the action if any watched field has been modified
                if self._check_trigger_fields(record):
                    ctx = {
                        'active_model': record._name,
                        'active_ids': record.ids,
                        'active_id': record.id,
                        'domain_post': domain_post,
                    }
                    try:
                        action_server.sudo().with_context(**ctx).run()
                    except Exception as e:
                        self._add_postmortem_action(e)
                        raise e

    def _check_trigger_fields(self, record):
        """ Return whether any of the trigger fields has been modified on ``record``. """
        self_sudo = self.sudo()
        if not self_sudo.trigger_field_ids:
            # all fields are implicit triggers
            return True

        if not self._context.get('old_values'):
            # this is a create: all fields are considered modified
            return True

        # Note: old_vals are in the format of read()
        old_vals = self._context['old_values'].get(record.id, {})

        def differ(name):
            field = record._fields[name]
            return (
                name in old_vals and
                field.convert_to_cache(record[name], record, validate=False) !=
                field.convert_to_cache(old_vals[name], record, validate=False)
            )
        return any(differ(field.name) for field in self_sudo.trigger_field_ids)

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
            @api.model_create_multi
            def create(self, vals_list, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation']._get_actions(self, ['on_create', 'on_create_or_write'])
                if not actions:
                    return create.origin(self, vals_list, **kw)
                # call original method
                records = create.origin(self.with_env(actions.env), vals_list, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=None):
                    action._process(action._filter_post(records))
                return records.with_env(self.env)

            return create

        def make_write():
            """ Instanciate a write method that processes action rules. """
            def write(self, vals, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation']._get_actions(self, ['on_write', 'on_create_or_write'])
                if not (actions and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(actions.env).filtered('id')
                # check preconditions on records
                pre = {action: action._filter_pre(records) for action in actions}
                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read(list(vals)) if vals else [])
                }
                # call original method
                write.origin(self.with_env(actions.env), vals, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    records, domain_post = action._filter_post_export_domain(pre[action])
                    action._process(records, domain_post=domain_post)
                return True

            return write

        def make_compute_field_value():
            """ Instanciate a compute_field_value method that processes action rules. """
            #
            # Note: This is to catch updates made by field recomputations.
            #
            def _compute_field_value(self, field):
                # determine fields that may trigger an action
                stored_fields = [f for f in self.pool.field_computed[field] if f.store]
                if not any(stored_fields):
                    return _compute_field_value.origin(self, field)
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation']._get_actions(self, ['on_write', 'on_create_or_write'])
                records = self.filtered('id').with_env(actions.env)
                if not (actions and records):
                    _compute_field_value.origin(self, field)
                    return True
                # check preconditions on records
                pre = {action: action._filter_pre(records) for action in actions}
                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read([f.name for f in stored_fields]))
                }
                # call original method
                _compute_field_value.origin(self, field)
                # check postconditions, and execute actions on the records that satisfy them
                for action in actions.with_context(old_values=old_values):
                    records, domain_post = action._filter_post_export_domain(pre[action])
                    action._process(records, domain_post=domain_post)
                return True

            return _compute_field_value

        def make_unlink():
            """ Instanciate an unlink method that processes action rules. """
            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                actions = self.env['base.automation']._get_actions(self, ['on_unlink'])
                records = self.with_env(actions.env)
                # check conditions, and execute actions on the records that satisfy them
                for action in actions:
                    action._process(action._filter_post(records))
                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(action_rule_id):
            """ Instanciate an onchange method for the given action rule. """
            def base_automation_onchange(self):
                action_rule = self.env['base.automation'].browse(action_rule_id)
                result = {}
                server_action = action_rule.sudo().action_server_id.with_context(
                    active_model=self._name,
                    active_id=self._origin.id,
                    active_ids=self._origin.ids,
                    onchange_self=self,
                )
                try:
                    res = server_action.run()
                except Exception as e:
                    action_rule._add_postmortem_action(e)
                    raise e

                if res:
                    if 'value' in res:
                        res['value'].pop('id', None)
                        self.update({key: val for key, val in res['value'].items() if key in self._fields})
                    if 'domain' in res:
                        result.setdefault('domain', {}).update(res['domain'])
                    if 'warning' in res:
                        result['warning'] = res['warning']
                return result

            return base_automation_onchange

        patched_models = defaultdict(set)
        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                origin = getattr(ModelClass, name)
                method.origin = origin
                wrapped = api.propagate(origin, method)
                wrapped.origin = origin
                setattr(ModelClass, name, wrapped)

        # retrieve all actions, and patch their corresponding model
        for action_rule in self.with_context({}).search([]):
            Model = self.env.get(action_rule.model_name)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning("Action rule with ID %d depends on model %s" %
                                (action_rule.id,
                                 action_rule.model_name))
                continue

            if action_rule.trigger == 'on_create':
                patch(Model, 'create', make_create())

            elif action_rule.trigger == 'on_create_or_write':
                patch(Model, 'create', make_create())
                patch(Model, 'write', make_write())
                patch(Model, '_compute_field_value', make_compute_field_value())

            elif action_rule.trigger == 'on_write':
                patch(Model, 'write', make_write())
                patch(Model, '_compute_field_value', make_compute_field_value())

            elif action_rule.trigger == 'on_unlink':
                patch(Model, 'unlink', make_unlink())

            elif action_rule.trigger == 'on_change':
                # register an onchange method for the action_rule
                method = make_onchange(action_rule.id)
                for field in action_rule.on_change_field_ids:
                    Model._onchange_methods[field.name].append(method)

    def _unregister_hook(self):
        """ Remove the patches installed by _register_hook() """
        NAMES = ['create', 'write', '_compute_field_value', 'unlink', '_onchange_methods']
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass

    @api.model
    def _check_delay(self, action, record, record_dt):
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day':
            return action.trg_date_calendar_id.plan_days(
                action.trg_date_range,
                fields.Datetime.from_string(record_dt),
                compute_leaves=True,
            )
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
        for action in self.with_context(active_test=True).search([('trigger', '=', 'on_time')]):
            _logger.info("Starting time-based automated action `%s`.", action.name)
            last_run = fields.Datetime.from_string(action.last_run) or datetime.datetime.utcfromtimestamp(0)

            # retrieve all the records that satisfy the action's condition
            domain = []
            context = dict(self._context)
            if action.filter_domain:
                domain = safe_eval.safe_eval(action.filter_domain, eval_context)
            records = self.env[action.model_name].with_context(context).search(domain)

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

            action.write({'last_run': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            _logger.info("Time-based automated action `%s` done.", action.name)

            if automatic:
                # auto-commit for batch processing
                self._cr.commit()
