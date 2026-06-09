import requests
import json
import base64
from odoo import models, fields, api, exceptions

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

    # 1. Thêm trường cấu hình cách chọn nhóm
    post_target = fields.Selection([
        ('all', 'Đăng vào TẤT CẢ các nhóm'),
        ('specific', 'Chỉ đăng vào nhóm được chọn bên dưới')
    ], string="Mục tiêu đăng", default='all', required=True)

    # THÊM TRƯỜNG NÀY: Kết nối bài viết với các Group cần đăng
    group_ids = fields.Many2many(
        "tool.group",
        "tool_post_group_rel",  # Tên bảng trung gian (trùng với khai báo ở trên)
        "post_id",             # Cột cho model hiện tại
        "group_id",            # Cột cho model liên kết
        string="Nhóm mục tiêu"
    )

    @api.constrains("attachment_ids")
    def _check_attachment_limit(self):
        for record in self:
            if len(record.attachment_ids) > 10:
                raise exceptions.ValidationError(
                    "A post can have at most 10 attachments."
                )
            
    def action_sync_groups_from_fastapi(self):
        """Hàm này chạy khi bấm nút trên giao diện Group, mở ra popup nhập UID/Username"""
        return {
            'name': 'Nhập thông tin tài khoản Facebook',
            'type': 'ir.actions.act_window',
            'res_model': 'tool.sync.group.wizard', # Gọi đến model wizard bên dưới
            'view_mode': 'form',
            'target': 'new', # Mở dạng popup (new window)
        }

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

            headers = {
                "X-API-Key": 'odoo_secret_key'
            }

            form_data = {
                "uid": str(self.uid)
            }

            response = requests.post(
                "http://localhost:8000/api/v1/bot/post-by-group-ids",
                headers=headers,
                data=form_data,
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