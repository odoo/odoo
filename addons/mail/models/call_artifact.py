from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CallArtifact(models.Model):
    _name = 'call.artifact'
    _description = 'Call Artifact'

    OVERLAP_TOLERANCE_MS = 500

    discuss_call_history_id = fields.Many2one('discuss.call.history', string='Discuss Call History', ondelete='cascade', required=False, index=True)
    media_id = fields.Many2one('ir.attachment', string='Media Attachment', compute='_compute_media_id')
    start_ms = fields.Integer(string='Start (ms)', default=0, required=True, help="Offset from the start of the call in milliseconds")
    end_ms = fields.Integer(string='End (ms)', default=0, required=True, help="Offset from the start of the call in milliseconds")

    # ---------------------------------------------------------------------
    # Constraints

    @api.constrains('discuss_call_history_id')
    def _constrains_artifact_has_possessor(self):
        for record in self:
            if not record.discuss_call_history_id:
                msg = "Artifact must be linked to a call source."
                raise ValidationError(msg)

    @api.constrains('start_ms', 'end_ms')
    def _constrains_start_before_end(self):
        for artifact in self:
            if artifact.end_ms <= artifact.start_ms:
                msg = "End time must be greater than start time."
                raise ValidationError(msg)

    @api.constrains('start_ms', 'end_ms', 'discuss_call_history_id')
    def _constrains_artifacts_overlap(self):
        """ Check that artifacts within the same call do not overlap significantly.
        """
        checked_calls = set()
        for record in self:
            key = record._get_call_key()
            if not key or key in checked_calls:
                continue

            artifacts = record._get_call_artifacts()
            record._check_artifact_overlap(artifacts)
            checked_calls.add(key)

    def _get_call_key(self):
        """Returns a hashable key (model, id) for the call, or None."""
        self.ensure_one()
        if self.discuss_call_history_id:
            return ('discuss.call.history', self.discuss_call_history_id.id)
        return None

    def _get_call_artifacts(self):
        """Returns all artifacts belonging to the same call."""
        self.ensure_one()
        if self.discuss_call_history_id:
            return self.search([('discuss_call_history_id', '=', self.discuss_call_history_id.id)])
        return self.browse()

    def _is_overlap_candidate(self):
        """Hook to determine if self should be checked for overlap."""
        return True

    def _check_artifact_overlap(self, artifacts):
        """Validates a set of artifacts belonging to a single call."""
        media_candidates = sorted(
            [a for a in artifacts if a._is_overlap_candidate()],
            key=lambda x: x.start_ms
        )
        for i in range(len(media_candidates) - 1):
            if media_candidates[i].end_ms > media_candidates[i + 1].start_ms + self.OVERLAP_TOLERANCE_MS:
                msg = "Media artifacts overlap significantly."
                raise ValidationError(msg)

    # ---------------------------------------------------------------------
    # Computes

    def _compute_media_id(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        attachment_by_res_id = {a.res_id: a for a in attachments}
        for artifact in self:
            artifact.media_id = attachment_by_res_id.get(artifact.id)
