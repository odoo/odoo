import logging
import requests
import json
from odoo import models, fields, exceptions, api

_logger = logging.getLogger(__name__)

class ToolSyncGroupWizard(models.TransientModel):
    _name = "tool.sync.group.wizard"
    _description = "Wizard đồng bộ nhóm từ FastAPI"

    def _get_active_fb_accounts(self):
        """
        Hàm này chỉ chạy Odoo khi load form/render field.
        Gọi API 1 lần duy nhất để lấy cả UID và Username.
        """
        headers = {"X-API-Key": 'odoo_secret_key'}
        try:
            # Gọi đến endpoint chung của bạn
            response = requests.get("http://localhost:8000/api/v1/active-accounts", headers=headers, timeout=5)
            if response.status_code == 200:
                # Lấy đúng key 'accounts' dạng dict từ FastAPI: {"10001": "Nguyễn Văn A", "10002": "Trần Thị B"}
                accounts_dict = response.json().get('accounts', {})

                # Trả về định dạng [(giá_trị_lưu_db, nhãn_hiển_thị)]
                # Kết quả sẽ dạng: [('10001', 'Nguyễn Văn A'), ('10002', 'Trần Thị B')]
                return [(str(uid), str(uid)) for uid, account in accounts_dict.items()]
            return []
        except Exception:
            return []

    # 1. Dropdown hiển thị Tên người dùng để chọn trực quan, nhưng dưới DB vẫn lưu UID số.
    uid = fields.Selection(selection=_get_active_fb_accounts, string="Chọn tài khoản FB", required=True)
    
    # 2. Field chứa username tách biệt
    username = fields.Char(string="Chọn tài khoản HT Tools", required=True)

    @api.onchange('uid')
    def _onchange_uid(self):
        """
        Hàm này chạy NGAY LẬP TỨC khi user chọn một tài khoản từ dropdown.
        """
        # Thì mới phải gọi API đơn lẻ (hoặc gọi lại endpoint chung)
        headers = {"X-API-Key": 'odoo_secret_key'}
        try:
            response = requests.get("http://localhost:8000/api/v1/active-accounts", headers=headers, timeout=5)
            if response.status_code == 200:
                accounts_dict = response.json().get('accounts', {})
                self.username = accounts_dict.get(self.uid, "Không xác định")
        except Exception:
            self.username = "Lỗi kết nối"

    def action_execute(self):
        """Hàm trung gian điều hướng dựa trên action_mode truyền từ context"""
        self.ensure_one()
        
        # Lấy chế độ hành động từ context truyền vào
        mode = self.env.context.get('action_mode', 'sync')

        if mode == 'post':
            _logger.info("=== Chuyển hướng xử lý: ĐĂNG BÀI ===")
            return self.action_send_to_bot()
        else:
            _logger.info("=== Chuyển hướng xử lý: ĐỒNG BỘ NHÓM ===")
            return self.action_confirm_sync()

    def action_send_to_bot(self):
        self.ensure_one()

        # 1. Đọc dữ liệu từ Context an toàn
        group_ids_raw = self.env.context.get('selected_group_ids', 'ALL')
        content = self.env.context.get('content', '')
        attachment_ids_raw = self.env.context.get('attachments', [])

        # Ép mảng thu được về dạng JSON string đúng chuẩn FastAPI: '["10001", "10002"]'
        group_ids_str = json.dumps(group_ids_raw) if group_ids_raw else "ALL"

        # 3. Chuẩn hóa mảng ID file đính kèm
        if isinstance(attachment_ids_raw, int):
            attachment_ids_raw = [attachment_ids_raw]

        files = []
        attachments = self.env['ir.attachment'].browse(attachment_ids_raw)
        
        try:
            # 4. Đóng gói danh sách file nhị phân gửi dạng Multipart
            for attachment in attachments:
                if not attachment.datas:
                    continue

                # Lấy dữ liệu bytes trực tiếp (Tối ưu từ Odoo 15+)
                file_content = attachment.raw or attachment._decode_datas(attachment.datas)

                files.append(
                    (
                        "images",
                        (
                            attachment.name,
                            file_content,
                            attachment.mimetype or "application/octet-stream",
                        ),
                    )
                )

            # 5. Cấu hình gói tin gửi đi
            headers = {
                "X-API-Key": 'odoo_secret_key'
            }

            form_data = {
                "uid": str(self.uid),
                "username": str(self.username or self.name or ""),
                "content": str(content),
                "group_ids": group_ids_str  # 🌟 Luôn là '["123", "456"]' hoặc 'ALL' chuẩn chỉ!
            }

            # 6. Thực hiện bắn POST request sang FastAPI
            response = requests.post(
                "http://localhost:8000/api/v1/bot/post-by-group-ids",
                headers=headers,
                data=form_data,
                files=files if files else None,
                timeout=120,
            )

            response.raise_for_status()
            result = response.json()
            job_id = result.get("job_id", "N/A")

            # 7. Hiển thị thông báo dạng Toast thành công trên giao diện Odoo
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thành công",
                    "message": f"Đã đưa tác vụ vào hàng đợi xử lý ngầm (Job ID: {job_id})",
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            raise exceptions.UserError(
                f"Gửi Bot thất bại:\n{str(e)}"
            )

    def action_confirm_sync(self):
        """Nút bấm Xác nhận trên giao diện Popup"""
        self.ensure_one()
        
        # 1. Cấu hình API endpoint kết nối tới FastAPI
        fastapi_url = "http://localhost:8000/api/v1/get-groups"
        params = {
            "uid": self.uid,
            "username": self.username
        }

        headers = {
                "X-API-Key": 'odoo_secret_key'
            }

        try:
            # 2. Gọi API sang FastAPI để lấy toàn bộ group (không phân trang)
            response = requests.get(fastapi_url, headers=headers ,params=params, timeout=15)

            if response.status_code != 200:
                raise exceptions.UserError(
                    f"Không thể lấy dữ liệu. FastAPI phản hồi mã lỗi: {response.status_code}"
                )

            res_data = response.json()

            # Dữ liệu thu về
            groups_list = res_data.get("data", [])

            if not groups_list:
                raise exceptions.UserError(f"Tài khoản '{self.username}' hiện không có nhóm nào trên hệ thống FastAPI.")

            # 3. Xử lý lưu dữ liệu vào bảng tool.group
            GroupModel = self.env['tool.group']
            sync_count = 0

            for group in groups_list:
                # Lấy group_id từ FastAPI (bọc str phòng hờ dữ liệu trả về dạng int)
                group_id = str(group.get("group_id") or "")
                name = group.get("group_name")

                if not group_id:
                    continue

                # Kiểm tra trùng lặp dựa vào trường group_id
                GroupModel.search([
                    ('user_id', '=', self.env.uid)
                ]).unlink()

                sync_count = 0

                for group in groups_list:
                    group_id = str(group.get("group_id") or "")
                    name = group.get("group_name")

                    if not group_id:
                        continue

                    GroupModel.create({
                        'name': name,
                        'group_id': group_id,
                        'user_id': self.env.uid,
                    })

                    sync_count += 1

            # 4. Bắn thông báo thành công dạng Toast Notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đồng bộ thành công',
                    'message': f'Đã nạp thành công {sync_count}/{len(groups_list)} nhóm của tài khoản {self.username} vào Odoo!',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except requests.exceptions.Timeout:
            raise exceptions.UserError("Kết nối tới FastAPI bị quá hạn (Timeout).")
        except requests.exceptions.ConnectionError:
            raise exceptions.UserError("Không thể kết nối tới FastAPI. Vui lòng kiểm tra lại URL hoặc xem Tool đã bật chưa.")
        except Exception as e:
            _logger.error(f"Lỗi không xác định: {str(e)}")
            raise exceptions.UserError(f"Đã xảy ra lỗi: {str(e)}")