# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" High-level objects for fields. """

from collections import defaultdict
from datetime import date, datetime, time
from operator import attrgetter
import itertools
import logging
import base64
import binascii
import pytz

try:
    from xmlrpc.client import MAXINT
except ImportError:
    #pylint: disable=bad-python3-import
    from xmlrpclib import MAXINT

import psycopg2

from .tools import float_repr, float_round, frozendict, html_sanitize, human_size, pg_varchar, \
    ustr, OrderedSet, pycompat, sql, date_utils, unique, IterableGenerator, image_process, merge_sequences
from .tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from .tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from .tools.translate import html_translate, _
from .tools.mimetypes import guess_mimetype
from odoo.exceptions import CacheMiss

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))
EMPTY_DICT = frozendict()

RENAMED_ATTRS = [('select', 'index'), ('digits_compute', 'digits')]
DEPRECATED_ATTRS = [("oldname", "use an upgrade script instead.")]

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__[:-7] + '.schema')

Default = object()                      # default value for __init__() methods


def first(records):
    """ Return the first record in ``records``, with the same prefetching. """
    return next(iter(records)) if len(records) > 1 else records


def resolve_mro(model, name, predicate):
    """ Return the list of successively overridden values of attribute ``name``
        in mro order on ``model`` that satisfy ``predicate``.  Model classes
        (the ones that appear in the registry) are ignored.
    """
    result = []
    for cls in type(model).__mro__:
        if not getattr(cls, 'pool', None) and name in cls.__dict__:
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
    """The field descriptor contains the field definition, and manages accesses
    and assignments of the corresponding field on records. The following
    attributes may be provided when instanciating a field:

    :param str string: the label of the field seen by users; if not
        set, the ORM takes the field name in the class (capitalized).

    :param str help: the tooltip of the field seen by users

    :param bool readonly: whether the field is readonly (default: ``False``)

        This only has an impact on the UI. Any field assignation in code will work
        (if the field is a stored field or an inversable one).

    :param bool required: whether the value of the field is required (default: ``False``)

    :param bool index: whether the field is indexed in database. Note: no effect
        on non-stored and virtual fields. (default: ``False``)

    :param default: the default value for the field; this is either a static
        value, or a function taking a recordset and returning a value; use
        ``default=None`` to discard default values for the field
    :type default: value or callable

    :param dict states: a dictionary mapping state values to lists of UI attribute-value
        pairs; possible attributes are: ``readonly``, ``required``, ``invisible``.

        .. warning:: Any state-based condition requires the ``state`` field value to be
            available on the client-side UI. This is typically done by including it in
            the relevant views, possibly made invisible if not relevant for the
            end-user.

    :param str groups: comma-separated list of group xml ids (string); this
        restricts the field access to the users of the given groups only

    :param bool company_dependent: whether the field value is dependent of the current company;

        The value isn't stored on the model table.  It is registered as `ir.property`.
        When the value of the company_dependent field is needed, an `ir.property`
        is searched, linked to the current company (and current record if one property
        exists).

        If the value is changed on the record, it either modifies the existing property
        for the current record (if one exists), or creates a new one for the current company
        and res_id.

        If the value is changed on the company side, it will impact all records on which
        the value hasn't been changed.

    :param bool copy: whether the field value should be copied when the record
        is duplicated (default: ``True`` for normal fields, ``False`` for
        ``one2many`` and computed fields, including property fields and
        related fields)

    :param bool store: whether the field is stored in database
        (default:``True``, ``False`` for computed fields)

    :param str group_operator: aggregate function used by :meth:`~odoo.models.Model.read_group`
        when grouping on this field.

        Supported aggregate functions are:

        * ``array_agg`` : values, including nulls, concatenated into an array
        * ``count`` : number of rows
        * ``count_distinct`` : number of distinct rows
        * ``bool_and`` : true if all values are true, otherwise false
        * ``bool_or`` : true if at least one value is true, otherwise false
        * ``max`` : maximum value of all values
        * ``min`` : minimum value of all values
        * ``avg`` : the average (arithmetic mean) of all values
        * ``sum`` : sum of all values

    :param str group_expand: function used to expand read_group results when grouping on
        the current field.

        .. code-block:: python

            @api.model
            def _read_group_selection_field(self, values, domain, order):
                return ['choice1', 'choice2', ...] # available selection choices.

            @api.model
            def _read_group_many2one_field(self, records, domain, order):
                return records + self.search([custom_domain])

    .. rubric:: Computed Fields

    :param str compute: name of a method that computes the field

        .. seealso:: :ref:`Advanced Fields/Compute fields <reference/fields/compute>`

    :param bool compute_sudo: whether the field should be recomputed as superuser
        to bypass access rights (by default ``True`` for stored fields, ``False``
        for non stored fields)

    :param str inverse: name of a method that inverses the field (optional)

    :param str search: name of a method that implement search on the field (optional)

    :param str related: sequence of field names

        .. seealso:: :ref:`Advanced fields/Related fields <reference/fields/related>`
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
        'depends_context': None,        # collection of context key dependencies
        'recursive': False,             # whether self depends on itself
        'compute': None,                # compute(recs) computes field on recs
        'compute_sudo': False,          # whether field should be recomputed as superuser
        'inverse': None,                # inverse(recs) inverses field on recs
        'search': None,                 # search(recs, operator, value) searches on self
        'related': None,                # sequence of field names, for related fields
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
        if self.args.get('automatic') and resolve_mro(model, name, self._can_setup_from):
            # prevent an automatic field from overriding a real field
            self.args.clear()
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
            # by default, computed fields are not stored, computed in superuser
            # mode if stored, not copied and readonly
            attrs['store'] = store = attrs.get('store', False)
            attrs['compute_sudo'] = attrs.get('compute_sudo', store)
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))
        if attrs.get('related'):
            # by default, related fields are not stored, computed in superuser
            # mode, not copied and readonly
            attrs['store'] = store = attrs.get('store', False)
            attrs['compute_sudo'] = attrs.get('compute_sudo', attrs.get('related_sudo', True))
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', True)
        if attrs.get('company_dependent'):
            # by default, company-dependent fields are not stored, not computed
            # in superuser mode and not copied
            attrs['store'] = False
            attrs['compute_sudo'] = attrs.get('compute_sudo', False)
            attrs['copy'] = attrs.get('copy', False)
            attrs['default'] = attrs.get('default', self._default_company_dependent)
            attrs['compute'] = self._compute_company_dependent
            if not attrs.get('readonly'):
                attrs['inverse'] = self._inverse_company_dependent
            attrs['search'] = self._search_company_dependent
            attrs['depends_context'] = attrs.get('depends_context', ()) + ('force_company',)
        if attrs.get('translate'):
            # by default, translatable fields are context-dependent
            attrs['depends_context'] = attrs.get('depends_context', ()) + ('lang',)
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
        for key, msg in DEPRECATED_ATTRS:
            if key in attrs:
                _logger.warning("Field %s: parameter %r is not longer supported; %s",
                                self, key, msg)

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
        pass

    def _setup_regular_full(self, model):
        """ Determine the dependencies and inverse field(s) of ``self``. """
        if self.depends is not None:
            return

        # determine the functions implementing self.compute
        if isinstance(self.compute, str):
            funcs = resolve_mro(model, self.compute, callable)
        elif self.compute:
            funcs = [self.compute]
        else:
            funcs = []

        # collect depends and depends_context
        depends = []
        depends_context = list(self.depends_context or ())
        for func in funcs:
            deps = getattr(func, '_depends', ())
            depends.extend(deps(model) if callable(deps) else deps)
            depends_context.extend(getattr(func, '_depends_context', ()))

        self.depends = tuple(depends)
        self.depends_context = tuple(depends_context)

        # display_name may depend on context['lang'] (`test_lp1071710`)
        if self.automatic and self.name == 'display_name' and model._rec_name:
            if model._fields[model._rec_name].base_field.translate:
                self.depends_context += ('lang',)

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
        if self.inherited or not (self.readonly or field.readonly):
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

        if field.depends_context:
            self.depends_context = field.depends_context

    def traverse_related(self, record):
        """ Traverse the fields of the related field `self` except for the last
        one, and return it as a pair `(last_record, last_field)`. """
        for name in self.related[:-1]:
            record = first(record[name])
        return record, self.related_field

    def _compute_related(self, records):
        """ Compute the related field ``self`` on ``records``. """
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
        values = list(records)
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
            record[self.name] = self._process_related(value[self.related_field.name])

    def _process_related(self, value):
        """No transformation by default, but allows override."""
        return value

    def _inverse_related(self, records):
        """ Inverse the related field ``self`` on ``records``. """
        # store record values, otherwise they may be lost by cache invalidation!
        record_value = {record: record[self.name] for record in records}
        for record in records:
            target, field = self.traverse_related(record)
            # update 'target' only if 'record' and 'target' are both real or
            # both new (see `test_base_objects.py`, `test_basic`)
            if target and bool(target.id) == bool(record.id):
                target[field.name] = record_value[record]

    def _search_related(self, records, operator, value):
        """ Determine the domain to search on field ``self``. """
        return [('.'.join(self.related), operator, value)]

    # properties used by _setup_related_full() to copy values from related field
    _related_comodel_name = property(attrgetter('comodel_name'))
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_groups = property(attrgetter('groups'))
    _related_group_operator = property(attrgetter('group_operator'))

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
    # Cache key for context-dependent fields
    #

    def cache_key(self, env):
        """ Return the cache key corresponding to ``self.depends_context``. """

        def get(key, get_context=env.context.get):
            if key == 'force_company':
                return get_context('force_company') or env.company.id
            elif key == 'uid':
                return (env.uid, env.su)
            elif key == 'active_test':
                return get_context('active_test', self.context.get('active_test', True))
            else:
                v = get_context(key)
                # The web client may set a list in the context:
                # https://github.com/odoo/odoo/blob/4b06fe19fa68255b7982d15e5847da2f6d6209fd/addons/web/static/src/js/views/control_panel/control_panel_model.js#L962
                # Therefore, we automatically convert lists into tuples
                if type(v) is list:
                    v = tuple(v)
                try: hash(v)
                except TypeError:
                    raise TypeError(
                        "Can only create cache keys from hashable values, "
                        "got non-hashable value {!r} at context key {!r} "
                        "(dependency of field {})".format(v, key, self)
                    ) from None # we don't need to chain the exception created 2 lines above
                else:
                    return v

        return tuple(get(key) for key in self.depends_context)

    #
    # Setup of field triggers
    #

    def resolve_depends(self, model):
        """ Return the dependencies of `self` as a collection of field tuples. """
        for dotnames in self.depends:
            field_seq = []
            field_model = model
            for index, fname in enumerate(dotnames.split('.')):
                if model._transient and not field_model._transient:
                    # modifying fields on regular models should not trigger
                    # recomputations of fields on transient models
                    break

                field = field_model._fields[fname]
                if field is self and index:
                    self.recursive = True

                field_seq.append(field)

                # do not make self trigger itself: for instance, a one2many
                # field line_ids with domain [('foo', ...)] will have
                # 'line_ids.foo' as a dependency
                if not (field is self and not index):
                    yield tuple(field_seq)

                if field.type in ('one2many', 'many2many'):
                    for inv_field in field_model._field_inverses[field]:
                        yield tuple(field_seq) + (inv_field,)

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
        return (self.column_type and self.store) or (self.inherited and self.related_field._description_sortable)

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
        return False if value is None else value

    def convert_to_read(self, value, record, use_name_get=True):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.read`.

        :param bool use_name_get: when True, the value's display name will be
            computed using :meth:`BaseModel.name_get`, if relevant for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, record):
        """ Convert ``value`` from any format to the format of method
        :meth:`BaseModel.write`.
        """
        cache_value = self.convert_to_cache(value, record, validate=False)
        record_value = self.convert_to_record(cache_value, record)
        return self.convert_to_read(record_value, record)

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
        return value

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
                # flush values before adding NOT NULL constraint
                model.flush([self.name])

        if self.required and not has_notnull:
            model.pool.post_constraint(apply_required, model, self.name)
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
                with model._cr.savepoint(flush=False):
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
        """ Write the value of ``self`` on ``records``. This method must update
        the cache and prepare database updates.

        :param value: a value in any format
        :return: the subset of `records` that have been modified
        """
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # update the cache, and discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return records
        cache.update(records, self, [cache_value] * len(records))

        # update towrite
        if self.store:
            towrite = records.env.all.towrite[self.model_name]
            record = records[:1]
            write_value = self.convert_to_write(cache_value, record)
            column_value = self.convert_to_column(write_value, record)
            for record in records.filtered('id'):
                towrite[record.id][self.name] = column_value

        return records

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

        if self.compute and (record.id in env.all.tocompute.get(self, ())) \
                and not env.is_protected(self, record):
            # self must be computed on record
            if self.recursive:
                recs = record
            else:
                recs = env.records_to_compute(self)
                # compute the field on real records only (if 'record' is real)
                # or new records only (if 'record' is new)
                recs = recs.filtered(lambda rec: bool(rec.id) == bool(record.id))
            try:
                self.compute_value(recs)
            except (AccessError, MissingError):
                self.compute_value(record)

        try:
            value = env.cache.get(record, self)

        except KeyError:
            # real record
            if record.id and self.store:
                recs = record._in_cache_without(self)
                try:
                    recs._fetch_field(self)
                except AccessError:
                    record._fetch_field(self)
                if not env.cache.contains(record, self) and not record.exists():
                    raise MissingError("\n".join([
                        _("Record does not exist or has been deleted."),
                        _("(Record: %s, User: %s)") % (record, env.uid),
                    ]))
                value = env.cache.get(record, self)

            elif self.compute:
                if env.is_protected(self, record):
                    value = self.convert_to_cache(False, record, validate=False)
                    env.cache.set(record, self, value)
                else:
                    recs = record if self.recursive else record._in_cache_without(self)
                    try:
                        self.compute_value(recs)
                    except (AccessError, MissingError):
                        self.compute_value(record)
                    value = env.cache.get(record, self)

            elif (not record.id) and record._origin:
                value = self.convert_to_cache(record._origin[self.name], record)
                env.cache.set(record, self, value)

            elif (not record.id) and self.type == 'many2one' and self.delegate:
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

        return self.convert_to_record(value, record)

    def __set__(self, records, value):
        """ set the value of field ``self`` on ``records`` """
        protected_ids = []
        new_ids = []
        other_ids = []
        for record_id in records._ids:
            if record_id in records.env._protected.get(self, ()):
                protected_ids.append(record_id)
            elif not record_id:
                new_ids.append(record_id)
            else:
                other_ids.append(record_id)

        if protected_ids:
            # records being computed: no business logic, no recomputation
            protected_records = records.browse(protected_ids)
            self.write(protected_records, value)

        if new_ids:
            # new records: no business logic
            new_records = records.browse(new_ids)
            with records.env.protecting(records._field_computed.get(self, [self]), records):
                new_records.modified([self.name])
                self.write(new_records, value)
                if self.relational:
                    new_records.modified([self.name])

        if other_ids:
            # base case: full business logic
            records = records.browse(other_ids)
            write_value = self.convert_to_write(value, records)
            records.write({self.name: write_value})

    ############################################################################
    #
    # Computation of field values
    #

    def compute_value(self, records):
        """ Invoke the compute method on ``records``; the results are in cache. """
        env = records.env
        if self.compute_sudo:
            records = records.sudo()
        fields = records._field_computed[self]

        # Just in case the compute method does not assign a value, we already
        # mark the computation as done. This is also necessary if the compute
        # method accesses the old value of the field: the field will be fetched
        # with _read(), which will flush() it. If the field is still to compute,
        # the latter flush() will recursively compute this field!
        for field in fields:
            env.remove_to_compute(field, records)

        try:
            with records.env.protecting(fields, records):
                records._compute_field_value(self)
        except Exception:
            for field in fields:
                env.add_to_compute(field, records)
            raise

    def determine_inverse(self, records):
        """ Given the value of ``self`` on ``records``, inverse the computation. """
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
    """ Encapsulates a :class:`bool`. """
    type = 'boolean'
    column_type = ('bool', 'bool')

    def convert_to_column(self, value, record, values=None, validate=True):
        return bool(value)

    def convert_to_cache(self, value, record, validate=True):
        return bool(value)

    def convert_to_export(self, value, record):
        return value


class Integer(Field):
    """ Encapsulates an :class:`int`. """
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
            return value.get('id', None)
        return int(value or 0)

    def convert_to_record(self, value, record):
        return value or 0

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
            return value
        return ''


class Float(Field):
    """ Encapsulates a :class:`float`.

    The precision digits are given by the (optional) ``digits`` attribute.

    :param digits: a pair (total, decimal) or a string referencing a
        :class:`~odoo.addons.base.models.decimal_precision.DecimalPrecision` record name.
    :type digits: tuple(int,int) or str
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

    def convert_to_record(self, value, record):
        return value or 0.0

    def convert_to_export(self, value, record):
        if value or value == 0.0:
            return value
        return ''


class Monetary(Field):
    """ Encapsulates a :class:`float` expressed in a given
    :class:`res_currency<odoo.addons.base.models.res_currency.Currency>`.

    The decimal precision and currency symbol are taken from the ``currency_field`` attribute.

    :param str currency_field: name of the :class:`Many2one` field
        holding the :class:`res_currency <odoo.addons.base.models.res_currency.Currency>`
        this monetary field is expressed in (default: `\'currency_id\'`)
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
            # BEWARE: do not prefetch other fields, because 'value' may be in
            # cache, and would be overridden by the value read from database!
            currency = record[:1].with_context(prefetch_fields=False)[self.currency_field]

        value = float(value or 0.0)
        if currency:
            return float_repr(currency.round(value), currency.decimal_places)
        return value

    def convert_to_cache(self, value, record, validate=True):
        # cache format: float
        value = float(value or 0.0)
        if value and validate:
            # FIXME @rco-odoo: currency may not be already initialized if it is
            # a function or related field!
            # BEWARE: do not prefetch other fields, because 'value' may be in
            # cache, and would be overridden by the value read from database!
            currency = record.sudo().with_context(prefetch_fields=False)[self.currency_field]
            if len(currency) > 1:
                raise ValueError("Got multiple currencies while assigning values of monetary field %s" % str(self))
            elif currency:
                value = currency.round(value)
        return value

    def convert_to_record(self, value, record):
        return value or 0.0

    def convert_to_read(self, value, record, use_name_get=True):
        return value

    def convert_to_write(self, value, record):
        return value


class _String(Field):
    """ Abstract class for string fields. """
    _slots = {
        'translate': False,             # whether the field is translated
        'prefetch': None,
    }

    def __init__(self, string=Default, **kwargs):
        # translate is either True, False, or a callable
        if 'translate' in kwargs and not callable(kwargs['translate']):
            kwargs['translate'] = bool(kwargs['translate'])
        super(_String, self).__init__(string=string, **kwargs)

    def _setup_attrs(self, model, name):
        super()._setup_attrs(model, name)
        if self.prefetch is None:
            # do not prefetch complex translated fields by default
            self.prefetch = not callable(self.translate)

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

    def write(self, records, value):
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # update the cache, and discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return records
        cache.update(records, self, [cache_value] * len(records))

        if not self.store:
            return records

        real_recs = records.filtered('id')
        if not real_recs._ids:
            return records

        update_column = True
        update_trans = False
        single_lang = len(records.env['res.lang'].get_installed()) <= 1
        if self.translate:
            lang = records.env.lang or None  # used in _update_translations below
            if single_lang:
                # a single language is installed
                update_trans = True
            elif callable(self.translate) or lang == 'en_US':
                # update the source and synchronize translations
                update_column = True
                update_trans = True
            elif lang != 'en_US' and lang is not None:
                # update the translations only except if emptying
                update_column = cache_value is None
                update_trans = True
            # else: lang = None

        # update towrite if modifying the source
        if update_column:
            towrite = records.env.all.towrite[self.model_name]
            for rid in real_recs._ids:
                # cache_value is already in database format
                towrite[rid][self.name] = cache_value
            if self.translate is True and cache_value is not None:
                tname = "%s,%s" % (records._name, self.name)
                records.env['ir.translation']._set_source(tname, real_recs._ids, value)
            if self.translate:
                # invalidate the field in the other languages
                cache.invalidate([(self, records.ids)])
                cache.update(records, self, [cache_value] * len(records))

        if update_trans:
            if callable(self.translate):
                # the source value of self has been updated, synchronize
                # translated terms when possible
                records.env['ir.translation']._sync_terms_translations(self, real_recs)

            else:
                # update translations
                value = self.convert_to_column(value, records)
                source_recs = real_recs.with_context(lang=None)
                source_value = first(source_recs)[self.name]
                if not source_value:
                    source_recs[self.name] = value
                    source_value = value
                tname = "%s,%s" % (self.model_name, self.name)
                if value is None:
                    records.env['ir.translation'].search([
                        ('name', '=', tname),
                        ('type', '=', 'model'),
                        ('res_id', 'in', real_recs._ids)
                    ]).unlink()
                elif single_lang:
                    records.env['ir.translation']._update_translations([dict(
                        src=source_value,
                        value=value,
                        name=tname,
                        lang=lang,
                        type='model',
                        state='translated',
                        res_id=res_id) for res_id in real_recs._ids])
                else:
                    records.env['ir.translation']._set_ids(
                        tname, 'model', lang, real_recs._ids, value, source_value,
                    )

        return records


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
    :type translate: bool or callable
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
            return None
        return pycompat.to_text(value)[:self.size]


class Text(_String):
    """ Very similar to :class:`Char` but used for longer contents, does not
    have a size and usually displayed as a multiline text box.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    :type translate: bool or callable
    """
    type = 'text'
    column_type = ('text', 'text')
    column_cast_from = ('varchar',)

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return None
        return ustr(value)


class Html(_String):
    """ Encapsulates an html code content.

    :param bool sanitize: whether value must be sanitized (default: ``True``)
    :param bool sanitize_tags: whether to sanitize tags
        (only a white list of attributes is accepted, default: ``True``)
    :param bool sanitize_attributes: whether to sanitize attributes
        (only a white list of attributes is accepted, default: ``True``)
    :param bool sanitize_style: whether to sanitize style attributes (default: ``False``)
    :param bool strip_style: whether to strip style attributes
        (removed and therefore not sanitized, default: ``False``)
    :param bool strip_classes: whether to strip classes attributes (default: ``False``)
    """
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

    def _get_attrs(self, model, name):
        # called by _setup_attrs(), working together with _String._setup_attrs()
        attrs = super()._get_attrs(model, name)
        # Translated sanitized html fields must use html_translate or a callable.
        if attrs.get('translate') is True and attrs.get('sanitize', True):
            attrs['translate'] = html_translate
        return attrs

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
            return None
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
    """ Encapsulates a python :class:`date <datetime.date>` object. """
    type = 'date'
    column_type = ('date', 'date')
    column_cast_from = ('timestamp',)

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    @staticmethod
    def today(*args):
        """Return the current day in the format expected by the ORM.

        .. note:: This function may be used to compute default values.
        """
        return date.today()

    @staticmethod
    def context_today(record, timestamp=None):
        """Return the current date as seen in the client's timezone in a format
        fit for date fields.

        .. note:: This method may be used to compute default values.

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
        """Attempt to convert ``value`` to a :class:`date` object.

        .. warning::

            If a datetime object is given as value,
            it will be converted to a date object and all
            datetime-specific information will be lost (HMS, TZ, ...).

        :param value: value to convert.
        :type value: str or date or datetime
        :return: an object representing ``value``.
        :rtype: date or None
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
            return None
        if isinstance(value, datetime):
            # TODO: better fix data files (crm demo data)
            value = value.date()
            # raise TypeError("%s (field %s) must be string or date, not datetime." % (value, self))
        return self.to_date(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return self.from_string(value)


class Datetime(Field):
    """ Encapsulates a python :class:`datetime <datetime.datetime>` object. """
    type = 'datetime'
    column_type = ('timestamp', 'timestamp')
    column_cast_from = ('date',)

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    @staticmethod
    def now(*args):
        """Return the current day and time in the format expected by the ORM.

        .. note:: This function may be used to compute default values.
        """
        # microseconds must be annihilated as they don't comply with the server datetime format
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def today(*args):
        """Return the current day, at midnight (00:00:00)."""
        return Datetime.now().replace(hour=0, minute=0, second=0)

    @staticmethod
    def context_timestamp(record, timestamp):
        """Return the given timestamp converted to the client's timezone.

        .. note:: This method is *not* meant for use as a default initializer,
            because datetime fields are automatically converted upon
            display on client side. For default values, :meth:`now`
            should be used instead.

        :param record: recordset from which the timezone will be obtained.
        :param datetime timestamp: naive datetime value (expressed in UTC)
            to be converted to the client timezone.
        :return: timestamp converted to timezone-aware datetime in context timezone.
        :rtype: datetime
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
        """Convert an ORM ``value`` into a :class:`datetime` value.

        :param value: value to convert.
        :type value: str or date or datetime
        :return: an object representing ``value``.
        :rtype: datetime or None
        """
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                if value.tzinfo:
                    raise ValueError("Datetime field expects a naive datetime: %s" % value)
                return value
            return datetime.combine(value, time.min)

        # TODO: fix data files
        return datetime.strptime(value, DATETIME_FORMAT[:len(value)-2])

    # kept for backwards compatibility, but consider `from_string` as deprecated, will probably
    # be removed after V12
    from_string = to_datetime

    @staticmethod
    def to_string(value):
        """Convert a :class:`datetime` or :class:`date` object to a string.

        :param value: value to convert.
        :type value: datetime or date
        :return: a string representing ``value`` in the server's datetime format,
            if ``value`` is of type :class:`date`,
            the time portion will be midnight (00:00:00).
        :rtype: str
        """
        return value.strftime(DATETIME_FORMAT) if value else False

    def convert_to_cache(self, value, record, validate=True):
        return self.to_datetime(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        value = self.convert_to_display_name(value, record)
        return self.from_string(value)

    def convert_to_display_name(self, value, record):
        assert record, 'Record expected'
        return Datetime.to_string(Datetime.context_timestamp(record, Datetime.from_string(value)))

# http://initd.org/psycopg/docs/usage.html#binary-adaptation
# Received data is returned as buffer (in Python 2) or memoryview (in Python 3).
_BINARY = memoryview


class Binary(Field):
    """Encapsulates a binary content (e.g. a file).

    :param bool attachment: whether the field should be stored as `ir_attachment`
        or in a column of the model's table (default: ``True``).
    """
    type = 'binary'
    _slots = {
        'prefetch': False,                  # not prefetched by default
        'depends_context': ('bin_size',),   # depends on context (content or size)
        'attachment': True,                 # whether value is stored in attachment
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
        magic_bytes = {
            b'P',  # first 6 bits of '<' (0x3C) b64 encoded
            b'<',  # plaintext XML tag opening
        }
        if isinstance(value, str):
            value = value.encode()
        if value[:1] in magic_bytes:
            try:
                decoded_value = base64.b64decode(value.translate(None, delete=b'\r\n'), validate=True)
            except binascii.Error:
                decoded_value = value
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
        if isinstance(value, str):
            # the cache must contain bytes or memoryview, but sometimes a string
            # is given when assigning a binary field (test `TestFileSeparator`)
            return value.encode()
        if isinstance(value, int) and \
                (record._context.get('bin_size') or
                 record._context.get('bin_size_' + self.name)):
            # If the client requests only the size of the field, we return that
            # instead of the content. Presumably a separate request will be done
            # to read the actual content, if necessary.
            value = human_size(value)
            # human_size can return False (-> None) or a string (-> encoded)
            return value.encode() if value else None
        return None if value is False else value

    def convert_to_record(self, value, record):
        if isinstance(value, _BINARY):
            return bytes(value)
        return False if value is None else value

    def compute_value(self, records):
        bin_size_name = 'bin_size_' + self.name
        if records.env.context.get('bin_size') or records.env.context.get(bin_size_name):
            # always compute without bin_size
            records_no_bin_size = records.with_context(**{'bin_size': False, bin_size_name: False})
            super().compute_value(records_no_bin_size)
            # manually update the bin_size cache
            cache = records.env.cache
            for record_no_bin_size, record in zip(records_no_bin_size, records):
                try:
                    value = cache.get(record_no_bin_size, self)
                    try:
                        value = base64.b64decode(value)
                    except (TypeError, binascii.Error):
                        pass
                    try:
                        if isinstance(value, (bytes, _BINARY)):
                            value = human_size(len(value))
                    except (TypeError):
                        pass
                    cache_value = self.convert_to_cache(value, record)
                    cache.set(record, self, cache_value)
                except CacheMiss:
                    pass
        else:
            super().compute_value(records)

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
        if not self.attachment:
            return super().write(records, value)

        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # update the cache, and discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return records
        if self.store:
            # determine records that are known to be not null
            not_null = cache.get_records_different_from(records, self, None)

        cache.update(records, self, [cache_value] * len(records))

        # retrieve the attachments that store the values, and adapt them
        if self.store:
            atts = records.env['ir.attachment'].sudo()
            if not_null:
                atts = atts.search([
                    ('res_model', '=', self.model_name),
                    ('res_field', '=', self.name),
                    ('res_id', 'in', records.ids),
                ])
            if value:
                # update the existing attachments
                atts.write({'datas': value})
                atts_records = records.browse(atts.mapped('res_id'))
                # create the missing attachments
                missing = (records - atts_records).filtered('id')
                if missing:
                    atts.create([{
                            'name': self.name,
                            'res_model': record._name,
                            'res_field': self.name,
                            'res_id': record.id,
                            'type': 'binary',
                            'datas': value,
                        }
                        for record in missing
                    ])
            else:
                atts.unlink()

        return records


class Image(Binary):
    """Encapsulates an image, extending :class:`Binary`.

    If image size is greater than the ``max_width``/``max_height`` limit of pixels, the image will be
    resized to the limit by keeping aspect ratio.

    :param int max_width: the maximum width of the image (default: ``0``, no limit)
    :param int max_height: the maximum height of the image (default: ``0``, no limit)
    :param bool verify_resolution: whether the image resolution should be verified
        to ensure it doesn't go over the maximum image resolution (default: ``True``).
        See :class:`odoo.tools.image.ImageProcess` for maximum image resolution (default: ``45e6``).

    .. note::

        If no ``max_width``/``max_height`` is specified (or is set to 0) and ``verify_resolution`` is False,
        the field content won't be verified at all and a :class:`Binary` field should be used.
    """
    _slots = {
        'max_width': 0,
        'max_height': 0,
        'verify_resolution': True,
    }

    def create(self, record_values):
        new_record_values = []
        for record, value in record_values:
            # strange behavior when setting related image field, when `self`
            # does not resize the same way as its related field
            new_value = self._image_process(value)
            new_record_values.append((record, new_value))
            cache_value = self.convert_to_cache(value if self.related else new_value, record)
            record.env.cache.update(record, self, [cache_value] * len(record))
        super(Image, self).create(new_record_values)

    def write(self, records, value):
        new_value = self._image_process(value)
        super(Image, self).write(records, new_value)
        cache_value = self.convert_to_cache(value if self.related else new_value, records)
        records.env.cache.update(records, self, [cache_value] * len(records))

    def _image_process(self, value):
        return image_process(value,
            size=(self.max_width, self.max_height),
            verify_resolution=self.verify_resolution,
        )

    def _process_related(self, value):
        """Override to resize the related value before saving it on self."""
        try:
            return self._image_process(super()._process_related(value))
        except UserError:
            # Avoid the following `write` to fail if the related image was saved
            # invalid, which can happen for pre-existing databases.
            return False


class Selection(Field):
    """ Encapsulates an exclusive choice between different values.

    :param selection: specifies the possible values for this field.
        It is given as either a list of pairs ``(value, label)``, or a model
        method, or a method name.
    :type selection: list(tuple(str,str)) or callable or str

    :param selection_add: provides an extension of the selection in the case
        of an overridden field. It is a list of pairs ``(value, label)`` or
        singletons ``(value,)``, where singleton values must appear in the
        overridden selection. The new values are inserted in an order that is
        consistent with the overridden selection and this list::

            selection = [('a', 'A'), ('b', 'B')]
            selection_add = [('c', 'C'), ('b',)]
            > result = [('a', 'A'), ('c', 'C'), ('b', 'B')]
    :type selection_add: list(tuple(str,str))

    The attribute ``selection`` is mandatory except in the case of
    ``related`` or extended fields.
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
        values = None
        labels = {}

        for field in reversed(resolve_mro(model, name, self._can_setup_from)):
            # We cannot use field.selection or field.selection_add here
            # because those attributes are overridden by ``_setup_attrs``.
            if 'selection' in field.args:
                selection = field.args['selection']
                if isinstance(selection, list):
                    if (
                        values is not None
                        and values != [kv[0] for kv in selection]
                    ):
                        _logger.warning("%s: selection=%r overrides existing selection; use selection_add instead", self, selection)
                    values = [kv[0] for kv in selection]
                    labels = dict(selection)
                else:
                    self.selection = selection
                    values = None
                    labels = {}

            if 'selection_add' in field.args:
                selection_add = field.args['selection_add']
                assert isinstance(selection_add, list), \
                    "%s: selection_add=%r must be a list" % (self, selection_add)
                assert values is not None, \
                    "%s: selection_add=%r on non-list selection %r" % (self, selection_add, self.selection)
                values = merge_sequences(values, [kv[0] for kv in selection_add])
                labels.update(kv for kv in selection_add if len(kv) == 2)

        if values is not None:
            self.selection = [(value, labels[value]) for value in values]

    def _selection_modules(self, model):
        """ Return a mapping from selection values to modules defining each value. """
        if not isinstance(self.selection, list):
            return {}
        value_modules = defaultdict(set)
        for field in reversed(resolve_mro(model, self.name, self._can_setup_from)):
            module = field.args.get('_module')
            if not module:
                continue
            if 'selection' in field.args:
                value_modules.clear()
                if isinstance(field.args['selection'], list):
                    for value, label in field.args['selection']:
                        value_modules[value].add(module)
            if 'selection_add' in field.args:
                for value_label in field.args['selection_add']:
                    if len(value_label) > 1:
                        value_modules[value_label[0]].add(module)
        return value_modules

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
            return env['ir.translation'].get_field_selection(self.model_name, self.name)
        else:
            return selection

    def get_values(self, env):
        """Return a list of the possible values."""
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
            return value or None
        if value and self.column_type[0] == 'int4':
            value = int(value)
        if value in self.get_values(record.env):
            return value
        elif not value:
            return None
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        if not isinstance(self.selection, list):
            # FIXME: this reproduces an existing buggy behavior!
            return value if value else ''
        for item in self._description_selection(record.env):
            if item[0] == value:
                return item[1]
        return ''


class Reference(Selection):
    """ Pseudo-relational field (no FK in database).

    The field value is stored as a :class:`string <str>` following the pattern
    ``"res_model.res_id"`` in database.
    """
    type = 'reference'

    @property
    def column_type(self):
        return ('varchar', pg_varchar())

    def convert_to_column(self, value, record, values=None, validate=True):
        return Field.convert_to_column(self, value, record, values, validate)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: str ("model,id") or None
        if isinstance(value, BaseModel):
            if not validate or (value._name in self.get_values(record.env) and len(value) <= 1):
                return "%s,%s" % (value._name, value.id) if value else None
        elif isinstance(value, str):
            res_model, res_id = value.split(',')
            if not validate or res_model in self.get_values(record.env):
                if record.env[res_model].browse(int(res_id)).exists():
                    return value
                else:
                    return None
        elif not value:
            return None
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_record(self, value, record):
        if value:
            res_model, res_id = value.split(',')
            return record.env[res_model].browse(int(res_id))
        return None

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
        'check_company': False,
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
        if self.check_company and not self.domain:
            if self.company_dependent:
                if self.comodel_name == "res.users":
                    # user needs access to current company (self.env.company)
                    return "[('company_ids', 'in', allowed_company_ids[0])]"
                else:
                    return "[('company_id', 'in', [allowed_company_ids[0], False])]"
            else:
                if self.comodel_name == "res.users":
                    # User allowed company ids = user.company_ids
                    return "['|', (not company_id, '=', True), ('company_ids', 'in', [company_id])]"
                else:
                    return "[('company_id', 'in', [company_id, False])]"
        return self.domain(env[self.model_name]) if callable(self.domain) else self.domain

    def null(self, record):
        return record.env[self.comodel_name]


class Many2one(_Relational):
    """ The value of such a field is a recordset of size 0 (no
    record) or 1 (a single record).

    :param str comodel_name: name of the target model
        ``Mandatory`` except for related or extended fields.

    :param domain: an optional domain to set on candidate values on the
        client side (domain or string)

    :param dict context: an optional context to use on the client side when
        handling that field

    :param str ondelete: what to do when the referred record is deleted;
        possible values are: ``'set null'``, ``'restrict'``, ``'cascade'``

    :param bool auto_join: whether JOINs are generated upon search through that
        field (default: ``False``)

    :param bool delegate: set it to ``True`` to make fields of the target model
        accessible from the current model (corresponds to ``_inherits``)

    :param bool check_company: Mark the field to be verified in
        :meth:`~odoo.models.Model._check_company`. Add a default company
        domain depending on the field attributes.
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
            comodel = model.env[self.comodel_name]
            if model.is_transient() and not comodel.is_transient():
                # Many2one relations from TransientModel Model are annoying because
                # they can block deletion due to foreign keys. So unless stated
                # otherwise, we default them to ondelete='cascade'.
                self.ondelete = 'cascade' if self.required else 'set null'
            else:
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
        return super(Many2one, self).update_db(model, columns)

    def update_db_column(self, model, column):
        super(Many2one, self).update_db_column(model, column)
        model.pool.post_init(self.update_db_foreign_key, model, column)

    def update_db_foreign_key(self, model, column):
        comodel = model.env[self.comodel_name]
        # foreign keys do not work on views, and users can define custom models on sql views.
        if not model._is_an_ordinary_table() or not comodel._is_an_ordinary_table():
            return
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
        # cache format: id or None
        if type(value) in IdType:
            id_ = value
        elif isinstance(value, BaseModel):
            if validate and (value._name != self.comodel_name or len(value) > 1):
                raise ValueError("Wrong value for %s: %r" % (self, value))
            id_ = value._ids[0] if value._ids else None
        elif isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            id_ = value[0] if value else None
        elif isinstance(value, dict):
            id_ = record.env[self.comodel_name].new(value).id
        else:
            id_ = None

        if self.delegate and record and not record.id:
            # the parent record of a new record is a new record
            id_ = id_ and NewId(id_)

        return id_

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        ids = () if value is None else (value,)
        prefetch_ids = IterableGenerator(prefetch_many2one_ids, record, self)
        return record.pool[self.comodel_name]._browse(record.env, ids, prefetch_ids)

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
        if type(value) in IdType:
            return value
        if not value:
            return False
        if isinstance(value, BaseModel) and value._name == self.comodel_name:
            return value.id
        if isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            return value[0] if value else False
        if isinstance(value, dict):
            return record.env[self.comodel_name].new(value).id
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        return value.display_name if value else ''

    def convert_to_display_name(self, value, record):
        return ustr(value.display_name)

    def convert_to_onchange(self, value, record, names):
        if not value.id:
            return False
        return super(Many2one, self).convert_to_onchange(value, record, names)

    def write(self, records, value):
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return records

        # remove records from the cache of one2many fields of old corecords
        self._remove_inverses(records, cache_value)

        # update the cache of self
        cache.update(records, self, [cache_value] * len(records))

        # update towrite
        if self.store:
            towrite = records.env.all.towrite[self.model_name]
            for record in records.filtered('id'):
                # cache_value is already in database format
                towrite[record.id][self.name] = cache_value

        # update the cache of one2many fields of new corecord
        self._update_inverses(records, cache_value)

        return records

    def _remove_inverses(self, records, value):
        """ Remove `records` from the cached values of the inverse fields of `self`. """
        cache = records.env.cache
        record_ids = set(records._ids)

        # align(id) returns a NewId if records are new, a real id otherwise
        align = (lambda id_: id_) if all(record_ids) else (lambda id_: id_ and NewId(id_))

        for invf in records._field_inverses[self]:
            corecords = records.env[self.comodel_name].browse(
                align(id_) for id_ in cache.get_values(records, self)
            )
            for corecord in corecords:
                ids0 = cache.get(corecord, invf, None)
                if ids0 is not None:
                    ids1 = tuple(id_ for id_ in ids0 if id_ not in record_ids)
                    cache.set(corecord, invf, ids1)

    def _update_inverses(self, records, value):
        """ Add `records` to the cached values of the inverse fields of `self`. """
        if value is None:
            return
        cache = records.env.cache
        corecord = self.convert_to_record(value, records)
        for invf in records._field_inverses[self]:
            valid_records = records.filtered_domain(invf.get_domain_list(corecord))
            if not valid_records:
                continue
            ids0 = cache.get(corecord, invf, None)
            # if the value for the corecord is not in cache, but this is a new
            # record, assign it anyway, as you won't be able to fetch it from
            # database (see `test_sale_order`)
            if ids0 is not None or not corecord.id:
                ids1 = tuple(unique((ids0 or ()) + valid_records._ids))
                cache.set(corecord, invf, ids1)


class Many2oneReference(Integer):
    """ Pseudo-relational field (no FK in database).

    The field value is stored as an :class:`integer <int>` id in database.

    Contrary to :class:`Reference` fields, the model has to be specified
    in a :class:`Char` field, whose name has to be specified in the
    `model_field` attribute for the current :class:`Many2oneReference` field.

    :param str model_field: name of the :class:`Char` where the model name is stored.
    """
    type = 'many2one_reference'
    _slots = {
        'model_field': None,
    }

    _related_model_field = property(attrgetter('model_field'))

    def convert_to_cache(self, value, record, validate=True):
        # cache format: id or None
        if isinstance(value, BaseModel):
            value = value._ids[0] if value._ids else None
        return super().convert_to_cache(value, record, validate)

    def _remove_inverses(self, records, value):
        # TODO: unused
        # remove records from the cache of one2many fields of old corecords
        cache = records.env.cache
        record_ids = set(records._ids)
        model_ids = self._record_ids_per_res_model(records)

        for invf in records._field_inverses[self]:
            records = records.browse(model_ids[invf.model_name])
            if not records:
                continue
            corecords = records.env[invf.model_name].browse(
                id_ for id_ in cache.get_values(records, self)
            )
            for corecord in corecords:
                ids0 = cache.get(corecord, invf, None)
                if ids0 is not None:
                    ids1 = tuple(id_ for id_ in ids0 if id_ not in record_ids)
                    cache.set(corecord, invf, ids1)

    def _update_inverses(self, records, value):
        """ Add `records` to the cached values of the inverse fields of `self`. """
        if not value:
            return
        cache = records.env.cache
        model_ids = self._record_ids_per_res_model(records)

        for invf in records._field_inverses[self]:
            records = records.browse(model_ids[invf.model_name])
            if not records:
                continue
            corecord = records.env[invf.model_name].browse(value)
            records = records.filtered_domain(invf.get_domain_list(corecord))
            if not records:
                continue
            ids0 = cache.get(corecord, invf, None)
            # if the value for the corecord is not in cache, but this is a new
            # record, assign it anyway, as you won't be able to fetch it from
            # database (see `test_sale_order`)
            if ids0 is not None or not corecord.id:
                ids1 = tuple(unique((ids0 or ()) + records._ids))
                cache.set(corecord, invf, ids1)

    def _record_ids_per_res_model(self, records):
        model_ids = defaultdict(set)
        for record in records:
            model = record[self.model_field]
            if not model and record._fields[self.model_field].compute:
                # fallback when the model field is computed :-/
                record._fields[self.model_field].compute_value(record)
                model = record[self.model_field]
                if not model:
                    continue
            model_ids[model].add(record.id)
        return model_ids


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """

    # Important: the cache contains the ids of all the records in the relation,
    # including inactive records.  Inactive records are filtered out by
    # convert_to_record(), depending on the context.

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``,
            and return whether everything is in cache.
        """
        if not isinstance(records, BaseModel):
            # the inverse of self is a non-relational field; `value` is a
            # corecord that refers to `records` by an integer field
            model = value.env[self.model_name]
            domain = self.domain(model) if callable(self.domain) else self.domain
            if not value.filtered_domain(domain):
                return
            records = model.browse(records)

        result = True

        if value:
            cache = records.env.cache
            for record in records:
                if cache.contains(record, self):
                    val = self.convert_to_cache(record[self.name] | value, record, validate=False)
                    cache.set(record, self, val)
                else:
                    result = False
            records.modified([self.name])

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
        prefetch_ids = IterableGenerator(prefetch_x2many_ids, record, self)
        corecords = record.pool[self.comodel_name]._browse(record.env, value, prefetch_ids)
        if (
            'active' in corecords
            and self.context.get('active_test', record.env.context.get('active_test', True))
        ):
            corecords = corecords.filtered('active').with_prefetch(prefetch_ids)
        return corecords

    def convert_to_read(self, value, record, use_name_get=True):
        return value.ids

    def convert_to_write(self, value, record):
        if isinstance(value, tuple):
            # a tuple of ids, this is the cache format
            value = record.env[self.comodel_name].browse(value)

        if isinstance(value, BaseModel) and value._name == self.comodel_name:
            # make result with new and existing records
            inv_names = {field.name for field in record._field_inverses[self]}
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

        if value is False or value is None:
            return [(5,)]

        if isinstance(value, list):
            return value

        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_export(self, value, record):
        return ','.join(name for id, name in value.name_get()) if value else ''

    def convert_to_display_name(self, value, record):
        raise NotImplementedError()

    def _setup_regular_full(self, model):
        super(_RelationalMulti, self)._setup_regular_full(model)
        if isinstance(self.domain, list):
            self.depends += tuple(
                self.name + '.' + arg[0]
                for arg in self.domain
                if isinstance(arg, (tuple, list)) and isinstance(arg[0], str)
            )

    def create(self, record_values):
        """ Write the value of ``self`` on the given records, which have just
        been created.

        :param record_values: a list of pairs ``(record, value)``, where
            ``value`` is in the format of method :meth:`BaseModel.write`
        """
        self.write_batch(record_values, True)

    def write(self, records, value):
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)
        return self.write_batch([(records, value)])

    def write_batch(self, records_commands_list, create=False):
        if not records_commands_list:
            return False

        for idx, (recs, value) in enumerate(records_commands_list):
            if isinstance(value, tuple):
                value = [(6, 0, value)]
            elif isinstance(value, BaseModel) and value._name == self.comodel_name:
                value = [(6, 0, value._ids)]
            elif value is False or value is None:
                value = [(5,)]
            elif isinstance(value, list) and value and not isinstance(value[0], (tuple, list)):
                value = [(6, 0, tuple(value))]
            if not isinstance(value, list):
                raise ValueError("Wrong value for %s: %s" % (self, value))
            records_commands_list[idx] = (recs, value)

        record_ids = {rid for recs, cs in records_commands_list for rid in recs._ids}
        if all(record_ids):
            return self.write_real(records_commands_list, create)
        else:
            assert not any(record_ids)
            return self.write_new(records_commands_list)


class One2many(_RelationalMulti):
    """One2many field; the value of such a field is the recordset of all the
    records in ``comodel_name`` such that the field ``inverse_name`` is equal to
    the current record.

    :param str comodel_name: name of the target model

    :param str inverse_name: name of the inverse ``Many2one`` field in
        ``comodel_name``

    :param domain: an optional domain to set on candidate values on the
        client side (domain or string)

    :param dict context: an optional context to use on the client side when
        handling that field

    :param bool auto_join: whether JOINs are generated upon search through that
        field (default: ``False``)

    :param int limit: optional limit to use upon read

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
            if isinstance(invf, (Many2one, Many2oneReference)):
                # setting one2many fields only invalidates many2one inverses;
                # integer inverses (res_model/res_id pairs) are not supported
                model._field_inverses.add(self, invf)
            comodel._field_inverses.add(invf, self)

    _description_relation_field = property(attrgetter('inverse_name'))

    def update_db(self, model, columns):
        if self.comodel_name in model.env:
            comodel = model.env[self.comodel_name]
            if self.inverse_name not in comodel._fields:
                raise UserError(_("No inverse field %r found for %r") % (self.inverse_name, self.comodel_name))

    def get_domain_list(self, records):
        comodel = records.env.registry[self.comodel_name]
        inverse_field = comodel._fields[self.inverse_name]
        domain = super(One2many, self).get_domain_list(records)
        if inverse_field.type == 'many2one_reference':
            domain = domain + [(inverse_field.model_field, '=', records._name)]
        return domain

    def read(self, records):
        # retrieve the lines in the comodel
        context = {'active_test': False}
        context.update(self.context)
        comodel = records.env[self.comodel_name].with_context(**context)
        inverse = self.inverse_name
        inverse_field = comodel._fields[inverse]
        get_id = (lambda rec: rec.id) if inverse_field.type == 'many2one' else int
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

    def write_real(self, records_commands_list, create=False):
        """ Update real records. """
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)

        ids = {rid for recs, cs in records_commands_list for rid in recs.ids}
        records = records_commands_list[0][0].browse(ids)

        if self.store:
            inverse = self.inverse_name
            to_create = []                  # line vals to create
            to_delete = []                  # line ids to delete
            to_inverse = {}
            allow_full_delete = not create

            def unlink(lines):
                if getattr(comodel._fields[inverse], 'ondelete', False) == 'cascade':
                    to_delete.extend(lines._ids)
                else:
                    lines[inverse] = False

            def flush():
                if to_delete:
                    # unlink() will remove the lines from the cache
                    comodel.browse(to_delete).unlink()
                    to_delete.clear()
                if to_create:
                    # create() will add the new lines to the cache of records
                    comodel.create(to_create)
                    to_create.clear()
                if to_inverse:
                    for record, inverse_ids in to_inverse.items():
                        lines = comodel.browse(inverse_ids)
                        lines = lines.filtered(lambda line: int(line[inverse]) != record.id)
                        lines[inverse] = record

            for recs, commands in records_commands_list:
                for command in (commands or ()):
                    if command[0] == 0:
                        for record in recs:
                            to_create.append(dict(command[2], **{inverse: record.id}))
                        allow_full_delete = False
                    elif command[0] == 1:
                        comodel.browse(command[1]).write(command[2])
                    elif command[0] == 2:
                        to_delete.append(command[1])
                    elif command[0] == 3:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == 4:
                        to_inverse.setdefault(recs[-1], set()).add(command[1])
                        allow_full_delete = False
                    elif command[0] in (5, 6) :
                        # do not try to delete anything in creation mode if nothing has been created before
                        line_ids = command[2] if command[0] == 6 else []
                        if not allow_full_delete and not line_ids:
                            continue
                        flush()
                        # assign the given lines to the last record only
                        lines = comodel.browse(line_ids)
                        domain = self.get_domain_list(model) + \
                            [(inverse, 'in', recs.ids), ('id', 'not in', lines.ids)]
                        unlink(comodel.search(domain))
                        lines[inverse] = recs[-1]

            flush()

        else:
            cache = records.env.cache

            def link(record, lines):
                ids = record[self.name]._ids
                cache.set(record, self, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    cache.set(record, self, (record[self.name] - lines)._ids)

            for recs, commands in records_commands_list:
                for command in (commands or ()):
                    if command[0] == 0:
                        for record in recs:
                            link(record, comodel.new(command[2], ref=command[1]))
                    elif command[0] == 1:
                        comodel.browse(command[1]).write(command[2])
                    elif command[0] == 2:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == 3:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == 4:
                        link(recs[-1], comodel.browse(command[1]))
                    elif command[0] in (5, 6):
                        # assign the given lines to the last record only
                        cache.update(recs, self, [()] * len(recs))
                        lines = comodel.browse(command[2] if command[0] == 6 else [])
                        cache.set(recs[-1], self, lines._ids)

        return records

    def write_new(self, records_commands_list):
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        cache = model.env.cache
        comodel = model.env[self.comodel_name].with_context(**self.context)

        ids = {record.id for records, _ in records_commands_list for record in records}
        records = model.browse(ids)

        def browse(ids):
            return comodel.browse([id_ and NewId(id_) for id_ in ids])

        # make sure self is in cache
        records[self.name]

        if self.store:
            inverse = self.inverse_name

            # make sure self's inverse is in cache
            inverse_field = comodel._fields[inverse]
            for record in records:
                cache.update(record[self.name], inverse_field, itertools.repeat(record.id))

            for recs, commands in records_commands_list:
                for command in commands:
                    if command[0] == 0:
                        for record in recs:
                            line = comodel.new(command[2], ref=command[1])
                            line[inverse] = record
                    elif command[0] == 1:
                        browse([command[1]]).update(command[2])
                    elif command[0] == 2:
                        browse([command[1]])[inverse] = False
                    elif command[0] == 3:
                        browse([command[1]])[inverse] = False
                    elif command[0] == 4:
                        browse([command[1]])[inverse] = recs[-1]
                    elif command[0] in (5, 6):
                        # assign the given lines to the last record only
                        cache.update(recs, self, [()] * len(recs))
                        lines = comodel.browse(command[2] if command[0] == 6 else [])
                        cache.set(recs[-1], self, lines._ids)

        else:
            def link(record, lines):
                ids = record[self.name]._ids
                cache.set(record, self, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    cache.set(record, self, (record[self.name] - lines)._ids)

            for recs, commands in records_commands_list:
                for command in commands:
                    if command[0] == 0:
                        for record in recs:
                            link(record, comodel.new(command[2], ref=command[1]))
                    elif command[0] == 1:
                        browse([command[1]]).update(command[2])
                    elif command[0] == 2:
                        unlink(browse([command[1]]))
                    elif command[0] == 3:
                        unlink(browse([command[1]]))
                    elif command[0] == 4:
                        link(recs[-1], browse([command[1]]))
                    elif command[0] in (5, 6):
                        # assign the given lines to the last record only
                        cache.update(recs, self, [()] * len(recs))
                        lines = comodel.browse(command[2] if command[0] == 6 else [])
                        cache.set(recs[-1], self, lines._ids)

        return records


class Many2many(_RelationalMulti):
    """ Many2many field; the value of such a field is the recordset.

    :param comodel_name: name of the target model (string)
        mandatory except in the case of related or extended fields

    :param str relation: optional name of the table that stores the relation in
        the database

    :param str column1: optional name of the column referring to "these" records
        in the table ``relation``

    :param str column2: optional name of the column referring to "those" records
        in the table ``relation``

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

    :param dict context: an optional context to use on the client side when
        handling that field

    :param bool check_company: Mark the field to be verified in
        :meth:`~odoo.models.Model._check_company`. Add a default company
        domain depending on the field attributes.

    :param int limit: optional limit to use upon read
    """
    type = 'many2many'
    _slots = {
        '_explicit': True,              # whether schema is explicitly given
        'relation': None,               # name of table
        'column1': None,                # column of table referring to model
        'column2': None,                # column of table referring to comodel
        'auto_join': False,             # whether joins are generated upon search
        'limit': None,                  # optional limit to use upon read
        'ondelete': None,               # optional ondelete for the column2 fkey
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
        # 3 cases:
        # 1) The ondelete attribute is not defined, we assign it a sensible default
        # 2) The ondelete attribute is defined and its definition makes sense
        # 3) The ondelete attribute is explicitly defined as 'set null' for a m2m,
        #    this is considered a programming error.
        self.ondelete = self.ondelete or 'cascade'
        if self.ondelete == 'set null':
            raise ValueError(
                "The m2m field %s of model %s declares its ondelete policy "
                "as being 'set null'. Only 'restrict' and 'cascade' make sense."
                % (self.name, model._name)
            )
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
        comodel = model.env[self.comodel_name]
        if not sql.table_exists(cr, self.relation):
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
        elif sql.table_kind(cr, comodel._table) != 'v' and self.ondelete != 'cascade':
            # Fix foreign key references with ondelete, unless the targets are
            # SQL views.
            # This is needed because by default the ondelete of the column1
            # fkey is set to 'cascade', but the relation on the opposite model
            # can override it by defining ondelete for its column2 fkey.
            sql.fix_foreign_key(cr, self.relation, self.column2, comodel._table, 'id', self.ondelete)

    def update_db_foreign_keys(self, model):
        """ Add the foreign keys corresponding to the field's relation table. """
        cr = model._cr
        comodel = model.env[self.comodel_name]
        reflect = model.env['ir.model.constraint']._reflect_constraint
        # create foreign key references with ondelete, unless the targets are SQL views
        if sql.table_kind(cr, model._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column1, model._table, 'id', 'cascade')
            reflect(model, '%s_%s_fkey' % (self.relation, self.column1), 'f', None, self._module)
        if sql.table_kind(cr, comodel._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column2, comodel._table, 'id', self.ondelete)
            reflect(model, '%s_%s_fkey' % (self.relation, self.column2), 'f', None, self._module)

    def read(self, records):
        context = {'active_test': False}
        context.update(self.context)
        comodel = records.env[self.comodel_name].with_context(**context)
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

    def write_real(self, records_commands_list, create=False):
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        comodel = records_commands_list[0][0].env[self.comodel_name].with_context(**self.context)
        cr = records_commands_list[0][0].env.cr

        # determine old and new relation {x: ys}
        set = OrderedSet
        ids = {rid for recs, cs in records_commands_list for rid in recs.ids}
        records = records_commands_list[0][0].browse(ids)

        if self.store:
            # Using `record[self.name]` generates 2 SQL queries when the value
            # is not in cache: one that actually checks access rules for
            # records, and the other one fetching the actual data. We use
            # `self.read` instead to shortcut the first query.
            missing_ids = list(records.env.cache.get_missing_ids(records, self))
            if missing_ids:
                self.read(records.browse(missing_ids))

        old_relation = {record.id: set(record[self.name]._ids) for record in records}
        new_relation = {x: set(ys) for x, ys in old_relation.items()}

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
                ys1 -= ys
            for ys1 in new_relation.values():
                ys1 -= ys

        for recs, commands in records_commands_list:
            to_create = []  # line vals to create
            to_delete = []  # line ids to delete
            for command in (commands or ()):
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == 0:
                    to_create.append((recs._ids, command[2]))
                elif command[0] == 1:
                    comodel.browse(command[1]).write(command[2])
                elif command[0] == 2:
                    to_delete.append(command[1])
                elif command[0] == 3:
                    relation_remove(recs._ids, command[1])
                elif command[0] == 4:
                    relation_add(recs._ids, command[1])
                elif command[0] in (5, 6):
                    # new lines must no longer be linked to records
                    to_create = [(set(ids) - set(recs._ids), vals) for (ids, vals) in to_create]
                    relation_set(recs._ids, command[2] if command[0] == 6 else ())

            if to_create:
                # create lines in batch, and link them
                lines = comodel.create([vals for ids, vals in to_create])
                for line, (ids, vals) in zip(lines, to_create):
                    relation_add(ids, line.id)

            if to_delete:
                # delete lines in batch
                comodel.browse(to_delete).unlink()
                relation_delete(to_delete)

        # update the cache of self
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(new_relation[record.id]))

        # process pairs to add (beware of duplicates)
        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            if self.store:
                query = "INSERT INTO {} ({}, {}) VALUES {} ON CONFLICT DO NOTHING".format(
                    self.relation, self.column1, self.column2, ", ".join(["%s"] * len(pairs)),
                )
                cr.execute(query, pairs)

            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
            for invf in records._field_inverses[self]:
                domain = invf.get_domain_list(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        # process pairs to remove
        pairs = [(x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]]
        if pairs:
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)

            if self.store:
                # express pairs as the union of cartesian products:
                #    pairs = [(1, 11), (1, 12), (1, 13), (2, 11), (2, 12), (2, 14)]
                # -> y_to_xs = {11: {1, 2}, 12: {1, 2}, 13: {1}, 14: {2}}
                # -> xs_to_ys = {{1, 2}: {11, 12}, {2}: {14}, {1}: {13}}
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

            # update the cache of inverse fields
            for invf in records._field_inverses[self]:
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        return records.filtered(
            lambda record: new_relation[record.id] != old_relation[record.id]
        )

    def write_new(self, records_commands_list):
        """ Update self on new records. """
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        new = lambda id_: id_ and NewId(id_)

        # determine old and new relation {x: ys}
        set = OrderedSet
        old_relation = {record.id: set(record[self.name]._ids) for records, _ in records_commands_list for record in records}
        new_relation = {x: set(ys) for x, ys in old_relation.items()}
        ids = set(old_relation.keys())

        records = model.browse(ids)

        for recs, commands in records_commands_list:
            for command in commands:
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == 0:
                    line_id = comodel.new(command[2], ref=command[1]).id
                    for line_ids in new_relation.values():
                        line_ids.add(line_id)
                elif command[0] == 1:
                    line_id = new(command[1])
                    comodel.browse([line_id]).update(command[2])
                elif command[0] == 2:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.discard(line_id)
                elif command[0] == 3:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.discard(line_id)
                elif command[0] == 4:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.add(line_id)
                elif command[0] in (5, 6):
                    # new lines must no longer be linked to records
                    line_ids = command[2] if command[0] == 6 else ()
                    line_ids = set(new(line_id) for line_id in line_ids)
                    for id_ in recs._ids:
                        new_relation[id_] = set(line_ids)

        if new_relation == old_relation:
            return records.browse()

        # update the cache of self
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(new_relation[record.id]))

        # process pairs to add (beware of duplicates)
        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
            for invf in records._field_inverses[self]:
                domain = invf.get_domain_list(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse([y])
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        # process pairs to remove
        pairs = [(x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]]
        if pairs:
            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
            for invf in records._field_inverses[self]:
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse([y])
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        return records.filtered(
            lambda record: new_relation[record.id] != old_relation[record.id]
        )


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
        if size == 0:
            return False
        elif size == 1:
            return ids[0]
        raise ValueError("Expected singleton: %s" % record)

    def __set__(self, record, value):
        raise TypeError("field 'id' cannot be assigned")


def prefetch_many2one_ids(record, field):
    """ Return an iterator over the ids of the cached values of a many2one
        field for the prefetch set of a record.
    """
    records = record.browse(record._prefetch_ids)
    ids = record.env.cache.get_values(records, field)
    return unique(id_ for id_ in ids if id_ is not None)


def prefetch_x2many_ids(record, field):
    """ Return an iterator over the ids of the cached values of an x2many
        field for the prefetch set of a record.
    """
    records = record.browse(record._prefetch_ids)
    ids_list = record.env.cache.get_values(records, field)
    return unique(id_ for ids in ids_list for id_ in ids)


def apply_required(model, field_name):
    """ Set a NOT NULL constraint on the given field, if necessary. """
    # At the time this function is called, the model's _fields may have been reset, although
    # the model's class is still the same. Retrieve the field to see whether the NOT NULL
    # constraint still applies
    field = model._fields[field_name]
    if field.store and field.required:
        sql.set_not_null(model.env.cr, model._table, field_name)


# imported here to avoid dependency cycle issues
from .exceptions import AccessError, MissingError, UserError
from .models import check_pg_name, BaseModel, NewId, IdType
