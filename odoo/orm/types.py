# ruff: noqa: E402, F401
import typing
from collections.abc import Mapping

from .environments import Environment
from .fields import Field
from .identifiers import IdType, NewId
from .models import BaseModel
from .registry import Registry
try:
    from typing_extensions import Self
except ImportError:
    try:
        from typing import Self
    except ImportError:
        Self = typing.TypeVar("Self")

DomainType = list[str | tuple[str, str, typing.Any]]
ContextType = Mapping[str, typing.Any]
ValuesType = dict[str, typing.Any]
