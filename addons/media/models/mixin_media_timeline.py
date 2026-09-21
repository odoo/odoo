from __future__ import annotations

import typing

from odoo import api, fields, models

if typing.TYPE_CHECKING:
    from .media_segment import MediaSegment
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MixinMediaTimeline(models.AbstractModel):
    _name = "mixin.media.timeline"
    _description = "Media Timeline"

    segment_ids: MediaSegment = fields.One2many(
        comodel_name="media.segment",
        inverse_name="res_id",
        string="Media",
        domain=lambda self: [("res_model", "=", self._name)],
    )
    media_duration_ms = fields.Integer(compute="_compute_media_duration_ms")
    has_media = fields.Boolean(compute="_compute_has_media")

    @api.depends("segment_ids.end_ms", "segment_ids.start_ms")
    def _compute_media_duration_ms(self) -> None:
        for record in self:
            ends = record.segment_ids.mapped("end_ms")
            record.media_duration_ms = max(ends) if ends else 0

    @api.depends("segment_ids")
    def _compute_has_media(self) -> None:
        for record in self:
            record.has_media = bool(record.segment_ids)

    def _add_media_segment(
        self, attachment: IrAttachment, start_ms: int, end_ms: int
    ) -> MediaSegment:
        self.check_singleton()
        segment = self.env["media.segment"].create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "attachment_id": attachment.id,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )
        segment._stamp_content_expiry(self._media_retention_days())
        return segment

    def _media_retention_days(self) -> int:
        return 0

    def _restamp_media_expiry(self) -> None:
        for record in self:
            record.segment_ids.filtered(
                lambda segment: not segment.content_released_at
            )._stamp_content_expiry(record._media_retention_days())

    @api.ondelete(at_uninstall=False)
    def _unlink_media_segments(self) -> None:
        self.env["media.segment"]._of(self).sudo().unlink()
