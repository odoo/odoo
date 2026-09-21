from __future__ import annotations

import typing

from odoo import api, fields, models

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


class SpeechSpeaker(models.Model):
    _name = "speech.speaker"
    _inherit = ["mixin.owner.access"]
    _description = "Speaker"
    _access_owner_field = "attachment_id"
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

    @api.depends("partner_id.user_ids.share")
    def _compute_user_id(self) -> None:
        for speaker in self:
            speaker.user_id = speaker.partner_id.user_ids.filtered(
                lambda user: not user.share
            )[:1]

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
