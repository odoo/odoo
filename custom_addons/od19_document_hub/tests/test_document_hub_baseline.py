# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestBaselineMetrics(TransactionCase):
    """เก็บตัวเลข baseline ของคลังเอกสาร (รันบน DB ทดสอบ ไม่แตะข้อมูลจริง)"""

    def test_report_metrics(self):
        Attachment = self.env["ir.attachment"]
        # การันตี pre-condition: ต้องมีไฟล์แนบแบบ binary อย่างน้อย 1 รายการ
        # (attachment ที่สร้างในเทสต์จะถูก rollback ตอน teardown — ไม่กระทบข้อมูลจริง)
        if Attachment.search_count([("type", "=", "binary")]) == 0:
            Attachment.create({
                "name": "baseline-probe.txt",
                "datas": base64.b64encode(b"baseline probe"),
            })

        total = Attachment.search_count([("type", "=", "binary")])
        with_checksum = Attachment.search_count([("checksum", "!=", False)])
        self.env.cr.execute("""
            SELECT COUNT(*) FROM (
                SELECT checksum FROM ir_attachment
                WHERE checksum IS NOT NULL
                GROUP BY checksum HAVING COUNT(*) > 1
            ) dup
        """)
        duplicate_groups = self.env.cr.fetchone()[0]
        self.env.cr.execute("""
            SELECT COALESCE(SUM(file_size), 0) FROM ir_attachment
        """)
        total_bytes = self.env.cr.fetchone()[0]

        metrics = (
            f"od19_document_hub.baseline total={total} "
            f"with_checksum={with_checksum} "
            f"dup_groups={duplicate_groups} total_bytes={total_bytes}"
        )
        # บันทึกเป็น log เพื่อใช้เทียบกับ KPI ในเฟสถัดไป (ir_logging มี NOT NULL: path/func/line)
        self.env.cr.execute("""
            INSERT INTO ir_logging
                (create_uid, create_date, name, level, type, dbname, message, path, func, line)
            VALUES (%s, NOW(), %s, %s, %s, current_database(), %s, %s, %s, %s)
        """, (
            self.env.uid, "od19_document_hub.baseline", "INFO", "server",
            metrics,
            "od19_document_hub/tests/test_document_hub_baseline.py",
            "test_report_metrics", "0",
        ))
        # TransactionCase rollback → บรรทัด ir_logging ไม่คงอยู่หลังเทสต์ จึง log ซ้ำเพื่อบันทึกถาวรใน run.log
        _logger.info(metrics)

        self.assertTrue(total >= 1, "ต้องมีไฟล์แนบอย่างน้อย 1 รายการเพื่อยืนยันว่าอ่านได้")
