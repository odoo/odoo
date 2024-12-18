# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" High-level objects for fields. """
from __future__ import annotations

import itertools
import logging
import typing
import warnings
from operator import attrgetter

from psycopg2.extras import Json as PsycopgJson

from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError
from odoo.tools import Query, SQL, lazy_property, sql
from odoo.tools.constants import PREFETCH_MAX
from odoo.tools.misc import SENTINEL, Sentinel

from .domains import NEGATIVE_CONDITION_OPERATORS, Domain
from .utils import COLLECTION_TYPES, SQL_OPERATORS, expand_ids

if typing.TYPE_CHECKING:
    from .models import BaseModel
T = typing.TypeVar("T")

IR_MODELS = (
    'ir.model', 'ir.model.data', 'ir.model.fields', 'ir.model.fields.selection',
    'ir.model.relation', 'ir.model.constraint', 'ir.module.module',
)

COMPANY_DEPENDENT_FIELDS = (
    'char', 'float', 'boolean', 'integer', 'text', 'many2one', 'date', 'datetime', 'selection', 'html'
)

_logger = logging.getLogger('odoo.fields')


def resolve_mro(model, name, predicate):
    """ Return the list of successively overridden values of attribute ``name``
        in mro order on ``model`` that satisfy ``predicate``.  Model registry
        classes are ignored.
    """
    result = []
    for cls in model._model_classes:
        value = cls.__dict__.get(name, SENTINEL)
        if value is SENTINEL:
            continue
        if not predicate(value):
            break
        result.append(value)
    return result


def determine(needle, records, *args):
    """ Simple helper for calling a method given as a string or a function.

    :param needle: callable or name of method to call on ``records``
    :param BaseModel records: recordset to call ``needle`` on or with
    :params args: additional arguments to pass to the determinant
    :returns: the determined value if the determinant is a method name or callable
    :raise TypeError: if ``records`` is not a recordset, or ``needle`` is not
                      a callable or valid method name
    """
    if not isinstance(records, _models.BaseModel):
        raise TypeError("Determination requires a subject recordset")
    if isinstance(needle, str):
        needle = getattr(records, needle)
        if needle.__name__.find('__'):
            return needle(*args)
    elif callable(needle):
        if needle.__name__.find('__'):
            return needle(records, *args)

    raise TypeError("Determination requires a callable or method name")


class MetaField(type):
    """ Metaclass for field classes. """
    by_type = {}

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


class Field(MetaField('DummyField', (object,), {}), typing.Generic[T]):
    """The field descriptor contains the field definition, and manages accesses
    and assignments of the corresponding field on records. The following
    attributes may be provided when instantiating a field:

    :param str string: the label of the field seen by users; if not
        set, the ORM takes the field name in the class (capitalized).

    :param str help: the tooltip of the field seen by users

    :param bool readonly: whether the field is readonly (default: ``False``)

        This only has an impact on the UI. Any field assignation in code will work
        (if the field is a stored field or an inversable one).

    :param bool required: whether the value of the field is required (default: ``False``)

    :param str index: whether the field is indexed in database, and the kind of index.
        Note: this has no effect on non-stored and virtual fields.
        The possible values are:

        * ``"btree"`` or ``True``: standard index, good for many2one
        * ``"btree_not_null"``: BTREE index without NULL values (useful when most
                                values are NULL, or when NULL is never searched for)
        * ``"trigram"``: Generalized Inverted Index (GIN) with trigrams (good for full-text search)
        * ``None`` or ``False``: no index (default)

    :param default: the default value for the field; this is either a static
        value, or a function taking a recordset and returning a value; use
        ``default=None`` to discard default values for the field
    :type default: value or callable

    :param str groups: comma-separated list of group xml ids (string); this
        restricts the field access to the users of the given groups only

    :param bool company_dependent: whether the field value is dependent of the current company;

        The value is stored on the model table as jsonb dict with the company id as the key.

        The field's default values stored in model ir.default are used as fallbacks for
        unspecified values in the jsonb dict.

    :param bool copy: whether the field value should be copied when the record
        is duplicated (default: ``True`` for normal fields, ``False`` for
        ``one2many`` and computed fields, including property fields and
        related fields)

    :param bool store: whether the field is stored in database
        (default:``True``, ``False`` for computed fields)

    :param str aggregator: aggregate function used by :meth:`~odoo.models.Model.read_group`
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
        the current field. For selection fields, ``group_expand=True`` automatically
        expands groups for all selection keys.

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

    :param bool precompute: whether the field should be computed before record insertion
        in database.  Should be used to specify manually some fields as precompute=True
        when the field can be computed before record insertion.
        (e.g. avoid statistics fields based on search/read_group), many2one
        linking to the previous record, ... (default: `False`)

        .. warning::

            Precomputation only happens when no explicit value and no default
            value is provided to create().  This means that a default value
            disables the precomputation, even if the field is specified as
            precompute=True.

            Precomputing a field can be counterproductive if the records of the
            given model are not created in batch.  Consider the situation were
            many records are created one by one.  If the field is not
            precomputed, it will normally be computed in batch at the flush(),
            and the prefetching mechanism will help making the computation
            efficient.  On the other hand, if the field is precomputed, the
            computation will be made one by one, and will therefore not be able
            to take advantage of the prefetching mechanism.

            Following the remark above, precomputed fields can be interesting on
            the lines of a one2many, which are usually created in batch by the
            ORM itself, provided that they are created by writing on the record
            that contains them.

    :param bool compute_sudo: whether the field should be recomputed as superuser
        to bypass access rights (by default ``True`` for stored fields, ``False``
        for non stored fields)

    :param bool recursive: whether the field has recursive dependencies (the field
        ``X`` has a dependency like ``parent_id.X``); declaring a field recursive
        must be explicit to guarantee that recomputation is correct

    :param str inverse: name of a method that inverses the field (optional)

    :param str search: name of a method that implement search on the field (optional)

    :param str related: sequence of field names

    :param bool default_export_compatible: whether the field must be exported by default in an import-compatible export

        .. seealso:: :ref:`Advanced fields/Related fields <reference/fields/related>`
    """

    type: str                           # type of the field (string)
    relational = False                  # whether the field is a relational one
    translate = False                   # whether the field is translated
    is_text = False                     # whether the field is a text type in the database
    falsy_value = None                  # falsy value for comparisons (optional)

    write_sequence = 0  # field ordering for write()
    # Database column type (ident, spec) for non-company-dependent fields.
    # Company-dependent fields are stored as jsonb (see column_type).
    _column_type: typing.Tuple[str, str] | None = None

    args = None                         # the parameters given to __init__()
    _module = None                      # the field's module name
    _modules = None                     # modules that define this field
    _setup_done = True                  # whether the field is completely set up
    _sequence = None                    # absolute ordering of the field
    _base_fields = ()                   # the fields defining self, in override order
    _extra_keys = ()                    # unknown attributes set on the field
    _direct = False                     # whether self may be used directly (shared)
    _toplevel = False                   # whether self is on the model's registry class

    inherited = False                   # whether the field is inherited (_inherits)
    inherited_field = None              # the corresponding inherited field

    name: str                           # name of the field
    model_name: str | None = None       # name of the model of this field
    comodel_name: str | None = None     # name of the model of values (if relational)

    store = True                        # whether the field is stored in database
    index = None                        # how the field is indexed in database
    manual = False                      # whether the field is a custom field
    copy = True                         # whether the field is copied over by BaseModel.copy()
    _depends = None                     # collection of field dependencies
    _depends_context = None             # collection of context key dependencies
    recursive = False                   # whether self depends on itself
    compute = None                      # compute(recs) computes field on recs
    compute_sudo = False                # whether field should be recomputed as superuser
    precompute = False                  # whether field has to be computed before creation
    inverse = None                      # inverse(recs) inverses field on recs
    search = None                       # search(recs, operator, value) searches on self
    related = None                      # sequence of field names, for related fields
    company_dependent = False           # whether ``self`` is company-dependent (property field)
    default = None                      # default(recs) returns the default value

    string: str | None = None           # field label
    export_string_translation = True    # whether the field label translations are exported
    help: str | None = None             # field tooltip
    readonly = False                    # whether the field is readonly
    required = False                    # whether the field is required
    groups: str | None = None           # csv list of group xml ids
    change_default = False              # whether the field may trigger a "user-onchange"

    related_field = None                # corresponding related field
    aggregator = None                   # operator for aggregating values
    group_expand = None                 # name of method to expand groups in read_group()
    falsy_value_label = None            # value to display when the field is not set (webclient attr)
    prefetch = True                     # the prefetch group (False means no group)

    default_export_compatible = False   # whether the field must be exported by default in an import-compatible export
    exportable = True

    def __init__(self, string: str | Sentinel = SENTINEL, **kwargs):
        kwargs['string'] = string
        self._sequence = next(_global_seq)
        self.args = {key: val for key, val in kwargs.items() if val is not SENTINEL}

    def __str__(self):
        if self.name is None:
            return "<%s.%s>" % (__name__, type(self).__name__)
        return "%s.%s" % (self.model_name, self.name)

    def __repr__(self):
        if self.name is None:
            return f"{'<%s.%s>'!r}" % (__name__, type(self).__name__)
        return f"{'%s.%s'!r}" % (self.model_name, self.name)

    ############################################################################
    #
    # Base field setup: things that do not depend on other models/fields
    #
    # The base field setup is done by field.__set_name__(), which determines the
    # field's name, model name, module and its parameters.
    #
    # The dictionary field.args gives the parameters passed to the field's
    # constructor.  Most parameters have an attribute of the same name on the
    # field.  The parameters as attributes are assigned by the field setup.
    #
    # When several definition classes of the same model redefine a given field,
    # the field occurrences are "merged" into one new field instantiated at
    # runtime on the registry class of the model.  The occurrences of the field
    # are given to the new field as the parameter '_base_fields'; it is a list
    # of fields in override order (or reverse MRO).
    #
    # In order to save memory, a field should avoid having field.args and/or
    # many attributes when possible.  We call "direct" a field that can be set
    # up directly from its definition class.  Direct fields are non-related
    # fields defined on models, and can be shared across registries.  We call
    # "toplevel" a field that is put on the model's registry class, and is
    # therefore specific to the registry.
    #
    # Toplevel field are set up once, and are no longer set up from scratch
    # after that.  Those fields can save memory by discarding field.args and
    # field._base_fields once set up, because those are no longer necessary.
    #
    # Non-toplevel non-direct fields are the fields on definition classes that
    # may not be shared.  In other words, those fields are never used directly,
    # and are always recreated as toplevel fields.  On those fields, the base
    # setup is useless, because only field.args is used for setting up other
    # fields.  We therefore skip the base setup for those fields.  The only
    # attributes of those fields are: '_sequence', 'args', 'model_name', 'name'
    # and '_module', which makes their __dict__'s size minimal.

    def __set_name__(self, owner, name):
        """ Perform the base setup of a field.

        :param owner: the owner class of the field (the model's definition or registry class)
        :param name: the name of the field
        """
        assert isinstance(owner, _models.MetaModel)
        self.model_name = owner._name
        self.name = name
        if getattr(owner, 'pool', None) is None:  # models.is_definition_class(owner)
            # only for fields on definition classes, not registry classes
            self._module = owner._module
            owner._field_definitions.append(self)

        if not self.args.get('related'):
            self._direct = True
        if self._direct or self._toplevel:
            self._setup_attrs(owner, name)
            if self._toplevel:
                # free memory, self.args and self._base_fields are no longer useful
                self.__dict__.pop('args', None)
                self.__dict__.pop('_base_fields', None)

    #
    # Setup field parameter attributes
    #

    def _get_attrs(self, model_class, name):
        """ Return the field parameter attributes as a dictionary. """
        # determine all inherited field attributes
        attrs = {}
        modules = []
        for field in self.args.get('_base_fields', ()):
            if not isinstance(self, type(field)):
                # 'self' overrides 'field' and their types are not compatible;
                # so we ignore all the parameters collected so far
                attrs.clear()
                modules.clear()
                continue
            attrs.update(field.args)
            if field._module:
                modules.append(field._module)
        attrs.update(self.args)
        if self._module:
            modules.append(self._module)

        attrs['args'] = self.args
        attrs['model_name'] = model_class._name
        attrs['name'] = name
        attrs['_module'] = modules[-1] if modules else None
        attrs['_modules'] = tuple(set(modules))

        # initialize ``self`` with ``attrs``
        if name == 'state':
            # by default, `state` fields should be reset on copy
            attrs['copy'] = attrs.get('copy', False)
        if attrs.get('compute'):
            # by default, computed fields are not stored, computed in superuser
            # mode if stored, not copied (unless stored and explicitly not
            # readonly), and readonly (unless inversible)
            attrs['store'] = store = attrs.get('store', False)
            attrs['compute_sudo'] = attrs.get('compute_sudo', store)
            if not (attrs['store'] and not attrs.get('readonly', True)):
                attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))
        if attrs.get('related'):
            # by default, related fields are not stored, computed in superuser
            # mode, not copied and readonly
            attrs['store'] = store = attrs.get('store', False)
            attrs['compute_sudo'] = attrs.get('compute_sudo', attrs.get('related_sudo', True))
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', True)
        if attrs.get('precompute'):
            if not attrs.get('compute') and not attrs.get('related'):
                warnings.warn(f"precompute attribute doesn't make any sense on non computed field {self}", stacklevel=1)
                attrs['precompute'] = False
            elif not attrs.get('store'):
                warnings.warn(f"precompute attribute has no impact on non stored field {self}", stacklevel=1)
                attrs['precompute'] = False
        if attrs.get('company_dependent'):
            if attrs.get('required'):
                warnings.warn(f"company_dependent field {self} cannot be required", stacklevel=1)
            if attrs.get('translate'):
                warnings.warn(f"company_dependent field {self} cannot be translated", stacklevel=1)
            if self.type not in COMPANY_DEPENDENT_FIELDS:
                warnings.warn(f"company_dependent field {self} is not one of the allowed types {COMPANY_DEPENDENT_FIELDS}", stacklevel=1)
            attrs['copy'] = attrs.get('copy', False)
            # speed up search and on delete
            attrs['index'] = attrs.get('index', 'btree_not_null')
            attrs['prefetch'] = attrs.get('prefetch', 'company_dependent')
            attrs['_depends_context'] = ('company',)
        # parameters 'depends' and 'depends_context' are stored in attributes
        # '_depends' and '_depends_context', respectively
        if 'depends' in attrs:
            attrs['_depends'] = tuple(attrs.pop('depends'))
        if 'depends_context' in attrs:
            attrs['_depends_context'] = tuple(attrs.pop('depends_context'))

        if 'group_operator' in attrs:
            warnings.warn("Since Odoo 18, 'group_operator' is deprecated, use 'aggregator' instead", DeprecationWarning, stacklevel=2)
            attrs['aggregator'] = attrs.pop('group_operator')

        return attrs

    def _setup_attrs(self, model_class, name):
        """ Initialize the field parameter attributes. """
        attrs = self._get_attrs(model_class, name)

        # determine parameters that must be validated
        extra_keys = [key for key in attrs if not hasattr(self, key)]
        if extra_keys:
            attrs['_extra_keys'] = extra_keys

        self.__dict__.update(attrs)

        # prefetch only stored, column, non-manual fields
        if not self.store or not self.column_type or self.manual:
            self.prefetch = False

        if not self.string and not self.related:
            # related fields get their string from their parent field
            self.string = (
                name[:-4] if name.endswith('_ids') else
                name[:-3] if name.endswith('_id') else name
            ).replace('_', ' ').title()

        # self.default must be either None or a callable
        if self.default is not None and not callable(self.default):
            value = self.default
            self.default = lambda model: value

    ############################################################################
    #
    # Complete field setup: everything else
    #

    def prepare_setup(self):
        self._setup_done = False

    def setup(self, model):
        """ Perform the complete setup of a field. """
        if not self._setup_done:
            # validate field params
            for key in self._extra_keys:
                if not model._valid_field_parameter(self, key):
                    _logger.warning(
                        "Field %s: unknown parameter %r, if this is an actual"
                        " parameter you may want to override the method"
                        " _valid_field_parameter on the relevant model in order to"
                        " allow it",
                        self, key
                    )
            if self.related:
                self.setup_related(model)
            else:
                self.setup_nonrelated(model)

            if not isinstance(self.required, bool):
                warnings.warn(f'Property {self}.required should be a boolean ({self.required}).', stacklevel=1)

            if not isinstance(self.readonly, bool):
                warnings.warn(f'Property {self}.readonly should be a boolean ({self.readonly}).', stacklevel=1)

            self._setup_done = True

    #
    # Setup of non-related fields
    #

    def setup_nonrelated(self, model):
        """ Determine the dependencies and inverse field(s) of ``self``. """
        pass

    def get_depends(self, model: BaseModel):
        """ Return the field's dependencies and cache dependencies. """
        if self._depends is not None:
            # the parameter 'depends' has priority over 'depends' on compute
            return self._depends, self._depends_context or ()

        if self.related:
            if self._depends_context is not None:
                depends_context = self._depends_context
            else:
                related_model = model.env[self.related_field.model_name]
                depends, depends_context = self.related_field.get_depends(related_model)
            return [self.related], depends_context

        if not self.compute:
            return (), self._depends_context or ()

        # determine the functions implementing self.compute
        if isinstance(self.compute, str):
            funcs = resolve_mro(model, self.compute, callable)
        else:
            funcs = [self.compute]

        # collect depends and depends_context
        depends = []
        depends_context = list(self._depends_context or ())
        for func in funcs:
            deps = getattr(func, '_depends', ())
            depends.extend(deps(model) if callable(deps) else deps)
            depends_context.extend(getattr(func, '_depends_context', ()))

        return depends, depends_context

    #
    # Setup of related fields
    #

    def setup_related(self, model):
        """ Setup the attributes of a related field. """
        assert isinstance(self.related, str), self.related

        # determine the chain of fields, and make sure they are all set up
        model_name = self.model_name
        for name in self.related.split('.'):
            field = model.pool[model_name]._fields.get(name)
            if field is None:
                raise KeyError(
                    f"Field {name} referenced in related field definition {self} does not exist."
                )
            if not field._setup_done:
                field.setup(model.env[model_name])
            model_name = field.comodel_name

        self.related_field = field

        # check type consistency
        if self.type != field.type:
            raise TypeError("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        self.compute = self._compute_related
        if self.inherited or not (self.readonly or field.readonly):
            self.inverse = self._inverse_related
        if field._description_searchable:
            # allow searching on self only if the related field is searchable
            self.search = self._search_related

        # A readonly related field without an inverse method should not have a
        # default value, as it does not make sense.
        if self.default and self.readonly and not self.inverse:
            _logger.warning("Redundant default on %s", self)

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            # check whether 'attr' is explicitly set on self (from its field
            # definition), and ignore its class-level value (only a default)
            if attr not in self.__dict__ and prop.startswith('_related_'):
                setattr(self, attr, getattr(field, prop))

        for attr in field._extra_keys:
            if not hasattr(self, attr) and model._valid_field_parameter(self, attr):
                setattr(self, attr, getattr(field, attr))

        # special cases of inherited fields
        if self.inherited:
            self.inherited_field = field
            if field.required:
                self.required = True
            # add modules from delegate and target fields; the first one ensures
            # that inherited fields introduced via an abstract model (_inherits
            # being on the abstract model) are assigned an XML id
            delegate_field = model._fields[self.related.split('.')[0]]
            self._modules = tuple({*self._modules, *delegate_field._modules, *field._modules})

        if self.store and self.translate:
            _logger.warning("Translated stored related field (%s) will not be computed correctly in all languages", self)

    def traverse_related(self, record):
        """ Traverse the fields of the related field `self` except for the last
        one, and return it as a pair `(last_record, last_field)`. """
        for name in self.related.split('.')[:-1]:
            # take the first record when traversing
            corecord = record[name]
            record = next(iter(corecord), corecord)
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
        for name in self.related.split('.')[:-1]:
            try:
                values = [next(iter(val := value[name]), val) for value in values]
            except AccessError as e:
                description = records.env['ir.model']._get(records._name).name
                env = records.env
                raise AccessError(env._(
                    "%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).",
                    previous_message=e.args[0],
                    document_kind=description,
                    document_model=records._name,
                ))
        # assign final values to records
        for record, value in zip(records, values):
            record[self.name] = self._process_related(value[self.related_field.name], record.env)

    def _process_related(self, value, env):
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

        # Compute the new domain for ('x.y.z', op, value)
        # as ('x', 'any', [('y', 'any', [('z', op, value)])])
        # If the followed relation is a nullable many2one, we accept null
        # for that path as well.

        # determine whether the related field can be null
        falsy_value = self.falsy_value
        if isinstance(value, COLLECTION_TYPES):
            value_is_null = any(val is False or val is None or val == falsy_value for val in value)
        else:
            value_is_null = value is False or value is None or value == falsy_value
        can_be_null = (  # (..., '=', False) or (..., 'not in', [truthy vals])
            (operator not in NEGATIVE_CONDITION_OPERATORS) == value_is_null
        )

        # build the domain
        # Note that the access of many2one fields in the path is done using sudo
        # (see compute_sudo), but the given value may have a different context
        model = records.env[self.model_name].with_context(active_test=False)
        model = model.sudo(records.env.su or self.compute_sudo)

        # parse the path
        path = self.related.split('.')
        path_fields = []  # [(field, comodel | None)]
        comodel = model
        for fname in path:
            field = comodel._fields[fname]
            if field.relational:
                comodel = model.env[field.comodel_name]
            else:
                comodel = None
            path_fields.append((field, comodel))

        # if the value is a domain, resolve it using records' environment
        if isinstance(value, Domain):
            field, comodel = path_fields[-1]
            value = comodel.with_env(records.env)._search(value)

        # build the domain backwards with the any operator
        field, comodel = path_fields[-1]
        domain = Domain(field.name, operator, value)
        for field, comodel in reversed(path_fields[:-1]):
            domain = Domain(field.name, 'any', comodel._search(domain))
            if can_be_null and field.type == 'many2one' and not field.required:
                domain |= Domain(field.name, '=', False)
        return domain

    # properties used by setup_related() to copy values from related field
    _related_comodel_name = property(attrgetter('comodel_name'))
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_groups = property(attrgetter('groups'))
    _related_aggregator = property(attrgetter('aggregator'))

    @lazy_property
    def column_type(self) -> tuple[str, str] | None:
        """ Return the actual column type for this field, if stored as a column. """
        return ('jsonb', 'jsonb') if self.company_dependent or self.translate else self._column_type

    @property
    def base_field(self):
        """ Return the base field of an inherited field, or ``self``. """
        return self.inherited_field.base_field if self.inherited_field else self

    #
    # Company-dependent fields
    #

    def get_company_dependent_fallback(self, records):
        assert self.company_dependent
        fallback = records.env['ir.default'] \
            .with_user(SUPERUSER_ID) \
            .with_company(records.env.company) \
            ._get_model_defaults(records._name).get(self.name)
        fallback = self.convert_to_cache(fallback, records, validate=False)
        return self.convert_to_record(fallback, records)

    #
    # Setup of field triggers
    #

    def resolve_depends(self, registry):
        """ Return the dependencies of `self` as a collection of field tuples. """
        Model0 = registry[self.model_name]

        for dotnames in registry.field_depends[self]:
            field_seq = []
            model_name = self.model_name
            check_precompute = self.precompute

            for index, fname in enumerate(dotnames.split('.')):
                Model = registry[model_name]
                if Model0._transient and not Model._transient:
                    # modifying fields on regular models should not trigger
                    # recomputations of fields on transient models
                    break

                try:
                    field = Model._fields[fname]
                except KeyError:
                    raise ValueError(
                        f"Wrong @depends on '{self.compute}' (compute method of field {self}). "
                        f"Dependency field '{fname}' not found in model {model_name}."
                    )
                if field is self and index and not self.recursive:
                    self.recursive = True
                    warnings.warn(f"Field {self} should be declared with recursive=True", stacklevel=1)

                # precomputed fields can depend on non-precomputed ones, as long
                # as they are reachable through at least one many2one field
                if check_precompute and field.store and field.compute and not field.precompute:
                    warnings.warn(f"Field {self} cannot be precomputed as it depends on non-precomputed field {field}", stacklevel=1)
                    self.precompute = False

                if field_seq and not field_seq[-1]._description_searchable:
                    # the field before this one is not searchable, so there is
                    # no way to know which on records to recompute self
                    warnings.warn(
                        f"Field {field_seq[-1]!r} in dependency of {self} should be searchable. "
                        f"This is necessary to determine which records to recompute when {field} is modified. "
                        f"You should either make the field searchable, or simplify the field dependency.",
                        stacklevel=1,
                    )

                field_seq.append(field)

                # do not make self trigger itself: for instance, a one2many
                # field line_ids with domain [('foo', ...)] will have
                # 'line_ids.foo' as a dependency
                if not (field is self and not index):
                    yield tuple(field_seq)

                if field.type == 'one2many':
                    for inv_field in Model.pool.field_inverses[field]:
                        yield tuple(field_seq) + (inv_field,)

                if check_precompute and field.type == 'many2one':
                    check_precompute = False

                model_name = field.comodel_name

    ############################################################################
    #
    # Field description
    #

    def get_description(self, env, attributes=None):
        """ Return a dictionary that describes the field ``self``. """
        desc = {}
        for attr, prop in self.description_attrs:
            if attributes is not None and attr not in attributes:
                continue
            if not prop.startswith('_description_'):
                continue
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value is not None:
                desc[attr] = value

        return desc

    # properties used by get_description()
    _description_name = property(attrgetter('name'))
    _description_type = property(attrgetter('type'))
    _description_store = property(attrgetter('store'))
    _description_manual = property(attrgetter('manual'))
    _description_related = property(attrgetter('related'))
    _description_company_dependent = property(attrgetter('company_dependent'))
    _description_readonly = property(attrgetter('readonly'))
    _description_required = property(attrgetter('required'))
    _description_groups = property(attrgetter('groups'))
    _description_change_default = property(attrgetter('change_default'))
    _description_default_export_compatible = property(attrgetter('default_export_compatible'))
    _description_exportable = property(attrgetter('exportable'))

    def _description_depends(self, env):
        return env.registry.field_depends[self]

    @property
    def _description_searchable(self):
        return bool(self.store or self.search)

    def _description_sortable(self, env):
        if self.column_type and self.store:  # shortcut
            return True

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        try:
            model._order_field_to_sql(model._table, self.name, SQL(), SQL(), query)
            return True
        except (ValueError, AccessError):
            return False

    def _description_groupable(self, env):
        if self.column_type and self.store:  # shortcut
            return True

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        groupby = self.name if self.type not in ('date', 'datetime') else f"{self.name}:month"
        try:
            model._read_group_groupby(groupby, query)
            return True
        except (ValueError, AccessError):
            return False

    def _description_aggregator(self, env):
        if not self.aggregator or self.column_type and self.store:  # shortcut
            return self.aggregator

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        try:
            model._read_group_select(f"{self.name}:{self.aggregator}", query)
            return self.aggregator
        except (ValueError, AccessError):
            return None

    def _description_string(self, env):
        if self.string and env.lang:
            model_name = self.base_field.model_name
            field_string = env['ir.model.fields'].get_field_string(model_name)
            return field_string.get(self.name) or self.string
        return self.string

    def _description_help(self, env):
        if self.help and env.lang:
            model_name = self.base_field.model_name
            field_help = env['ir.model.fields'].get_field_help(model_name)
            return field_help.get(self.name) or self.help
        return self.help

    def _description_falsy_value_label(self, env):
        return env._(self.falsy_value_label) if self.falsy_value_label else None # pylint: disable=gettext-variable

    def is_editable(self):
        """ Return whether the field can be editable in a view. """
        return not self.readonly

    ############################################################################
    #
    # Conversion of values
    #

    def convert_to_column(self, value, record, values=None, validate=True):
        """ Convert ``value`` from the ``write`` format to the SQL parameter
        format for SQL conditions. This is used to compare a field's value when
        the field actually stores multiple values (translated or company-dependent).
        """
        if value is None or value is False:
            return None
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode()
        else:
            return str(value)

    def convert_to_column_insert(self, value, record, values=None, validate=True):
        """ Convert ``value`` from the ``write`` format to the SQL parameter
        format for INSERT queries. This method handles the case of fields that
        store multiple values (translated or company-dependent).
        """
        value = self.convert_to_column(value, record, values, validate)
        if not self.company_dependent:
            return value
        fallback = record.env['ir.default']._get_model_defaults(record._name).get(self.name)
        if value == self.convert_to_column(fallback, record):
            return None
        return PsycopgJson({record.env.company.id: value})

    def convert_to_column_update(self, value, record):
        """ Convert ``value`` from the ``to_flush`` format to the SQL parameter
        format for UPDATE queries. The ``to_flush`` format is the same as the
        cache format, except for translated fields (``{'lang_code': 'value', ...}``
        or ``None``) and company-dependent fields (``{company_id: value, ...}``).
        """
        if self.company_dependent:
            return PsycopgJson(value)
        return self.convert_to_column_insert(
            self.convert_to_write(value, record),
            record,
        )

    def convert_to_cache(self, value, record, validate=True):
        """ Convert ``value`` to the cache format; ``value`` may come from an
        assignment, or have the format of methods :meth:`BaseModel.read` or
        :meth:`BaseModel.write`. If the value represents a recordset, it should
        be added for prefetching on ``record``.

        :param value:
        :param record:
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

    def convert_to_read(self, value, record, use_display_name=True):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.read`.

        :param value:
        :param record:
        :param bool use_display_name: when True, the value's display name will be
            computed using `display_name`, if relevant for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, record):
        """ Convert ``value`` from any format to the format of method
        :meth:`BaseModel.write`.
        """
        cache_value = self.convert_to_cache(value, record, validate=False)
        record_value = self.convert_to_record(cache_value, record)
        return self.convert_to_read(record_value, record)

    def convert_to_export(self, value, record):
        """ Convert ``value`` from the record format to the export format. """
        if not value:
            return ''
        return value

    def convert_to_display_name(self, value, record):
        """ Convert ``value`` from the record format to a suitable display name. """
        return str(value) if value else False

    ############################################################################
    #
    # Update database schema
    #

    @property
    def column_order(self):
        """ Prescribed column order in table. """
        return 0 if self.column_type is None else sql.SQL_ORDER_BY_TYPE[self.column_type[0]]

    def update_db(self, model, columns):
        """ Update the database schema to implement this field.

            :param model: an instance of the field's model
            :param columns: a dict mapping column names to their configuration in database
            :return: ``True`` if the field must be recomputed on existing rows
        """
        if not self.column_type:
            return

        column = columns.get(self.name)

        # create/update the column, not null constraint; the index will be
        # managed by registry.check_indexes()
        self.update_db_column(model, column)
        self.update_db_notnull(model, column)

        # optimization for computing simple related fields like 'foo_id.bar'
        if (
            not column
            and self.related and self.related.count('.') == 1
            and self.related_field.store and not self.related_field.compute
            and not (self.related_field.type == 'binary' and self.related_field.attachment)
            and self.related_field.type not in ('one2many', 'many2many')
        ):
            join_field = model._fields[self.related.split('.')[0]]
            if (
                join_field.type == 'many2one'
                and join_field.store and not join_field.compute
            ):
                model.pool.post_init(self.update_db_related, model)
                # discard the "classical" computation
                return False

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
        if column['is_nullable'] == 'NO':
            sql.drop_not_null(model._cr, model._table, self.name)
        self._convert_db_column(model, column)

    def _convert_db_column(self, model, column):
        """ Convert the given database column to the type of the field. """
        sql.convert_column(model._cr, model._table, self.name, self.column_type[1])

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
            # _init_column may delay computations in post-init phase
            @model.pool.post_init
            def add_not_null():
                # flush values before adding NOT NULL constraint
                model.flush_model([self.name])
                model.pool.post_constraint(apply_required, model, self.name)

        elif not self.required and has_notnull:
            sql.drop_not_null(model._cr, model._table, self.name)

    def update_db_related(self, model):
        """ Compute a stored related field directly in SQL. """
        comodel = model.env[self.related_field.model_name]
        join_field, comodel_field = self.related.split('.')
        model.env.cr.execute(SQL(
            """ UPDATE %(model_table)s AS x
                SET %(model_field)s = y.%(comodel_field)s
                FROM %(comodel_table)s AS y
                WHERE x.%(join_field)s = y.id """,
            model_table=SQL.identifier(model._table),
            model_field=SQL.identifier(self.name),
            comodel_table=SQL.identifier(comodel._table),
            comodel_field=SQL.identifier(comodel_field),
            join_field=SQL.identifier(join_field),
        ))

    ############################################################################
    #
    # SQL generation methods
    #

    def to_sql(self, model: BaseModel, alias: str, flush: bool = True) -> SQL:
        """ Return an :class:`SQL` object that represents the value of the given
        field from the given table alias.

        The query object is necessary for fields that need to add tables to the query.

        When parameter ``flush`` is true, the method adds some metadata in the
        result to make method :meth:`~odoo.api.Environment.execute_query` flush
        the field before executing the query.
        """
        if not self.store or not self.column_type:
            raise ValueError(f"Cannot convert {self} to SQL because it is not stored")
        field_to_flush = self if flush else None
        sql_field = SQL.identifier(alias, self.name, to_flush=field_to_flush)
        if self.company_dependent:
            fallback = self.get_company_dependent_fallback(model)
            fallback = self.convert_to_column(self.convert_to_write(fallback, model), model)
            # in _read_group_orderby the result of field to sql will be mogrified and split to
            # e.g SQL('COALESCE(%s->%s') and SQL('to_jsonb(%s))::boolean') as 2 orderby values
            # and concatenated by SQL(',') in the final result, which works in an unexpected way
            sql_field = SQL(
                "COALESCE(%(column)s->%(company_id)s,to_jsonb(%(fallback)s::%(column_type)s))",
                column=sql_field,
                company_id=str(model.env.company.id),
                fallback=fallback,
                column_type=SQL(self._column_type[1]),
            )
            if self.type in ('boolean', 'integer', 'float', 'monetary'):
                return SQL('(%s)::%s', sql_field, SQL(self._column_type[1]))
            # here the specified value for a company might be NULL e.g. '{"1": null}'::jsonb
            # the result of current sql_field might be 'null'::jsonb
            # ('null'::jsonb)::text == 'null'
            # ('null'::jsonb->>0)::text IS NULL
            return SQL('(%s->>0)::%s', sql_field, SQL(self._column_type[1]))
        return sql_field

    def property_to_sql(self, field_sql: SQL, property_name: str, model: BaseModel, alias: str, query: Query) -> SQL:
        """ Return an :class:`SQL` object that represents the value of the given
        expression from the given table alias.

        The query object is necessary for fields that need to add tables to the query.
        """
        raise ValueError(f"Invalid field property {property_name!r} on {self}")

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        """ Return an :class:`SQL` object that represents the domain condition
        given by the triple ``(field_expr, operator, value)`` with the given
        table alias, and in the context of the given query.

        This method should use the model to resolve the SQL and check access
        of the field.
        """
        sql_expr = self._condition_to_sql(field_expr, operator, value, model, alias, query)
        if self.company_dependent:
            sql_expr = self._condition_to_sql_company(sql_expr, field_expr, operator, value, model, alias, query)
        return sql_expr

    def _condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        sql_field = model._field_to_sql(alias, field_expr, query)

        def _value_to_column(v):
            return self.convert_to_column(v, model, validate=False)

        # support for SQL value
        # TODO deprecate this usage
        if operator in SQL_OPERATORS and isinstance(value, SQL):
            return SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], value)

        # operator: in (equality)
        equal_operator = None
        if operator in ('=', '!='):
            equal_operator = operator
            operator = 'in' if operator == '=' else 'not in'
            value = [value]

        if operator in ('in', 'not in'):
            assert isinstance(value, COLLECTION_TYPES), \
                f"condition_to_sql() 'in' operator expects a collection, not a {value!r}"
            params = tuple(_value_to_column(v) for v in value if v is not False and v is not None)
            null_in_condition = len(params) < len(value)
            # if we have a value treated as null
            if (null_value := self.falsy_value) is not None:
                null_value = _value_to_column(null_value)
                if null_value in params:
                    null_in_condition = True
                elif null_in_condition:
                    params = (*params, null_value)

            sql = None
            if params:
                if equal_operator:
                    assert len(params) == 1
                    sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[equal_operator], params[0])
                else:
                    sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], params)

            if (operator == 'in') == null_in_condition:
                # field in {val, False} => field IN vals OR field IS NULL
                # field not in {val} => field NOT IN vals OR field IS NULL
                sql_null = SQL("%s IS NULL", sql_field)
                return SQL("(%s OR %s)", sql, sql_null) if sql else sql_null

            elif operator == 'not in' and null_in_condition and not sql:
                # if we have a base query, null values are already exluded
                return SQL("%s IS NOT NULL", sql_field)

            assert sql, f"Missing sql query for {operator} {value!r}"
            return sql

        # operator: like
        if operator.endswith('like'):
            # cast value to text for any like comparison
            sql_left = sql_field if self.is_text else SQL("%s::text", sql_field)

            # add wildcard and unaccent depending on the operator
            need_wildcard = '=' not in operator
            if need_wildcard:
                sql_value = SQL("%s", f"%{value}%")
            else:
                sql_value = SQL("%s", str(value))
            if operator.endswith('ilike'):
                sql_left = model.env.registry.unaccent(sql_left)
                sql_value = model.env.registry.unaccent(sql_value)

            sql = SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], sql_value)
            if operator in NEGATIVE_CONDITION_OPERATORS:
                sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
            return sql

        # operator: inequality
        if operator in ('>', '<', '>=', '<='):
            can_be_null = False
            if (null_value := self.falsy_value) is not None and not isinstance(null_value, str):  # TODO remove check on str
                value = self.convert_to_cache(value, model) or null_value
                can_be_null = (
                    null_value < value if operator == '<' else
                    null_value > value if operator == '>' else
                    null_value <= value if operator == '<=' else
                    null_value >= value  # operator == '>='
                )
            sql_value = SQL("%s", _value_to_column(value))

            sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], sql_value)
            if can_be_null:
                sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
            return sql

        # operator: any
        # Note: relational operators overwrite this function for a more specific
        # behaviour, here we check just the field against the subselect.
        # Example usage: ('id', 'any', Query | SQL)
        if operator in ('any', 'not any'):
            if isinstance(value, Query):
                subselect = value.subselect()
            elif isinstance(value, SQL):
                subselect = SQL("(%s)", value)
            else:
                raise TypeError(f"condition_to_sql() operator 'any' accepts SQL or Query, got {value}")
            sql_operator = SQL_OPERATORS["in" if operator == "any" else "not in"]
            return SQL("%s%s%s", sql_field, sql_operator, subselect)

        raise NotImplementedError(f"Invalid operator {operator!r} for SQL in domain term {(field_expr, operator, value)!r}")

    def _condition_to_sql_company(self, sql_expr: SQL, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        """ Add a not null condition on the field for company-dependent fields to use an existing index for better performance."""
        if (
            self.company_dependent
            and self.index == 'btree_not_null'
            and not (self.type in ('datetime', 'date') and field_expr != self.name)  # READ_GROUP_NUMBER_GRANULARITY is not supported
            and model.env['ir.default']._evaluate_condition_with_fallback(model._name, field_expr, operator, value) is False
        ):
            return SQL('(%s IS NOT NULL AND %s)', SQL.identifier(alias, self.name), sql_expr)
        return sql_expr

    ############################################################################
    #
    # Alternatively stored fields: if fields don't have a `column_type` (not
    # stored as regular db columns) they go through a read/create/write
    # protocol instead
    #

    def read(self, records):
        """ Read the value of ``self`` on ``records``, and store it in cache. """
        if not self.column_type:
            raise NotImplementedError("Method read() undefined on %s" % self)

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

        :param records:
        :param value: a value in any format
        """
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return

        # update the cache
        dirty = self.store and any(records._ids)
        cache.update(records, self, itertools.repeat(cache_value), dirty=dirty)

    ############################################################################
    #
    # Descriptor methods
    #

    def __get__(self, record: BaseModel, owner=None) -> T:
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

        if self.compute and self.store:
            # process pending computations
            self.recompute(record)

        try:
            value = env.cache.get(record, self)
            return self.convert_to_record(value, record)
        except KeyError:
            pass
        # behavior in case of cache miss:
        #
        #   on a real record:
        #       stored -> fetch from database (computation done above)
        #       not stored and computed -> compute
        #       not stored and not computed -> default
        #
        #   on a new record w/ origin:
        #       stored and not (computed and readonly) -> fetch from origin
        #       stored and computed and readonly -> compute
        #       not stored and computed -> compute
        #       not stored and not computed -> default
        #
        #   on a new record w/o origin:
        #       stored and computed -> compute
        #       stored and not computed -> new delegate or default
        #       not stored and computed -> compute
        #       not stored and not computed -> default
        #
        if self.store and record.id:
            # real record: fetch from database
            recs = self._in_cache_without(record, PREFETCH_MAX)
            try:
                recs._fetch_field(self)
            except AccessError:
                if len(recs) == 1:
                    raise
                record._fetch_field(self)
            if not env.cache.contains(record, self):
                raise MissingError("\n".join([
                    env._("Record does not exist or has been deleted."),
                    env._("(Record: %(record)s, User: %(user)s)", record=record, user=env.uid),
                ])) from None
            value = env.cache.get(record, self)

        elif self.store and record._origin and not (self.compute and self.readonly):
            # new record with origin: fetch from origin
            value = self.convert_to_cache(record._origin[self.name], record, validate=False)
            value = env.cache.patch_and_set(record, self, value)

        elif self.compute: #pylint: disable=using-constant-test
            # non-stored field or new record without origin: compute
            if env.is_protected(self, record):
                value = self.convert_to_cache(False, record, validate=False)
                env.cache.set(record, self, value)
            else:
                recs = record if self.recursive else self._in_cache_without(record, PREFETCH_MAX)
                try:
                    self.compute_value(recs)
                except (AccessError, MissingError):
                    self.compute_value(record)
                    recs = record

                missing_recs_ids = tuple(env.cache.get_missing_ids(recs, self))
                if missing_recs_ids:
                    missing_recs = record.browse(missing_recs_ids)
                    if self.readonly and not self.store:
                        raise ValueError(f"Compute method failed to assign {missing_recs}.{self.name}")
                    # fallback to null value if compute gives nothing, do it for every unset record
                    false_value = self.convert_to_cache(False, record, validate=False)
                    env.cache.update(missing_recs, self, itertools.repeat(false_value))

                value = env.cache.get(record, self)

        elif self.type == 'many2one' and self.delegate and not record.id:
            # parent record of a new record: new record, with the same
            # values as record for the corresponding inherited fields
            def is_inherited_field(name):
                field = record._fields[name]
                return field.inherited and field.related.split('.')[0] == self.name

            parent = record.env[self.comodel_name].new({
                name: value
                for name, value in record._cache.items()
                if is_inherited_field(name)
            })
            # in case the delegate field has inverse one2many fields, this
            # updates the inverse fields as well
            record._update_cache({self.name: parent}, validate=False)
            value = env.cache.get(record, self)

        else:
            # non-stored field or stored field on new record: default value
            value = self.convert_to_cache(False, record, validate=False)
            value = env.cache.patch_and_set(record, self, value)
            defaults = record.default_get([self.name])
            if self.name in defaults:
                # The null value above is necessary to convert x2many field
                # values. For instance, converting [(Command.LINK, id)]
                # accesses the field's current value, then adds the given
                # id. Without an initial value, the conversion ends up here
                # to determine the field's value, and generates an infinite
                # recursion.
                value = self.convert_to_cache(defaults[self.name], record)
                env.cache.set(record, self, value)

        return self.convert_to_record(value, record)

    def _in_cache_without(self, record, limit=None):
        """ Return records to prefetch that have no value in cache. """
        ids = expand_ids(record.id, record._prefetch_ids)
        ids = record.env.cache.get_missing_ids(record.browse(ids), self)
        if limit:
            ids = itertools.islice(ids, limit)
        # Those records are aimed at being either fetched, or computed.  But the
        # method '_fetch_field' is not correct with new records: it considers
        # them as forbidden records, and clears their cache!  On the other hand,
        # compute methods are not invoked with a mix of real and new records for
        # the sake of code simplicity.
        return record.browse(ids)

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
            protected_records = records.__class__(records.env, tuple(protected_ids), records._prefetch_ids)
            self.write(protected_records, value)

        if new_ids:
            # new records: no business logic
            new_records = records.__class__(records.env, tuple(new_ids), records._prefetch_ids)
            with records.env.protecting(records.pool.field_computed.get(self, [self]), new_records):
                if self.relational:
                    new_records.modified([self.name], before=True)
                self.write(new_records, value)
                new_records.modified([self.name])

            if self.inherited:
                # special case: also assign parent records if they are new
                parents = new_records[self.related.split('.')[0]]
                parents.filtered(lambda r: not r.id)[self.name] = value

        if other_ids:
            # base case: full business logic
            records = records.__class__(records.env, tuple(other_ids), records._prefetch_ids)
            write_value = self.convert_to_write(value, records)
            records.write({self.name: write_value})

    ############################################################################
    #
    # Computation of field values
    #

    def recompute(self, records):
        """ Process the pending computations of ``self`` on ``records``. This
        should be called only if ``self`` is computed and stored.
        """
        to_compute_ids = records.env.transaction.tocompute.get(self)
        if not to_compute_ids:
            return

        def apply_except_missing(func, records):
            """ Apply `func` on `records`, with a fallback ignoring non-existent records. """
            try:
                func(records)
            except MissingError:
                existing = records.exists()
                if existing:
                    func(existing)
                # mark the field as computed on missing records, otherwise they
                # remain to compute forever, which may lead to an infinite loop
                missing = records - existing
                for f in records.pool.field_computed[self]:
                    records.env.remove_to_compute(f, missing)

        if self.recursive:
            # recursive computed fields are computed record by record, in order
            # to recursively handle dependencies inside records
            def recursive_compute(records):
                for record in records:
                    if record.id in to_compute_ids:
                        self.compute_value(record)

            apply_except_missing(recursive_compute, records)
            return

        for record in records:
            if record.id in to_compute_ids:
                ids = expand_ids(record.id, to_compute_ids)
                recs = record.browse(itertools.islice(ids, PREFETCH_MAX))
                try:
                    apply_except_missing(self.compute_value, recs)
                except AccessError:
                    self.compute_value(record)

    def compute_value(self, records):
        """ Invoke the compute method on ``records``; the results are in cache. """
        env = records.env
        if self.compute_sudo:
            records = records.sudo()
        fields = records.pool.field_computed[self]

        # Just in case the compute method does not assign a value, we already
        # mark the computation as done. This is also necessary if the compute
        # method accesses the old value of the field: the field will be fetched
        # with _read(), which will flush() it. If the field is still to compute,
        # the latter flush() will recursively compute this field!
        for field in fields:
            if field.store:
                env.remove_to_compute(field, records)

        try:
            with records.env.protecting(fields, records):
                records._compute_field_value(self)
        except Exception:
            for field in fields:
                if field.store:
                    env.add_to_compute(field, records)
            raise

    def determine_inverse(self, records):
        """ Given the value of ``self`` on ``records``, inverse the computation. """
        determine(self.inverse, records)

    def determine_domain(self, records, operator, value):
        """ Return a domain representing a condition on ``self``. """
        return determine(self.search, records, operator, value)


def apply_required(model, field_name):
    """ Set a NOT NULL constraint on the given field, if necessary. """
    # At the time this function is called, the model's _fields may have been reset, although
    # the model's class is still the same. Retrieve the field to see whether the NOT NULL
    # constraint still applies
    field = model._fields[field_name]
    if field.store and field.required:
        sql.set_not_null(model.env.cr, model._table, field_name)


# forward-reference to models because we have this last cyclic dependency
# it is used in this file only for asserts
from . import models as _models  # noqa: E402
