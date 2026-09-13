import typing
from collections.abc import (
    Collection,
)

from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, ValuesType
    from ..runtime import Environment

    M = typing.TypeVar("M", bound=BaseModel)


from ._field_stubs import _FieldStubs

_debug = DebugLog(__name__)


class _FieldDescriptionMixin(_FieldStubs):
    def get_description(
        self, env: Environment, attributes: Collection[str] | None = None
    ) -> ValuesType:
        desc = {}
        for attr, prop in self.description_attrs:
            if attributes is not None and attr not in attributes:
                continue
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value is not None:
                desc[attr] = value

        return desc

    def _description_depends(self, env: Environment) -> Collection[str]:
        return env.registry.field_depends[self]

    @property
    def _description_searchable(self) -> bool:
        return bool(self.store or self.search)

    def _description_sortable(self, env: Environment) -> bool:
        if self.is_column:
            return True
        if self.inherited_field and self.inherited_field._description_sortable(env):
            return True
        return env[self.model_name]._is_field_sortable(self.name)

    def _description_groupable(self, env: Environment) -> bool:
        if self.is_column:
            return True
        if self.inherited_field and self.inherited_field._description_groupable(env):
            return True
        return env[self.model_name]._is_field_groupable(self.name)

    def _description_aggregator(self, env: Environment) -> str | None:
        if not self.aggregator or self.is_column:
            return self.aggregator
        if self.inherited_field and self.inherited_field._description_aggregator(env):
            return self.aggregator

        model = env[self.model_name]
        try:
            query = model._as_query(ordered=False)
            model._read_group_select(f"{self.name}:{self.aggregator}", query)
            return self.aggregator
        except (ValueError, AccessError, NotImplementedError) as e:
            _debug.logic(
                "field.description.aggregator_unsupported",
                model=self.model_name,
                field=self.name,
                aggregator=self.aggregator,
                error=type(e).__name__,
            )
            return None

    def _description_string(self, env: Environment) -> str | None:
        if self.string and (env.lang or self.base_field.manual):
            model_name = self.base_field.model_name
            field_string = env.registry.metaschema.field_strings(env, model_name)
            return field_string.get(self.name) or self.string
        return self.string

    def _description_help(self, env: Environment) -> str | None:
        if self.help and (env.lang or self.base_field.manual):
            model_name = self.base_field.model_name
            field_help = env.registry.metaschema.field_helps(env, model_name)
            return field_help.get(self.name) or self.help
        return self.help

    def _description_falsy_value_label(self, env) -> str | None:
        if not self.falsy_value_label:
            return None
        return env._(self.falsy_value_label)  # noqa: E8502  _lt() at the declaration

    def is_editable(self) -> bool:
        return not self.readonly
