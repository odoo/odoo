# ruff: noqa: E402, F401
import typing
from collections.abc import Mapping
from typing import Self

from .commands import Command
from .domains import Domain
from .environments import Environment
from .fields import Field
from .identifiers import IdType, NewId
from .models import BaseModel
from .registry import Registry

DomainType = Domain | list[str | tuple[str, str, typing.Any]]
ContextType = Mapping[str, typing.Any]
ValuesType = dict[str, typing.Any]
ModelType = typing.TypeVar("ModelType", bound=BaseModel)

if typing.TYPE_CHECKING:
    from .commands import CommandValue
