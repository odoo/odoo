import enum
import typing
from collections.abc import Collection, Mapping
from collections.abc import Set as AbstractSet

from odoo.libs.sql import SQL

type ContextType = Mapping[str, typing.Any]
type ValuesType = dict[str, typing.Any]

COLLECTION_TYPES = (list, tuple, AbstractSet)


class NewId:
    __slots__ = ("__hash", "origin", "ref")

    def __init__(self, origin: int | None = None, ref: typing.Any = None) -> None:
        self.origin = origin
        self.ref = ref
        if origin is not None:
            self.__hash = hash(origin)
        elif ref is not None:
            self.__hash = hash(ref)
        else:
            self.__hash = id(self)

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, NewId):
            return NotImplemented
        if self.origin is not None and other.origin is not None:
            return self.origin == other.origin
        if self.origin is None and other.origin is None:
            if self.ref is not None and other.ref is not None:
                return self.ref == other.ref
        return False

    def __hash__(self) -> int:
        return self.__hash

    # a total order in which a NewId sorts right after its origin and every
    # NewId without one sorts last: n < NewId(origin=n) < n + 1 < NewId()
    def __lt__(self, other: object) -> bool:
        if isinstance(other, NewId):
            s, o = self.origin, other.origin
            if s is None:
                return False
            if o is None:
                return True
            return s < o
        if isinstance(other, int):
            if self.origin is None:
                return False
            return self.origin < other
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if self is other:
            return True
        if isinstance(other, NewId):
            if self == other:
                return True
            s, o = self.origin, other.origin
            if s is None:
                return False
            if o is None:
                return True
            return s <= o
        if isinstance(other, int):
            if self.origin is None:
                return False
            return self.origin < other
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, NewId):
            s, o = self.origin, other.origin
            if s is None and o is None:
                return False
            if s is None:
                return True
            if o is None:
                return False
            return s > o
        if isinstance(other, int):
            if self.origin is None:
                return True
            return self.origin >= other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if self is other:
            return True
        if isinstance(other, NewId):
            if self == other:
                return True
            s, o = self.origin, other.origin
            if s is None and o is None:
                return False
            if s is None:
                return True
            if o is None:
                return False
            return s >= o
        if isinstance(other, int):
            if self.origin is None:
                return True
            return self.origin >= other
        return NotImplemented

    def __repr__(self) -> str:
        if self.origin is not None:
            return f"<NewId origin={self.origin!r}>"
        if self.ref is not None:
            return f"<NewId ref={self.ref!r}>"
        return f"<NewId 0x{id(self):x}>"

    def __str__(self) -> str:
        if self.origin is not None:
            id_part = repr(self.origin)
        elif self.ref is not None:
            id_part = repr(self.ref)
        else:
            id_part = hex(id(self))
        return f"NewId_{id_part}"


type IdType = int | NewId | str


class Command(enum.IntEnum):
    CREATE = 0
    UPDATE = 1
    DELETE = 2
    UNLINK = 3
    LINK = 4
    CLEAR = 5
    SET = 6

    @classmethod
    def create(cls, values: ValuesType) -> CommandCreate:
        return (cls.CREATE, 0, values)

    @classmethod
    def update(cls, id: IdType, values: ValuesType) -> CommandUpdate:
        return (cls.UPDATE, id, values)

    @classmethod
    def delete(cls, id: IdType) -> CommandDelete:
        return (cls.DELETE, id, 0)

    @classmethod
    def unlink(cls, id: IdType) -> CommandUnlink:
        return (cls.UNLINK, id, 0)

    @classmethod
    def link(cls, id: IdType) -> CommandLink:
        return (cls.LINK, id, 0)

    @classmethod
    def clear(cls) -> CommandClear:
        return (cls.CLEAR, 0, 0)

    @classmethod
    def set(cls, ids: Collection[IdType]) -> CommandSet:
        return (cls.SET, 0, ids)


type CommandCreate = tuple[typing.Literal[Command.CREATE], IdType, ValuesType]
type CommandUpdate = tuple[typing.Literal[Command.UPDATE], IdType, ValuesType]
type CommandDelete = tuple[typing.Literal[Command.DELETE], IdType, typing.Literal[0]]
type CommandUnlink = tuple[typing.Literal[Command.UNLINK], IdType, typing.Literal[0]]
type CommandLink = tuple[typing.Literal[Command.LINK], IdType, typing.Literal[0]]
type CommandClear = tuple[
    typing.Literal[Command.CLEAR], typing.Literal[0], typing.Literal[0]
]
type CommandSet = tuple[
    typing.Literal[Command.SET], typing.Literal[0], Collection[IdType]
]

type CommandValue = (
    CommandCreate
    | CommandUpdate
    | CommandDelete
    | CommandUnlink
    | CommandLink
    | CommandClear
    | CommandSet
)


SUPERUSER_ID = 1

SQL_DEFAULT = SQL("DEFAULT")

SQL_OPERATORS = {
    "=": SQL(" = "),
    "!=": SQL(" != "),
    "in": SQL(" IN "),
    "not in": SQL(" NOT IN "),
    "<": SQL(" < "),
    ">": SQL(" > "),
    "<=": SQL(" <= "),
    ">=": SQL(" >= "),
    "like": SQL(" LIKE "),
    "ilike": SQL(" ILIKE "),
    "=like": SQL(" LIKE "),
    "=ilike": SQL(" ILIKE "),
    "not like": SQL(" NOT LIKE "),
    "not ilike": SQL(" NOT ILIKE "),
    "not =like": SQL(" NOT LIKE "),
    "not =ilike": SQL(" NOT ILIKE "),
    "=~": SQL(" ~ "),
    "not =~": SQL(" !~ "),
}


LOG_ACCESS_COLUMNS = ["create_uid", "create_date", "write_uid", "write_date"]

MAGIC_COLUMNS = ["id"] + LOG_ACCESS_COLUMNS


STATE_FIELD = "state"

SEQUENCE_FIELD = "sequence"

CONVENTIONAL_FIELD_NAMES: dict[str, str] = {
    STATE_FIELD: "defaults to copy=False -- a workflow state is not duplicated",
    SEQUENCE_FIELD: "defaults to aggregator=None -- ordering numbers are not summed",
    "currency_id": "Monetary's implicit currency field (then x_currency_id)",
    "company_id": "the implicit _check_company target on a relational field",
    "display_name": "the computed label, special-cased in search and expressions",
}

NO_ACCESS = "."

MODULE_UNINSTALL_FLAG = "_force_unlink"


INSERT_BATCH_SIZE = 100
UPDATE_BATCH_SIZE = 100

PREFETCH_MAX = 1000

GC_UNLINK_LIMIT = 100_000


__all__ = [
    "COLLECTION_TYPES",
    "CONVENTIONAL_FIELD_NAMES",
    "GC_UNLINK_LIMIT",
    "INSERT_BATCH_SIZE",
    "LOG_ACCESS_COLUMNS",
    "MAGIC_COLUMNS",
    "MODULE_UNINSTALL_FLAG",
    "NO_ACCESS",
    "PREFETCH_MAX",
    "SEQUENCE_FIELD",
    "SQL_DEFAULT",
    "SQL_OPERATORS",
    "STATE_FIELD",
    "SUPERUSER_ID",
    "UPDATE_BATCH_SIZE",
    "Command",
    "CommandValue",
    "ContextType",
    "IdType",
    "NewId",
    "ValuesType",
]
