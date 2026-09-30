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

    user_id = fields.Many2one(
        "res.users",
        string="Owner",
        default=lambda self: self.env.user,
        required=True,
        index=True
    )

    @api.onchange('post_target')
    def _onchange_post_target(self):
        """Tự động xóa sạch các nhóm đã chọn nếu người dùng chuyển sang chế độ Đăng tất cả"""
        if self.post_target == 'all':
            self.group_ids = [(5, 0, 0)]

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
            'context': {
                'action_mode': 'sync'
            }
        }

    def action_send_to_bot(self):
        """Hàm này chạy khi bấm nút trên giao diện Group, mở ra popup nhập UID/Username"""
        fb_group_ids = [str(g.group_id) for g in self.group_ids if g.group_id]

        return {
            'name': 'Nhập thông tin tài khoản Facebook',
            'type': 'ir.actions.act_window',
            'res_model': 'tool.sync.group.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                # Giữ lại context cũ của hệ thống để không làm mất các biến mặc định khác
                **self.env.context, 
                # Truyền tham số tùy chỉnh của bạn (Đặt key tên là gì tùy ý, bắt đầu bằng 'default_' nếu muốn gán thẳng vào field của wizard)
                'selected_group_ids': fb_group_ids,
                'mode': self.post_target,
                'content': self.content,
                'attachments': self.attachment_ids.ids,
                'action_mode': 'post'
            }
        }