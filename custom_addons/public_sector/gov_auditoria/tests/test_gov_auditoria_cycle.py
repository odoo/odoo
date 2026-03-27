from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests.common import TransactionCase


class TestGovAuditoriaCycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        if "gov_public_accounting_enabled" in cls.company._fields:
            cls.company.write(
                {
                    "gov_public_accounting_enabled": True,
                    "fiscalyear_lock_date": "2025-12-31",
                }
            )
        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY 2025 Auditoria",
                "company_id": cls.company.id,
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        )
        cls.orgao = cls.env.ref("gov_auditoria.gov_auditoria_orgao_tce")
        cls.env.user.write(
            {
                "group_ids": [
                    (4, cls.env.ref("gov_auditoria.group_auditoria_manager").id),
                    (4, cls.env.ref("gov_auditoria.group_auditoria_admin").id),
                ]
            }
        )

    def test_cycle_unique_constraint(self):
        orgao_unique = self.env["gov.auditoria.orgao"].create(
            {
                "name": "Tribunal Teste Unicidade",
                "sigla": "TTU",
                "tipo": "tce",
            }
        )
        self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": orgao_unique.id,
                "tipo_prestacao": "ordinaria",
            }
        )
        with self.cr.savepoint(), self.assertRaises(IntegrityError):
            self.env["gov.auditoria.ciclo"].create(
                {
                    "company_id": self.company.id,
                    "exercicio_id": self.fiscal_year.id,
                    "orgao_id": orgao_unique.id,
                    "tipo_prestacao": "ordinaria",
                }
            )

    def test_remessa_creates_checklist_and_deadline(self):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "especial",
                "mapeamento_validado": True,
            }
        )
        ciclo.action_to_consolidacao()
        ciclo.action_to_conferencia()
        ciclo.action_to_remessa()
        self.assertEqual(ciclo.state, "remessa")
        self.assertTrue(ciclo.checklist_id)
        self.assertTrue(ciclo.prazo_ids)

    def test_dashboard_flags_and_actions_follow_cycle_pendencies(self):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "tomada_de_contas_especial",
                "modo_dados": "espelho",
            }
        )
        prazo = self.env["gov.auditoria.prazo"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "legal",
                "descricao": "Prazo vencido",
                "data_inicio": "2025-01-01",
                "data_fim_legal": "2025-01-10",
            }
        )
        documento = self.env["gov.auditoria.documento"].create(
            {
                "ciclo_id": ciclo.id,
                "nome": "Documento pendente",
                "tipo": "relatorio",
                "origem": "manual",
                "state": "finalizado",
            }
        )
        apontamento = self.env["gov.auditoria.apontamento"].create(
            {
                "ciclo_id": ciclo.id,
                "descricao": "Apontamento em aberto",
            }
        )
        decisao = self.env["gov.auditoria.decisao"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "regular_com_ressalvas",
                "numero_acordao": "456/2025",
                "ementa": "Decisao para painel",
            }
        )
        determinacao = self.env["gov.auditoria.determinacao"].create(
            {
                "decisao_id": decisao.id,
                "descricao": "Determinacao pendente",
                "prazo_cumprimento": "2026-01-30",
            }
        )

        self.assertTrue(ciclo.has_prazo_vencido)
        self.assertTrue(ciclo.has_documento_pendente)
        self.assertTrue(ciclo.has_apontamento_aberto)
        self.assertTrue(ciclo.has_determinacao_pendente)
        self.assertTrue(ciclo.has_pendencia_critica)
        self.assertTrue(ciclo.has_pendencia_operacional)
        self.assertEqual(ciclo.action_open_overdue_deadlines()["domain"], [("ciclo_id", "=", ciclo.id), ("state", "=", "vencido")])
        self.assertEqual(
            ciclo.action_open_pending_documents()["domain"],
            [("ciclo_id", "=", ciclo.id), ("state", "in", ["rascunho", "finalizado"])],
        )
        self.assertEqual(
            ciclo.action_open_open_findings()["domain"],
            [("ciclo_id", "=", ciclo.id), ("state", "in", ["aberto", "respondido"])],
        )
        self.assertEqual(
            ciclo.action_open_pending_determinations()["domain"],
            [("decisao_id", "=", decisao.id), ("state", "in", ["pendente", "parcial", "descumprido"])],
        )
        self.assertEqual(prazo.state, "vencido")
        self.assertEqual(documento.state, "finalizado")
        self.assertEqual(apontamento.state, "aberto")
        self.assertEqual(determinacao.state, "pendente")

    def test_executive_action_uses_operational_defaults(self):
        action = self.env.ref("gov_auditoria.action_gov_auditoria_ciclo_executivo").read()[0]

        self.assertEqual(action["res_model"], "gov.auditoria.ciclo")
        self.assertIn("search_default_f_exec", action["context"])
        self.assertIn("search_default_g_company", action["context"])

    def test_operational_activity_sync_creates_and_clears_activities(self):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "especial",
                "responsavel_ids": [(6, 0, [self.env.user.id])],
                "modo_dados": "espelho",
            }
        )
        prazo = self.env["gov.auditoria.prazo"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "legal",
                "descricao": "Prazo muito proximo",
                "data_inicio": fields.Date.today(),
                "data_fim_legal": fields.Date.today(),
            }
        )
        documento = self.env["gov.auditoria.documento"].create(
            {
                "ciclo_id": ciclo.id,
                "nome": "Documento nao enviado",
                "tipo": "relatorio",
                "origem": "manual",
                "state": "finalizado",
            }
        )
        decisao = self.env["gov.auditoria.decisao"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "regular_com_ressalvas",
                "numero_acordao": "789/2025",
                "ementa": "Decisao para atividades",
            }
        )
        determinacao = self.env["gov.auditoria.determinacao"].create(
            {
                "decisao_id": decisao.id,
                "descricao": "Pendencia de cumprimento",
                "prazo_cumprimento": fields.Date.today(),
            }
        )

        ciclo._sync_operational_activities()
        activities = self.env["mail.activity"].search(
            [("res_model", "=", "gov.auditoria.ciclo"), ("res_id", "=", ciclo.id)]
        )
        self.assertEqual(set(activities.mapped("summary")), {"Prazo proximo", "Documento pendente", "Cumprimento pendente"})

        documento.write({"state": "enviado"})
        determinacao.action_mark_cumprido()
        prazo.write({"state": "cumprido"})
        ciclo._sync_operational_activities()

        remaining = self.env["mail.activity"].search(
            [("res_model", "=", "gov.auditoria.ciclo"), ("res_id", "=", ciclo.id)]
        )
        self.assertFalse(remaining)

    def test_dossier_typst_generation_creates_versioned_document(self):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "especial",
                "responsavel_ids": [(6, 0, [self.env.user.id])],
                "mapeamento_validado": True,
            }
        )
        self.env["gov.auditoria.documento"].create(
            {
                "ciclo_id": ciclo.id,
                "nome": "Parecer tecnico",
                "tipo": "relatorio",
                "origem": "manual",
                "state": "finalizado",
            }
        )
        self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "protocolo_envio",
                "descricao": "Envio inicial ao orgao",
            }
        )
        self.env["gov.auditoria.prazo"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "legal",
                "descricao": "Prazo principal",
                "data_inicio": "2025-01-01",
                "data_fim_legal": "2025-01-31",
            }
        )

        with patch(
            "odoo.addons.gov_auditoria.models.gov_auditoria_ciclo.GovTypstService.compile",
            return_value=b"%PDF-1.4 fake dossier pdf",
        ) as compile_mock:
            ciclo.action_generate_dossier_typst()
            compile_mock.assert_called_once()

            first = self.env["gov.auditoria.documento"].search(
                [
                    ("ciclo_id", "=", ciclo.id),
                    ("nome", "=", f"Dossie Consolidado - {ciclo.name}"),
                ],
                order="versao desc, id desc",
                limit=1,
            )
            self.assertEqual(first.versao, 1)
            self.assertEqual(first.state, "finalizado")
            self.assertTrue(first.attachment_id)
            self.assertTrue(first.source_attachment_id)
            self.assertEqual(first.source_attachment_id.mimetype, "text/plain")
            self.assertEqual(first.hash_sha256, "3f4286682d9871c15984c4d3961918553c42e8b6ee931c52077c479d37e263aa")

            ciclo.action_generate_dossier_typst()

        docs = self.env["gov.auditoria.documento"].search(
            [
                ("ciclo_id", "=", ciclo.id),
                ("nome", "=", f"Dossie Consolidado - {ciclo.name}"),
            ],
            order="versao asc, id asc",
        )
        self.assertEqual(docs.mapped("versao"), [1, 2])
        self.assertEqual(docs[0].state, "substituido")
        self.assertEqual(docs[1].state, "finalizado")
        self.assertEqual(docs[1].versao_anterior_id, docs[0])
