# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" High-level objects for fields. """

from collections import OrderedDict, defaultdict
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from functools import partial
from operator import attrgetter
import itertools
import logging
import base64

import pytz

try:
    from xmlrpc.client import MAXINT
except ImportError:
    #pylint: disable=bad-python3-import
    from xmlrpclib import MAXINT

import psycopg2

from .tools import float_repr, float_round, frozendict, html_sanitize, human_size, pg_varchar, \
    ustr, OrderedSet, pycompat, sql, date_utils, unique, IterableGenerator
from .tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from .tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from .tools.translate import html_translate, _
from .tools.mimetypes import guess_mimetype

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))
EMPTY_DICT = frozendict()

RENAMED_ATTRS = [('select', 'index'), ('digits_compute', 'digits')]

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__[:-7] + '.schema')

Default = object()                      # default value for __init__() methods

def copy_cache(records, env):
    """ Recursively copy the cache of ``records`` to the environment ``env``. """
    env.cache.copy(records, env)

def first(records):
    """ Return the first record in ``records``, with the same prefetching. """
    return next(iter(records)) if len(records) > 1 else records


def resolve_mro(model, name, predicate):
    """ Return the list of successively overridden values of attribute ``name``
        in mro order on ``model`` that satisfy ``predicate``.
    """
    result = []
    for cls in type(model).__mro__:
        if name in cls.__dict__:
            value = cls.__dict__[name]
            if not predicate(value):
                break
            result.append(value)
    return result


class MetaField(type):
    """ Metaclass for field classes. """
    by_type = {}

    def __new__(meta, name, bases, attrs):
        """ Combine the ``_slots`` dict from parent classes, and determine
        ``__slots__`` for them on the new class.
        """
        base_slots = {}
        for base in reversed(bases):
            base_slots.update(getattr(base, '_slots', ()))

        slots = dict(base_slots)
        slots.update(attrs.get('_slots', ()))

        attrs['__slots__'] = set(slots) - set(base_slots)
        attrs['_slots'] = slots
        return type.__new__(meta, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        super(MetaField, cls).__init__(name, bases, attrs)
        if not hasattr(cls, 'type'):
            return

        if cls.type and cls.type not in MetaField.by_type:
            MetaField.by_type[cls.type] = cls

        # compute class attributes to avoid calling dir() on fields
        cls.related_attrs = []
        cls.description_attrs = []
        for attr in dir(cls):
            if attr.startswith('_related_'):
                cls.related_attrs.append((attr[9:], attr))
            elif attr.startswith('_description_'):
                cls.description_attrs.append((attr[13:], attr))

_global_seq = iter(itertools.count())
class Field(MetaField('DummyField', (object,), {})):
    """ The field descriptor contains the field definition, and manages accesses
        and assignments of the corresponding field on records. The following
        attributes may be provided when instanciating a field:

        :param string: the label of the field seen by users (string); if not
            set, the ORM takes the field name in the class (capitalized).

        :param help: the tooltip of the field seen by users (string)

        :param readonly: whether the field is readonly (boolean, by default ``False``)

        :param required: whether the value of the field is required (boolean, by
            default ``False``)

        :param index: whether the field is indexed in database. Note: no effect
            on non-stored and virtual fields. (boolean, by default ``False``)

        :param default: the default value for the field; this is either a static
            value, or a function taking a recordset and returning a value; use
            ``default=None`` to discard default values for the field

        :param states: a dictionary mapping state values to lists of UI attribute-value
            pairs; possible attributes are: 'readonly', 'required', 'invisible'.
            Note: Any state-based condition requires the ``state`` field value to be
            available on the client-side UI. This is typically done by including it in
            the relevant views, possibly made invisible if not relevant for the
            end-user.

        :param groups: comma-separated list of group xml ids (string); this
            restricts the field access to the users of the given groups only

        :param bool copy: whether the field value should be copied when the record
            is duplicated (default: ``True`` for normal fields, ``False`` for
            ``one2many`` and computed fields, including property fields and
            related fields)

        :param string oldname: the previous name of this field, so that ORM can rename
            it automatically at migration

        .. _field-computed:

        .. rubric:: Computed fields

        One can define a field whose value is computed instead of simply being
        read from the database. The attributes that are specific to computed
        fields are given below. To define such a field, simply provide a value
        for the attribute ``compute``.

        :param compute: name of a method that computes the field

        :param inverse: name of a method that inverses the field (optional)

        :param search: name of a method that implement search on the field (optional)

        :param store: whether the field is stored in database (boolean, by
            default ``False`` on computed fields)

        :param compute_sudo: whether the field should be recomputed as superuser
            to bypass access rights (boolean, by default ``False``)
            Note that this has no effects on non-stored computed fields

        The methods given for ``compute``, ``inverse`` and ``search`` are model
        methods. Their signature is shown in the following example::

            upper = fields.Char(compute='_compute_upper',
                                inverse='_inverse_upper',
                                search='_search_upper')

            @api.depends('name')
            def _compute_upper(self):
                for rec in self:
                    rec.upper = rec.name.upper() if rec.name else False

            def _inverse_upper(self):
                for rec in self:
                    rec.name = rec.upper.lower() if rec.upper else False

            def _search_upper(self, operator, value):
                if operator == 'like':
                    operator = 'ilike'
                return [('name', operator, value)]

        The compute method has to assign the field on all records of the invoked
        recordset. The decorator :meth:`odoo.api.depends` must be applied on
        the compute method to specify the field dependencies; those dependencies
        are used to determine when to recompute the field; recomputation is
        automatic and guarantees cache/database consistency. Note that the same
        method can be used for several fields, you simply have to assign all the
        given fields in the method; the method will be invoked once for all
        those fields.

        By default, a computed field is not stored to the database, and is
        computed on-the-fly. Adding the attribute ``store=True`` will store the
        field's values in the database. The advantage of a stored field is that
        searching on that field is done by the database itself. The disadvantage
        is that it requires database updates when the field must be recomputed.

        The inverse method, as its name says, does the inverse of the compute
        method: the invoked records have a value for the field, and you must
        apply the necessary changes on the field dependencies such that the
        computation gives the expected value. Note that a computed field without
        an inverse method is readonly by default.

        The search method is invoked when processing domains before doing an
        actual search on the model. It must return a domain equivalent to the
        condition: ``field operator value``.

        .. _field-related:

        .. rubric:: Related fields

        The value of a related field is given by following a sequence of
        relational fields and reading a field on the reached model. The complete
        sequence of fields to traverse is specified by the attribute

        :param related: sequence of field names

        Some field attributes are automatically copied from the source field if
        they are not redefined: ``string``, ``help``, ``readonly``, ``required`` (only
        if all fields in the sequence are required), ``groups``, ``digits``, ``size``,
        ``translate``, ``sanitize``, ``selection``, ``comodel_name``, ``domain``,
        ``context``. All semantic-free attributes are copied from the source
        field.

        By default, the values of related fields are not stored to the database.
        Add the attribute ``store=True`` to make it stored, just like computed
        fields. Related fields are automatically recomputed when their
        dependencies are modified.

        .. _field-company-dependent:

        .. rubric:: Company-dependent fields

        Formerly known as 'property' fields, the value of those fields depends
        on the company. In other words, users that belong to different companies
        may see different values for the field on a given record.

        :param company_dependent: whether the field is company-dependent (boolean)

        .. _field-incremental-definition:

        .. rubric:: Incremental definition

        A field is defined as class attribute on a model class. If the model
        is extended (see :class:`~odoo.models.Model`), one can also extend
        the field definition by redefining a field with the same name and same
        type on the subclass. In that case, the attributes of the field are
        taken from the parent class and overridden by the ones given in
        subclasses.

        For instance, the second class below only adds a tooltip on the field
        ``state``::

            class First(models.Model):
                _name = 'foo'
                state = fields.Selection([...], required=True)

            class Second(models.Model):
                _inherit = 'foo'
                state = fields.Selection(help="Blah blah blah")

    """

    type = None                         # type of the field (string)
    relational = False                  # whether the field is a relational one
    translate = False                   # whether the field is translated

    column_type = None                  # database column type (ident, spec)
    column_format = '%s'                # placeholder for value in queries
    column_cast_from = ()               # column types that may be cast to this

    _slots = {
        'args': EMPTY_DICT,             # the parameters given to __init__()
        '_attrs': EMPTY_DICT,           # the field's non-slot attributes
        '_module': None,                # the field's module name
        '_modules': None,               # modules that define this field
        '_setup_done': None,            # the field's setup state: None, 'base' or 'full'
        '_sequence': None,              # absolute ordering of the field

        'automatic': False,             # whether the field is automatically created ("magic" field)
        'inherited': False,             # whether the field is inherited (_inherits)
        'inherited_field': None,        # the corresponding inherited field

        'name': None,                   # name of the field
        'model_name': None,             # name of the model of this field
        'comodel_name': None,           # name of the model of values (if relational)

        'store': True,                  # whether the field is stored in database
        'index': False,                 # whether the field is indexed in database
        'manual': False,                # whether the field is a custom field
        'copy': True,                   # whether the field is copied over by BaseModel.copy()
        'depends': None,                # collection of field dependencies
        'recursive': False,             # whether self depends on itself
        'compute': None,                # compute(recs) computes field on recs
        'compute_sudo': False,          # whether field should be recomputed as admin
        'inverse': None,                # inverse(recs) inverses field on recs
        'search': None,                 # search(recs, operator, value) searches on self
        'related': None,                # sequence of field names, for related fields
        'related_sudo': True,           # whether related fields should be read as admin
        'company_dependent': False,     # whether ``self`` is company-dependent (property field)
        'default': None,                # default(recs) returns the default value

        'string': None,                 # field label
        'help': None,                   # field tooltip
        'readonly': False,              # whether the field is readonly
        'required': False,              # whether the field is required
        'states': None,                 # set readonly and required depending on state
        'groups': None,                 # csv list of group xml ids
        'change_default': False,        # whether the field may trigger a "user-onchange"
        'deprecated': None,             # whether the field is deprecated

        'related_field': None,          # corresponding related field
        'group_operator': None,         # operator for aggregating values
        'group_expand': None,           # name of method to expand groups in read_group()
        'prefetch': True,               # whether the field is prefetched
        'context_dependent': False,     # whether the field's value depends on context
    }

    def __init__(self, string=Default, **kwargs):
        kwargs['string'] = string
        self._sequence = kwargs['_sequence'] = next(_global_seq)
        args = {key: val for key, val in kwargs.items() if val is not Default}
        self.args = args or EMPTY_DICT
        self._setup_done = None

    def new(self, **kwargs):
        """ Return a field of the same type as ``self``, with its own parameters. """
        return type(self)(**kwargs)

    def __getattr__(self, name):
        """ Access non-slot field attribute. """
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """ Set slot or non-slot field attribute. """
        try:
            object.__setattr__(self, name, value)
        except AttributeError:
            if self._attrs:
                self._attrs[name] = value
            else:
                self._attrs = {name: value}     # replace EMPTY_DICT

    def set_all_attrs(self, attrs):
        """ Set all field attributes at once (with slot defaults). """
        # optimization: we assign slots only
        assign = object.__setattr__
        for key, val in self._slots.items():
            assign(self, key, attrs.pop(key, val))
        if attrs:
            assign(self, '_attrs', attrs)

    def __delattr__(self, name):
        """ Remove non-slot field attribute. """
        try:
            del self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return "%s.%s" % (self.model_name, self.name)

    def __repr__(self):
        return "%s.%s" % (self.model_name, self.name)

    ############################################################################
    #
    # Base field setup: things that do not depend on other models/fields
    #

    def setup_base(self, model, name):
        """ Base setup: things that do not depend on other models/fields. """
        if self._setup_done and not self.related:
            # optimization for regular fields: keep the base setup
            self._setup_done = 'base'
        else:
            # do the base setup from scratch
            self._setup_attrs(model, name)
            if not self.related:
                self._setup_regular_base(model)
            self._setup_done = 'base'

    #
    # Setup field parameter attributes
    #

    def _can_setup_from(self, field):
        """ Return whether ``self`` can retrieve parameters from ``field``. """
        return isinstance(field, type(self))

    def _get_attrs(self, model, name):
        """ Return the field parameter attributes as a dictionary. """
        # determine all inherited field attributes
        modules = set()
        attrs = {}
        if not (self.args.get('automatic') or self.args.get('manual')):
            # magic and custom fields do not inherit from parent classes
            for field in reversed(resolve_mro(model, name, self._can_setup_from)):
                attrs.update(field.args)
                if '_module' in field.args:
                    modules.add(field.args['_module'])
        attrs.update(self.args)         # necessary in case self is not in class

        attrs['args'] = self.args
        attrs['model_name'] = model._name
        attrs['name'] = name
        attrs['_modules'] = modules

        # initialize ``self`` with ``attrs``
        if attrs.get('compute'):
            # by default, computed fields are not stored, not copied and readonly
            attrs['store'] = attrs.get('store', False)
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))
            attrs['context_dependent'] = attrs.get('context_dependent', True)
        if attrs.get('related'):
            # by default, related fields are not stored and not copied
            attrs['store'] = attrs.get('store', False)
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', True)
        if attrs.get('company_dependent'):
            # by default, company-dependent fields are not stored and not copied
            attrs['store'] = False
            attrs['copy'] = attrs.get('copy', False)
            attrs['default'] = self._default_company_dependent
            attrs['compute'] = self._compute_company_dependent
            if not attrs.get('readonly'):
                attrs['inverse'] = self._inverse_company_dependent
            attrs['search'] = self._search_company_dependent
            attrs['context_dependent'] = attrs.get('context_dependent', True)
        if attrs.get('translate'):
            # by default, translatable fields are context-dependent
            attrs['context_dependent'] = attrs.get('context_dependent', True)
        if 'depends' in attrs:
            attrs['depends'] = tuple(attrs['depends'])

        return attrs

    def _setup_attrs(self, model, name):
        """ Initialize the field parameter attributes. """
        attrs = self._get_attrs(model, name)
        self.set_all_attrs(attrs)

        # check for renamed attributes (conversion errors)
        for key1, key2 in RENAMED_ATTRS:
            if key1 in attrs:
                _logger.warning("Field %s: parameter %r is no longer supported; use %r instead.",
                                self, key1, key2)

        # prefetch only stored, column, non-manual and non-deprecated fields
        if not (self.store and self.column_type) or self.manual or self.deprecated:
            self.prefetch = False

        if not self.string and not self.related:
            # related fields get their string from their parent field
            self.string = (
                name[:-4] if name.endswith('_ids') else
                name[:-3] if name.endswith('_id') else name
            ).replace('_', ' ').title()

        # self.default must be a callable
        if self.default is not None:
            value = self.default
            self.default = value if callable(value) else lambda model: value

    ############################################################################
    #
    # Full field setup: everything else, except recomputation triggers
    #

    def setup_full(self, model):
        """ Full setup: everything else, except recomputation triggers. """
        if self._setup_done != 'full':
            if not self.related:
                self._setup_regular_full(model)
            else:
                self._setup_related_full(model)
            self._setup_done = 'full'

    #
    # Setup of non-related fields
    #

    def _setup_regular_base(self, model):
        """ Setup the attributes of a non-related field. """
        if self.depends is not None:
            return

        def get_depends(func):
            deps = getattr(func, '_depends', ())
            return deps(model) if callable(deps) else deps

        if isinstance(self.compute, str):
            # if the compute method has been overridden, concatenate all their _depends
            self.depends = tuple(
                dep
                for method in resolve_mro(model, self.compute, callable)
                for dep in get_depends(method)
            )
        else:
            self.depends = tuple(get_depends(self.compute))

    def _setup_regular_full(self, model):
        """ Setup the inverse field(s) of ``self``. """
        pass

    #
    # Setup of related fields
    #

    def _setup_related_full(self, model):
        """ Setup the attributes of a related field. """
        # fix the type of self.related if necessary
        if isinstance(self.related, str):
            self.related = tuple(self.related.split('.'))

        # determine the chain of fields, and make sure they are all set up
        target = model
        for name in self.related:
            field = target._fields[name]
            field.setup_full(target)
            target = target[name]

        self.related_field = field

        # check type consistency
        if self.type != field.type:
            raise TypeError("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        if self.depends is None:
            self.depends = ('.'.join(self.related),)
        self.compute = self._compute_related
        if not (self.readonly or field.readonly):
            self.inverse = self._inverse_related
        if field._description_searchable:
            # allow searching on self only if the related field is searchable
            self.search = self._search_related

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            if not getattr(self, attr):
                setattr(self, attr, getattr(field, prop))

        for attr, value in field._attrs.items():
            if attr not in self._attrs:
                setattr(self, attr, value)

        # special case for states: copy it only for inherited fields
        if not self.states and self.inherited:
            self.states = field.states

        # special case for inherited required fields
        if self.inherited and field.required:
            self.required = True

        if self.inherited:
            self._modules.update(field._modules)

    def traverse_related(self, record):
        """ Traverse the fields of the related field `self` except for the last
        one, and return it as a pair `(last_record, last_field)`. """
        for name in self.related[:-1]:
            record = first(record[name])
        return record, self.related_field

    def _compute_related(self, records):
        """ Compute the related field ``self`` on ``records``. """
        # when related_sudo, bypass access rights checks when reading values
        others = records.sudo() if self.related_sudo else records
        # copy the cache of draft records into others' cache
        if not all(records._ids) and records.env != others.env:
            copy_cache(records - records.filtered('id'), others.env)
        #
        # Traverse fields one by one for all records, in order to take advantage
        # of prefetching for each field access. In order to clarify the impact
        # of the algorithm, consider traversing 'foo.bar' for records a1 and a2,
        # where 'foo' is already present in cache for a1, a2. Initially, both a1
        # and a2 are marked for prefetching. As the commented code below shows,
        # traversing all fields one record at a time will fetch 'bar' one record
        # at a time.
        #
        #       b1 = a1.foo         # mark b1 for prefetching
        #       v1 = b1.bar         # fetch/compute bar for b1
        #       b2 = a2.foo         # mark b2 for prefetching
        #       v2 = b2.bar         # fetch/compute bar for b2
        #
        # On the other hand, traversing all records one field at a time ensures
        # maximal prefetching for each field access.
        #
        #       b1 = a1.foo         # mark b1 for prefetching
        #       b2 = a2.foo         # mark b2 for prefetching
        #       v1 = b1.bar         # fetch/compute bar for b1, b2
        #       v2 = b2.bar         # value already in cache
        #
        # This difference has a major impact on performance, in particular in
        # the case where 'bar' is a computed field that takes advantage of batch
        # computation.
        #
        values = list(others)
        for name in self.related[:-1]:
            try:
                values = [first(value[name]) for value in values]
            except AccessError as e:
                description = records.env['ir.model']._get(records._name).name
                raise AccessError(
                    _("%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).") % {
                        'previous_message': e.args[0],
                        'document_kind': description,
                        'document_model': records._name,
                    }
                )
        # assign final values to records
        for record, value in zip(records, values):
            record[self.name] = value[self.related_field.name]

    def _inverse_related(self, records):
        """ Inverse the related field ``self`` on ``records``. """
        # store record values, otherwise they may be lost by cache invalidation!
        record_value = {record: record[self.name] for record in records}
        for record in records:
            other, field = self.traverse_related(record)
            if other:
                other[field.name] = record_value[record]

    def _search_related(self, records, operator, value):
        """ Determine the domain to search on field ``self``. """
        return [('.'.join(self.related), operator, value)]

    # properties used by _setup_related_full() to copy values from related field
    _related_comodel_name = property(attrgetter('comodel_name'))
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_groups = property(attrgetter('groups'))
    _related_group_operator = property(attrgetter('group_operator'))
    _related_context_dependent = property(attrgetter('context_dependent'))

    @property
    def base_field(self):
        """ Return the base field of an inherited field, or ``self``. """
        return self.inherited_field.base_field if self.inherited_field else self

    #
    # Company-dependent fields
    #

    def _default_company_dependent(self, model):
        return model.env['ir.property'].get(self.name, self.model_name)

    def _compute_company_dependent(self, records):
        # read property as superuser, as the current user may not have access
        context = records.env.context
        if 'force_company' not in context:
            company = records.env.company
            context = dict(context, force_company=company.id)
        Property = records.env(context=context, su=True)['ir.property']
        values = Property.get_multi(self.name, self.model_name, records.ids)
        for record in records:
            record[self.name] = values.get(record.id)

    def _inverse_company_dependent(self, records):
        # update property as superuser, as the current user may not have access
        context = records.env.context
        if 'force_company' not in context:
            company = records.env.company
            context = dict(context, force_company=company.id)
        Property = records.env(context=context, su=True)['ir.property']
        values = {
            record.id: self.convert_to_write(record[self.name], record)
            for record in records
        }
        Property.set_multi(self.name, self.model_name, values)

    def _search_company_dependent(self, records, operator, value):
        Property = records.env['ir.property']
        return Property.search_multi(self.name, self.model_name, operator, value)

    #
    # Setup of field triggers
    #
    # The triggers of a field F is a tree that contains the fields that depend
    # on F, together with the fields to inverse to find out which records to
    # recompute.
    #
    # For instance, assume that G depends on F, H depends on X.F, I depends on
    # W.X.F, and J depends on Y.F. The triggers of F will be the tree:
    #
    #                                   [G]
    #                                 X/   \Y
    #                               [H]     [J]
    #                             W/
    #                           [I]
    #
    # This tree provides perfect support for the trigger mechanism:
    # when F is # modified on records,
    #  - mark G to recompute on records,
    #  - mark H to recompute on inverse(X, records),
    #  - mark I to recompute on inverse(W, inverse(X, records)),
    #  - mark J to recompute on inverse(Y, records).

    def setup_triggers(self, model):
        def add_trigger(field, path):
            """ add a trigger on field to recompute self """
            field_model = model.env[field.model_name]
            node = field_model._field_triggers.setdefault(field, {})
            for f in reversed(path):
                node = node.setdefault(f, {})
            node.setdefault(None, []).append(self)

        for dotnames in self.depends:
            field_model = model
            path = []                   # fields from model to field_model
            for fname in dotnames.split('.'):
                field = field_model._fields[fname]
                add_trigger(field, path)

                if (field is self) and path:
                    self.recursive = True

                path.append(field)
                if field.type in ('one2many', 'many2many'):
                    for inv_field in field_model._field_inverses[field]:
                        add_trigger(inv_field, path)

                field_model = model.env.get(field.comodel_name)

    ############################################################################
    #
    # Field description
    #

    def get_description(self, env):
        """ Return a dictionary that describes the field ``self``. """
        desc = {'type': self.type}
        for attr, prop in self.description_attrs:
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value is not None:
                desc[attr] = value

        return desc

    # properties used by get_description()
    _description_store = property(attrgetter('store'))
    _description_manual = property(attrgetter('manual'))
    _description_depends = property(attrgetter('depends'))
    _description_related = property(attrgetter('related'))
    _description_company_dependent = property(attrgetter('company_dependent'))
    _description_readonly = property(attrgetter('readonly'))
    _description_required = property(attrgetter('required'))
    _description_states = property(attrgetter('states'))
    _description_groups = property(attrgetter('groups'))
    _description_change_default = property(attrgetter('change_default'))
    _description_deprecated = property(attrgetter('deprecated'))
    _description_group_operator = property(attrgetter('group_operator'))

    @property
    def _description_searchable(self):
        return bool(self.store or self.search)

    @property
    def _description_sortable(self):
        return self.store or (self.inherited and self.related_field._description_sortable)

    def _description_string(self, env):
        if self.string and env.lang:
            model_name = self.base_field.model_name
            field_string = env['ir.translation'].get_field_string(model_name)
            return field_string.get(self.name) or self.string
        return self.string

    def _description_help(self, env):
        if self.help and env.lang:
            model_name = self.base_field.model_name
            field_help = env['ir.translation'].get_field_help(model_name)
            return field_help.get(self.name) or self.help
        return self.help

    ############################################################################
    #
    # Conversion of values
    #

    def null(self, record):
        """ Return the null value for this field in the record format. """
        return False

    def convert_to_column(self, value, record, values=None, validate=True):
        """ Convert ``value`` from the ``write`` format to the SQL format. """
        if value is None or value is False:
            return None
        return pycompat.to_text(value)

    def convert_to_cache(self, value, record, validate=True):
        """ Convert ``value`` to the cache format; ``value`` may come from an
        assignment, or have the format of methods :meth:`BaseModel.read` or
        :meth:`BaseModel.write`. If the value represents a recordset, it should
        be added for prefetching on ``record``.

        :param bool validate: when True, field-specific validation of ``value``
            will be performed
        """
        return value

    def convert_to_record(self, value, record):
        """ Convert ``value`` from the cache format to the record format.
        If the value represents a recordset, it should share the prefetching of
        ``record``.
        """
        return value

    def convert_to_read(self, value, record, use_name_get=True):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.read`.

        :param bool use_name_get: when True, the value's display name will be
            computed using :meth:`BaseModel.name_get`, if relevant for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, record):
        """ Convert ``value`` from the record format to the format of method
        :meth:`BaseModel.write`.
        """
        return self.convert_to_read(value, record)

    def convert_to_onchange(self, value, record, names):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.onchange`.

        :param names: a tree of field names (for relational fields only)
        """
        return self.convert_to_read(value, record)

    def convert_to_export(self, value, record):
        """ Convert ``value`` from the record format to the export format. """
        if not value:
            return ''
        return value if record._context.get('export_raw_data') else ustr(value)

    def convert_to_display_name(self, value, record):
        """ Convert ``value`` from the record format to a suitable display name. """
        return ustr(value)

    ############################################################################
    #
    # Update database schema
    #

    def update_db(self, model, columns):
        """ Update the database schema to implement this field.

            :param model: an instance of the field's model
            :param columns: a dict mapping column names to their configuration in database
            :return: ``True`` if the field must be recomputed on existing rows
        """
        if not self.column_type:
            return

        column = columns.get(self.name)
        if not column and hasattr(self, 'oldname'):
            # column not found; check whether it exists under its old name
            column = columns.get(self.oldname)
            if column:
                sql.rename_column(model._cr, model._table, self.oldname, self.name)

        # create/update the column, not null constraint, indexes
        self.update_db_column(model, column)
        self.update_db_notnull(model, column)
        self.update_db_index(model, column)

        return not column

    def update_db_column(self, model, column):
        """ Create/update the column corresponding to ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        if not column:
            # the column does not exist, create it
            sql.create_column(model._cr, model._table, self.name, self.column_type[1], self.string)
            return
        if column['udt_name'] == self.column_type[0]:
            return
        if column['udt_name'] in self.column_cast_from:
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])
        else:
            newname = (self.name + '_moved{}').format
            i = 0
            while sql.column_exists(model._cr, model._table, newname(i)):
                i += 1
            if column['is_nullable'] == 'NO':
                sql.drop_not_null(model._cr, model._table, self.name)
            sql.rename_column(model._cr, model._table, self.name, newname(i))
            sql.create_column(model._cr, model._table, self.name, self.column_type[1], self.string)

    def update_db_notnull(self, model, column):
        """ Add or remove the NOT NULL constraint on ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        has_notnull = column and column['is_nullable'] == 'NO'

        if not column or (self.required and not has_notnull):
            # the column is new or it becomes required; initialize its values
            if model._table_has_rows():
                model._init_column(self.name)

        if self.required and not has_notnull:
            sql.set_not_null(model._cr, model._table, self.name)
        elif not self.required and has_notnull:
            sql.drop_not_null(model._cr, model._table, self.name)

    def update_db_index(self, model, column):
        """ Add or remove the index corresponding to ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        indexname = '%s_%s_index' % (model._table, self.name)
        if self.index:
            try:
                with model._cr.savepoint():
                    sql.create_index(model._cr, indexname, model._table, ['"%s"' % self.name])
            except psycopg2.OperationalError:
                _schema.error("Unable to add index for %s", self)
        else:
            sql.drop_index(model._cr, indexname, model._table)

    ############################################################################
    #
    # Read from/write to database
    #

    def read(self, records):
        """ Read the value of ``self`` on ``records``, and store it in cache. """
        return NotImplementedError("Method read() undefined on %s" % self)

    def create(self, record_values):
        """ Write the value of ``self`` on the given records, which have just
        been created.

        :param record_values: a list of pairs ``(record, value)``, where
            ``value`` is in the format of method :meth:`BaseModel.write`
        """
        for record, value in record_values:
            self.write(record, value)

    def write(self, records, value):
        """ Write the value of ``self`` on ``records``.

        :param value: a value in the format of method :meth:`BaseModel.write`
        """
        return NotImplementedError("Method write() undefined on %s" % self)

    ############################################################################
    #
    # Descriptor methods
    #

    def __get__(self, record, owner):
        """ return the value of field ``self`` on ``record`` """
        if record is None:
            return self         # the field is accessed through the owner class

        if not record._ids:
            # null record -> return the null value for this field
            value = self.convert_to_cache(False, record, validate=False)
            return self.convert_to_record(value, record)

        env = record.env

        # only a single record may be accessed
        record.ensure_one()
        if env.check_todo(self, record) and record not in env.protected(self):
            recs = record if self.recursive else env.field_todo(self)
            self.compute_value(recs)

        if not env.cache.contains(record, self):
            if record.id:
                # real record
                if self.store:
                    recs = record._in_cache_without(self)
                    try:
                        recs._fetch_field(self)
                    except AccessError:
                        record._fetch_field(self)

                elif self.compute:
                    recs = self.recursive and record or record._in_cache_without(self)
                    try:
                        # DLE P35: `test_11_computed_access`
                        # Prefetch compute fields for which we don't have the access. Same case than just above here
                        self.compute_value(recs)
                    except AccessError:
                        self.compute_value(record)

                else:
                    value = self.convert_to_cache(False, record, validate=False)
                    env.cache.set(record, self, value)

            else:
                if self.compute:
                    # RCO TODO: compute_sudo is not handled here
                    self.compute_value(record)

                elif record._origin:
                    # retrieve value from origin record
                    value = self.convert_to_cache(record._origin[self.name], record)
                    env.cache.set(record, self, value)

                elif self.type == 'many2one' and self.delegate:
                    # special case: parent records are new as well
                    parent = record.env[self.comodel_name].new()
                    value = self.convert_to_cache(parent, record)
                    env.cache.set(record, self, value)

                else:
                    value = self.convert_to_cache(False, record, validate=False)
                    env.cache.set(record, self, value)

                    defaults = record.default_get([self.name])
                    if self.name in defaults:
                        # The null value above is necessary to convert x2many field values.
                        # For instance, converting [(4, id)] accesses the field's current
                        # value, then adds the given id. Without an initial value, the
                        # conversion ends up here to determine the field's value, and this
                        # generates an infinite recursion.
                        value = self.convert_to_cache(defaults[self.name], record)
                        env.cache.set(record, self, value)

        # raise access rights here instead of in the end of read()
        value = env.cache.get(record, self)

        return self.convert_to_record(value, record)

    def __set__(self, records, value):
        """ set the value of field ``self`` on ``records`` """
        # DLE P34: `test_01_basic_set_assertion
        # You should not be able to assign on a single record. Or if you believe we should from now on, then the test must be changed.
        # only a single record may be updated
        records.ensure_one()
        # DLE P18: need to convert to write the value, at least for *2many
        # Some write overwrites expects the *2many values to be tuple commands and not browse record
        # See https://github.com/odoo/odoo/blob/659ff0da13951d0b940c24a070a4a7e51b0897bb/odoo/addons/base/models/res_users.py#L934
        # test `test_bindings`, `action2.groups_id += group`
        write_value = self.convert_to_write(value, records) if isinstance(value, BaseModel) else value
        # DLE P29: issue with `write` overwrite of `/mail/models/mail_thread.py`
        # Before calling super, it tried to get the value of computed field, which therefore recalled "write"
        # therefore recalling the write overwrite of `mail`, therefore creating an infinite loop.
        if self.compute:
            not_protected = (records - records.env.protected(self))
            if not_protected:
                not_protected.write({self.name: write_value})
            protecteds = (records & records.env.protected(self))
            if protecteds:
                for record in protecteds:
                    record.env.cache.set(record, self, self.convert_to_cache(value, record))
                    if record.id and self.store:
                        record.env.all.towrite[record._name][record.id][self.name] = write_value
        else:
            records.write({self.name: write_value})


    ############################################################################
    #
    # Computation of field values
    #

    def compute_value(self, records):
        """ Invoke the compute method on ``records``; the results are in cache. """
        fields = records._field_computed[self]
        # DLE P29: This is part of P29. See other comment.
        with records.env.protecting(fields, records):
            if isinstance(self.compute, str):
                getattr(records, self.compute)()
            else:
                self.compute(records)

        # even if __set__ already removed the todo, compute method might not set a value
        for field in fields:
            records.env.remove_todo(field, records)

    def determine_inverse(self, records):
        """ Given the value of ``self`` on ``records``, inverse the computation. """
        # DLE P38: `test_13_inverse`
        fields = records._field_computed[self]
        # if we are in the inverse of a field, don't call its compute
        records = records - records.env.protected(self)
        with records.env.protecting(fields, records):
            if isinstance(self.inverse, str):
                getattr(records, self.inverse)()
            else:
                self.inverse(records)

    def determine_domain(self, records, operator, value):
        """ Return a domain representing a condition on ``self``. """
        if isinstance(self.search, str):
            return getattr(records, self.search)(operator, value)
        else:
            return self.search(records, operator, value)

    ############################################################################
    #
    # Notification when fields are modified
    #


class Boolean(Field):
    type = 'boolean'
    column_type = ('bool', 'bool')

    def convert_to_column(self, value, record, values=None, validate=True):
        return bool(value)

    def convert_to_cache(self, value, record, validate=True):
        return bool(value)

    def convert_to_export(self, value, record):
        if record._context.get('export_raw_data'):
            return value
        return ustr(value)


class Integer(Field):
    type = 'integer'
    column_type = ('int4', 'int4')
    _slots = {
        'group_operator': 'sum',
    }

    def convert_to_column(self, value, record, values=None, validate=True):
        return int(value or 0)

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, dict):
            # special case, when an integer field is used as inverse for a one2many
            return value.get('id', False)
        return int(value or 0)

    def convert_to_read(self, value, record, use_name_get=True):
        # Integer values greater than 2^31-1 are not supported in pure XMLRPC,
        # so we have to pass them as floats :-(
        if value and value > MAXINT:
            return float(value)
        return value

    def _update(self, records, value):
        # special case, when an integer field is used as inverse for a one2many
        cache = records.env.cache
        for record in records:
            cache.set(record, self, value.id or 0)

    def convert_to_export(self, value, record):
        if value or value == 0:
            return value if record._context.get('export_raw_data') else ustr(value)
        return ''


class Float(Field):
    """ The precision digits are given by the attribute

    :param digits: a pair (total, decimal), or a function taking a database
                   cursor and returning a pair (total, decimal)
    """
    type = 'float'
    column_cast_from = ('int4', 'numeric', 'float8')
    _slots = {
        '_digits': None,                # digits argument passed to class initializer
        'group_operator': 'sum',
    }

    def __init__(self, string=Default, digits=Default, **kwargs):
        super(Float, self).__init__(string=string, _digits=digits, **kwargs)

    @property
    def column_type(self):
        # Explicit support for "falsy" digits (0, False) to indicate a NUMERIC
        # field with no fixed precision. The values are saved in the database
        # with all significant digits.
        # FLOAT8 type is still the default when there is no precision because it
        # is faster for most operations (sums, etc.)
        return ('numeric', 'numeric') if self._digits is not None else \
               ('float8', 'double precision')

    def get_digits(self, env):
        if isinstance(self._digits, str):
            precision = env['decimal.precision'].precision_get(self._digits)
            return 16, precision
        else:
            return self._digits

    _related__digits = property(attrgetter('_digits'))

    def _description_digits(self, env):
        return self.get_digits(env)

    def convert_to_column(self, value, record, values=None, validate=True):
        result = float(value or 0.0)
        digits = self.get_digits(record.env)
        if digits:
            precision, scale = digits
            result = float_repr(float_round(result, precision_digits=scale), precision_digits=scale)
        return result

    def convert_to_cache(self, value, record, validate=True):
        # apply rounding here, otherwise value in cache may be wrong!
        value = float(value or 0.0)
        if not validate:
            return value
        digits = self.get_digits(record.env)
        return float_round(value, precision_digits=digits[1]) if digits else value

    def convert_to_export(self, value, record):
        if value or value == 0.0:
            return value if record._context.get('export_raw_data') else ustr(value)
        return ''


class Monetary(Field):
    """ The decimal precision and currency symbol are taken from the attribute

    :param currency_field: name of the field holding the currency this monetary
                           field is expressed in (default: `currency_id`)
    """
    type = 'monetary'
    column_type = ('numeric', 'numeric')
    column_cast_from = ('float8',)
    _slots = {
        'currency_field': None,
        'group_operator': 'sum',
    }

    def __init__(self, string=Default, currency_field=Default, **kwargs):
        super(Monetary, self).__init__(string=string, currency_field=currency_field, **kwargs)

    _description_currency_field = property(attrgetter('currency_field'))

    def _setup_currency_field(self, model):
        if not self.currency_field:
            # pick a default, trying in order: 'currency_id', 'x_currency_id'
            if 'currency_id' in model._fields:
                self.currency_field = 'currency_id'
            elif 'x_currency_id' in model._fields:
                self.currency_field = 'x_currency_id'
        assert self.currency_field in model._fields, \
            "Field %s with unknown currency_field %r" % (self, self.currency_field)

    def _setup_regular_full(self, model):
        super(Monetary, self)._setup_regular_full(model)
        self._setup_currency_field(model)

    def _setup_related_full(self, model):
        super(Monetary, self)._setup_related_full(model)
        if self.inherited:
            self.currency_field = self.related_field.currency_field
        self._setup_currency_field(model)

    def convert_to_column(self, value, record, values=None, validate=True):
        # retrieve currency from values or record
        if values and self.currency_field in values:
            field = record._fields[self.currency_field]
            currency = field.convert_to_cache(values[self.currency_field], record, validate)
            currency = field.convert_to_record(currency, record)
        else:
            # Note: this is wrong if 'record' is several records with different
            # currencies, which is functional nonsense and should not happen
            currency = record[:1][self.currency_field]

        value = float(value or 0.0)
        if currency:
            return float_repr(currency.round(value), currency.decimal_places)
        return value

    def convert_to_cache(self, value, record, validate=True):
        # cache format: float
        value = float(value or 0.0)
        if validate and record[self.currency_field]:
            # FIXME @rco-odoo: currency may not be already initialized if it is
            # a function or related field!
            value = record[self.currency_field].round(value)
        return value

    def convert_to_read(self, value, record, use_name_get=True):
        return value

    def convert_to_write(self, value, record):
        return value


class _String(Field):
    """ Abstract class for string fields. """
    _slots = {
        'translate': False,             # whether the field is translated
    }

    def __init__(self, string=Default, **kwargs):
        # translate is either True, False, or a callable
        if 'translate' in kwargs and not callable(kwargs['translate']):
            kwargs['translate'] = bool(kwargs['translate'])
        super(_String, self).__init__(string=string, **kwargs)

    _related_translate = property(attrgetter('translate'))

    def _description_translate(self, env):
        return bool(self.translate)

    def get_trans_terms(self, value):
        """ Return the sequence of terms to translate found in `value`. """
        if not callable(self.translate):
            return [value] if value else []
        terms = []
        self.translate(terms.append, value)
        return terms

    def get_trans_func(self, records):
        """ Return a translation function `translate` for `self` on the given
        records; the function call `translate(record_id, value)` translates the
        field value to the language given by the environment of `records`.
        """
        if callable(self.translate):
            rec_src_trans = records.env['ir.translation']._get_terms_translations(self, records)

            def translate(record_id, value):
                src_trans = rec_src_trans[record_id]
                return self.translate(src_trans.get, value)

        else:
            rec_trans = records.env['ir.translation']._get_ids(
                '%s,%s' % (self.model_name, self.name), 'model', records.env.lang, records.ids)

            def translate(record_id, value):
                return rec_trans.get(record_id) or value

        return translate

    def check_trans_value(self, value):
        """ Check and possibly sanitize the translated term `value`. """
        if callable(self.translate):
            # do a "no-translation" to sanitize the value
            callback = lambda term: None
            return self.translate(callback, value)
        else:
            return value


class Char(_String):
    """ Basic string field, can be length-limited, usually displayed as a
    single-line string in clients.

    :param int size: the maximum size of values stored for that field

    :param bool trim: states whether the value is trimmed or not (by default,
        ``True``). Note that the trim operation is applied only by the web client.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    """
    type = 'char'
    column_cast_from = ('text',)
    _slots = {
        'size': None,                   # maximum size of values (deprecated)
        'trim': True,                   # whether value is trimmed (only by web client)
    }

    @property
    def column_type(self):
        return ('varchar', pg_varchar(self.size))

    def update_db_column(self, model, column):
        if (
            column and column['udt_name'] == 'varchar' and column['character_maximum_length'] and
            (self.size is None or column['character_maximum_length'] < self.size)
        ):
            # the column's varchar size does not match self.size; convert it
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])
        super(Char, self).update_db_column(model, column)

    _related_size = property(attrgetter('size'))
    _related_trim = property(attrgetter('trim'))
    _description_size = property(attrgetter('size'))
    _description_trim = property(attrgetter('trim'))

    def _setup_regular_base(self, model):
        super(Char, self)._setup_regular_base(model)
        assert self.size is None or isinstance(self.size, int), \
            "Char field %s with non-integer size %r" % (self, self.size)

    def convert_to_column(self, value, record, values=None, validate=True):
        if value is None or value is False:
            return None
        # we need to convert the string to a unicode object to be able
        # to evaluate its length (and possibly truncate it) reliably
        return pycompat.to_text(value)[:self.size]

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return pycompat.to_text(value)[:self.size]


class Text(_String):
    """ Very similar to :class:`~.Char` but used for longer contents, does not
    have a size and usually displayed as a multiline text box.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    """
    type = 'text'
    column_type = ('text', 'text')
    column_cast_from = ('varchar',)

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return ustr(value)


class Html(_String):
    type = 'html'
    column_type = ('text', 'text')
    _slots = {
        'sanitize': True,               # whether value must be sanitized
        'sanitize_tags': True,          # whether to sanitize tags (only a white list of attributes is accepted)
        'sanitize_attributes': True,    # whether to sanitize attributes (only a white list of attributes is accepted)
        'sanitize_style': False,        # whether to sanitize style attributes
        'strip_style': False,           # whether to strip style attributes (removed and therefore not sanitized)
        'strip_classes': False,         # whether to strip classes attributes
    }

    def _setup_attrs(self, model, name):
        super(Html, self)._setup_attrs(model, name)
        # Translated sanitized html fields must use html_translate or a callable.
        if self.translate is True and self.sanitize:
            self.translate = html_translate

    _related_sanitize = property(attrgetter('sanitize'))
    _related_sanitize_tags = property(attrgetter('sanitize_tags'))
    _related_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _related_sanitize_style = property(attrgetter('sanitize_style'))
    _related_strip_style = property(attrgetter('strip_style'))
    _related_strip_classes = property(attrgetter('strip_classes'))

    _description_sanitize = property(attrgetter('sanitize'))
    _description_sanitize_tags = property(attrgetter('sanitize_tags'))
    _description_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _description_sanitize_style = property(attrgetter('sanitize_style'))
    _description_strip_style = property(attrgetter('strip_style'))
    _description_strip_classes = property(attrgetter('strip_classes'))

    def convert_to_column(self, value, record, values=None, validate=True):
        if value is None or value is False:
            return None
        if self.sanitize:
            return html_sanitize(
                value, silent=True,
                sanitize_tags=self.sanitize_tags,
                sanitize_attributes=self.sanitize_attributes,
                sanitize_style=self.sanitize_style,
                strip_style=self.strip_style,
                strip_classes=self.strip_classes)
        return value

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        if validate and self.sanitize:
            return html_sanitize(
                value, silent=True,
                sanitize_tags=self.sanitize_tags,
                sanitize_attributes=self.sanitize_attributes,
                sanitize_style=self.sanitize_style,
                strip_style=self.strip_style,
                strip_classes=self.strip_classes)
        return value


class Date(Field):
    type = 'date'
    column_type = ('date', 'date')
    column_cast_from = ('timestamp',)

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    @staticmethod
    def today(*args):
        """ Return the current day in the format expected by the ORM.
            This function may be used to compute default values.
        """
        return date.today()

    @staticmethod
    def context_today(record, timestamp=None):
        """
        Return the current date as seen in the client's timezone in a format
        fit for date fields. This method may be used to compute default
        values.

        :param record: recordset from which the timezone will be obtained.
        :param datetime timestamp: optional datetime value to use instead of
            the current date and time (must be a datetime, regular dates
            can't be converted between timezones).
        :rtype: date
        """
        today = timestamp or datetime.now()
        context_today = None
        tz_name = record._context.get('tz') or record.env.user.tz
        if tz_name:
            try:
                today_utc = pytz.timezone('UTC').localize(today, is_dst=False)  # UTC = no DST
                context_today = today_utc.astimezone(pytz.timezone(tz_name))
            except Exception:
                _logger.debug("failed to compute context/client-specific today date, using UTC value for `today`",
                              exc_info=True)
        return (context_today or today).date()

    @staticmethod
    def to_date(value):
        """
        Attempt to convert ``value`` to a :class:`date` object.

        This function can take as input different kinds of types:
            * A falsy object, in which case None will be returned.
            * A string representing a date or datetime.
            * A date object, in which case the object will be returned as-is.
            * A datetime object, in which case it will be converted to a date object and all\
                        datetime-specific information will be lost (HMS, TZ, ...).

        :param value: value to convert.
        :return: an object representing ``value``.
        :rtype: date
        """
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                return value.date()
            return value
        value = value[:DATE_LENGTH]
        return datetime.strptime(value, DATE_FORMAT).date()

    # kept for backwards compatibility, but consider `from_string` as deprecated, will probably
    # be removed after V12
    from_string = to_date

    @staticmethod
    def to_string(value):
        """
        Convert a :class:`date` or :class:`datetime` object to a string.

        :param value: value to convert.
        :return: a string representing ``value`` in the server's date format, if ``value`` is of
            type :class:`datetime`, the hours, minute, seconds, tzinfo will be truncated.
        :rtype: str
        """
        return value.strftime(DATE_FORMAT) if value else False

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        if isinstance(value, datetime):
            # DLE P28: crm demo data pass datetimes to date fields.
            value = value.date()
        return self.to_date(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return self.to_date(value) if record._context.get('export_raw_data') else ustr(value)


class Datetime(Field):
    type = 'datetime'
    column_type = ('timestamp', 'timestamp')
    column_cast_from = ('date',)

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    @staticmethod
    def now(*args):
        """ Return the current day and time in the format expected by the ORM.
            This function may be used to compute default values.
        """
        # microseconds must be annihilated as they don't comply with the server datetime format
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def today(*args):
        """
        Return the current day, at midnight (00:00:00).
        """
        return Datetime.now().replace(hour=0, minute=0, second=0)

    @staticmethod
    def context_timestamp(record, timestamp):
        """
        Returns the given timestamp converted to the client's timezone.
        This method is *not* meant for use as a default initializer,
        because datetime fields are automatically converted upon
        display on client side. For default values, :meth:`fields.Datetime.now`
        should be used instead.

        :param record: recordset from which the timezone will be obtained.
        :param datetime timestamp: naive datetime value (expressed in UTC)
            to be converted to the client timezone.
        :rtype: datetime
        :return: timestamp converted to timezone-aware datetime in context timezone.
        """
        assert isinstance(timestamp, datetime), 'Datetime instance expected'
        tz_name = record._context.get('tz') or record.env.user.tz
        utc_timestamp = pytz.utc.localize(timestamp, is_dst=False)  # UTC = no DST
        if tz_name:
            try:
                context_tz = pytz.timezone(tz_name)
                return utc_timestamp.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific timestamp, "
                              "using the UTC value",
                              exc_info=True)
        return utc_timestamp

    @staticmethod
    def to_datetime(value):
        """
        Convert an ORM ``value`` into a :class:`datetime` value.

        This function can take as input different kinds of types:
            * A falsy object, in which case None will be returned.
            * A string representing a date or datetime.
            * A datetime object, in which case the object will be returned as-is.
            * A date object, in which case it will be converted to a datetime object.

        :param value: value to convert.
        :return: an object representing ``value``.
        :rtype: datetime
        """
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                if value.tzinfo:
                    raise ValueError("Datetime field expects a naive datetime: %s" % value)
                return value
            return datetime.combine(value, time.min)

        return datetime.strptime(value, DATETIME_FORMAT[:len(value)-2])

    # kept for backwards compatibility, but consider `from_string` as deprecated, will probably
    # be removed after V12
    from_string = to_datetime

    @staticmethod
    def to_string(value):
        """
        Convert a :class:`datetime` or :class:`date` object to a string.

        :param value: value to convert.
        :return: a string representing ``value`` in the server's datetime format, if ``value`` is
            of type :class:`date`, the time portion will be midnight (00:00:00).
        :rtype: str
        """
        return value.strftime(DATETIME_FORMAT) if value else False

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        # DLE P36:
        # `test_27_company_dependent`
        # Do not force to pass datetime, accept date as well.
        return self.to_datetime(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        value = self.convert_to_display_name(value, record)
        return self.to_datetime(value) if record._context.get('export_raw_data') else ustr(value)

    def convert_to_display_name(self, value, record):
        assert record, 'Record expected'
        return Datetime.to_string(Datetime.context_timestamp(record, Datetime.from_string(value)))

# http://initd.org/psycopg/docs/usage.html#binary-adaptation
# Received data is returned as buffer (in Python 2) or memoryview (in Python 3).
_BINARY = memoryview


class Binary(Field):
    type = 'binary'
    _slots = {
        'prefetch': False,              # not prefetched by default
        'context_dependent': True,      # depends on context (content or size)
        'attachment': True,             # whether value is stored in attachment
    }

    @property
    def column_type(self):
        return None if self.attachment else ('bytea', 'bytea')

    _description_attachment = property(attrgetter('attachment'))

    def convert_to_column(self, value, record, values=None, validate=True):
        # Binary values may be byte strings (python 2.6 byte array), but
        # the legacy OpenERP convention is to transfer and store binaries
        # as base64-encoded strings. The base64 string may be provided as a
        # unicode in some circumstances, hence the str() cast here.
        # This str() coercion will only work for pure ASCII unicode strings,
        # on purpose - non base64 data must be passed as a 8bit byte strings.
        if not value:
            return None
        # Detect if the binary content is an SVG for restricting its upload
        # only to system users.
        if value[:1] in (b'P', 'P'):  # Fast detection of first 6 bits of '<' (0x3C)
            decoded_value = base64.b64decode(value)
            # Full mimetype detection
            if (guess_mimetype(decoded_value).startswith('image/svg') and
                    not record.env.is_system()):
                raise UserError(_("Only admins can upload SVG files."))
        if isinstance(value, bytes):
            return psycopg2.Binary(value)
        try:
            return psycopg2.Binary(str(value).encode('ascii'))
        except UnicodeEncodeError:
            raise UserError(_("ASCII characters are required for %s in %s") % (value, self.name))

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, _BINARY):
            return bytes(value)
        # DLE P25: test `TestFileSeparator`
        # When assigning a binary field value in a create/write,
        # it is supposed to be bytes, but in some case it is not, it's strings.
        # Before, they we put in cache as bytes despite the fact we set them using string because they were read from
        # database, and there they were converted to bytes
        # Here, as we store directly in cache on create without reading from the database, we need to encode the strings
        # to bytes when needed.
        if isinstance(value, str):
            return value.encode()
        if isinstance(value, int) and \
                (record._context.get('bin_size') or
                 record._context.get('bin_size_' + self.name)):
            # If the client requests only the size of the field, we return that
            # instead of the content. Presumably a separate request will be done
            # to read the actual content, if necessary.
            return human_size(value)
        return value

    def read(self, records):
        # values are stored in attachments, retrieve them
        assert self.attachment
        domain = [
            ('res_model', '=', records._name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ]
        # Note: the 'bin_size' flag is handled by the field 'datas' itself
        data = {att.res_id: att.datas
                for att in records.env['ir.attachment'].sudo().search(domain)}
        cache = records.env.cache
        for record in records:
            cache.set(record, self, data.get(record.id, False))

    def create(self, record_values):
        assert self.attachment
        if not record_values:
            return
        # create the attachments that store the values
        env = record_values[0][0].env
        with env.norecompute():
            env['ir.attachment'].sudo().with_context(
                binary_field_real_user=env.user,
            ).create([{
                    'name': self.name,
                    'res_model': self.model_name,
                    'res_field': self.name,
                    'res_id': record.id,
                    'type': 'binary',
                    'datas': value,
                }
                for record, value in record_values
                if value
            ])

    def write(self, records, value):
        assert self.attachment
        # retrieve the attachments that store the values, and adapt them
        atts = records.env['ir.attachment'].sudo().search([
            ('res_model', '=', self.model_name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ])
        with records.env.norecompute():
            if value:
                # update the existing attachments
                atts.write({'datas': value})
                atts_records = records.browse(atts.mapped('res_id'))
                # create the missing attachments
                if len(atts_records) < len(records):
                    atts.create([{
                            'name': self.name,
                            'res_model': record._name,
                            'res_field': self.name,
                            'res_id': record.id,
                            'type': 'binary',
                            'datas': value,
                        }
                        for record in (records - atts_records)
                    ])
            else:
                atts.unlink()


class Selection(Field):
    """
    :param selection: specifies the possible values for this field.
        It is given as either a list of pairs (``value``, ``string``), or a
        model method, or a method name.
    :param selection_add: provides an extension of the selection in the case
        of an overridden field. It is a list of pairs (``value``, ``string``).

    The attribute ``selection`` is mandatory except in the case of
    :ref:`related fields <field-related>` or :ref:`field extensions
    <field-incremental-definition>`.
    """
    type = 'selection'
    column_type = ('varchar', pg_varchar())
    _slots = {
        'selection': None,              # [(value, string), ...], function or method name
        'validate': True,               # whether validating upon write
    }

    def __init__(self, selection=Default, string=Default, **kwargs):
        super(Selection, self).__init__(selection=selection, string=string, **kwargs)

    def _setup_regular_base(self, model):
        super(Selection, self)._setup_regular_base(model)
        assert self.selection is not None, "Field %s without selection" % self
        if isinstance(self.selection, list):
            assert all(isinstance(v, str) for v, _ in self.selection), \
                "Field %s with non-str value in selection" % self

    def _setup_related_full(self, model):
        super(Selection, self)._setup_related_full(model)
        # selection must be computed on related field
        field = self.related_field
        self.selection = lambda model: field._description_selection(model.env)

    def _setup_attrs(self, model, name):
        super(Selection, self)._setup_attrs(model, name)
        # determine selection (applying 'selection_add' extensions)
        for field in reversed(resolve_mro(model, name, self._can_setup_from)):
            # We cannot use field.selection or field.selection_add here
            # because those attributes are overridden by ``_setup_attrs``.
            if 'selection' in field.args:
                self.selection = field.args['selection']
            if 'selection_add' in field.args:
                # use an OrderedDict to update existing values
                selection_add = field.args['selection_add']
                self.selection = list(OrderedDict(self.selection + selection_add).items())

    def _description_selection(self, env):
        """ return the selection list (pairs (value, label)); labels are
            translated according to context language
        """
        selection = self.selection
        if isinstance(selection, str):
            return getattr(env[self.model_name], selection)()
        if callable(selection):
            return selection(env[self.model_name])

        # translate selection labels
        if env.lang:
            name = "%s,%s" % (self.model_name, self.name)
            translate = partial(
                env['ir.translation']._get_source, name, 'selection', env.lang)
            return [(value, translate(label) if label else label) for value, label in selection]
        else:
            return selection

    def get_values(self, env):
        """ return a list of the possible values """
        selection = self.selection
        if isinstance(selection, str):
            selection = getattr(env[self.model_name], selection)()
        elif callable(selection):
            selection = selection(env[self.model_name])
        return [value for value, _ in selection]

    def convert_to_column(self, value, record, values=None, validate=True):
        if validate and self.validate:
            value = self.convert_to_cache(value, record)
        return super(Selection, self).convert_to_column(value, record, values, validate)

    def convert_to_cache(self, value, record, validate=True):
        if not validate:
            return value or False
        if value and self.column_type[0] == 'int4':
            value = int(value)
        if value in self.get_values(record.env):
            return value
        elif not value:
            return False
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        if not isinstance(self.selection, list):
            # FIXME: this reproduces an existing buggy behavior!
            return value if value else ''
        for item in self._description_selection(record.env):
            if item[0] == value:
                return item[1]
        return False


class Reference(Selection):
    type = 'reference'

    @property
    def column_type(self):
        return ('varchar', pg_varchar())

    def convert_to_column(self, value, record, values=None, validate=True):
        return Field.convert_to_column(self, value, record, values, validate)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: (res_model, res_id) or False
        if isinstance(value, BaseModel):
            if not validate or (value._name in self.get_values(record.env) and len(value) <= 1):
                return (value._name, value.id) if value else False
        elif isinstance(value, str):
            res_model, res_id = value.split(',')
            if not validate or res_model in self.get_values(record.env):
                if record.env[res_model].browse(int(res_id)).exists():
                    return (res_model, int(res_id))
                else:
                    return False
        elif not value:
            return False
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_record(self, value, record):
        return value and record.env[value[0]].browse([value[1]])

    def convert_to_read(self, value, record, use_name_get=True):
        return "%s,%s" % (value._name, value.id) if value else False

    def convert_to_export(self, value, record):
        return value.display_name if value else ''

    def convert_to_display_name(self, value, record):
        return ustr(value and value.display_name)


class _Relational(Field):
    """ Abstract class for relational fields. """
    relational = True
    _slots = {
        'domain': [],                   # domain for searching values
        'context': {},                  # context for searching values
    }

    def __get__(self, records, owner):
        # base case: do the regular access
        if records is None or len(records._ids) <= 1:
            return super().__get__(records, owner)
        # multirecord case: return the union of the values of 'self' on records
        get = super().__get__
        comodel = records.env[self.comodel_name]
        return comodel.union(*[get(record, owner) for record in records])

    def _setup_regular_base(self, model):
        super(_Relational, self)._setup_regular_base(model)
        if self.comodel_name not in model.pool:
            _logger.warning("Field %s with unknown comodel_name %r", self, self.comodel_name)
            self.comodel_name = '_unknown'

    def get_domain_list(self, model):
        """ Return a list domain from the domain parameter. """
        domain = self.domain
        if callable(domain):
            domain = domain(model)
        return domain if isinstance(domain, list) else []

    @property
    def _related_domain(self):
        if callable(self.domain):
            # will be called with another model than self's
            return lambda recs: self.domain(recs.env[self.model_name])
        else:
            # maybe not correct if domain is a string...
            return self.domain

    _related_context = property(attrgetter('context'))

    _description_relation = property(attrgetter('comodel_name'))
    _description_context = property(attrgetter('context'))

    def _description_domain(self, env):
        return self.domain(env[self.model_name]) if callable(self.domain) else self.domain

    def null(self, record):
        return record.env[self.comodel_name]


class Many2one(_Relational):
    """ The value of such a field is a recordset of size 0 (no
    record) or 1 (a single record).

    :param comodel_name: name of the target model (string)

    :param domain: an optional domain to set on candidate values on the
        client side (domain or string)

    :param context: an optional context to use on the client side when
        handling that field (dictionary)

    :param ondelete: what to do when the referred record is deleted;
        possible values are: ``'set null'``, ``'restrict'``, ``'cascade'``

    :param auto_join: whether JOINs are generated upon search through that
        field (boolean, by default ``False``)

    :param delegate: set it to ``True`` to make fields of the target model
        accessible from the current model (corresponds to ``_inherits``)

    The attribute ``comodel_name`` is mandatory except in the case of related
    fields or field extensions.
    """
    type = 'many2one'
    column_type = ('int4', 'int4')
    _slots = {
        'ondelete': None,               # what to do when value is deleted
        'auto_join': False,             # whether joins are generated upon search
        'delegate': False,              # whether self implements delegation
    }

    def __init__(self, comodel_name=Default, string=Default, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    def _setup_attrs(self, model, name):
        super(Many2one, self)._setup_attrs(model, name)
        # determine self.delegate
        if not self.delegate:
            self.delegate = name in model._inherits.values()

    def _setup_regular_base(self, model):
        super()._setup_regular_base(model)
        # 3 cases:
        # 1) The ondelete attribute is not defined, we assign it a sensible default
        # 2) The ondelete attribute is defined and its definition makes sense
        # 3) The ondelete attribute is explicitly defined as 'set null' for a required m2o,
        #    this is considered a programming error.
        if not self.ondelete:
            self.ondelete = 'restrict' if self.required else 'set null'
        if self.ondelete == 'set null' and self.required:
            raise ValueError(
                "The m2o field %s of model %s is required but declares its ondelete policy "
                "as being 'set null'. Only 'restrict' and 'cascade' make sense."
                % (self.name, model._name)
            )

    def update_db(self, model, columns):
        comodel = model.env[self.comodel_name]
        if not model.is_transient() and comodel.is_transient():
            raise ValueError('Many2one %s from Model to TransientModel is forbidden' % self)
        if model.is_transient() and not comodel.is_transient():
            # Many2one relations from TransientModel Model are annoying because
            # they can block deletion due to foreign keys. So unless stated
            # otherwise, we default them to ondelete='cascade'.
            self.ondelete = self.ondelete or 'cascade'
        return super(Many2one, self).update_db(model, columns)

    def update_db_column(self, model, column):
        super(Many2one, self).update_db_column(model, column)
        model.pool.post_init(self.update_db_foreign_key, model, column)

    def update_db_foreign_key(self, model, column):
        comodel = model.env[self.comodel_name]
        # ir_actions is inherited, so foreign key doesn't work on it
        if not comodel._auto or comodel._table == 'ir_actions':
            return
        # create/update the foreign key, and reflect it in 'ir.model.constraint'
        process = sql.fix_foreign_key if column else sql.add_foreign_key
        new = process(model._cr, model._table, self.name, comodel._table, 'id', self.ondelete or 'set null')
        if new:
            conname = '%s_%s_fkey' % (model._table, self.name)
            model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, self._module)

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``. """
        cache = records.env.cache
        for record in records:
            cache.set(record, self, self.convert_to_cache(value, record, validate=False))

    def convert_to_column(self, value, record, values=None, validate=True):
        return value or None

    def convert_to_cache(self, value, record, validate=True):
        # cache format: tuple(ids)
        if type(value) in IdType:
            ids = (value,)
        elif isinstance(value, BaseModel):
            if validate and (value._name != self.comodel_name or len(value) > 1):
                raise ValueError("Wrong value for %s: %r" % (self, value))
            ids = value._ids
        elif isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            ids = value[:1]
        elif isinstance(value, dict):
            ids = record.env[self.comodel_name].new(value)._ids
        else:
            ids = ()

        if self.delegate and record and not record.id:
            # the parent record of a new record is a new record
            ids = tuple(it and NewId(it) for it in ids)

        return ids

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        prefetch_ids = IterableGenerator(prefetch_value_ids, record, self)
        return record.pool[self.comodel_name]._browse(record.env, value, prefetch_ids)

    def convert_to_read(self, value, record, use_name_get=True):
        if use_name_get and value:
            # evaluate name_get() as superuser, because the visibility of a
            # many2one field value (id and name) depends on the current record's
            # access rights, and not the value's access rights.
            try:
                # performance: value.sudo() prefetches the same records as value
                return (value.id, value.sudo().display_name)
            except MissingError:
                # Should not happen, unless the foreign key is missing.
                return False
        else:
            return value.id

    def convert_to_write(self, value, record):
        return value.id

    def convert_to_export(self, value, record):
        return value.display_name if value else ''

    def convert_to_display_name(self, value, record):
        return ustr(value.display_name)

    def convert_to_onchange(self, value, record, names):
        if not value.id:
            return False
        return super(Many2one, self).convert_to_onchange(value, record, names)


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """
    _slots = {
        # DLE P9: If there is a change in the context, the one2many fields cache values of the initial context is not recomputed
        # See test test_70_archive_internal_partners
        'context_dependent': False,      # depends on context (active_test)
    }
    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``, return True if everything is in cache. """
        if not isinstance(records, BaseModel):
            # the inverse of self is a non-relational field; do not update in
            # this case, as we do not know whether the records are the ones that
            # value makes reference to (via a res_model/res_id pair)
            return
        cache = records.env.cache
        result = True
        for record in records:
            if cache.contains(record, self):
                try:
                    val = self.convert_to_cache(record[self.name] | value, record, validate=False)
                    cache.set(record, self, val)
                except Exception as exc:
                    # delay the failure until the field is necessary
                    cache.set_failed(record, [self], exc)
            else:
                result = False
        return result

    def convert_to_cache(self, value, record, validate=True):
        # cache format: tuple(ids)
        if isinstance(value, BaseModel):
            if validate and value._name != self.comodel_name:
                raise ValueError("Wrong value for %s: %s" % (self, value))
            ids = value._ids
            if record and not record.id:
                # x2many field value of new record is new records
                ids = tuple(it and NewId(it) for it in ids)
            return ids

        elif isinstance(value, (list, tuple)):
            # value is a list/tuple of commands, dicts or record ids
            comodel = record.env[self.comodel_name]
            # if record is new, the field's value is new records
            if record and not record.id:
                browse = lambda it: comodel.browse([it and NewId(it)])
            else:
                browse = comodel.browse
            # determine the value ids
            ids = OrderedSet(record[self.name]._ids if validate else ())
            # modify ids with the commands
            for command in value:
                if isinstance(command, (tuple, list)):
                    if command[0] == 0:
                        ids.add(comodel.new(command[2], ref=command[1]).id)
                    elif command[0] == 1:
                        line = browse(command[1])
                        if validate:
                            line.update(command[2])
                        else:
                            line._update_cache(command[2], validate=False)
                        ids.add(line.id)
                    elif command[0] in (2, 3):
                        ids.discard(browse(command[1]).id)
                    elif command[0] == 4:
                        ids.add(browse(command[1]).id)
                    elif command[0] == 5:
                        ids.clear()
                    elif command[0] == 6:
                        ids = OrderedSet(browse(it).id for it in command[2])
                elif isinstance(command, dict):
                    ids.add(comodel.new(command).id)
                else:
                    ids.add(browse(command).id)
            # return result as a tuple
            return tuple(ids)

        elif not value:
            return ()

        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        prefetch_ids = IterableGenerator(prefetch_value_ids, record, self)
        return record.pool[self.comodel_name]._browse(record.env, value, prefetch_ids)

    def convert_to_read(self, value, record, use_name_get=True):
        return value.ids

    def convert_to_write(self, value, record):
        inv_names = {field.name for field in record._field_inverses[self]}
        # make result with new and existing records
        result = [(6, 0, [])]
        for record in value:
            origin = record._origin
            if not origin:
                values = record._convert_to_write({
                    name: record[name]
                    for name in record._cache
                    if name not in inv_names
                })
                result.append((0, 0, values))
            else:
                result[0][2].append(origin.id)
                if record != origin:
                    values = record._convert_to_write({
                        name: record[name]
                        for name in record._cache
                        if name not in inv_names and record[name] != origin[name]
                    })
                    if values:
                        result.append((1, origin.id, values))
        return result

    def convert_to_onchange(self, value, record, names):
        # return the recordset value as a list of commands; the commands may
        # give all fields values, the client is responsible for figuring out
        # which fields are actually dirty
        vals = {record: {} for record in value}
        for name, subnames in names.items():
            if name == 'id':
                continue
            field = value._fields[name]
            # read all values before converting them (better prefetching)
            rec_vals = [(rec, rec[name]) for rec in value]
            for rec, val in rec_vals:
                vals[rec][name] = field.convert_to_onchange(val, rec, subnames)

        result = [(5,)]
        for record in value:
            if not record.id and not record._origin:
                result.append((0, record.id.ref or 0, vals[record]))
            elif vals[record]:
                result.append((1, record._origin.id, vals[record]))
            else:
                result.append((4, record._origin.id))
        return result

    def convert_to_export(self, value, record):
        return ','.join(name for id, name in value.name_get()) if value else ''

    def convert_to_display_name(self, value, record):
        raise NotImplementedError()

    def _compute_related(self, records):
        """ Compute the related field ``self`` on ``records``. """
        super(_RelationalMulti, self)._compute_related(records)
        if self.related_sudo:
            # determine which records in the relation are actually accessible
            line_ids = set(records[self.name]._filter_access_rules('read')._ids)
            accessible = lambda line: line.id in line_ids
            # filter values to keep the accessible records only
            for record in records:
                record[self.name] = record[self.name].filtered(accessible)

    def _setup_regular_base(self, model):
        super(_RelationalMulti, self)._setup_regular_base(model)
        if isinstance(self.domain, list):
            self.depends += tuple(
                self.name + '.' + arg[0]
                for arg in self.domain
                if isinstance(arg, (tuple, list)) and isinstance(arg[0], str)
            )


class One2many(_RelationalMulti):
    """ One2many field; the value of such a field is the recordset of all the
        records in ``comodel_name`` such that the field ``inverse_name`` is equal to
        the current record.

        :param comodel_name: name of the target model (string)

        :param inverse_name: name of the inverse ``Many2one`` field in
            ``comodel_name`` (string)

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param auto_join: whether JOINs are generated upon search through that
            field (boolean, by default ``False``)

        :param limit: optional limit to use upon read (integer)

        The attributes ``comodel_name`` and ``inverse_name`` are mandatory except in
        the case of related fields or field extensions.
    """
    type = 'one2many'
    _slots = {
        'inverse_name': None,           # name of the inverse field
        'auto_join': False,             # whether joins are generated upon search
        'limit': None,                  # optional limit to use upon read
        'copy': False,                  # o2m are not copied by default
    }

    def __init__(self, comodel_name=Default, inverse_name=Default, string=Default, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs
        )

    def _setup_regular_full(self, model):
        super(One2many, self)._setup_regular_full(model)
        if self.inverse_name:
            # link self to its inverse field and vice-versa
            comodel = model.env[self.comodel_name]
            invf = comodel._fields[self.inverse_name]
            if isinstance(invf, Many2one):
                # setting one2many fields only invalidates many2one inverses;
                # integer inverses (res_model/res_id pairs) are not supported
                model._field_inverses.add(self, invf)
            comodel._field_inverses.add(invf, self)

    _description_relation_field = property(attrgetter('inverse_name'))

    def convert_to_onchange(self, value, record, names):
        names = names.copy()
        names.pop(self.inverse_name, None)
        return super(One2many, self).convert_to_onchange(value, record, names)

    def update_db(self, model, columns):
        if self.comodel_name in model.env:
            comodel = model.env[self.comodel_name]
            if self.inverse_name not in comodel._fields:
                raise UserError(_("No inverse field %r found for %r") % (self.inverse_name, self.comodel_name))

    def read(self, records):
        # retrieve the lines in the comodel
        comodel = records.env[self.comodel_name].with_context(**self.context)
        inverse = self.inverse_name
        get_id = (lambda rec: rec.id) if comodel._fields[inverse].type == 'many2one' else int
        domain = self.get_domain_list(records) + [(inverse, 'in', records.ids)]
        lines = comodel.search(domain, limit=self.limit)

        # group lines by inverse field (without prefetching other fields)
        group = defaultdict(list)
        for line in lines.with_context(prefetch_fields=False):
            # line[inverse] may be a record or an integer
            group[get_id(line[inverse])].append(line.id)

        # store result in cache
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(group[record.id]))

    def create(self, record_values):
        self._write(record_values)

    def write(self, records, value):
        self._write([(records, value)])

    def _write(self, records_commands_list):
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        inverse = self.inverse_name

        to_create = []                  # line vals to create
        to_delete = []                  # line ids to delete
        to_relink = {}                  # lines to relink {line_id: record_id}

        def unlink(line_ids):
            if getattr(comodel._fields[inverse], 'ondelete', False) == 'cascade':
                to_delete.extend(line_ids)
            else:
                to_relink.update(dict.fromkeys(line_ids, False))

        def flush():
            if to_delete:
                comodel.browse(to_delete).unlink()
                to_delete.clear()
            if to_create:
                comodel.create(to_create)
                to_create.clear()
            if to_relink:
                # group line ids to update by record id, and update them
                groups = defaultdict(list)
                lines = comodel.browse(to_relink).sudo().with_context(prefetch_fields=False)
                for line, record_id in zip(lines, to_relink.values()):
                    if int(line[inverse]) != record_id:
                        groups[record_id].append(line.id)
                for record_id, line_ids in groups.items():
                    comodel.browse(line_ids).write({inverse: record_id})
                to_relink.clear()

        with model.env.norecompute():
            for records, commands in records_commands_list:
                for act in (commands or ()):
                    if act[0] == 0:
                        for record in records:
                            to_create.append(dict(act[2], **{inverse: record.id}))
                    elif act[0] == 1:
                        comodel.browse(act[1]).write(act[2])
                    elif act[0] == 2:
                        to_delete.append(act[1])
                    elif act[0] == 3:
                        unlink([act[1]])
                    elif act[0] == 4:
                        to_relink[act[1]] = records[-1].id
                    elif act[0] in (5, 6):
                        flush()
                        ids = act[2] if act[0] == 6 else []
                        domain = self.get_domain_list(model) + [(inverse, 'in', records.ids)]
                        if ids:
                            domain = domain + [('id', 'not in', ids)]
                        unlink(comodel.search(domain)._ids)
                        to_relink.update(dict.fromkeys(ids, records[-1].id))

            flush()


class Many2many(_RelationalMulti):
    """ Many2many field; the value of such a field is the recordset.

        :param comodel_name: name of the target model (string)

        The attribute ``comodel_name`` is mandatory except in the case of related
        fields or field extensions.

        :param relation: optional name of the table that stores the relation in
            the database (string)

        :param column1: optional name of the column referring to "these" records
            in the table ``relation`` (string)

        :param column2: optional name of the column referring to "those" records
            in the table ``relation`` (string)

        The attributes ``relation``, ``column1`` and ``column2`` are optional.
        If not given, names are automatically generated from model names,
        provided ``model_name`` and ``comodel_name`` are different!

        Note that having several fields with implicit relation parameters on a
        given model with the same comodel is not accepted by the ORM, since
        those field would use the same table. The ORM prevents two many2many
        fields to use the same relation parameters, except if

        - both fields use the same model, comodel, and relation parameters are
          explicit; or

        - at least one field belongs to a model with ``_auto = False``.

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param limit: optional limit to use upon read (integer)

    """
    type = 'many2many'
    _slots = {
        '_explicit': True,              # whether schema is explicitly given
        'relation': None,               # name of table
        'column1': None,                # column of table referring to model
        'column2': None,                # column of table referring to comodel
        'auto_join': False,             # whether joins are generated upon search
        'limit': None,                  # optional limit to use upon read
    }

    def __init__(self, comodel_name=Default, relation=Default, column1=Default,
                 column2=Default, string=Default, **kwargs):
        super(Many2many, self).__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs
        )

    def _setup_regular_base(self, model):
        super(Many2many, self)._setup_regular_base(model)
        if self.store:
            if not (self.relation and self.column1 and self.column2):
                self._explicit = False
                # table name is based on the stable alphabetical order of tables
                comodel = model.env[self.comodel_name]
                if not self.relation:
                    tables = sorted([model._table, comodel._table])
                    assert tables[0] != tables[1], \
                        "%s: Implicit/canonical naming of many2many relationship " \
                        "table is not possible when source and destination models " \
                        "are the same" % self
                    self.relation = '%s_%s_rel' % tuple(tables)
                if not self.column1:
                    self.column1 = '%s_id' % model._table
                if not self.column2:
                    self.column2 = '%s_id' % comodel._table
            # check validity of table name
            check_pg_name(self.relation)
        else:
            self.relation = self.column1 = self.column2 = None

    def _setup_regular_full(self, model):
        super(Many2many, self)._setup_regular_full(model)
        if self.relation:
            m2m = model.pool._m2m

            # check whether other fields use the same schema
            fields = m2m[(self.relation, self.column1, self.column2)]
            for field in fields:
                if (    # same model: relation parameters must be explicit
                    self.model_name == field.model_name and
                    self.comodel_name == field.comodel_name and
                    self._explicit and field._explicit
                ) or (  # different models: one model must be _auto=False
                    self.model_name != field.model_name and
                    not (model._auto and model.env[field.model_name]._auto)
                ):
                    continue
                msg = "Many2many fields %s and %s use the same table and columns"
                raise TypeError(msg % (self, field))
            fields.append(self)

            # retrieve inverse fields, and link them in _field_inverses
            for field in m2m[(self.relation, self.column2, self.column1)]:
                model._field_inverses.add(self, field)
                model.env[field.model_name]._field_inverses.add(field, self)

    def update_db(self, model, columns):
        cr = model._cr
        # Do not reflect relations for custom fields, as they do not belong to a
        # module. They are automatically removed when dropping the corresponding
        # 'ir.model.field'.
        if not self.manual:
            model.pool.post_init(model.env['ir.model.relation']._reflect_relation,
                                 model, self.relation, self._module)
        if not sql.table_exists(cr, self.relation):
            comodel = model.env[self.comodel_name]
            query = """
                CREATE TABLE "{rel}" ("{id1}" INTEGER NOT NULL,
                                      "{id2}" INTEGER NOT NULL,
                                      UNIQUE("{id1}","{id2}"));
                COMMENT ON TABLE "{rel}" IS %s;
                CREATE INDEX ON "{rel}" ("{id1}");
                CREATE INDEX ON "{rel}" ("{id2}")
            """.format(rel=self.relation, id1=self.column1, id2=self.column2)
            cr.execute(query, ['RELATION BETWEEN %s AND %s' % (model._table, comodel._table)])
            _schema.debug("Create table %r: m2m relation between %r and %r", self.relation, model._table, comodel._table)
            model.pool.post_init(self.update_db_foreign_keys, model)
            return True

    def update_db_foreign_keys(self, model):
        """ Add the foreign keys corresponding to the field's relation table. """
        cr = model._cr
        comodel = model.env[self.comodel_name]
        reflect = model.env['ir.model.constraint']._reflect_constraint
        # create foreign key references with ondelete=cascade, unless the targets are SQL views
        if sql.table_kind(cr, model._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column1, model._table, 'id', 'cascade')
            reflect(model, '%s_%s_fkey' % (self.relation, self.column1), 'f', None, self._module)
        if sql.table_kind(cr, comodel._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column2, comodel._table, 'id', 'cascade')
            reflect(model, '%s_%s_fkey' % (self.relation, self.column2), 'f', None, self._module)

    def read(self, records):
        comodel = records.env[self.comodel_name].with_context(**self.context)
        domain = self.get_domain_list(records)
        wquery = comodel._where_calc(domain)
        comodel._apply_ir_rules(wquery, 'read')
        order_by = comodel._generate_order_by(None, wquery)
        from_c, where_c, where_params = wquery.get_sql()
        query = """ SELECT {rel}.{id1}, {rel}.{id2} FROM {rel}, {from_c}
                    WHERE {where_c} AND {rel}.{id1} IN %s AND {rel}.{id2} = {tbl}.id
                    {order_by} {limit} OFFSET {offset}
                """.format(rel=self.relation, id1=self.column1, id2=self.column2,
                           tbl=comodel._table, from_c=from_c, where_c=where_c or '1=1',
                           limit=(' LIMIT %d' % self.limit) if self.limit else '',
                           offset=0, order_by=order_by)
        where_params.append(tuple(records.ids))

        # retrieve lines and group them by record
        group = defaultdict(list)
        records._cr.execute(query, where_params)
        for row in records._cr.fetchall():
            group[row[0]].append(row[1])

        # store result in cache
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(group[record.id]))

    def create(self, record_values):
        self._write(record_values, create=True)

    def write(self, records, value):
        self._write([(records, value)])

    def _write(self, records_commands_list, create=False):
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        cr = model.env.cr

        # determine old relation {x: ys}
        old_relation = defaultdict(set)
        if not create:
            # DLE P53: it was possible to add links to many2many fields while you had not the right to access the comodel records,
            # but then it wasn't possible to remove this link using [(5,)], as it only removed the links of the records to which you had the read access right
            # e.g. you have the access to self.id1, but not to self.id2
            # the below added to the current records links to self.id1 & self.id2
            # `container_user.write({'some_ids': [(6, 0, [self.id1, self.id2])]})`
            # then, the below only removed self.id1, as you had no the access to self.id2
            # `container_user.write({'some_ids': [(5,)]})`
            # It should behave as many2one field: You can write in many2one field a record to which you don't have the access,
            # as well as emptying the many2one field from this record to which you do not had the access.
            # test `test_many2many`
            tables = ['"%s"' % model.env[comodel._name]._table]
            if '"%s"' % self.relation not in tables:
                tables.append('"%s"' % self.relation)
            query = """
                SELECT {rel}.{id1}, {rel}.{id2} FROM {tables}
                WHERE {rel}.{id1} IN %s AND {rel}.{id2}={table}.id AND {cond}
            """.format(
                rel=self.relation, id1=self.column1, id2=self.column2,
                table=comodel._table, tables=",".join(tables),
                cond="1=1",
            )
            ids = {rid for recs, cs in records_commands_list for rid in recs.ids}
            cr.execute(query, [tuple(ids)])
            for x, y in cr.fetchall():
                old_relation[x].add(y)

        # determine new relation {x: ys}
        new_relation = defaultdict(set)
        for x, ys in old_relation.items():
            new_relation[x] = set(ys)

        # operations on new relation
        def relation_add(xs, y):
            for x in xs:
                new_relation[x].add(y)

        def relation_remove(xs, y):
            for x in xs:
                new_relation[x].discard(y)

        def relation_set(xs, ys):
            for x in xs:
                new_relation[x] = set(ys)

        def relation_delete(ys):
            # the pairs (x, y) have been cascade-deleted from relation
            for ys1 in old_relation.values():
                ys1.difference_update(ys)
            for ys1 in new_relation.values():
                ys1.difference_update(ys)

        to_create = []                  # line vals to create [(ids, vals)]
        to_delete = []                  # line ids to delete

        with model.env.norecompute():
            for records, commands in records_commands_list:
                for act in (commands or ()):
                    if not isinstance(act, (list, tuple)) or not act:
                        continue
                    if act[0] == 0:
                        to_create.append((records._ids, act[2]))
                    elif act[0] == 1:
                        comodel.browse(act[1]).write(act[2])
                    elif act[0] == 2:
                        to_delete.append(act[1])
                    elif act[0] == 3:
                        relation_remove(records._ids, act[1])
                    elif act[0] == 4:
                        relation_add(records._ids, act[1])
                    elif act[0] in (5, 6):
                        # new lines must no longer be linked to records
                        to_create = [(set(ids) - set(records._ids), vals)
                                     for (ids, vals) in to_create]
                        relation_set(records._ids, act[2] if act[0] == 6 else ())

            if to_create:
                # create lines in batch, and link them
                lines = comodel.create([vals for ids, vals in to_create])
                for line, (ids, vals) in zip(lines, to_create):
                    relation_add(ids, line.id)

            if to_delete:
                # delete lines in batch
                comodel.browse(to_delete).unlink()
                relation_delete(to_delete)

        # process pairs to add (beware of duplicates)
        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            query = "INSERT INTO {} ({}, {}) VALUES {} ON CONFLICT DO NOTHING".format(
                self.relation, self.column1, self.column2, ", ".join(["%s"] * len(pairs)),
            )
            cr.execute(query, pairs)
            # DLE P35: Update the many2many field cache with the new added values
            # `odoo/addons/test_new_api/tests/test_new_fields.py`
            # `test_11_stored`
            for record_id, co_record_ids in new_relation.items():
                self._update(model.browse(record_id), comodel.browse(co_record_ids))

        # process pairs to remove
        pairs = [(x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]]
        if pairs:
            # express pairs as the union of cartesian products:
            #    pairs = [(1, 11), (1, 12), (1, 13), (2, 11), (2, 12), (2, 14)]
            # -> y_to_xs = {11: {1, 2}, 12: {1, 2}, 13: {1}, 14: {2}}
            # -> xs_to_ys = {{1, 2}: {11, 12}, {2}: {14}, {1}: {13}}
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
            xs_to_ys = defaultdict(set)
            for y, xs in y_to_xs.items():
                xs_to_ys[frozenset(xs)].add(y)
            # delete the rows where (id1 IN xs AND id2 IN ys) OR ...
            COND = "{} IN %s AND {} IN %s".format(self.column1, self.column2)
            query = "DELETE FROM {} WHERE {}".format(
                self.relation, " OR ".join([COND] * len(xs_to_ys)),
            )
            params = [arg for xs, ys in xs_to_ys.items() for arg in [tuple(xs), tuple(ys)]]
            cr.execute(query, params)


class Id(Field):
    """ Special case for field 'id'. """
    type = 'integer'
    column_type = ('int4', 'int4')
    _slots = {
        'string': 'ID',
        'store': True,
        'readonly': True,
        'prefetch': False,
    }

    def update_db(self, model, columns):
        pass                            # this column is created with the table

    def __get__(self, record, owner):
        if record is None:
            return self         # the field is accessed through the class owner

        # the code below is written to make record.id as quick as possible
        ids = record._ids
        size = len(ids)
        if size is 0:
            return False
        elif size is 1:
            return ids[0]
        raise ValueError("Expected singleton: %s" % record)

    def __set__(self, record, value):
        raise TypeError("field 'id' cannot be assigned")


def prefetch_value_ids(record, field):
    """ Return an iterator over the ids of the cached values of a relational
        field for the prefetch set of a record.
    """
    records = record.browse(record._prefetch_ids)
    ids_seq = record.env.cache.get_values(records, field, ())
    return unique(id_ for ids in ids_seq for id_ in ids)


# imported here to avoid dependency cycle issues
from .exceptions import AccessError, MissingError, UserError
from .models import check_pg_name, BaseModel, NewId, IdType
