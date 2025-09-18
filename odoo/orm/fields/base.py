"""High-level objects for fields."""

import collections
import functools
import itertools
import logging
import operator as pyoperator
import re
import time
import typing
import warnings
from collections.abc import Set as AbstractSet
from datetime import date, datetime
from operator import attrgetter

from psycopg.types.json import Json as PsycopgJson

from odoo.exceptions import AccessError, MissingError
from odoo.libs._field_access import scalar_cache_get as _scalar_cache_get
from odoo.libs.constants import PREFETCH_MAX
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    SQL,
    Query,
    reset_cached_properties,
    sql,
)

try:
    from odoo_rust import (
        to_prefetch_ids as _to_prefetch_ids_rust,  # type: ignore[import-untyped]
    )
except ImportError:
    _to_prefetch_ids_rust = None
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    MutableMapping,
)

from odoo.tools.misc import PENDING, SENTINEL, ReadonlyDict, Sentinel, unique

from ..domain import Domain
from ..primitives import COLLECTION_TYPES, SQL_OPERATORS, SUPERUSER_ID

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, DomainType, ModelType, Self, ValuesType
    from ..primitives import IdType
    from ..runtime import Environment, Registry

    M = typing.TypeVar("M", bound=BaseModel)


def expand_ids(id0: IdType, ids: Iterable[IdType]) -> Iterator[IdType]:
    """Return an iterator of unique ids from the concatenation of ``[id0]`` and
    ``ids``, and of the same kind (all real or all new).
    """
    yield id0
    seen = {id0}
    kind = bool(id0)
    for id_ in ids:
        if id_ not in seen and bool(id_) == kind:
            yield id_
            seen.add(id_)


IR_MODELS = (
    "ir.model",
    "ir.model.data",
    "ir.model.fields",
    "ir.model.fields.selection",
    "ir.model.relation",
    "ir.model.constraint",
    "ir.module.module",
)

COMPANY_DEPENDENT_FIELDS = (
    "char",
    "float",
    "boolean",
    "integer",
    "text",
    "many2one",
    "date",
    "datetime",
    "selection",
    "html",
)
PYTHON_INEQUALITY_OPERATOR = {
    "<": pyoperator.lt,
    ">": pyoperator.gt,
    "<=": pyoperator.le,
    ">=": pyoperator.ge,
}

_logger = logging.getLogger("odoo.fields")
_orm_compute = logging.getLogger("odoo.orm.compute")


def resolve_mro(model: BaseModel, name: str, predicate) -> list[typing.Any]:
    """Return the list of successively overridden values of attribute ``name``
    in mro order on ``model`` that satisfy ``predicate``.  Model registry
    classes are ignored.
    """
    result = []
    for cls in model._model_classes__:
        value = cls.__dict__.get(name, SENTINEL)
        if value is SENTINEL:
            continue
        if not predicate(value):
            break
        result.append(value)
    return result


def determine(needle: str | Callable, records: BaseModel, *args) -> typing.Any:
    """Simple helper for calling a method given as a string or a function.

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
        if not needle.__name__.startswith("__"):
            return needle(*args)
    elif callable(needle):
        if not needle.__name__.startswith("__"):
            return needle(records, *args)

    raise TypeError("Determination requires a callable or method name")


_global_seq = itertools.count()


class Field[T]:
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

    :param bool default_export_compatible: whether the field must be exported
        by default in an import-compatible export

    :param str search: name of a method that implements search on the field.
        The method takes an operator and value. Basic domain optimizations are
        ran before calling this function.
        For instance, all ``'='`` are transformed to ``'in'``, and boolean
        fields conditions are made such that operator is ``'in'``/``'not in'``
        and value is ``[True]``.

        The method should ``return NotImplemented`` if it does not support the
        operator.
        In that case, the ORM can try to call it with other, semantically
        equivalent, operators. For instance, try with the positive operator if
        its corresponding negative operator is not implemented.
        The method must return a :ref:`reference/orm/domains` that replaces
        ``(field, operator, value)`` in its domain.

        Note that a stored field can actually have a search method. The search
        method will be invoked to rewrite the condition. This may be useful for
        sanitizing the values used in the condition, for instance.

        .. code-block:: python

            def _search_partner_ref(self, operator, value):
                if operator not in ('in', 'like'):
                    return NotImplemented
                ...  # add your logic here, example
                return Domain('partner_id.ref', operator, value)

    .. rubric:: Aggregation

    :param str aggregator: default aggregate function used by the webclient
        on this field when using "Group By" feature.

        Supported aggregators are:

        * ``count`` : number of rows
        * ``count_distinct`` : number of distinct rows
        * ``bool_and`` : true if all values are true, otherwise false
        * ``bool_or`` : true if at least one value is true, otherwise false
        * ``max`` : maximum value of all values
        * ``min`` : minimum value of all values
        * ``avg`` : the average (arithmetic mean) of all values
        * ``sum`` : sum of all values

    :param str group_expand: function used to expand results when grouping on the
        current field for kanban/list/gantt views. For selection fields,
        ``group_expand=True`` automatically expands groups for all selection keys.

        .. code-block:: python

            @api.model
            def _read_group_selection_field(self, values, domain):
                return ['choice1', 'choice2', ...]  # available selection choices.


            @api.model
            def _read_group_many2one_field(self, records, domain):
                return records + self.search([custom_domain])

    .. rubric:: Computed Fields

    :param str compute: name of a method that computes the field

        .. seealso:: :ref:`Advanced Fields/Compute fields <reference/fields/compute>`

    :param bool precompute: whether the field should be computed before record insertion
        in database.  Should be used to specify manually some fields as precompute=True
        when the field can be computed before record insertion.
        (e.g. avoid statistics fields based on search/_read_group), many2one
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

    :param str related: sequence of field names

        .. seealso:: :ref:`Advanced fields/Related fields <reference/fields/related>`
    """

    type: str  # type of the field (string)
    relational: bool = False  # whether the field is a relational one
    translate: bool = False  # whether the field is translated
    is_text: bool = False  # whether the field is a text type in the database
    falsy_value: T | None = None  # falsy value for comparisons (optional)

    write_sequence: int = 0
    """Field processing priority in ``write()`` — lower values are processed first.

    Controls the order in which ``mark_dirty()`` is called during ``write()``.
    This matters for correctness when fields depend on each other's cached values:

    ========== ============== ============================================
    Sequence   Field Type     Reason
    ========== ============== ============================================
    0          Regular        Default — scalar fields, M2O, currency fields
    10         Monetary       Needs ``currency_id`` (seq 0) cached for rounding
    10         Properties     Must be written after the definition field
    20         x2many (O2M)   May flush other fields when deleting lines
    ========== ============== ============================================

    Custom field types with similar dependencies should override this attribute.
    """
    # Database column type (ident, spec) for non-company-dependent fields.
    # Company-dependent fields are stored as jsonb (see column_type).
    _column_type: tuple[str, str] | None = None

    _args__: dict[str, typing.Any] | None = None  # the parameters given to __init__()
    _module: str | None = None  # the field's module name
    _modules: tuple[str, ...] = ()  # modules that define this field
    _setup_done = True  # whether the field is completely set up
    _sequence: int  # absolute ordering of the field
    _base_fields__: tuple[Self, ...] = ()  # the fields defining self, in override order
    _extra_keys__: tuple[str, ...] = ()  # unknown attributes set on the field
    _direct: bool = False  # whether self may be used directly (shared)
    _toplevel: bool = False  # whether self is on the model's registry class

    inherited: bool = False  # whether the field is inherited (_inherits)
    inherited_field: Field | None = None  # the corresponding inherited field

    name: str = ""  # name of the field
    model_name: str = ""  # name of the model of this field
    comodel_name: str | None = None  # name of the model of values (if relational)

    store: bool = True  # whether the field is stored in database
    index: str | None = None  # how the field is indexed in database
    manual: bool = False  # whether the field is a custom field
    copy: bool = True  # whether the field is copied over by BaseModel.copy()
    _depends: Collection[str] | None = None  # collection of field dependencies
    _depends_context: Collection[str] | None = (
        None  # collection of context key dependencies
    )
    recursive: bool = False  # whether self depends on itself
    compute: str | Callable[[BaseModel], None] | None = (
        None  # compute(recs) computes field on recs
    )
    compute_sudo: bool = False  # whether field should be recomputed as superuser
    precompute: bool = False  # whether field has to be computed before creation
    inverse: str | Callable[[BaseModel], None] | None = (
        None  # inverse(recs) inverses field on recs
    )
    search: str | Callable[[BaseModel, str, typing.Any], DomainType] | None = (
        None  # search(recs, operator, value) searches on self
    )
    related: str | None = None  # sequence of field names, for related fields
    company_dependent: bool = (
        False  # whether ``self`` is company-dependent (property field)
    )
    default: Callable[[BaseModel], T] | T | None = (
        None  # default(recs) returns the default value
    )

    string: str | None = None  # field label
    export_string_translation: bool = (
        True  # whether the field label translations are exported
    )
    help: str | None = None  # field tooltip
    readonly: bool = False  # whether the field is readonly
    required: bool = False  # whether the field is required (NOT NULL in database)
    groups: str | None = None  # csv list of group xml ids
    change_default = False  # whether the field may trigger a "user-onchange"

    related_field: Field | None = None  # corresponding related field
    aggregator: str | None = None  # operator for aggregating values
    group_expand: (
        str | Callable[[BaseModel, ModelType, DomainType], ModelType] | None
    ) = None  # name of method to expand groups in formatted_read_group()
    falsy_value_label: str | None = (
        None  # value to display when the field is not set (webclient attr)
    )
    prefetch: bool | str = True  # the prefetch group (False means no group)

    default_export_compatible: bool = (
        False  # whether the field must be exported by default in an import-compatible export
    )
    exportable: bool = True

    # mapping from type name to field type
    _by_type__: dict[str, Field] = {}

    def __init__(self, string: str | Sentinel = SENTINEL, **kwargs):
        kwargs["string"] = string
        self._sequence = next(_global_seq)
        self._args__ = ReadonlyDict(
            {key: val for key, val in kwargs.items() if val is not SENTINEL}
        )

    def __str__(self) -> str:
        if not self.name:
            return f"<{__name__}.{type(self).__name__}>"
        return f"{self.model_name}.{self.name}"

    def __repr__(self) -> str:
        if not self.name:
            return repr(f"<{__name__}.{type(self).__name__}>")
        return repr(f"{self.model_name}.{self.name}")

    def __init_subclass__(cls):
        super().__init_subclass__()
        if not hasattr(cls, "type"):
            return

        if cls.type:
            cls._by_type__.setdefault(cls.type, cls)

        # compute class attributes to avoid calling dir() on fields
        cls.related_attrs = []
        cls.description_attrs = []
        for attr in dir(cls):
            if attr.startswith("_related_"):
                cls.related_attrs.append((attr.removeprefix("_related_"), attr))
            elif attr.startswith("_description_"):
                cls.description_attrs.append((attr.removeprefix("_description_"), attr))
        cls.related_attrs = tuple(cls.related_attrs)
        cls.description_attrs = tuple(cls.description_attrs)

    ############################################################################
    #
    # Base field setup: things that do not depend on other models/fields
    #
    # The base field setup is done by field.__set_name__(), which determines the
    # field's name, model name, module and its parameters.
    #
    # The dictionary field._args__ gives the parameters passed to the field's
    # constructor.  Most parameters have an attribute of the same name on the
    # field.  The parameters as attributes are assigned by the field setup.
    #
    # When several definition classes of the same model redefine a given field,
    # the field occurrences are "merged" into one new field instantiated at
    # runtime on the registry class of the model.  The occurrences of the field
    # are given to the new field as the parameter '_base_fields__'; it is a list
    # of fields in override order (or reverse MRO).
    #
    # In order to save memory, a field should avoid having field._args__ and/or
    # many attributes when possible.  We call "direct" a field that can be set
    # up directly from its definition class.  Direct fields are non-related
    # fields defined on models, and can be shared across registries.  We call
    # "toplevel" a field that is put on the model's registry class, and is
    # therefore specific to the registry.
    #
    # Toplevel field are set up once, and are no longer set up from scratch
    # after that.  Those fields can save memory by discarding field._args__ and
    # field._base_fields__ once set up, because those are no longer necessary.
    #
    # Non-toplevel non-direct fields are the fields on definition classes that
    # may not be shared.  In other words, those fields are never used directly,
    # and are always recreated as toplevel fields.  On those fields, the base
    # setup is useless, because only field._args__ is used for setting up other
    # fields.  We therefore skip the base setup for those fields.  The only
    # attributes of those fields are: '_sequence', '_args__', 'model_name', 'name'
    # and '_module', which makes their __dict__'s size minimal.

    def __set_name__(self, owner: type[BaseModel], name: str) -> None:
        """Perform the base setup of a field.

        :param owner: the owner class of the field (the model's definition or registry class)
        :param name: the name of the field
        """
        # during initialization, when importing `_models` at the end of this
        # file, it is not yet available and we already declare fields:
        # id and display_name
        # Note: also check for MetaModel attribute to handle partial module initialization
        # (when _models package is being loaded but MetaModel not yet available)
        _models_ref = globals().get("_models")
        assert (
            _models_ref is None
            or not hasattr(_models_ref, "MetaModel")
            or isinstance(owner, _models_ref.MetaModel)
        )
        self.model_name = owner._name
        self.name = name
        if getattr(owner, "pool", None) is None:  # models.is_model_definition(owner)
            # only for fields on definition classes, not registry classes
            self._module = owner._module
            owner._field_definitions.append(self)

        if not self._args__.get("related"):
            self._direct = True
        if self._direct or self._toplevel:
            self._setup_attrs__(owner, name)
            if self._toplevel:
                # free memory from stuff that is no longer useful
                self.__dict__.pop("_args__", None)
                if not self.related:
                    # keep _base_fields__ on related fields for incremental model setup
                    self.__dict__.pop("_base_fields__", None)

    #
    # Setup field parameter attributes
    #

    def _get_attrs(
        self, model_class: type[BaseModel], name: str
    ) -> dict[str, typing.Any]:
        """Return the field parameter attributes as a dictionary."""
        # determine all inherited field attributes
        attrs = {}
        modules: list[str] = []
        for field in self._args__.get("_base_fields__", ()):
            if not isinstance(self, type(field)):
                # 'self' overrides 'field' and their types are not compatible;
                # so we ignore all the parameters collected so far
                attrs.clear()
                modules.clear()
                continue
            attrs.update(field._args__)
            if field._module:
                modules.append(field._module)
        attrs.update(self._args__)
        if self._module:
            modules.append(self._module)

        attrs["model_name"] = model_class._name
        attrs["name"] = name
        attrs["_module"] = modules[-1] if modules else None
        # the following is faster than calling unique or using OrderedSet
        attrs["_modules"] = tuple(unique(modules) if len(modules) > 1 else modules)

        # initialize ``self`` with ``attrs``
        if name == "state":
            # by default, `state` fields should be reset on copy
            attrs["copy"] = attrs.get("copy", False)
        if attrs.get("compute"):
            # by default, computed fields are not stored, computed in superuser
            # mode if stored, not copied (unless stored and explicitly not
            # readonly), and readonly (unless inversible)
            attrs["store"] = store = attrs.get("store", False)
            attrs["compute_sudo"] = attrs.get("compute_sudo", store)
            if not (attrs["store"] and not attrs.get("readonly", True)):
                attrs["copy"] = attrs.get("copy", False)
            attrs["readonly"] = attrs.get("readonly", not attrs.get("inverse"))
        if attrs.get("related"):
            # by default, related fields are not stored, computed in superuser
            # mode, not copied and readonly
            attrs["store"] = store = attrs.get("store", False)
            attrs["compute_sudo"] = attrs.get(
                "compute_sudo", attrs.get("related_sudo", True)
            )
            attrs["copy"] = attrs.get("copy", False)
            attrs["readonly"] = attrs.get("readonly", True)
        if attrs.get("precompute"):
            if not attrs.get("compute") and not attrs.get("related"):
                warnings.warn(
                    f"precompute attribute doesn't make any sense on non computed field {self}",
                    stacklevel=1,
                )
                attrs["precompute"] = False
            elif not attrs.get("store"):
                warnings.warn(
                    f"precompute attribute has no impact on non stored field {self}",
                    stacklevel=1,
                )
                attrs["precompute"] = False
        if attrs.get("company_dependent"):
            if attrs.get("required"):
                warnings.warn(
                    f"company_dependent field {self} cannot be required",
                    stacklevel=1,
                )
            if attrs.get("translate"):
                warnings.warn(
                    f"company_dependent field {self} cannot be translated",
                    stacklevel=1,
                )
            if self.type not in COMPANY_DEPENDENT_FIELDS:
                warnings.warn(
                    f"company_dependent field {self} is not one of the allowed types {COMPANY_DEPENDENT_FIELDS}",
                    stacklevel=1,
                )
            attrs["copy"] = attrs.get("copy", False)
            # speed up search and on delete
            attrs["index"] = attrs.get("index", "btree_not_null")
            attrs["prefetch"] = attrs.get("prefetch", "company_dependent")
            attrs["_depends_context"] = ("company",)
        # parameters 'depends' and 'depends_context' are stored in attributes
        # '_depends' and '_depends_context', respectively
        if "depends" in attrs:
            attrs["_depends"] = tuple(attrs.pop("depends"))
        if "depends_context" in attrs:
            attrs["_depends_context"] = tuple(attrs.pop("depends_context"))

        if "group_operator" in attrs:
            warnings.warn(
                "Since Odoo 18, 'group_operator' is deprecated, use 'aggregator' instead",
                DeprecationWarning,
                stacklevel=2,
            )
            attrs["aggregator"] = attrs.pop("group_operator")

        return attrs

    def _setup_attrs__(self, model_class: type[BaseModel], name: str) -> None:
        """Initialize the field parameter attributes."""
        attrs = self._get_attrs(model_class, name)

        # determine parameters that must be validated
        extra_keys = tuple(key for key in attrs if not hasattr(self, key))
        if extra_keys:
            attrs["_extra_keys__"] = extra_keys

        self.__dict__.update(attrs)

        # prefetch only stored, column, non-manual fields
        if not self.store or not self.column_type or self.manual:
            self.prefetch = False

        if not self.string and not self.related:
            # related fields get their string from their parent field
            self.string = (
                (name[:-4] if name.endswith("_ids") else name.removesuffix("_id"))
                .replace("_", " ")
                .title()
            )

        # self.default must be either None or a callable
        if self.default is not None and not callable(self.default):
            value = self.default
            self.default = lambda model: value

    ############################################################################
    #
    # Complete field setup: everything else
    #

    def prepare_setup(self) -> None:
        self._setup_done = False

    def setup(self, model: BaseModel) -> None:
        """Perform the complete setup of a field."""
        if not self._setup_done:
            # validate field params
            for key in self._extra_keys__:
                if not model._valid_field_parameter(self, key):
                    _logger.warning(
                        "Field %s: unknown parameter %r, if this is an actual"
                        " parameter you may want to override the method"
                        " _valid_field_parameter on the relevant model in order to"
                        " allow it",
                        self,
                        key,
                    )
            if self.related:
                self.setup_related(model)
            else:
                self.setup_nonrelated(model)

            if not isinstance(self.required, bool):
                warnings.warn(
                    f"Property {self}.required should be a boolean ({self.required}).",
                    stacklevel=1,
                )

            if not isinstance(self.readonly, bool):
                warnings.warn(
                    f"Property {self}.readonly should be a boolean ({self.readonly}).",
                    stacklevel=1,
                )

            self._setup_done = True
            # column_type might be changed during Field.setup
            reset_cached_properties(self)

    #
    # Setup of non-related fields
    #

    def setup_nonrelated(self, model: BaseModel) -> None:
        """Determine the dependencies and inverse field(s) of ``self``."""
        pass

    def get_depends(self, model: BaseModel) -> tuple[Iterable[str], Iterable[str]]:
        """Return the field's dependencies and cache dependencies."""
        if self._depends is not None:
            # the parameter 'depends' has priority over 'depends' on compute
            return self._depends, self._depends_context or ()

        if self.related:
            if self._depends_context is not None:
                depends_context = self._depends_context
            else:
                depends_context = []
                field_model_name = model._name
                for field_name in self.related.split("."):
                    field_model = model.env[field_model_name]
                    field = field_model._fields[field_name]
                    depends_context.extend(field.get_depends(field_model)[1])
                    field_model_name = field.comodel_name
                depends_context = tuple(unique(depends_context))
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
            deps = getattr(func, "_depends", ())
            depends.extend(deps(model) if callable(deps) else deps)
            depends_context.extend(getattr(func, "_depends_context", ()))

        return depends, depends_context

    #
    # Setup of related fields
    #

    def setup_related(self, model: BaseModel) -> None:
        """Setup the attributes of a related field."""
        assert isinstance(self.related, str), self.related

        # determine the chain of fields, and make sure they are all set up
        field_seq = []
        model_name = self.model_name
        for name in self.related.split("."):
            field = model.pool[model_name]._fields.get(name)
            if field is None:
                raise KeyError(
                    f"Field {name} referenced in related field definition {self} does not exist."
                )
            if not field._setup_done:
                field.setup(model.env[model_name])
            field_seq.append(field)
            model_name = field.comodel_name

        # check type consistency
        if self.type != field.type:
            raise TypeError(
                f"Type of related field {self} is inconsistent with {field}"
            )

        self.related_field = field

        # if field's setup is invalidated, then self's setup must be invalidated, too
        model.pool.field_setup_dependents.add(field, self)

        # determine dependencies, compute, inverse, and search
        self.compute = self._compute_related
        if self.inherited or not (self.readonly or field.readonly):
            self.inverse = self._inverse_related
        if not self.store and all(f._description_searchable for f in field_seq):
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
            if attr not in self.__dict__ and prop.startswith("_related_"):
                setattr(self, attr, getattr(field, prop))

        for attr in field._extra_keys__:
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
            delegate_field = model._fields[self.related.split(".")[0]]
            self._modules = tuple(
                {*self._modules, *delegate_field._modules, *field._modules}
            )

    def traverse_related(self, record: BaseModel) -> tuple[BaseModel, Field]:
        """Traverse the fields of the related field `self` except for the last
        one, and return it as a pair `(last_record, last_field)`."""
        for name in self.related.split(".")[:-1]:
            # take the first record when traversing
            corecord = record[name]
            record = next(iter(corecord), corecord)
        return record, self.related_field

    def _compute_related(self, records: BaseModel) -> None:
        """Compute the related field ``self`` on ``records``."""
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
        for name in self.related.split(".")[:-1]:
            try:
                values = [next(iter(val := value[name]), val) for value in values]
            except AccessError as e:
                description = records.env["ir.model"]._get(records._name).name
                env = records.env
                raise AccessError(
                    env._(
                        "%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).",
                        previous_message=e.args[0],
                        document_kind=description,
                        document_model=records._name,
                    )
                )
        # assign final values to records
        for record, value in zip(records, values, strict=False):
            record[self.name] = self._process_related(
                value[self.related_field.name], record.env
            )

    def _process_related(self, value, env: Environment) -> typing.Any:
        """No transformation by default, but allows override."""
        return value

    def _inverse_related(self, records: BaseModel) -> None:
        """Inverse the related field ``self`` on ``records``."""
        # store record values, otherwise they may be lost by cache invalidation!
        record_value = {record: record[self.name] for record in records}
        for record in records:
            target, field = self.traverse_related(record)
            # update 'target' only if 'record' and 'target' are both real or
            # both new (see `test_base_objects.py`, `test_basic`)
            if target and bool(target.id) == bool(record.id):
                target[field.name] = record_value[record]

    def _search_related(self, records: BaseModel, operator: str, value) -> DomainType:
        """Determine the domain to search on field ``self``."""

        # Compute the new domain for ('x.y.z', op, value)
        # as ('x', 'any', [('y', 'any', [('z', op, value)])])
        # If the followed relation is a nullable many2one, we accept null
        # for that path as well.

        # determine whether the related field can be null
        falsy_value = self.falsy_value
        if isinstance(value, COLLECTION_TYPES):
            value_is_null = any(
                val is False or val is None or val == falsy_value for val in value
            )
        else:
            value_is_null = value is False or value is None or value == falsy_value
        can_be_null = (  # (..., '=', False) or (..., 'not in', [truthy vals])
            operator not in Domain.NEGATIVE_OPERATORS
        ) == value_is_null
        if operator in Domain.NEGATIVE_OPERATORS and not value_is_null:
            # we have a condition like 'not in' ['a']
            # let's call back with a positive operator
            return NotImplemented

        # parse the path
        field_seq = []
        model_name = self.model_name
        for fname in self.related.split("."):
            field = records.env[model_name]._fields[fname]
            field_seq.append(field)
            model_name = field.comodel_name

        # build the domain backwards with the any operator
        domain = Domain(field_seq[-1].name, operator, value)
        for field in reversed(field_seq[:-1]):
            domain = Domain(field.name, "any!" if self.compute_sudo else "any", domain)
            if can_be_null and field.type == "many2one" and not field.required:
                domain |= Domain(field.name, "=", False)
        return domain

    # properties used by setup_related() to copy values from related field
    _related_comodel_name = property(attrgetter("comodel_name"))
    _related_string = property(attrgetter("string"))
    _related_help = property(attrgetter("help"))
    _related_groups = property(attrgetter("groups"))
    _related_aggregator = property(attrgetter("aggregator"))

    @functools.cached_property
    def column_type(self) -> tuple[str, str] | None:
        """Return the actual column type for this field, if stored as a column."""
        return (
            ("jsonb", "jsonb")
            if self.company_dependent or self.translate
            else self._column_type
        )

    @functools.cached_property
    def is_column(self) -> bool:
        """Return whether this field is stored as a database column."""
        return bool(self.store and self.column_type)

    @functools.cached_property
    def is_stored_computed(self) -> bool:
        """Return whether this field is computed and stored in the database."""
        return bool(self.compute and self.store)

    @functools.cached_property
    def spec(self):
        """Return an immutable :class:`FieldSpec` snapshot of this field's metadata.

        The spec captures the field's *definition* (type, constraints,
        dependencies) without any runtime behavior.  Useful for static
        analysis, validation, and testing.
        """
        from ..components.field_spec import FieldSpec

        return FieldSpec(
            name=self.name,
            type=self.type,
            model_name=self.model_name,
            store=self.store,
            column_type=self.column_type,
            index=self.index,
            company_dependent=self.company_dependent,
            translate=self.translate,
            compute=self.compute,
            depends=tuple(self._depends or ()),
            depends_context=tuple(getattr(self, "_depends_context", ())),
            inverse=self.inverse,
            precompute=self.precompute,
            compute_sudo=self.compute_sudo if self.compute else None,
            recursive=self.recursive,
            related=self.related,
            required=self.required,
            readonly=self.readonly,
            copy=self.copy,
            groups=self.groups,
            string=self.string or "",
            help=self.help or "",
            aggregator=self.aggregator,
            comodel_name=getattr(self, "comodel_name", None),
            relation=getattr(self, "relation", None),
            ondelete=getattr(self, "ondelete", None),
            has_default=self.default is not None,
        )

    @property
    def base_field(self) -> Self:
        """Return the base field of an inherited field, or ``self``."""
        return self.inherited_field.base_field if self.inherited_field else self

    #
    # Company-dependent fields
    #

    def get_company_dependent_fallback(self, records: BaseModel) -> typing.Any:
        assert self.company_dependent
        fallback = (
            records.env["ir.default"]
            .with_user(SUPERUSER_ID)
            .with_company(records.env.company)
            ._get_model_defaults(records._name)
            .get(self.name)
        )
        fallback = self.convert_to_cache(fallback, records, validate=False)
        return self.convert_to_record(fallback, records)

    #
    # Setup of field triggers
    #

    def resolve_depends(self, registry: Registry) -> Iterator[tuple[Field, ...]]:
        """Return the dependencies of `self` as a collection of field tuples."""
        Model0 = registry[self.model_name]

        for dotnames in registry.field_depends[self]:
            field_seq: list[Field] = []
            model_name = self.model_name
            check_precompute = self.precompute

            for index, fname in enumerate(dotnames.split(".")):
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
                    ) from None
                if field is self and index and not self.recursive:
                    self.recursive = True
                    warnings.warn(
                        f"Field {self} should be declared with recursive=True",
                        stacklevel=1,
                    )

                # precomputed fields can depend on non-precomputed ones, as long
                # as they are reachable through at least one many2one field
                if (
                    check_precompute
                    and field.store
                    and field.compute
                    and not field.precompute
                ):
                    warnings.warn(
                        f"Field {self} cannot be precomputed as it depends on non-precomputed field {field}",
                        stacklevel=1,
                    )
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

                if field.type == "one2many":
                    for inv_field in Model.pool.field_inverses[field]:
                        yield tuple(field_seq) + (inv_field,)

                if check_precompute and field.type == "many2one":
                    check_precompute = False

                model_name = field.comodel_name

    ############################################################################
    #
    # Field description
    #

    def get_description(
        self, env: Environment, attributes: Collection[str] | None = None
    ) -> ValuesType:
        """Return a dictionary that describes the field ``self``."""
        desc = {}
        for attr, prop in self.description_attrs:
            if attributes is not None and attr not in attributes:
                continue
            if not prop.startswith("_description_"):
                continue
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value is not None:
                desc[attr] = value

        return desc

    # properties used by get_description()
    _description_name = property(attrgetter("name"))
    _description_type = property(attrgetter("type"))
    _description_store = property(attrgetter("store"))
    _description_manual = property(attrgetter("manual"))
    _description_related = property(attrgetter("related"))
    _description_company_dependent = property(attrgetter("company_dependent"))
    _description_readonly = property(attrgetter("readonly"))
    _description_required = property(attrgetter("required"))
    _description_groups = property(attrgetter("groups"))
    _description_change_default = property(attrgetter("change_default"))
    _description_default_export_compatible = property(
        attrgetter("default_export_compatible")
    )
    _description_exportable = property(attrgetter("exportable"))

    def _description_depends(self, env: Environment):
        return env.registry.field_depends[self]

    @property
    def _description_searchable(self) -> bool:
        return bool(self.store or self.search)

    def _description_sortable(self, env: Environment):
        if self.is_column:  # shortcut
            return True
        if self.inherited_field and self.inherited_field._description_sortable(env):
            # avoid compuation for inherited field
            return True

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        try:
            model._order_field_to_sql(
                model._table, self.name, SQL.EMPTY, SQL.EMPTY, query
            )
            return True
        except ValueError, AccessError:
            return False

    def _description_groupable(self, env: Environment):
        if self.is_column:  # shortcut
            return True
        if self.inherited_field and self.inherited_field._description_groupable(env):
            # avoid compuation for inherited field
            return True

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        groupby = (
            self.name if self.type not in ("date", "datetime") else f"{self.name}:month"
        )
        try:
            model._read_group_groupby(model._table, groupby, query)
            return True
        except ValueError, AccessError:
            return False

    def _description_aggregator(self, env: Environment):
        if not self.aggregator or self.is_column:  # shortcut
            return self.aggregator
        if self.inherited_field and self.inherited_field._description_aggregator(env):
            # avoid compuation for inherited field
            return self.inherited_field.aggregator

        model = env[self.model_name]
        query = model._as_query(ordered=False)
        try:
            model._read_group_select(f"{self.name}:{self.aggregator}", query)
            return self.aggregator
        except ValueError, AccessError:
            return None

    def _description_string(self, env: Environment) -> str:
        if self.string and env.lang:
            model_name = self.base_field.model_name
            field_string = env["ir.model.fields"].get_field_string(model_name)
            return field_string.get(self.name) or self.string
        return self.string

    def _description_help(self, env: Environment):
        if self.help and env.lang:
            model_name = self.base_field.model_name
            field_help = env["ir.model.fields"].get_field_help(model_name)
            return field_help.get(self.name) or self.help
        return self.help

    def _description_falsy_value_label(self, env) -> str | None:
        return (
            env._(self.falsy_value_label)
            if self.falsy_value_label
            else None  # pylint: disable=gettext-variable,E8502
        )

    def is_editable(self) -> bool:
        """Return whether the field can be editable in a view."""
        return not self.readonly

    ############################################################################
    #
    # Conversion of values
    #
    # The ORM maintains several value formats.  Each conversion method bridges
    # two adjacent formats.  The canonical data flows are:
    #
    #   WRITE (user/API → cache):
    #     write_value ──convert_to_cache──> cache_value
    #
    #   FLUSH (cache → database UPDATE):
    #     cache_value ──get_column_update──> SQL param
    #       (internally reads from cache_store, then calls
    #        convert_to_column; handles translated/company-dependent JSONB)
    #
    #   CREATE (user/API → database INSERT, bypasses cache):
    #     write_value ──convert_to_column_insert──> SQL param
    #       (delegates to convert_to_column, then wraps for JSONB if needed)
    #
    #   READ (database → cache → Python):
    #     SQL row ──(raw setdefault into cache)──> cache_value
    #     cache_value ──convert_to_record──> record_value  (what record.field returns)
    #
    #   EXPORT (Python → web client / RPC):
    #     record_value ──convert_to_read──> read_value  (dicts with display_name for m2o)
    #
    #   ROUNDTRIP (for __set__ on real records):
    #     any_value ──convert_to_write──> write_value
    #       (chains: convert_to_cache → convert_to_record → convert_to_read)
    #

    def convert_to_column(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        """Convert ``value`` from the write format to a SQL parameter for
        UPDATE conditions and column comparisons.

        This is the base scalar conversion.  For INSERT, use
        :meth:`convert_to_column_insert` (adds translated/company-dependent
        JSONB wrapping).  For flushing dirty cache, :meth:`get_column_update`
        reads from cache and delegates here.
        """
        if value is None or value is False:
            return None
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode()
        else:
            return str(value)

    @staticmethod
    def _to_json_value(value):
        """Convert a column value to a JSON-safe type for JSONB storage."""
        if isinstance(value, datetime):
            return value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if isinstance(value, date):
            return value.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return value

    def convert_to_column_insert(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        """Convert ``value`` from the write format to a SQL parameter for
        INSERT/COPY queries.  Delegates to :meth:`convert_to_column` for the
        scalar conversion, then wraps in JSONB for translated or
        company-dependent fields.

        Used by :meth:`~odoo.orm.models.mixins.crud.CrudMixin._create`.
        """
        value = self.convert_to_column(value, record, values, validate)
        if self.translate:
            if value is None:
                return None
            return PsycopgJson({"en_US": value, record.env.lang or "en_US": value})
        if not self.company_dependent:
            return value
        fallback = (
            record.env["ir.default"]._get_model_defaults(record._name).get(self.name)
        )
        if value == self.convert_to_column(fallback, record):
            return None
        return PsycopgJson({record.env.company.id: self._to_json_value(value)})

    def get_column_update(self, record: BaseModel):
        """Read the dirty value of ``record`` from cache and return it as a
        SQL parameter for UPDATE queries.  This is the cache → SQL path used
        by :meth:`~odoo.orm.models.mixins.cache.CacheMixin._flush`.

        For most fields: reads ``cache_store.get_field_data(self)[record.id]``
        and delegates to :meth:`convert_to_column`.  Translated and
        company-dependent fields assemble JSONB directly.
        """
        record_id = record.id
        field_cache = record.env._core.field_data(self)
        if self.translate is True:
            # Model translation: reconstruct {lang: value} from per-lang sub-dicts
            # (mirrors the company_dependent pattern below).
            langs_dict = {}
            for cache_key, sub_cache in field_cache.items():
                if not isinstance(sub_cache, dict):
                    continue  # skip stale flat entries from before field_depends_context setup
                if (value := sub_cache.get(record_id, SENTINEL)) is not SENTINEL:
                    lang = cache_key[0]
                    if value is not None:
                        langs_dict[lang] = value
            return PsycopgJson(langs_dict) if langs_dict else None
        if self.translate:
            # callable translate: single flat dict {id: {lang: value}}
            value = field_cache[record_id]
            return PsycopgJson(value) if value else None
        if not self.company_dependent:
            if self not in record.env._field_depends_context:
                # Fast path: direct cache read + column conversion (most fields)
                value = field_cache[record_id]
                if value is PENDING:
                    return PENDING
                return self.convert_to_column(value, record, validate=False)
            # Context-dependent: find first available value across contexts
            for cache in field_cache.values():
                if (value := cache.get(record_id, SENTINEL)) is not SENTINEL:
                    if value is PENDING:
                        return PENDING
                    return self.convert_to_column(value, record, validate=False)
            raise AssertionError(
                f"Value not in cache for field {self} and id={record_id}"
            )
        # Company-dependent: collect values from all company contexts into JSONB
        values = {}
        for ctx_key, cache in field_cache.items():
            if (
                value := cache.get(record_id, SENTINEL)
            ) is not SENTINEL and value is not PENDING:
                values[ctx_key[0]] = self._to_json_value(
                    self.convert_to_column(value, record)
                )
        return PsycopgJson(values) if values else None

    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        """Convert ``value`` to the cache format.  This is the entry point of
        the WRITE path: values from :meth:`BaseModel.write`,
        :meth:`BaseModel.create`, or direct assignment pass through here
        before being stored in the field cache (``cache_store``).

        If the value represents a recordset, it should be added for
        prefetching on ``record``.

        :param value: a value in write format (from user/API)
        :param record: target recordset (used for env, validation context)
        :param bool validate: when True, field-specific validation of
            ``value`` will be performed
        """
        return value

    def convert_to_record(self, value, record: BaseModel) -> T:
        """Convert ``value`` from the cache format to the record format — the
        Python value returned by ``record.field``.  This is the READ path
        exit point, called by :meth:`__get__`.

        If the value represents a recordset, it should share the prefetching
        of ``record``.
        """
        return False if value is None else value

    def convert_to_read(
        self, value, record: BaseModel, use_display_name: bool = True
    ) -> typing.Any:
        """Convert ``value`` from the record format to the EXPORT format
        returned by :meth:`BaseModel.read` and consumed by the web client.
        For relational fields this adds ``display_name``; for others it is
        typically an identity.

        :param value: a value in record format (from :meth:`convert_to_record`)
        :param record: source recordset
        :param bool use_display_name: when True, the value's display name will
            be computed using ``display_name``, if relevant for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, record: BaseModel) -> typing.Any:
        """Convert ``value`` from any format to the write format accepted by
        :meth:`BaseModel.write`.  Used by :meth:`__set__` on real records to
        roundtrip a value through the conversion pipeline before delegating
        to ``records.write()``.

        Default implementation chains: cache → record → read.
        """
        cache_value = self.convert_to_cache(value, record, validate=False)
        record_value = self.convert_to_record(cache_value, record)
        return self.convert_to_read(record_value, record)

    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        """Convert ``value`` from the record format to the export format."""
        if not value:
            return ""
        return value

    def convert_to_display_name(
        self, value, record: BaseModel
    ) -> str | typing.Literal[False]:
        """Convert ``value`` from the record format to a suitable display name."""
        return str(value) if value else False

    ############################################################################
    #
    # Update database schema
    #

    @property
    def column_order(self) -> int:
        """Prescribed column order in table."""
        return (
            0
            if self.column_type is None
            else sql.SQL_ORDER_BY_TYPE[self.column_type[0]]
        )

    def update_db(
        self, model: BaseModel, columns: dict[str, dict[str, typing.Any]]
    ) -> bool:
        """Update the database schema to implement this field.

        :param model: an instance of the field's model
        :param columns: a dict mapping column names to their configuration in database
        :return: ``True`` if the field must be recomputed on existing rows
        """
        if not self.column_type:
            return False

        column = columns.get(self.name)

        # create/update the column, not null constraint; the index will be
        # managed by registry.check_indexes()
        self.update_db_column(model, column)
        self.update_db_notnull(model, column)

        # optimization for computing simple related fields like 'foo_id.bar'
        if (
            not column
            and self.related
            and self.related.count(".") == 1
            and self.related_field.store
            and not self.related_field.compute
            and not (
                self.related_field.type == "binary" and self.related_field.attachment
            )
            and self.related_field.type not in ("one2many", "many2many")
        ):
            join_field = model._fields[self.related.split(".")[0]]
            if (
                join_field.type == "many2one"
                and join_field.store
                and not join_field.compute
            ):
                model.pool.post_init(self.update_db_related, model)
                # discard the "classical" computation
                return False

        return not column

    def update_db_column(self, model: BaseModel, column: dict[str, typing.Any]) -> None:
        """Create/update the column corresponding to ``self``.

        :param model: an instance of the field's model
        :param column: the column's configuration (dict) if it exists, or ``None``
        """
        if not column:
            # the column does not exist, create it
            sql.create_column(
                model.env.cr,
                model._table,
                self.name,
                self.column_type[1],
                self.string,
            )
            return
        if column["udt_name"] == self.column_type[0]:
            return
        self._convert_db_column(model, column)

    def _convert_db_column(self, model: BaseModel, column: dict[str, typing.Any]):
        """Convert the given database column to the type of the field."""
        sql.convert_column(model.env.cr, model._table, self.name, self.column_type[1])

    def update_db_notnull(
        self, model: BaseModel, column: dict[str, typing.Any]
    ) -> None:
        """Add or remove the NOT NULL constraint on ``self``.

        :param model: an instance of the field's model
        :param column: the column's configuration (dict) if it exists, or ``None``
        """
        has_notnull = column and column["is_nullable"] == "NO"

        if not column or (self.required and not has_notnull):
            # the column is new or it becomes required; initialize its values
            if model._table_has_rows():
                model._init_column(self.name)

        if self.required and not has_notnull:
            # _init_column may delay computations in post-init phase
            @model.pool.post_init
            def add_not_null():
                # At the time this function is called, the model's _fields may have been reset, although
                # the model's class is still the same. Retrieve the field to see whether the NOT NULL
                # constraint still applies.
                field = model._fields[self.name]
                if not field.required or not field.store:
                    return
                if field.compute:
                    records = model.browse(
                        id_
                        for (id_,) in model.env.execute_query(
                            SQL(
                                "SELECT id FROM %s AS t WHERE %s IS NULL",
                                SQL.identifier(model._table),
                                model._field_to_sql("t", field.name),
                            )
                        )
                    )
                    model.env.add_to_compute(field, records)
                # Flush values before adding NOT NULL constraint.
                model.flush_model([field.name])

                # Compute a SQL DEFAULT for required fields with static defaults.
                # This protects against NOT NULL violations when the module that
                # added the field is later not loaded: the ORM won't include the
                # field in INSERT, but the column retains NOT NULL.
                sql_default = None
                if (
                    field.default
                    and not field.translate
                    and not field.company_dependent
                ):
                    try:
                        value = field.default(model.browse())
                        if isinstance(value, (str, int, float, bool)):
                            sql_default = value
                    except Exception:
                        pass

                def apply_not_null(cr):
                    sql.set_not_null(cr, model._table, field.name)
                    if sql_default is not None:
                        sql.set_default(cr, model._table, field.name, sql_default)

                model.pool.post_constraint(
                    model.env.cr,
                    apply_not_null,
                    key=f"add_not_null:{model._table}:{field.name}",
                )

        elif not self.required and has_notnull:
            sql.drop_not_null(model.env.cr, model._table, self.name)

    def update_db_related(self, model: BaseModel) -> None:
        """Compute a stored related field directly in SQL."""
        comodel = model.env[self.related_field.model_name]
        join_field, comodel_field = self.related.split(".")
        model.env.cr.execute(
            SQL(
                """ UPDATE %(model_table)s AS x
                SET %(model_field)s = y.%(comodel_field)s
                FROM %(comodel_table)s AS y
                WHERE x.%(join_field)s = y.id """,
                model_table=SQL.identifier(model._table),
                model_field=SQL.identifier(self.name),
                comodel_table=SQL.identifier(comodel._table),
                comodel_field=SQL.identifier(comodel_field),
                join_field=SQL.identifier(join_field),
            )
        )

    ############################################################################
    #
    # SQL generation methods
    #

    def to_sql(self, model: BaseModel, alias: str) -> SQL:
        """Return an :class:`SQL` object that represents the value of the given
        field from the given table alias.

        The query object is necessary for fields that need to add tables to the query.
        """
        if not self.store or not self.column_type:
            raise ValueError(f"Cannot convert {self} to SQL because it is not stored")
        sql_field = SQL.identifier(alias, self.name, to_flush=self)
        if self.company_dependent:
            fallback = self.get_company_dependent_fallback(model)
            fallback = self.convert_to_column(
                self.convert_to_write(fallback, model), model
            )
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
            if self.type in ("boolean", "integer", "float", "monetary"):
                return SQL("(%s)::%s", sql_field, SQL(self._column_type[1]))
            # here the specified value for a company might be NULL e.g. '{"1": null}'::jsonb
            # the result of current sql_field might be 'null'::jsonb
            # ('null'::jsonb)::text == 'null'
            # ('null'::jsonb->>0)::text IS NULL
            return SQL("(%s->>0)::%s", sql_field, SQL(self._column_type[1]))

        return sql_field

    def property_to_sql(
        self,
        field_sql: SQL,
        property_name: str,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        """Return an :class:`SQL` object that represents the value of the given
        expression from the given table alias.

        The query object is necessary for fields that need to add tables to the query.
        """
        raise ValueError(f"Invalid field property {property_name!r} on {self}")

    def condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        """Return an :class:`SQL` object that represents the domain condition
        given by the triple ``(field_expr, operator, value)`` with the given
        table alias, and in the context of the given query.

        This method should use the model to resolve the SQL and check access
        of the field.
        """
        sql_expr = self._condition_to_sql(
            field_expr, operator, value, model, alias, query
        )
        if self.company_dependent:
            sql_expr = self._condition_to_sql_company(
                sql_expr, field_expr, operator, value, model, alias, query
            )
        return sql_expr

    def _condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        sql_field = model._field_to_sql(alias, field_expr, query)

        if field_expr == self.name:

            def _value_to_column(v):
                return self.convert_to_column(v, model, validate=False)

        else:
            # reading a property, keep value as-is
            def _value_to_column(v):
                return v

        # support for SQL value
        if operator in SQL_OPERATORS and isinstance(value, SQL):
            warnings.warn(
                "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
                DeprecationWarning, stacklevel=2,
            )
            return SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], value)

        # nullability
        can_be_null = self not in model.env.registry.not_null_fields

        # operator: in (equality)
        if operator in ("in", "not in"):
            assert isinstance(
                value, COLLECTION_TYPES
            ), f"condition_to_sql() 'in' operator expects a collection, not a {value!r}"
            params = tuple(
                _value_to_column(v) for v in value if v is not False and v is not None
            )
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
                sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], params)

            if (operator == "in") == null_in_condition:
                # field in {val, False} => field IN vals OR field IS NULL
                # field not in {val} => field NOT IN vals OR field IS NULL
                if not can_be_null:
                    return sql or SQL("FALSE")
                sql_null = SQL("%s IS NULL", sql_field)
                return SQL("(%s OR %s)", sql, sql_null) if sql else sql_null

            elif operator == "not in" and null_in_condition and not sql:
                # if we have a base query, null values are already exluded
                return SQL("%s IS NOT NULL", sql_field) if can_be_null else SQL("TRUE")

            assert sql, f"Missing sql query for {operator} {value!r}"
            return sql

        # operator: like
        if operator.endswith("like"):
            # cast value to text for any like comparison
            sql_left = sql_field if self.is_text else SQL("%s::text", sql_field)

            # add wildcard and unaccent depending on the operator
            need_wildcard = "=" not in operator
            if need_wildcard:
                sql_value = SQL("%s", f"%{value}%")
            else:
                sql_value = SQL("%s", str(value))
            if operator.endswith("ilike"):
                sql_left = model.env.registry.unaccent(sql_left)
                sql_value = model.env.registry.unaccent(sql_value)

            sql = SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], sql_value)
            if operator in Domain.NEGATIVE_OPERATORS and can_be_null:
                sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
            return sql

        # operator: inequality
        if operator in (">", "<", ">=", "<="):
            accept_null_value = False
            if (null_value := self.falsy_value) is not None:
                value = self.convert_to_cache(value, model) or null_value
                accept_null_value = can_be_null and (
                    null_value < value
                    if operator == "<"
                    else (
                        null_value > value
                        if operator == ">"
                        else (
                            null_value <= value
                            if operator == "<="
                            else null_value >= value
                        )
                    )  # operator == '>='
                )
            sql_value = SQL("%s", _value_to_column(value))

            sql = SQL("%s%s%s", sql_field, SQL_OPERATORS[operator], sql_value)
            if accept_null_value:
                sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
            return sql

        # operator: any
        # Note: relational operators overwrite this function for a more specific
        # behaviour, here we check just the field against the subselect.
        # Example usage: ('id', 'any!', Query | SQL)
        if operator in ("any!", "not any!"):
            if isinstance(value, Query):
                subselect = value.subselect()
            elif isinstance(value, SQL):
                subselect = SQL("(%s)", value)
            else:
                raise TypeError(
                    f"condition_to_sql() operator 'any!' accepts SQL or Query, got {value}"
                )
            sql_operator = SQL_OPERATORS["in" if operator == "any!" else "not in"]
            return SQL("%s%s%s", sql_field, sql_operator, subselect)

        raise NotImplementedError(
            f"Invalid operator {operator!r} for SQL in domain term {(field_expr, operator, value)!r}"
        )

    def _condition_to_sql_company(
        self,
        sql_expr: SQL,
        field_expr: str,
        operator: str,
        value,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        """Add a not null condition on the field for company-dependent fields to use an existing index for better performance."""
        if (
            self.company_dependent
            and self.index == "btree_not_null"
            and not (
                self.type in ("datetime", "date") and field_expr != self.name
            )  # READ_GROUP_NUMBER_GRANULARITY is not supported
            and model.env["ir.default"]._evaluate_condition_with_fallback(
                model._name, field_expr, operator, value
            )
            is False
        ):
            return SQL(
                "(%s IS NOT NULL AND %s)",
                SQL.identifier(alias, self.name),
                sql_expr,
            )
        return sql_expr

    ############################################################################
    #
    # Expressions and filtering of records
    #

    def expression_getter(self, field_expr: str) -> Callable[[BaseModel], typing.Any]:
        """Given some field expression (what you find in domain conditions),
        return a function that returns the corresponding expression for a record::

            field = record._fields['create_date']
            get_value = field.expression_getter('create_date.month_number')
            month_number = get_value(record)
        """
        if field_expr == self.name:
            return self.__get__
        raise ValueError(f"Expression not supported on {self}: {field_expr!r}")

    def filter_function(
        self, records: M, field_expr: str, operator: str, value
    ) -> Callable[[M], M]:
        assert (
            operator not in Domain.NEGATIVE_OPERATORS
        ), "only positive operators are implemented"
        getter = self.expression_getter(field_expr)
        # assert not isinstance(value, (SQL, Query))

        # -------------------------------------------------
        # operator: in (equality)
        if operator == "in":
            assert (
                isinstance(value, COLLECTION_TYPES) and value
            ), f"filter_function() 'in' operator expects a collection, not a {type(value)}"
            if not isinstance(value, AbstractSet):
                value = set(value)
            if False in value or self.falsy_value in value:
                if len(value) == 1:
                    return lambda rec: not getter(rec)
                return lambda rec: (val := getter(rec)) in value or not val
            return lambda rec: getter(rec) in value

        # -------------------------------------------------
        # operator: like
        if operator.endswith("like"):
            # we may get a value which is not a string
            if operator.endswith("ilike"):
                # ilike uses unaccent and lower-case comparison
                unaccent_python = records.env.registry.unaccent_python

                def unaccent(x):
                    return unaccent_python(str(x).lower()) if x else ""

            else:

                def unaccent(x):
                    return str(x) if x else ""

            # build a regex that matches the SQL-like expression
            # note that '\' is used for escaping in SQL
            def build_like_regex(value: str, exact: bool):
                yield "^" if exact else ".*"
                escaped = False
                for char in value:
                    if escaped:
                        escaped = False
                        yield re.escape(char)
                    elif char == "\\":
                        escaped = True
                    elif char == "%":
                        yield ".*"
                    elif char == "_":
                        yield "."
                    else:
                        yield re.escape(char)
                if exact:
                    yield "$"
                # no need to match r'.*' in else because we only use .match()

            like_regex = re.compile(
                "".join(build_like_regex(unaccent(value), "=" in operator)),
                flags=re.DOTALL,
            )
            return lambda rec: like_regex.match(unaccent(getter(rec)))

        # -------------------------------------------------
        # operator: inequality
        if pyop := PYTHON_INEQUALITY_OPERATOR.get(operator):
            can_be_null = False
            if (null_value := self.falsy_value) is not None:
                value = value or null_value
                can_be_null = (
                    null_value < value
                    if operator == "<"
                    else (
                        null_value > value
                        if operator == ">"
                        else (
                            null_value <= value
                            if operator == "<="
                            else null_value >= value
                        )
                    )  # operator == '>='
                )

            def check_inequality(rec):
                rec_value = getter(rec)
                try:
                    if rec_value is False or rec_value is None:
                        return can_be_null
                    return pyop(rec_value, value)
                except ValueError, TypeError:
                    # ignoring error, type mismatch
                    return False

            return check_inequality

        # -------------------------------------------------
        raise NotImplementedError(f"Invalid simple operator {operator!r}")

    ############################################################################
    #
    # Alternatively stored fields: if fields don't have a `column_type` (not
    # stored as regular db columns) they go through a read/create/write
    # protocol instead
    #

    def read(self, records: BaseModel) -> None:
        """Read the value of ``self`` on ``records``, and store it in cache."""
        if not self.column_type:
            raise NotImplementedError(f"Method read() undefined on {self}")

    def create(self, record_values: Collection[tuple[BaseModel, typing.Any]]) -> None:
        """Write the value of ``self`` on the given records, which have just
        been created.

        :param record_values: a list of pairs ``(record, value)``, where
            ``value`` is in the format of method :meth:`BaseModel.write`
        """
        for record, value in record_values:
            self.mark_dirty(record, value)

    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        """Apply a write value for ``self`` on ``records``.  For stored scalar
        fields this converts the value, updates the cache, and marks it dirty
        (actual SQL happens at flush time).  Relational and attachment field
        overrides may execute immediate database operations.

        This is the field-level counterpart of :meth:`BaseModel.write`.

        :param records: recordset to update
        :param value: a value in any format
        """
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # discard the records that are not modified
        cache_value = self.convert_to_cache(value, records)
        records = self._filter_not_equal(records, cache_value)
        if not records:
            return

        # update the cache
        self._update_cache(records, cache_value, dirty=True)

    ############################################################################
    #
    # Cache management methods
    #

    def _get_cache(self, env: Environment) -> MutableMapping[IdType, typing.Any]:
        """Return the field's cache, i.e., a mutable mapping from record id to
        a cache value.  The cache may be environment-specific.  This mapping is
        the way to retrieve a field's value for a given record.

        Calling this function multiple times, always returns the same mapping
        instance for a given environment, unless the transaction was entirely
        invalidated.
        """
        field_cache = env._field_cache_memo.get(self)
        if field_cache is not None:
            return field_cache
        field_cache = self._get_cache_impl(env)
        env._field_cache_memo[self] = field_cache
        return field_cache

    def _get_cache_impl(self, env: Environment) -> MutableMapping[IdType, typing.Any]:
        """Implementation of :meth:`_get_cache`.  This method may provide a
        view to the actual cache, depending on the needs of the field.
        """
        cache = env._core.field_data(self)
        if self in env._field_depends_context:
            cache = cache.setdefault(env.cache_key(self), {})
        return cache

    def _invalidate_cache(
        self, env: Environment, ids: Collection[IdType] | None = None
    ) -> None:
        """Invalidate the field's cache for the given ids, or all record ids if ``None``."""
        cache = env._core.field_data_or_none(self)
        if not cache:
            return

        if self in env._field_depends_context:
            # During module setup, field_data may contain both per-context
            # sub-dicts (tuple keys → dict values) AND stale flat entries
            # (id keys → scalar values) from before field_depends_context
            # was populated.  Only iterate actual sub-dicts.
            caches = [v for v in cache.values() if isinstance(v, dict)]
        else:
            caches = [cache]
        for field_cache in caches:
            if ids is None:
                field_cache.clear()
                continue
            for id_ in ids:
                field_cache.pop(id_, None)

    def _get_all_cache_ids(self, env: Environment) -> Collection[IdType]:
        """Return all the record ids that have a value in cache in any environment."""
        cache = env._core.field_data(self)
        if self in env._field_depends_context:
            # trick to cheaply "merge" the keys of the environment-specific dicts
            subs = [v for v in cache.values() if isinstance(v, dict)]
            return collections.ChainMap(*subs) if subs else {}
        return cache

    def _cache_missing_ids(self, records: BaseModel) -> Iterator[IdType]:
        """Generator of ids that have no value in cache.

        Records with :data:`PENDING` (stored computed fields awaiting
        recomputation) are treated as missing.
        """
        field_cache = self._get_cache(records.env)
        _pending = PENDING
        return (
            id_
            for id_ in records._ids
            if id_ not in field_cache or field_cache.get(id_) is _pending
        )

    def _filter_not_equal(
        self, records: ModelType, cache_value: typing.Any
    ) -> ModelType:
        """Return the subset of ``records`` for which the value of ``self`` is
        either not in cache, or different from ``cache_value``.
        """
        field_cache = self._get_cache(records.env)
        # Fast path for singletons (the common case from write): avoid
        # browse() allocation when the value changed or is not cached.
        ids = records._ids
        if len(ids) == 1:
            if field_cache.get(ids[0], SENTINEL) != cache_value:
                return records
            return records.browse()
        return records.browse(
            record_id
            for record_id in ids
            if field_cache.get(record_id, SENTINEL) != cache_value
        )

    def _to_prefetch(self, record: ModelType) -> ModelType:
        """Return a recordset including ``record`` to prefetch the field."""
        field_cache = self._get_cache(record.env)
        prefetch_ids = record._prefetch_ids
        record_id = record.id
        # Rust fast path: real records with tuple prefetch IDs and dict cache (~3-5x faster).
        # LangProxyDict (callable-translate fields) and PrefetchX2many fall back to Python.
        if (
            _to_prefetch_ids_rust is not None
            and isinstance(prefetch_ids, tuple)
            and type(field_cache) is dict
        ):
            result = _to_prefetch_ids_rust(
                record_id, prefetch_ids, field_cache, PREFETCH_MAX
            )
            if result is not None:
                return record.browse(result)
        # Python fallback: NewId records or non-tuple prefetch IDs
        kind = bool(record_id)
        result = [record_id]
        # Skip IDs already in field_cache (O(1) dict lookup) instead of
        # building O(n) set from all cache keys.  Track added IDs in a
        # small set to avoid duplicates from prefetch_ids.
        added = {record_id}
        for id_ in prefetch_ids:
            if len(result) >= PREFETCH_MAX:
                break
            if id_ not in field_cache and id_ not in added and bool(id_) == kind:
                result.append(id_)
                added.add(id_)
        return record.browse(result)

    def _insert_cache(self, records: BaseModel, values: Iterable) -> None:
        """Update the cache of the given records with the corresponding values,
        ignoring the records that don't have a value in cache already.  This
        enables to keep the pending updates of records, and flush them later.
        """
        field_cache = self._get_cache(records.env)
        # call setdefault for all ids, values (looping in C)
        # this is ~15% faster than the equivalent:
        # ```
        # for record, value in zip(records._ids, values):
        #   field_cache.setdefault(record, value)
        # ```
        collections.deque(map(field_cache.setdefault, records._ids, values, strict=False), maxlen=0)

    def _update_cache(
        self, records: BaseModel, cache_value: typing.Any, dirty: bool = False
    ) -> None:
        """Update the value in the cache for the given records, and optionally
        make the field dirty for those records (for stored column fields only).

        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        logs an error.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        """
        env = records.env
        field_cache = self._get_cache(env)
        ids = records._ids
        if len(ids) <= 1:
            # fast path for singleton (most common) and empty recordsets
            if ids:
                field_cache[ids[0]] = cache_value
        else:
            # batch update: push the loop into C via dict.fromkeys
            field_cache.update(dict.fromkeys(ids, cache_value))

        # dirty only makes sense for stored column fields
        if self.is_column:
            if dirty:
                env._core.mark_dirty(self, (id_ for id_ in records._ids if id_))
            else:
                dirty_ids = env._core.get_dirty(self)
                if dirty_ids and not dirty_ids.isdisjoint(records._ids):
                    _logger.error(
                        "Field._update_cache() updating the value on %s.%s where dirty flag is already set",
                        records,
                        self.name,
                        stack_info=True,
                    )

    ############################################################################
    #
    # Descriptor methods
    #

    def __get__(self, record: BaseModel, owner=None) -> T:
        """return the value of field ``self`` on ``record``"""
        if record is None:
            return self  # the field is accessed through the owner class

        env = record.env
        # Precondition 1: ACL check (see ensure_access()).
        # Inlined here for performance: most fields have groups=None, so
        # ``not self.groups`` short-circuits first, skipping env.su lookup.
        if not (not self.groups or env.su or record._has_field_access(self, "read")):
            record._check_field_access(self, "read")

        record_ids = record._ids
        if len(record_ids) != 1:
            if record_ids:
                # let ensure_one() raise the proper exception
                record.ensure_one()
                raise AssertionError("ensure_one() did not raise for multi-record")
            # null record -> return the null value for this field
            value = self.convert_to_cache(False, record, validate=False)
            return self.convert_to_record(value, record)

        # Precondition 2: ensure recomputation (see ensure_computed()).
        # Inlined: most fields are not stored-computed, so
        # is_stored_computed short-circuits immediately.
        if self.is_stored_computed and env._core.has_pending(self):
            self.recompute(record)

        record_id = record_ids[0]
        # Inline _get_cache memo: double dict subscription bypasses the
        # method dispatch + descriptor protocol overhead.
        try:
            field_cache = env.__dict__["_field_cache_memo"][self]
        except KeyError:
            field_cache = self._get_cache(env)
        try:
            value = field_cache[record_id]
        except KeyError:
            value = SENTINEL
        if value is not SENTINEL and value is not PENDING:
            try:
                # convert_to_record may raise KeyError for translation misses
                return self.convert_to_record(value, record)
            except KeyError:
                pass
        # Evict PENDING so downstream code (fetch, _cache_missing_ids,
        # _to_prefetch) sees a true cache miss, not a stale placeholder.
        if value is PENDING:
            field_cache.pop(record_id, None)
            # If the field is currently being computed (protected), return the
            # falsy default instead of triggering a DB fetch.  This matches the
            # pre-PENDING behavior where cache held None during _create(), and
            # avoids a wasted roundtrip for the NULL value.
            if env.is_protected(self, record):
                value = self.convert_to_cache(False, record, validate=False)
                self._update_cache(record, value)
                return self.convert_to_record(value, record)
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
        if self.store and record_id:
            # real record: fetch from database
            recs = self._to_prefetch(record)
            try:
                recs._fetch_field(self)
                fallback_single = False
            except AccessError:
                if len(recs) == 1:
                    raise
                fallback_single = True
            if fallback_single:
                record._fetch_field(self)
            value = field_cache.get(record_id, SENTINEL)
            if value is SENTINEL:
                raise MissingError(
                    "\n".join(
                        [
                            env._("Record does not exist or has been deleted."),
                            env._(
                                "(Record: %(record)s, User: %(user)s)",
                                record=record,
                                user=env.uid,
                            ),
                        ]
                    )
                ) from None

        elif self.store and record._origin and not (self.compute and self.readonly):
            # new record with origin: fetch from origin, and assign the
            # records to prefetch in cache (which is necessary for
            # relational fields to "map" prefetching ids to their value)
            recs = self._to_prefetch(record)
            try:
                for rec in recs:
                    if rec_origin := rec._origin:
                        value = self.convert_to_cache(
                            rec_origin[self.name], rec, validate=False
                        )
                        self._update_cache(rec, value)
                fallback_single = False
            except AccessError, KeyError, MissingError:
                if len(recs) == 1:
                    raise
                fallback_single = True
            if fallback_single:
                value = self.convert_to_cache(
                    record._origin[self.name], record, validate=False
                )
                self._update_cache(record, value)
            # get the final value (see patches in x2many fields)
            value = field_cache[record_id]

        elif self.compute:
            # non-stored field or new record without origin: compute
            if env.is_protected(self, record):
                value = self.convert_to_cache(False, record, validate=False)
                self._update_cache(record, value)
            else:
                recs = record if self.recursive else self._to_prefetch(record)
                try:
                    self.compute_value(recs)
                    fallback_single = False
                except AccessError, MissingError:
                    fallback_single = True
                if fallback_single:
                    self.compute_value(record)
                    recs = record

                missing_recs_ids = tuple(self._cache_missing_ids(recs))
                if missing_recs_ids:
                    missing_recs = record.browse(missing_recs_ids)
                    if self.readonly and not self.store:
                        raise ValueError(
                            f"Compute method failed to assign {missing_recs}.{self.name}"
                        )
                    # fallback to null value if compute gives nothing, do it for every unset record
                    false_value = self.convert_to_cache(False, record, validate=False)
                    self._update_cache(missing_recs, false_value)

                # cache could have been entirely invalidated by compute
                # as some compute methods call indirectly env.invalidate_all()
                field_cache = self._get_cache(env)
                value = field_cache[record_id]

        elif self.type == "many2one" and self.delegate and not record_id:
            # parent record of a new record: new record, with the same
            # values as record for the corresponding inherited fields
            def is_inherited_field(name):
                field = record._fields[name]
                return field.inherited and field.related.split(".")[0] == self.name

            parent = record.env[self.comodel_name].new(
                {
                    name: value
                    for name, value in record._cache.items()
                    if is_inherited_field(name)
                }
            )
            # in case the delegate field has inverse one2many fields, this
            # updates the inverse fields as well
            value = self.convert_to_cache(parent, record, validate=False)
            self._update_cache(record, value)
            # Set inverse fields on new records in the comodel.
            # This stays here (not in _update_cache) because inverse field
            # updates are specific to delegate field setup, not general
            # cache population.  Moving it would couple _update_cache with
            # relational inverse semantics.
            if inv_recs := parent.filtered(lambda r: not r.id):
                for invf in env.registry.field_inverses[self]:
                    invf._update_inverse(inv_recs, record)

        else:
            # non-stored field or stored field on new record: default value
            value = self.convert_to_cache(False, record, validate=False)
            self._update_cache(record, value)
            defaults = record.default_get([self.name])
            if self.name in defaults:
                # The null value above is necessary to convert x2many field
                # values. For instance, converting [(Command.LINK, id)]
                # accesses the field's current value, then adds the given
                # id. Without an initial value, the conversion ends up here
                # to determine the field's value, and generates an infinite
                # recursion.
                value = self.convert_to_cache(defaults[self.name], record)
                self._update_cache(record, value)
            # get the final value (see patches in x2many fields)
            value = field_cache[record_id]

        return self.convert_to_record(value, record)

    def __set__(self, records: BaseModel, value) -> None:
        """Set the value of field ``self`` on ``records``.

        Records are partitioned into three buckets, each with different
        semantics (see the ``_assign_*`` methods for details):

        - **Protected**: currently being computed — direct cache write, no
          business logic, no recomputation triggers.
        - **New**: unsaved records (``NewId``) — cache write with dependency
          tracking via ``modified()``, but no access checks or validation.
        - **Real**: saved records with a database id — full ``write()`` flow
          including access checks, audit, validation, and constraints.
        """
        record_ids = records._ids
        # Fast path: singleton record (the vast majority of __set__ calls
        # during compute methods).  Skips list creation, loop, partitioning,
        # function dispatch, and redundant recordset construction.
        core = records.env._core
        if len(record_ids) == 1:
            record_id = record_ids[0]
            if core.is_protected(self, record_id):
                self.mark_dirty(records, value)
                return
            if not record_id:
                self._assign_new(records, [record_id], value)
                return
            write_value = self.convert_to_write(value, records)
            records.write({self.name: write_value})
            return

        _protected_ids = core.protected_ids(self)
        protected_ids = []
        new_ids = []
        other_ids = []
        for record_id in record_ids:
            if record_id in _protected_ids:
                protected_ids.append(record_id)
            elif not record_id:
                new_ids.append(record_id)
            else:
                other_ids.append(record_id)

        if protected_ids:
            self._assign_protected(records, protected_ids, value)
        if new_ids:
            self._assign_new(records, new_ids, value)
        if other_ids:
            self._assign_real(records, other_ids, value)

    def _assign_protected(self, records: BaseModel, ids: list, value) -> None:
        """Assign ``value`` to protected records (currently being computed).

        Minimal path: directly updates the cache via :meth:`mark_dirty`.
        No access checks, no ``modified()`` triggers, no recomputation.
        This is used inside compute methods where the field is being set
        as part of its own computation.
        """
        protected_records = records.__class__(
            records.env, tuple(ids), records._prefetch_ids
        )
        self.mark_dirty(protected_records, value)

    def _assign_new(self, records: BaseModel, ids: list, value) -> None:
        """Assign ``value`` to new (unsaved) records.

        Updates the cache and triggers ``modified()`` for dependency tracking,
        so that computed fields depending on this one get recomputed.  No
        access checks or constraint validation — new records are typically
        being built in onchange handlers or ``new()`` calls where the full
        ``write()`` flow would be inappropriate.

        For inherited fields, also propagates the value to the parent record
        if the parent is itself new.
        """
        new_records = records.__class__(records.env, tuple(ids), records._prefetch_ids)
        with records.env.protecting(
            records.pool.field_computed.get(self, [self]), new_records
        ):
            if self.relational:
                new_records._modified_before([self.name])
            self.mark_dirty(new_records, value)
            new_records.modified([self.name])

        if self.inherited:
            # special case: also assign parent records if they are new
            parents = new_records[self.related.split(".")[0]]
            parents.filtered(lambda r: not r.id)[self.name] = value

    def _assign_real(self, records: BaseModel, ids: list, value) -> None:
        """Assign ``value`` to real (saved) records.

        Full ``write()`` path: the value is round-tripped through
        :meth:`convert_to_write` and then passed to :meth:`BaseModel.write`,
        which performs access checks, audit logging, constraint validation,
        and triggers recomputation.
        """
        records = records.__class__(records.env, tuple(ids), records._prefetch_ids)
        write_value = self.convert_to_write(value, records)
        records.write({self.name: write_value})

    ############################################################################
    #
    # Precondition API — explicit contracts for cache-bypass fast paths
    #
    # Code that reads the field cache without going through __get__ must call
    # these precondition methods first.  Together they form the documented
    # contract so that future optimizers (like _read_format) can bypass
    # __get__ safely without silently violating hidden invariants.
    #

    def ensure_access(self, record: BaseModel) -> None:
        """Check that the current user has read access to this field.

        Must be called before reading from the field cache when bypassing
        :meth:`__get__`.  No-op when ``env.su`` is True or the field has
        no ``groups`` restriction.
        """
        env = record.env
        if not (not self.groups or env.su or record._has_field_access(self, "read")):
            record._check_field_access(self, "read")

    def read_cache(self, record_id: int, env) -> tuple[bool, typing.Any]:
        """Read a single value from this field's cache.

        Returns ``(True, value)`` on cache hit, ``(False, SENTINEL)`` on miss.
        Treats :data:`PENDING` as a miss (stored computed field awaiting
        recomputation).

        Callers must ensure :meth:`ensure_computed` has been called first —
        this method does NOT trigger recomputation.
        """
        value = self._get_cache(env).get(record_id, SENTINEL)
        if value is SENTINEL or value is PENDING:
            return False, SENTINEL
        return True, value

    ############################################################################
    #
    # Computation of field values
    #

    def ensure_computed(self, records: BaseModel) -> None:
        """Ensure pending recomputations of ``self`` are processed.

        Must be called before reading from the field cache for stored computed
        fields.  This is automatically handled by :meth:`__get__`, but code
        that bypasses ``__get__`` (e.g. direct cache access in
        ``_read_format``) must call this explicitly.

        No-op when the field is not stored-computed or has no pending entries
        in ``compute_engine``.
        """
        if self.is_stored_computed and records.env._core.has_pending(self):
            self.recompute(records)

    def recompute(self, records: BaseModel) -> None:
        """Process the pending computations of ``self`` on ``records``. This
        should be called only if ``self`` is computed and stored.
        """
        to_compute_ids = records.env._core.pending_ids(self)
        if not to_compute_ids:
            return

        _debug = _orm_compute.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()
            _count = len(records)

        def apply_except_missing(func, records):
            """Apply `func` on `records`, with a fallback ignoring non-existent records."""
            try:
                func(records)
                return
            except MissingError:
                pass

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
            if _debug:
                _orm_compute.debug(
                    "[%.3f ms] recompute %s.%s: %d records (recursive=True)",
                    (time.perf_counter() - _t0) * 1000,
                    self.model_name,
                    self.name,
                    _count,
                )
            return

        for record in records:
            if record.id in to_compute_ids:
                ids = expand_ids(record.id, to_compute_ids)
                recs = record.browse(itertools.islice(ids, PREFETCH_MAX))
                try:
                    apply_except_missing(self.compute_value, recs)
                    continue
                except AccessError:
                    pass
                self.compute_value(record)

        if _debug:
            _orm_compute.debug(
                "[%.3f ms] recompute %s.%s: %d records (recursive=False)",
                (time.perf_counter() - _t0) * 1000,
                self.model_name,
                self.name,
                _count,
            )

    def compute_value(self, records: BaseModel) -> None:
        """Invoke the compute method on ``records``; the results are in cache."""
        _debug = _orm_compute.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

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

        if _debug:
            _orm_compute.debug(
                "[%.3f ms] compute_value %s.%s: %d records (sudo=%s)",
                (time.perf_counter() - _t0) * 1000,
                self.model_name,
                self.name,
                len(records),
                self.compute_sudo,
            )

    def determine_inverse(self, records: BaseModel) -> None:
        """Given the value of ``self`` on ``records``, inverse the computation."""
        _debug = _orm_compute.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

        determine(self.inverse, records)

        if _debug:
            _orm_compute.debug(
                "[%.3f ms] determine_inverse %s.%s: %d records",
                (time.perf_counter() - _t0) * 1000,
                self.model_name,
                self.name,
                len(records),
            )

    def determine_domain(self, records: BaseModel, operator: str, value) -> typing.Any:
        """Return a domain representing a condition on ``self``."""
        return determine(self.search, records, operator, value)

    def determine_group_expand(
        self, records: BaseModel, values: typing.Any, domain: DomainType
    ) -> typing.Any:
        """Return a domain representing a condition on ``self``."""
        return determine(self.group_expand, records, values, domain)


############################################################################
#
# Scalar __get__ factory
#


def _make_scalar_get(cache_to_record: Callable) -> Callable:
    """Generate a ``__get__`` override for scalar field types.

    The generated closure inlines all optimizations from :meth:`Field.__get__`:

    - ``not self.groups`` ACL short-circuit
    - C-level triple dict lookup via ``scalar_cache_get`` (bypasses bytecode
      dispatch for the memo→cache→id chain and the try/except KeyError block)
    - ``compute_engine.has_pending()`` guard before ``recompute()``
    - ``PENDING`` / ``SENTINEL`` awareness via identity comparison in Rust

    Each scalar subclass replaces its 18-line hand-written override with::

        __get__ = _make_scalar_get(lambda v: v or 0)

    :param cache_to_record: ``callable(cache_value) -> record_value``
        Converts a non-sentinel cache value to record format.
    """
    _PENDING = PENDING
    _SENTINEL = SENTINEL
    _base_get = Field.__get__
    _cache_get = _scalar_cache_get

    def __get__(self, record, owner=None):
        if record is None:
            return self
        env = record.env
        if not (not self.groups or env.su or record._has_field_access(self, "read")):
            record._check_field_access(self, "read")
        ids = record._ids
        if len(ids) != 1:
            return _base_get(self, record, owner)
        if self.is_stored_computed and env._core.has_pending(self):
            self.recompute(record)
        value = _cache_get(env.__dict__, self, ids[0], _PENDING, _SENTINEL)
        if value is not _SENTINEL:
            return cache_to_record(value)
        return _base_get(self, record, owner)

    return __get__


# forward-reference to models because we have this last cyclic dependency
# it is used in this file only for asserts
from .. import models as _models  # noqa: E402
