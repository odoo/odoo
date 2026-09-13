from urllib.parse import quote

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.documents import get_format_of_extension
from odoo.tools.image import base64_to_image

SUPPORTED_IMAGE_EXTENSIONS = ("gif", "jpg", "png", "svg", "webp")
# Every spelling of each format, mapped to the extension a file of it is written under.
SUPPORTED_IMAGE_MIMETYPES = {
    mimetype: f".{extension}"
    for extension in SUPPORTED_IMAGE_EXTENSIONS
    for mimetype in get_format_of_extension(extension).mimetypes
}


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    local_url = fields.Char(
        string="Attachment URL",
        compute="_compute_local_url",
    )
    image_src = fields.Char(compute="_compute_image_src")
    image_width = fields.Integer(compute="_compute_image_size")
    image_height = fields.Integer(compute="_compute_image_size")
    original_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Original (unoptimized, unresized) attachment",
        index="btree_not_null",
    )

    @api.depends("url", "checksum")
    def _compute_local_url(self):
        for attachment in self:
            if attachment.url:
                attachment.local_url = attachment.url
            else:
                attachment.local_url = (
                    f"/web/image/{attachment.id}?unique={attachment.checksum}"
                )

    @api.depends("mimetype", "url", "name")
    def _compute_image_src(self):
        for attachment in self:
            if (
                not attachment.mimetype
                or attachment.mimetype.split(";")[0] not in SUPPORTED_IMAGE_MIMETYPES
            ):
                attachment.image_src = False
                continue

            if attachment.type == "url":
                if attachment.url.startswith("/"):
                    attachment.image_src = attachment.url
                else:
                    name = quote(attachment.name)
                    attachment.image_src = f"/web/image/{attachment.id}-redirect/{name}"
            else:
                unique = attachment.checksum[:8]
                if attachment.url:
                    separator = "&" if "?" in attachment.url else "?"
                    attachment.image_src = f"{attachment.url}{separator}unique={unique}"
                else:
                    name = quote(attachment.name)
                    attachment.image_src = f"/web/image/{attachment.id}-{unique}/{name}"

    @api.depends("datas")
    def _compute_image_size(self):
        for attachment in self:
            try:
                image = base64_to_image(attachment.datas)
                attachment.image_width = image.width
                attachment.image_height = image.height
            except UserError:
                attachment.image_width = 0
                attachment.image_height = 0

    def _get_media_info(self):
        self.check_singleton()
        return self._read_format(
            [
                "id",
                "name",
                "description",
                "mimetype",
                "checksum",
                "url",
                "type",
                "res_id",
                "res_model",
                "public",
                "access_token",
                "image_src",
                "image_width",
                "image_height",
                "original_id",
            ]
        )[0]

    def _can_bypass_rights_on_media_dialog(self, **attachment_data):
        return False
