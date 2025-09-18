"""
Environment manipulation mixin for BaseModel.

This module contains methods for creating recordsets in different environments:
with_env, sudo, with_user, with_company, with_context, with_prefetch.
"""

import typing
import warnings
from collections.abc import Reversible
from typing import Self

from ... import decorators as api
from ..._typing import IdType, ValuesType
from ...helpers import OriginIds, _origin_ids
from ...primitives import NewId

if typing.TYPE_CHECKING:
    from ...runtime import Environment


class EnvironmentMixin:
    """Mixin providing environment manipulation methods for recordsets.

    This mixin contains methods for:
    - Creating recordsets in different environments (with_env)
    - Superuser mode (sudo)
    - User switching (with_user)
    - Company switching (with_company)
    - Context manipulation (with_context)
    - Prefetch configuration (with_prefetch)
    - Record conversion and utility methods
    """

    __slots__ = ()

    @api.private
    def ensure_one(self) -> Self:
        """Verify that the current recordset holds a single record.

        :raise odoo.exceptions.ValueError: ``len(self) != 1``
        """
        try:
            # unpack to ensure there is only one value is faster than len when true and
            # has a significant impact as this check is largely called
            (_id,) = self._ids
            return self
        except ValueError:
            raise ValueError(f"Expected singleton: {self}")

    @api.private
    def with_env(self, env: Environment) -> Self:
        """Return a new version of this recordset attached to the provided environment.

        .. note::
            The returned recordset has the same prefetch object as ``self``.
        """
        rs = object.__new__(self.__class__)
        rs.env = env
        rs._ids = self._ids
        rs._prefetch_ids = self._prefetch_ids
        return rs

    @api.private
    def sudo(self, flag: bool = True) -> Self:
        """Return a new version of this recordset with superuser mode enabled or
        disabled, depending on `flag`. The superuser mode does not change the
        current user, and simply bypasses access rights checks.

        .. warning::

            Using ``sudo`` could cause data access to cross the
            boundaries of record rules, possibly mixing records that
            are meant to be isolated (e.g. records from different
            companies in multi-company environments).

            It may lead to un-intuitive results in methods which select one
            record among many - for example getting the default company, or
            selecting a Bill of Materials.

        .. note::

            The returned recordset has the same prefetch object as ``self``.

        """
        assert isinstance(flag, bool)
        if flag == self.env.su:
            return self
        return self.with_env(self.env(su=flag))

    @api.private
    def with_user(self, user) -> Self:
        """Return a new version of this recordset attached to the given user, in
        non-superuser mode, unless `user` is the superuser (by convention, the
        superuser is always in superuser mode.)
        """
        if not user:
            return self
        return self.with_env(self.env(user=user, su=False))

    @api.private
    def with_company(self, company) -> Self:
        """Return a new version of this recordset with a modified context, such that::

            result.env.company = company
            result.env.companies = self.env.companies | company

        .. warning::

            When using an unauthorized company for current user,
            accessing the company(ies) on the environment may trigger
            an AccessError if not done in a sudoed environment.
        """
        if not company:
            # With company = None/False/0/[]/empty recordset: keep current environment
            return self

        company_id = int(company)
        allowed_company_ids = self.env.context.get("allowed_company_ids") or []
        if allowed_company_ids and company_id == allowed_company_ids[0]:
            return self
        # Copy the allowed_company_ids list
        # to avoid modifying the context of the current environment.
        allowed_company_ids = list(allowed_company_ids)
        if company_id in allowed_company_ids:
            allowed_company_ids.remove(company_id)
        allowed_company_ids.insert(0, company_id)

        return self.with_context(allowed_company_ids=allowed_company_ids)

    @api.private
    def with_context(
        self, ctx: dict[str, typing.Any] | None = None, /, **overrides
    ) -> Self:
        """Return a new version of this recordset attached to an extended
        context.

        The extended context is either the provided ``context`` in which
        ``overrides`` are merged or the *current* context in which
        ``overrides`` are merged e.g.::

            # current context is {'key1': True}
            r2 = records.with_context({}, key2=True)
            # -> r2.env.context is {'key2': True}
            r2 = records.with_context(key2=True)
            # -> r2.env.context is {'key1': True, 'key2': True}

        .. note:

            The returned recordset has the same prefetch object as ``self``.
        """  # noqa: RST210
        context = dict(ctx if ctx is not None else self.env.context, **overrides)
        if "force_company" in context:
            warnings.warn(
                "Since 19.0, context key 'force_company' is no longer supported. "
                "Use with_company(company) instead.",
                DeprecationWarning, stacklevel=2,
            )
        if "company" in context:
            warnings.warn(
                "Context key 'company' is not recommended, because "
                "of its special meaning in @depends_context.", stacklevel=2,
            )
        if (
            "allowed_company_ids" not in context
            and "allowed_company_ids" in self.env.context
        ):
            # Force 'allowed_company_ids' to be kept when context is overridden
            # without 'allowed_company_ids'
            context["allowed_company_ids"] = self.env.context["allowed_company_ids"]
        return self.with_env(self.env(context=context))

    @api.private
    def with_prefetch(self, prefetch_ids: Reversible[IdType] | None = None) -> Self:
        """Return a new version of this recordset that uses the given prefetch ids,
        or ``self``'s ids if not given.
        """
        if prefetch_ids is None:
            prefetch_ids = self._ids
        rs = object.__new__(self.__class__)
        rs.env = self.env
        rs._ids = self._ids
        rs._prefetch_ids = prefetch_ids
        return rs

    def _update_cache(self, values: ValuesType, validate: bool = True) -> None:
        """Update the cache of ``self`` with ``values``.

        :param values: dict of field values, in any format.
        :param validate: whether values must be checked
        """
        self.ensure_one()
        fields = self._fields
        try:
            field_values = [
                (fields[name], value) for name, value in values.items() if name != "id"
            ]
        except KeyError as e:
            raise ValueError(f"Invalid field {e.args[0]!r} on model {self._name!r}")

        # convert monetary fields after other columns for correct value rounding
        for field, value in sorted(
            field_values, key=lambda item: item[0].write_sequence
        ):
            value = field.convert_to_cache(value, self, validate)
            field._update_cache(self, value)

            # set inverse fields on new records in the comodel
            if field.relational:
                inv_recs = self[field.name].filtered(lambda r: not r.id)
                if not inv_recs:
                    continue
                # we need to adapt the value of the inverse fields to integrate self into it:
                # x2many fields should add self, while many2one fields should replace with self
                for invf in self.pool.field_inverses[field]:
                    invf._update_inverse(inv_recs, self)

    def _convert_to_record(self, values):
        """Convert the ``values`` dictionary from the cache format to the
        record format.
        """
        return {
            name: self._fields[name].convert_to_record(value, self)
            for name, value in values.items()
        }

    def _convert_to_write(self, values):
        """Convert the ``values`` dictionary into the format of :meth:`write`."""
        fields = self._fields
        result = {}
        for name, value in values.items():
            if name in fields:
                field = fields[name]
                value = field.convert_to_write(value, self)
                if not isinstance(value, NewId):
                    result[name] = value
        return result

    #
    # New records - represent records that do not exist in the database yet;
    # they are used to perform onchanges.
    #

    @api.model
    @api.private
    def new(
        self,
        values: ValuesType | None = None,
        origin: Self | None = None,
        ref: str | None = None,
    ) -> Self:
        """Return a new record instance attached to the current environment and
        initialized with the provided ``value``. The record is *not* created
        in database, it only exists in memory.

        One can pass an ``origin`` record, which is the actual record behind the
        result. It is retrieved as ``record._origin``. Two new records with the
        same origin record are considered equal.

        One can also pass a ``ref`` value to identify the record among other new
        records. The reference is encapsulated in the ``id`` of the record.
        """
        if values is None:
            values = {}
        if origin is not None:
            origin = origin.id
        record = self.browse((NewId(origin, ref),))
        record._update_cache(values, validate=False)

        return record

    @property
    def _origin(self) -> Self:
        """Return the actual records corresponding to ``self``."""
        if all(self._ids):
            return self  # already real records
        ids = tuple(_origin_ids(self._ids))
        prefetch_ids = _origin_ids(self._prefetch_ids)
        rs = object.__new__(self.__class__)
        rs.env = self.env
        rs._ids = ids
        rs._prefetch_ids = prefetch_ids
        return rs
