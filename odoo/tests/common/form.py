import collections
import functools
import json
import operator
import re
from datetime import date, datetime

from lxml import etree

import odoo
from odoo.models import BaseModel
from odoo.osv import expression
from odoo.osv.expression import FALSE_LEAF, TRUE_LEAF, normalize_domain
from odoo.tests.common import _logger
from odoo.tools.safe_eval import safe_eval


class Form(object):
    """ Server-side form view implementation (partial)

    Implements much of the "form view" manipulation flow, such that
    server-side tests can more properly reflect the behaviour which would be
    observed when manipulating the interface:

    * call default_get and the relevant onchanges on "creation"
    * call the relevant onchanges on setting fields
    * properly handle defaults & onchanges around x2many fields

    Saving the form returns the created record if in creation mode.

    Regular fields can just be assigned directly to the form, for
    :class:`~odoo.fields.Many2one` fields assign a singleton recordset::

        # empty recordset => creation mode
        f = Form(self.env['sale.order'])
        f.partner_id = a_partner
        so = f.save()

    When editing a record, using the form as a context manager to
    automatically save it at the end of the scope::

        with Form(so) as f2:
            f2.payment_term_id = env.ref('account.account_payment_term_15days')
            # f2 is saved here

    For :class:`~odoo.fields.Many2many` fields, the field itself is a
    :class:`~odoo.tests.common.M2MProxy` and can be altered by adding or
    removing records::

        with Form(user) as u:
            u.groups_id.add(env.ref('account.group_account_manager'))
            u.groups_id.remove(id=env.ref('base.group_portal').id)

    Finally :class:`~odoo.fields.One2many` are reified as
    :class:`~odoo.tests.common.O2MProxy`.

    Because the :class:`~odoo.fields.One2many` only exists through its
    parent, it is manipulated more directly by creating "sub-forms"
    with the :meth:`~odoo.tests.common.O2MProxy.new` and
    :meth:`~odoo.tests.common.O2MProxy.edit` methods. These would
    normally be used as context managers since they get saved in the
    parent record::

        with Form(so) as f3:
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

    :param recordp: empty or singleton recordset. An empty recordset will
                    put the view in "creation" mode and trigger calls to
                    default_get and on-load onchanges, a singleton will
                    put it in "edit" mode and only load the view's data.
    :type recordp: odoo.models.Model
    :param view: the id, xmlid or actual view object to use for
                    onchanges and view constraints. If none is provided,
                    simply loads the default view for the model.
    :type view: int | str | odoo.model.Model

    .. versionadded:: 12.0
    """
    def __init__(self, recordp, view=None):
        # necessary as we're overriding setattr
        assert isinstance(recordp, BaseModel)
        env = recordp.env
        object.__setattr__(self, '_env', env)

        # store model bit only
        object.__setattr__(self, '_model', recordp.browse(()))
        if isinstance(view, BaseModel):
            assert view._name == 'ir.ui.view', "the view parameter must be a view id, xid or record, got %s" % view
            view_id = view.id
        elif isinstance(view, str):
            view_id = env.ref(view).id
        else:
            view_id = view or False
        fvg = recordp.get_view(view_id, 'form')
        fvg['tree'] = etree.fromstring(fvg['arch'])
        fvg['fields'] = self._get_view_fields(fvg['tree'], recordp)

        object.__setattr__(self, '_view', fvg)

        self._process_fvg(recordp, fvg)

        # ordered?
        vals = dict.fromkeys(fvg['fields'], False)
        object.__setattr__(self, '_values', vals)
        object.__setattr__(self, '_changed', set())
        if recordp:
            assert recordp['id'], "editing unstored records is not supported"
            # always load the id
            vals['id'] = recordp['id']

            self._init_from_values(recordp)
        else:
            self._init_from_defaults(self._model)

    def _get_view_fields(self, node, model):
        level = node.xpath('count(ancestor::field)')
        fnames = set(el.get('name') for el in node.xpath('.//field[count(ancestor::field) = %s]' % level))
        fields = {fname: info for fname, info in model.fields_get().items() if fname in fnames}
        return fields

    def _o2m_set_edition_view(self, descr, node, level):
        default_view = next(
            (m for m in node.get('mode', 'tree').split(',') if m != 'form'),
            'tree'
        )
        refs = self._env['ir.ui.view']._get_view_refs(node)
        # always fetch for simplicity, ensure we always have a tree and
        # a form view
        submodel = self._env[descr['relation']]
        views = {view.tag: view for view in node.xpath('./*[descendant::field]')}
        for view_type in ['tree', 'form']:
            # embedded views should take the priority on externals
            if view_type not in views:
                sub_fvg = submodel.with_context(**refs).get_view(view_type=view_type)
                sub_node = etree.fromstring(sub_fvg['arch'])
                views[view_type] = sub_node
                node.append(sub_node)
        # if the default view is a kanban or a non-editable list, the
        # "edition controller" is the form view
        edition_view = 'tree' if default_view == 'tree' and views['tree'].get('editable') else 'form'
        edition = {
            'fields': self._get_view_fields(views[edition_view], submodel),
            'tree': views[edition_view],
        }

        # don't recursively process o2ms in o2ms
        self._process_fvg(submodel, edition, level=level-1)
        descr['edition_view'] = edition

    def __str__(self):
        return "<%s %s(%s)>" % (
            type(self).__name__,
            self._model._name,
            self._values.get('id', False),
        )

    def _process_fvg(self, model, fvg, level=2):
        """ Post-processes to augment the view_get with:
        * an id field (may not be present if not in the view but needed)
        * pre-processed modifiers (map of modifier name to json-loaded domain)
        * pre-processed onchanges list
        """
        inherited_modifiers = ['invisible']
        fvg['fields'].setdefault('id', {'type': 'id'})
        # pre-resolve modifiers & bind to arch toplevel
        modifiers = fvg['modifiers'] = {'id': {'required': [FALSE_LEAF], 'readonly': [TRUE_LEAF]}}
        contexts = fvg['contexts'] = {}
        order = fvg['fields_ordered'] = []
        field_level = fvg['tree'].xpath('count(ancestor::field)')
        for f in fvg['tree'].xpath('.//field[count(ancestor::field) = %s]' % field_level):
            fname = f.get('name')
            order.append(fname)

            node_modifiers = {
                modifier: ([TRUE_LEAF] if domain else [FALSE_LEAF]) if isinstance(domain, int) else normalize_domain(domain)
                for modifier, domain in json.loads(f.get('modifiers', '{}')).items()
            }

            for a in f.xpath('ancestor::*[@modifiers][count(ancestor::field) = %s]' % field_level):
                ancestor_modifiers = json.loads(a.get('modifiers'))
                for modifier in inherited_modifiers:
                    if modifier in ancestor_modifiers:
                        domain = ancestor_modifiers[modifier]
                        ancestor_domain = ([TRUE_LEAF] if domain else [FALSE_LEAF]) if isinstance(domain, int) else normalize_domain(domain)
                        node_domain = node_modifiers.get(modifier, [])
                        # Combine the field modifiers with his ancestor modifiers with an OR connector
                        # e.g. A field is invisible if its own invisible modifier is True
                        # OR if one of its ancestor invisible modifier is True
                        node_modifiers[modifier] = expression.OR([ancestor_domain, node_domain])

            if fname in modifiers:
                # The field is multiple times in the view, combine the modifier domains with an AND connector
                # e.g. a field is invisible if all occurences of the field are invisible in the view.
                # e.g. a field is readonly if all occurences of the field are readonly in the view.
                for modifier in set(node_modifiers.keys()).union(modifiers[fname].keys()):
                    modifiers[fname][modifier] = expression.AND([
                        modifiers[fname].get(modifier, [FALSE_LEAF]),
                        node_modifiers.get(modifier, [FALSE_LEAF]),
                    ])
            else:
                modifiers[fname] = node_modifiers

            ctx = f.get('context')
            if ctx:
                contexts[fname] = ctx

            descr = fvg['fields'].get(fname) or {'type': None}
            # FIXME: better widgets support
            # NOTE: selection breaks because of m2o widget=selection
            if f.get('widget') in ['many2many']:
                descr['type'] = f.get('widget')
            if level and descr['type'] == 'one2many':
                self._o2m_set_edition_view(descr, f, level)

        fvg['onchange'] = model._onchange_spec({'arch': etree.tostring(fvg['tree'])})

    def _init_from_defaults(self, model):
        vals = self._values
        vals.clear()
        vals['id'] = False

        # call onchange with an empty list of fields; this retrieves default
        # values, applies onchanges and return the result
        self._perform_onchange([])
        # fill in whatever fields are still missing with falsy values
        vals.update(
            (f, _cleanup_from_default(descr['type'], False))
            for f, descr in self._view['fields'].items()
            if f not in vals
        )
        # mark all fields as modified (though maybe this should be done on
        # save when creating for better reliability?)
        self._changed.update(self._view['fields'])

    def _init_from_values(self, values):
        self._values.update(
            record_to_values(self._view['fields'], values))

    def __getattr__(self, field):
        descr = self._view['fields'].get(field)
        assert descr is not None, "%s was not found in the view" % field

        v = self._values[field]
        if descr['type'] == 'many2one':
            Model = self._env[descr['relation']]
            if not v:
                return Model
            return Model.browse(v)
        elif descr['type'] == 'many2many':
            return M2MProxy(self, field)
        elif descr['type'] == 'one2many':
            return O2MProxy(self, field)
        return v

    def _get_modifier(self, field, modifier, *, default=False, view=None, modmap=None, vals=None):
        if view is None:
            view = self._view

        d = (modmap or view['modifiers'])[field].get(modifier, default)
        if isinstance(d, bool):
            return d

        if vals is None:
            vals = self._values
        stack = []
        for it in reversed(d):
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
                elif it == FALSE_LEAF:
                    stack.append(False)
                    continue
                f, op, val = it
                # hack-ish handling of parent.<field> modifiers
                f, n = re.subn(r'^parent\.', '', f, 1)
                if n:
                    field_val = vals['•parent•'][f]
                else:
                    field_val = vals[f]
                    # apparent artefact of JS data representation: m2m field
                    # values are assimilated to lists of ids?
                    # FIXME: SSF should do that internally, but the requirement
                    #        of recursively post-processing to generate lists of
                    #        commands on save (e.g. m2m inside an o2m) means the
                    #        data model needs proper redesign
                    # we're looking up the "current view" so bits might be
                    # missing when processing o2ms in the parent (see
                    # values_to_save:1450 or so)
                    f_ = view['fields'].get(f, {'type': None})
                    if f_['type'] == 'many2many':
                        # field value should be [(6, _, ids)], we want just the ids
                        field_val = field_val[0][2] if field_val else []

                stack.append(self._OPS[op](field_val, val))
            else:
                raise ValueError("Unknown domain element %s" % [it])
        [result] = stack
        return result
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
    }
    def _get_context(self, field):
        c = self._view['contexts'].get(field)
        if not c:
            return {}

        # see _getEvalContext
        # the context for a field's evals (of domain/context) is the composition of:
        # * the parent's values
        # * ??? element.context ???
        # * the environment's context (?)
        # * a few magic values
        record_id = self._values.get('id') or False

        ctx = dict(self._values_to_save(all_fields=True))
        ctx.update(self._env.context)
        ctx.update(
            id=record_id,
            active_id=record_id,
            active_ids=[record_id] if record_id else [],
            active_model=self._model._name,
            current_date=date.today().strftime("%Y-%m-%d"),
        )
        return safe_eval(c, ctx, {'context': ctx})

    def __setattr__(self, field, value):
        descr = self._view['fields'].get(field)
        assert descr is not None, "%s was not found in the view" % field
        assert descr['type'] not in ('many2many', 'one2many'), \
            "Can't set an o2m or m2m field, manipulate the corresponding proxies"

        assert not self._get_modifier(field, 'readonly'), \
            "can't write on readonly field {}".format(field)
        assert not self._get_modifier(field, 'invisible'), \
            "can't write on invisible field {}".format(field)

        if descr['type'] == 'many2one':
            assert isinstance(value, BaseModel) and value._name == descr['relation']
            # store just the id: that's the output of default_get & (more
            # or less) onchange.
            value = value.id

        self._values[field] = value
        self._perform_onchange([field])

    # enables with Form(...) as f: f.a = 1; f.b = 2; f.c = 3
    # q: how to get recordset?
    def __enter__(self):
        return self
    def __exit__(self, etype, _evalue, _etb):
        if not etype:
            self.save()

    def save(self):
        """ Saves the form, returns the created record if applicable

        * does not save ``readonly`` fields
        * does not save unmodified fields (during edition) — any assignment
          or onchange return marks the field as modified, even if set to its
          current value

        :raises AssertionError: if the form has any unfilled required field
        """
        id_ = self._values.get('id')
        values = self._values_to_save()
        if id_:
            r = self._model.browse(id_)
            if values:
                r.write(values)
        else:
            r = self._model.create(values)
        self._values.update(
            record_to_values(self._view['fields'], r)
        )
        self._changed.clear()
        self._model.env.flush_all()
        self._model.env.clear()  # discard cache and pending recomputations
        return r

    def _values_to_save(self, all_fields=False):
        """ Validates values and returns only fields modified since
        load/save

        :param bool all_fields: if False (the default), checks for required
                                fields and only save fields which are changed
                                and not readonly
        """
        view = self._view
        fields = self._view['fields']
        record_values = self._values
        changed = self._changed
        return self._values_to_save_(
            record_values, fields, view,
            changed, all_fields
        )

    def _values_to_save_(
            self, record_values, fields, view,
            changed, all_fields=False, modifiers_values=None,
            parent_link=None
    ):
        """ Validates & extracts values to save, recursively in order to handle
         o2ms properly

        :param dict record_values: values of the record to extract
        :param dict fields: fields_get result
        :param view: view tree
        :param set changed: set of fields which have been modified (since last save)
        :param bool all_fields:
            whether to ignore normal filtering and just return everything
        :param dict modifiers_values:
            defaults to ``record_values``, but o2ms need some additional
            massaging
        """
        values = {}
        for f in fields:
            if f == 'id':
                continue

            get_modifier = functools.partial(
                self._get_modifier,
                f, view=view,
                vals=modifiers_values or record_values
            )
            descr = fields[f]
            v = record_values[f]
            # note: maybe `invisible` should not skip `required` if model attribute
            if v is False and not (all_fields or f == parent_link or descr['type'] == 'boolean' or get_modifier('invisible') or get_modifier('column_invisible')):
                if get_modifier('required'):
                    raise AssertionError("{} is a required field ({})".format(f, view['modifiers'][f]))

            # skip unmodified fields unless all_fields
            if not (all_fields or f in changed):
                continue

            if get_modifier('readonly'):
                node = _get_node(view, f)
                if not (all_fields or node.get('force_save')):
                    continue

            if descr['type'] == 'one2many':
                subview = descr['edition_view']
                fields_ = subview['fields']
                oldvals = v
                v = []
                for (c, rid, vs) in oldvals:
                    if c == 1 and not vs:
                        c, vs = 4, False
                    elif c in (0, 1):
                        vs = vs or {}

                        missing = fields_.keys() - vs.keys()
                        # FIXME: maybe do this during initial loading instead?
                        if missing:
                            Model = self._env[descr['relation']]
                            if c == 0:
                                vs.update(dict.fromkeys(missing, False))
                                vs.update(
                                    (k, _cleanup_from_default(fields_[k], v))
                                    for k, v in Model.default_get(list(missing)).items()
                                )
                            else:
                                vs.update(record_to_values(
                                    {k: v for k, v in fields_.items() if k not in vs},
                                    Model.browse(rid)
                                ))
                        vs = self._values_to_save_(
                            vs, fields_, subview,
                            vs._changed if isinstance(vs, UpdateDict) else vs.keys(),
                            all_fields,
                            modifiers_values={'id': False, **vs, '•parent•': record_values},
                            # related o2m don't have a relation_field
                            parent_link=descr.get('relation_field'),
                        )
                    v.append((c, rid, vs))

            values[f] = v
        return values

    def _perform_onchange(self, fields):
        assert isinstance(fields, list)
        # marks any onchange source as changed
        self._changed.update(fields)

        # skip calling onchange() if there's no trigger on any of the changed
        # fields
        spec = self._view['onchange']
        if fields and not any(spec[f] for f in fields):
            return

        record = self._model.browse(self._values.get('id'))
        result = record.onchange(self._onchange_values(), fields, spec)
        self._model.env.flush_all()
        self._model.env.clear()  # discard cache and pending recomputations
        if result.get('warning'):
            _logger.getChild('onchange').warning("%(title)s %(message)s" % result.get('warning'))
        values = result.get('value', {})
        # mark onchange output as changed
        self._changed.update(values.keys() & self._view['fields'].keys())
        self._values.update(
            (k, self._cleanup_onchange(
                self._view['fields'][k],
                v, self._values.get(k),
            ))
            for k, v in values.items()
            if k in self._view['fields']
        )
        return result

    def _onchange_values(self):
        return self._onchange_values_(self._view['fields'], self._values)

    def _onchange_values_(self, fields, record):
        """ Recursively cleanup o2m values for onchanges:

        * if an o2m command is a 1 (UPDATE) and there is nothing to update, send
          a 4 instead (LINK_TO) instead as that's what the webclient sends for
          unmodified rows
        * if an o2m command is a 1 (UPDATE) and only a subset of its fields have
          been modified, only send the modified ones

        This needs to be recursive as there are people who put invisible o2ms
        inside their o2ms.
        """
        values = {}
        for k, v in record.items():
            if fields[k]['type'] == 'one2many':
                subfields = fields[k]['edition_view']['fields']
                it = values[k] = []
                for (c, rid, vs) in v:
                    if c == 1 and isinstance(vs, UpdateDict):
                        vs = dict(vs.changed_items())

                    if c == 1 and not vs:
                        it.append((4, rid, False))
                    elif c in (0, 1):
                        it.append((c, rid, self._onchange_values_(subfields, vs)))
                    else:
                        it.append((c, rid, vs))
            else:
                values[k] = v
        return values

    def _cleanup_onchange(self, descr, value, current):
        if descr['type'] == 'many2one':
            if not value:
                return False
            # out of onchange, m2o are name-gotten
            return value[0]
        elif descr['type'] == 'one2many':
            # ignore o2ms nested in o2ms
            if not descr['edition_view']:
                return []

            if current is None:
                current = []
            v = []
            c = {t[1] for t in current if t[0] in (1, 2)}
            current_values = {c[1]: c[2] for c in current if c[0] == 1}
            # which view should this be???
            subfields = descr['edition_view']['fields']
            # TODO: simplistic, unlikely to work if e.g. there's a 5 inbetween other commands
            for command in value:
                if command[0] == 0:
                    v.append((0, 0, {
                        k: self._cleanup_onchange(subfields[k], v, None)
                        for k, v in command[2].items()
                        if k in subfields
                    }))
                elif command[0] == 1:
                    record_id = command[1]
                    c.discard(record_id)
                    stored = current_values.get(record_id)
                    if stored is None:
                        record = self._env[descr['relation']].browse(record_id)
                        stored = UpdateDict(record_to_values(subfields, record))

                    updates = (
                        (k, self._cleanup_onchange(subfields[k], v, stored.get(k)))
                        for k, v in command[2].items()
                        if k in subfields
                    )
                    for field, value in updates:
                        # if there are values from the onchange which differ
                        # from current values, update & mark field as changed
                        if stored.get(field, value) != value:
                            stored._changed.add(field)
                            stored[field] = value

                    v.append((1, record_id, stored))
                elif command[0] == 2:
                    c.discard(command[1])
                    v.append((2, command[1], False))
                elif command[0] == 4:
                    c.discard(command[1])
                    v.append((1, command[1], None))
                elif command[0] == 5:
                    v = []
            # explicitly mark all non-relinked (or modified) records as deleted
            for id_ in c: v.append((2, id_, False))
            return v
        elif descr['type'] == 'many2many':
            # onchange result is a bunch of commands, normalize to single 6
            if current is None:
                ids = []
            else:
                ids = list(current[0][2])
            for command in value:
                if command[0] == 1:
                    ids.append(command[1])
                elif command[0] == 3:
                    ids.remove(command[1])
                elif command[0] == 4:
                    ids.append(command[1])
                elif command[0] == 5:
                    del ids[:]
                elif command[0] == 6:
                    ids[:] = command[2]
                else:
                    raise ValueError(
                        "Unsupported M2M command %d" % command[0])
            return [(6, False, ids)]

        return value


class O2MForm(Form):
    # noinspection PyMissingConstructor
    def __init__(self, proxy, index=None):
        m = proxy._model
        object.__setattr__(self, '_proxy', proxy)
        object.__setattr__(self, '_index', index)

        object.__setattr__(self, '_env', m.env)
        object.__setattr__(self, '_model', m)

        # copy so we don't risk breaking it too much (?)
        fvg = dict(proxy._descr['edition_view'])
        object.__setattr__(self, '_view', fvg)
        self._process_fvg(m, fvg)

        vals = dict.fromkeys(fvg['fields'], False)
        object.__setattr__(self, '_values', vals)
        object.__setattr__(self, '_changed', set())
        if index is None:
            self._init_from_defaults(m)
        else:
            vals = proxy._records[index]
            self._values.update(vals)
            if hasattr(vals, '_changed'):
                self._changed.update(vals._changed)

    def _get_modifier(self, field, modifier, *, default=False, view=None, modmap=None, vals=None):
        if vals is None:
            vals = {**self._values, '•parent•': self._proxy._parent._values}

        return super()._get_modifier(field, modifier, default=default, view=view, modmap=modmap, vals=vals)

    def _onchange_values(self):
        values = super(O2MForm, self)._onchange_values()
        # computed o2m may not have a relation_field(?)
        descr = self._proxy._descr
        if 'relation_field' in descr: # note: should be fine because not recursive
            values[descr['relation_field']] = self._proxy._parent._onchange_values()
        return values

    def save(self):
        proxy = self._proxy
        commands = proxy._parent._values[proxy._field]
        values = self._values_to_save()
        if self._index is None:
            commands.append((0, 0, values))
        else:
            index = proxy._command_index(self._index)
            (c, id_, vs) = commands[index]
            if c == 0:
                vs.update(values)
            elif c == 1:
                if vs is None:
                    vs = UpdateDict()
                assert isinstance(vs, UpdateDict), type(vs)
                vs.update(values)
                commands[index] = (1, id_, vs)
            else:
                raise AssertionError("Expected command type 0 or 1, found %s" % c)

        # FIXME: should be called when performing on change => value needs to be serialised into parent every time?
        proxy._parent._perform_onchange([proxy._field])

    def _values_to_save(self, all_fields=False):
        """ Validates values and returns only fields modified since
        load/save
        """
        values = UpdateDict(self._values)
        values._changed.update(self._changed)
        if all_fields:
            return values

        for f in self._view['fields']:
            if self._get_modifier(f, 'required') and not (self._get_modifier(f, 'column_invisible') or self._get_modifier(f, 'invisible')):
                assert self._values[f] is not False, "{} is a required field".format(f)

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


class X2MProxy(object):
    _parent = None
    _field = None
    def _assert_editable(self):
        assert not self._parent._get_modifier(self._field, 'readonly'),\
            'field %s is not editable' % self._field
        assert not self._parent._get_modifier(self._field, 'invisible'),\
            'field %s is not visible' % self._field


class O2MProxy(X2MProxy):
    """ O2MProxy()
    """
    def __init__(self, parent, field):
        self._parent = parent
        self._field = field
        # reify records to a list so they can be manipulated easily?
        self._records = []
        model = self._model
        fields = self._descr['edition_view']['fields']
        for (command, rid, values) in self._parent._values[self._field]:
            if command == 0:
                self._records.append(values)
            elif command == 1:
                if values is None:
                    # read based on view info
                    r = model.browse(rid)
                    values = UpdateDict(record_to_values(fields, r))
                self._records.append(values)
            elif command == 2:
                pass
            else:
                raise AssertionError("O2M proxy only supports commands 0, 1 and 2, found %s" % command)

    def __len__(self):
        return len(self._records)

    @property
    def _model(self):
        model = self._parent._env[self._descr['relation']]
        ctx = self._parent._get_context(self._field)
        if ctx:
            model = model.with_context(**ctx)
        return model

    @property
    def _descr(self):
        return self._parent._view['fields'][self._field]

    def _command_index(self, for_record):
        """ Takes a record index and finds the corresponding record index
        (skips all 2s, basically)

        :param int for_record:
        """
        commands = self._parent._values[self._field]
        return next(
            cidx
            for ridx, cidx in enumerate(
                cidx for cidx, (c, _1, _2) in enumerate(commands)
                if c in (0, 1)
            )
            if ridx == for_record
        )

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
        commands = self._parent._values[self._field]
        (command, rid, _) = commands[cidx]
        if command == 0:
            # record not saved yet -> just remove the command
            del commands[cidx]
        elif command == 1:
            # record already saved, replace by 2
            commands[cidx] = (2, rid, 0)
        else:
            raise AssertionError("Expected command 0 or 1, got %s" % commands[cidx])
        # remove reified record
        del self._records[index]
        self._parent._perform_onchange([self._field])


class M2MProxy(X2MProxy, collections.abc.Sequence):
    """ M2MProxy()

    Behaves as a :class:`~collection.Sequence` of recordsets, can be
    indexed or sliced to get actual underlying recordsets.
    """
    def __init__(self, parent, field):
        self._parent = parent
        self._field = field

    def __getitem__(self, it):
        p = self._parent
        model = p._view['fields'][self._field]['relation']
        return p._env[model].browse(self._get_ids()[it])

    def __len__(self):
        return len(self._get_ids())

    def __iter__(self):
        return iter(self[:])

    def __contains__(self, record):
        relation_ = self._parent._view['fields'][self._field]['relation']
        assert isinstance(record, BaseModel)\
           and record._name == relation_

        return record.id in self._get_ids()


    def add(self, record):
        """ Adds ``record`` to the field, the record must already exist.

        The addition will only be finalized when the parent record is saved.
        """
        self._assert_editable()
        parent = self._parent
        relation_ = parent._view['fields'][self._field]['relation']
        assert isinstance(record, BaseModel) and record._name == relation_,\
            "trying to assign a '{}' object to a '{}' field".format(
                record._name,
                relation_,
            )
        self._get_ids().append(record.id)

        parent._perform_onchange([self._field])

    def _get_ids(self):
        return self._parent._values[self._field][0][2]

    def remove(self, id=None, index=None):
        """ Removes a record at a certain index or with a provided id from
        the field.
        """

        self._assert_editable()
        assert (id is None) ^ (index is None), \
            "can remove by either id or index"

        if id is None:
            # remove by index
            del self._get_ids()[index]
        else:
            self._get_ids().remove(id)

        self._parent._perform_onchange([self._field])

    def clear(self):
        """ Removes all existing records in the m2m
        """
        self._assert_editable()
        self._get_ids()[:] = []
        self._parent._perform_onchange([self._field])


def record_to_values(fields, record):
    r = {}
    # don't read the id explicitly, not sure why but if any of the "magic" hr
    # field is read alongside `id` then it blows up e.g.
    # james.read(['barcode']) works fine but james.read(['id', 'barcode'])
    # triggers an ACL error on barcode, likewise km_home_work or
    # emergency_contact or whatever. Since we always get the id anyway, just
    # remove it from the fields to read
    to_read = list(fields.keys() - {'id'})
    if not to_read:
        return r
    for f, v in record.read(to_read)[0].items():
        descr = fields[f]
        if descr['type'] == 'many2one':
            v = v and v[0]
        elif descr['type'] == 'many2many':
            v = [(6, 0, v or [])]
        elif descr['type'] == 'one2many':
            v = [(1, r, None) for r in v or []]
        elif descr['type'] == 'datetime' and isinstance(v, datetime):
            v = odoo.fields.Datetime.to_string(v)
        elif descr['type'] == 'date' and isinstance(v, date):
            v = odoo.fields.Date.to_string(v)
        r[f] = v
    return r


def _cleanup_from_default(type_, value):
    if not value:
        if type_ == 'many2many':
            return [(6, False, [])]
        elif type_ == 'one2many':
            return []
        elif type_ in ('integer', 'float'):
            return 0
        return value

    if type_ == 'one2many':
        return [c for c in value if c[0] != 6]
    elif type_ == 'datetime' and isinstance(value, datetime):
        return odoo.fields.Datetime.to_string(value)
    elif type_ == 'date' and isinstance(value, date):
        return odoo.fields.Date.to_string(value)
    return value


def _get_node(view, f, *arg):
    """ Find etree node for the field ``f`` in the view's arch
    """
    return next((
        n for n in view['tree'].iter('field')
        if n.get('name') == f
    ), *arg)
