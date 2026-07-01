# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.discuss.rtc import RtcController


class CloudStorageRtcController(RtcController):
    def _get_recording_destination(self, call_history, start_ms, end_ms):
        """
           :param: channel_id: the 'discuss.channel' record that has the attachment field
           :return: the recording destination
        """
        super()._get_recording_destination(call_history, start_ms, end_ms)
        artifact_sudo = self.env["mail.call.artifact"].sudo().create({
            "discuss_call_history_id": call_history.id,
            "start_ms": start_ms,
            "end_ms": end_ms,
        })
        content_type = self.httprequest.content_type or "audio/ogg"
        attachment_sudo = self.env["ir.attachment"].sudo().create({
            "name": f"audio_{call_history.id}",
            "type": "cloud_storage",
            "raw": False,
            "res_model": "mail.call.artifact",
            "res_id": artifact_sudo.id,
            "mimetype": content_type,
        })
        return attachment_sudo._generate_cloud_storage_download_info()["url"]
