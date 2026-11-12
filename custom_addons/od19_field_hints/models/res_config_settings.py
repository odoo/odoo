# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_field_hints_enabled = fields.Boolean(
        string="ข้อความแนะนำในช่องกรอก",
        config_parameter="od19_field_hints.enabled",
        default=True,
        help="แสดงข้อความตัวอย่าง/คำแนะนำ/คำเตือนสีเทาในช่องที่ยังว่างอยู่ "
        "เป็นเพียงข้อความแสดงผล ไม่ถูกบันทึกเป็นข้อมูลจริง "
        "(ต้องรีเฟรชหน้าเว็บหลังเปลี่ยนค่า)",
    )
    od19_field_hints_apply_core = fields.Boolean(
        string="ใช้กับโมดูลมาตรฐาน (Core/OCA) ด้วย",
        config_parameter="od19_field_hints.apply_core",
        default=False,
        help="ถ้าปิด จะแสดงเฉพาะโมดูล od19_* ของเรา",
    )

    def set_values(self):
        super().set_values()
        # `ir.config_parameter.set_param(key, False)` ลบ parameter ทิ้ง และ
        # `_get_client_config` จะอ่านค่า default "True" เมื่อ parameter หายไป
        # จึงต้องเก็บค่าเป็นสตริง "True"/"False" เพื่อให้การปิดสวิตช์ติดจริง
        self.env["ir.config_parameter"].sudo().set_param(
            "od19_field_hints.enabled",
            "True" if self.od19_field_hints_enabled else "False",
        )
