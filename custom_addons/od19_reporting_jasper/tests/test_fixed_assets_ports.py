# -*- coding: utf-8 -*-
"""Tests for the 7 legacy ``dtr_fixed_assets_report`` Jasper ports.

Covers the batch of fixed-asset reports ported into ``od19_reporting_jasper``:
ทะเบียนทรัพย์สิน (ฟอร์ม / รายงาน / บาร์โค้ด / QR), ค่าเสื่อมราคา
(รายเดือน / รายบรรทัด) and มูลค่าตามบัญชี.

The tests assert two things:

* the 7 wizard models are registered in the Odoo 19 registry, and
* the 7 compiled ``.jasper`` templates are shipped with the module.
"""
import os

from odoo.tests.common import TransactionCase

MODELS = (
    "asset.card.form",
    "asset.card.report",
    "asset.card.barcode.report",
    "asset.card.qrcode.report",
    "asset.depreciation.report",
    "asset.depreciation.line.report",
    "book.value.report",
)

JASPER_FILES = (
    "asset_card_form.jasper",
    "asset_card_report.jasper",
    "asset_card_barcode_report.jasper",
    "asset_card_qrcode_report.jasper",
    "asset_depreciation_report.jasper",
    "asset_depreciation_line_report.jasper",
    "book_value_report.jasper",
)


class TestFixedAssetsPorts(TransactionCase):
    """Odoo 19 port of the legacy ``dtr_fixed_assets_report`` reports."""

    def test_models_are_registered(self):
        for model in MODELS:
            self.assertIn(model, self.env)

    def test_default_jasper_file_matches_module(self):
        for model, name in zip(MODELS, JASPER_FILES):
            report = self.env[model].create({})
            self.assertTrue(
                report.jasper_file.endswith(name), report.jasper_file
            )

    def test_compiled_templates_are_shipped(self):
        report = self.env["asset.card.form"].create({})
        jrxml_dir = os.path.dirname(report.jasper_file)
        for name in JASPER_FILES:
            path = os.path.join(jrxml_dir, name)
            self.assertTrue(os.path.isfile(path), path)
            self.assertGreater(os.path.getsize(path), 0, path)
