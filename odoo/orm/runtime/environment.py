import functools
import logging
import typing
from collections import defaultdict
from collections.abc import Collection, Mapping, MutableMapping

from psycopg import ProgrammingError

from odoo.db import BaseCursor
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.libs.accel import rows_to_dicts as _rows_to_dicts
from odoo.libs.datetime import timezone as get_timezone
from odoo.libs.datetime import utc
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    SQL,
    OrderedSet,
    clean_context,
    frozendict,
    reset_cached_properties,
)
from odoo.tools.misc import ReadonlyDict
from odoo.tools.translate import (
    LazyGettext,
    get_translated_module,
    get_translation,
)

from .registry import Registry
from .transaction import Transaction

if typing.TYPE_CHECKING:
    from datetime import tzinfo

    from .._protocols import (
        DecimalPrecisionProtocol,
        IrAttachmentProtocol,
        IrConfigParameterProtocol,
        IrCronProtocol,
        IrDefaultProtocol,
        IrModelAccessProtocol,
        IrModelConstraintProtocol,
        IrModelDataProtocol,
        IrModelFieldsProtocol,
        IrModelFieldsSelectionProtocol,
        IrModelInheritProtocol,
        IrModelProtocol,
        IrModelRelationProtocol,
        IrModuleModuleProtocol,
        IrRuleProtocol,
        IrUiViewProtocol,
        ResCountryProtocol,
        ResLangProtocol,
        ResUsersProtocol,
    )
    from .._typing import BaseModel, Field
    from ..components.core import OrmCore
    from ..primitives import IdType
    from .backend import StorageBackend

    M = typing.TypeVar("M", bound=BaseModel)

_logger = logging.getLogger("odoo.api")
_debug = DebugLog(__name__)
_MISSING = object()


class _Protecting:
    __slots__ = ("_active", "_core", "_records", "_what")

    def __init__(self, core: OrmCore[Field], what, records) -> None:
        self._core = core
        self._what = what
        self._records = records
        self._active = False

    def __enter__(self) -> None:
        what = self._what
        if not what:
            return
        core = self._core
        core.push_protection()
        self._active = True
        records = self._records
        if records is not None:
            ids = frozenset(records._ids)
            for field in what:
                core.protect(field, ids)
            return
        ids_by_field = defaultdict(list)
        for fields, what_records in what:
            for field in fields:
                ids_by_field[field].extend(what_records._ids)
        for field, rec_ids in ids_by_field.items():
            core.protect(field, frozenset(rec_ids))

    def __exit__(self, *exc: object) -> None:
        if self._active:
            self._active = False
            self._core.pop_protection()


class Environment(Mapping[str, "BaseModel"]):
    cr: BaseCursor
    uid: int | None
    context: frozendict
    su: bool
    transaction: Transaction

    def __new__(cls, cr: BaseCursor, uid: int | None, context: dict, su: bool = False):
        if not isinstance(cr, BaseCursor):
            raise TypeError(
                f"Environment(cr=...) expected BaseCursor, got {type(cr).__name__}"
            )
        if isinstance(uid, bool):
            raise TypeError(
                f"Environment(uid=...) expected int, None or a request "
                f"placeholder, got bool ({uid!r})"
            )
        transaction = cr.transaction
        if transaction is None:
            transaction = cr.transaction = Transaction(Registry(cr.dbname))
            _debug.lifecycle(
                "environment.transaction_attached", db=cr.dbname, uid=uid, su=su
            )
        return transaction.environment(cr, uid, context, su)

    @classmethod
    def _interned(
        cls,
        transaction: Transaction,
        cr: BaseCursor,
        uid: int | None,
        context: frozendict,
        su: bool,
    ) -> Environment:
        self = object.__new__(cls)
        self.cr, self.uid, self.su = cr, uid, su
        self.context = context
        self.transaction = transaction
        return self

    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name in vars(self):
            raise AttributeError(
                f"Attribute {name!r} is read-only, call `env()` instead"
            )
        return super().__setattr__(name, value)

    def __contains__(self, model_name) -> bool:
        return model_name in self.registry

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["decimal.precision"]
    ) -> DecimalPrecisionProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.attachment"]
    ) -> IrAttachmentProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.config_parameter"]
    ) -> IrConfigParameterProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.cron"]
    ) -> IrCronProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.default"]
    ) -> IrDefaultProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model"]
    ) -> IrModelProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.access"]
    ) -> IrModelAccessProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.constraint"]
    ) -> IrModelConstraintProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.data"]
    ) -> IrModelDataProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.fields"]
    ) -> IrModelFieldsProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.fields.selection"]
    ) -> IrModelFieldsSelectionProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.inherit"]
    ) -> IrModelInheritProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.model.relation"]
    ) -> IrModelRelationProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.module.module"]
    ) -> IrModuleModuleProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.rule"]
    ) -> IrRuleProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["ir.ui.view"]
    ) -> IrUiViewProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["res.country"]
    ) -> ResCountryProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["res.lang"]
    ) -> ResLangProtocol: ...

    @typing.overload
    def __getitem__(  # type: ignore[overload-overlap]
        self, model_name: typing.Literal["res.users"]
    ) -> ResUsersProtocol: ...

    @typing.overload
    def __getitem__(self, model_name: str) -> BaseModel: ...

    def __getitem__(self, model_name: str) -> typing.Any:
        rs = object.__new__(self.registry[model_name])
        rs.env = self
        rs._ids = ()
        rs._prefetch_ids = ()
        return rs

    def __iter__(self):
        return iter(self.registry)

    def __len__(self):
        return len(self.registry)

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return object.__hash__(self)

    def __call__(
        self,
        cr: BaseCursor | None = None,
        user: int | BaseModel | None = None,
        context: dict | None = None,
        su: bool | None = None,
    ) -> Environment:
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)
        if context is None:
            context = self.context
            # keep the frozendict itself when there is nothing to strip: the
            # transaction then matches the last environment by identity and
            # reuses its cached hash instead of copying and rehashing
            if su and not self.su and any(k.startswith("default_") for k in context):
                context = clean_context(context)
                if _debug.logic.enabled:
                    _debug.logic(
                        "environment.sudo_context_cleaned",
                        uid=uid,
                        keys=len(self.context) - len(context),
                    )
        su = (user is None and self.su) if su is None else su
        return Environment(cr, uid, context, su)

    @typing.overload
    def ref(
        self, xml_id: str, raise_if_not_found: typing.Literal[True] = True
    ) -> BaseModel: ...

    @typing.overload
    def ref(
        self, xml_id: str, raise_if_not_found: typing.Literal[False]
    ) -> BaseModel | None: ...

    def ref(self, xml_id: str, raise_if_not_found: bool = True) -> BaseModel | None:
        res_model, res_id = self.registry.xmlids.target(
            self, xml_id, raise_if_not_found
        )

        if res_model and res_id:
            record = self[res_model].browse(res_id)
            ref_cache = self.transaction._ref_cache
            cache_key = (res_model, res_id)
            if ref_cache.get(cache_key) or record.exists():
                ref_cache[cache_key] = True
                return record
            _debug.logic(
                "environment.ref.record_missing",
                xml_id=xml_id,
                model=res_model,
                res_id=res_id,
                raise_if_not_found=raise_if_not_found,
            )
            if raise_if_not_found:
                raise ValueError(
                    f"No record found for unique ID {xml_id}. It may have been deleted."
                )
        return None

    def is_superuser(self) -> bool:
        return self.su

    def is_admin(self) -> bool:
        return self.su or self.user._is_admin()

    def is_system(self) -> bool:
        return self.su or self.user._is_system()

    @functools.cached_property
    def registry(self) -> Registry:
        return self.transaction.registry

    @functools.cached_property
    def cache(self):
        return self.transaction.cache

    @functools.cached_property
    def core(self) -> OrmCore[Field]:
        return self.transaction.core

    @property
    def backend(self) -> StorageBackend:
        return self.transaction.backend

    @functools.cached_property
    def user(self) -> ResUsersProtocol:
        return self(su=True)["res.users"].browse(self.uid)

    def _get_allowed_company_ids(self) -> list[int]:
        company_ids = self.context.get("allowed_company_ids", [])
        if company_ids and not self.su:
            if set(company_ids) - set(self.user._get_company_ids()):
                _debug.logic(
                    "environment.company.unauthorized",
                    uid=self.uid,
                    allowed=company_ids,
                    user_companies=self.user._get_company_ids(),
                )
                raise AccessError(
                    self._("Access to unauthorized or invalid companies.")
                )
        return company_ids

    @functools.cached_property
    def company(self) -> BaseModel:
        if company_ids := self._get_allowed_company_ids():
            return self["res.company"].browse(company_ids[0])
        _debug.logic("environment.company.fallback_to_user", uid=self.uid)
        return self.user.company_id.with_env(self)

    @functools.cached_property
    def companies(self) -> BaseModel:
        if company_ids := self._get_allowed_company_ids():
            return self["res.company"].browse(company_ids)
        _debug.logic("environment.companies.fallback_to_user", uid=self.uid)
        user_company_ids = list(self.user._get_company_ids())
        current = self.user.company_id.id
        if current in user_company_ids:
            user_company_ids.remove(current)
            user_company_ids.insert(0, current)
        return self["res.company"].browse(user_company_ids)

    def _access_scope(self) -> typing.Any:
        if self.su:
            return True
        if company_ids := self.context.get("allowed_company_ids"):
            _debug.logic(
                "environment.access_scope.from_context",
                uid=self.uid,
                companies=len(company_ids),
            )
            return (self.uid, tuple(sorted(company_ids)))
        try:
            scope = (self.uid, tuple(sorted(self.user._get_company_ids())))
        except MissingError:
            _debug.logic("environment.access_scope.user_missing", uid=self.uid)
            return (self.uid, None)
        _debug.logic(
            "environment.access_scope.from_user",
            uid=self.uid,
            companies=len(scope[1]),
        )
        return scope

    @functools.cached_property
    def tz(self) -> tzinfo:
        tz_name = self.context.get("tz") or self.user.tz
        if tz_name:
            try:
                return get_timezone(tz_name)
            except Exception:
                _logger.debug("Invalid timezone %r", tz_name, exc_info=True)
                _debug.logic("environment.tz.invalid", uid=self.uid, tz=tz_name)
        return utc

    @functools.cached_property
    def lang(self) -> str | None:
        lang = self.context.get("lang")
        if (
            lang
            and lang != "en_US"
            and not self.registry.locale.is_lang_installed(self, lang)
        ):
            raise UserError(  # noqa: E8505  see above: this one cannot be translated
                f"Invalid language code: {lang}"
            )
        return lang or None

    @functools.cached_property
    def _lang(self) -> str:
        context = self.context
        lang = self.lang or "en_US"
        if context.get("edit_translations") or context.get("check_translations"):
            lang = "_" + lang
        return lang

    def _(self, source: str | LazyGettext, *args, **kwargs) -> str:
        lang = self.lang or "en_US"
        if isinstance(source, str):
            if args and kwargs:
                raise TypeError("Use args or kwargs, not both")
            format_args = args or kwargs
        elif isinstance(source, LazyGettext):
            if args or kwargs:
                raise TypeError("All args should come from the lazy text")
            return source._translate(lang)
        else:
            raise TypeError(f"Cannot translate {source!r}")
        if lang == "en_US":
            return get_translation("base", "en_US", source, format_args)
        try:
            module = get_translated_module(2)
            return get_translation(module, lang, source, format_args)
        except Exception as exc:
            _debug.logic(
                "environment.translation_failed",
                lang=lang,
                error=type(exc).__name__,
            )
            _logger.debug(
                'translation went wrong for "%r", skipped',
                source,
                exc_info=True,
            )
        return source

    def clear(self) -> None:
        _debug.lifecycle("environment.clear", uid=self.uid)
        reset_cached_properties(self)
        self.transaction.clear()

    def invalidate_all(
        self, flush: bool = True, *, keep_new_records: bool = False
    ) -> None:
        _debug.lifecycle("environment.invalidate_all", uid=self.uid, flush=flush)
        if flush:
            self.flush_all()
        self.transaction.invalidate_field_data(keep_new_records=keep_new_records)

    def flush_all(self) -> None:
        self.transaction.flush(self)

    def is_protected(self, field: Field, record: BaseModel) -> bool:
        return self.core.is_protected(field, record.id)

    def protecting(self, what, records=None) -> _Protecting:
        return _Protecting(self.core, what, records)

    def fields_to_compute(self) -> Collection[Field]:
        return self.core.get_pending_fields()

    def get_records_to_compute(self, field: Field) -> BaseModel:
        return self[field.model_name].browse(self.core.get_pending_ids(field))

    def is_to_compute(self, field: Field, record: BaseModel) -> bool:
        return self.core.is_pending(field, record.id)

    def add_to_compute(self, field: Field, records: BaseModel) -> None:
        if not records:
            return
        assert field.store and field.compute, (
            "Cannot add to recompute no-store or no-computed field"
        )
        _debug.pipeline(
            "environment.to_compute_added",
            model=field.model_name,
            field=field.name,
            records=len(records),
        )
        self.core.schedule(field, records._ids)

    def remove_to_compute(self, field: Field, records: BaseModel) -> None:
        if not records:
            return
        self.core.mark_done(field, records._ids)

    def get_cache_key(self, field: Field) -> typing.Any:

        def get(key, get_context=self.context.get):
            if key == "company":
                return self.company.id
            elif key == "uid":
                return self.uid if field.compute_sudo else (self.uid, self.su)
            elif key == "access":
                return None if field.compute else self._access_scope()
            elif key == "lang":
                return get_context("lang") or "en_US"
            elif key == "active_test":
                return get_context(
                    "active_test", field.context.get("active_test", True)
                )
            elif key.startswith("bin_size"):
                return bool(get_context(key))
            else:
                val = get_context(key)
                if type(val) is list:
                    val = tuple(val)
                try:
                    hash(val)
                except TypeError:
                    raise TypeError(
                        "Can only create cache keys from hashable values, "
                        f"got non-hashable value {val!r} at context key {key!r} "
                        f"(dependency of field {field})"
                    ) from None
                else:
                    return val

        return tuple(get(key) for key in self._field_depends_context[field])

    @functools.cached_property
    def _derived_envs(self) -> dict[tuple, Environment]:
        return {}

    def _derive(self, *, su: bool | None = None, **overrides) -> Environment:
        # sudo().with_context(key=value) as the ORM's own hot paths spell it
        # (trigger traversal, monetary rounding): the answer for a given
        # environment never changes, and each lookup would hash a fresh
        # context, so it is memoized per environment
        key = (su, tuple(sorted(overrides.items())))
        env = self._derived_envs.get(key)
        if env is None:
            env = self if su is None or su == self.su else self(su=su)
            if any(env.context.get(k, _MISSING) != v for k, v in overrides.items()):
                env = env(context=dict(env.context, **overrides))
            self._derived_envs[key] = env
        return env

    @functools.cached_property
    def _field_cache_memo(
        self,
    ) -> dict[Field, MutableMapping[IdType, typing.Any]]:
        return {}

    @functools.cached_property
    def _context_defaults(self) -> Mapping[str, typing.Any]:
        return ReadonlyDict(
            {
                key[8:]: value
                for key, value in self.context.items()
                if key.startswith("default_")
            }
        )

    @functools.cached_property
    def _field_depends_context(self):
        return self.registry.field_depends_context

    def flush_query(self, query: SQL) -> None:
        fields_to_flush = tuple(query.to_flush)
        if not fields_to_flush:
            return

        _debug.pipeline(
            "environment.flush_query",
            fields=len(fields_to_flush),
            first=f"{fields_to_flush[0].model_name}.{fields_to_flush[0].name}",
        )
        first = fields_to_flush[0]
        first_model = first.model_name
        single_model = len(fields_to_flush) == 1 or all(
            f.model_name == first_model for f in fields_to_flush
        )
        if single_model and not self.registry[first_model]._table_inheritance_root:
            self[first_model].flush_model([f.name for f in fields_to_flush])
            return

        fnames_to_flush = defaultdict[str, OrderedSet[str]](OrderedSet)
        for field in fields_to_flush:
            fnames_to_flush[field.model_name].add(field.name)
        for model_name, field_names in list(fnames_to_flush.items()):
            # a query on a table-inheritance root reads the rows every model
            # of the tree writes, each through its own field cache
            for tree_model_name in self._table_inheritance_tree(model_name):
                fnames_to_flush[tree_model_name].update(
                    name
                    for name in field_names
                    if name in self[tree_model_name]._fields
                )
        for model_name, field_names in fnames_to_flush.items():
            self[model_name].flush_model(field_names)

    def _table_inheritance_tree(self, model_name: str) -> tuple[str, ...]:
        # A root UPDATE reaches the rows of every table inheriting from it and
        # a leaf SELECT reads the rows the root writes, so the tree is the
        # same set of models seen from any of its members.
        root = self.registry[model_name]._table_inheritance_root
        if not root:
            return ()
        return tuple(
            name
            for name in self.registry.model_names_by_inheritance_root.get(root, ())
            if name != model_name
        )

    def execute_query(self, query: SQL) -> list[tuple]:
        if not isinstance(query, SQL):
            raise TypeError(f"execute_query expected SQL, got {type(query).__name__}")
        self.flush_query(query)
        self.cr.execute(query)  # noqa: E8501  query is checked to be SQL above
        try:
            return self.cr.fetchall()
        except ProgrammingError as exc:
            if exc.sqlstate is not None:
                raise
            _debug.logic("environment.execute_query.no_result_set", uid=self.uid)
            return []

    def execute_query_dict(self, query: SQL) -> list[dict]:
        rows = self.execute_query(query)
        if not rows:
            return []
        description = self.cr.description
        if description is None:
            raise RuntimeError(
                "No cr.description, the executed query does not return a table."
            )
        cols = tuple(col.name for col in description)
        return _rows_to_dicts(cols, rows)
