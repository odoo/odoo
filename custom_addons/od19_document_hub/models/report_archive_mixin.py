# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Od19ReportArchiveMixin(models.AbstractModel):
    _name = "od19.report.archive.mixin"
    _description = "Mixin เก็บรายงานที่สร้างภายในเข้าแฟ้มเอกสาร"

    @api.model
    def _od19_resolve_category(self, category_code):
        if not category_code:
            return self.env["od19.document.category"]
        return self.env["od19.document.category"].search(
            [("code", "=", category_code)], limit=1,
        )

    @api.model
    def _od19_archive_report(
        self, report_name, binary_content, res_model, res_id,
        filename=None, category_code=None, doc_date=None,
    ):
        """เก็บผลลัพธ์รายงาน (bytes) เป็น ir.attachment พร้อม metadata ครบ"""
        category = self._od19_resolve_category(category_code)
        if category_code and not category:
            _logger.warning(
                "od19_document_hub: ไม่พบหมวด '%s' — เก็บรายงานโดยไม่ระบุหมวด",
                category_code,
            )
        return self.env["ir.attachment"].create({
            "name": filename or f"{report_name}.pdf",
            "datas": base64.b64encode(binary_content),
            "res_model": res_model,
            "res_id": res_id,
            "od19_origin": "internal",
            "od19_source_ref": report_name,
            "od19_doc_date": doc_date or fields.Date.context_today(self),
            "od19_category_id": category.id,
        })
