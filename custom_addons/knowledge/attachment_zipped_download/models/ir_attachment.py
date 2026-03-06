# Copyright 2019 César Fernández Domínguez <cesfernandez@outlook.com>
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import zipfile
from io import BytesIO

from odoo import models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def action_attachments_download(self):
        items = self.filtered(lambda x: x.type == "binary")
        if not items:
            raise UserError(
                self.env._("None attachment selected. Only binary attachments allowed.")
            )
        ids = ",".join(map(str, items.ids))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/attachment/download_zip?ids={ids}",
            "target": "self",
        }

    def _create_temp_zip(self):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for attachment in self:
                attachment.check("read")
                zip_file.writestr(
                    attachment._compute_zip_file_name(),
                    attachment.raw,
                )
            zip_buffer.seek(0)
            zip_file.close()
        return zip_buffer

    def _compute_zip_file_name(self):
        """Give a chance of easily changing the name of the file inside the ZIP."""
        self.ensure_one()
        return self.name
