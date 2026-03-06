# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class IrAttachmentActionDownloadMixin(models.AbstractModel):
    _name = "ir.attachment.action_download"
    _description = """
        Mixin to help download attachments linked to record(s).
    """

    def _get_downloadable_attachments(self):
        """Give a chance to easily overwrite this method
        on sub modules to limit restict attachement able to downlaods

        In some case we probably want the user download some specific
        document that are probably related to the current model

        By default return all attachment link the the record.
        """
        return self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )

    def action_download_attachments(self):
        """Return action to:
        * emit a warning message if no attachment found
        * download a file if only 1 file found
        * zip and download the list of attachment returns by
          `_get_downloadable_attachments`
        """
        attachments = self._get_downloadable_attachments()
        if not attachments:
            title = self.env._("No attachment!")
            message = self.env._("There is no document found to download.")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "title": title,
                    "message": message,
                    "sticky": True,
                },
            }

        if len(attachments) == 1:
            return {
                "target": "self",
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachments.id}?download=1",
            }
        else:
            return attachments.action_attachments_download()
