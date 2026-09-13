from __future__ import annotations

import typing
from collections import defaultdict
from itertools import pairwise

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


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
    transcription_state = fields.Selection(
        related="attachment_id.speech_state",
        string="Transcription",
    )
    speech_cues = fields.Json(related="attachment_id.speech_cues")

    _span_is_forward = models.Constraint(
        "CHECK (end_ms > start_ms)", "A media segment must end after it starts."
    )
    _span_is_positive = models.Constraint(
        "CHECK (start_ms >= 0)", "A media segment cannot start before its recording."
    )
    _attachment_unique = models.Constraint(
        "UNIQUE (attachment_id)", "A media file belongs to one segment only."
    )
    _owner_idx = models.Index("(res_model, res_id, start_ms)")

    @api.depends("start_ms", "end_ms")
    def _compute_duration_ms(self) -> None:
        for segment in self:
            segment.duration_ms = max(segment.end_ms - segment.start_ms, 0)

    @api.constrains("res_model", "res_id", sudo=False)
    def _constrains_the_owner_is_writable(self) -> None:
        # A segment puts audio into someone else's timeline, and its transcript
        # into their record. Without this any internal user could file their own
        # recording against a call they were never in.
        if self.env.su:
            return
        for res_model, res_id in {(s.res_model, s.res_id) for s in self}:
            if res_model not in self.env:
                raise ValidationError(
                    self.env._("%(model)s is not a model.", model=res_model)
                )
            owner = self.env[res_model].browse(res_id).exists()
            if not owner:
                raise ValidationError(
                    self.env._("A media segment must belong to a record.")
                )
            try:
                owner.check_access("write")
            except AccessError as error:
                raise ValidationError(
                    self.env._(
                        "You may not add media to %(name)s.", name=owner.display_name
                    )
                ) from error

    @api.constrains("res_model", "res_id", "start_ms", "end_ms")
    def _constrains_segments_do_not_overlap(self) -> None:
        siblings = self.search(
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

    @api.ondelete(at_uninstall=False)
    def _unlink_media(self) -> None:
        self.attachment_id.sudo().unlink()
