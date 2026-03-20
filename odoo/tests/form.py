# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.form` provides an implementation of a client form
view for server-side unit tests.
"""
from __future__ import annotations

import ast
import collections
import collections.abc
import itertools
import logging
from datetime import datetime, date

from lxml import etree

from odoo import api, fields
from odoo.models import BaseModel
from odoo.fields import Command
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

MODIFIER_ALIASES = {'1': 'True', '0': 'False'}


class Form:
    """ Server-side form view implementation (partial)

    Implements much of the "form view" manipulation flow, such that server-side
    tests can more properly reflect the behaviour which would be observed when
    manipulating the interface:

    * call the relevant onchanges on "creation";
    * call the relevant onchanges on setting fields;
    * properly handle defaults & onchanges around x2many fields.

    Saving the form returns the current record (which means the created record
    if in creation mode). It can also be accessed as ``form.record``, but only
    when the form has no pending changes.

    Regular fields can just be assigned directly to the form. In the case
    of :class:`~odoo.fields.Many2one` fields, one can assign a recordset::

        # empty recordset => creation mode
        f = Form(self.env['sale.order'])
        f.partner_id = a_partner
        so = f.save()

    One can also use the form as a context manager to create or edit a record.
    The changes are automatically saved at the end of the scope::

        with Form(self.env['sale.order']) as f1:
            f1.partner_id = a_partner
            # f1 is saved here

        # retrieve the created record
        so = f1.record

        # call Form on record => edition mode
        with Form(so) as f2:
            f2.payment_term_id = env.ref('account.account_payment_term_15days')
            # f2 is saved here

    For :class:`~odoo.fields.Many2many` fields, the field itself is a
    :class:`~odoo.tests.common.M2MProxy` and can be altered by adding or
    removing records::

        with Form(user) as u:
            u.group_ids.add(env.ref('account.group_account_manager'))
            u.group_ids.remove(id=env.ref('base.group_portal').id)

    Finally :class:`~odoo.fields.One2many` are reified as :class:`~O2MProxy`.

    Because the :class:`~odoo.fields.One2many` only exists through its parent,
    it is manipulated more directly by creating "sub-forms" with
    the :meth:`~O2MProxy.new` and :meth:`~O2MProxy.edit` methods. These would
    normally be used as context managers since they get saved in the parent
    record::

        with Form(so) as f3:
            f.partner_id = a_partner
            # add support
            with f3.order_line.new() as line:
                line.product_id = env.ref('product.product_product_2')
            # add a computer
            with f3.order_line.new() as line:
                line.product_id = env.ref('product.product_product_3')
            # we actually want 5 computers
            with f3.order_line.edit(1) as line:
                line.product_uom_qty = 5
            # remove support
            f3.order_line.remove(index=0)
            # SO is saved here

    :param record: empty or singleton recordset. An empty recordset will put
                   the view in "creation" mode from default values, while a
                   singleton will put it in "edit" mode and only load the
                   view's data.
    :param view: the id, xmlid or actual view object to use for onchanges and
                 view constraints. If none is provided, simply loads the
                 default view for the model.

    .. versionadded:: 12.0
    """
    def __init__(self, record: BaseModel, view: None | int | str | BaseModel = None) -> None:
        assert isinstance(record, BaseModel)
        assert len(record) <= 1

        # use object.__setattr__ to bypass Form's override of __setattr__
        object.__setattr__(self, '_record', record)
        object.__setattr__(self, '_env', record.env)

        # determine view and process it
        if isinstance(view, BaseModel):
            assert view._name == 'ir.ui.view', "the view parameter must be a view id, xid or record, got %s" % view
            view_id = view.id
        elif isinstance(view, str):
            view_id = record.env.ref(view).id
        else:
            view_id = view or False

        views = record.get_views([(view_id, 'form')])
        object.__setattr__(self, '_models_info', views['models'])
        # self._models_info = {model_name: {fields: {field_name: field_info}}}
        tree = etree.fromstring(views['views']['form']['arch'])
        view = self._process_view(tree, record)
        object.__setattr__(self, '_view', view)
        # self._view = {
        #     'tree': view_arch_etree,
        #     'fields': {field_name: field_info},
        #     'fields_spec': web_read_fields_spec,
        #     'modifiers': {field_name: {modifier: expression}},
        #     'contexts': {field_name: field_context_str},
        #     'onchange': onchange_spec,
        # }

        # determine record values
        object.__setattr__(self, '_values', UpdateDict())
        if record:
            self._init_from_record()
        else:
            self._init_from_defaults()

    @classmethod
    def from_action(cls, env: api.Environment, action: dict) -> Form:
        assert action['type'] == 'ir.actions.act_window', \
            f"only window actions are valid, got {action['type']}"
        # ensure the first-requested view is a form view
        if views := action.get('views'):
            assert views[0][1] == 'form', \
                f"the actions dict should have a form as first view, got {views[0][1]}"
            view_id = views[0][0]
        else:
            view_mode = action.get('view_mode', '')
            if not view_mode.startswith('form'):
                raise ValueError(f"The actions dict should have a form first view mode, got {view_mode}")
            view_id = action.get('view_id')
            if view_id and ',' in view_mode:
                raise ValueError(f"A `view_id` is only valid if the action has a single `view_mode`, got {view_mode}")
        context = action.get('context', {})
        if isinstance(context, str):
            context = ast.literal_eval(context)
        record = env[action['res_model']]\
            .with_context(context)\
            .browse(action.get('res_id'))

        return cls(record, view_id)

    def _process_view(self, tree, model, level=2):
        """ Post-processes to augment the view_get with:
        * an id field (may not be present if not in the view but needed)
        * pre-processed modifiers
        * pre-processed onchanges list
        """
        fields = {'id': {'type': 'id'}}
        fields_spec = {}
        modifiers = {'id': {'required': 'False', 'readonly': 'True'}}
        contexts = {}
        # retrieve <field> nodes at the current level
        flevel = tree.xpath('count(ancestor::field)')
        daterange_field_names = {}
        field_infos = self._models_info.get(model._name, {}).get("fields", {})

        for node in tree.xpath(f'.//field[count(ancestor::field) = {flevel}]'):
            field_name = node.get('name')

            # add field_info into fields
            field_info = field_infos.get(field_name) or {'type': None}
            fields[field_name] = field_info
            fields_spec[field_name] = field_spec = {}

            # determine modifiers
            field_modifiers = {}
            for attr in ('required', 'readonly', 'invisible', 'column_invisible'):
                # use python field attribute as default value
                default = attr in ('required', 'readonly') and field_info.get(attr, False)
                expr = node.get(attr) or str(default)
                field_modifiers[attr] = MODIFIER_ALIASES.get(expr, expr)

            # Combine the field modifiers with its ancestor modifiers with an
            # OR: A field is invisible if its own invisible modifier is True OR
            # if one of its ancestor invisible modifier is True
            for ancestor in node.xpath(f'ancestor::*[@invisible][count(ancestor::field) = {flevel}]'):
                modifier = 'invisible'
                expr = ancestor.get(modifier)
                if expr == 'True' or field_modifiers[modifier] == 'True':
                    field_modifiers[modifier] = 'True'
                if expr == 'False':
                    field_modifiers[modifier] = field_modifiers[modifier]
                elif field_modifiers[modifier] == 'False':
                    field_modifiers[modifier] = expr
                else:
                    field_modifiers[modifier] = f'({expr}) or ({field_modifiers[modifier]})'

            # merge field_modifiers into modifiers[field_name]
            if field_name in modifiers:
                # The field is several times in the view, combine the modifier
                # expression with an AND: a field is X if all occurences of the
                # field in the view are X.
                for modifier, expr in modifiers[field_name].items():
                    if expr == 'False' or field_modifiers[modifier] == 'False':
                        field_modifiers[modifier] = 'False'
                    if expr == 'True':
                        field_modifiers[modifier] = field_modifiers[modifier]
                    elif field_modifiers[modifier] == 'True':
                        field_modifiers[modifier] = expr
                    else:
                        field_modifiers[modifier] = f'({expr}) and ({field_modifiers[modifier]})'

            modifiers[field_name] = field_modifiers

            # determine context
            ctx = node.get('context')
            if ctx:
                contexts[field_name] = ctx
                field_spec['context'] = get_static_context(ctx)

            # FIXME: better widgets support
            # NOTE: selection breaks because of m2o widget=selection
            if node.get('widget') in ['many2many']:
                field_info['type'] = node.get('widget')
            elif node.get('widget') == 'daterange':
                options = ast.literal_eval(node.get('options', '{}'))
                related_field = options.get('start_date_field') or options.get('end_date_field')
                daterange_field_names[related_field] = field_name

            # determine subview to use for edition
            if field_info['type'] == 'one2many':
                if level:
                    field_info['invisible'] = field_modifiers.get('invisible')
                    edition_view = self._get_one2many_edition_view(field_info, node, level)
                    field_info['edition_view'] = edition_view
                    field_spec['fields'] = edition_view['fields_spec']
                else:
                    # this trick enables the following invariant: every one2many
                    # field has some 'edition_view' in its info dict
                    field_info['type'] = 'many2many'

        for related_field, start_field in daterange_field_names.items():
            # If the field doesn't exist in the view add it implicitly
            if related_field not in modifiers:
                field_info = field_infos.get(related_field) or {'type': None}
                fields[related_field] = field_info
                fields_spec[related_field] = {}
                modifiers[related_field] = {
                    'required': field_info.get('required', False),
                    'readonly': field_info.get('readonly', False),
                }
            modifiers[related_field]['invisible'] = modifiers[start_field].get('invisible', False)

        return {
            'tree': tree,
            'fields': fields,
            'fields_spec': fields_spec,
            'modifiers': modifiers,
            'contexts': contexts,
            'onchange': model._onchange_spec({'arch': etree.tostring(tree)}),
        }

    def _get_one2many_edition_view(self, field_info, node, level):
        """ Return a suitable view for editing records into a one2many field. """
        submodel = self._env[field_info['relation']]

        # by simplicity, ensure we always have tree and form views
        views = {
            view.tag: view for view in node.xpath('./*[descendant::field]')
        }
        for view_type in ['list', 'form']:
            if view_type in views:
                continue
            if field_info['invisible'] == 'True':
                # add an empty view
                views[view_type] = etree.Element(view_type)
                continue
            refs = self._env['ir.ui.view']._get_view_refs(node)
            subviews = submodel.with_context(**refs).get_views([(None, view_type)])
            subnode = etree.fromstring(subviews['views'][view_type]['arch'])
            views[view_type] = subnode
            node.append(subnode)
            for model_name, value in subviews['models'].items():
                model_info = self._models_info.setdefault(model_name, {})
                if "fields" not in model_info:
                    model_info["fields"] = {}
                model_info["fields"].update(value["fields"])

        # pick the first editable subview
        view_type = next(
            vtype for vtype in node.get('mode', 'list').split(',') if vtype != 'form'
        )
        if not (view_type == 'list' and views['list'].get('editable')):
            view_type = 'form'

        # don't recursively process o2ms in o2ms
        return self._process_view(views[view_type], submodel, level=level-1)

    def __str__(self):
        return f"<{type(self).__name__} {self._record}>"

    def _init_from_record(self):
        """ Initialize the form for an existing record. """
        assert self._record.id, "editing unstored records is not supported"
        self._values.clear()

        [record_values] = self._record.web_read(self._view['fields_spec'])
        self._env.flush_all()
        self._env.clear()  # discard cache and pending recomputations

        values = convert_read_to_form(record_values, self._view['fields'])
        self._values.update(values)

    def _init_from_defaults(self):
        """ Initialize the form for a new record. """
        vals = self._values
        vals['id'] = False

        # call onchange with no field; this retrieves default values, applies
        # onchanges and return the result
        self._perform_onchange()
        # mark all fields as modified
        self._values._changed.update(self._view['fields'])

    def __getattr__(self, field_name):
        """ Return the current value of the given field. """
        return self[field_name]

    def __getitem__(self, field_name):
        """ Return the current value of the given field. """
        field_info = self._view['fields'].get(field_name)
        assert field_info is not None, f"{field_name!r} was not found in the view"

        value = self._values[field_name]
        if field_info['type'] == 'many2one':
            Model = self._env[field_info['relation']]
            return Model.browse(value)
        elif field_info['type'] == 'one2many':
            return O2MProxy(self, field_name)
        elif field_info['type'] == 'many2many':
            return M2MProxy(self, field_name)
        return value

    def __setattr__(self, field_name, value):
        """ Set the given field to the given value, and proceed with the expected onchanges. """
        self[field_name] = value

    def __setitem__(self, field_name, value):
        """ Set the given field to the given value, and proceed with the expected onchanges. """
        field_info = self._view['fields'].get(field_name)
        assert field_info is not None, f"{field_name!r} was not found in the view"
        assert field_info['type'] != 'one2many', "Can't set an one2many field directly, use its proxy instead"
        assert not self._get_modifier(field_name, 'readonly'), f"can't write on readonly field {field_name!r}"
        assert not self._get_modifier(field_name, 'invisible'), f"can't write on invisible field {field_name!r}"

        if field_info['type'] == 'many2many':
            return M2MProxy(self, field_name).set(value)

        if field_info['type'] == 'many2one':
            assert isinstance(value, BaseModel) and value._name == field_info['relation']
            value = value.id

        self._values[field_name] = value
        self._perform_onchange(field_name)

    def _get_modifier(self, field_name, modifier, *, view=None, vals=None):
        if view is None:
            view = self._view

        expr = view['modifiers'][field_name].get(modifier, False)
        if isinstance(expr, bool):
            return expr
        if expr in ('True', 'False'):
            return expr == 'True'

        if vals is None:
            vals = self._values

        eval_context = self._get_eval_context(vals)

        return bool(safe_eval(expr, eval_context))

    def _get_context(self, field_name):
        """ Return the context of a given field. """
        context_str = self._view['contexts'].get(field_name)
        if not context_str:
            return {}
        eval_context = self._get_eval_context()
        return safe_eval(context_str, eval_context)

    def _get_eval_context(self, values=None):
        """ Return the context dict to eval something. """
        context = {
            'id': self._record.id,
            'active_id': self._record.id,
            'active_ids': self._record.ids,
            'active_model': self._record._name,
            'current_date': date.today().strftime("%Y-%m-%d"),
            **self._env.context,
        }
        if values is None:
            values = self._get_all_values()
        return {
            **context,
            'context': context,
            **values,
        }

    def _get_all_values(self):
        """ Return the values of all fields. """
        return self._get_values('all')

    def __enter__(self):
        """ This makes the Form usable as a context manager. """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self.save()

    def save(self):
        """ Save the form (if necessary) and return the current record:

        * does not save ``readonly`` fields;
        * does not save unmodified fields (during edition) — any assignment
          or onchange return marks the field as modified, even if set to its
          current value.

        When nothing must be saved, it simply returns the current record.

        :raises AssertionError: if the form has any unfilled required field
        """
        values = self._get_save_values()
        if not self._record or values:
            # save and reload
            [record_values] = self._record.web_save(values, self._view['fields_spec'])
            self._env.flush_all()
            self._env.clear()  # discard cache and pending recomputations

            if not self._record:
                record = self._record.browse(record_values['id'])
                object.__setattr__(self, '_record', record)

            values = convert_read_to_form(record_values, self._view['fields'])
            self._values.clear()
            self._values.update(values)

        return self._record

    @property
    def record(self):
        """ Return the record being edited by the form. This attribute is
        readonly and can only be accessed when the form has no pending changes.
        """
        assert not self._values._changed
        return self._record

    def _get_save_values(self):
        """ Validate and return field values modified since load/save. """
        return self._get_values('save')

    def _get_values(self, mode, values=None, view=None, modifiers_values=None, parent_link=None):
        """ Validate & extract values, recursively in order to handle o2ms properly.

        :param mode: can be ``"save"`` (validate and return non-readonly modified fields),
            ``"onchange"`` (return modified fields) or ``"all"`` (return all field values)
        :param UpdateDict values: values of the record to extract
        :param view: view info
        :param dict modifiers_values: defaults to ``values``, but o2ms need some additional massaging
        :param parent_link: optional field representing "parent"
        """
        assert mode in ('save', 'onchange', 'all')

        if values is None:
            values = self._values
        if view is None:
            view = self._view
        assert isinstance(values, UpdateDict)

        modifiers_values = modifiers_values or values

        result = {}
        for field_name, field_info in view['fields'].items():
            if field_name == 'id' or field_name not in values:
                continue

            value = values[field_name]

            # note: maybe `invisible` should not skip `required` if model attribute
            if (
                mode == 'save'
                and value is False
                and field_name != parent_link
                and field_info['type'] != 'boolean'
                and not self._get_modifier(field_name, 'invisible', view=view, vals=modifiers_values)
                and not self._get_modifier(field_name, 'column_invisible', view=view, vals=modifiers_values)
                and self._get_modifier(field_name, 'required', view=view, vals=modifiers_values)
            ):
                raise AssertionError(f"{field_name} is a required field ({view['modifiers'][field_name]})")

            # skip unmodified fields unless all_fields
            if mode in ('save', 'onchange') and field_name not in values._changed:
                continue

            if mode == 'save' and self._get_modifier(field_name, 'readonly', view=view, vals=modifiers_values):
                field_node = next(
                    node
                    for node in view['tree'].iter('field')
                    if node.get('name') == field_name
                )
                if not field_node.get('force_save'):
                    continue

            if field_info['type'] == 'one2many':
                if mode == 'all':
                    # in the context of an eval, format it as a list of ids
                    value = list(value)
                else:
                    subview = field_info['edition_view']
                    value = value.to_commands(lambda vals: self._get_values(
                        mode, vals, subview,
                        modifiers_values={'id': False, **vals, 'parent': Dotter(values)},
                        # related o2m don't have a relation_field
                        parent_link=field_info.get('relation_field'),
                    ))

            elif field_info['type'] == 'many2many':
                if mode == 'all':
                    # in the context of an eval, format it as a list of ids
                    value = list(value)
                else:
                    value = value.to_commands()

            result[field_name] = value

        return result

    def _perform_onchange(self, field_name=None):
        assert field_name is None or isinstance(field_name, str)

        # marks onchange source as changed
        if field_name:
            field_names = [field_name]
            self._values._changed.add(field_name)
        else:
            field_names = []

        # skip calling onchange() if there's no on_change on the field
        if field_name and not self._view['onchange'][field_name]:
            return

        record = self._record

        # if the onchange is triggered by a field, add the context of that field
        if field_name:
            context = self._get_context(field_name)
            if context:
                record = record.with_context(**context)

        values = self._get_onchange_values()
        result = record.onchange(values, field_names, self._view['fields_spec'])
        self._env.flush_all()
        self._env.clear()  # discard cache and pending recomputations

        if w := result.get('warning'):
            if isinstance(w, collections.abc.Mapping) and w.keys() >= {'title', 'message'}:
                _logger.getChild('onchange').warning("%(title)s %(message)s", w)
            else:
                _logger.getChild('onchange').error(
                    "received invalid warning %r from onchange on %r (should be a dict with keys `title` and `message`)",
                    w,
                    field_names,
                )

        if not field_name:
            # fill in whatever fields are still missing with falsy values
            self._values.update({
                field_name: _cleanup_from_default(field_info['type'], False)
                for field_name, field_info in self._view['fields'].items()
                if field_name not in self._values
            })

        if result.get('value'):
            self._apply_onchange(result['value'])

        return result

    def _get_onchange_values(self):
        """ Return modified field values for onchange. """
        return self._get_values('onchange')

    def _apply_onchange(self, values):
        self._apply_onchange_(self._values, self._view['fields'], values)

    def _apply_onchange_(self, values, fields, onchange_values):
        assert isinstance(values, UpdateDict)
        for fname, value in onchange_values.items():
            field_info = fields[fname]
            if field_info['type'] in ('one2many', 'many2many'):
                subfields = {}
                if field_info['type'] == 'one2many':
                    subfields = field_info['edition_view']['fields']
                field_value = values[fname]
                for cmd in value:
                    match cmd[0]:
                        case Command.CREATE:
                            vals = UpdateDict(convert_read_to_form(dict.fromkeys(subfields, False), subfields))
                            self._apply_onchange_(vals, subfields, cmd[2])
                            field_value.create(vals)
                        case Command.UPDATE:
                            vals = field_value.get_vals(cmd[1])
                            self._apply_onchange_(vals, subfields, cmd[2])
                        case Command.DELETE | Command.UNLINK:
                            field_value.remove(cmd[1])
                        case Command.LINK:
                            field_value.add(cmd[1], convert_read_to_form(cmd[2], subfields))
                        case c:
                            raise ValueError(f"Unexpected onchange() o2m command {c!r}")
            else:
                values[fname] = value
            values._changed.add(fname)


class O2MForm(Form):
    # noinspection PyMissingConstructor
    # pylint: disable=super-init-not-called
    def __init__(self, proxy, index=None):
        model = proxy._model
        object.__setattr__(self, '_proxy', proxy)
        object.__setattr__(self, '_index', index)

        object.__setattr__(self, '_record', model)
        object.__setattr__(self, '_env', model.env)

        object.__setattr__(self, '_models_info', proxy._form._models_info)
        object.__setattr__(self, '_view', proxy._field_info['edition_view'])

        object.__setattr__(self, '_values', UpdateDict())
        if index is None:
            self._init_from_defaults()
        else:
            vals = proxy._records[index]
            self._values.update(vals)
            if vals.get('id'):
                object.__setattr__(self, '_record', model.browse(vals['id']))

    def _get_modifier(self, field_name, modifier, *, view=None, vals=None):
        if modifier != 'required' and self._proxy._form._get_modifier(self._proxy._field, modifier):
            return True
        return super()._get_modifier(field_name, modifier, view=view, vals=vals)

    def _get_eval_context(self, values=None):
        eval_context = super()._get_eval_context(values)
        eval_context['parent'] = Dotter(self._proxy._form._values)
        return eval_context

    def _get_onchange_values(self):
        values = super()._get_onchange_values()
        # computed o2m may not have a relation_field(?)
        field_info = self._proxy._field_info
        if 'relation_field' in field_info:  # note: should be fine because not recursive
            parent_form = self._proxy._form
            parent_values = parent_form._get_onchange_values()
            if parent_form._record.id:
                parent_values['id'] = parent_form._record.id
            values[field_info['relation_field']] = parent_values
        return values

    def save(self):
        proxy = self._proxy
        field_value = proxy._form._values[proxy._field]
        values = self._get_save_values()
        if self._index is None:
            field_value.create(values)
        else:
            id_ = field_value[self._index]
            field_value.update(id_, values)

        proxy._form._perform_onchange(proxy._field)

    def _get_save_values(self):
        """ Validate and return field values modified since load/save. """
        values = UpdateDict(self._values)

        for field_name in self._view['fields']:
            if self._get_modifier(field_name, 'required') and not (
                self._get_modifier(field_name, 'column_invisible')
                or self._get_modifier(field_name, 'invisible')
            ):
                assert values[field_name] is not False, f"{field_name!r} is a required field"

        return values


class UpdateDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changed = set()
        if args and isinstance(args[0], UpdateDict):
            self._changed.update(args[0]._changed)

    def __repr__(self):
        items = [
            f"{key!r}{'*' if key in self._changed else ''}: {val!r}"
            for key, val in self.items()
        ]
        return f"{{{', '.join(items)}}}"

    def changed_items(self):
        return (
            (k, v) for k, v in self.items()
            if k in self._changed
        )

    def update(self, *args, **kw):
        super().update(*args, **kw)
        if args and isinstance(args[0], UpdateDict):
            self._changed.update(args[0]._changed)

    def clear(self):
        super().clear()
        self._changed.clear()


class X2MValue(collections.abc.Sequence):
    """ The value of a one2many field, with the API of a sequence of record ids. """
    _virtual_seq = itertools.count()

    def __init__(self, iterable_of_vals=()):
        self._data = {vals['id']: UpdateDict(vals) for vals in iterable_of_vals}

    def __repr__(self):
        return repr(self._data)

    def __contains__(self, id_):
        return id_ in self._data

    def __getitem__(self, index):
        return list(self._data)[index]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        # this enables to compare self with a list
        return list(self) == other

    def get_vals(self, id_):
        return self._data[id_]

    def add(self, id_, vals):
        assert id_ not in self._data
        self._data[id_] = UpdateDict(vals)

    def remove(self, id_):
        self._data.pop(id_)

    def clear(self):
        self._data.clear()

    def create(self, vals):
        id_ = f'virtual_{next(self._virtual_seq)}'
        create_vals = UpdateDict(vals)
        create_vals._changed.update(vals)
        self._data[id_] = create_vals

    def update(self, id_, changes, changed=()):
        vals = self._data[id_]
        vals.update(changes)
        vals._changed.update(changed)

    def to_list_of_vals(self):
        return list(self._data.values())


class O2MValue(X2MValue):
    def __init__(self, iterable_of_vals=()):
        super().__init__(iterable_of_vals)
        self._given = list(self._data)

    def to_commands(self, convert_values=lambda vals: vals):
        given = set(self._given)
        result = []
        for id_, vals in self._data.items():
            if isinstance(id_, str) and id_.startswith('virtual_'):
                result.append((Command.CREATE, id_, convert_values(vals)))
                continue
            if id_ not in given:
                result.append(Command.link(id_))
            if vals._changed:
                result.append(Command.update(id_, convert_values(vals)))
        for id_ in self._given:
            if id_ not in self._data:
                result.append(Command.delete(id_))
        return result


class M2MValue(X2MValue):
    def __init__(self, iterable_of_vals=()):
        super().__init__(iterable_of_vals)
        self._given = list(self._data)

    def to_commands(self):
        given = set(self._given)
        result = []
        for id_, vals in self._data.items():
            if isinstance(id_, str) and id_.startswith('virtual_'):
                result.append((Command.CREATE, id_, {
                    key: val.to_commands() if isinstance(val, X2MValue) else val
                    for key, val in vals.changed_items()
                }))
                continue
            if id_ not in given:
                result.append(Command.link(id_))
            if vals._changed:
                result.append(Command.update(id_, {
                    key: val.to_commands() if isinstance(val, X2MValue) else val
                    for key, val in vals.changed_items()
                }))
        for id_ in self._given:
            if id_ not in self._data:
                result.append(Command.unlink(id_))
        return result


class X2MProxy:
    """ A proxy represents the value of an x2many field, but not directly.
    Instead, it provides an API to add, remove or edit records in the value.
    """
    _form = None        # Form containing the corresponding x2many field
    _field = None       # name of the x2many field
    _field_info = None  # field info

    def __init__(self, form, field_name):
        self._form = form
        self._field = field_name
        self._field_info = form._view['fields'][field_name]
        self._field_value = form._values[field_name]

    @property
    def ids(self):
        return list(self._field_value)

    def _assert_editable(self):
        assert not self._form._get_modifier(self._field, 'readonly'), f'field {self._field!r} is not editable'
        assert not self._form._get_modifier(self._field, 'invisible'), f'field {self._field!r} is not visible'


class O2MProxy(X2MProxy):
    """ Proxy object for editing the value of a one2many field. """
    def __len__(self):
        return len(self._field_value)

    @property
    def _model(self):
        model = self._form._env[self._field_info['relation']]
        context = self._form._get_context(self._field)
        if context:
            model = model.with_context(**context)
        return model

    @property
    def _records(self):
        return self._field_value.to_list_of_vals()

    def new(self):
        """ Returns a :class:`Form` for a new
        :class:`~odoo.fields.One2many` record, properly initialised.

        The form is created from the list view if editable, or the field's
        form view otherwise.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        return O2MForm(self)

    def edit(self, index):
        """ Returns a :class:`Form` to edit the pre-existing
        :class:`~odoo.fields.One2many` record.

        The form is created from the list view if editable, or the field's
        form view otherwise.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        return O2MForm(self, index)

    def remove(self, index):
        """ Removes the record at ``index`` from the parent form.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        self._field_value.remove(self._field_value[index])
        self._form._perform_onchange(self._field)


class M2MProxy(X2MProxy, collections.abc.Sequence):
    """ Proxy object for editing the value of a many2many field.

    Behaves as a :class:`~collection.Sequence` of recordsets, can be
    indexed or sliced to get actual underlying recordsets.
    """
    def __getitem__(self, index):
        comodel_name = self._field_info['relation']
        return self._form._env[comodel_name].browse(self._field_value[index])

    def __len__(self):
        return len(self._field_value)

    def __iter__(self):
        comodel_name = self._field_info['relation']
        records = self._form._env[comodel_name].browse(self._field_value)
        return iter(records)

    def __contains__(self, record):
        comodel_name = self._field_info['relation']
        assert isinstance(record, BaseModel) and record._name == comodel_name
        return record.id in self._field_value

    def add(self, record):
        """ Adds ``record`` to the field, the record must already exist.

        The addition will only be finalized when the parent record is saved.
        """
        self._assert_editable()
        parent = self._form
        comodel_name = self._field_info['relation']
        assert isinstance(record, BaseModel) and record._name == comodel_name, \
            f"trying to assign a {record._name!r} object to a {comodel_name!r} field"

        if record.id not in self._field_value:
            self._field_value.add(record.id, {'id': record.id})
            parent._perform_onchange(self._field)

    # pylint: disable=redefined-builtin
    def remove(self, id=None, index=None):
        """ Removes a record at a certain index or with a provided id from
        the field.
        """
        self._assert_editable()
        assert (id is None) ^ (index is None), "can remove by either id or index"
        if id is None:
            id = self._field_value[index]
        self._field_value.remove(id)
        self._form._perform_onchange(self._field)

    def set(self, records):
        """ Set the field value to be ``records``. """
        self._assert_editable()
        comodel_name = self._field_info['relation']
        assert isinstance(records, BaseModel) and records._name == comodel_name, \
            f"trying to assign a {records._name!r} object to a {comodel_name!r} field"

        if set(records.ids) != set(self._field_value):
            self._field_value.clear()
            for id_ in records.ids:
                self._field_value.add(id_, {'id': id_})
            self._form._perform_onchange(self._field)

    def clear(self):
        """ Removes all existing records in the m2m
        """
        self._assert_editable()
        self._field_value.clear()
        self._form._perform_onchange(self._field)


def convert_read_to_form(values, model_fields):
    result = {}
    for fname, value in values.items():
        field_info = {'type': 'id'} if fname == 'id' else model_fields[fname]
        if field_info['type'] == 'one2many':
            if 'edition_view' in field_info:
                subfields = field_info['edition_view']['fields']
                value = O2MValue(convert_read_to_form(vals, subfields) for vals in (value or ()))
            else:
                value = O2MValue({'id': id_} for id_ in (value or ()))
        elif field_info['type'] == 'many2many':
            value = M2MValue({'id': id_} for id_ in (value or ()))
        elif field_info['type'] == 'datetime' and isinstance(value, datetime):
            value = fields.Datetime.to_string(value)
        elif field_info['type'] == 'date' and isinstance(value, date):
            value = fields.Date.to_string(value)
        result[fname] = value
    return result


def _cleanup_from_default(type_, value):
    if not value:
        if type_ == 'one2many':
            return O2MValue()
        elif type_ == 'many2many':
            return M2MValue()
        elif type_ in ('integer', 'float'):
            return 0
        return value

    if type_ == 'one2many':
        raise NotImplementedError()
    elif type_ == 'datetime' and isinstance(value, datetime):
        return fields.Datetime.to_string(value)
    elif type_ == 'date' and isinstance(value, date):
        return fields.Date.to_string(value)
    return value


def get_static_context(context_str):
    """ Parse the given context string, and return the literal part of it. """
    context_ast = ast.parse(context_str.strip(), mode='eval').body
    assert isinstance(context_ast, ast.Dict)
    result = {}
    for key_ast, val_ast in zip(context_ast.keys, context_ast.values):
        try:
            key = ast.literal_eval(key_ast)
            val = ast.literal_eval(val_ast)
            result[key] = val
        except ValueError:
            pass
    return result


class Dotter:
    """ Simple wrapper for a dict where keys are accessed as readonly attributes. """
    __slots__ = ['__values']

    def __init__(self, values):
        self.__values = values

    def __getattr__(self, key):
        val = self.__values[key]
        return Dotter(val) if isinstance(val, dict) else val

