import requests
import json
import base64
from odoo import models, fields, api, exceptions

class Group(models.Model):
    _name = "tool.group"
    _description = "Nhóm đăng bài"

    name = fields.Char(string="Tên Nhóm")
    group_id = fields.Char(string="Group ID")
    
    # Kết nối ngược lại với Post để biết nhóm này đã có những bài viết nào (Tùy chọn)
    post_ids = fields.Many2many(
        "tool.post",
        "tool_post_group_rel",
        "group_id",
        "post_id",
        string="Bài viết đã đăng"
    )

    user_id = fields.Many2one(
        "res.users",
        string="Owner",
        default=lambda self: self.env.user,
        required=True,
        index=True
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
