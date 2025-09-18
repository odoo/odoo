"""The Odoo ORM Environment — request-scoped context."""

import functools
import logging
import time
import typing
import warnings
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager
from weakref import ref as weakref_ref

from psycopg import ProgrammingError

from odoo.db import BaseCursor
from odoo.exceptions import AccessError, UserError
from odoo.libs.datetime import utc
from odoo.libs.datetime.tz import timezone as get_timezone
from odoo.tools import (
    SQL,
    OrderedSet,
    Query,
    clean_context,
    frozendict,
    reset_cached_properties,
)
from odoo.tools.translate import (
    LazyGettext,
    get_translated_module,
    get_translation,
)

from ..components.core import OrmCore

# Rust-accelerated rows→dicts conversion (see cursor.py for details).
try:
    from odoo_rust import rows_to_dicts as _rows_to_dicts
except ImportError:
    _rows_to_dicts = None
from collections.abc import Collection, Iterator, MutableMapping
from datetime import tzinfo

from ..primitives import SUPERUSER_ID
from .registry import Registry
from .transaction import MAX_FIXPOINT_ITERATIONS, Transaction

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, Field
    from ..primitives import IdType, NewId

    M = typing.TypeVar("M", bound=BaseModel)

_logger = logging.getLogger("odoo.api")
_orm_cache = logging.getLogger("odoo.orm.cache")


class Environment(Mapping[str, "BaseModel"]):
    """The environment stores various contextual data used by the ORM:

    - :attr:`cr`: the current database cursor (for database queries);
    - :attr:`uid`: the current user id (for access rights checks);
    - :attr:`context`: the current context dictionary (arbitrary metadata);
    - :attr:`su`: whether in superuser mode.

    It provides access to the registry by implementing a mapping from model
    names to models. It also holds a cache for records, and a data
    structure to manage recomputations.
    """

    cr: BaseCursor
    uid: int
    context: frozendict
    su: bool
    transaction: Transaction

    def reset(self) -> None:
        """Reset the transaction, see :meth:`Transaction.reset`."""
        warnings.warn(
            "Since 19.0, use directly `transaction.reset()`", DeprecationWarning, stacklevel=2
        )
        self.transaction.reset()

    def __new__(cls, cr: BaseCursor, uid: int, context: dict, su: bool = False):
        assert isinstance(cr, BaseCursor)
        if uid == SUPERUSER_ID:
            su = True

        # determine transaction object
        transaction = cr.transaction
        if transaction is None:
            transaction = cr.transaction = Transaction(Registry(cr.dbname))

        # if env already exists, return it
        # Fast path: check last returned env (covers repeated with_user/sudo calls)
        _last_ref = transaction._last_env
        _last = _last_ref() if _last_ref is not None else None
        if (
            _last is not None
            and _last.cr is cr
            and _last.uid == uid
            and _last.su == su
            and (_last.context is context or _last.context == context)
        ):
            return _last
        for env in transaction.envs:
            if (
                env.cr is cr
                and env.uid == uid
                and env.su == su
                and (env.context is context or env.context == context)
            ):
                transaction._last_env = weakref_ref(env)
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        self.cr, self.uid, self.su = cr, uid, su
        self.context = (
            context if isinstance(context, frozendict) else frozendict(context)
        )
        self.transaction = transaction

        transaction.envs.add(self)
        transaction._last_env = weakref_ref(self)
        # the default transaction's environment is the first one with a valid uid
        if transaction.default_env is None and uid and isinstance(uid, int):
            transaction.default_env = self
        return self

    def __setattr__(self, name: str, value: typing.Any) -> None:
        # once initialized, attributes are read-only
        if name in vars(self):
            raise AttributeError(
                f"Attribute {name!r} is read-only, call `env()` instead"
            )
        return super().__setattr__(name, value)

    #
    # Mapping methods
    #

    def __contains__(self, model_name) -> bool:
        """Test whether the given model exists."""
        return model_name in self.registry

    def __getitem__(self, model_name: str) -> BaseModel:
        """Return an empty recordset from the given model."""
        # Inline object.__new__ + slot assignment avoids the __init__
        # function dispatch overhead (~50-80ns per call).  Equivalent to
        # ``self.registry[model_name](self, (), ())``.
        rs = object.__new__(self.registry[model_name])
        rs.env = self
        rs._ids = ()
        rs._prefetch_ids = ()
        return rs

    def __iter__(self):
        """Return an iterator on model names."""
        return iter(self.registry)

    def __len__(self):
        """Return the size of the model registry."""
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
        user: IdType | BaseModel | None = None,
        context: dict | None = None,
        su: bool | None = None,
    ) -> Environment:
        """Return an environment based on ``self`` with modified parameters.

        :param cr: optional database cursor to change the current cursor
        :type cursor: :class:`~odoo.db.Cursor`
        :param user: optional user/user id to change the current user
        :type user: int or :class:`res.users record<~odoo.addons.base.models.res_users.ResUsers>`
        :param dict context: optional context dictionary to change the current context
        :param bool su: optional boolean to change the superuser mode
        :returns: environment with specified args (new or existing one)
        """
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)  # type: ignore
        if context is None:
            context = (
                clean_context(self.context) if su and not self.su else self.context
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
        """Return the record corresponding to the given ``xml_id``.

        :param str xml_id: record xml_id, under the format ``<module.id>``
        :param bool raise_if_not_found: whether the method should raise if record is not found
        :returns: Found record or None
        :raise ValueError: if record wasn't found and ``raise_if_not_found`` is True
        """
        res_model, res_id = self["ir.model.data"]._xmlid_to_res_model_res_id(
            xml_id, raise_if_not_found=raise_if_not_found
        )

        if res_model and res_id:
            record = self[res_model].browse(res_id)
            # Use per-transaction cache to skip repeated exists() queries
            # for the same (model, id). Cleared by invalidate_all/invalidate_field_data.
            ref_cache = self.transaction._ref_cache
            cache_key = (res_model, res_id)
            if cache_key in ref_cache:
                if ref_cache[cache_key]:
                    return record
                # record was previously checked and did not exist
            elif record.exists():
                ref_cache[cache_key] = True
                return record
            else:
                ref_cache[cache_key] = False
            if raise_if_not_found:
                raise ValueError(
                    f"No record found for unique ID {xml_id}. It may have been deleted."
                )
        return None

    def is_superuser(self) -> bool:
        """Return whether the environment is in superuser mode."""
        return self.su

    def is_admin(self) -> bool:
        """Return whether the current user has group "Access Rights", or is in
        superuser mode."""
        return self.su or self.user._is_admin()

    def is_system(self) -> bool:
        """Return whether the current user has group "Settings", or is in
        superuser mode."""
        return self.su or self.user._is_system()

    @functools.cached_property
    def registry(self) -> Registry:
        """Return the registry associated with the transaction."""
        return self.transaction.registry

    @functools.cached_property
    def cache(self):
        """Return the legacy cache wrapper of the transaction.

        .. deprecated:: 19.0
            Use ``env._core`` for cache operations instead.  The only
            remaining use case for ``env.cache`` is the ``check()``
            method which validates cache-vs-database consistency in tests.
        """
        return self.transaction.cache

    @functools.cached_property
    def _core(self) -> OrmCore:
        """Layer 1 facade — flat API over cache + compute.

        Internal ORM consumers use this instead of navigating the
        ``transaction.cache_store`` / ``transaction.compute_engine``
        attribute chains::

            # Before (3 attr lookups + method):
            env.transaction.compute_engine.has_pending_field(field)

            # After (1 attr lookup + method):
            env._core.has_pending(field)
        """
        return self.transaction.core

    @functools.cached_property
    def user(self) -> BaseModel:
        """Return the current user (as an instance).

        :returns: current user - sudoed
        :rtype: :class:`res.users record<~odoo.addons.base.models.res_users.ResUsers>`
        """
        return self(su=True)["res.users"].browse(self.uid)

    @functools.cached_property
    def company(self) -> BaseModel:
        """Return the current company (as an instance).

        If not specified in the context (`allowed_company_ids`),
        fallback on current user main company.

        :raise AccessError: invalid or unauthorized `allowed_company_ids` context key content.
        :return: current company (default=`self.user.company_id`), with the current environment
        :rtype: :class:`res.company record<~odoo.addons.base.models.res_company.Company>`

        .. warning::

            No sanity checks applied in sudo mode!
            When in sudo mode, a user can access any company,
            even if not in his allowed companies.

            This allows to trigger inter-company modifications,
            even if the current user doesn't have access to
            the targeted company.
        """
        company_ids = self.context.get("allowed_company_ids", [])
        if company_ids:
            if not self.su:
                user_company_ids = self.user._get_company_ids()
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(
                        self._("Access to unauthorized or invalid companies.")
                    )
            return self["res.company"].browse(company_ids[0])
        return self.user.company_id.with_env(self)

    @functools.cached_property
    def companies(self) -> BaseModel:
        """Return a recordset of the enabled companies by the user.

        If not specified in the context(`allowed_company_ids`),
        fallback on current user companies.

        :raise AccessError: invalid or unauthorized `allowed_company_ids` context key content.
        :return: current companies (default=`self.user.company_ids`), with the current environment
        :rtype: :class:`res.company recordset<~odoo.addons.base.models.res_company.Company>`

        .. warning::

            No sanity checks applied in sudo mode !
            When in sudo mode, a user can access any company,
            even if not in his allowed companies.

            This allows to trigger inter-company modifications,
            even if the current user doesn't have access to
            the targeted company.
        """
        company_ids = self.context.get("allowed_company_ids", [])
        user_company_ids = self.user._get_company_ids()
        if company_ids:
            if not self.su:
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(
                        self._("Access to unauthorized or invalid companies.")
                    )
            return self["res.company"].browse(company_ids)
        # By setting the default companies to all user companies instead of the main one
        # we save a lot of potential trouble in all "out of context" calls, such as
        # /mail/redirect or /web/image, etc. And it is not unsafe because the user does
        # have access to these other companies. The risk of exposing foreign records
        # (wrt to the context) is low because all normal RPCs will have a proper
        # allowed_company_ids.
        # Examples:
        #   - when printing a report for several records from several companies
        #   - when accessing to a record from the notification email template
        #   - when loading an binary image on a template
        return self["res.company"].browse(user_company_ids)

    @functools.cached_property
    def tz(self) -> tzinfo:
        """Return the current timezone info, defaults to UTC."""
        tz_name = self.context.get("tz") or self.user.tz
        if tz_name:
            try:
                return get_timezone(tz_name)
            except Exception:
                _logger.debug("Invalid timezone %r", tz_name, exc_info=True)
        return utc

    @functools.cached_property
    def lang(self) -> str | None:
        """Return the current language code."""
        lang = self.context.get("lang")
        if lang and lang != "en_US" and not self["res.lang"]._get_data(code=lang):
            # cannot translate here because we do not have a valid language
            raise UserError(  # pylint: disable=missing-gettext,E8507
                f"Invalid language code: {lang}"
            )
        return lang or None

    @functools.cached_property
    def _lang(self) -> str:
        """Return the technical language code of the current context for **model_terms** translated field"""
        context = self.context
        lang = self.lang or "en_US"
        if context.get("edit_translations") or context.get("check_translations"):
            lang = "_" + lang
        return lang

    def _(self, source: str | LazyGettext, *args, **kwargs) -> str:
        """Translate the term using current environment's language.

        Usage:

        ```
        self.env._("hello world")  # dynamically get module name
        self.env._("hello %s", "test")
        self.env._(LAZY_TRANSLATION)
        ```

        :param source: String to translate or lazy translation
        :param ...: args or kwargs for templating
        :return: The transalted string
        """
        lang = self.lang or "en_US"
        if isinstance(source, str):
            assert not (args and kwargs), "Use args or kwargs, not both"
            format_args = args or kwargs
        elif isinstance(source, LazyGettext):
            # translate a lazy text evaluation
            assert not args and not kwargs, "All args should come from the lazy text"
            return source._translate(lang)
        else:
            raise TypeError(f"Cannot translate {source!r}")
        if lang == "en_US":
            # we ignore the module as en_US is not translated
            return get_translation("base", "en_US", source, format_args)
        try:
            module = get_translated_module(2)
            return get_translation(module, lang, source, format_args)
        except Exception:
            _logger.debug(
                'translation went wrong for "%r", skipped',
                source,
                exc_info=True,
            )
        return source

    def clear(self) -> None:
        """Clear all record caches, and discard all fields to recompute.
        This may be useful when recovering from a failed ORM operation.
        """
        reset_cached_properties(self)
        self.transaction.clear()

    def invalidate_all(self, flush: bool = True) -> None:
        """Invalidate the cache of all records.

        :param flush: whether pending updates should be flushed before invalidation.
            It is ``True`` by default, which ensures cache consistency.
            Do not use this parameter unless you know what you are doing.
        """
        if flush:
            self.flush_all()
        self.transaction.invalidate_field_data()

    def flush_all(self) -> None:
        """Flush all pending computations and updates to the database.

        Delegates the convergence loop to :class:`UnitOfWork`, which
        encapsulates the fixpoint algorithm: recompute → flush → repeat.

        Each flush may trigger new computations (via ``modified()`` in
        write), which may dirty more fields, requiring another iteration.
        The :class:`UnitOfWork` component detects stalls and reports them
        via :class:`LoopResult`; this method handles error policy
        (``tolerant_recompute`` context key) and debug logging.
        """
        _debug = _orm_cache.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

        def recompute_fn(field):
            self[field.model_name]._recompute_field(field)

        def flush_fn(model_names):
            with self.cr.pipeline():
                for model_name in model_names:
                    self[model_name].flush_model()

        result = self.transaction.unit_of_work.run_flush_loop(recompute_fn, flush_fn)

        if not result.converged:
            remaining = result.stalled_fields
            if self.context.get("tolerant_recompute"):
                _logger.error(
                    "flush_all() did not converge after %d iterations. "
                    "Stalled fields: %s (tolerant mode, continuing)",
                    result.iterations,
                    remaining,
                )
            else:
                raise RuntimeError(
                    f"flush_all() did not converge after "
                    f"{result.iterations} iterations.  "
                    f"Stalled fields: {remaining}\n\n"
                    f"This indicates a circular compute or flush dependency.  "
                    f"Use context key 'tolerant_recompute' to suppress."
                )

        if _debug:
            _t_end = time.perf_counter()
            _orm_cache.debug(
                "[%.3f ms] flush_all: %d iterations",
                (_t_end - _t0) * 1000,
                result.iterations,
            )

    def is_protected(self, field: Field, record: BaseModel) -> bool:
        """Return whether `record` is protected against invalidation or
        recomputation for `field`.
        """
        return self._core.is_protected(field, record.id)

    def protected(self, field: Field) -> BaseModel:
        """Return the recordset for which ``field`` should not be invalidated or recomputed."""
        return self[field.model_name].browse(self._core.protected_ids(field))

    @typing.overload
    def protecting(
        self, what: Collection[Field], records: BaseModel
    ) -> typing.ContextManager[None]: ...

    @typing.overload
    def protecting(
        self, what: Collection[tuple[Collection[Field], BaseModel]]
    ) -> typing.ContextManager[None]: ...

    @contextmanager
    def protecting(self, what, records=None) -> Iterator[None]:
        """Prevent the invalidation or recomputation of fields on records.
        The parameters are either:

        - ``what`` a collection of fields and ``records`` a recordset, or
        - ``what`` a collection of pairs ``(fields, records)``.
        """
        # Fast path: nothing to protect — skip push/pop overhead entirely.
        # Common for simple writes (no inverse, no editable computed fields).
        if not what:
            yield
            return
        core = self._core
        try:
            core.push_protection()
            if records is not None:
                # Fast path: single (fields, records) pair — the common case
                # from write(). Avoids creating defaultdict + intermediate lists.
                ids = frozenset(records._ids)
                for field in what:
                    core.protect(field, ids)
            else:
                ids_by_field = defaultdict(list)
                for fields, what_records in what:
                    for field in fields:
                        ids_by_field[field].extend(what_records._ids)
                for field, rec_ids in ids_by_field.items():
                    core.protect(field, frozenset(rec_ids))
            yield
        finally:
            core.pop_protection()

    def fields_to_compute(self) -> Collection[Field]:
        """Return a view on the field to compute."""
        return self._core.pending_fields()

    def records_to_compute(self, field: Field) -> BaseModel:
        """Return the records to compute for ``field``."""
        return self[field.model_name].browse(self._core.pending_ids(field))

    def is_to_compute(self, field: Field, record: BaseModel) -> bool:
        """Return whether ``field`` must be computed on ``record``."""
        return self._core.is_pending(field, record.id)

    def not_to_compute(self, field: Field, records: BaseModel) -> BaseModel:
        """Return the subset of ``records`` for which ``field`` must not be computed."""
        pending = self._core.pending_ids(field)
        return records.browse(id_ for id_ in records._ids if id_ not in pending)

    def add_to_compute(self, field: Field, records: BaseModel) -> None:
        """Mark ``field`` to be computed on ``records``."""
        if not records:
            return
        assert (
            field.store and field.compute
        ), "Cannot add to recompute no-store or no-computed field"
        self._core.schedule(field, records._ids)

    def remove_to_compute(self, field: Field, records: BaseModel) -> None:
        """Mark ``field`` as computed on ``records``."""
        if not records:
            return
        self._core.mark_done(field, records._ids)

    def cache_key(self, field: Field) -> typing.Any:
        """Return the cache key of the given ``field``."""

        def get(key, get_context=self.context.get):
            if key == "company":
                return self.company.id
            elif key == "uid":
                return self.uid if field.compute_sudo else (self.uid, self.su)
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
                    ) from None  # we don't need to chain the exception created 2 lines above
                else:
                    return val

        return tuple(get(key) for key in self.registry.field_depends_context[field])

    @functools.cached_property
    def _field_cache_memo(
        self,
    ) -> dict[Field, MutableMapping[IdType, typing.Any]]:
        """Memo for `Field._get_cache(env)`.  Do not use it."""
        return {}

    @functools.cached_property
    def _field_depends_context(self):
        return self.registry.field_depends_context

    def flush_query(self, query: SQL) -> None:
        """Flush all the fields in the metadata of ``query``."""
        fields_to_flush = tuple(query.to_flush)
        if not fields_to_flush:
            return

        # Fast path: single model (very common — most queries touch one table)
        first = fields_to_flush[0]
        if len(fields_to_flush) == 1:
            self[first.model_name].flush_model([first.name])
            return
        first_model = first.model_name
        if all(f.model_name == first_model for f in fields_to_flush):
            self[first_model].flush_model([f.name for f in fields_to_flush])
            return

        # Multi-model: group by model
        fnames_to_flush = defaultdict[str, OrderedSet[str]](OrderedSet)
        for field in fields_to_flush:
            fnames_to_flush[field.model_name].add(field.name)
        for model_name, field_names in fnames_to_flush.items():
            self[model_name].flush_model(field_names)

    def execute_query(self, query: SQL) -> list[tuple]:
        """Execute the given query, fetch its result and it as a list of tuples
        (or an empty list if no result to fetch).  The method automatically
        flushes all the fields in the metadata of the query.
        """
        assert isinstance(query, SQL)
        self.flush_query(query)
        self.cr.execute(query)
        # In pipeline mode, cursor.description is not available until after
        # fetchall() syncs the pipeline.  Always attempt fetchall(); for
        # non-returning statements (INSERT/UPDATE without RETURNING) psycopg
        # raises ProgrammingError which we catch and return [].
        try:
            return self.cr.fetchall()
        except ProgrammingError:
            return []

    def execute_query_dict(self, query: SQL) -> list[dict]:
        """Execute the given query, fetch its results as a list of dicts.
        The method automatically flushes fields in the metadata of the query.
        """
        rows = self.execute_query(query)
        if not rows:
            return []
        description = self.cr.description
        assert (
            description is not None
        ), "No cr.description, the executed query does not return a table."
        cols = tuple(col.name for col in description)
        if _rows_to_dicts is not None:
            return _rows_to_dicts(cols, rows)
        return [dict(zip(cols, row, strict=False)) for row in rows]


# Re-export for backward compatibility (code using ``from .environment import Cache``)
from .cache_compat import Cache, Starred  # noqa: F401
