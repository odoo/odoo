from __future__ import annotations

import typing
from collections import defaultdict

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.func import classproperty
from odoo.tools.access_scan import (
    get_accessible_query,
    get_inaccessible_owners,
    prepare_column_fetcher,
    prepare_document_access_error,
    stable_order,
)

if typing.TYPE_CHECKING:
    from odoo.api import DomainType
    from odoo.tools import Query


class MixinOwnerAccess(models.AbstractModel):
    _name = "mixin.owner.access"
    _description = "Access Following an Owner Record"

    _access_owner_field: str = ""
    _SEARCH_ACCESS_CHUNK_MIN = 80
    _SEARCH_ACCESS_CHUNK_MAX = 8192

    @classproperty
    def _search_visibility_fields(self) -> tuple[str, ...]:
        return _owner_columns(self)

    def _access_owner_columns(self) -> tuple[str, ...]:
        return _owner_columns(type(self))

    def _access_owner_rows(self, rows: list[tuple]) -> list[tuple[int, str, int]]:
        field = self._fields[self._access_owner_field]
        if field.type == "many2one_reference":
            return [(id_, res_model, res_id) for id_, res_model, res_id in rows]
        return [(id_, field.comodel_name, res_id) for id_, res_id in rows]

    def _access_owners(self) -> list[tuple[int, str, int]]:
        columns = self._access_owner_columns()
        rows = [
            (record.id, *(record[column] for column in columns))
            for record in self.sudo()
        ]
        field = self._fields[self._access_owner_field]
        if field.type == "many2one":
            rows = [(id_, owner.id) for id_, owner in rows]
        return self._access_owner_rows(rows)

    def _access_forbidden_ids(
        self, owners: list[tuple[int, str, int]], operation: str
    ) -> list[int]:
        by_model = defaultdict(set)
        for _id, res_model, res_id in owners:
            by_model[res_model].add(res_id)
        unreachable = self._access_unreachable_owners(by_model, operation)
        return [
            id_
            for id_, res_model, res_id in owners
            if (res_model, res_id) in unreachable
        ]

    def _access_owner_operation(self, operation: str) -> str:
        return "read" if operation == "read" else "write"

    def _access_unreachable_owners(
        self, by_model: dict[str, set[int]], operation: str
    ) -> set[tuple[str, int]]:
        return set(
            get_inaccessible_owners(
                self.env, by_model, self._access_owner_operation(operation)
            )
        )

    @api.model
    def _access_owner_delegates(self) -> bool:
        # a many2one owner whose model states its whole access in ir.access is
        # read through the 'access' operator; a many2one_reference owner, or a
        # model that checks more in code, is scanned record by record
        field = self._fields.get(self._access_owner_field)
        if field is None or field.type != "many2one":
            return False
        comodel = type(self.env[field.comodel_name])
        return comodel._check_access is models.BaseModel._check_access

    @api.model
    def _access_guard(self, operation: str) -> Domain:
        guard = super()._access_guard(operation)
        if not self._access_owner_delegates():
            return guard
        field = self._fields[self._access_owner_field]
        owner = Domain(field.name, "=", False) | Domain(
            field.name, "access", self._access_owner_operation(operation)
        )
        if field.comodel_name == "res.users":
            owner |= Domain(field.name, "=", self.env.uid)
        return guard & owner

    def _check_access(self, operation: str) -> tuple | None:
        result = super()._check_access(operation)
        if not self or self.env.su or self._access_owner_delegates():
            return result
        candidates = self - result[0] if result else self
        forbidden = candidates._access_forbidden_ids(
            candidates._access_owners(), operation
        )
        if not forbidden:
            return result
        forbidden = self.browse(forbidden)
        if result:
            return (result[0] + forbidden, result[1])
        return (forbidden, lambda: prepare_document_access_error(forbidden, operation))

    def _search(
        self,
        domain: DomainType,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        *,
        bypass_access: bool = False,
        **kwargs,
    ) -> Query:
        if self.env.su or bypass_access:
            return super()._search(
                domain, offset, limit, stable_order(order), bypass_access=True, **kwargs
            )
        if self._access_owner_delegates():
            return super()._search(domain, offset, limit, order, **kwargs)

        def allowed(rows: list[tuple]) -> set[int]:
            owners = self._access_owner_rows(rows)
            forbidden = set(self._access_forbidden_ids(owners, "read"))
            return {row[0] for row in rows if row[0] not in forbidden}

        return get_accessible_query(
            self,
            domain,
            offset,
            limit,
            order,
            super()._search,
            fetch=prepare_column_fetcher(self, ("id", *self._access_owner_columns())),
            allowed=allowed,
            chunk_min=self._SEARCH_ACCESS_CHUNK_MIN,
            chunk_max=self._SEARCH_ACCESS_CHUNK_MAX,
            **kwargs,
        )

    @api.constrains(lambda self: self._access_owner_columns())
    def _constrains_the_owner_exists(self) -> None:
        for _id, res_model, res_id in self._access_owners():
            if res_model not in self.env:
                raise ValidationError(
                    self.env._("%(model)s is not a model.", model=res_model)
                )
            if res_id and not self.env[res_model].browse(res_id).exists():
                raise ValidationError(
                    self.env._(
                        "%(description)s must belong to an existing record.",
                        description=self._description,
                    )
                )

    @api.model
    def _of(self, records: models.BaseModel) -> models.BaseModel:
        if not records:
            return self.browse()
        columns = self._access_owner_columns()
        domain = [(columns[-1], "in", records.ids)]
        if len(columns) == 2:
            domain.append((columns[0], "=", records._name))
        return self.search(domain)

    def _owner(self) -> models.BaseModel | None:
        self.check_singleton()
        [(_id, res_model, res_id)] = self._access_owners()
        if not res_model or res_model not in self.env or not res_id:
            return None
        return self.env[res_model].browse(res_id).exists()


def _owner_columns(model_class: type) -> tuple[str, ...]:
    field = getattr(model_class, "_fields", {}).get(model_class._access_owner_field)
    if field is None:
        return ()
    if field.type == "many2one_reference":
        return (field.model_field, field.name)
    return (field.name,)
