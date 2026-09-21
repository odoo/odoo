from __future__ import annotations

import typing
from collections import defaultdict
from itertools import pairwise

from odoo import api, fields, models
from odoo.exceptions import ValidationError

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class MediaSegment(models.Model):
    _name = "media.segment"
    _inherit = ["mixin.owner.access"]
    _description = "Media Segment"
    _access_owner_field = "res_id"
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

    def _stamp_content_expiry(self, days: int) -> None:
        for segment in self.sudo():
            attachment = segment.attachment_id
            attachment.content_expires_at = (
                fields.Datetime.add(attachment.create_date, days=days)
                if days
                else False
            )
