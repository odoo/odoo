# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.discuss.rtc import RtcController


class CloudStorageRtcController(RtcController):
    def _get_recording_destination(self, channel_id):
        """
           :param: channel_id: the 'discuss.channel' record that has the attachment field
           :return: the recording destination
        """
        if channel_id:
            # TODO create a cloud ir attachment, attached to the call history
            # return the cloud url of that attachment so that the SFU can upload the recording there
            return "CLOUD_URL_PLACEHOLDER"
        return super()._get_recording_destination(channel_id)
