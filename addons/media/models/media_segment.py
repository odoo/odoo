from __future__ import annotations

import typing
from collections import defaultdict
from itertools import pairwise

from odoo import api, fields, models
from odoo.exceptions import ValidationError
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

    from odoo.addons.base.models.ir_attachment import IrAttachment

SEARCH_ACCESS_CHUNK_MIN = 80
SEARCH_ACCESS_CHUNK_MAX = 8192


class MediaSegment(models.Model):
    _name = "media.segment"
    _description = "Media Segment"
    _order = "res_model, res_id, start_ms, id"

    res_model = fields.Char(
        string="Resource Model",
        index="btree_not_null",
        required=True,
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Resource ID",
        required=True,
    )
    attachment_id: IrAttachment = fields.Many2one(
        comodel_name="ir.attachment",
        index=True,
        required=True,
        ondelete="cascade",
    )
    start_ms = fields.Integer(
        default=0,
        required=True,
    )
    end_ms = fields.Integer(
        default=0,
        required=True,
    )
    duration_ms = fields.Integer(compute="_compute_duration_ms")
    mimetype = fields.Char(related="attachment_id.mimetype")
    content_released_at = fields.Datetime(related="attachment_id.content_released_at")

    _owner_idx = models.Index("(res_model, res_id, start_ms)")
    _span_is_forward = models.Constraint(
        "CHECK (end_ms > start_ms)", "A media segment must end after it starts."
    )
    _span_is_positive = models.Constraint(
        "CHECK (start_ms >= 0)", "A media segment cannot start before its recording."
    )
    _attachment_unique = models.Constraint(
        "UNIQUE (attachment_id)", "A media file belongs to one segment only."
    )

    @api.constrains("res_model", "res_id")
    def _constrains_the_owner_exists(self) -> None:
        for res_model, res_id in {(s.res_model, s.res_id) for s in self}:
            if res_model not in self.env:
                raise ValidationError(
                    self.env._("%(model)s is not a model.", model=res_model)
                )
            if not self.env[res_model].browse(res_id).exists():
                raise ValidationError(
                    self.env._("A media segment must belong to a record.")
                )

    @api.constrains("res_model", "res_id", "start_ms", "end_ms")
    def _constrains_segments_do_not_overlap(self) -> None:
        siblings = self.sudo().search(
            [
                ("res_model", "in", list(set(self.mapped("res_model")))),
                ("res_id", "in", list(set(self.mapped("res_id")))),
            ]
        )
        by_owner = defaultdict(list)
        for segment in siblings:
            by_owner[(segment.res_model, segment.res_id)].append(segment)
        for (res_model, _res_id), segments in by_owner.items():
            segments.sort(key=lambda segment: (segment.start_ms, segment.id))
            for earlier, later in pairwise(segments):
                if earlier.end_ms > later.start_ms:
                    raise ValidationError(
                        self.env._(
                            "Two media segments of %(model)s cover the same moment.",
                            model=res_model,
                        )
                    )

    @api.ondelete(at_uninstall=False)
    def _unlink_media(self) -> None:
        self.attachment_id.sudo().unlink()

    @api.depends("start_ms", "end_ms")
    def _compute_duration_ms(self) -> None:
        for segment in self:
            segment.duration_ms = max(segment.end_ms - segment.start_ms, 0)

    def _check_access(self, operation: str) -> tuple | None:
        result = super()._check_access(operation)
        if not self or self.env.su:
            return result
        candidates = self - result[0] if result else self
        forbidden = candidates._ids_with_inaccessible_owner(operation)
        if not forbidden:
            return result
        forbidden = self.browse(forbidden)
        if result:
            return (result[0] + forbidden, result[1])
        return (forbidden, lambda: prepare_document_access_error(forbidden, operation))

    def _ids_with_inaccessible_owner(self, operation: str) -> list[int]:
        rows = [(s.id, s.res_model, s.res_id) for s in self.sudo()]
        return _forbidden_ids(self.env, rows, operation)

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

        def allowed(rows: list[tuple]) -> set[int]:
            forbidden = set(_forbidden_ids(self.env, rows, "read"))
            return {row[0] for row in rows if row[0] not in forbidden}

        return get_accessible_query(
            self,
            domain,
            offset,
            limit,
            order,
            super()._search,
            fetch=prepare_column_fetcher(self, ("id", "res_model", "res_id")),
            allowed=allowed,
            chunk_min=SEARCH_ACCESS_CHUNK_MIN,
            chunk_max=SEARCH_ACCESS_CHUNK_MAX,
            **kwargs,
        )

    def _stamp_content_expiry(self, days: int) -> None:
        for segment in self.sudo():
            attachment = segment.attachment_id
            attachment.content_expires_at = (
                fields.Datetime.add(attachment.create_date, days=days)
                if days
                else False
            )

    @api.model
    def _of(self, records: models.Model) -> models.Model:
        if not records:
            return self.browse()
        return self.search(
            [("res_model", "=", records._name), ("res_id", "in", records.ids)]
        )

    def _owner(self) -> models.Model | None:
        self.check_singleton()
        if not self.res_model or self.res_model not in self.env:
            return None
        return self.env[self.res_model].browse(self.res_id).exists()


def _forbidden_ids(env, rows, operation: str) -> list[int]:
    owner_operation = "read" if operation == "read" else "write"
    owners = defaultdict(set)
    for _id, res_model, res_id in rows:
        owners[res_model].add(res_id)
    unreachable = set(get_inaccessible_owners(env, owners, owner_operation))
    return [
        id_ for id_, res_model, res_id in rows if (res_model, res_id) in unreachable
    ]
