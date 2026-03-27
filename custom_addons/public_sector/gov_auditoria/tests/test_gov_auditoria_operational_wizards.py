from odoo.tests.common import TransactionCase


class TestGovAuditoriaOperationalWizards(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY 2026 Operacional",
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

    def _create_cycle(self, state="em_analise"):
        ciclo = self.env["gov.auditoria.ciclo"].create(
            {
                "company_id": self.company.id,
                "exercicio_id": self.fiscal_year.id,
                "orgao_id": self.orgao.id,
                "tipo_prestacao": "especial",
                "modo_dados": "espelho",
            }
        )
        ciclo.state = state
        return ciclo

    def test_diligencia_wizard_creates_event_and_deadline(self):
        ciclo = self._create_cycle("em_analise")
        wizard = self.env["gov.auditoria.diligencia.wizard"].create(
            {
                "ciclo_id": ciclo.id,
                "descricao": "Diligencia de teste",
                "prazo_dias": 10,
                "criar_prazo": True,
            }
        )

        wizard.action_confirm()

        self.assertEqual(ciclo.state, "diligencia")
        self.assertTrue(ciclo.evento_ids.filtered(lambda evento: evento.tipo == "diligencia_emitida"))
        self.assertTrue(ciclo.prazo_ids.filtered(lambda prazo: prazo.descricao == "Prazo de resposta a diligencia"))

    def test_acordao_wizard_creates_decision_and_document(self):
        ciclo = self._create_cycle("julgamento")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "acordao_teste.pdf",
                "datas": "VEVTVEU=",
                "mimetype": "application/pdf",
            }
        )
        wizard = self.env["gov.auditoria.acordao.wizard"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo_decisao": "regular_com_ressalvas",
                "numero_acordao": "123/2026",
                "ementa": "Acordao de teste",
                "prazo_recurso_dias": 15,
                "attachment_ids": [(6, 0, [attachment.id])],
            }
        )

        wizard.action_confirm()

        self.assertEqual(ciclo.state, "acordao")
        self.assertTrue(ciclo.decisao_id)
        self.assertEqual(ciclo.decisao_id.numero_acordao, "123/2026")
        self.assertTrue(ciclo.documento_ids.filtered(lambda doc: doc.tipo == "acordao"))

    def test_apontamento_response_wizard_creates_defense_document(self):
        ciclo = self._create_cycle("diligencia")
        prazo = self.env["gov.auditoria.prazo"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "legal",
                "descricao": "Prazo de defesa",
                "data_inicio": "2026-03-01",
                "data_fim_legal": "2026-03-10",
            }
        )
        apontamento = self.env["gov.auditoria.apontamento"].create(
            {
                "ciclo_id": ciclo.id,
                "codigo": "AP-01",
                "descricao": "Apontamento de teste",
                "prazo_defesa_id": prazo.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "defesa_ap01.pdf",
                "datas": "VEVTVEU=",
                "mimetype": "application/pdf",
            }
        )
        wizard = self.env["gov.auditoria.apontamento.resposta.wizard"].create(
            {
                "ciclo_id": ciclo.id,
                "apontamento_id": apontamento.id,
                "resposta": "Resposta formal apresentada.",
                "protocolo_externo": "DEF-2026-1",
                "attachment_ids": [(6, 0, [attachment.id])],
            }
        )

        wizard.action_confirm()

        self.assertEqual(apontamento.state, "respondido")
        self.assertEqual(prazo.state, "cumprido")
        self.assertEqual(ciclo.state, "defesa")
        self.assertTrue(ciclo.documento_ids.filtered(lambda doc: doc.tipo == "defesa"))
        self.assertTrue(ciclo.evento_ids.filtered(lambda evt: evt.tipo == "resposta_defesa_enviada"))

    def test_determinacao_creates_deadline_and_can_be_completed(self):
        ciclo = self._create_cycle("acordao")
        decisao = self.env["gov.auditoria.decisao"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "regular_com_ressalvas",
                "numero_acordao": "321/2026",
                "ementa": "Decisao com determinacao",
            }
        )
        determinacao = self.env["gov.auditoria.determinacao"].create(
            {
                "decisao_id": decisao.id,
                "descricao": "Encaminhar comprovacao de ajuste.",
                "prazo_cumprimento": "2026-04-15",
            }
        )

        self.assertTrue(determinacao.prazo_id)
        self.assertEqual(determinacao.prazo_id.ciclo_id, ciclo)

        determinacao.action_mark_cumprido()

        self.assertEqual(determinacao.state, "cumprido")
        self.assertEqual(determinacao.prazo_id.state, "cumprido")
        self.assertTrue(ciclo.evento_ids.filtered(lambda evt: evt.tipo == "determinacao_cumprida"))

    def test_protocolo_wizard_marks_documents_sent_and_advances_cycle(self):
        ciclo = self._create_cycle("remessa")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "recibo_envio.pdf",
                "datas": "VEVTVEU=",
                "mimetype": "application/pdf",
            }
        )
        documento = self.env["gov.auditoria.documento"].create(
            {
                "ciclo_id": ciclo.id,
                "nome": "Balanco anual",
                "tipo": "relatorio",
                "origem": "manual",
                "state": "finalizado",
            }
        )
        wizard = self.env["gov.auditoria.protocolo.wizard"].create(
            {
                "ciclo_id": ciclo.id,
                "protocolo_externo": "PROTO-2026-001",
                "documento_ids": [(6, 0, [documento.id])],
                "recibo_attachment_id": attachment.id,
                "observacao": "Envio ao tribunal.",
            }
        )

        wizard.action_confirm()

        self.assertEqual(ciclo.state, "em_analise")
        self.assertEqual(ciclo.numero_protocolo, "PROTO-2026-001")
        self.assertEqual(documento.state, "enviado")
        self.assertEqual(documento.protocolo_externo, "PROTO-2026-001")
        self.assertTrue(ciclo.evento_ids.filtered(lambda evt: evt.tipo == "protocolo_envio"))
        self.assertTrue(
            ciclo.documento_ids.filtered(
                lambda doc: doc.tipo == "certidao" and doc.protocolo_externo == "PROTO-2026-001"
            )
        )
