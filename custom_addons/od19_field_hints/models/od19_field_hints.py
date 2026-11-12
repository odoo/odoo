# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models, tools
from odoo.tools import str2bool

# คำนำหน้าตามชนิดข้อความ (kind -> prefix)
PREFIXES = {
    "example": "ตัวอย่าง:",
    "hint": "แนะนำ:",
    "warning": "สำคัญ:",
}

# ข้อความอัตโนมัติตามชนิดฟิลด์: type -> (kind, เนื้อความ)
AUTO_HINTS = {
    "char": ("example", "ระบุข้อความ"),
    "text": ("hint", "พิมพ์รายละเอียด"),
    "html": ("hint", "พิมพ์รายละเอียด"),
    "date": ("example", "วว/ดด/ปปปป"),
    "datetime": ("example", "วว/ดด/ปปปป ชช:นน"),
    "monetary": ("example", "0.00"),
    "float": ("example", "0.00"),
    "integer": ("example", "0"),
    "many2one": ("hint", "เลือกจากรายการ"),
    "many2many": ("hint", "เลือกจากรายการ"),
    "one2many": ("hint", "เลือกจากรายการ"),
    "selection": ("hint", "เลือกจากรายการ"),
    "email": ("example", "name@example.com"),
    "phone": ("example", "0X-XXX-XXXX"),
    "url": ("example", "https://example.com"),
}
DEFAULT_HINT = ("hint", "ระบุข้อมูล")

# ข้อความเจาะจงรายฟิลด์: model -> {field: (kind, เนื้อความ)}
OVERRIDES = {
    "res.partner": {
        "name": ("example", "เช่น: บริษัท Auto Info จำกัด"),
        "vat": ("example", "เช่น: 0105551234567"),
        "email": ("example", "เช่น: contact@auto-info.co.th"),
        "phone": ("example", "เช่น: 02-123-4567"),
    },
}

# ฟิลด์สำคัญที่อยากมีข้อความแม้ไม่ required: model -> [field]
IMPORTANT_FIELDS = {
    "res.partner": ["ref", "website"],
}


class Od19FieldHints(models.AbstractModel):
    _name = "od19.field.hints"
    _description = "OD19 Field Hints Config"

    @tools.ormcache()
    def _get_custom_models(self):
        """ชื่อโมเดลทั้งหมดที่มีฟิลด์ซึ่งนิยาม/สืบทอดโดยโมดูล od19_*"""
        result = set()
        for model_name, model in self.env.registry.items():
            for field in model._fields.values():
                if any(module.startswith("od19_") for module in (field._modules or ())):
                    result.add(model_name)
                    break
        return tuple(sorted(result))

    def _get_client_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": str2bool(params.get_param("od19_field_hints.enabled", "True")),
            "apply_core": str2bool(params.get_param("od19_field_hints.apply_core", "False")),
            "prefixes": PREFIXES,
            "auto": {key: list(value) for key, value in AUTO_HINTS.items()},
            "default": list(DEFAULT_HINT),
            "overrides": {
                model: {
                    field: {"kind": kind, "text": text}
                    for field, (kind, text) in fields.items()
                }
                for model, fields in OVERRIDES.items()
            },
            "important": IMPORTANT_FIELDS,
            "custom_models": list(self._get_custom_models()),
        }
