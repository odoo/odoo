from __future__ import annotations

from odoo import fields, models
from odoo.exceptions import AccessError


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _open_call_history(self) -> models.Model:
        self.check_singleton()
        return (
            self.env["discuss.call.history"]
            .sudo()
            .search(
                [("channel_id", "=", self.id), ("end_dt", "=", False)],
                order="start_dt DESC",
                limit=1,
            )
        )

    def _open_or_create_call_history(self) -> models.Model:
        self.check_singleton()
        return self._open_call_history() or (
            self.env["discuss.call.history"]
            .sudo()
            .create({"channel_id": self.id, "start_dt": fields.Datetime.now()})
        )

    def _start_call_recording(self, rtc_session: models.Model) -> bool:
        """Make ``rtc_session`` this call's one recorder, or refuse.

        Each start is a new recorder clock counting from zero, so the offset
        is taken again from where the timeline ends now: a second recording in
        the same call follows the first instead of overlapping it.
        """
        history = self._open_or_create_call_history()
        if history.recorder_session_id not in (rtc_session, rtc_session.browse()):
            return False
        history.write(
            {
                "recorder_session_id": rtc_session.id,
                "recording_offset_ms": history.media_duration_ms,
            }
        )
        return True

    def _stop_call_recording(self, rtc_session: models.Model) -> None:
        history = self._open_call_history()
        if history and history.recorder_session_id == rtc_session:
            history.recorder_session_id = False

    def _record_call_media(
        self, rtc_session: models.Model, attachment, start_ms: int, end_ms: int
    ) -> models.Model:
        history = self._open_call_history()
        if not history or history.recorder_session_id != rtc_session:
            raise AccessError(self.env._("You are not recording this call."))
        offset = history.recording_offset_ms
        return history._add_media_segment(
            attachment, offset + start_ms, offset + end_ms
        )
