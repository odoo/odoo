from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGovAuditoriaChecklist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        if "gov_public_accounting_enabled" in cls.company._fields:
            cls.company.write(
                {
                    "gov_public_accounting_enabled": True,
                    "fiscalyear_lock_date": "2026-12-31",
                }
            )
        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY 2026 Checklist",
                "company_id": cls.company.id,
                "date_from": "2026-01-01",
                "date_to": "2026-12-31",
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

    def _create_cycle(self):
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
        return ciclo

    def test_open_checklist_creates_structure(self):
        ciclo = self._create_cycle()

        action = ciclo.action_open_checklist()

        self.assertTrue(ciclo.checklist_id)
        self.assertEqual(action["res_model"], "gov.auditoria.checklist")
        self.assertEqual(action["res_id"], ciclo.checklist_id.id)
        self.assertTrue(ciclo.checklist_id.item_ids)

    def test_checklist_item_state_actions_update_progress(self):
        ciclo = self._create_cycle()
        checklist = ciclo.checklist_id
        item = checklist.item_ids[0]
        optional_item = checklist.item_ids.filtered(lambda rec: not rec.obrigatorio)[:1]
        if not optional_item:
            optional_item = self.env["gov.auditoria.checklist.item"].create(
                {
                    "checklist_id": checklist.id,
                    "descricao": "Item opcional",
                    "obrigatorio": False,
                }
            )

        item.action_mark_ok()
        optional_item.action_mark_na()

        self.assertEqual(item.state, "ok")
        self.assertEqual(optional_item.state, "na")
        self.assertGreater(checklist.progresso, 0.0)
        self.assertGreaterEqual(ciclo.checklist_progresso, checklist.progresso)

    def test_required_item_cannot_be_marked_na(self):
        ciclo = self._create_cycle()
        required_item = ciclo.checklist_id.item_ids.filtered("obrigatorio")[:1]

        with self.assertRaises(ValidationError):
            required_item.action_mark_na()
