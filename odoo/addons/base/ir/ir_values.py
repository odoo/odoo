# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.tools import pickle

import logging
_logger = logging.getLogger(__name__)


EXCLUDED_FIELDS = set(('code',
    'report_sxw_content', 'report_rml_content', 'report_sxw', 'report_rml',
    'report_sxw_content_data', 'report_rml_content_data', 'search_view', ))

#: Possible slots to bind an action to with :meth:`~.set_action`
ACTION_SLOTS = [
    "client_action_multi",      # sidebar wizard action
    "client_print_multi",       # sidebar report printing button
    "client_action_relate",     # sidebar related link
    "tree_but_open",            # double-click on item in tree view
    "tree_but_action",          # deprecated: same as tree_but_open
]


class IrValues(models.Model):
    """Holds internal model-specific action bindings and user-defined default
       field values. definitions. This is a legacy internal model, mixing
       two different concepts, and will likely be updated or replaced in a
       future version by cleaner, separate models. You should not depend
       explicitly on it.

       The purpose of each ``ir.values`` entry depends on its type, defined
       by the ``key`` column:

        * 'default': user-defined default values, used when creating new
          records of this model:
        * 'action': binding of an action to a particular *action slot* of
          this model, making the action easily available in the user
          interface for this model.

       The ``key2`` column acts as a qualifier, further refining the type
       of the entry. The possible values are:

        * for 'default' entries: an optional condition restricting the
          cases where this particular default value will be applicable,
          or ``False`` for no condition
        * for 'action' entries: the ``key2`` qualifier is one of the available
          action slots, defining how this action can be invoked:

            * ``'client_print_multi'`` for report printing actions that will
              be available on views displaying items from this model
            * ``'client_action_multi'`` for assistants (wizards) actions
              that will be available in views displaying objects of this model
            * ``'client_action_relate'`` for links towards related documents
              that should be available in views displaying objects of this model
            * ``'tree_but_open'`` for actions that will be triggered when
              double-clicking an item from this model in a hierarchical tree view

       Each entry is specific to a model (``model`` column), and for ``'actions'``
       type, may even be made specific to a given record of that model when the
       ``res_id`` column contains a record ID (``False`` means it's global for
       all records).

       The content of the entry is defined by the ``value`` column, which may either
       contain an arbitrary value, or a reference string defining the action that
       should be executed.

       .. rubric:: Usage: default values
       
       The ``'default'`` entries are usually defined manually by the
       users, and set by their UI clients calling :meth:`~.set_default`.
       These default values are then automatically used by the
       ORM every time a new record is about to be created, i.e. when
       :meth:`~odoo.models.Model.default_get`
       or :meth:`~odoo.models.Model.create` are called.

       .. rubric:: Usage: action bindings

       Business applications will usually bind their actions during
       installation, and Odoo UI clients will apply them as defined,
       based on the list of actions included in the result of
       :meth:`~odoo.models.Model.fields_view_get`,
       or directly returned by explicit calls to :meth:`~.get_actions`.
    """
    _name = 'ir.values'

    name = fields.Char(required=True)
    model = fields.Char(string='Model Name', index=True, required=True,
                        help="Model to which this entry applies")

    # TODO: model_id and action_id should be read-write function fields
    model_id = fields.Many2one('ir.model', string='Model (change only)',
                               help="Model to which this entry applies - "
                                    "helper field for setting a model, will "
                                    "automatically set the correct model name")
    action_id = fields.Many2one('ir.actions.actions', string='Action (change only)',
                                help="Action bound to this entry - "
                                     "helper field for binding an action, will "
                                     "automatically set the correct reference")

    value = fields.Text(help="Default value (pickled) or reference to an action")
    value_unpickle = fields.Text(string='Default value or action reference',
                                 compute='_value_unpickle', inverse='_value_pickle')
    key = fields.Selection([('action', 'Action'), ('default', 'Default')],
                           string='Type', index=True, required=True, default='action',
                           help="- Action: an action attached to one slot of the given model\n"
                                "- Default: a default value for a model field")
    key2 = fields.Char(string='Qualifier', index=True, default='tree_but_open',
                       help="For actions, one of the possible action slots: \n"
                            "  - client_action_multi\n"
                            "  - client_print_multi\n"
                            "  - client_action_relate\n"
                            "  - tree_but_open\n"
                            "For defaults, an optional condition")
    res_id = fields.Integer(string='Record ID', index=True,
                            help="Database identifier of the record to which this applies. "
                                 "0 = for all records")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', index=True,
                              help="If set, action binding only applies for this user.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', index=True,
                                 help="If set, action binding only applies for this company")

    @api.depends('key', 'value')
    def _value_unpickle(self):
        for record in self:
            value = record.value
            if record.key == 'default' and value:
                # default values are pickled on the fly
                with tools.ignore(Exception):
                    value = str(pickle.loads(value))
            record.value_unpickle = value

    def _value_pickle(self):
        context = dict(self._context)
        context.pop(self.CONCURRENCY_CHECK_FIELD, None)
        for record in self.with_context(context):
            value = record.value_unpickle
            # Only char-like fields should be written directly. Other types should be converted to
            # their appropriate type first.
            if record.model in self.env and record.name in self.env[record.model]._fields:
                field = self.env[record.model]._fields[record.name]
                if field.type not in ['char', 'text', 'html', 'selection']:
                    value = literal_eval(value)
            if record.key == 'default':
                value = pickle.dumps(value)
            record.value = value

    @api.onchange('model_id')
    def onchange_object_id(self):
        if self.model_id:
            self.model = self.model_id.model

    @api.onchange('action_id')
    def onchange_action_id(self):
        if self.action_id:
            self.value_unpickle = self.action_id

    @api.model_cr_context
    def _auto_init(self):
        res = super(IrValues, self)._auto_init()
        tools.create_index(self._cr, 'ir_values_key_model_key2_res_id_user_id_idx',
                           self._table, ['key', 'model', 'key2', 'res_id', 'user_id'])
        return res

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(IrValues, self).create(vals)

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(IrValues, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(IrValues, self).unlink()

    @api.model
    @api.returns('self', lambda value: value.id)
    def set_default(self, model, field_name, value, for_all_users=True, company_id=False, condition=False):
        """Defines a default value for the given model and field_name. Any previous
           default for the same scope (model, field_name, value, for_all_users, company_id, condition)
           will be replaced and lost in the process.

           Defaults can be later retrieved via :meth:`~.get_defaults`, which will return
           the highest priority default for any given field. Defaults that are more specific
           have a higher priority, in the following order (highest to lowest):

               * specific to user and company
               * specific to user only
               * specific to company only
               * global to everyone

           :param string model: model name
           :param string field_name: field name to which the default applies
           :param value: the default field value to set
           :type value: any serializable Python value
           :param bool for_all_users: whether the default should apply to everybody or only
                                      the user calling the method
           :param int company_id: optional ID of the company to which the default should
                                  apply. If omitted, the default will be global. If True
                                  is passed, the current user's company will be used.
           :param string condition: optional condition specification that can be used to
                                    restrict the applicability of the default values
                                    (e.g. based on another field's value). This is an
                                    opaque string as far as the API is concerned, but client
                                    stacks typically use single-field conditions in the
                                    form ``'key=stringified_value'``.
                                    (Currently, the condition is trimmed to 200 characters,
                                    so values that share the same first 200 characters always
                                    match)
           :return: the newly created ir.values entry
        """
        if isinstance(value, unicode):
            value = value.encode('utf8')
        if company_id is True:
            # should be company-specific, need to get company id
            company_id = self.env.user.company_id.id

        # check consistency of model, field_name and value
        try:
            field = self.env[model]._fields[field_name]
            field.convert_to_cache(value, self.browse())
        except KeyError:
            _logger.warning("Invalid field %s.%s", model, field_name)
        except Exception:
            raise ValidationError(_("Invalid value for %s.%s: %s") % (model, field_name, value))

        # remove existing defaults for the same scope
        search_criteria = [
            ('key', '=', 'default'),
            ('key2', '=', condition and condition[:200]),
            ('model', '=', model),
            ('name', '=', field_name),
            ('user_id', '=', False if for_all_users else self._uid),
            ('company_id', '=', company_id)
        ]
        self.search(search_criteria).unlink()

        return self.create({
            'name': field_name,
            'value': pickle.dumps(value),
            'model': model,
            'key': 'default',
            'key2': condition and condition[:200],
            'user_id': False if for_all_users else self._uid,
            'company_id': company_id,
        })

    @api.model
    def get_default(self, model, field_name, for_all_users=True, company_id=False, condition=False):
        """ Return the default value defined for model, field_name, users, company and condition.
            Return ``None`` if no such default exists.
        """
        search_criteria = [
            ('key', '=', 'default'),
            ('key2', '=', condition and condition[:200]),
            ('model', '=', model),
            ('name', '=', field_name),
            ('user_id', '=', False if for_all_users else self._uid),
            ('company_id', '=', company_id)
        ]
        defaults = self.search(search_criteria)
        return pickle.loads(defaults.value.encode('utf-8')) if defaults else None

    @api.model
    def get_defaults(self, model, condition=False):
        """Returns any default values that are defined for the current model and user,
           (and match ``condition``, if specified), previously registered via
           :meth:`~.set_default`.

           Defaults are global to a model, not field-specific, but an optional
           ``condition`` can be provided to restrict matching default values
           to those that were defined for the same condition (usually based
           on another field's value).

           Default values also have priorities depending on whom they apply
           to: only the highest priority value will be returned for any
           field. See :meth:`~.set_default` for more details.

           :param string model: model name
           :param string condition: optional condition specification that can be used to
                                    restrict the applicability of the default values
                                    (e.g. based on another field's value). This is an
                                    opaque string as far as the API is concerned, but client
                                    stacks typically use single-field conditions in the
                                    form ``'key=stringified_value'``.
                                    (Currently, the condition is trimmed to 200 characters,
                                    so values that share the same first 200 characters always
                                    match)
           :return: list of default values tuples of the form ``(id, field_name, value)``
                    (``id`` is the ID of the default entry, usually irrelevant)
        """
        # use a direct SQL query for performance reasons,
        # this is called very often
        query = """ SELECT v.id, v.name, v.value FROM ir_values v
                    LEFT JOIN res_users u ON (v.user_id = u.id)
                    WHERE v.key = %%s AND v.model = %%s
                        AND (v.user_id = %%s OR v.user_id IS NULL)
                        AND (v.company_id IS NULL OR
                             v.company_id = (SELECT company_id FROM res_users WHERE id = %%s)
                            )
                    %s
                    ORDER BY v.user_id, v.company_id, v.id"""
        params = ('default', model, self._uid, self._uid)
        if condition:
            query = query % 'AND v.key2 = %s'
            params += (condition[:200],)
        else:
            query = query % 'AND v.key2 IS NULL'
        self._cr.execute(query, params)

        # keep only the highest priority default for each field
        defaults = {}
        for row in self._cr.dictfetchall():
            value = pickle.loads(row['value'].encode('utf-8'))
            defaults.setdefault(row['name'], (row['id'], row['name'], value))
        return defaults.values()

    # use ormcache: this is called a lot by BaseModel.default_get()!
    @api.model
    @tools.ormcache('self._uid', 'model', 'condition')
    def get_defaults_dict(self, model, condition=False):
        """ Returns a dictionary mapping field names with their corresponding
            default value. This method simply improves the returned value of
            :meth:`~.get_defaults`.
        """
        return dict((f, v) for i, f, v in self.get_defaults(model, condition))

    @api.model
    @api.returns('self', lambda value: value.id)
    def set_action(self, name, action_slot, model, action, res_id=False):
        """Binds an the given action to the given model's action slot - for later
           retrieval via :meth:`~.get_actions`. Any existing binding of the same action
           to the same slot is first removed, allowing an update of the action's name.
           See the class description for more details about the various action
           slots: :class:`~ir_values`.

           :param string name: action label, usually displayed by UI client
           :param string action_slot: the action slot to which the action should be
                                      bound to - one of ``client_action_multi``,
                                      ``client_print_multi``, ``client_action_relate``,
                                      ``tree_but_open``.
           :param string model: model name
           :param string action: action reference, in the form ``'model,id'``
           :param int res_id: optional record id - will bind the action only to a
                              specific record of the model, not all records.
           :return: the newly created ir.values entry
        """
        assert isinstance(action, basestring) and ',' in action, \
               'Action definition must be an action reference, e.g. "ir.actions.act_window,42"'
        assert action_slot in ACTION_SLOTS, \
               'Action slot (%s) must be one of: %r' % (action_slot, ACTION_SLOTS)

        # remove existing action definition of same slot and value
        search_criteria = [
            ('key', '=', 'action'),
            ('key2', '=', action_slot),
            ('model', '=', model),
            ('res_id', '=', res_id or 0),  # int field -> NULL == 0
            ('value', '=', action),
        ]
        self.search(search_criteria).unlink()

        return self.create({
            'key': 'action',
            'key2': action_slot,
            'model': model,
            'res_id': res_id,
            'name': name,
            'value': action,
        })

    @api.model
    @tools.ormcache_context('self._uid', 'action_slot', 'model', 'res_id', keys=('lang',))
    def get_actions(self, action_slot, model, res_id=False):
        """Retrieves the list of actions bound to the given model's action slot.
           See the class description for more details about the various action
           slots: :class:`~.ir_values`.

           :param string action_slot: the action slot to which the actions should be
                                      bound to - one of ``client_action_multi``,
                                      ``client_print_multi``, ``client_action_relate``,
                                      ``tree_but_open``.
           :param string model: model name
           :param int res_id: optional record id - will bind the action only to a
                              specific record of the model, not all records.
           :return: list of action tuples of the form ``(id, name, action_def)``,
                    where ``id`` is the ID of the default entry, ``name`` is the
                    action label, and ``action_def`` is a dict containing the
                    action definition as obtained by calling
                    :meth:`~odoo.models.Model.read` on the action record.
        """
        assert action_slot in ACTION_SLOTS, 'Illegal action slot value: %s' % action_slot
        # use a direct SQL query for performance reasons,
        # this is called very often
        query = """ SELECT v.id, v.name, v.value FROM ir_values v
                    WHERE v.key = %s AND v.key2 = %s AND v.model = %s
                        AND (v.res_id = %s OR v.res_id IS NULL OR v.res_id = 0)
                    ORDER BY v.id """
        self._cr.execute(query, ('action', action_slot, model, res_id or None))

        # map values to their corresponding action record
        actions = []
        for id, name, value in self._cr.fetchall():
            if not value:
                continue                # skip if undefined
            action_model, action_id = value.split(',')
            if action_model not in self.env:
                continue                # unknown model? skip it!
            action = self.env[action_model].browse(int(action_id))
            actions.append((id, name, action))

        # process values and their action
        results = {}
        for id, name, action in actions:
            fields = [field for field in action._fields if field not in EXCLUDED_FIELDS]
            # FIXME: needs cleanup
            try:
                action_def = {
                    field: action._fields[field].convert_to_read(action[field], action)
                    for field in fields
                }
                if action._name in ('ir.actions.report.xml', 'ir.actions.act_window'):
                    if action.groups_id and not action.groups_id & self.env.user.groups_id:
                        if name == 'Menuitem':
                            raise AccessError(_('You do not have the permission to perform this operation!!!'))
                        continue
                # keep only the last action registered for each action name
                results[name] = (id, name, action_def)
            except (AccessError, MissingError):
                continue
        return sorted(results.values())
