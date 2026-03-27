from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestGovProcessosSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "UG Segregada B"})

        group_operador = cls.env.ref("gov_base.group_gov_operador")
        group_gestor = cls.env.ref("gov_base.group_gov_gestor")

        cls.user_operador_a = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Operador UG A",
                "login": "operador.uga@example.com",
                "email": "operador.uga@example.com",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "group_ids": [(6, 0, [group_operador.id])],
            }
        )
        cls.user_gestor = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Gestor Multi UG",
                "login": "gestor.multi@example.com",
                "email": "gestor.multi@example.com",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
                "group_ids": [(6, 0, [group_gestor.id])],
            }
        )

        cls.processo_a = cls.env["gov.processo"].create(
            {
                "subject": "Processo da UG A",
                "ug_id": cls.company_a.id,
            }
        )
        cls.processo_b = cls.env["gov.processo"].create(
            {
                "subject": "Processo da UG B",
                "ug_id": cls.company_b.id,
            }
        )
        cls.doc_a = cls.env["gov.processo.doc"].create(
            {
                "processo_id": cls.processo_a.id,
                "name": "Documento UG A",
                "doc_type": "despacho",
            }
        )
        cls.doc_b = cls.env["gov.processo.doc"].create(
            {
                "processo_id": cls.processo_b.id,
                "name": "Documento UG B",
                "doc_type": "despacho",
            }
        )
        cls.tramite_a = cls.env["gov.processo.tramite"].with_context(skip_tramite_chatter=True).create(
            {
                "processo_id": cls.processo_a.id,
                "action": "despacho",
            }
        )
        cls.tramite_b = cls.env["gov.processo.tramite"].with_context(skip_tramite_chatter=True).create(
            {
                "processo_id": cls.processo_b.id,
                "action": "despacho",
            }
        )

    def test_operador_fica_isolado_na_propria_ug(self):
        Processo = self.env["gov.processo"].with_user(self.user_operador_a)
        Documento = self.env["gov.processo.doc"].with_user(self.user_operador_a)
        Tramite = self.env["gov.processo.tramite"].with_user(self.user_operador_a)

        self.assertEqual(Processo.search_count([("id", "=", self.processo_a.id)]), 1)
        self.assertEqual(Processo.search_count([("id", "=", self.processo_b.id)]), 0)
        self.assertEqual(Documento.search_count([("id", "=", self.doc_a.id)]), 1)
        self.assertEqual(Documento.search_count([("id", "=", self.doc_b.id)]), 0)
        self.assertEqual(Tramite.search_count([("id", "=", self.tramite_a.id)]), 1)
        self.assertEqual(Tramite.search_count([("id", "=", self.tramite_b.id)]), 0)

        with self.assertRaises(AccessError):
            Processo.browse(self.processo_b.id).read(["subject"])

    def test_gestor_com_duas_ugs_visualiza_ambos_os_lados(self):
        Processo = self.env["gov.processo"].with_user(self.user_gestor)
        Documento = self.env["gov.processo.doc"].with_user(self.user_gestor)
        Tramite = self.env["gov.processo.tramite"].with_user(self.user_gestor)

        self.assertEqual(Processo.search_count([("id", "in", [self.processo_a.id, self.processo_b.id])]), 2)
        self.assertEqual(Documento.search_count([("id", "in", [self.doc_a.id, self.doc_b.id])]), 2)
        self.assertEqual(Tramite.search_count([("id", "in", [self.tramite_a.id, self.tramite_b.id])]), 2)
