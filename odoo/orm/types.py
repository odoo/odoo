# ruff: noqa: E402, F401
import typing
from collections.abc import Mapping

from .api import Environment, IdType, NewId
from .fields import Field
from .models import BaseModel
from .registry import Registry
try:
    from typing_extensions import Self
except ImportError:
    from typing import Self

DomainType = list[str | tuple[str, str, typing.Any]]
ContextType = Mapping[str, typing.Any]
ValuesType = dict[str, typing.Any]
