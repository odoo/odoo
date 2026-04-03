import json

from odoo.tests.common import TransactionCase


class TestGovDocumentLayoutNormalizer(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Normalizer Teste",
                "code": "normalizer_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Normalizer Teste",
                "code": "template_normalizer_test",
                "document_type_id": self.document_type.id,
            }
        )
        self.normalizer = self.env["gov.document.layout.normalizer"]

    def test_normalize_returns_sequence_ordered_nodes(self):
        payload = json.dumps(
            [
                {"id": "n2", "type": "richtext", "sequence": 20, "props": {}},
                {"id": "n1", "type": "heading1", "sequence": 10, "props": {}},
            ]
        )

        nodes = self.normalizer.normalize(payload)

        self.assertEqual([node["id"] for node in nodes], ["n1", "n2"])

    def test_normalize_invalid_json_returns_empty_list(self):
        nodes = self.normalizer.normalize("{json inválido")

        self.assertEqual(nodes, [])

    def test_validate_detects_duplicate_ids(self):
        nodes = [
            {"id": "dup", "type": "heading1", "sequence": 10, "props": {}, "binding": {}},
            {"id": "dup", "type": "richtext", "sequence": 20, "props": {}, "binding": {}},
        ]

        errors = self.normalizer.validate(nodes)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["node_id"], "dup")
