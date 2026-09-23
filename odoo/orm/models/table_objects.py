import typing

from odoo.db import schema as sql
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import normalize_identifier

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from psycopg.errors import Diagnostic

    from ..runtime import Environment, Registry

    BaseModel = typing.Any

    ConstraintMessageType = str | Callable[[Environment, Diagnostic | None], str]
    ConstraintDefinitionType = str | Callable[[Registry], str]
    IndexDefinitionType = str | Callable[[Registry], str]


class TableObject:
    name: str
    message: ConstraintMessageType = ""
    _module: str = ""

    def __init__(self) -> None:
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        if not name.startswith("_"):
            raise TypeError(
                f"Name {name!r} of SQL object on {owner.__name__!r} must start with '_'"
            )
        if name.startswith(f"_{owner.__name__}__"):
            raise TypeError(
                f"Name {name!r} of SQL object on {owner.__name__!r} must not be mangled "
                "(use a single leading underscore, not two)"
            )
        self.name = name[1:]
        model_class = typing.cast("typing.Any", owner)
        if getattr(owner, "pool", None) is None:
            self._module = model_class._module
            model_class._table_object_definitions.append(self)
            _debug.lifecycle(
                "table_object.defined",
                kind=type(self).__name__,
                name=self.name,
                cls=owner.__name__,
                module=self._module,
            )

    def get_definition(self, registry: Registry) -> str:
        raise NotImplementedError

    def get_full_name(self, model: BaseModel) -> str:
        assert self.name, "The table object is not named"
        name = f"{model._table}_{self.name}"
        return normalize_identifier(name)

    def get_error_message(
        self, model: BaseModel, diagnostics: Diagnostic | None = None
    ) -> str:
        message = self.message
        if callable(message):
            return message(model.env, diagnostics)
        return message

    def apply_to_database(self, model: BaseModel) -> None:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"({self.name!r}, {self.message!r})"


class Constraint(TableObject):
    def __init__(
        self,
        definition: ConstraintDefinitionType,
        message: ConstraintMessageType = "",
    ) -> None:
        super().__init__()
        self._definition = definition
        if message:
            self.message = message

    def get_definition(self, registry: Registry) -> str:
        if callable(self._definition):
            return self._definition(registry)
        return self._definition

    def apply_to_database(self, model: BaseModel) -> None:
        cr = model.env.cr
        conname = self.get_full_name(model)
        definition = self.get_definition(model.pool)
        current_definition = sql.get_constraint_definition(cr, model._table, conname)
        if current_definition == definition:
            return

        _debug.lifecycle(
            "table_object.constraint_queued",
            model=getattr(model, "_name", None),
            name=conname,
            replaces_constraint=bool(current_definition),
        )
        if current_definition:
            sql.drop_constraint(cr, model._table, conname)
        elif sql.get_index_definition(cr, conname)[0]:
            sql.drop_index(cr, conname, model._table)

        model.pool.post_constraint(
            cr,
            lambda cr: sql.add_constraint(cr, model._table, conname, definition),
            conname,
        )


class Index(TableObject):
    unique: bool = False

    def __init__(self, definition: IndexDefinitionType) -> None:
        super().__init__()
        self._index_definition = definition

    def _get_definition_clause(self, registry: Registry) -> str:
        if callable(self._index_definition):
            return self._index_definition(registry)
        return self._index_definition

    def _format_definition(self, clause: str) -> str:
        if not clause:
            return ""
        return f"{'UNIQUE ' if self.unique else ''}INDEX {clause}"

    def get_definition(self, registry: Registry) -> str:
        return self._format_definition(self._get_definition_clause(registry))

    def apply_to_database(self, model: BaseModel) -> None:
        cr = model.env.cr
        conname = self.get_full_name(model)
        definition_clause = self._get_definition_clause(model.pool)
        definition = self._format_definition(definition_clause)

        if owning_constraint := sql.get_index_constraint(cr, conname):
            _debug.lifecycle(
                "table_object.index_owner_constraint_dropped",
                model=getattr(model, "_name", None),
                name=conname,
                constraint=owning_constraint,
            )
            sql.drop_constraint(cr, model._table, owning_constraint)
            db_definition = db_comment = None
        else:
            db_definition, db_comment = sql.get_index_definition(cr, conname)

        if db_comment == definition or (not db_comment and db_definition):
            return

        _debug.lifecycle(
            "table_object.index_queued",
            model=getattr(model, "_name", None),
            name=conname,
            unique=self.unique,
            replaces_index=bool(db_definition),
            owned_by_constraint=bool(owning_constraint),
            dropped_only=not definition_clause,
        )
        if db_definition:
            sql.drop_index(cr, conname, model._table)

        if not definition_clause:
            return
        model.pool.post_constraint(
            cr,
            lambda cr: sql.add_index(
                cr,
                conname,
                model._table,
                comment=definition,
                definition=definition_clause,
                unique=self.unique,
            ),
            conname,
        )


class UniqueIndex(Index):
    unique = True

    def __init__(
        self,
        definition: IndexDefinitionType,
        message: ConstraintMessageType = "",
    ) -> None:
        super().__init__(definition)
        if message:
            self.message = message
