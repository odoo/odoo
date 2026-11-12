# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportArchive(TransactionCase):

    def test_archive_creates_internal_attachment(self):
        category = self.env["od19.document.category"].create({
            "name": "รายงานภาษี", "code": "RPT_TAX",
        })
        attachment = self.env["od19.report.archive.mixin"]._od19_archive_report(
            report_name="l10n_th.tax.report.pdf",
            binary_content=b"%PDF-1.4 fake",
            res_model="res.partner",
            res_id=self.env.user.partner_id.id,
            filename="tax-report.pdf",
            category_code="RPT_TAX",
        )
        self.assertEqual(attachment.od19_origin, "internal")
        self.assertEqual(attachment.od19_source_ref, "l10n_th.tax.report.pdf")
        self.assertEqual(attachment.od19_category_id, category)
        self.assertIn("tax-report", attachment.name)

    def test_archive_unknown_category_is_skipped(self):
        attachment = self.env["od19.report.archive.mixin"]._od19_archive_report(
            report_name="unknown.pdf",
            binary_content=b"x",
            res_model="res.partner",
            res_id=self.env.user.partner_id.id,
            category_code="NOT_EXIST",
        )
        self.assertFalse(attachment.od19_category_id)
