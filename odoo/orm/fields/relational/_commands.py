import typing
from collections.abc import Callable, Iterable
from collections.abc import Set as AbstractSet

from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet

from ...primitives import Command

if typing.TYPE_CHECKING:
    from ...primitives import IdType, ValuesType

_debug = DebugLog(__name__)


class CommandDelta:
    __slots__ = (
        "created",
        "deleted",
        "linked",
        "replaced",
        "set_ids",
        "superseding",
        "unlinked",
        "updated",
    )

    def __init__(self) -> None:
        self.created: list[tuple[typing.Any, ValuesType]] = []
        self.updated: list[tuple[IdType, ValuesType]] = []
        self.deleted: OrderedSet[IdType] = OrderedSet()
        self.linked: OrderedSet[IdType] = OrderedSet()
        self.unlinked: OrderedSet[IdType] = OrderedSet()
        self.replaced: bool = False
        self.set_ids: tuple[IdType, ...] = ()
        self.superseding: bool = True

    @classmethod
    def fold(
        cls,
        commands: Iterable[typing.Any] | None,
        normalize: Callable[[typing.Any], IdType] = lambda id_: id_,
        *,
        superseding: bool = True,
    ) -> typing.Self:
        delta = cls()
        delta.superseding = superseding
        for command in commands or ():
            if isinstance(command, dict):
                delta.created.append((None, command))
                continue
            if not isinstance(command, (tuple, list)):
                delta._link(normalize(command))
                continue
            if not command:
                continue
            match command[0]:
                case Command.CREATE:
                    delta.created.append((command[1], command[2]))
                case Command.UPDATE:
                    delta.updated.append((normalize(command[1]), command[2]))
                case Command.DELETE:
                    id_ = normalize(command[1])
                    delta.deleted.add(id_)
                    delta.linked.discard(id_)
                case Command.UNLINK:
                    id_ = normalize(command[1])
                    delta.unlinked.add(id_)
                    delta.linked.discard(id_)
                case Command.LINK:
                    delta._link(normalize(command[1]))
                case Command.CLEAR:
                    delta._replace(())
                case Command.SET:
                    ids = command[2]
                    if ids.__class__ is int:
                        ids = (ids,)
                    # an RPC payload can carry false/null where the ids go;
                    # clear, like the empty list, instead of a raw TypeError
                    delta._replace(tuple(normalize(id_) for id_ in ids or ()))
        return delta

    def _link(self, id_: IdType) -> None:
        self.linked.add(id_)
        self.unlinked.discard(id_)

    def _replace(self, ids: tuple[IdType, ...]) -> None:
        self.replaced = True
        self.set_ids = ids
        if self.superseding:
            if _debug.logic.enabled and (self.created or self.linked or self.unlinked):
                _debug.logic(
                    "field.x2many.commands_superseded",
                    set_ids=len(ids),
                    created=len(self.created),
                    linked=len(self.linked),
                    unlinked=len(self.unlinked),
                )
            self.created.clear()
            self.linked.clear()
            self.unlinked.clear()

    @property
    def removed(self) -> AbstractSet[IdType]:
        return self.unlinked | self.deleted

    def get_final_ids(
        self, current: Iterable[IdType], created_ids: Iterable[IdType] = ()
    ) -> OrderedSet[IdType]:
        ids = OrderedSet(self.set_ids if self.replaced else current)
        ids -= self.removed
        ids.update(self.linked)
        ids.update(created_ids)
        return ids
