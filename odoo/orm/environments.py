# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo API module defines Odoo Environments.
"""
from __future__ import annotations

import functools
import logging
import pytz
import typing
import warnings
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager, suppress
from pprint import pformat
from weakref import WeakSet

from odoo.exceptions import AccessError, UserError, CacheMiss
from odoo.sql_db import BaseCursor
from odoo.tools import clean_context, frozendict, reset_cached_properties, OrderedSet, Query, SQL
from odoo.tools.translate import get_translation, get_translated_module, LazyGettext
from odoo.tools.misc import StackMap, SENTINEL

from .registry import Registry
from .utils import SUPERUSER_ID

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator, MutableMapping
    from datetime import tzinfo
    from .identifiers import IdType, NewId
    from .types import BaseModel, Field

    M = typing.TypeVar('M', bound=BaseModel)

_logger = logging.getLogger('odoo.api')

MAX_FIXPOINT_ITERATIONS = 10


class Environment(Mapping[str, "BaseModel"]):
    """ The environment stores various contextual data used by the ORM:

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
        """ Reset the transaction, see :meth:`Transaction.reset`. """
        warnings.warn("Since 19.0, use directly `transaction.reset()`", DeprecationWarning)
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
        for env in transaction.envs:
            if env.cr is cr and env.uid == uid and env.su == su and env.context == context:
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        self.cr, self.uid, self.su = cr, uid, su
        self.context = frozendict(context)
        self.transaction = transaction

        transaction.envs.add(self)
        # the default transaction's environment is the first one with a valid uid
        if transaction.default_env is None and uid and isinstance(uid, int):
            transaction.default_env = self
        return self

    def __setattr__(self, name: str, value: typing.Any) -> None:
        # once initialized, attributes are read-only
        if name in vars(self):
            raise AttributeError(f"Attribute {name!r} is read-only, call `env()` instead")
        return super().__setattr__(name, value)

    #
    # Mapping methods
    #

    def __contains__(self, model_name) -> bool:
        """ Test whether the given model exists. """
        return model_name in self.registry

    def __getitem__(self, model_name: str) -> BaseModel:
        """ Return an empty recordset from the given model. """
        return self.registry[model_name](self, (), ())

    def __iter__(self):
        """ Return an iterator on model names. """
        return iter(self.registry)

    def __len__(self):
        """ Return the size of the model registry. """
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
        """ Return an environment based on ``self`` with modified parameters.

        :param cr: optional database cursor to change the current cursor
        :type cursor: :class:`~odoo.sql_db.Cursor`
        :param user: optional user/user id to change the current user
        :type user: int or :class:`res.users record<~odoo.addons.base.models.res_users.ResUsers>`
        :param dict context: optional context dictionary to change the current context
        :param bool su: optional boolean to change the superuser mode
        :returns: environment with specified args (new or existing one)
        """
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)  # type: ignore
        if context is None:
            context = clean_context(self.context) if su and not self.su else self.context
        su = (user is None and self.su) if su is None else su
        return Environment(cr, uid, context, su)

    @typing.overload
    def ref(self, xml_id: str, raise_if_not_found: typing.Literal[True] = True) -> BaseModel:
        ...

    @typing.overload
    def ref(self, xml_id: str, raise_if_not_found: typing.Literal[False]) -> BaseModel | None:
        ...

    def ref(self, xml_id: str, raise_if_not_found: bool = True) -> BaseModel | None:
        """ Return the record corresponding to the given ``xml_id``.

        :param str xml_id: record xml_id, under the format ``<module.id>``
        :param bool raise_if_not_found: whether the method should raise if record is not found
        :returns: Found record or None
        :raise ValueError: if record wasn't found and ``raise_if_not_found`` is True
        """
        res_model, res_id = self['ir.model.data']._xmlid_to_res_model_res_id(
            xml_id, raise_if_not_found=raise_if_not_found
        )

        if res_model and res_id:
            record = self[res_model].browse(res_id)
            if record.exists():
                return record
            if raise_if_not_found:
                raise ValueError('No record found for unique ID %s. It may have been deleted.' % (xml_id))
        return None

    def is_superuser(self) -> bool:
        """ Return whether the environment is in superuser mode. """
        return self.su

    def is_admin(self) -> bool:
        """ Return whether the current user has group "Access Rights", or is in
            superuser mode. """
        return self.su or self.user._is_admin()

    def is_system(self) -> bool:
        """ Return whether the current user has group "Settings", or is in
            superuser mode. """
        return self.su or self.user._is_system()

    @functools.cached_property
    def registry(self) -> Registry:
        """Return the registry associated with the transaction."""
        return self.transaction.registry

    @functools.cached_property
    def _protected(self):
        """Return the protected map of the transaction."""
        return self.transaction.protected

    @functools.cached_property
    def cache(self):
        """Return the cache object of the transaction."""
        return self.transaction.cache

    @functools.cached_property
    def user(self) -> BaseModel:
        """Return the current user (as an instance).

        :returns: current user - sudoed
        :rtype: :class:`res.users record<~odoo.addons.base.models.res_users.ResUsers>`"""
        return self(su=True)['res.users'].browse(self.uid)

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
        company_ids = self.context.get('allowed_company_ids', [])
        if company_ids:
            if not self.su:
                user_company_ids = self.user._get_company_ids()
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(self._("Access to unauthorized or invalid companies."))
            return self['res.company'].browse(company_ids[0])
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
        company_ids = self.context.get('allowed_company_ids', [])
        user_company_ids = self.user._get_company_ids()
        if company_ids:
            if not self.su:
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(self._("Access to unauthorized or invalid companies."))
            return self['res.company'].browse(company_ids)
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
        return self['res.company'].browse(user_company_ids)

    @functools.cached_property
    def tz(self) -> tzinfo:
        """Return the current timezone info, defaults to UTC."""
        timezone = self.context.get('tz') or self.user.tz
        if timezone:
            try:
                return pytz.timezone(timezone)
            except Exception:  # noqa: BLE001
                _logger.debug("Invalid timezone %r", timezone, exc_info=True)
        return pytz.utc

    @functools.cached_property
    def lang(self) -> str | None:
        """Return the current language code."""
        lang = self.context.get('lang')
        if lang and lang != 'en_US' and not self['res.lang']._get_data(code=lang):
            # cannot translate here because we do not have a valid language
            raise UserError(f'Invalid language code: {lang}')  # pylint: disable=missing-gettext
        return lang or None

    @functools.cached_property
    def _lang(self) -> str:
        """Return the technical language code of the current context for **model_terms** translated field
        """
        context = self.context
        lang = self.lang or 'en_US'
        if context.get('edit_translations') or context.get('check_translations'):
            lang = '_' + lang
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
        lang = self.lang or 'en_US'
        if isinstance(source, str):
            assert not (args and kwargs), "Use args or kwargs, not both"
            format_args = args or kwargs
        elif isinstance(source, LazyGettext):
            # translate a lazy text evaluation
            assert not args and not kwargs, "All args should come from the lazy text"
            return source._translate(lang)
        else:
            raise TypeError(f"Cannot translate {source!r}")
        if lang == 'en_US':
            # we ignore the module as en_US is not translated
            return get_translation('base', 'en_US', source, format_args)
        try:
            module = get_translated_module(2)
            return get_translation(module, lang, source, format_args)
        except Exception:  # noqa: BLE001
            _logger.debug('translation went wrong for "%r", skipped', source, exc_info=True)
        return source

    def clear(self) -> None:
        """ Clear all record caches, and discard all fields to recompute.
            This may be useful when recovering from a failed ORM operation.
        """
        reset_cached_properties(self)
        self.transaction.clear()

    def invalidate_all(self, flush: bool = True) -> None:
        """ Invalidate the cache of all records.

        :param flush: whether pending updates should be flushed before invalidation.
            It is ``True`` by default, which ensures cache consistency.
            Do not use this parameter unless you know what you are doing.
        """
        if flush:
            self.flush_all()
        self.transaction.invalidate_field_data()

    def _recompute_all(self) -> None:
        """ Process all pending computations. """
        for _ in range(MAX_FIXPOINT_ITERATIONS):
            # fields to compute on real records (new records are not recomputed)
            fields_ = [field for field, ids in self.transaction.tocompute.items() if any(ids)]
            if not fields_:
                break
            for field in fields_:
                self[field.model_name]._recompute_field(field)
        else:
            _logger.warning("Too many iterations for recomputing fields!")

    def flush_all(self) -> None:
        """ Flush all pending computations and updates to the database. """
        for _ in range(MAX_FIXPOINT_ITERATIONS):
            self._recompute_all()
            model_names = OrderedSet(field.model_name for field in self._field_dirty)
            if not model_names:
                break
            for model_name in model_names:
                self[model_name].flush_model()
        else:
            _logger.warning("Too many iterations for flushing fields!")

    def is_protected(self, field: Field, record: BaseModel) -> bool:
        """ Return whether `record` is protected against invalidation or
            recomputation for `field`.
        """
        return record.id in self._protected.get(field, ())

    def protected(self, field: Field) -> BaseModel:
        """ Return the recordset for which ``field`` should not be invalidated or recomputed. """
        return self[field.model_name].browse(self._protected.get(field, ()))

    @typing.overload
    def protecting(self, what: Collection[Field], records: BaseModel) -> typing.ContextManager[None]:
        ...

    @typing.overload
    def protecting(self, what: Collection[tuple[Collection[Field], BaseModel]]) -> typing.ContextManager[None]:
        ...

    @contextmanager
    def protecting(self, what, records=None) -> Iterator[None]:
        """ Prevent the invalidation or recomputation of fields on records.
        The parameters are either:

        - ``what`` a collection of fields and ``records`` a recordset, or
        - ``what`` a collection of pairs ``(fields, records)``.
        """
        protected = self._protected
        try:
            protected.pushmap()
            if records is not None:  # convert first signature to second one
                what = [(what, records)]
            ids_by_field = defaultdict(list)
            for fields, what_records in what:
                for field in fields:
                    ids_by_field[field].extend(what_records._ids)

            for field, rec_ids in ids_by_field.items():
                ids = protected.get(field)
                protected[field] = ids.union(rec_ids) if ids else frozenset(rec_ids)
            yield
        finally:
            protected.popmap()

    def fields_to_compute(self) -> Collection[Field]:
        """ Return a view on the field to compute. """
        return self.transaction.tocompute.keys()

    def records_to_compute(self, field: Field) -> BaseModel:
        """ Return the records to compute for ``field``. """
        ids = self.transaction.tocompute.get(field, ())
        return self[field.model_name].browse(ids)

    def is_to_compute(self, field: Field, record: BaseModel) -> bool:
        """ Return whether ``field`` must be computed on ``record``. """
        return record.id in self.transaction.tocompute.get(field, ())

    def not_to_compute(self, field: Field, records: BaseModel) -> BaseModel:
        """ Return the subset of ``records`` for which ``field`` must not be computed. """
        ids = self.transaction.tocompute.get(field, ())
        return records.browse(id_ for id_ in records._ids if id_ not in ids)

    def add_to_compute(self, field: Field, records: BaseModel) -> None:
        """ Mark ``field`` to be computed on ``records``. """
        if not records:
            return
        assert field.store and field.compute, "Cannot add to recompute no-store or no-computed field"
        self.transaction.tocompute[field].update(records._ids)

    def remove_to_compute(self, field: Field, records: BaseModel) -> None:
        """ Mark ``field`` as computed on ``records``. """
        if not records:
            return
        ids = self.transaction.tocompute.get(field, None)
        if ids is None:
            return
        ids.difference_update(records._ids)
        if not ids:
            del self.transaction.tocompute[field]

    def cache_key(self, field: Field) -> typing.Any:
        """ Return the cache key of the given ``field``. """
        def get(key, get_context=self.context.get):
            if key == 'company':
                return self.company.id
            elif key == 'uid':
                return self.uid if field.compute_sudo else (self.uid, self.su)
            elif key == 'lang':
                return get_context('lang') or None
            elif key == 'active_test':
                return get_context('active_test', field.context.get('active_test', True))
            elif key.startswith('bin_size'):
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
    def _field_cache_memo(self) -> dict[Field, MutableMapping[IdType, typing.Any]]:
        """Memo for `Field._get_cache(env)`.  Do not use it."""
        return {}

    @functools.cached_property
    def _field_dirty(self):
        """ Map fields to set of dirty ids. """
        return self.transaction.field_dirty

    @functools.cached_property
    def _field_depends_context(self):
        return self.registry.field_depends_context

    def flush_query(self, query: SQL) -> None:
        """ Flush all the fields in the metadata of ``query``. """
        fields_to_flush = tuple(query.to_flush)
        if not fields_to_flush:
            return

        fnames_to_flush = defaultdict[str, OrderedSet[str]](OrderedSet)
        for field in fields_to_flush:
            fnames_to_flush[field.model_name].add(field.name)
        for model_name, field_names in fnames_to_flush.items():
            self[model_name].flush_model(field_names)

    def execute_query(self, query: SQL) -> list[tuple]:
        """ Execute the given query, fetch its result and it as a list of tuples
        (or an empty list if no result to fetch).  The method automatically
        flushes all the fields in the metadata of the query.
        """
        assert isinstance(query, SQL)
        self.flush_query(query)
        self.cr.execute(query)
        return [] if self.cr.description is None else self.cr.fetchall()

    def execute_query_dict(self, query: SQL) -> list[dict]:
        """ Execute the given query, fetch its results as a list of dicts.
        The method automatically flushes fields in the metadata of the query.
        """
        rows = self.execute_query(query)
        if not rows:
            return []
        description = self.cr.description
        assert description is not None, "No cr.description, the executed query does not return a table."
        return [
            {column.name: row[index] for index, column in enumerate(description)}
            for row in rows
        ]


class Transaction:
    """ A object holding ORM data structures for a transaction. """
    __slots__ = (
        '_Transaction__file_open_tmp_paths', 'cache',
        'default_env', 'envs', 'field_data', 'field_data_patches', 'field_dirty',
        'protected', 'registry', 'tocompute',
    )

    def __init__(self, registry: Registry):
        self.registry = registry
        # weak OrderedSet of environments
        self.envs = WeakSet[Environment]()
        self.envs.data = OrderedSet()  # type: ignore[attr-defined]
        # default environment (for flushing)
        self.default_env: Environment | None = None

        # cache data {field: cache_data_managed_by_field} often uses a dict
        # to store a mapping from id to a value, but fields may use this field
        # however they need
        self.field_data = defaultdict["Field", typing.Any](dict)
        # {field: set[id]} stores the fields and ids that are changed in the
        # cache, but not yet written in the database; their changed values are
        # in `data`
        self.field_dirty = defaultdict["Field", OrderedSet["IdType"]](OrderedSet)
        # {field: {record_id: ids}} record ids to be added to the values of
        # x2many fields if they are not in cache yet
        self.field_data_patches = defaultdict["Field", defaultdict["IdType", list["IdType"]]](lambda: defaultdict(list))
        # fields to protect {field: ids}
        self.protected = StackMap["Field", OrderedSet["IdType"]]()
        # pending computations {field: ids}
        self.tocompute = defaultdict["Field", OrderedSet["IdType"]](OrderedSet)
        # backward-compatible view of the cache
        self.cache = Cache(self)

        # temporary directories (managed in odoo.tools.file_open_temporary_directory)
        self.__file_open_tmp_paths = ()  # type: ignore # noqa: PLE0237

    def flush(self) -> None:
        """ Flush pending computations and updates in the transaction. """
        if self.default_env is not None:
            self.default_env.flush_all()
        else:
            for env in self.envs:
                _logger.warning("Missing default_env, flushing as public user")
                public_user = env.ref('base.public_user')
                Environment(env.cr, public_user.id, {}).flush_all()
                break

    def clear(self):
        """ Clear the caches and pending computations and updates in the transactions. """
        self.invalidate_field_data()
        self.field_data_patches.clear()
        self.field_dirty.clear()
        self.tocompute.clear()
        for env in self.envs:
            env.cr.cache.clear()
            break  # all envs of the transaction share the same cursor

    def reset(self) -> None:
        """ Reset the transaction.  This clears the transaction, and reassigns
            the registry on all its environments.  This operation is strongly
            recommended after reloading the registry.
        """
        self.registry = Registry(self.registry.db_name)
        for env in self.envs:
            reset_cached_properties(env)
        self.clear()

    def invalidate_field_data(self) -> None:
        """ Invalidate the cache of all the fields.

        This operation is unsafe by default, and must be used with care.
        Indeed, invalidating a dirty field on a record may lead to an error,
        because doing so drops the value to be written in database.
        """
        self.field_data.clear()
        # reset Field._get_cache()
        for env in self.envs:
            with suppress(AttributeError):
                del env._field_cache_memo


# sentinel value for optional parameters
EMPTY_DICT = frozendict()  # type: ignore


class Cache:
    """ Implementation of the cache of records.

    For most fields, the cache is simply a mapping from a record and a field to
    a value.  In the case of context-dependent fields, the mapping also depends
    on the environment of the given record.  For the sake of performance, the
    cache is first partitioned by field, then by record.  This makes some
    common ORM operations pretty fast, like determining which records have a
    value for a given field, or invalidating a given field on all possible
    records.

    The cache can also mark some entries as "dirty".  Dirty entries essentially
    marks values that are different from the database.  They represent database
    updates that haven't been done yet.  Note that dirty entries only make
    sense for stored fields.  Note also that if a field is dirty on a given
    record, and the field is context-dependent, then all the values of the
    record for that field are considered dirty.  For the sake of consistency,
    the values that should be in the database must be in a context where all
    the field's context keys are ``None``.
    """
    __slots__ = ('transaction',)

    def __init__(self, transaction: Transaction):
        self.transaction = transaction

    def __repr__(self) -> str:
        # for debugging: show the cache content and dirty flags as stars
        data: dict[Field, dict] = {}
        for field, field_cache in sorted(self.transaction.field_data.items(), key=lambda item: str(item[0])):
            dirty_ids = self.transaction.field_dirty.get(field, ())
            if field in self.transaction.registry.field_depends_context:
                data[field] = {
                    key: {
                        Starred(id_) if id_ in dirty_ids else id_: val if field.type != 'binary' else '<binary>'
                        for id_, val in key_cache.items()
                    }
                    for key, key_cache in field_cache.items()
                }
            else:
                data[field] = {
                    Starred(id_) if id_ in dirty_ids else id_: val if field.type != 'binary' else '<binary>'
                    for id_, val in field_cache.items()
                }
        return repr(data)

    def _get_field_cache(self, model: BaseModel, field: Field) -> Mapping[IdType, typing.Any]:
        """ Return the field cache of the given field, but not for modifying it. """
        return self._set_field_cache(model, field)

    def _set_field_cache(self, model: BaseModel, field: Field) -> dict[IdType, typing.Any]:
        """ Return the field cache of the given field for modifying it. """
        return field._get_cache(model.env)

    def contains(self, record: BaseModel, field: Field) -> bool:
        """ Return whether ``record`` has a value for ``field``. """
        return record.id in self._get_field_cache(record, field)

    def contains_field(self, field: Field) -> bool:
        """ Return whether ``field`` has a value for at least one record. """
        cache = self.transaction.field_data.get(field)
        if not cache:
            return False
        # 'cache' keys are tuples if 'field' is context-dependent, record ids otherwise
        if field in self.transaction.registry.field_depends_context:
            return any(value for value in cache.values())
        return True

    def get(self, record: BaseModel, field: Field, default=SENTINEL):
        """ Return the value of ``field`` for ``record``. """
        try:
            field_cache = self._get_field_cache(record, field)
            return field_cache[record._ids[0]]
        except KeyError:
            if default is SENTINEL:
                raise CacheMiss(record, field) from None
            return default

    def set(self, record: BaseModel, field: Field, value: typing.Any, dirty: bool = False) -> None:
        """ Set the value of ``field`` for ``record``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        """
        field._update_cache(record, value, dirty=dirty)

    def update(self, records: BaseModel, field: Field, values: Iterable, dirty: bool = False) -> None:
        """ Set the values of ``field`` for several ``records``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        """
        for record, value in zip(records, values):
            field._update_cache(record, value, dirty=dirty)

    def update_raw(self, records: BaseModel, field: Field, values: Iterable, dirty: bool = False) -> None:
        """ This is a variant of method :meth:`~update` without the logic for
        translated fields.
        """
        if field.translate:
            records = records.with_context(prefetch_langs=True)
        for record, value in zip(records, values):
            field._update_cache(record, value, dirty=dirty)

    def insert_missing(self, records: BaseModel, field: Field, values: Iterable) -> None:
        """ Set the values of ``field`` for the records in ``records`` that
        don't have a value yet.  In other words, this does not overwrite
        existing values in cache.
        """
        warnings.warn("Since 19.0, use Field._insert_cache", DeprecationWarning)
        field._insert_cache(records, values)

    def patch(self, records: BaseModel, field: Field, new_id: NewId):
        """ Apply a patch to an x2many field on new records. The patch consists
        in adding new_id to its value in cache. If the value is not in cache
        yet, it will be applied once the value is put in cache with method
        :meth:`patch_and_set`.
        """
        warnings.warn("Since 19.0, this method is internal", DeprecationWarning)
        from .fields_relational import _RelationalMulti  # noqa: PLC0415
        assert isinstance(field, _RelationalMulti)
        value = records.env[field.comodel_name].browse((new_id,))
        field._update_inverse(records, value)

    def patch_and_set(self, record: BaseModel, field: Field, value: typing.Any) -> typing.Any:
        """ Set the value of ``field`` for ``record``, like :meth:`set`, but
        apply pending patches to ``value`` and return the value actually put
        in cache.
        """
        warnings.warn("Since 19.0, this method is internal", DeprecationWarning)
        field._update_cache(record, value)
        return self.get(record, field)

    def remove(self, record: BaseModel, field: Field) -> None:
        """ Remove the value of ``field`` for ``record``. """
        assert record.id not in self.transaction.field_dirty.get(field, ())
        try:
            field_cache = self._set_field_cache(record, field)
            del field_cache[record._ids[0]]
        except KeyError:
            pass

    def get_values(self, records: BaseModel, field: Field) -> Iterator[typing.Any]:
        """ Return the cached values of ``field`` for ``records``. """
        field_cache = self._get_field_cache(records, field)
        for record_id in records._ids:
            try:
                yield field_cache[record_id]
            except KeyError:
                pass

    def get_until_miss(self, records: BaseModel, field: Field) -> list[typing.Any]:
        """ Return the cached values of ``field`` for ``records`` until a value is not found. """
        warnings.warn("Since 19.0, this is managed directly by Field")
        field_cache = self._get_field_cache(records, field)
        vals = []
        for record_id in records._ids:
            try:
                vals.append(field_cache[record_id])
            except KeyError:
                break
        return vals

    def get_records_different_from(self, records: M, field: Field, value: typing.Any) -> M:
        """ Return the subset of ``records`` that has not ``value`` for ``field``. """
        warnings.warn("Since 19.0, becomes internal function of fields", DeprecationWarning)
        return field._filter_not_equal(records, value)

    def get_fields(self, record: BaseModel) -> Iterator[Field]:
        """ Return the fields with a value for ``record``. """
        for name, field in record._fields.items():
            if name != 'id' and record.id in self._get_field_cache(record, field):
                yield field

    def get_records(self, model: BaseModel, field: Field, all_contexts: bool = False) -> BaseModel:
        """ Return the records of ``model`` that have a value for ``field``.
        By default the method checks for values in the current context of ``model``.
        But when ``all_contexts`` is true, it checks for values *in all contexts*.
        """
        ids: Iterable
        if all_contexts and field in model.pool.field_depends_context:
            field_cache = self.transaction.field_data.get(field, EMPTY_DICT)
            ids = OrderedSet(id_ for sub_cache in field_cache.values() for id_ in sub_cache)
        else:
            ids = self._get_field_cache(model, field)
        return model.browse(ids)

    def get_missing_ids(self, records: BaseModel, field: Field) -> Iterator[IdType]:
        """ Return the ids of ``records`` that have no value for ``field``. """
        return field._cache_missing_ids(records)

    def get_dirty_fields(self) -> Collection[Field]:
        """ Return the fields that have dirty records in cache. """
        warnings.warn("Since 19.0, don't use Cache to manipulate dirty fields")
        return self.transaction.field_dirty.keys()

    def filtered_dirty_records(self, records: BaseModel, field: Field) -> BaseModel:
        """ Filtered ``records`` where ``field`` is dirty. """
        warnings.warn("Since 19.0, don't use Cache to manipulate dirty fields")
        dirties = self.transaction.field_dirty.get(field, ())
        return records.browse(id_ for id_ in records._ids if id_ in dirties)

    def filtered_clean_records(self, records: BaseModel, field: Field) -> BaseModel:
        """ Filtered ``records`` where ``field`` is not dirty. """
        warnings.warn("Since 19.0, don't use Cache to manipulate dirty fields")
        dirties = self.transaction.field_dirty.get(field, ())
        return records.browse(id_ for id_ in records._ids if id_ not in dirties)

    def has_dirty_fields(self, records: BaseModel, fields: Collection[Field] | None = None) -> bool:
        """ Return whether any of the given records has dirty fields.

        :param fields: a collection of fields or ``None``; the value ``None`` is
            interpreted as any field on ``records``
        """
        warnings.warn("Since 19.0, don't use Cache to manipulate dirty fields")
        if fields is None:
            return any(
                not ids.isdisjoint(records._ids)
                for field, ids in self.transaction.field_dirty.items()
                if field.model_name == records._name
            )
        else:
            return any(
                field in self.transaction.field_dirty and not self.transaction.field_dirty[field].isdisjoint(records._ids)
                for field in fields
            )

    def clear_dirty_field(self, field: Field) -> Collection[IdType]:
        """ Make the given field clean on all records, and return the ids of the
        formerly dirty records for the field.
        """
        warnings.warn("Since 19.0, don't use Cache to manipulate dirty fields")
        return self.transaction.field_dirty.pop(field, ())

    def invalidate(self, spec: Collection[tuple[Field, Collection[IdType] | None]] | None = None) -> None:
        """ Invalidate the cache, partially or totally depending on ``spec``.

        If a field is context-dependent, invalidating it for a given record
        actually invalidates all the values of that field on the record.  In
        other words, the field is invalidated for the record in all
        environments.

        This operation is unsafe by default, and must be used with care.
        Indeed, invalidating a dirty field on a record may lead to an error,
        because doing so drops the value to be written in database.

            spec = [(field, ids), (field, None), ...]
        """
        if spec is None:
            self.transaction.invalidate_field_data()
            return
        env = next(iter(self.transaction.envs))
        for field, ids in spec:
            field._invalidate_cache(env, ids)

    def clear(self):
        """ Invalidate the cache and its dirty flags. """
        self.transaction.invalidate_field_data()
        self.transaction.field_dirty.clear()
        self.transaction.field_data_patches.clear()

    def check(self, env: Environment) -> None:
        """ Check the consistency of the cache for the given environment. """
        depends_context = env.registry.field_depends_context
        invalids = []

        def process(model: BaseModel, field: Field, field_cache):
            # ignore new records and records to flush
            dirty_ids = self.transaction.field_dirty.get(field, ())
            ids = [id_ for id_ in field_cache if id_ and id_ not in dirty_ids]
            if not ids:
                return

            # select the column for the given ids
            query = Query(env, model._table, model._table_sql)
            sql_id = SQL.identifier(model._table, 'id')
            sql_field = model._field_to_sql(model._table, field.name, query)
            if field.type == 'binary' and (
                model.env.context.get('bin_size') or model.env.context.get('bin_size_' + field.name)
            ):
                sql_field = SQL('pg_size_pretty(length(%s)::bigint)', sql_field)
            query.add_where(SQL("%s IN %s", sql_id, tuple(ids)))
            env.cr.execute(query.select(sql_id, sql_field))

            # compare returned values with corresponding values in cache
            for id_, value in env.cr.fetchall():
                cached = field_cache[id_]
                if value == cached or (not value and not cached):
                    continue
                invalids.append((model.browse((id_,)), field, {'cached': cached, 'fetched': value}))

        for field, field_cache in self.transaction.field_data.items():
            # check column fields only
            if not field.store or not field.column_type or field.translate or field.company_dependent:
                continue

            model = env[field.model_name]
            if field in depends_context:
                for context_keys, inner_cache in field_cache.items():
                    context = dict[str, typing.Any](zip(depends_context[field], context_keys))
                    if 'company' in context:
                        # the cache key 'company' actually comes from context
                        # key 'allowed_company_ids' (see property env.company
                        # and method env.cache_key())
                        context['allowed_company_ids'] = [context.pop('company')]
                    process(model.with_context(context), field, inner_cache)
            else:
                process(model, field, field_cache)

        if invalids:
            _logger.warning("Invalid cache: %s", pformat(invalids))


class Starred:
    """ Simple helper class to ``repr`` a value with a star suffix. """
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.value!r}*"
