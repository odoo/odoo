# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import traceback
from collections import defaultdict
from uuid import uuid4

from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, safe_eval
from odoo.http import request

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

CREATE_TRIGGERS = [
    'on_create',

    'on_create_or_write',
    'on_priority_set',
    'on_stage_set',
    'on_state_set',
    'on_tag_set',
    'on_user_set',
]

WRITE_TRIGGERS = [
    'on_write',
    'on_archive',
    'on_unarchive',

    'on_create_or_write',
    'on_priority_set',
    'on_stage_set',
    'on_state_set',
    'on_tag_set',
    'on_user_set',
]

MAIL_TRIGGERS = ("on_message_received", "on_message_sent")

CREATE_WRITE_SET = set(CREATE_TRIGGERS + WRITE_TRIGGERS)

TIME_TRIGGERS = [
    'on_time',
    'on_time_created',
    'on_time_updated',
]

def get_webhook_request_payload():
    if not request:
        return None
    try:
        payload = request.get_json_data()
    except ValueError:
        payload = {**request.httprequest.args}
    return payload


class BaseAutomation(models.Model):
    _name = 'base.automation'
    _description = 'Automation Rule'

    name = fields.Char(string="Automation Rule Name", required=True, translate=True)
    description = fields.Html(string="Description")
    model_id = fields.Many2one(
        "ir.model", string="Model", domain=[("field_id", "!=", False)], required=True, ondelete="cascade",
        help="Model on which the automation rule runs."
    )
    model_name = fields.Char(related="model_id.model", string="Model Name", readonly=True, inverse="_inverse_model_name")
    model_is_mail_thread = fields.Boolean(related="model_id.is_mail_thread")
    action_server_ids = fields.One2many("ir.actions.server", "base_automation_id",
        context={'default_usage': 'base_automation'},
        string="Actions",
        compute="_compute_action_server_ids",
        store=True,
        readonly=False,
    )
    url = fields.Char(compute='_compute_url')
    webhook_uuid = fields.Char(string="Webhook UUID", readonly=True, copy=False, default=lambda self: str(uuid4()))
    record_getter = fields.Char(default="model.env[payload.get('_model')].browse(int(payload.get('_id')))",
                                help="This code will be run to find on which record the automation rule should be run.")
    log_webhook_calls = fields.Boolean(string="Log Calls", default=False)
    active = fields.Boolean(default=True, help="When unchecked, the rule is hidden and will not be executed.")

    @api.constrains("trigger", "model_id")
    def _check_trigger(self):
        for automation in self:
            if automation.trigger in MAIL_TRIGGERS and not automation.model_id.is_mail_thread:
                raise exceptions.ValidationError(_("Mail event can not be configured on model %s. Only models with discussion feature can be used.", automation.model_id.name))

    trigger = fields.Selection(
        [
            ('on_stage_set', "Stage is set to"),
            ('on_user_set', "User is set"),
            ('on_tag_set', "Tag is added"),
            ('on_state_set', "State is set to"),
            ('on_priority_set', "Priority is set to"),
            ('on_archive', "On archived"),
            ('on_unarchive', "On unarchived"),
            ('on_create_or_write', "On save"),
            ('on_create', "On creation"),  # deprecated, use 'on_create_or_write' instead
            ('on_write', "On update"),  # deprecated, use 'on_create_or_write' instead

            ('on_unlink', "On deletion"),
            ('on_change', "On UI change"),

            ('on_time', "Based on date field"),
            ('on_time_created', "After creation"),
            ('on_time_updated', "After last update"),

            ("on_message_received", "On incoming message"),
            ("on_message_sent", "On outgoing message"),

            ('on_webhook', "On webhook"),
        ], string='Trigger',
        compute='_compute_trigger_and_trigger_field_ids', readonly=False, store=True, required=True)
    trg_selection_field_id = fields.Many2one(
        'ir.model.fields.selection',
        string='Trigger Field',
        domain="[('field_id', 'in', trigger_field_ids)]",
        compute='_compute_trg_selection_field_id',
        readonly=False, store=True,
        help="Some triggers need a reference to a selection field. This field is used to store it.")
    trg_field_ref_model_name = fields.Char(
        string='Trigger Field Model',
        compute='_compute_trg_field_ref__model_and_display_names')
    trg_field_ref = fields.Many2oneReference(
        model_field='trg_field_ref_model_name',
        compute='_compute_trg_field_ref',
        string='Trigger Reference',
        readonly=False,
        store=True,
        help="Some triggers need a reference to another field. This field is used to store it.")
    trg_field_ref_display_name = fields.Char(
        string='Trigger Reference Display Name',
        compute='_compute_trg_field_ref__model_and_display_names')
    trg_date_id = fields.Many2one(
        'ir.model.fields', string='Trigger Date',
        compute='_compute_trg_date_id',
        readonly=False, store=True,
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]",
        help="""When should the condition be triggered.
                If present, will be checked by the scheduler. If empty, will be checked at creation and update.""")
    trg_date_range = fields.Integer(
        string='Delay after trigger date',
        compute='_compute_trg_date_range_data',
        readonly=False, store=True,
        help="Delay after the trigger date. "
        "You can put a negative number if you need a delay before the "
        "trigger date, like sending a reminder 15 minutes before a meeting.")
    trg_date_range_type = fields.Selection(
        [('minutes', 'Minutes'), ('hour', 'Hours'), ('day', 'Days'), ('month', 'Months')],
        string='Delay type',
        compute='_compute_trg_date_range_data',
        readonly=False, store=True)
    trg_date_calendar_id = fields.Many2one(
        "resource.calendar", string='Use Calendar',
        compute='_compute_trg_date_calendar_id',
        readonly=False, store=True,
        help="When calculating a day-based timed condition, it is possible"
             "to use a calendar to compute the date based on working days.")
    filter_pre_domain = fields.Char(
        string='Before Update Domain',
        compute='_compute_filter_pre_domain',
        readonly=False, store=True,
        help="If present, this condition must be satisfied before the update of the record.")
    filter_domain = fields.Char(
        string='Apply on',
        help="If present, this condition must be satisfied before executing the automation rule.",
        compute='_compute_filter_domain',
        readonly=False, store=True
    )
    last_run = fields.Datetime(readonly=True, copy=False)
    on_change_field_ids = fields.Many2many(
        "ir.model.fields",
        relation="base_automation_onchange_fields_rel",
        compute='_compute_on_change_field_ids',
        readonly=False, store=True,
        string="On Change Fields Trigger",
        help="Fields that trigger the onchange.",
    )
    trigger_field_ids = fields.Many2many(
        'ir.model.fields', string='Trigger Fields',
        compute='_compute_trigger_and_trigger_field_ids', readonly=False, store=True,
        help="The automation rule will be triggered if and only if one of these fields is updated."
             "If empty, all fields are watched.")
    least_delay_msg = fields.Char(compute='_compute_least_delay_msg')

    # which fields have an impact on the registry and the cron
    CRITICAL_FIELDS = ['model_id', 'active', 'trigger', 'on_change_field_ids']
    RANGE_FIELDS = ['trg_date_range', 'trg_date_range_type']

    @api.constrains('model_id', 'action_server_ids')
    def _check_action_server_model(self):
        for rule in self:
            failing_actions = rule.action_server_ids.filtered(
                lambda action: action.model_id != rule.model_id
            )
            if failing_actions:
                raise exceptions.ValidationError(
                    _('Target model of actions %(action_names)s are different from rule model.',
                      action_names=', '.join(failing_actions.mapped('name'))
                     )
                )
    @api.depends("trigger", "webhook_uuid")
    def _compute_url(self):
        for automation in self:
            if automation.trigger != "on_webhook":
                automation.url = ""
            else:
                automation.url = "%s/web/hook/%s" % (automation.get_base_url(), automation.webhook_uuid)

    def _inverse_model_name(self):
        for rec in self:
            rec.model_id = self.env["ir.model"]._get(rec.model_name)

    @api.constrains('trigger', 'action_server_ids')
    def _check_trigger_state(self):
        for record in self:
            no_code_actions = record.action_server_ids.filtered(lambda a: a.state != 'code')
            if record.trigger == 'on_change' and no_code_actions:
                raise exceptions.ValidationError(
                    _('"On live update" automation rules can only be used with "Execute Python Code" action type.')
                )
            mail_actions = record.action_server_ids.filtered(
                lambda a: a.state in ['mail_post', 'followers', 'next_activity']
            )
            if record.trigger == 'on_unlink' and mail_actions:
                raise exceptions.ValidationError(
                    _('Email, follower or activity action types cannot be used when deleting records, '
                      'as there are no more records to apply these changes to!')
                )

    @api.depends('model_id')
    def _compute_action_server_ids(self):
        """ When changing / setting model, remove actions that are not targeting
        the same model anymore. """
        for rule in self.filtered('model_id'):
            actions_to_remove = rule.action_server_ids.filtered(
                lambda action: action.model_id != rule.model_id
            )
            if actions_to_remove:
                rule.action_server_ids = [(3, action.id) for action in actions_to_remove]

    @api.depends('trigger', 'trigger_field_ids')
    def _compute_trg_date_id(self):
        to_reset = self.filtered(lambda a: a.trigger not in TIME_TRIGGERS or len(a.trigger_field_ids) != 1)
        to_reset.trg_date_id = False
        for record in (self - to_reset):
            record.trg_date_id = record.trigger_field_ids

    @api.depends('trigger')
    def _compute_trg_date_range_data(self):
        to_reset = self.filtered(lambda a: a.trigger not in TIME_TRIGGERS)
        to_reset.trg_date_range = False
        to_reset.trg_date_range_type = False
        (self - to_reset).filtered(lambda a: not a.trg_date_range_type).trg_date_range_type = 'hour'

    @api.depends('trigger', 'trg_date_id', 'trg_date_range_type')
    def _compute_trg_date_calendar_id(self):
        to_reset = self.filtered(
            lambda a: a.trigger not in TIME_TRIGGERS or not a.trg_date_id or a.trg_date_range_type != 'day'
        )
        to_reset.trg_date_calendar_id = False

    @api.depends('trigger', 'trigger_field_ids')
    def _compute_trg_selection_field_id(self):
        to_reset = self.filtered(lambda a: a.trigger not in ['on_priority_set', 'on_state_set'] or len(a.trigger_field_ids) != 1)
        to_reset.trg_selection_field_id = False
        for automation in (self - to_reset):
            # always re-assign to an empty value to make sure we have no discrepencies
            automation.trg_selection_field_id = self.env['ir.model.fields.selection']

    @api.depends('trigger', 'trigger_field_ids')
    def _compute_trg_field_ref(self):
        to_reset = self.filtered(lambda a: a.trigger not in ['on_stage_set', 'on_tag_set'] or len(a.trigger_field_ids) != 1)
        to_reset.trg_field_ref = False
        for automation in (self - to_reset):
            relation = automation.trigger_field_ids.relation
            automation.trg_field_ref_model_name = relation
            # always re-assign to an empty value to make sure we have no discrepencies
            automation.trg_field_ref = self.env[relation]

    @api.depends('trg_field_ref', 'trigger_field_ids')
    def _compute_trg_field_ref__model_and_display_names(self):
        to_compute = self.filtered(lambda a: a.trigger in ['on_stage_set', 'on_tag_set'] and a.trg_field_ref is not False)
        # wondering why we check based on 'is not'? Because the ref could be an empty recordset
        # and we still need to introspec on the model in that case - not just ignore it
        to_reset = (self - to_compute)
        to_reset.trg_field_ref_model_name = False
        to_reset.trg_field_ref_display_name = False
        for automation in to_compute:
            relation = automation.trigger_field_ids.relation
            if not relation:
                automation.trg_field_ref_model_name = False
                automation.trg_field_ref_display_name = False
                continue
            resid = automation.trg_field_ref
            automation.trg_field_ref_model_name = relation
            automation.trg_field_ref_display_name = self.env[relation].browse(resid).display_name

    @api.depends('trigger', 'trigger_field_ids', 'trg_field_ref')
    def _compute_filter_pre_domain(self):
        to_reset = self.filtered(lambda a: a.trigger != 'on_tag_set' or len(a.trigger_field_ids) != 1)
        to_reset.filter_pre_domain = False
        for automation in (self - to_reset):
            field = automation.trigger_field_ids.name
            value = automation.trg_field_ref
            automation.filter_pre_domain = f"[('{field}', 'not in', [{value}])]" if value else False

    @api.depends('trigger', 'trigger_field_ids', 'trg_selection_field_id', 'trg_field_ref')
    def _compute_filter_domain(self):
        for record in self:
            trigger_fields_count = len(record.trigger_field_ids)
            if trigger_fields_count == 0:
                record.filter_domain = False

            elif trigger_fields_count == 1:
                field = record.trigger_field_ids.name
                trigger = record.trigger
                if trigger in ['on_state_set', 'on_priority_set']:
                    value = record.trg_selection_field_id.value
                    record.filter_domain = f"[('{field}', '=', '{value}')]" if value else False
                elif trigger == 'on_stage_set':
                    value = record.trg_field_ref
                    record.filter_domain = f"[('{field}', '=', {value})]" if value else False
                elif trigger == 'on_tag_set':
                    value = record.trg_field_ref
                    record.filter_domain = f"[('{field}', 'in', [{value}])]" if value else False
                elif trigger == 'on_user_set':
                    record.filter_domain = f"[('{field}', '!=', False)]"
                elif trigger in ['on_archive', 'on_unarchive']:
                    record.filter_domain = f"[('{field}', '=', {trigger == 'on_unarchive'})]"
                else:
                    record.filter_domain = False

    @api.depends('model_id', 'trigger')
    def _compute_on_change_field_ids(self):
        to_reset = self.filtered(lambda a: a.trigger != 'on_change')
        to_reset.on_change_field_ids = False
        for record in (self - to_reset).filtered('on_change_field_ids'):
            record.on_change_field_ids = record.on_change_field_ids.filtered(lambda field: field.model_id == record.model_id)

    @api.depends('model_id', 'trigger')
    def _compute_trigger_and_trigger_field_ids(self):
        for automation in self:
            domain = [('model_id', '=', automation.model_id.id)]
            if automation.trigger == 'on_stage_set':
                domain += [('ttype', '=', 'many2one'), ('name', 'in', ['stage_id', 'x_studio_stage_id'])]
            elif automation.trigger == 'on_tag_set':
                domain += [('ttype', '=', 'many2many'), ('name', 'in', ['tag_ids', 'x_studio_tag_ids'])]
            elif automation.trigger == 'on_priority_set':
                domain += [('ttype', '=', 'selection'), ('name', 'in', ['priority', 'x_studio_priority'])]
            elif automation.trigger == 'on_state_set':
                domain += [('ttype', '=', 'selection'), ('name', 'in', ['state', 'x_studio_state'])]
            elif automation.trigger == 'on_user_set':
                domain += [
                    ('relation', '=', 'res.users'),
                    ('ttype', 'in', ['many2one', 'many2many']),
                    ('name', 'in', ['user_id', 'user_ids', 'x_studio_user_id', 'x_studio_user_ids']),
                ]
            elif automation.trigger in ['on_archive', 'on_unarchive']:
                domain += [('ttype', '=', 'boolean'), ('name', 'in', ['active', 'x_active'])]
            elif automation.trigger == 'on_time_created':
                domain += [('ttype', '=', 'datetime'), ('name', '=', 'create_date')]
            elif automation.trigger == 'on_time_updated':
                domain += [('ttype', '=', 'datetime'), ('name', '=', 'write_date')]
            else:
                automation.trigger_field_ids = False
                continue
            if automation.model_id.is_mail_thread and automation.trigger in MAIL_TRIGGERS:
                continue

            automation.trigger_field_ids = self.env['ir.model.fields'].search(domain, limit=1)
            automation.trigger = False if not automation.trigger_field_ids else automation.trigger

    @api.onchange('trigger', 'action_server_ids')
    def _onchange_trigger_or_actions(self):
        no_code_actions = self.action_server_ids.filtered(lambda a: a.state != 'code')
        if self.trigger == 'on_change' and len(no_code_actions) > 0:
            trigger_field = self._fields['trigger']
            action_states = dict(self.action_server_ids._fields['state']._description_selection(self.env))
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "The \"%(trigger_value)s\" %(trigger_label)s can only be "
                    "used with the \"%(state_value)s\" action type",
                    trigger_value=dict(trigger_field._description_selection(self.env))['on_change'],
                    trigger_label=trigger_field._description_string(self.env),
                    state_value=action_states['code'])
            }}

        MAIL_STATES = ('mail_post', 'followers', 'next_activity')
        mail_actions = self.action_server_ids.filtered(lambda a: a.state in MAIL_STATES)
        if self.trigger == 'on_unlink' and len(mail_actions) > 0:
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "You cannot send an email, add followers or create an activity "
                    "for a deleted record.  It simply does not work."
                ),
            }}

    @api.model_create_multi
    def create(self, vals_list):
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

    def copy(self, default=None):
        """Copy the actions of the automation while
        copying the automation itself."""
        actions = self.action_server_ids.copy_multi()
        record_copy = super().copy(default)
        record_copy.action_server_ids = actions
        return record_copy

    def action_rotate_webhook_uuid(self):
        for automation in self:
            automation.webhook_uuid = str(uuid4())

    def action_view_webhook_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Webhook Logs'),
            'res_model': 'ir.logging',
            'view_mode': 'tree,form',
            'domain': [('path', '=', "base_automation(%s)" % self.id)],
        }

    def _prepare_loggin_values(self, **values):
        self.ensure_one()
        defaults = {
            'name': _("Webhook Log"),
            'type': 'server',
            'dbname': self._cr.dbname,
            'level': 'INFO',
            'path': "base_automation(%s)" % self.id,
            'func': '',
            'line': ''
        }
        defaults.update(**values)
        return defaults

    def _execute_webhook(self, payload):
        """ Execute the webhook for the given payload.
        The payload is a dictionnary that can be used by the `record_getter` to
        identify the record on which the automation should be run.
        """
        self.ensure_one()
        ir_logging_sudo = self.env['ir.logging'].sudo()

        # info logging is done by the ir.http logger
        msg = "Webhook #%s triggered with payload %s"
        msg_args = (self.id, payload)
        _logger.debug(msg, *msg_args)
        if self.log_webhook_calls:
            ir_logging_sudo.create(self._prepare_loggin_values(message=msg % msg_args))

        record = self.env[self.model_name]
        if self.record_getter:
            try:
                record = safe_eval.safe_eval(self.record_getter, self._get_eval_context(payload=payload))
            except Exception as e: # noqa: BLE001
                msg = "Webhook #%s could not be triggered because the record_getter failed:\n%s"
                msg_args = (self.id, traceback.format_exc())
                _logger.warning(msg, *msg_args)
                if self.log_webhook_calls:
                    ir_logging_sudo.create(self._prepare_loggin_values(message=msg % msg_args, level="ERROR"))
                raise e

        if not record.exists():
            msg = "Webhook #%s could not be triggered because no record to run it on was found."
            msg_args = (self.id,)
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(self._prepare_loggin_values(message=msg % msg_args, level="ERROR"))
            raise exceptions.ValidationError(_("No record to run the automation on was found."))

        try:
            return self._process(record)
        except Exception as e: # noqa: BLE001
            msg = "Webhook #%s failed with error:\n%s"
            msg_args = (self.id, traceback.format_exc())
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(self._prepare_loggin_values(message=msg % msg_args, level="ERROR"))
            raise e

    def _update_cron(self):
        """ Activate the cron job depending on whether there exists automation rules
        based on time conditions.  Also update its frequency according to
        the smallest automation delay, or restore the default 4 hours if there
        is no time based automation.
        """
        cron = self.env.ref('base_automation.ir_cron_data_base_automation_check', raise_if_not_found=False)
        if cron:
            automations = self.with_context(active_test=True).search([('trigger', 'in', TIME_TRIGGERS)])
            cron.try_write({
                'active': bool(automations),
                'interval_type': 'minutes',
                'interval_number': self._get_cron_interval(automations),
            })

    def _update_registry(self):
        """ Update the registry after a modification on automation rules. """
        if self.env.registry.ready and not self.env.context.get('import_file'):
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _get_actions(self, records, triggers):
        """ Return the automations of the given triggers for records' model. The
            returned automations' context contain an object to manage processing.
        """
        # Note: we keep the old action naming for the method and context variable
        # to avoid breaking existing code/downstream modules
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [('model_name', '=', records._name), ('trigger', 'in', triggers)]
        automations = self.with_context(active_test=True).sudo().search(domain)
        return automations.with_env(self.env)

    def _get_eval_context(self, payload=None):
        """ Prepare the context used when evaluating python code
            :returns: dict -- evaluation context given to safe_eval
        """
        self.ensure_one()
        model = self.env[self.model_name]
        eval_context = {
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'time': safe_eval.time,
            'uid': self.env.uid,
            'user': self.env.user,
            'model': model,
        }
        if payload is not None:
            eval_context['payload'] = payload
        return eval_context

    def _get_cron_interval(self, automations=None):
        """ Return the expected time interval used by the cron, in minutes. """
        def get_delay(rec):
            return rec.trg_date_range * DATE_RANGE_FACTOR[rec.trg_date_range_type]

        if automations is None:
            automations = self.with_context(active_test=True).search([('trigger', 'in', TIME_TRIGGERS)])

        # Minimum 1 minute, maximum 4 hours, 10% tolerance
        delay = min(automations.mapped(get_delay), default=0)
        return min(max(1, delay // 10), 4 * 60) if delay else 4 * 60

    def _compute_least_delay_msg(self):
        msg = _("Note that this automation rule can be triggered up to %d minutes after its schedule.")
        self.least_delay_msg = msg % self._get_cron_interval()

    def _filter_pre(self, records, feedback=False):
        """ Filter the records that satisfy the precondition of automation ``self``. """
        self_sudo = self.sudo()
        if self_sudo.filter_pre_domain and records:
            if feedback:
                # this context flag enables to detect the executions of
                # automations while evaluating their precondition
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(self_sudo.filter_pre_domain, self._get_eval_context())
            return records.sudo().filtered_domain(domain).with_env(records.env)
        else:
            return records

    def _filter_post(self, records, feedback=False):
        return self._filter_post_export_domain(records, feedback)[0]

    def _filter_post_export_domain(self, records, feedback=False):
        """ Filter the records that satisfy the postcondition of automation ``self``. """
        self_sudo = self.sudo()
        if self_sudo.filter_domain and records:
            if feedback:
                # this context flag enables to detect the executions of
                # automations while evaluating their postcondition
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(self_sudo.filter_domain, self._get_eval_context())
            return records.sudo().filtered_domain(domain).with_env(records.env), domain
        else:
            return records, None

    @api.model
    def _add_postmortem(self, e):
        if self.user_has_groups('base.group_user'):
            e.context = {}
            e.context['exception_class'] = 'base_automation'
            e.context['base_automation'] = {
                'id': self.id,
                'name': self.sudo().name,
            }

    def _process(self, records, domain_post=None):
        """ Process automation ``self`` on the ``records`` that have not been done yet. """
        # filter out the records on which self has already been done
        automation_done = self._context.get('__action_done', {})
        records_done = automation_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        # mark the remaining records as done (to avoid recursive processing)
        if self.env.context.get('__action_feedback'):
            # modify the context dict in place: this is useful when fields are
            # computed during the pre/post filtering, in order to know which
            # automations have already been run by the computation itself
            automation_done[self] = records_done + records
        else:
            automation_done = dict(automation_done)
            automation_done[self] = records_done + records
            self = self.with_context(__action_done=automation_done)
            records = records.with_context(__action_done=automation_done)

        # modify records
        if 'date_automation_last' in records._fields:
            records.date_automation_last = fields.Datetime.now()

        # we process the automation on the records for which any watched field
        # has been modified, and only mark the automation as done for those
        records = records.filtered(self._check_trigger_fields)
        automation_done[self] = records_done + records

        # prepare the contexts for server actions
        contexts = [
            {
                'active_model': record._name,
                'active_ids': record.ids,
                'active_id': record.id,
                'domain_post': domain_post,
            }
            for record in records
        ]

        # execute server actions
        for action in self.sudo().action_server_ids:
            for ctx in contexts:
                try:
                    action.with_context(**ctx).run()
                except Exception as e:
                    self._add_postmortem(e)
                    raise

    def _check_trigger_fields(self, record):
        """ Return whether any of the trigger fields has been modified on ``record``. """
        self_sudo = self.sudo()
        if not self_sudo.trigger_field_ids:
            # all fields are implicit triggers
            return True

        if self._context.get('old_values') is None:
            # this is a create: all fields are considered modified
            return True

        # note: old_vals are in the record format
        old_vals = self._context['old_values'].get(record.id, {})

        def differ(name):
            return name in old_vals and record[name] != old_vals[name]

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
            """ Instanciate a create method that processes automation rules. """
            @api.model_create_multi
            def create(self, vals_list, **kw):
                # retrieve the automation rules to possibly execute
                automations = self.env['base.automation']._get_actions(self, CREATE_TRIGGERS)
                if not automations:
                    return create.origin(self, vals_list, **kw)
                # call original method
                records = create.origin(self.with_env(automations.env), vals_list, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for automation in automations.with_context(old_values=None):
                    automation._process(automation._filter_post(records, feedback=True))
                return records.with_env(self.env)

            return create

        def make_write():
            """ Instanciate a write method that processes automation rules. """
            def write(self, vals, **kw):
                # retrieve the automation rules to possibly execute
                automations = self.env['base.automation']._get_actions(self, WRITE_TRIGGERS)
                if not (automations and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(automations.env).filtered('id')
                # check preconditions on records
                pre = {a: a._filter_pre(records) for a in automations}
                # read old values before the update
                old_values = {
                    record.id: {field_name: record[field_name] for field_name in vals}
                    for record in records
                }
                # call original method
                write.origin(self.with_env(automations.env), vals, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for automation in automations.with_context(old_values=old_values):
                    records, domain_post = automation._filter_post_export_domain(pre[automation], feedback=True)
                    automation._process(records, domain_post=domain_post)
                return True

            return write

        def make_compute_field_value():
            """ Instanciate a compute_field_value method that processes automation rules. """
            #
            # Note: This is to catch updates made by field recomputations.
            #
            def _compute_field_value(self, field):
                # determine fields that may trigger an automation
                stored_fnames = [f.name for f in self.pool.field_computed[field] if f.store]
                if not stored_fnames:
                    return _compute_field_value.origin(self, field)
                # retrieve the action rules to possibly execute
                automations = self.env['base.automation']._get_actions(self, WRITE_TRIGGERS)
                records = self.filtered('id').with_env(automations.env)
                if not (automations and records):
                    _compute_field_value.origin(self, field)
                    return True
                # check preconditions on records
                pre = {a: a._filter_pre(records) for a in automations}
                # read old values before the update
                old_values = {
                    record.id: {fname: record[fname] for fname in stored_fnames}
                    for record in records
                }
                # call original method
                _compute_field_value.origin(self, field)
                # check postconditions, and execute automations on the records that satisfy them
                for automation in automations.with_context(old_values=old_values):
                    records, domain_post = automation._filter_post_export_domain(pre[automation], feedback=True)
                    automation._process(records, domain_post=domain_post)
                return True

            return _compute_field_value

        def make_unlink():
            """ Instanciate an unlink method that processes automation rules. """
            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                automations = self.env['base.automation']._get_actions(self, ['on_unlink'])
                records = self.with_env(automations.env)
                # check conditions, and execute actions on the records that satisfy them
                for automation in automations:
                    automation._process(automation._filter_post(records, feedback=True))
                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(automation_rule_id):
            """ Instanciate an onchange method for the given automation rule. """
            def base_automation_onchange(self):
                automation_rule = self.env['base.automation'].browse(automation_rule_id)
                result = {}
                actions = automation_rule.sudo().action_server_ids.with_context(
                    active_model=self._name,
                    active_id=self._origin.id,
                    active_ids=self._origin.ids,
                    onchange_self=self,
                )
                for action in actions:
                    try:
                        res = action.run()
                    except Exception as e:
                        automation_rule._add_postmortem(e)
                        raise

                    if res:
                        if 'value' in res:
                            res['value'].pop('id', None)
                            self.update({key: val for key, val in res['value'].items() if key in self._fields})
                        if 'domain' in res:
                            result.setdefault('domain', {}).update(res['domain'])
                        if 'warning' in res:
                            result['warning'] = res["warning"]
                return result

            return base_automation_onchange

        def make_message_post():
            def _message_post(self, *args, **kwargs):
                message = _message_post.origin(self, *args, **kwargs)
                # Don't execute automations for a message emitted during
                # the run of automations for a real message
                # Don't execute if we know already that a message is only internal
                message_sudo = message.sudo().with_context(active_test=False)
                if "__action_done"  in self.env.context or message_sudo.is_internal or message_sudo.subtype_id.internal:
                    return message
                if message_sudo.message_type in ('notification', 'auto_comment', 'user_notification'):
                    return message

                # always execute actions when the author is a customer
                # if author is not set, it means the message is coming from outside
                mail_trigger = "on_message_received" if not message_sudo.author_id or message_sudo.author_id.partner_share else "on_message_sent"
                automations = self.env['base.automation']._get_actions(self, [mail_trigger])
                for automation in automations.with_context(old_values=None):
                    records = automation._filter_pre(self, feedback=True)
                    automation._process(records)

                return message
            return _message_post

        patched_models = defaultdict(set)

        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = model.env.registry[model._name]
                method.origin = getattr(ModelClass, name)
                setattr(ModelClass, name, method)

        # retrieve all actions, and patch their corresponding model
        for automation_rule in self.with_context({}).search([]):
            Model = self.env.get(automation_rule.model_name)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning(
                    "Automation rule with name '%s' (ID %d) depends on model %s (ID: %d)",
                    automation_rule.name,
                    automation_rule.id,
                    automation_rule.model_name,
                    automation_rule.model_id.id)
                continue

            if automation_rule.trigger in CREATE_WRITE_SET:
                if automation_rule.trigger in CREATE_TRIGGERS:
                    patch(Model, 'create', make_create())
                if automation_rule.trigger in WRITE_TRIGGERS:
                    patch(Model, 'write', make_write())
                    patch(Model, '_compute_field_value', make_compute_field_value())

            elif automation_rule.trigger == 'on_unlink':
                patch(Model, 'unlink', make_unlink())

            elif automation_rule.trigger == 'on_change':
                # register an onchange method for the automation_rule
                method = make_onchange(automation_rule.id)
                for field in automation_rule.on_change_field_ids:
                    Model._onchange_methods[field.name].append(method)
                if automation_rule.on_change_field_ids:
                    self.env.registry.clear_cache('templates')

            if automation_rule.model_id.is_mail_thread and automation_rule.trigger in MAIL_TRIGGERS:
                patch(Model, "message_post", make_message_post())

    def _unregister_hook(self):
        """ Remove the patches installed by _register_hook() """
        NAMES = ['create', 'write', '_compute_field_value', 'unlink', '_onchange_methods', "message_post"]
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass

    @api.model
    def _check_delay(self, automation, record, record_dt):
        if self._get_calendar(automation, record) and automation.trg_date_range_type == 'day':
            return self._get_calendar(automation, record).plan_days(
                automation.trg_date_range,
                fields.Datetime.from_string(record_dt),
                compute_leaves=True,
            )
        else:
            delay = DATE_RANGE_FUNCTION[automation.trg_date_range_type](automation.trg_date_range)
            return fields.Datetime.from_string(record_dt) + delay

    @api.model
    def _get_calendar(self, automation, record):
        return automation.trg_date_calendar_id

    @api.model
    def _check(self, automatic=False, use_new_cursor=False):
        """ This Function is called by scheduler. """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})

        # retrieve all the automation rules to run based on a timed condition
        for automation in self.with_context(active_test=True).search([('trigger', 'in', TIME_TRIGGERS)]):
            _logger.info("Starting time-based automation rule `%s`.", automation.name)
            last_run = fields.Datetime.from_string(automation.last_run) or datetime.datetime.fromtimestamp(0, tz=None)
            eval_context = automation._get_eval_context()

            # retrieve all the records that satisfy the automation's condition
            domain = []
            context = dict(self._context)
            if automation.filter_domain:
                domain = safe_eval.safe_eval(automation.filter_domain, eval_context)
            records = self.env[automation.model_name].with_context(context).search(domain)

            def get_record_dt(record):
                # determine when automation should occur for the records
                if automation.trg_date_id.name == "date_automation_last" and "create_date" in records._fields:
                    return record[automation.trg_date_id.name] or record.create_date
                else:
                    return record[automation.trg_date_id.name]

            # process action on the records that should be executed
            now = datetime.datetime.now()
            past_now = {}
            past_last_run = {}
            for record in records:
                record_dt = get_record_dt(record)
                if not record_dt:
                    continue
                if automation.trg_date_calendar_id and automation.trg_date_range_type == 'day':
                    calendar = self._get_calendar(automation, record)
                    if calendar.id not in past_now:
                        past_now[calendar.id] = calendar.plan_days(
                            - automation.trg_date_range,
                            now,
                            compute_leaves=True,
                        )
                        past_last_run[calendar.id] = calendar.plan_days(
                            - automation.trg_date_range,
                            last_run,
                            compute_leaves=True,
                        )
                    is_process_to_run = past_last_run[calendar.id] <= fields.Datetime.to_datetime(record_dt) < past_now[calendar.id]
                else:
                    is_process_to_run = last_run <= self._check_delay(automation, record, record_dt) < now
                if is_process_to_run:
                    try:
                        automation._process(record)
                    except Exception:
                        _logger.error(traceback.format_exc())

            automation.write({'last_run': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            _logger.info("Time-based automation rule `%s` done.", automation.name)

            if automatic:
                # auto-commit for batch processing
                self._cr.commit()
