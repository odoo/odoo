# ruff: noqa: E402, F401
import typing
from collections.abc import Mapping

from .environments import Environment
from .fields import Field
from .identifiers import IdType, NewId
from .models import BaseModel
from .registry import Registry

if typing.TYPE_CHECKING:
    # for pre python 3.11, import extensions first
    try:
        from typing_extensions import Self
    except ImportError:
        from typing import Self
else:
    try:
        from typing import Self
    except ImportError:
        # fallback for 3.10
        Self = typing.Any

DomainType = list[str | tuple[str, str, typing.Any]]
ContextType = Mapping[str, typing.Any]
ValuesType = dict[str, typing.Any]
