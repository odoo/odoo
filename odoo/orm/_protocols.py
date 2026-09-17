from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from odoo.exceptions import AccessError

    from .domain import Domain


class RecordsetProtocol(Protocol):
    id: Any
    _fields: Any

    def browse(self, ids: Any = ()) -> Any: ...

    def create(self, vals_list: Any) -> Any: ...

    def invalidate_model(
        self, fnames: Collection[str] | None = None, flush: bool = True
    ) -> None: ...

    def search(
        self,
        domain: Any,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> Any: ...

    def search_count(self, domain: Any, limit: int | None = None) -> int: ...

    def search_fetch(
        self,
        domain: Any,
        field_names: Sequence[str] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> Any: ...

    def search_read(
        self,
        domain: Any = None,
        fields: Sequence[str] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        **read_kwargs: Any,
    ) -> list[Any]: ...

    def sudo(self, flag: bool = True) -> Any: ...

    def with_context(self, ctx: Any = None, /, **overrides: Any) -> Any: ...

    def with_user(self, user: Any) -> Any: ...

    def write(self, vals: Any) -> Any: ...


class DecimalPrecisionProtocol(RecordsetProtocol, Protocol):
    def get_precision(self, application: str) -> int: ...


class IrModelDataProtocol(RecordsetProtocol, Protocol):
    def _load_xmlid(self, xml_id: str) -> Any: ...

    def _process_end(self, modules: list[str]) -> None: ...

    def _update_xmlids(
        self, data_list: list[dict[str, Any]], update: bool = False
    ) -> None: ...

    def _xmlid_to_res_model_res_id(
        self, xmlid: str, raise_if_not_found: bool = False
    ) -> tuple[Any, Any]: ...


class IrModelProtocol(RecordsetProtocol, Protocol):
    def _get(self, name: str) -> Any: ...

    def _get_manual_model_data(self) -> list[dict[str, Any]]: ...

    def _prepare_class_attrs(self, model_data: dict[str, Any]) -> dict[str, Any]: ...

    def _reflect_models(self, model_names: list[str]) -> None: ...


class IrModelFieldsProtocol(RecordsetProtocol, Protocol):
    def _get(self, model_name: str, name: str) -> Any: ...

    def _get_ids_by_name(self, model_name: str) -> dict[str, int]: ...

    def _get_manual_field_data(self, model_name: str) -> dict[str, Any]: ...

    def _is_field_ready(self, field_data: dict[str, Any]) -> bool: ...

    def _prepare_field_attrs(self, field_data: dict[str, Any]) -> dict[str, Any]: ...

    def _reflect_fields(self, model_names: list[str]) -> None: ...

    def get_field_help(self, model_name: str) -> dict[str, str | None]: ...

    def get_field_selection(
        self, model_name: str, field_name: str
    ) -> list[tuple[str, str]]: ...

    def get_field_string(self, model_name: str) -> dict[str, str]: ...


class IrModelConstraintProtocol(RecordsetProtocol, Protocol):
    def _reflect_constraint(
        self,
        model: Any,
        conname: str,
        type: str,
        definition: str,
        module: str,
        message: str | None = None,
    ) -> Any: ...

    def _reflect_constraints(self, model_names: list[str]) -> None: ...


class IrModelAccessProtocol(RecordsetProtocol, Protocol):
    def check(
        self, model: str, mode: str = "read", raise_exception: bool = True
    ) -> bool: ...

    def _prepare_access_error(self, model: str, mode: str) -> AccessError: ...


class IrRuleProtocol(RecordsetProtocol, Protocol):
    def _get_domain_accessible_records(
        self, model_name: str, mode: str = "read"
    ) -> Domain: ...

    def _prepare_access_error(self, operation: str, records: Any) -> AccessError: ...


class IrDefaultProtocol(RecordsetProtocol, Protocol):
    def _evaluate_condition_with_fallback(
        self, model_name: str, field_expr: str, operator: str, value: Any
    ) -> bool | None: ...

    def _get_field_column_fallbacks(self, model_name: str, field_name: str) -> str: ...

    def _get_model_defaults(
        self, model_name: str, condition: str | bool = False
    ) -> dict[str, Any]: ...


class IrAttachmentProtocol(RecordsetProtocol, Protocol):
    def _gc_file_store_unsafe(
        self, checklist: dict[str, Any] | None = None, grace: float | None = None
    ) -> int: ...

    def _get_content_checksum(self, bin_data: bytes) -> str: ...

    def _get_filestore(self) -> str: ...

    def _with_bin_size_disabled(self) -> Any: ...


class IrUiViewProtocol(RecordsetProtocol, Protocol):
    def _render_template(
        self, template: int | str, values: dict[str, Any] | None = None
    ) -> Any: ...

    def _get_custom_views(self, models: Any = None) -> Any: ...

    def _check_module_views(self, module: str) -> None: ...


class IrConfigParameterProtocol(RecordsetProtocol, Protocol):
    def init(self, force: bool = False) -> None: ...

    def get_param(self, key: str, default: str | bool = False) -> str | bool: ...

    def set_param(self, key: str, value: Any) -> str | bool: ...


class IrCronProtocol(RecordsetProtocol, Protocol):
    def _trigger(self, at: Any = None, *, coalesce: int = 0) -> Any: ...


class IrModelFieldsSelectionProtocol(RecordsetProtocol, Protocol):
    def _reflect_selections(self, model_names: list[str]) -> None: ...


class IrModelRelationProtocol(RecordsetProtocol, Protocol):
    def _reflect_relations(self, items: Any, *, model_tables: Any = ()) -> None: ...


class IrModelInheritProtocol(RecordsetProtocol, Protocol):
    def _reflect_inherits(self, model_names: list[str]) -> None: ...


class IrModuleModuleProtocol(RecordsetProtocol, Protocol):
    def _check(self) -> None: ...

    def _extract_resource_attachment_translations(
        self, module: Any, lang: Any
    ) -> Any: ...

    def _get_domain_modules_to_load(self) -> list[tuple[str, str, str]]: ...

    def _import_zipfile(
        self, module_file: Any, force: bool = False, with_demo: bool = False
    ) -> Any: ...

    def _update_translations(
        self, filter_lang: Any = None, overwrite: bool = False
    ) -> None: ...

    def get_values_from_terp(self, terp: Any) -> dict[str, Any]: ...

    def update_list(self) -> Any: ...


class ResCountryProtocol(RecordsetProtocol, Protocol):
    code: Any
    currency_id: Any


class ResLangProtocol(RecordsetProtocol, Protocol):
    def _get_data(self, **kwargs: Any) -> Any: ...

    def _get_lang_cached(self, code: str) -> Any: ...

    def get_installed(self) -> list[tuple[str, str]]: ...


class ResUsersProtocol(RecordsetProtocol, Protocol):
    company_id: Any
    company_ids: Any
    lang: Any
    tz: Any

    def _check_uid_passwd(self, uid: int, passwd: str) -> None: ...

    def _get_session_token(self, sid: str) -> str | bool: ...

    def _get_company_ids(self) -> tuple[int, ...]: ...

    def _has_group(self, group_ext_id: str) -> bool: ...

    def _is_admin(self) -> bool: ...

    def _is_public(self) -> bool: ...

    def _is_system(self) -> bool: ...

    def authenticate(
        self, credential: dict[str, Any], user_agent_env: dict[str, Any]
    ) -> dict[str, Any]: ...

    def context_get(self) -> Any: ...

    def has_group(self, group_ext_id: str) -> bool: ...

    def has_groups(self, group_spec: str) -> bool: ...


FRAMEWORK_MODEL_PROTOCOLS: dict[str, type] = {
    "decimal.precision": DecimalPrecisionProtocol,
    "ir.attachment": IrAttachmentProtocol,
    "ir.config_parameter": IrConfigParameterProtocol,
    "ir.cron": IrCronProtocol,
    "ir.default": IrDefaultProtocol,
    "ir.model": IrModelProtocol,
    "ir.model.access": IrModelAccessProtocol,
    "ir.model.constraint": IrModelConstraintProtocol,
    "ir.model.data": IrModelDataProtocol,
    "ir.model.fields": IrModelFieldsProtocol,
    "ir.model.fields.selection": IrModelFieldsSelectionProtocol,
    "ir.model.inherit": IrModelInheritProtocol,
    "ir.model.relation": IrModelRelationProtocol,
    "ir.module.module": IrModuleModuleProtocol,
    "ir.rule": IrRuleProtocol,
    "ir.ui.view": IrUiViewProtocol,
    "res.country": ResCountryProtocol,
    "res.lang": ResLangProtocol,
    "res.users": ResUsersProtocol,
}
