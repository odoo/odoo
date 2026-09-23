import typing

from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, frozendict

from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from types import MappingProxyType

    from ..._typing import BaseModel
    from ...fields.base import Field
    from ...runtime import Registry
    from ..table_objects import TableObject

_debug = DebugLog(__name__)


class _ModelMetadataMixin(_ModelStubs):
    __slots__ = ()

    pool: Registry

    _fields__: dict[str, Field]
    _fields: MappingProxyType[str, Field]

    _auto: bool = False
    _abstract: bool = True
    _transient: bool = False
    _is_registry_metadata: bool = False

    _name: str = None  # type: ignore[assignment]
    _description: str | None = None
    _module: str | None = None
    _custom: bool = False

    _inherit: str | list[str] | tuple[str, ...] = ()
    _inherits: dict[str, str] = frozendict()
    _table: str = ""
    _table_query: SQL | str | None = None
    _table_objects: dict[str, TableObject] = frozendict()
    _table_inheritance_root: str = ""
    _inherit_children: OrderedSet[str]
    _inherit_module: dict[str, str | None]

    _base_classes__: tuple[type[BaseModel], ...]
    _model_classes__: tuple[type, ...]
    _setup_done__: bool
    _setup_in_progress__: bool
    _init_attrs_in_progress__: bool

    _rec_name: str | None = None
    _rec_names_search: list[str] | None = None
    _name_create_on_import: bool = False
    _order: str = "id"
    _parent_name: str = "parent_id"
    _parent_store: bool = False
    _active_name: str | None = None
    _display_name_column: str | tuple[str, ...] | None = None
    _display_name_column_guard: str | None = None
    _display_name_context_keys: tuple[str, ...] = ()
    _display_name_search_default: bool = False
    _display_name_search_exact: tuple[str, ...] = ()
    _inherits_sudo_fields: tuple[str, ...] = ()
    _inherits_rules: bool = True
    _fold_name: str = "fold"

    _translate: bool = True
    _check_company_auto: bool = False
    _search_visibility_fields: tuple[str, ...] | None = None

    _allow_sudo_commands: bool = True

    _depends: frozendict[str, Iterable[str]] = frozendict()

    @property
    def _table_sql(self) -> SQL:
        table_query = self._table_query
        if table_query and isinstance(table_query, SQL):
            table_sql = SQL("(%s)", table_query)
        elif table_query:
            table_sql = SQL(f"({table_query})")
        else:
            table_sql = SQL.identifier(self._table)
        if not self._depends:
            return table_sql

        fields_to_flush: OrderedSet[Field] = OrderedSet()
        seen: set[str] = {self._name}
        models = [self]
        while models:
            current_model = models.pop()
            for model_name, field_names in current_model._depends.items():
                model = self.env[model_name]
                if model_name not in seen:
                    seen.add(model_name)
                    models.append(model)
                fields_to_flush.update(model._fields[fname] for fname in field_names)

        _debug.logic(
            "metadata.table_sql_flush_dependencies",
            model=self._name,
            table_query=bool(table_query),
            models=len(seen),
            fields=len(fields_to_flush),
        )
        return SQL.EMPTY.join(
            [
                table_sql,
                *(SQL(to_flush=field) for field in fields_to_flush),
            ]
        )

    def _is_an_ordinary_table(self) -> bool:
        return self.pool.is_an_ordinary_table(self)

    def _is_table_inheritance_root(self) -> bool:
        return bool(self._table) and self._table == self._table_inheritance_root

    def _get_root_model_name(self) -> str:
        """The model owning the root table. Not a cache key: `self._name` is
        already one, and resolving this walks the tree."""
        root_table = self._table_inheritance_root
        for name in self.pool.model_names_by_inheritance_root.get(root_table, ()):
            if self.pool[name]._table == root_table:
                return name
        return self._name

    def _get_reference_model_name(self) -> str:
        """The name a polymorphic reference (`res_model`, `mail.message.model`)
        records for this model's rows. A model is its own reference; a member
        of a table-inheritance tree overrides this with its root, because a
        message, a follower or an attachment belongs to the row, whichever
        model the row was read through."""
        return self._name
