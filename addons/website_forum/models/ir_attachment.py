from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _can_bypass_rights_on_media_dialog(self, **attachment_data):
        res_model = attachment_data.get("res_model")
        res_id = attachment_data.get("res_id")
        if (
            res_model == "forum.post"
            and res_id
            and self.env["forum.post"].browse(res_id).can_use_full_editor
        ):
            return True

        return super()._can_bypass_rights_on_media_dialog(**attachment_data)
