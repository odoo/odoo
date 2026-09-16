import typing
from collections import defaultdict
from typing import override

from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import pg_varchar
from odoo.tools.misc import SENTINEL, Sentinel, merge_sequences

from .base import Field, _logger, _prepare_fast_get, call_hook, resolve_mro

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from .._typing import BaseModel, ModelClass, ModelLike
    from ..runtime import Environment

    SelectValue = tuple[str, str]
    OnDeletePolicy = str | Callable[[BaseModel], None]

_debug = DebugLog(__name__)


class Selection[T = str | typing.Literal[False]](Field[T]):
    type = "selection"
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _column_type = ("varchar", pg_varchar())

    selection: (
        list[SelectValue] | str | Callable[[BaseModel], list[SelectValue]] | None
    ) = None
    validate: bool = True
    ondelete: dict[str, OnDeletePolicy] | None = None

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(
            lambda field, value, record: False if value is None else value
        )

    def __init__(
        self,
        selection: typing.Any = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(selection=selection, string=string, **kwargs)
        self._selection = dict(selection) if isinstance(selection, list) else None

    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        assert self.selection is not None, f"Field {self} without selection"

    def setup_related(self, model: BaseModel) -> None:
        super().setup_related(model)
        field = self.related_field
        assert field is not None, f"{self}: setup_related left no related field"
        self.selection = lambda model: field._description_selection(model.env)
        self._selection = None

    def _get_attrs(self, model_class: ModelClass, name: str) -> dict[str, typing.Any]:
        attrs = super()._get_attrs(model_class, name)
        attrs.pop("selection_add", None)
        if attrs.get("group_expand") is True:
            attrs["group_expand"] = self._get_group_expand
        return attrs

    def _apply_selection_arg(self, field, values):
        if self.related:
            _logger.warning(
                "%s: selection attribute will be ignored as the field is related",
                self,
            )
        selection = field._args__["selection"]
        if isinstance(selection, (list, tuple)):
            if values is not None and list(values) != [kv[0] for kv in selection]:
                _debug.logic(
                    "field.selection.overridden",
                    model=self.model_name,
                    field=self.name,
                    module=field._module,
                    previous=len(values),
                    values=len(selection),
                )
                _logger.warning(
                    "%s: selection=%r overrides existing selection; use selection_add instead",
                    self,
                    selection,
                )
            values = dict(selection)
            self.ondelete = {}
        elif callable(selection) or isinstance(selection, str):
            self.ondelete = None
            self.selection = selection
            values = None
            _debug.logic(
                "field.selection.dynamic",
                model=self.model_name,
                field=self.name,
                module=field._module,
                source="method" if isinstance(selection, str) else "callable",
            )
        else:
            raise ValueError(
                f"{self!r}: selection={selection!r} should be a list, a callable or a method name"
            )
        return values

    def _apply_selection_add(self, field, values):
        if self.related:
            _logger.warning(
                "%s: selection_add attribute will be ignored as the field is related",
                self,
            )
        selection_add = field._args__["selection_add"]
        if not isinstance(selection_add, list):
            raise TypeError(f"{self}: selection_add={selection_add!r} must be a list")
        if values is None or self.ondelete is None:
            raise TypeError(
                f"{self}: selection_add={selection_add!r} on non-list selection {self.selection!r}"
            )

        values_add = {kv[0]: (kv[1] if len(kv) > 1 else None) for kv in selection_add}
        ondelete = dict(field._args__.get("ondelete") or {})
        new_values = [key for key in values_add if key not in values]
        for key in new_values:
            ondelete.setdefault(key, "set null")
        if self.required and new_values and "set null" in ondelete.values():
            raise ValueError(
                f"{self!r}: required selection fields must define an ondelete policy that "
                "implements the proper cleanup of the corresponding records upon "
                "module uninstallation. Please use one or more of the following "
                "policies: 'set default' (if the field has a default defined), 'cascade', "
                "or a single-argument callable where the argument is the recordset "
                "containing the specified option."
            )

        for key, val in ondelete.items():
            if callable(val) or val in ("set null", "cascade"):
                continue
            if val == "set default":
                if self.default is None:
                    raise ValueError(
                        f"{self!r}: ondelete policy of type 'set default' is invalid for this field "
                        "as it does not define a default! Either define one in the base "
                        "field, or change the chosen ondelete policy"
                    )
            elif val.startswith("set "):
                if val[4:] not in values:
                    raise ValueError(
                        f"{self}: ondelete policy of type 'set %' must be either 'set null', "
                        "'set default', or 'set value' where value is a valid selection value."
                    )
            else:
                raise ValueError(
                    f"{self!r}: ondelete policy {val!r} for selection value {key!r} is not a valid ondelete"
                    " policy, please choose one of 'set null', 'set default', "
                    "'set [value]', 'cascade' or a callable"
                )

        values = {
            key: values_add.get(key) or values[key]
            for key in merge_sequences(values, values_add)
        }
        self.ondelete.update(ondelete)
        _debug.logic(
            "field.selection.add_merged",
            model=self.model_name,
            field=self.name,
            module=field._module,
            added=new_values,
            relabeled=len(values_add) - len(new_values),
            total=len(values),
        )
        return values

    def _setup_attrs__(self, model_class: ModelClass, name: str) -> None:
        super()._setup_attrs__(model_class, name)
        if not self._base_fields__:
            return

        values = None

        for field in self._base_fields__:
            if "selection" in field._args__:
                values = self._apply_selection_arg(field, values)

            if "selection_add" in field._args__:
                values = self._apply_selection_add(field, values)

        if values is not None:
            self.selection = list(values.items())
            assert all(isinstance(key, str) for key in values), (
                f"Field {self} with non-str value in selection"
            )

        self._selection = values

    def _get_selection_modules(self, model: BaseModel) -> dict[str, set[str]]:
        if not isinstance(self.selection, list):
            return {}
        value_modules: defaultdict[str, set[str]] = defaultdict(set)
        for field in reversed(
            resolve_mro(model, self.name, type(self).__instancecheck__)
        ):
            module = field._module
            if not module:
                continue
            if "selection" in field._args__:
                value_modules.clear()
                if isinstance(field._args__["selection"], list):
                    for value, _label in field._args__["selection"]:
                        value_modules[value].add(module)
            if "selection_add" in field._args__:
                for value_label in field._args__["selection_add"]:
                    if len(value_label) > 1:
                        value_modules[value_label[0]].add(module)
        return value_modules

    @override
    def _dynamic_description_attrs(self, env: Environment) -> frozenset[str]:
        dynamic = super()._dynamic_description_attrs(env)
        selection = self._get_selection()
        if isinstance(selection, str) or callable(selection):
            return dynamic | {"selection"}
        return dynamic

    def _description_selection(self, env: Environment) -> list[SelectValue]:
        selection = self._get_selection()
        if isinstance(selection, str) or callable(selection):
            selection = call_hook(selection, env[self.model_name])
            return [(str(key), str(label)) for key, label in selection]

        if not env.lang:
            return selection

        translations = dict(
            env.registry.metaschema.field_selection(env, self.model_name, self.name)
        )
        return [(key, translations.get(key, label)) for key, label in selection]

    def _get_group_expand(
        self, records: BaseModel, groups: typing.Any, domain: typing.Any
    ) -> list[str]:
        return self.get_values(records.env)

    def _get_selection(
        self,
    ) -> list[SelectValue] | str | Callable[[BaseModel], list[SelectValue]]:
        if self.selection is None:
            raise TypeError(f"{self} declares no selection")
        return self.selection

    def get_values(self, env: Environment) -> list[str]:
        selection = self._get_selection()
        if isinstance(selection, str) or callable(selection):
            selection = call_hook(
                selection, env[self.model_name].with_context(lang="en_US")
            )
        return [value for value, _ in selection]

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if validate and self.validate:
            value = self.convert_to_cache(value, record)
        return super().convert_to_column(value, record, values, validate)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> str | None:
        if not validate or not self.validate or self._selection is None:
            return value or None
        if value in self._selection:
            return value
        if not value:
            return None
        raise ValueError(f"Wrong value for {self}: {value!r}")

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> str:
        for item in self._description_selection(record.env):
            if item[0] == value:
                return item[1]
        return value or ""
