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
    _order: str = "id"
    _parent_name: str = "parent_id"
    _parent_store: bool = False
    _active_name: str | None = None
    # a stored column that IS display_name whenever the context carries none
    # of the keys, so a read engine can serve it without the compute; the
    # guard names a field whose empty rows render a translated placeholder
    # instead, which the stored column carries in English only
    _display_name_column: str | tuple[str, ...] | None = None
    _display_name_column_guard: str | None = None
    _display_name_context_keys: tuple[str, ...] = ()
    # the model's _search_display_name is the default composition whenever the
    # context carries none of the keys above
    _display_name_search_default: bool = False
    # stored fields whose exact match takes precedence in _search_display_name:
    # for "in" / "ilike" with a value, rows matching one of them exactly are the
    # whole answer when any exist, the default composition answers otherwise
    _display_name_search_exact: tuple[str, ...] = ()
    _fold_name: str = "fold"

    _translate: bool = True
    _check_company_auto: bool = False
    # the fields a _search override reads to decide what a user sees, beyond
    # the record rules: a write to one of them evicts the x2many slots users
    # hold on this model's records. None on an override means every field
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
