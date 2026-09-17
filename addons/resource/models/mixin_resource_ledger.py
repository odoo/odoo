from typing import Any

from odoo import api, models
from odoo.fields import Domain
from odoo.models import ValuesType


class MixinResourceLedger(models.AbstractModel):
    _name = "mixin.resource.ledger"
    _description = "Resource Ledger Mixin"

    @api.model
    def _get_fields_projection_key(self) -> tuple[str, ...]:
        return ("resource_id",)

    @api.model
    def _get_domain_projection(self, record: models.BaseModel) -> Domain:
        return Domain(
            [("res_model", "=", record._name), ("res_id", "=", record.id)],
        )

    def _get_projection_key(self, vals: ValuesType | None = None) -> tuple[Any, ...]:
        if vals is None:
            return tuple(
                self._fields[fname].convert_to_write(self[fname], self)
                for fname in self._get_fields_projection_key()
            )
        return tuple(
            vals.get(fname) or False for fname in self._get_fields_projection_key()
        )

    @api.model
    def _prepare_projection_link_vals(self, record: models.BaseModel) -> ValuesType:
        return {"res_model": record._name, "res_id": record.id}

    @api.model
    def _sync_projection(
        self,
        record: models.BaseModel,
        vals_list: list[ValuesType],
        existing: models.BaseModel | None = None,
    ) -> models.BaseModel:
        """Reconcile this ledger's rows for `record` with `vals_list`."""
        if not record.id or not isinstance(record.id, int):
            return self.browse()

        if existing is None:
            existing = (
                self.sudo()
                .with_context(active_test=False)
                .search(self._get_domain_projection(record))
            )

        if not vals_list:
            existing.sudo().unlink()
            return self.browse()

        existing_by_key = {}
        for row in existing:
            existing_by_key.setdefault(row._get_projection_key(), []).append(row)
        link_vals = self._prepare_projection_link_vals(record)
        to_create = []

        for vals in vals_list:
            base_vals = {**vals, **link_vals}
            if "active" in self._fields:
                base_vals.setdefault("active", True)
            bucket = existing_by_key.get(self._get_projection_key(base_vals))
            if bucket:
                row = bucket.pop(0)
                changed_vals = {
                    fname: value
                    for fname, value in base_vals.items()
                    if row._fields[fname].convert_to_write(row[fname], row) != value
                }
                if changed_vals:
                    row.sudo().write(changed_vals)
            else:
                to_create.append(base_vals)

        to_delete = self.browse().union(
            *(row for bucket in existing_by_key.values() for row in bucket)
        )
        if to_delete:
            to_delete.sudo().unlink()
        created = self.sudo().create(to_create) if to_create else self.browse()
        return (existing - to_delete) | created
