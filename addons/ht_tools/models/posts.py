from odoo import models, fields, exceptions, api
import requests

class Post(models.Model):
    _name = "tool.post"
    _description = "Post"

    name = fields.Char(string="Tiêu đề", required=True)
    content = fields.Text(string="Nội dung")
    active = fields.Boolean(default=True)
    uid = fields.Char(string="ID FB", required=True)

    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Đính kèm"
    )

    @api.constrains("attachment_ids")
    def _check_attachment_limit(self):
        for record in self:
            if len(record.attachment_ids) > 10:
                raise exceptions.ValidationError(
                    "A post can have at most 10 attachments."
                )
            
    def action_send_to_bot(self):
        self.ensure_one()

        files = []

        try:
            for attachment in self.attachment_ids:
                if not attachment.datas:
                    continue

                files.append(
                    (
                        "images",
                        (
                            attachment.name,
                            attachment.raw,
                            attachment.mimetype or "application/octet-stream",
                        ),
                    )
                )

            response = requests.post(
                "http://localhost:8000/run-bot",
                data={
                    "uid": self.uid,
                    "action": "post",
                    "content": self.content or "",
                },
                files=files,
                timeout=120,
            )

            response.raise_for_status()

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Success",
                    "message": "Đã gửi sang Bot thành công",
                    "type": "success",
                },
            }

        except Exception as e:
            raise exceptions.UserError(
                f"Gửi Bot thất bại:\n{str(e)}"
            )