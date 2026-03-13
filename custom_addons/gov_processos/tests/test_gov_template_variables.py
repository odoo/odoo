from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGovTemplateVariables(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Aquisição de materiais de limpeza",
            }
        )
        self.template = self.env["gov.ai.template"].create(
            {
                "name": "Template DFD Dinâmico",
                "doc_type": "dfd",
                "process_type": "compras_servicos",
                "process_scope": "all",
                "fase": 0,
                "output_format": "latex",
                "parameter_spec_json": """
                {
                  "optional": [
                    {"key": "numero_processo_externo", "type": "string", "fase": 0},
                    {"key": "valor_total_planejado", "type": "string", "fase": 1}
                  ]
                }
                """,
                "latex_template": r"""
\section*{DFD}
Processo interno: {{processo_numero}}
Processo externo: {{numero_processo_externo}}
Valor planejado: {{valor_total_planejado}}
                """,
            }
        )
        self.doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "name": "DFD Teste",
                "doc_type": "dfd",
                "ai_template_id": self.template.id,
            }
        )

    def test_sync_parameters_by_phase(self):
        params = self.processo.parameter_ids.sorted("key")
        self.assertEqual(params.mapped("key"), ["numero_processo_externo", "valor_total_planejado"])
        status_by_key = {rec.key: rec.status for rec in params}
        self.assertEqual(status_by_key["numero_processo_externo"], "aberta")
        self.assertEqual(status_by_key["valor_total_planejado"], "pendente")

    def test_apply_latex_template_uses_process_variables(self):
        external_number = self.processo.parameter_ids.filtered(
            lambda rec: rec.key == "numero_processo_externo"
        )
        external_number.write({"value_text": "SEI-2026/000123"})

        self.doc.action_apply_template_latex()

        self.assertIn(self.processo.name, self.doc.latex_source)
        self.assertIn("SEI-2026/000123", self.doc.latex_source)

    def test_closed_phase_parameter_cannot_be_edited(self):
        external_number = self.processo.parameter_ids.filtered(
            lambda rec: rec.key == "numero_processo_externo"
        )
        self.processo.action_avancar_fase()

        with self.assertRaises(ValidationError):
            external_number.write({"value_text": "ALTERADO-DEPOIS"})
