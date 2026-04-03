from odoo.tests.common import TransactionCase


class TestGovDocumentContextResolver(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Contexto Teste",
                "code": "context_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Contexto Teste",
                "code": "template_context_test",
                "document_type_id": self.document_type.id,
            }
        )
        self.resolver = self.env["gov.document.context.resolver"]

    def test_resolve_binding_process_objeto(self):
        context = {
            "process": {
                "objeto": "Aquisição de medicamentos",
            }
        }
        binding = {
            "source": "process",
            "path": "objeto",
            "fallback": "",
        }

        value = self.resolver.resolve_binding(binding, context)

        self.assertEqual(value, "Aquisição de medicamentos")

    def test_apply_transformer_strip_and_upper(self):
        self.assertEqual(self.resolver.apply_transformer("  semsa  ", "strip"), "semsa")
        self.assertEqual(self.resolver.apply_transformer("semsa", "upper"), "SEMSA")

    def test_resolve_binding_returns_fallback_for_missing_path(self):
        context = {"process": {"numero": "001/2026"}}
        binding = {
            "source": "process",
            "path": "objeto",
            "fallback": "não informado",
        }

        value = self.resolver.resolve_binding(binding, context)

        self.assertEqual(value, "não informado")
