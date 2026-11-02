import os

from odoo.tests.common import TransactionCase

MODELS = ("sales.tax.report", "purchase.tax.report", "tax.invoice.report")


class TestTaxPorts(TransactionCase):
    """The three tax Jasper wizards ported from ``dtr_taxation`` /
    ``dtr_invoicing_report`` must be registered and ship a compiled template.
    """

    def test_models_are_registered(self):
        for model in MODELS:
            self.assertIn(model, self.env, "model %s is not registered" % model)

    def test_compiled_templates_are_shipped(self):
        for model in MODELS:
            report = self.env[model].create({})
            self.assertTrue(
                report.jasper_file.endswith(".jasper"), report.jasper_file
            )
            self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)
