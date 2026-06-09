import logging
import requests
from odoo import models, fields, exceptions, api

_logger = logging.getLogger(__name__)

class ToolSyncGroupWizard(models.TransientModel):
    _name = "tool.sync.group.wizard"
    _description = "Wizard đồng bộ nhóm từ FastAPI"

    def _get_active_fb_accounts(self):
        headers = {"X-API-Key": 'odoo_secret_key'}
        try:
            response = requests.get("http://localhost:8000/api/v1/active-accounts", headers=headers, timeout=5)
            if response.status_code == 200:
                # Odoo chủ động vào lấy đúng key 'accounts' ra xử lý
                accounts_dict = response.json().get('accounts', {})
                return [(str(uid), str(uid)) for uid in accounts_dict.keys()]
            return []
        except Exception:
            return []

    @api.onchange('uid')
    def _onchange_uid(self):
        if self.uid:
            headers = {"X-API-Key": 'odoo_secret_key'}
            try:
                response = requests.get("http://localhost:8000/api/v1/active-accounts", headers=headers, timeout=5)
                if response.status_code == 200:
                    accounts_dict = response.json().get('accounts', {})
                    self.username = accounts_dict.get(self.uid, "Không xác định")
            except Exception:
                self.username = "Lỗi kết nối"

    # Dropdown chọn UID lấy động từ Redis
    uid = fields.Selection(selection=_get_active_fb_accounts, string="Chọn tài khoản FB", required=True)
    username = fields.Char(string="Chọn tài khoản HT Tools", required=True)

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
                existing_group = GroupModel.search([('group_id', '=', group_id)], limit=1)

                if existing_group:
                    # Nếu có rồi thì cập nhật lại tên mới nhất
                    existing_group.write({
                        'name': name
                    })
                else:
                    # Chưa có thì tạo mới
                    GroupModel.create({
                        'name': name,
                        'group_id': group_id
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