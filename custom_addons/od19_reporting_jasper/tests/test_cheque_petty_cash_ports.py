import os

from odoo.tests.common import TransactionCase


class TestChequePettyCashPorts(TransactionCase):
    """Jasper ports of the legacy cheque / petty-cash reports.

    Verifies that the three wizard models are registered and that their
    compiled ``.jasper`` templates ship with the module.
    """

    MODELS = (
        "cheque.balance.report",
        "petty.cash.request.report",
        "petty.cash.payment.report",
    )

    def _shipped(self, model):
        report = self.env[model].create({})
        self.assertTrue(report.jasper_file.endswith(".jasper"))
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)
        return report

    def test_models_are_registered(self):
        for model in self.MODELS:
            self.assertIn(model, self.env)

    def test_compiled_templates_are_shipped(self):
        self.assertTrue(
            self._shipped("cheque.balance.report").jasper_file.endswith(
                "cheque_balance_report.jasper"
            )
        )
        self.assertTrue(
            self._shipped("petty.cash.request.report").jasper_file.endswith(
                "petty_cash_request_report.jasper"
            )
        )
        self.assertTrue(
            self._shipped("petty.cash.payment.report").jasper_file.endswith(
                "petty_cash_payment_report.jasper"
            )
        )
