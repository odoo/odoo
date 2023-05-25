# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.form` provides an implementation of a client form
view for server-side unit tests.
"""
import ast
import collections
import json
import logging
import operator
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from lxml import etree

import odoo
from odoo.models import BaseModel
from odoo.fields import Command
from odoo.osv import expression
from odoo.osv.expression import normalize_domain, TRUE_LEAF, FALSE_LEAF
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


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
            u.groups_id.add(env.ref('account.group_account_manager'))
            u.groups_id.remove(id=env.ref('base.group_portal').id)

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
    :type record: odoo.models.Model
    :param view: the id, xmlid or actual view object to use for onchanges and
                 view constraints. If none is provided, simply loads the
                 default view for the model.
    :type view: int | str | odoo.model.Model

    .. versionadded:: 12.0
    """
    def __init__(self, record, view=None):
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
        # self._models_info = {model_name: {field_name: field_info}}
        tree = etree.fromstring(views['views']['form']['arch'])
        view = self._process_view(tree, record)
        object.__setattr__(self, '_view', view)
        # self._view = {
        #     'tree': view_arch_etree,
        #     'fields': {field_name: field_info},
        #     'modifiers': {field_name: {modifier: domain}},
        #     'contexts': {field_name: field_context_str},
        #     'onchange': onchange_spec,
        # }

        # determine record values
        object.__setattr__(self, '_values', UpdateDict())
        if record:
            assert record.id, "editing unstored records is not supported"
            self._values.update(read_record(record, self._view['fields']))
        else:
            self._init_from_defaults()

    def _process_view(self, tree, model, level=2):
        """ Post-processes to augment the view_get with:
        * an id field (may not be present if not in the view but needed)
        * pre-processed modifiers (map of modifier name to json-loaded domain)
        * pre-processed onchanges list
        """
        fields = {'id': {'type': 'id'}}
        modifiers = {'id': {'required': [FALSE_LEAF], 'readonly': [TRUE_LEAF]}}
        contexts = {}
        view = {
            'tree': tree,
            'fields': fields,
            'modifiers': modifiers,
            'contexts': contexts,
        }
        # pre-resolve modifiers & bind to arch toplevel
        eval_context = {
            "uid": self._env.user.id,
            "tz": self._env.user.tz,
            "lang": self._env.user.lang,
            "datetime": datetime,
            "context_today": lambda: odoo.fields.Date.context_today(self._env.user),
            "relativedelta": relativedelta,
            "current_date": time.strftime("%Y-%m-%d"),
            "allowed_company_ids": [self._env.user.company_id.id],
            "context": {},
        }
        # retrieve <field> nodes at the current level
        flevel = tree.xpath('count(ancestor::field)')
        daterange_field_names = {}
        for node in tree.xpath(f'.//field[count(ancestor::field) = {flevel}]'):
            field_name = node.get('name')

            # add field_info into fields
            field_info = self._models_info[model._name].get(field_name) or {'type': None}
            fields[field_name] = field_info

            # determine modifiers
            field_modifiers = {}
            for modifier, domain in json.loads(node.get('modifiers', '{}')).items():
                if isinstance(domain, int):
                    domain = [TRUE_LEAF] if domain else [FALSE_LEAF]
                elif isinstance(domain, str):
                    domain = safe_eval(domain, eval_context)
                field_modifiers[modifier] = normalize_domain(domain)

            # Combine the field modifiers with its ancestor modifiers with an
            # OR: A field is invisible if its own invisible modifier is True OR
            # if one of its ancestor invisible modifier is True
            for ancestor in node.xpath(f'ancestor::*[@modifiers][count(ancestor::field) = {flevel}]'):
                ancestor_modifiers = json.loads(ancestor.get('modifiers'))
                if 'invisible' in ancestor_modifiers:
                    domain = ancestor_modifiers['invisible']
                    if isinstance(domain, int):
                        domain = [TRUE_LEAF] if domain else [FALSE_LEAF]
                    elif isinstance(domain, str):
                        domain = safe_eval(domain, eval_context)
                    domain = normalize_domain(domain)
                    field_modifiers['invisible'] = expression.OR([
                        domain,
                        field_modifiers.get('invisible', [FALSE_LEAF]),
                    ])

            # merge field_modifiers into modifiers[field_name]
            if field_name in modifiers:
                # The field is several times in the view, combine the modifier
                # domains with an AND: a field is X if all occurences of the
                # field in the view are X.
                for modifier in field_modifiers.keys() | modifiers[field_name].keys():
                    field_modifiers[modifier] = expression.AND([
                        modifiers[field_name].get(modifier, [FALSE_LEAF]),
                        field_modifiers.get(modifier, [FALSE_LEAF]),
                    ])

            modifiers[field_name] = field_modifiers

            # determine context
            ctx = node.get('context')
            if ctx:
                contexts[field_name] = ctx

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
                    field_info['invisible'] = field_modifiers.get('invisible') == [TRUE_LEAF]
                    field_info['edition_view'] = self._get_one2many_edition_view(field_info, node, level)
                else:
                    # this trick enables the following invariant: every one2many
                    # field has some 'edition_view' in its info dict
                    field_info['type'] = 'many2many'

        for related_field, start_field in daterange_field_names.items():
            modifiers[related_field]['invisible'] = modifiers[start_field].get('invisible', False)

        view['onchange'] = model._onchange_spec({'arch': etree.tostring(tree)})

        return view

    def _get_one2many_edition_view(self, field_info, node, level):
        """ Return a suitable view for editing records into a one2many field. """
        submodel = self._env[field_info['relation']]

        # by simplicity, ensure we always have tree and form views
        views = {
            view.tag: view for view in node.xpath('./*[descendant::field]')
        }
        for view_type in ['tree', 'form']:
            if view_type in views:
                continue
            if field_info['invisible']:
                # add an empty view
                views[view_type] = etree.Element(view_type)
                continue
            refs = self._env['ir.ui.view']._get_view_refs(node)
            subviews = submodel.with_context(**refs).get_views([(None, view_type)])
            subnode = etree.fromstring(subviews['views'][view_type]['arch'])
            views[view_type] = subnode
            node.append(subnode)
            for model_name, fields in subviews['models'].items():
                self._models_info.setdefault(model_name, {}).update(fields)

        # pick the first editable subview
        view_type = next(
            vtype for vtype in node.get('mode', 'tree').split(',') if vtype != 'form'
        )
        if not (view_type == 'tree' and views['tree'].get('editable')):
            view_type = 'form'

        # don't recursively process o2ms in o2ms
        return self._process_view(views[view_type], submodel, level=level-1)

    def __str__(self):
        return f"<{type(self).__name__} {self._record}>"

    def _init_from_defaults(self):
        """ Initialize the form for a new record. """
        vals = self._values
        vals['id'] = False

        # call onchange with no field; this retrieves default values, applies
        # onchanges and return the result
        self._perform_onchange()
        # fill in whatever fields are still missing with falsy values
        vals.update({
            field_name: _cleanup_from_default(field_info['type'], False)
            for field_name, field_info in self._view['fields'].items()
            if field_name not in vals
        })
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

        domain = view['modifiers'][field_name].get(modifier, False)
        if isinstance(domain, bool):
            return domain

        if vals is None:
            vals = self._values

        stack = []
        for it in reversed(domain):
            if it == '!':
                stack.append(not stack.pop())
            elif it == '&':
                e1 = stack.pop()
                e2 = stack.pop()
                stack.append(e1 and e2)
            elif it == '|':
                e1 = stack.pop()
                e2 = stack.pop()
                stack.append(e1 or e2)
            elif isinstance(it, tuple):
                if it == TRUE_LEAF:
                    stack.append(True)
                    continue
                if it == FALSE_LEAF:
                    stack.append(False)
                    continue
                left, operator, right = it
                # hack-ish handling of parent.<field> modifiers
                if left.startswith('parent.'):
                    left_value = vals['•parent•'][left[7:]]
                else:
                    left_value = vals[left]
                    # apparent artefact of JS data representation: m2m field
                    # values are assimilated to lists of ids?
                    # FIXME: SSF should do that internally, but the requirement
                    #        of recursively post-processing to generate lists of
                    #        commands on save (e.g. m2m inside an o2m) means the
                    #        data model needs proper redesign
                    # we're looking up the "current view" so bits might be
                    # missing when processing o2ms in the parent (see
                    # values_to_save:1450 or so)
                    left_field = view['fields'].get(left, {'type': None})
                    if left_field['type'] == 'many2many':
                        # field value should be [(6, _, ids)], we want just the ids
                        left_value = left_value[0][2] if left_value else []
                stack.append(self._OPS[operator](left_value, right))
            else:
                raise ValueError(f"Unknown domain element {it!r}")
        assert len(stack) == 1
        return stack[0]

    _OPS = {
        '=': operator.eq,
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>=': operator.ge,
        '>': operator.gt,
        'in': lambda a, b: (a in b) if isinstance(b, (tuple, list)) else (b in a),
        'not in': lambda a, b: (a not in b) if isinstance(b, (tuple, list)) else (b not in a),
        'like': lambda a, b: a and b and isinstance(a, str) and isinstance(b, str) and a in b,
        'ilike': lambda a, b: a and b and isinstance(a, str) and isinstance(b, str) and a.lower() in b.lower(),
        'not like': lambda a, b: a and b and isinstance(a, str) and isinstance(b, str) and a not in b,
        'not ilike': lambda a, b: a and b and isinstance(a, str) and isinstance(b, str) and a.lower() not in b.lower(),
    }

    def _get_context(self, field_name):
        """ Return the context of a given field. """
        context_str = self._view['contexts'].get(field_name)
        if not context_str:
            return {}
        eval_context = self._get_eval_context()
        return safe_eval(context_str, eval_context)

    def _get_eval_context(self):
        """ Return the context dict to eval something. """
        context = {
            'id': self._record.id,
            'active_id': self._record.id,
            'active_ids': self._record.ids,
            'active_model': self._record._name,
            'current_date': date.today().strftime("%Y-%m-%d"),
            **self._env.context,
        }
        return {
            **context,
            'context': context,
            **self._get_all_values(),
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
        if self._record:
            if values:
                self._record.write(values)
        else:
            object.__setattr__(self, '_record', self._record.create(values))
        # reload the record
        self._values.clear()
        self._values.update(read_record(self._record, self._view['fields']))
        self._env.flush_all()
        self._env.clear()  # discard cache and pending recomputations
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

        :param mode: can be ``"save"`` (validate and return non-readonly modified fields)
            or ``"all"`` (return all field values)
        :param UpdateDict values: values of the record to extract
        :param view: view info
        :param dict modifiers_values: defaults to ``values``, but o2ms need some additional massaging
        :param parent_link: optional field representing "parent"
        """
        assert mode in ('save', 'all')

        if values is None:
            values = self._values
        if view is None:
            view = self._view
        assert isinstance(values, UpdateDict)

        modifiers_values = modifiers_values or values

        result = {}
        for field_name, field_info in view['fields'].items():
            if field_name == 'id':
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
            if mode == 'save' and field_name not in values._changed:
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
                subview = field_info['edition_view']
                subfields = subview['fields']
                res = []
                for (cmd, rid, vs) in value:
                    if cmd == Command.UPDATE and not vs:
                        cmd, vs = Command.LINK, False
                    elif cmd in (Command.CREATE, Command.UPDATE):
                        vs = vs or {}

                        missing = subfields.keys() - vs.keys()
                        # FIXME: maybe do this during initial loading instead?
                        if missing:
                            comodel = self._env[field_info['relation']]
                            if cmd == Command.CREATE:
                                vs.update(dict.fromkeys(missing, False))
                                vs.update({
                                    key: _cleanup_from_default(subfields[key], val)
                                    for key, val in comodel.default_get(list(missing)).items()
                                })
                            else:
                                vs.update(read_record(
                                    comodel.browse(rid),
                                    {key: val for key, val in subfields.items() if key not in vs},
                                ))
                        if not isinstance(vs, UpdateDict):
                            vs = UpdateDict(vs)
                            vs._changed.update(vs)
                        vs = self._get_values(
                            mode, vs, subview,
                            modifiers_values={'id': False, **vs, '•parent•': values},
                            # related o2m don't have a relation_field
                            parent_link=field_info.get('relation_field'),
                        )
                    res.append((cmd, rid, vs))
                value = res

            result[field_name] = value
        return result

    def _perform_onchange(self, field_name=None):
        assert field_name is None or isinstance(field_name, str)

        # marks onchange source as changed
        if field_name:
            self._values._changed.add(field_name)

        # skip calling onchange() if there's no on_change on the field
        spec = self._view['onchange']
        if field_name and not spec[field_name]:
            return

        record = self._record

        # if the onchange is triggered by a field, add the context of that field
        if field_name:
            context = self._get_context(field_name)
            if context:
                record = record.with_context(**context)

        result = record.onchange(self._onchange_values(), field_name, spec)
        self._env.flush_all()
        self._env.clear()  # discard cache and pending recomputations

        if result.get('warning'):
            _logger.getChild('onchange').warning("%(title)s %(message)s", result['warning'])

        # mark onchange output as changed
        fields = self._view['fields']
        values = {
            key: self._cleanup_onchange(fields[key], val, self._values.get(key))
            for key, val in result.get('value', {}).items()
            if key in fields
        }
        self._values.update(values)
        self._values._changed.update(values)
        return result

    def _onchange_values(self):
        return self._onchange_values_(self._view['fields'], self._values)

    def _onchange_values_(self, fields, values):
        """ Recursively cleanup o2m values for onchanges:

        * if an o2m command is a 1 (UPDATE) and there is nothing to update, send
          a 4 instead (LINK_TO) instead as that's what the webclient sends for
          unmodified rows
        * if an o2m command is a 1 (UPDATE) and only a subset of its fields have
          been modified, only send the modified ones

        This needs to be recursive as there are people who put invisible o2ms
        inside their o2ms.
        """
        result = {}
        for key, val in values.items():
            if fields[key]['type'] == 'one2many':
                subfields = fields[key]['edition_view']['fields']
                result[key] = []
                for (cmd, rid, vs) in val:
                    if cmd == Command.UPDATE and isinstance(vs, UpdateDict):
                        vs = dict(vs.changed_items())
                    if cmd == Command.UPDATE and not vs:
                        result[key].append((Command.LINK, rid, False))
                    elif cmd in (Command.CREATE, Command.UPDATE):
                        result[key].append((cmd, rid, self._onchange_values_(subfields, vs)))
                    else:
                        result[key].append((cmd, rid, vs))
            else:
                result[key] = val
        return result

    def _cleanup_onchange(self, field_info, value, current):
        """ Transform the value returned by onchange() into the expected format
        for self._values.
        """
        if field_info['type'] == 'many2one':
            return value[0] if value else False

        if field_info['type'] == 'one2many':
            # ignore o2ms nested in o2ms
            if not field_info['edition_view']:
                return []

            if current is None:
                current = []

            result = []
            current_ids = {rid for cmd, rid, vs in current if cmd in (1, 2)}
            current_values = {rid: vs for cmd, rid, vs in current if cmd == 1}
            # which view should this be???
            subfields = field_info['edition_view']['fields']
            # TODO: simplistic, unlikely to work if e.g. there's a 5 inbetween other commands
            for command in value:
                if command[0] == Command.CREATE:
                    result.append((Command.CREATE, 0, {
                        key: self._cleanup_onchange(subfields[key], val, None)
                        for key, val in command[2].items()
                        if key in subfields
                    }))
                elif command[0] == Command.UPDATE:
                    record_id = command[1]
                    current_ids.discard(record_id)
                    stored = current_values.get(record_id)
                    if stored is None:
                        record = self._env[field_info['relation']].browse(record_id)
                        stored = UpdateDict(read_record(record, subfields))
                    for key, val in command[2].items():
                        if key in subfields:
                            val = self._cleanup_onchange(subfields[key], val, stored.get(key))
                            # if there are values from the onchange which differ
                            # from current values, update & mark field as changed
                            if stored.get(key, val) != val:
                                stored[key] = val
                                stored._changed.add(key)
                    result.append((Command.UPDATE, record_id, stored))
                elif command[0] == Command.DELETE:
                    current_ids.discard(command[1])
                    result.append((Command.DELETE, command[1], False))
                elif command[0] == Command.LINK:
                    current_ids.discard(command[1])
                    result.append((Command.UPDATE, command[1], None))
                elif command[0] == Command.CLEAR:
                    result = []
            # explicitly mark all non-relinked (or modified) records as deleted
            for id_ in current_ids:
                result.append((Command.DELETE, id_, False))
            return result

        if field_info['type'] == 'many2many':
            # onchange result is a bunch of commands, normalize to single 6
            ids = [] if current is None else list(current[0][2])
            for command in value:
                if command[0] == Command.UPDATE:
                    ids.append(command[1])
                elif command[0] == Command.UNLINK:
                    ids.remove(command[1])
                elif command[0] == Command.LINK:
                    ids.append(command[1])
                elif command[0] == Command.CLEAR:
                    del ids[:]
                elif command[0] == Command.SET:
                    ids[:] = command[2]
                else:
                    raise ValueError(f"Unsupported M2M command {command[0]}")
            return [(Command.SET, False, ids)]

        return value


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
        if vals is None:
            vals = {**self._values, '•parent•': self._proxy._form._values}
        return super()._get_modifier(field_name, modifier, view=view, vals=vals)

    def _get_eval_context(self):
        eval_context = super()._get_eval_context()
        eval_context['parent'] = Dotter(self._proxy._form._values)
        return eval_context

    def _onchange_values(self):
        values = super()._onchange_values()
        # computed o2m may not have a relation_field(?)
        field_info = self._proxy._field_info
        if 'relation_field' in field_info:  # note: should be fine because not recursive
            values[field_info['relation_field']] = self._proxy._form._onchange_values()
        return values

    def save(self):
        proxy = self._proxy
        field_value = proxy._form._values[proxy._field]
        values = self._get_save_values()
        if self._index is None:
            field_value.append((Command.CREATE, 0, values))
        else:
            index = proxy._command_index(self._index)
            (cmd, id_, vs) = field_value[index]
            if cmd == Command.CREATE:
                vs.update(values)
            elif cmd == Command.UPDATE:
                if vs is None:
                    vs = UpdateDict()
                assert isinstance(vs, UpdateDict), type(vs)
                vs.update(values)
                field_value[index] = (Command.UPDATE, id_, vs)
            else:
                raise AssertionError(f"Expected command 0 or 1, found {cmd!r}")

        proxy._form._perform_onchange(proxy._field)

    def _get_save_values(self):
        """ Validate and return field values modified since load/save. """
        values = UpdateDict(self._values)

        for field_name in self._view['fields']:
            if self._get_modifier(field_name, 'required') and not (
                self._get_modifier(field_name, 'column_invisible')
                or self._get_modifier(field_name, 'invisible')
            ):
                assert values[field_name] is not False, "{fname!r} is a required field"

        return values


class UpdateDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changed = set()
        if args and isinstance(args[0], UpdateDict):
            self._changed.update(args[0]._changed)

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
        self._field_info = self._form._view['fields'][field_name]

    def _assert_editable(self):
        assert not self._form._get_modifier(self._field, 'readonly'), f'field {self._field!r} is not editable'
        assert not self._form._get_modifier(self._field, 'invisible'), f'field {self._field!r} is not visible'


class O2MProxy(X2MProxy):
    """ Proxy object for editing the value of a one2many field. """
    def __init__(self, form, field_name):
        super().__init__(form, field_name)
        # reify records to a list so they can be manipulated easily?
        self._records = []
        model = self._model
        fields = self._field_info['edition_view']['fields']
        for (command, rid, values) in self._form._values[self._field]:
            if command == Command.CREATE:
                self._records.append(values)
            elif command == Command.UPDATE:
                if values is None:
                    # read based on view info
                    r = model.browse(rid)
                    values = UpdateDict(read_record(r, fields))
                self._records.append(values)
            elif command == Command.DELETE:
                pass
            else:
                raise AssertionError("O2M proxy only supports commands 0, 1 and 2, found %s" % command)

    def __len__(self):
        return len(self._records)

    @property
    def _model(self):
        model = self._form._env[self._field_info['relation']]
        context = self._form._get_context(self._field)
        if context:
            model = model.with_context(**context)
        return model

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
        # remove reified record from local list & either remove 0 from
        # commands list or replace 1 (update) by 2 (remove)
        cidx = self._command_index(index)
        commands = self._form._values[self._field]
        (command, rid, _) = commands[cidx]
        if command == Command.CREATE:
            # record not saved yet -> just remove the command
            del commands[cidx]
        elif command == Command.UPDATE:
            # record already saved, replace by 2
            commands[cidx] = (Command.DELETE, rid, 0)
        else:
            raise AssertionError("Expected command 0 or 1, got %s" % commands[cidx])
        # remove reified record
        del self._records[index]
        self._form._perform_onchange(self._field)

    def _command_index(self, for_record):
        """ Takes a record index and finds the corresponding record index
        (skips all 2s, basically)

        :param int for_record:
        """
        commands = self._form._values[self._field]
        return next(
            cidx
            for ridx, cidx in enumerate(
                cidx for cidx, (c, _1, _2) in enumerate(commands)
                if c in (Command.CREATE, Command.UPDATE)
            )
            if ridx == for_record
        )


class M2MProxy(X2MProxy, collections.abc.Sequence):
    """ Proxy object for editing the value of a many2many field.

    Behaves as a :class:`~collection.Sequence` of recordsets, can be
    indexed or sliced to get actual underlying recordsets.
    """
    def __getitem__(self, index):
        comodel_name = self._field_info['relation']
        return self._form._env[comodel_name].browse(self._get_ids()[index])

    def __len__(self):
        return len(self._get_ids())

    def __iter__(self):
        comodel_name = self._field_info['relation']
        records = self._form._env[comodel_name].browse(self._get_ids())
        return iter(records)

    def __contains__(self, record):
        comodel_name = self._field_info['relation']
        assert isinstance(record, BaseModel) and record._name == comodel_name
        return record.id in self._get_ids()

    def _get_ids(self):
        return self._form._values[self._field][0][2]

    def add(self, record):
        """ Adds ``record`` to the field, the record must already exist.

        The addition will only be finalized when the parent record is saved.
        """
        self._assert_editable()
        parent = self._form
        comodel_name = self._field_info['relation']
        assert isinstance(record, BaseModel) and record._name == comodel_name, \
            f"trying to assign a {record._name!r} object to a {comodel_name!r} field"
        self._get_ids().append(record.id)

        parent._perform_onchange(self._field)

    # pylint: disable=redefined-builtin
    def remove(self, id=None, index=None):
        """ Removes a record at a certain index or with a provided id from
        the field.
        """
        self._assert_editable()
        assert (id is None) ^ (index is None), "can remove by either id or index"
        if id is None:
            # remove by index
            del self._get_ids()[index]
        else:
            self._get_ids().remove(id)
        self._form._perform_onchange(self._field)

    def set(self, records):
        """ Set the field value to be ``records``. """
        self._assert_editable()
        comodel_name = self._field_info['relation']
        assert isinstance(records, BaseModel) and records._name == comodel_name, \
            f"trying to assign a {records._name!r} object to a {comodel_name!r} field"

        if set(records.ids) != set(self._get_ids()):
            self._get_ids()[:] = records.ids
            self._form._perform_onchange(self._field)

    def clear(self):
        """ Removes all existing records in the m2m
        """
        self._assert_editable()
        self._get_ids()[:] = []
        self._form._perform_onchange(self._field)


def read_record(record, fields):
    """ Read the given fields (field descriptions) on the given record. """
    result = {}
    # don't read the id explicitly, not sure why but if any of the "magic" hr
    # field is read alongside `id` then it blows up e.g.
    # james.read(['barcode']) works fine but james.read(['id', 'barcode'])
    # triggers an ACL error on barcode, likewise km_home_work or
    # emergency_contact or whatever. Since we always get the id anyway, just
    # remove it from the fields to read
    field_names = [fname for fname in fields if fname != 'id']
    if not field_names:
        return result
    for fname, value in record.read(field_names)[0].items():
        field_info = fields[fname]
        if field_info['type'] == 'many2one':
            value = value and value[0]
        elif field_info['type'] == 'many2many':
            value = [(Command.SET, 0, value or [])]
        elif field_info['type'] == 'one2many':
            value = [(Command.UPDATE, result, None) for result in value or []]
        elif field_info['type'] == 'datetime' and isinstance(value, datetime):
            value = odoo.fields.Datetime.to_string(value)
        elif field_info['type'] == 'date' and isinstance(value, date):
            value = odoo.fields.Date.to_string(value)
        result[fname] = value
    return result


def _cleanup_from_default(type_, value):
    if not value:
        if type_ == 'many2many':
            return [(Command.SET, False, [])]
        elif type_ == 'one2many':
            return []
        elif type_ in ('integer', 'float'):
            return 0
        return value

    if type_ == 'one2many':
        return [cmd for cmd in value if cmd[0] != Command.SET]
    elif type_ == 'datetime' and isinstance(value, datetime):
        return odoo.fields.Datetime.to_string(value)
    elif type_ == 'date' and isinstance(value, date):
        return odoo.fields.Date.to_string(value)
    return value


class Dotter:
    """ Simple wrapper for a dict where keys are accessed as readonly attributes. """
    __slots__ = ['__values']

    def __init__(self, values):
        self.__values = values

    def __getattr__(self, key):
        val = self.__values[key]
        return Dotter(val) if isinstance(val, dict) else val
