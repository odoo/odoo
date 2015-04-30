# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

import openerp
from openerp import api, fields, models
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

DATE_RANGE_FUNCTION = {
    'minutes': lambda interval: timedelta(minutes=interval),
    'hour': lambda interval: timedelta(hours=interval),
    'day': lambda interval: timedelta(days=interval),
    'month': lambda interval: timedelta(months=interval),
    False: lambda interval: timedelta(0),
}


class BaseActionRule(models.Model):
    """ Base Action Rules """

    _name = 'base.action.rule'
    _description = 'Action Rules'
    _order = 'sequence'

    name = fields.Char('Rule Name', required=True)
    model_id = fields.Many2one(
        'ir.model', string='Related Document Model',
        required=True, domain=[('osv_memory', '=', False)])
    model = fields.Char(related='model_id.model')
    active = fields.Boolean(
        default=True,
        help="When unchecked, the rule is hidden and will not be executed.")
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of rules.")
    kind = fields.Selection([
        ('on_create', 'On Creation'),
        ('on_write', 'On Update'),
        ('on_create_or_write', 'On Creation & Update'),
        ('on_time', 'Based on Timed Condition')],
        string='When to Run')
    trg_date_id = fields.Many2one(
        'ir.model.fields', string='Trigger Date',
        help="When should the condition be triggered. If present, will be checked by the scheduler. If empty, will be checked at creation and update.",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]")
    trg_date_range = fields.Integer(
        'Delay after trigger date',
        help="Delay after the trigger date."
        "You can put a negative number if you need as delay before the"
        "trigger date, like sending a reminder 15 minutes before a meeting.")
    trg_date_range_type = fields.Selection([
        ('minutes', 'Minutes'), ('hour', 'Hours'),
        ('day', 'Days'), ('month', 'Months')],
        'Delay type', default='day')
    trg_date_calendar_id = fields.Many2one(
        'resource.calendar', string='Use Calendar',
        help='When calculating a day-based timed condition, it is possible to use a calendar to compute the date based on working days.',
        ondelete='set null')
    act_user_id = fields.Many2one('res.users', string='Set Responsible')
    act_followers = fields.Many2many("res.partner", string="Add Followers")
    server_action_ids = fields.Many2many(
        'ir.actions.server', string='Server Actions',
        domain="[('model_id', '=', model_id)]",
        help="Examples: email reminders, call object service, etc.")
    filter_pre_id = fields.Many2one(
        'ir.filters', string='Before Update Filter',
        ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
        help="If present, this condition must be satisfied before the update of the record.")
    filter_pre_domain = fields.Char(string='Before Update Domain', help="If present, this condition must be satisfied before the update of the record.")
    filter_id = fields.Many2one(
        'ir.filters', string='Filter',
        ondelete='restrict', domain="[('model_id', '=', model_id.model)]",
        help="If present, this condition must be satisfied before executing the action rule.")
    filter_domain = fields.Char(string='Domain', help="If present, this condition must be satisfied before executing the action rule.")
    last_run = fields.Datetime(readonly=True, copy=False)

    @api.onchange('kind')
    def _onchange_kind(self):
        if self.kind in ['on_create', 'on_create_or_write']:
            self.filter_pre_id = False
            self.trg_date_id = False
            self.trg_date_range = False
            self.trg_date_range_type = False
        elif self.kind in ['on_write', 'on_create_or_write']:
            self.trg_date_id = False
            self.trg_date_range = False
            self.trg_date_range_type = False
        elif self.kind == 'on_time':
            self.filter_pre_id = False

    @api.onchange('filter_pre_id')
    def _onchange_filter_pre_id(self):
        self.filter_pre_domain = self.filter_pre_id.domain

    @api.onchange('filter_id')
    def _onchange_filter_id(self):
        self.filter_domain = self.filter_id.domain

    @api.model
    def _filter(self, action, action_filter, record_ids, domain=False):
        """ Filter the list record_ids that satisfy the domain or the action filter. """
        if record_ids and (domain or action_filter):
            if domain:
                new_domain = [('id', 'in', record_ids)] + eval(domain)
                ctx = dict(self.env.context)
            elif action_filter:
                assert action.model == action_filter.model_id, "Filter model different from action rule model"
                new_domain = [('id', 'in', record_ids)] + eval(action_filter.domain)
                ctx = dict(self.env.context)
                ctx.update(dict(action_filter.env.context))
            record_ids = self.with_context(ctx).env[action.model].search(new_domain).ids
        return record_ids

    @api.model
    def _process(self, action, record_ids):
        """ process the given action on the records """
        Model = self.env[action.model_id.model]
        # modify records
        values = {}
        if 'date_action_last' in Model._fields:
            values['date_action_last'] = fields.Datetime.now()
        if action.act_user_id and 'user_id' in Model._fields:
            values['user_id'] = action.act_user_id.id
        if values:
            Model.browse(record_ids).write(values)

        if action.act_followers and hasattr(Model, 'message_subscribe'):
            follower_ids = map(int, action.act_followers)
            Model.message_subscribe(record_ids, follower_ids)

        # execute server actions
        if action.server_action_ids:
            server_action_ids = map(int, action.server_action_ids)
            for record in Model.browse(record_ids):
                ActionServer = self.env['ir.actions.server'].with_context(dict(self.env.context, active_model=Model._name, active_ids=[record.id], active_id=record.id)).browse(server_action_ids)
                ActionServer.run()

    @api.v7
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
                action_ids = action_model.search(cr, uid, action_dom, context=context)

                # check postconditions, and execute actions on the records that satisfy them
                for action in action_model.browse(cr, uid, action_ids, context=context):
                    if action_model._filter(cr, uid, action, action.filter_id, [new_id], domain=action.filter_domain, context=context):
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
                    pre_ids[action] = action_model._filter(cr, uid, action, action.filter_pre_id, ids, domain=action.filter_pre_domain, context=context)

                # call original method
                write.origin(self, cr, uid, ids, vals, context=context, **kwargs)

                # check postconditions, and execute actions on the records that satisfy them
                for action in actions:
                    post_ids = action_model._filter(cr, uid, action, action.filter_id, pre_ids[action], domain=action.filter_domain, context=context)
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

    @api.v8
    def _register_hook(self):
        return self._model._register_hook(self.env.cr, self.ids)

    @api.model
    def _update_cron(self):
        try:
            Cron = self.env['ir.model.data'].get_object('BaseActionRule', 'ir_cron_crm_action')
        except ValueError:
            return False
        return Cron.toggle(model=self._name, domain=[('kind', '=', 'on_time')])

    @api.model
    def create(self, vals):
        res_id = super(BaseActionRule, self).create(vals)
        if res_id._register_hook():
            openerp.modules.registry.RegistryManager.signal_registry_change(self.env.cr.dbname)
        self._update_cron()
        return res_id

    @api.multi
    def write(self, vals):
        super(BaseActionRule, self).write(vals)
        if self._register_hook():
            openerp.modules.registry.RegistryManager.signal_registry_change(self.env.cr.dbname)
        self._update_cron()
        return True

    @api.multi
    def unlink(self):
        res = super(BaseActionRule, self).unlink()
        self._update_cron()
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.model = self.model_id.model
        self.filter_pre_id = False
        self.filter_id = False

    @api.model
    def _check_delay(self, action, record, record_dt):
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day':
            start_dt = fields.Datetime.from_string(record_dt)
            action_dt = self.env['resource.calendar'].schedule_days_get_date(
                action.trg_date_calendar_id.id, action.trg_date_range,
                day_date=start_dt, compute_leaves=True
            )
        else:
            delay = DATE_RANGE_FUNCTION[action.trg_date_range_type](action.trg_date_range)
            action_dt = fields.Datetime.from_string(record_dt) + delay
        return action_dt

    @api.model
    def _check(self, automatic=False, use_new_cursor=False):
        """ This Function is called by scheduler. """
        # retrieve all the action rules to run based on a timed condition
        for action in self.search([('kind', '=', 'on_time')]):
            now = datetime.now()
            if action.last_run:
                last_run = fields.Datetime.from_string(action.last_run)
            else:
                last_run = datetime.utcfromtimestamp(0)
            # retrieve all the records that satisfy the action's condition
            Model = self.env[action.model_id.model]
            domain = []
            ctx = dict(self.env.context)
            if action.filter_domain is not False:
                domain = eval(action.filter_domain)
            elif action.filter_id:
                domain = eval(action.filter_id.domain)
                ctx.update(dict(action.filter_id.env.context))
                if 'lang' not in ctx:
                    # Filters might be language-sensitive, attempt to reuse creator lang
                    # as we are usually running this as super-user in background
                    [filter_meta] = action.filter_id.get_metadata()
                    user_id = filter_meta['write_uid'] and filter_meta['write_uid'][0] or \
                        filter_meta['create_uid'][0]
                    ctx['lang'] = self.env['res.users'].browse(user_id).lang
            records = Model.with_context(ctx).search(domain)

            # determine when action should occur for the records
            date_field = action.trg_date_id.name
            if date_field == 'date_action_last' and 'create_date' in Model._fields:
                get_record_dt = lambda record: record[date_field] or record.create_date
            else:
                get_record_dt = lambda record: record[date_field]

            # process action on the records that should be executed
            for record in records:
                record_dt = get_record_dt(record)
                if not record_dt:
                    continue
                action_dt = self._check_delay(action, record, record_dt)
                if last_run <= action_dt < now:
                    try:
                        self.with_context(action=True)._process(action, [record.id])
                    except Exception:
                        import traceback
                        _logger.error(traceback.format_exc())
            action.write({'last_run': fields.Datetime.now()})
            if automatic:
                # auto-commit for batch processing
                self.env.cr.commit()
