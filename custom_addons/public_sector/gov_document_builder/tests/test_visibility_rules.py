from odoo.tests.common import TransactionCase


class TestGovDocumentVisibilityRules(TransactionCase):
    def setUp(self):
        super().setUp()
        self.resolver = self.env["gov.document.context.resolver"]

    def test_exists_operator_returns_true_for_non_empty_value(self):
        context = {
            "execution": {
                "ordens_fornecimento_count": 3,
            }
        }

        result = self.resolver.evaluate_visibility_rule(
            "execution.ordens_fornecimento_count exists",
            context,
        )

        self.assertTrue(result)

    def test_not_exists_operator_returns_true_for_empty_value(self):
        context = {
            "auction": {
                "fornecedor": "",
            }
        }

        result = self.resolver.evaluate_visibility_rule(
            "auction.fornecedor not_exists",
            context,
        )

        self.assertTrue(result)

    def test_invalid_rule_fails_open(self):
        context = {"process": {"subject": "Teste"}}

        result = self.resolver.evaluate_visibility_rule("regra_invalida", context)

        self.assertTrue(result)
