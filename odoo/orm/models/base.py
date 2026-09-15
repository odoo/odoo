import collections
import typing

from .. import decorators as api
from .._recordset import set_base_model
from ..fields.base import Field
from .metaclass import MetaModel
from .mixins import (
    AccessMixin,
    CacheMixin,
    CopyMixin,
    CreateMixin,
    EnvironmentMixin,
    ExportMixin,
    IterationMixin,
    LifecycleMixin,
    LoadMixin,
    ReadGroupMixin,
    ReadMixin,
    RecomputeMixin,
    SchemaMixin,
    SearchMixin,
    TranslationMixin,
    TraversalMixin,
    UnlinkMixin,
    WriteMixin,
)
from .mixins._constraints import _ConstraintsMixin
from .mixins._display_name import _DisplayNameMixin
from .mixins._field_compute import _FieldComputeMixin
from .mixins._hooks import _HooksMixin
from .mixins._magic_fields import _MagicFieldsMixin
from .mixins._metadata import _ModelMetadataMixin
from .mixins._properties import _PropertiesMixin
from .mixins._query import _QueryMixin


class BaseModel(
    CreateMixin,
    WriteMixin,
    UnlinkMixin,
    CopyMixin,
    IterationMixin,
    TraversalMixin,
    CacheMixin,
    RecomputeMixin,
    EnvironmentMixin,
    LifecycleMixin,
    ReadMixin,
    SearchMixin,
    ReadGroupMixin,
    TranslationMixin,
    SchemaMixin,
    ExportMixin,
    LoadMixin,
    AccessMixin,
    _PropertiesMixin,
    _QueryMixin,
    _ConstraintsMixin,
    _DisplayNameMixin,
    _FieldComputeMixin,
    _HooksMixin,
    _MagicFieldsMixin,
    _ModelMetadataMixin,
    metaclass=MetaModel,
):
    __slots__ = ["_ids", "_prefetch_ids", "env"]

    _register: bool = False

    def _is_valid_field_parameter(self, field: Field, name: str) -> bool:
        return name == "related_sudo"

    @api.model
    def _post_model_setup__(self) -> None:
        pass

    def get_base_url(self) -> str:
        if len(self) > 1:
            raise ValueError(f"Expected singleton or no record: {self}")
        return self.env.registry.settings.get(self.env, "web.base.url")


collections.abc.Set.register(BaseModel)
collections.abc.Sequence.register(BaseModel)

set_base_model(BaseModel)


AbstractModel = BaseModel


class Model(AbstractModel):
    _auto: bool = True
    _register: bool = False
    _abstract: typing.Literal[False] = False
