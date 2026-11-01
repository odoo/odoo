# -*- coding: utf-8 -*-
"""Port checks for the legacy ``receipt_report`` Jasper report.

The wizard is the multi-payment ``receipt.report`` model ported from the
Odoo 15 ``dtr_accounting_report`` module.  These tests assert the model is
registered and that both compiled templates ship with the module on disk.
"""
import os

from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestReceiptReportPort(TransactionCase):
    def test_model_is_registered(self):
        report = self.env["receipt.report"]
        self.assertEqual(report._name, "receipt.report")
        self.assertEqual(report._description, "Receipt Report")
        self.assertEqual(list(report._inherit), ["od19.jasper.report"])

    def _shipped(self, model):
        report = self.env[model].create({})
        self.assertTrue(report.jasper_file.endswith(".jasper"))
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)
        return report

    def test_main_template_is_shipped(self):
        report = self._shipped("receipt.report")
        self.assertTrue(report.jasper_file.endswith("receipt_report.jasper"))

    def test_cheque_subreport_is_shipped(self):
        report = self.env["receipt.report"].create({})
        subreport = os.path.join(
            os.path.dirname(report.jasper_file), "sub_receipt_cheque.jasper"
        )
        self.assertTrue(os.path.isfile(subreport), subreport)

    def test_parameters_follow_legacy_contract(self):
        report = self.env["receipt.report"].with_context(
            active_ids=[1, 2], iscopy=1
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "where pay.id in (1, 2)")
        self.assertEqual(parameters["iscopy"], "1")

    def test_parameters_default_to_original_copy(self):
        report = self.env["receipt.report"].with_context(
            active_ids=[7]
        ).create({})
        self.assertEqual(report.get_parameters()["iscopy"], "0")
