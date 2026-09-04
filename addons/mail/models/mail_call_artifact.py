from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailCallArtifact(models.Model):
    """Represent a discrete product of a call (audio, transcript etc.)

    For media artifacts, each record acts as a thin metadata wrapper (timing, source, etc.) for
    exactly one media file, keeping the ir_attachment table lean"""

    _name = "mail.call.artifact"
    _description = "Call Artifact"

    # required=False as artifact can also owned by other call models (ensured by constraints)
    discuss_call_history_id = fields.Many2one(
        "discuss.call.history", string="Discuss Call History",
        ondelete="cascade", required=False, index=True,
    )
    recording_started_by_id = fields.Many2one(
        "res.partner", string="Recording Started By", readonly=True, ondelete="set null",
    )
    media_id = fields.Many2one(
        "ir.attachment", string="Media Attachment", compute="_compute_media_id",
    )
    start_ms = fields.Integer(
        string="Start (ms)", default=0, required=True,
        help="Offset from the start of the call in milliseconds",
    )
    end_ms = fields.Integer(
        string="End (ms)", default=0, required=True,
        help="Offset from the start of the call in milliseconds",
    )

    # ---------------------------------------------------------------------
    # Constraints

    _start_before_end = models.Constraint(
        "CHECK(start_ms < end_ms)", "End time must be after the start time.",
    )
    _artifact_has_possessor = models.Constraint(
        "CHECK(num_nonnulls(discuss_call_history_id) = 1)", "Artifact must be linked to a call source.",
    )

    @api.constrains("start_ms", "end_ms", "discuss_call_history_id")
    def _constrains_artifacts_overlap(self):
        """Check that artifacts within the same call do not overlap."""
        grouped_artifacts = self._get_artifacts_grouped_by_call()
        for key, artifacts in grouped_artifacts.items():
            if not key:
                continue
            self._check_artifacts_overlap(artifacts)

    def _get_artifacts_grouped_by_call(self):
        """Return a dict mapping call records to their respective artifact recordsets.

        This hook allows other modules to include artifacts linked to different
        call models (e.g., voip.call) in the overlap validation"""
        all_artifacts = self.discuss_call_history_id.artifact_ids
        return all_artifacts.grouped('discuss_call_history_id')

    def _is_overlap_candidate(self):
        """Determine if self should be checked for overlap"""
        return True

    def _check_artifacts_overlap(self, artifacts):
        """Check if the provided artifacts overlap in time"""
        candidates = sorted(
            (a for a in artifacts if a._is_overlap_candidate()),
            key=lambda x: x.start_ms,
        )
        for i in range(len(candidates) - 1):
            if candidates[i].end_ms > candidates[i + 1].start_ms:
                raise ValidationError(self.env._("Media artifacts overlap."))

    # ---------------------------------------------------------------------
    # Computes

    def _compute_media_id(self):
        attachments = self.env["ir.attachment"].search_fetch([
            ("res_model", "=", self._name),
            ("res_id", "in", self.ids),
        ], ['res_id'])
        attachment_by_res_id = attachments.grouped('res_id')
        for artifact in self:
            artifact.media_id = attachment_by_res_id.get(artifact.id)

    # ---------------------------------------------------------------------
    # Methods

    def _get_related_call(self):
        """Return the parent call record (discuss.call.history, voip.call, etc.)"""
        self.ensure_one()
        return self.discuss_call_history_id

    def _is_recording_media(self):
        self.ensure_one()
        return bool(
            self.media_id
            and self.media_id.mimetype
            and self.media_id.mimetype.startswith(("audio/", "video/"))
        )

    def _is_recording_available(self):
        self.ensure_one()
        return self._is_recording_media()

    def _send_recording_available_email(self):
        template = self.env.ref(
            "mail.mail_template_discuss_call_recording_available",
            raise_if_not_found=False,
        )
        if not template:
            return
        for artifact in self:
            if not artifact.recording_started_by_id or not artifact._is_recording_available():
                continue
            template.send_mail(artifact.id, force_send=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_cleanup_media_attachment(self):
        self.media_id.sudo().unlink()
