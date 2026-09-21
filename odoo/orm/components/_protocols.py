from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..primitives import IdType as RecordId
else:
    RecordId = object


class FieldKey(Protocol):
    """What this package requires of a field: that it can key a dict.

    The generic parameter of `FieldCache`, `ComputeEngine` and `UnitOfWork` is
    bound to this and nothing more, which is what lets a test drive them with
    a two-field NamedTuple. Several methods read more than a key, though, and
    they do it through `getattr(field, name, default)` rather than by widening
    the bound -- so the attribute is optional at runtime and invisible to the
    checker. Those reads are listed here so the contract is at least written
    down:

    | Read | Where | Default |
    |---|---|---|
    | `model_name` | `FieldCache.pop_dirty_for_model`, `UnitOfWork.get_dirty_model_names` | `None` |
    | `tree_siblings` | `ComputeEngine._keys` | `()` |
    | `name` | `RecomputeScheduler`'s debug events, `ModelGraph`'s string interning | the field itself |
    | `inverse_name`, `comodel_name` | `ModelGraph`'s string interning | `None` |

    A field missing one of those behaves as the default says: a key with no
    `model_name` is never popped for a model, a field with no `tree_siblings`
    stands alone, and a nameless one prints as itself.
    """

    def __hash__(self) -> int: ...


class NamedField(FieldKey, Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def name(self) -> str: ...


class SchedulableField(FieldKey, Protocol):
    @property
    def recursive(self) -> bool: ...

    @property
    def is_stored_computed(self) -> bool: ...

    @property
    def tree_siblings(self) -> tuple[SchedulableField, ...]:
        """The same-named fields of the other models sharing this one's table.

        A value done or protected is a fact of the row, so it is recorded for
        every model of the tree; `ComputeEngine._keys` is what spreads it.
        """


class FieldLike(NamedField, SchedulableField, Protocol):
    @property
    def type(self) -> str: ...

    @property
    def store(self) -> bool: ...

    @property
    def relational(self) -> bool: ...

    @property
    def compute(self) -> str | Callable[..., None] | None: ...

    @property
    def inverse_name(self) -> str | None: ...

    @property
    def comodel_name(self) -> str | None: ...
