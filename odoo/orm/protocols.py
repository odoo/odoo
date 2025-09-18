"""
Structural typing protocols for cross-layer ORM contracts.

Lower layers (domain, fields, parsing) need to answer "is this a recordset?"
without importing BaseModel, which lives in a higher layer. This module defines
lightweight Protocols that describe the interface these layers actually need.

This eliminates upward dependency violations (lazy imports, TYPE_CHECKING
workarounds) and makes the cross-layer contracts explicit and mypy-checkable.
"""

import typing
from collections.abc import Mapping

from .primitives import IdType

if typing.TYPE_CHECKING:
    from .runtime.environment import Environment


@typing.runtime_checkable
class RecordSetProto(typing.Protocol):
    """Structural type for recordset-like objects.

    Used by lower layers (domain, fields, utils) to check
    ``isinstance(value, RecordSetProto)`` without importing BaseModel.

    BaseModel satisfies this protocol implicitly — no registration needed.
    """

    _ids: tuple[IdType, ...]

    @property
    def ids(self) -> list[int]: ...

    @property
    def env(self) -> Environment: ...


@typing.runtime_checkable
class EnvironmentProtocol(typing.Protocol):
    """Structural type describing what model methods need from ``self.env``.

    The real :class:`~odoo.orm.runtime.environment.Environment` satisfies
    this protocol implicitly via structural subtyping.  Future lightweight
    test doubles can implement just this interface.

    The ~20 operations listed here cover the vast majority of model method
    interactions with ``env``:

    - Model lookup (``env['res.partner']``)
    - Context switching (``env(user=..., su=...)``)
    - Current user / company / language introspection
    - XML-ID resolution (``env.ref()``)
    - Permission checks (``is_superuser``, ``is_admin``, ``is_system``)
    """

    cr: typing.Any
    uid: int
    context: Mapping
    su: bool

    def __getitem__(self, model_name: str) -> RecordSetProto: ...

    def __contains__(self, model_name: str) -> bool: ...

    def __call__(
        self,
        cr: typing.Any = ...,
        user: typing.Any = ...,
        context: dict | None = ...,
        su: bool | None = ...,
    ) -> typing.Self: ...

    @property
    def user(self) -> RecordSetProto: ...

    @property
    def company(self) -> RecordSetProto: ...

    @property
    def companies(self) -> RecordSetProto: ...

    @property
    def lang(self) -> str | None: ...

    @property
    def tz(self) -> typing.Any: ...

    def ref(
        self,
        xml_id: str,
        raise_if_not_found: bool = True,
    ) -> RecordSetProto | None: ...

    def is_superuser(self) -> bool: ...

    def is_admin(self) -> bool: ...

    def is_system(self) -> bool: ...
