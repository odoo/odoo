from psycopg2 import IntegrityError

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
