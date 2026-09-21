from __future__ import annotations

import typing

from odoo import api, fields, models
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


class SpeechSpeaker(models.Model):
    _name = "speech.speaker"
    _description = "Speaker"
    _order = "attachment_id, first_spoke_s, id"

    attachment_id: IrAttachment = fields.Many2one(
        comodel_name="ir.attachment",
        index=True,
        required=True,
        ondelete="cascade",
    )
    label = fields.Char(
        required=True,
        help="What the transcriber called this voice, e.g. SPEAKER_0",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Person",
        index="btree_not_null",
    )
    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_user_id",
    )
    talk_time_s = fields.Float(
        string="Talk time (s)",
        digits=(12, 1),
        compute="_compute_talk",
        store=True,
    )
    turns = fields.Integer(
        compute="_compute_talk",
        store=True,
    )
    first_spoke_s = fields.Float(
        string="First spoke at (s)",
        digits=(12, 1),
        compute="_compute_talk",
        store=True,
    )

    _attachment_label_unique = models.Constraint(
        "UNIQUE (attachment_id, label)",
        "A voice is named once per recording.",
    )

    @api.depends("partner_id.name", "label")
    def _compute_name(self) -> None:
        for speaker in self:
            if speaker.partner_id:
                speaker.name = speaker.partner_id.name
            elif not speaker.name:
                speaker.name = speaker.label

    @api.depends("partner_id.main_user_id.share")
    def _compute_user_id(self) -> None:
        for speaker in self:
            user = speaker.partner_id.main_user_id
            speaker.user_id = user if user and not user.share else False

    @api.depends("attachment_id.transcript_cues", "label")
    def _compute_talk(self) -> None:
        for speaker in self:
            spans = [
                cue
                for cue in speaker.attachment_id.transcript_cues or []
                if cue.get("speaker") == speaker.label
            ]
            speaker.turns = len(spans)
            speaker.talk_time_s = sum(
                max(0.0, (cue.get("end") or 0.0) - (cue.get("start") or 0.0))
                for cue in spans
            )
            speaker.first_spoke_s = min(
                (cue.get("start") or 0.0 for cue in spans), default=0.0
            )

    @api.model
    def _sync_from_cues(self, attachment: IrAttachment) -> SpeechSpeaker:
        labels = {
            cue.get("speaker")
            for cue in attachment.transcript_cues or []
            if cue.get("speaker")
        }
        known = set(
            self.sudo().search([("attachment_id", "=", attachment.id)]).mapped("label")
        )
        return self.sudo().create(
            [
                {"attachment_id": attachment.id, "label": label}
                for label in sorted(labels - known)
            ]
        )

    def _check_access(self, operation: str) -> tuple | None:
        result = super()._check_access(operation)
        if not self or self.env.su:
            return result
        candidates = self - result[0] if result else self
        attachments = {s.attachment_id.id for s in candidates.sudo()}
        owner_operation = "read" if operation == "read" else "write"
        unreachable = {
            res_id
            for _model, res_id in get_inaccessible_owners(
                self.env, {"ir.attachment": attachments}, owner_operation
            )
        }
        forbidden = candidates.sudo().filtered(
            lambda s: s.attachment_id.id in unreachable
        )
        if not forbidden:
            return result
        forbidden = self.browse(forbidden.ids)
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

        def allowed(rows: list[tuple]) -> set[int]:
            unreachable = {
                res_id
                for _model, res_id in get_inaccessible_owners(
                    self.env, {"ir.attachment": {row[1] for row in rows}}, "read"
                )
            }
            return {row[0] for row in rows if row[1] not in unreachable}

        return get_accessible_query(
            self,
            domain,
            offset,
            limit,
            order,
            super()._search,
            fetch=prepare_column_fetcher(self, ("id", "attachment_id")),
            allowed=allowed,
            chunk_min=SEARCH_ACCESS_CHUNK_MIN,
            chunk_max=SEARCH_ACCESS_CHUNK_MAX,
            **kwargs,
        )
