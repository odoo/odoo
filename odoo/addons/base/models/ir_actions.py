# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import MissingError, ValidationError, AccessError
from odoo.tools import frozendict
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.tools.float_utils import float_compare
from odoo.http import request

import base64
from collections import defaultdict
import functools
import logging

from pytz import timezone

_logger = logging.getLogger(__name__)
_server_action_logger = _logger.getChild("server_action_safe_eval")


class LoggerProxy:
    """ Proxy of the `_logger` element in order to be used in server actions.
    We purposefully restrict its method as it will be executed in `safe_eval`.
    """
    @staticmethod
    def log(level, message, *args, stack_info=False, exc_info=False):
        _server_action_logger.log(level, message, *args, stack_info=stack_info, exc_info=exc_info)

    @staticmethod
    def info(message, *args, stack_info=False, exc_info=False):
        _server_action_logger.info(message, *args, stack_info=stack_info, exc_info=exc_info)

    @staticmethod
    def warning(message, *args, stack_info=False, exc_info=False):
        _server_action_logger.warning(message, *args, stack_info=stack_info, exc_info=exc_info)

    @staticmethod
    def error(message, *args, stack_info=False, exc_info=False):
        _server_action_logger.error(message, *args, stack_info=stack_info, exc_info=exc_info)

    @staticmethod
    def exception(message, *args, stack_info=False, exc_info=True):
        _server_action_logger.exception(message, *args, stack_info=stack_info, exc_info=exc_info)


class IrActions(models.Model):
    _name = 'ir.actions.actions'
    _description = 'Actions'
    _table = 'ir_actions'
    _order = 'name'

    name = fields.Char(string='Action Name', required=True, translate=True)
    type = fields.Char(string='Action Type', required=True)
    xml_id = fields.Char(compute='_compute_xml_id', string="External ID")
    help = fields.Html(string='Action Description',
                       help='Optional help text for the users with a description of the target view, such as its usage and purpose.',
                       translate=True)
    binding_model_id = fields.Many2one('ir.model', ondelete='cascade',
                                       help="Setting a value makes this action available in the sidebar for the given model.")
    binding_type = fields.Selection([('action', 'Action'),
                                     ('report', 'Report')],
                                    required=True, default='action')
    binding_view_types = fields.Char(default='list,form')

    def _compute_xml_id(self):
        res = self.get_external_id()
        for record in self:
            record.xml_id = res.get(record.id)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(IrActions, self).create(vals_list)
        # self.get_bindings() depends on action records
        self.clear_caches()
        return res

    def write(self, vals):
        res = super(IrActions, self).write(vals)
        # self.get_bindings() depends on action records
        self.clear_caches()
        return res

    def unlink(self):
        """unlink ir.action.todo which are related to actions which will be deleted.
           NOTE: ondelete cascade will not work on ir.actions.actions so we will need to do it manually."""
        todos = self.env['ir.actions.todo'].search([('action_id', 'in', self.ids)])
        todos.unlink()
        res = super(IrActions, self).unlink()
        # self.get_bindings() depends on action records
        self.clear_caches()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_check_home_action(self):
        self.env['res.users'].with_context(active_test=False).search([('action_id', 'in', self.ids)]).sudo().write({'action_id': None})

    @api.model
    def _get_eval_context(self, action=None):
        """ evaluation context to pass to safe_eval """
        return {
            'uid': self._uid,
            'user': self.env.user,
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            'timezone': timezone,
            'float_compare': float_compare,
            'b64encode': base64.b64encode,
            'b64decode': base64.b64decode,
            'Command': Command,
        }

    @api.model
    def get_bindings(self, model_name):
        """ Retrieve the list of actions bound to the given model.

           :return: a dict mapping binding types to a list of dict describing
                    actions, where the latter is given by calling the method
                    ``read`` on the action record.
        """
        result = {}
        for action_type, all_actions in self._get_bindings(model_name).items():
            actions = []
            for action in all_actions:
                action = dict(action)
                groups = action.pop('groups_id', None)
                if groups and not self.user_has_groups(groups):
                    # the user may not perform this action
                    continue
                res_model = action.pop('res_model', None)
                if res_model and not self.env['ir.model.access'].check(
                    res_model,
                    mode='read',
                    raise_exception=False
                ):
                    # the user won't be able to read records
                    continue
                actions.append(action)
            if actions:
                result[action_type] = actions
        return result

    @tools.ormcache('model_name', 'self.env.lang')
    def _get_bindings(self, model_name):
        cr = self.env.cr

        # discard unauthorized actions, and read action definitions
        result = defaultdict(list)

        self.env.flush_all()
        cr.execute("""
            SELECT a.id, a.type, a.binding_type
              FROM ir_actions a
              JOIN ir_model m ON a.binding_model_id = m.id
             WHERE m.model = %s
          ORDER BY a.id
        """, [model_name])
        for action_id, action_model, binding_type in cr.fetchall():
            try:
                action = self.env[action_model].sudo().browse(action_id)
                fields = ['name', 'binding_view_types']
                for field in ('groups_id', 'res_model', 'sequence'):
                    if field in action._fields:
                        fields.append(field)
                action = action.read(fields)[0]
                if action.get('groups_id'):
                    groups = self.env['res.groups'].browse(action['groups_id'])
                    action['groups_id'] = ','.join(ext_id for ext_id in groups._ensure_xml_id().values())
                result[binding_type].append(frozendict(action))
            except (MissingError):
                continue

        # sort actions by their sequence if sequence available
        if result.get('action'):
            result['action'] = tuple(sorted(result['action'], key=lambda vals: vals.get('sequence', 0)))
        return frozendict(result)

    @api.model
    def _for_xml_id(self, full_xml_id):
        """ Returns the action content for the provided xml_id

        :param xml_id: the namespace-less id of the action (the @id
                       attribute from the XML file)
        :return: A read() view of the ir.actions.action safe for web use
        """
        record = self.env.ref(full_xml_id)
        assert isinstance(self.env[record._name], type(self))
        return record._get_action_dict()

    def _get_action_dict(self):
        """ Returns the action content for the provided action record.
        """
        self.ensure_one()
        readable_fields = self._get_readable_fields()
        return {
            field: value
            for field, value in self.sudo().read()[0].items()
            if field in readable_fields
        }

    def _get_readable_fields(self):
        """ return the list of fields that are safe to read

        Fetched via /web/action/load or _for_xml_id method
        Only fields used by the web client should included
        Accessing content useful for the server-side must
        be done manually with superuser
        """
        return {
            "binding_model_id", "binding_type", "binding_view_types",
            "display_name", "help", "id", "name", "type", "xml_id",
        }


class IrActionsActWindow(models.Model):
    _name = 'ir.actions.act_window'
    _description = 'Action Window'
    _table = 'ir_act_window'
    _inherit = 'ir.actions.actions'
    _order = 'name'

    @api.constrains('res_model', 'binding_model_id')
    def _check_model(self):
        for action in self:
            if action.res_model not in self.env:
                raise ValidationError(_('Invalid model name %r in action definition.', action.res_model))
            if action.binding_model_id and action.binding_model_id.model not in self.env:
                raise ValidationError(_('Invalid model name %r in action definition.', action.binding_model_id.model))

    @api.depends('view_ids.view_mode', 'view_mode', 'view_id.type')
    def _compute_views(self):
        """ Compute an ordered list of the specific view modes that should be
            enabled when displaying the result of this action, along with the
            ID of the specific view to use for each mode, if any were required.

            This function hides the logic of determining the precedence between
            the view_modes string, the view_ids o2m, and the view_id m2o that
            can be set on the action.
        """
        for act in self:
            act.views = [(view.view_id.id, view.view_mode) for view in act.view_ids]
            got_modes = [view.view_mode for view in act.view_ids]
            all_modes = act.view_mode.split(',')
            missing_modes = [mode for mode in all_modes if mode not in got_modes]
            if missing_modes:
                if act.view_id.type in missing_modes:
                    # reorder missing modes to put view_id first if present
                    missing_modes.remove(act.view_id.type)
                    act.views.append((act.view_id.id, act.view_id.type))
                act.views.extend([(False, mode) for mode in missing_modes])

    @api.constrains('view_mode')
    def _check_view_mode(self):
        for rec in self:
            modes = rec.view_mode.split(',')
            if len(modes) != len(set(modes)):
                raise ValidationError(_('The modes in view_mode must not be duplicated: %s', modes))
            if ' ' in modes:
                raise ValidationError(_('No spaces allowed in view_mode: %r', modes))

    @api.depends('res_model', 'search_view_id')
    def _compute_search_view(self):
        for act in self:
            fvg = self.env[act.res_model].get_view(act.search_view_id.id, 'search')
            act.search_view = str(fvg)

    type = fields.Char(default="ir.actions.act_window")
    view_id = fields.Many2one('ir.ui.view', string='View Ref.', ondelete='set null')
    domain = fields.Char(string='Domain Value',
                         help="Optional domain filtering of the destination data, as a Python expression")
    context = fields.Char(string='Context Value', default={}, required=True,
                          help="Context dictionary as Python expression, empty by default (Default: {})")
    res_id = fields.Integer(string='Record ID', help="Database ID of record to open in form view, when ``view_mode`` is set to 'form' only")
    res_model = fields.Char(string='Destination Model', required=True,
                            help="Model name of the object to open in the view window")
    target = fields.Selection([('current', 'Current Window'), ('new', 'New Window'), ('inline', 'Inline Edit'), ('fullscreen', 'Full Screen'), ('main', 'Main action of Current Window')], default="current", string='Target Window')
    view_mode = fields.Char(required=True, default='tree,form',
                            help="Comma-separated list of allowed view modes, such as 'form', 'tree', 'calendar', etc. (Default: tree,form)")
    usage = fields.Char(string='Action Usage',
                        help="Used to filter menu and home actions from the user form.")
    view_ids = fields.One2many('ir.actions.act_window.view', 'act_window_id', string='No of Views')
    views = fields.Binary(compute='_compute_views',
                          help="This function field computes the ordered list of views that should be enabled " \
                               "when displaying the result of an action, federating view mode, views and " \
                               "reference view. The result is returned as an ordered list of pairs (view_id,view_mode).")
    limit = fields.Integer(default=80, help='Default limit for the list view')
    groups_id = fields.Many2many('res.groups', 'ir_act_window_group_rel',
                                 'act_id', 'gid', string='Groups')
    search_view_id = fields.Many2one('ir.ui.view', string='Search View Ref.')
    filter = fields.Boolean()
    search_view = fields.Text(compute='_compute_search_view')

    def read(self, fields=None, load='_classic_read'):
        """ call the method get_empty_list_help of the model and set the window action help message
        """
        result = super(IrActionsActWindow, self).read(fields, load=load)
        if not fields or 'help' in fields:
            for values in result:
                model = values.get('res_model')
                if model in self.env:
                    eval_ctx = dict(self.env.context)
                    try:
                        ctx = safe_eval(values.get('context', '{}'), eval_ctx)
                    except:
                        ctx = {}
                    values['help'] = self.with_context(**ctx).env[model].get_empty_list_help(values.get('help', ''))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        for vals in vals_list:
            if not vals.get('name') and vals.get('res_model'):
                vals['name'] = self.env[vals['res_model']]._description
        return super(IrActionsActWindow, self).create(vals_list)

    def unlink(self):
        self.clear_caches()
        return super(IrActionsActWindow, self).unlink()

    def exists(self):
        ids = self._existing()
        existing = self.filtered(lambda rec: rec.id in ids)
        return existing

    @api.model
    @tools.ormcache()
    def _existing(self):
        self._cr.execute("SELECT id FROM %s" % self._table)
        return set(row[0] for row in self._cr.fetchall())


    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "context", "domain", "filter", "groups_id", "limit", "res_id",
            "res_model", "search_view", "search_view_id", "target", "view_id",
            "view_mode", "views",
            # `flags` is not a real field of ir.actions.act_window but is used
            # to give the parameters to generate the action
            "flags"
        }


VIEW_TYPES = [
    ('tree', 'Tree'),
    ('form', 'Form'),
    ('graph', 'Graph'),
    ('pivot', 'Pivot'),
    ('calendar', 'Calendar'),
    ('gantt', 'Gantt'),
    ('kanban', 'Kanban'),
]


class IrActionsActWindowView(models.Model):
    _name = 'ir.actions.act_window.view'
    _description = 'Action Window View'
    _table = 'ir_act_window_view'
    _rec_name = 'view_id'
    _order = 'sequence,id'

    sequence = fields.Integer()
    view_id = fields.Many2one('ir.ui.view', string='View')
    view_mode = fields.Selection(VIEW_TYPES, string='View Type', required=True)
    act_window_id = fields.Many2one('ir.actions.act_window', string='Action', ondelete='cascade')
    multi = fields.Boolean(string='On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view.")

    def _auto_init(self):
        res = super(IrActionsActWindowView, self)._auto_init()
        tools.create_unique_index(self._cr, 'act_window_view_unique_mode_per_action',
                                  self._table, ['act_window_id', 'view_mode'])
        return res


class IrActionsActWindowclose(models.Model):
    _name = 'ir.actions.act_window_close'
    _description = 'Action Window Close'
    _inherit = 'ir.actions.actions'
    _table = 'ir_actions'

    type = fields.Char(default='ir.actions.act_window_close')

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            # 'effect' and 'infos' are not real fields of `ir.actions.act_window_close` but they are
            # used to display the rainbowman ('effect') and waited by the action_service ('infos').
            "effect", "infos"
        }


class IrActionsActUrl(models.Model):
    _name = 'ir.actions.act_url'
    _description = 'Action URL'
    _table = 'ir_act_url'
    _inherit = 'ir.actions.actions'
    _order = 'name'

    type = fields.Char(default='ir.actions.act_url')
    url = fields.Text(string='Action URL', required=True)
    target = fields.Selection([('new', 'New Window'), ('self', 'This Window')],
                              string='Action Target', default='new', required=True)

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "target", "url",
        }


class IrActionsServer(models.Model):
    """ Server actions model. Server action work on a base model and offer various
    type of actions that can be executed automatically, for example using base
    action rules, of manually, by adding the action in the 'More' contextual
    menu.

    Since Odoo 8.0 a button 'Create Menu Action' button is available on the
    action form view. It creates an entry in the More menu of the base model.
    This allows to create server actions and run them in mass mode easily through
    the interface.

    The available actions are :

    - 'Execute Python Code': a block of python code that will be executed
    - 'Create a new Record': create a new record with new values
    - 'Write on a Record': update the values of a record
    - 'Execute several actions': define an action that triggers several other
      server actions
    """
    _name = 'ir.actions.server'
    _description = 'Server Actions'
    _table = 'ir_act_server'
    _inherit = 'ir.actions.actions'
    _order = 'sequence,name'

    DEFAULT_PYTHON_CODE = """# Available variables:
#  - env: environment on which the action is triggered
#  - model: model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: utility function to compare floats based on specific precision
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - _logger: _logger.info(message): logger to emit messages in server logs
#  - UserError: exception class for raising user-facing warning messages
#  - Command: x2many commands namespace
# To return an action, assign: action = {...}\n\n\n\n"""

    type = fields.Char(default='ir.actions.server')
    usage = fields.Selection([
        ('ir_actions_server', 'Server Action'),
        ('ir_cron', 'Scheduled Action')], string='Usage',
        default='ir_actions_server', required=True)
    state = fields.Selection([
        ('code', 'Execute Python Code'),
        ('object_create', 'Create a new Record'),
        ('object_write', 'Update the Record'),
        ('multi', 'Execute several actions')], string='Action To Do',
        default='object_write', required=True, copy=True,
        help="Type of server action. The following values are available:\n"
             "- 'Execute Python Code': a block of python code that will be executed\n"
             "- 'Create a new Record': create a new record with new values\n"
             "- 'Update a Record': update the values of a record\n"
             "- 'Execute several actions': define an action that triggers several other server actions\n"
             "- 'Send Email': post a message, a note or send an email (Discuss)\n"
             "- 'Add Followers': add followers to a record (Discuss)\n"
             "- 'Create Next Activity': create an activity (Discuss)\n"
             "- 'Send SMS Text Message': send SMS, log them on documents (SMS)")
    # Generic
    sequence = fields.Integer(default=5,
                              help="When dealing with multiple actions, the execution order is "
                                   "based on the sequence. Low number means high priority.")
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade',
                               help="Model on which the server action runs.")
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    # Python code
    code = fields.Text(string='Python Code', groups='base.group_system',
                       default=DEFAULT_PYTHON_CODE,
                       help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about python expression is given in the help tab.")
    # Multi
    child_ids = fields.Many2many('ir.actions.server', 'rel_server_actions', 'server_id', 'action_id',
                                 string='Child Actions', help='Child server actions that will be executed. Note that the last return returned action value will be used as global return value.')
    # Create
    crud_model_id = fields.Many2one(
        'ir.model', string='Target Model',
        compute='_compute_crud_model_id', readonly=False, store=True,
        help="Model for record creation / update. Set this field only to specify a different model than the base model.")
    crud_model_name = fields.Char(related='crud_model_id.model', string='Target Model Name', readonly=True)
    link_field_id = fields.Many2one(
        'ir.model.fields', string='Link Field',
        compute='_compute_link_field_id', readonly=False, store=True,
        help="Provide the field used to link the newly created record on the record used by the server action.")
    fields_lines = fields.One2many('ir.server.object.lines', 'server_id', string='Value Mapping', copy=True)
    groups_id = fields.Many2many('res.groups', 'ir_act_server_group_rel',
                                 'act_id', 'gid', string='Groups')

    @api.onchange('model_id')
    def _compute_crud_model_id(self):
        invalid = self.filtered(lambda act: act.crud_model_id != act.model_id)
        if invalid:
            invalid.crud_model_id = False

    @api.depends('model_id')
    def _compute_link_field_id(self):
        invalid = self.filtered(lambda act: act.link_field_id.model_id != act.model_id)
        if invalid:
            invalid.link_field_id = False

    @api.constrains('code')
    def _check_python_code(self):
        for action in self.sudo().filtered('code'):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.constrains('child_ids')
    def _check_recursion(self):
        if not self._check_m2m_recursion('child_ids'):
            raise ValidationError(_('Recursion found in child server actions'))

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "groups_id", "model_name",
        }

    def _get_runner(self):
        multi = True
        t = type(self)
        fn = getattr(t, f'_run_action_{self.state}_multi', None)\
          or getattr(t, f'run_action_{self.state}_multi', None)
        if not fn:
            multi = False
            fn = getattr(t, f'_run_action_{self.state}', None)\
              or getattr(t, f'run_action_{self.state}', None)
        if fn and fn.__name__.startswith('run_action_'):
            fn = functools.partial(fn, self)
        return fn, multi

    def _register_hook(self):
        super()._register_hook()

        for cls in type(self).mro():
            for symbol in vars(cls).keys():
                if symbol.startswith('run_action_'):
                    _logger.warning(
                        "RPC-public action methods are deprecated, found %r (in class %s.%s)",
                        symbol, cls.__module__, cls.__name__
                    )

    def create_action(self):
        """ Create a contextual action for each server action. """
        for action in self:
            action.write({'binding_model_id': action.model_id.id,
                          'binding_type': 'action'})
        return True

    def unlink_action(self):
        """ Remove the contextual actions created for the server actions. """
        self.check_access_rights('write', raise_exception=True)
        self.filtered('binding_model_id').write({'binding_model_id': False})
        return True

    def _run_action_code_multi(self, eval_context):
        safe_eval(self.code.strip(), eval_context, mode="exec", nocopy=True, filename=str(self))  # nocopy allows to return 'action'
        return eval_context.get('action')

    def _run_action_multi(self, eval_context=None):
        res = False
        for act in self.child_ids.sorted():
            res = act.run() or res
        return res

    def _run_action_object_write(self, eval_context=None):
        """Apply specified write changes to active_id."""
        vals = self.fields_lines.eval_value(eval_context=eval_context)
        res = {line.col1.name: vals[line.id] for line in self.fields_lines}

        if self._context.get('onchange_self'):
            record_cached = self._context['onchange_self']
            for field, new_value in res.items():
                record_cached[field] = new_value
        else:
            self.env[self.model_id.model].browse(self._context.get('active_id')).write(res)

    def _run_action_object_create(self, eval_context=None):
        """Create specified model object with specified values.

        If applicable, link active_id.<self.link_field_id> to the new record.
        """
        vals = self.fields_lines.eval_value(eval_context=eval_context)
        res = {line.col1.name: vals[line.id] for line in self.fields_lines}

        res = self.env[self.crud_model_id.model].create(res)

        if self.link_field_id:
            record = self.env[self.model_id.model].browse(self._context.get('active_id'))
            if self.link_field_id.ttype in ['one2many', 'many2many']:
                record.write({self.link_field_id.name: [Command.link(res.id)]})
            else:
                record.write({self.link_field_id.name: res.id})

    def _get_eval_context(self, action=None):
        """ Prepare the context used when evaluating python code, like the
        python formulas or code server actions.

        :param action: the current server action
        :type action: browse record
        :returns: dict -- evaluation context given to (safe_)safe_eval """
        def log(message, level="info"):
            with self.pool.cursor() as cr:
                cr.execute("""
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.env.uid, 'server', self._cr.dbname, __name__, level, message, "action", action.id, action.name))

        eval_context = super(IrActionsServer, self)._get_eval_context(action=action)
        model_name = action.model_id.sudo().model
        model = self.env[model_name]
        record = None
        records = None
        if self._context.get('active_model') == model_name and self._context.get('active_id'):
            record = model.browse(self._context['active_id'])
        if self._context.get('active_model') == model_name and self._context.get('active_ids'):
            records = model.browse(self._context['active_ids'])
        if self._context.get('onchange_self'):
            record = self._context['onchange_self']
        eval_context.update({
            # orm
            'env': self.env,
            'model': model,
            # Exceptions
            'UserError': odoo.exceptions.UserError,
            # record
            'record': record,
            'records': records,
            # helpers
            'log': log,
            '_logger': LoggerProxy,
        })
        return eval_context

    def run(self):
        """ Runs the server action. For each server action, the
        :samp:`_run_action_{TYPE}[_multi]` method is called. This allows easy
        overriding of the server actions.

        The ``_multi`` suffix means the runner can operate on multiple records,
        otherwise if there are multiple records the runner will be called once
        for each.

        The call context should contain the following keys:

        active_id
            id of the current object (single mode)
        active_model
            current model that should equal the action's model
        active_ids (optional)
           ids of the current records (mass mode). If ``active_ids`` and
           ``active_id`` are present, ``active_ids`` is given precedence.
        :return: an ``action_id`` to be executed, or ``False`` is finished
                 correctly without return action
        """
        res = False
        for action in self.sudo():
            action_groups = action.groups_id
            if action_groups:
                if not (action_groups & self.env.user.groups_id):
                    raise AccessError(_("You don't have enough access rights to run this action."))
            else:
                try:
                    self.env[action.model_name].check_access_rights("write")
                except AccessError:
                    _logger.warning("Forbidden server action %r executed while the user %s does not have access to %s.",
                        action.name, self.env.user.login, action.model_name,
                    )
                    raise

            eval_context = self._get_eval_context(action)
            records = eval_context.get('record') or eval_context['model']
            records |= eval_context.get('records') or eval_context['model']
            if records:
                try:
                    records.check_access_rule('write')
                except AccessError:
                    _logger.warning("Forbidden server action %r executed while the user %s does not have access to %s.",
                        action.name, self.env.user.login, records,
                    )
                    raise

            runner, multi = action._get_runner()
            if runner and multi:
                # call the multi method
                run_self = action.with_context(eval_context['env'].context)
                res = runner(run_self, eval_context=eval_context)
            elif runner:
                active_id = self._context.get('active_id')
                if not active_id and self._context.get('onchange_self'):
                    active_id = self._context['onchange_self']._origin.id
                    if not active_id:  # onchange on new record
                        res = runner(action, eval_context=eval_context)
                active_ids = self._context.get('active_ids', [active_id] if active_id else [])
                for active_id in active_ids:
                    # run context dedicated to a particular active_id
                    run_self = action.with_context(active_ids=[active_id], active_id=active_id)
                    eval_context["env"].context = run_self._context
                    res = runner(run_self, eval_context=eval_context)
            else:
                _logger.warning(
                    "Found no way to execute server action %r of type %r, ignoring it. "
                    "Verify that the type is correct or add a method called "
                    "`_run_action_<type>` or `_run_action_<type>_multi`.",
                    action.name, action.state
                )
        return res or False


class IrServerObjectLines(models.Model):
    _name = 'ir.server.object.lines'
    _description = 'Server Action value mapping'

    server_id = fields.Many2one('ir.actions.server', string='Related Server Action', ondelete='cascade')
    col1 = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade')
    value = fields.Text(required=True, help="Expression containing a value specification. \n"
                                            "When Formula type is selected, this field may be a Python expression "
                                            " that can use the same values as for the code field on the server action.\n"
                                            "If Value type is selected, the value will be used directly without evaluation.")
    evaluation_type = fields.Selection([
        ('value', 'Value'),
        ('reference', 'Reference'),
        ('equation', 'Python expression')
    ], 'Evaluation Type', default='value', required=True, change_default=True)
    resource_ref = fields.Reference(
        string='Record', selection='_selection_target_model',
        compute='_compute_resource_ref', inverse='_set_resource_ref')

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    @api.depends('col1.relation', 'value', 'evaluation_type')
    def _compute_resource_ref(self):
        for line in self:
            if line.evaluation_type in ['reference', 'value'] and line.col1 and line.col1.relation:
                value = line.value or ''
                try:
                    value = int(value)
                    if not self.env[line.col1.relation].browse(value).exists():
                        record = list(self.env[line.col1.relation]._search([], limit=1))
                        value = record[0] if record else 0
                except ValueError:
                    record = list(self.env[line.col1.relation]._search([], limit=1))
                    value = record[0] if record else 0
                line.resource_ref = '%s,%s' % (line.col1.relation, value)
            else:
                line.resource_ref = False

    @api.constrains('col1', 'evaluation_type')
    def _raise_many2many_error(self):
        if self.filtered(lambda line: line.col1.ttype == 'many2many' and line.evaluation_type == 'reference'):
            raise ValidationError(_('many2many fields cannot be evaluated by reference'))

    @api.onchange('resource_ref')
    def _set_resource_ref(self):
        for line in self.filtered(lambda line: line.evaluation_type == 'reference'):
            if line.resource_ref:
                line.value = str(line.resource_ref.id)

    def eval_value(self, eval_context=None):
        result = {}
        for line in self:
            expr = line.value
            if line.evaluation_type == 'equation':
                expr = safe_eval(line.value, eval_context)
            elif line.col1.ttype in ['many2one', 'integer']:
                try:
                    expr = int(line.value)
                except Exception:
                    pass
            result[line.id] = expr
        return result


class IrActionsTodo(models.Model):
    """
    Configuration Wizards
    """
    _name = 'ir.actions.todo'
    _description = "Configuration Wizards"
    _rec_name = 'action_id'
    _order = "sequence, id"

    action_id = fields.Many2one('ir.actions.actions', string='Action', required=True, index=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection([('open', 'To Do'), ('done', 'Done')], string='Status', default='open', required=True)
    name = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        todos = super(IrActionsTodo, self).create(vals_list)
        for todo in todos:
            if todo.state == "open":
                self.ensure_one_open_todo()
        return todos

    def write(self, vals):
        res = super(IrActionsTodo, self).write(vals)
        if vals.get('state', '') == 'open':
            self.ensure_one_open_todo()
        return res

    @api.model
    def ensure_one_open_todo(self):
        open_todo = self.search([('state', '=', 'open')], order='sequence asc, id desc', offset=1)
        if open_todo:
            open_todo.write({'state': 'done'})

    def unlink(self):
        if self:
            try:
                todo_open_menu = self.env.ref('base.open_menu')
                # don't remove base.open_menu todo but set its original action
                if todo_open_menu in self:
                    todo_open_menu.action_id = self.env.ref('base.action_client_base_menu').id
                    self -= todo_open_menu
            except ValueError:
                pass
        return super(IrActionsTodo, self).unlink()

    def action_launch(self):
        """ Launch Action of Wizard"""
        self.ensure_one()

        self.write({'state': 'done'})

        # Load action
        action_type = self.action_id.type
        action = self.env[action_type].browse(self.action_id.id)

        result = action.read()[0]
        if action_type != 'ir.actions.act_window':
            return result
        result.setdefault('context', '{}')

        # Open a specific record when res_id is provided in the context
        ctx = safe_eval(result['context'], {'user': self.env.user})
        if ctx.get('res_id'):
            result['res_id'] = ctx.pop('res_id')

        # disable log for automatic wizards
        ctx['disable_log'] = True

        result['context'] = ctx

        return result

    def action_open(self):
        """ Sets configuration wizard in TODO state"""
        return self.write({'state': 'open'})


class IrActionsActClient(models.Model):
    _name = 'ir.actions.client'
    _description = 'Client Action'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_client'
    _order = 'name'

    type = fields.Char(default='ir.actions.client')

    tag = fields.Char(string='Client action tag', required=True,
                      help="An arbitrary string, interpreted by the client"
                           " according to its own needs and wishes. There "
                           "is no central tag repository across clients.")
    target = fields.Selection([('current', 'Current Window'), ('new', 'New Window'), ('fullscreen', 'Full Screen'), ('main', 'Main action of Current Window')], default="current", string='Target Window')
    res_model = fields.Char(string='Destination Model', help="Optional model, mostly used for needactions.")
    context = fields.Char(string='Context Value', default="{}", required=True, help="Context dictionary as Python expression, empty by default (Default: {})")
    params = fields.Binary(compute='_compute_params', inverse='_inverse_params', string='Supplementary arguments',
                           help="Arguments sent to the client along with "
                                "the view tag")
    params_store = fields.Binary(string='Params storage', readonly=True, attachment=False)

    @api.depends('params_store')
    def _compute_params(self):
        self_bin = self.with_context(bin_size=False, bin_size_params_store=False)
        for record, record_bin in zip(self, self_bin):
            record.params = record_bin.params_store and safe_eval(record_bin.params_store, {'uid': self._uid})

    def _inverse_params(self):
        for record in self:
            params = record.params
            record.params_store = repr(params) if isinstance(params, dict) else params

    def _get_default_form_view(self):
        doc = super(IrActionsActClient, self)._get_default_form_view()
        params = doc.find(".//field[@name='params']")
        params.getparent().remove(params)
        params_store = doc.find(".//field[@name='params_store']")
        params_store.getparent().remove(params_store)
        return doc


    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "context", "params", "res_model", "tag", "target",
        }
