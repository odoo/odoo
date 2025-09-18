"""
BaseModel implementation - the core ORM class.

This module contains the main BaseModel class and the Model subclass.
All operational logic is in mixins (crud, query, read, lifecycle, etc.).
This file focuses on model identity, field/method discovery, and coordination.
"""

import collections
import functools
import logging
import time
import typing
from collections import defaultdict
from collections.abc import Iterable
from inspect import getmembers

from odoo.exceptions import UserError
from odoo.tools import SQL, OrderedSet, frozendict

from .. import decorators as api
from ..fields.base import Field, determine
from ..fields.misc import Id
from ..fields.textual import Char
from ..parsing import parse_field_expr

# Import from sibling modules in this package
from .metaclass import MetaModel

# Import ALL mixins from mixins/ subpackage (consolidated location)
from .mixins import (
    AccessMixin,
    CacheMixin,
    # Core operations
    CopyMixin,
    CrudMixin,
    EnvironmentMixin,
    IOMixin,
    IterationMixin,
    LifecycleMixin,
    ReadGroupMixin,
    # Data access
    ReadMixin,
    SchemaMixin,
    SearchMixin,
    # Features
    TranslationMixin,
    TraversalMixin,
)

if typing.TYPE_CHECKING:
    from types import MappingProxyType

    from ..runtime import Registry
    from .table_objects import TableObject


_logger = logging.getLogger("odoo.models")
_orm_crud = logging.getLogger("odoo.orm.crud")


class BaseModel(
    CrudMixin,
    CopyMixin,
    IterationMixin,
    TraversalMixin,
    CacheMixin,
    EnvironmentMixin,
    LifecycleMixin,
    ReadMixin,
    SearchMixin,
    ReadGroupMixin,
    TranslationMixin,
    SchemaMixin,
    IOMixin,
    AccessMixin,
    metaclass=MetaModel,
):
    """Base class for Odoo models.

    Odoo models are created by inheriting one of the following:

    *   :class:`Model` for regular database-persisted models

    *   :class:`TransientModel` for temporary data, stored in the database but
        automatically vacuumed every so often

    *   :class:`AbstractModel` for abstract super classes meant to be shared by
        multiple inheriting models

    The system automatically instantiates every model once per database. Those
    instances represent the available models on each database, and depend on
    which modules are installed on that database. The actual class of each
    instance is built from the Python classes that create and inherit from the
    corresponding model.

    Every model instance is a "recordset", i.e., an ordered collection of
    records of the model. Recordsets are returned by methods like
    :meth:`~.browse`, :meth:`~.search`, or field accesses. Records have no
    explicit representation: a record is represented as a recordset of one
    record.

    To create a class that should not be instantiated,
    the :attr:`~odoo.models.BaseModel._register` attribute may be set to False.
    """

    __slots__ = ["_ids", "_prefetch_ids", "env"]

    pool: Registry
    """The registry instance, set as a class attribute during model setup.

    ``self.pool`` and ``self.env.registry`` are the same object at runtime.
    Convention: use ``self.pool`` for registry *metadata* access (field_computed,
    field_inverses, field_triggers, etc.) and ``self.env.registry`` or
    ``self.env[model_name]`` for model class lookups.
    """

    _fields__: dict[str, Field]
    _fields: MappingProxyType[str, Field]

    _auto: bool = False
    """Whether a database table should be created.
    If set to ``False``, override :meth:`~odoo.models.BaseModel.init`
    to create the database table.

    Automatically defaults to `True` for abstract models.

    .. tip:: To create a model without any table, inherit
            from :class:`~odoo.models.AbstractModel`.
    """
    _register: bool = False  #: registry visibility
    _abstract: bool = True
    """ Whether the model is *abstract*.

    .. seealso:: :class:`AbstractModel`
    """
    _transient: bool = False
    """ Whether the model is *transient*.

    .. seealso:: :class:`TransientModel`
    """

    _name: str = None  #: the model name (in dot-notation, module namespace)
    _description: str | None = None  #: the model's informal name
    _module: str | None = None  #: the model's module (in the Odoo sense)
    _custom: bool = False  #: should be True for custom models only

    _inherit: str | list[str] | tuple[str, ...] = ()
    """Python-inherited models:

    :type: str or list(str) or tuple(str)

    .. note::

        * If :attr:`._name` is set, name(s) of parent models to inherit from
        * If :attr:`._name` is unset, name of a single model to extend in-place
    """
    _inherits: frozendict[str, str] = frozendict()
    """dictionary {'parent_model': 'm2o_field'} mapping the _name of the parent business
    objects to the names of the corresponding foreign key fields to use::

      _inherits = {
          'a.model': 'a_field_id',
          'b.model': 'b_field_id'
      }

    implements composition-based inheritance: the new model exposes all
    the fields of the inherited models but stores none of them:
    the values themselves remain stored on the linked record.

    .. warning::

      if multiple fields with the same name are defined in the
      :attr:`~odoo.models.Model._inherits`-ed models, the inherited field will
      correspond to the last one (in the inherits list order).
    """
    _table: str = ""  #: SQL table name used by model if :attr:`_auto`
    _table_query: SQL | str | None = (
        None  #: SQL expression of the table's content (optional)
    )
    _table_objects: dict[str, TableObject] = frozendict()  #: SQL/Table objects
    _inherit_children: OrderedSet[str]

    _rec_name: str | None = None
    """Field to use for labeling records. Default: ``name`` if the model has it.

    Set during model setup in ``registration.py``.  Changing the default to
    ``''`` was considered but rejected: it would break ``_compute_display_name``
    for the majority of models that rely on the implicit ``name`` fallback.
    """
    _rec_names_search: list[str] | None = None  #: fields to consider in ``name_search``
    _order: str = "id"  #: default order field for searching results
    _parent_name: str = "parent_id"  #: the many2one field used as parent field
    _parent_store: bool = False
    """set to True to compute parent_path field.

    Alongside a :attr:`~.parent_path` field, sets up an indexed storage
    of the tree structure of records, to enable faster hierarchical queries
    on the records of the current model using the ``child_of`` and
    ``parent_of`` domain operators.
    """
    _active_name: str | None = None
    """field to use for active records, automatically set to either ``"active"``
    or ``"x_active"``.
    """
    _fold_name: str = "fold"  #: field to determine folded groups in kanban views

    _translate: bool = True
    """Whether to export translations for this model.

    Legacy attribute from the old API.  Kept for backward compatibility
    as some models (e.g. ir.model.constraint) set ``_translate = False``
    to suppress translation export.  Low cost, no urgency to remove.
    """
    _check_company_auto: bool = False
    """On write and create, call ``_check_company`` to ensure companies
    consistency on the relational fields having ``check_company=True``
    as attribute.
    """

    _allow_sudo_commands: bool = True
    """Allow One2many and Many2many Commands targeting this model in an environment using `sudo()` or `with_user()`.
    By disabling this flag, security-sensitive models protect themselves
    against malicious manipulation of One2many or Many2many fields
    through an environment using `sudo` or a more privileged user.
    """

    _depends: frozendict[str, Iterable[str]] = frozendict()
    """dependencies of models backed up by SQL views
    ``{model_name: field_names}``, where ``field_names`` is an iterable.
    This is only used to determine the changes to flush to database before
    executing any search/read operations. It won't be used for cache
    invalidation or recomputing fields.
    """

    id = Id()
    display_name = Char(
        string="Display Name",
        compute="_compute_display_name",
        search="_search_display_name",
    )

    def _valid_field_parameter(self, field, name):
        """Return whether the given parameter name is valid for the field."""
        return name == "related_sudo"

    @api.model
    def _post_model_setup__(self):
        """Method called after the model has been setup."""
        pass

    @property
    def _table_sql(self) -> SQL:
        """Return an :class:`SQL` object that represents SQL table identifier
        or table query.
        """
        table_query = self._table_query
        if table_query and isinstance(table_query, SQL):
            table_sql = SQL("(%s)", table_query)
        elif table_query:
            table_sql = SQL(f"({table_query})")
        else:
            table_sql = SQL.identifier(self._table)
        if not self._depends:
            return table_sql

        # add self._depends (and its transitive closure) as metadata to table_sql
        fields_to_flush: list[Field] = []
        seen: set[str] = set()
        models = [self]
        while models:
            current_model = models.pop()
            for model_name, field_names in current_model._depends.items():
                if model_name not in seen:
                    seen.add(model_name)
                    model = self.env[model_name]
                    models.append(model)
                fields_to_flush.extend(self.env[model_name]._fields[fname] for fname in field_names)

        return SQL.EMPTY.join(
            [
                table_sql,
                *(SQL(to_flush=field) for field in fields_to_flush),
            ]
        )

    @property
    def _constraint_methods(self):
        """Return a list of methods implementing Python constraints."""

        def is_constraint(func):
            return callable(func) and hasattr(func, "_constrains")

        def wrap(func, names):
            # wrap func into a proxy function with explicit '_constrains',
            # preserving the original sudo preference
            sudo_flag = getattr(func, "_constrains_sudo", True)

            @api.constrains(*names, sudo=sudo_flag)
            def wrapper(self):
                return func(self)

            return wrapper

        cls = self.env.registry[self._name]
        methods = []
        for attr, func in getmembers(cls, is_constraint):
            if callable(func._constrains):
                func = wrap(func, func._constrains(self.sudo()))
            for name in func._constrains:
                field = cls._fields.get(name)
                if not field:
                    _logger.warning(
                        "method %s.%s: @constrains parameter %r is not a field name",
                        cls._name,
                        attr,
                        name,
                    )
                elif not (field.store or field.inverse or field.inherited):
                    _logger.warning(
                        "method %s.%s: @constrains parameter %r is not writeable",
                        cls._name,
                        attr,
                        name,
                    )
            methods.append(func)

        # optimization: memoize result on cls, it will not be recomputed
        cls._constraint_methods = methods
        return methods

    @property
    def _ondelete_methods(self):
        """Return a list of methods implementing checks before unlinking."""

        def is_ondelete(func):
            return callable(func) and hasattr(func, "_ondelete")

        cls = self.env.registry[self._name]
        methods = [func for _, func in getmembers(cls, is_ondelete)]
        # optimization: memoize results on cls, it will not be recomputed
        cls._ondelete_methods = methods
        return methods

    @property
    def _onchange_methods(self):
        """Return a dictionary mapping field names to onchange methods."""

        def is_onchange(func):
            return callable(func) and hasattr(func, "_onchange")

        # collect onchange methods on the model's class
        cls = self.env.registry[self._name]
        methods = defaultdict(list)
        for _attr, func in getmembers(cls, is_onchange):
            missing = []
            for name in func._onchange:
                if name not in cls._fields:
                    missing.append(name)
                methods[name].append(func)
            if missing:
                _logger.warning(
                    "@api.onchange%r parameters must be field names -> not valid: %s",
                    func._onchange,
                    missing,
                )

        # add onchange methods to implement "change_default" on fields
        def onchange_default(field, self):
            value = field.convert_to_write(self[field.name], self)
            condition = f"{field.name}={value}"
            defaults = self.env["ir.default"]._get_model_defaults(self._name, condition)
            self.update(defaults)

        for name, field in cls._fields.items():
            if field.change_default:
                methods[name].append(functools.partial(onchange_default, field))

        # optimization: memoize result on cls, it will not be recomputed
        cls._onchange_methods = methods
        return methods

    def _is_an_ordinary_table(self):
        return self.pool.is_an_ordinary_table(self)

    def _validate_fields(
        self, field_names: Iterable[str], excluded_names: Iterable[str] = ()
    ) -> None:
        """Invoke the constraint methods for which at least one field name is
        in ``field_names`` and none is in ``excluded_names``.
        """
        methods = self._constraint_methods
        if not methods:
            return

        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()
            _count = 0

        # By default, constraints run as sudo (like stored computed fields —
        # see Field.compute_value()).  Individual constraints may opt out with
        # @api.constrains(..., sudo=False) for user-aware validation.
        records_sudo = self.sudo()
        records_user = self
        field_names = set(field_names)
        excluded_names = set(excluded_names)
        for check in methods:
            if not field_names.isdisjoint(
                check._constrains
            ) and excluded_names.isdisjoint(check._constrains):
                use_sudo = getattr(check, "_constrains_sudo", True)
                check(records_sudo if use_sudo else records_user)
                if _debug:
                    _count += 1

        if _debug:
            _orm_crud.debug(
                "[%.3f ms] _validate_fields %s: %d constraints",
                (time.perf_counter() - _t0) * 1000,
                self._name,
                _count,
            )

    @api.model
    def _rec_name_fallback(self) -> str:
        # if self._rec_name is set, it belongs to self._fields
        return self._rec_name or "id"

    #
    # display_name, name_create
    #

    @api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
    def _compute_display_name(self):
        """Compute the value of the `display_name` field.

        The `display_name` field is a textual representation of the record.
        This method can be overridden to change the representation.  If needed,
        it can be made field-dependent using :attr:`~odoo.api.depends` and
        context-dependent using :attr:`~odoo.api.depends_context`.
        """
        if self._rec_name:
            convert = self._fields[self._rec_name].convert_to_display_name
            for record in self:
                record.display_name = convert(record[self._rec_name], record)
        else:
            for record in self:
                record.display_name = f"{record._name},{record.id}"

    @api.model
    def name_create(self, name: str) -> tuple[int, str] | typing.Literal[False]:
        """Create a new record by calling :meth:`~.create` with only one value
        provided: the display name of the new record.

        The new record will be initialized with any default values
        applicable to this model, or provided through the context. The usual
        behavior of :meth:`~.create` applies.

        :param name: display name of the record to create
        :return: the (id, display_name) pair value of the created record
        """
        if not self._rec_name:
            raise UserError(
                f"Cannot execute name_create: no _rec_name defined on {self._name}"
            )
        record = self.create({self._rec_name: name})
        return record.id, record.display_name

    # -------------------------------------------------------------------------
    # Property definition
    # -------------------------------------------------------------------------
    @api.model
    def get_property_definition(self, full_name: str) -> dict:
        """Return the definition of the given property.

        :param full_name: Name of the field / property
            (e.g. "property.integer")
        """
        self.browse().check_access("read")
        field_name, property_name = parse_field_expr(full_name)
        field = self._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field {field_name!r} on model {self._name!r}")
        from ..fields.properties import check_property_field_value_name

        check_property_field_value_name(property_name)

        target_model = self.env[self._fields[field.definition_record].comodel_name]
        field_definition = target_model._fields[field.definition_record_field]
        result = self.env.execute_query_dict(
            SQL(
                """ SELECT definition
                  FROM %(table)s, jsonb_array_elements(%(field)s) definition
                 WHERE %(field)s IS NOT NULL AND definition->>'name' = %(name)s
                 LIMIT 1 """,
                table=SQL.identifier(target_model._table),
                field=SQL.identifier(
                    field.definition_record_field, to_flush=field_definition
                ),
                name=property_name,
            )
        )
        return result[0]["definition"] if result else {}

    def get_base_url(self) -> str:
        """Return rooturl for a specific record.

        By default, it returns the ir.config.parameter of base_url
        but it can be overridden by model.

        :return: the base url for this record
        """
        if len(self) > 1:
            raise ValueError(f"Expected singleton or no record: {self}")
        return self.env["ir.config_parameter"].sudo().get_param("web.base.url")

    def _compute_field_value(self, field: Field) -> None:
        determine(field.compute, self)

        if field.store and any(self._ids):
            # check constraints of the fields that have been computed
            fnames = [f.name for f in self.pool.field_computed[field]]
            self.filtered("id")._validate_fields(fnames)

    def _clean_properties(self) -> None:
        """Remove all properties of ``self`` that are no longer in the related definition"""
        for fname, field in self._fields.items():
            if field.type != "properties":
                continue
            for record in self:
                old_value = record[fname]._values
                if not old_value:
                    continue

                definitions = field._get_properties_definition(record)
                all_names = {definition["name"] for definition in definitions}
                new_values = {
                    name: value
                    for name, value in old_value.items()
                    if name in all_names
                }
                if len(new_values) != len(old_value):
                    record[fname] = new_values

    def _validate_properties_definition(self, properties_definition, field):
        """Allow to validate additional properties attributes."""

    def _additional_allowed_keys_properties_definition(self):
        """Allow to add more allowed key for properties."""
        return ()

    def _convert_to_cache_properties_definition(self, value):
        """Allow to patch `convert_to_cache` of the properties definition."""
        return value

    def _convert_to_column_properties_definition(self, value):
        """Allow to patch `convert_to_column` of the properties definition."""
        return value

    #
    # Deprecated properties for backward compatibility
    #

    @property
    @api.deprecated("Deprecated since 19.0, use self.env.cr directly")
    def _cr(self):
        return self.env.cr


collections.abc.Set.register(BaseModel)
# not exactly true as BaseModel doesn't have index or count
collections.abc.Sequence.register(BaseModel)


AbstractModel = BaseModel


class Model(AbstractModel):
    """Main super-class for regular database-persisted Odoo models.

    Odoo models are created by inheriting from this class::

        class ResUsers(Model): ...

    The system will later instantiate the class once per database (on
    which the class' module is installed).
    """

    _auto: bool = True  # automatically create database backend
    _register: bool = (
        False  # not visible in ORM registry, meant to be python-inherited only
    )
    _abstract: typing.Literal[False] = False  # not abstract
