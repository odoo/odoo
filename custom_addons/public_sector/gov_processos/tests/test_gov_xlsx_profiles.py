from odoo.tests.common import TransactionCase


class TestGovXlsxProfiles(TransactionCase):
    def test_process_scope_defaults_service_profile(self):
        processo = self.env["gov.processo"].create(
            {
                "subject": "Contratacao de servicos continuados",
                "process_scope": "servicos_continuados",
            }
        )

        self.assertEqual(processo.xlsx_profile, "service_continuous_labor")

    def test_doc_and_job_inherit_service_profile(self):
        processo = self.env["gov.processo"].create(
            {
                "subject": "Apoio administrativo continuado",
                "process_scope": "servicos_continuados",
            }
        )
        doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": processo.id,
                "name": "TR de servicos continuados",
                "doc_type": "tr",
            }
        )

        job = self.env["gov.processo.planilha.job"].create_from_doc(doc)

        self.assertEqual(doc.xlsx_profile, "service_continuous_labor")
        self.assertEqual(job.profile, "service_continuous_labor")

    def test_service_profile_builds_service_focused_payload(self):
        processo = self.env["gov.processo"].create(
            {
                "subject": "Servico continuado com postos",
                "process_scope": "servicos_continuados",
            }
        )
        self.env["gov.processo.planilha.item"].create(
            {
                "processo_id": processo.id,
                "lot_code": "1",
                "item_number": 1,
                "class_abc": "A",
                "lot_description": "Cobertura 12x36",
                "description": "Porteiro diurno",
                "unit": "Posto",
                "monthly_quantity": 4,
                "annual_quantity": 48,
                "unit_price": 3250.0,
                "specification": "CCT local e beneficios obrigatorios",
            }
        )

        payload = self.env["gov.xlsx.worker.service"].build_service_continuous_payload(processo)

        self.assertEqual(
            payload["metadata"]["summary_title"],
            f"RESUMO DE POSTOS E CUSTOS - {processo.name}",
        )
        self.assertTrue(
            payload["metadata"]["schedule_title"].startswith(
                "CRONOGRAMA DE COBERTURA E MEDICAO - "
            )
        )
        self.assertEqual(payload["items"][0]["description"], "Porteiro diurno")
        self.assertEqual(
            payload["metadata"]["regime_execucao"],
            "Execucao continuada com postos dedicados e cobertura mensal.",
        )
