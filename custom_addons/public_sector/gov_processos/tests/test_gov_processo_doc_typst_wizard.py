from odoo.tests.common import TransactionCase


class TestGovProcessoDocTypstWizard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.processo = self.env["gov.processo"].create(
            {
                "subject": "Aquisicao de material hospitalar",
            }
        )
        self.source_doc = self.env["gov.processo.doc"].create(
            {
                "processo_id": self.processo.id,
                "doc_type": "dfd",
                "name": "DFD Recebido",
                "latex_source": r"\section{DFD}",
                "pdf_file": "cGRm",
                "pdf_filename": "dfd-recebido.pdf",
                "dfd_area_requisitante": "Diretoria Administrativa",
                "dfd_objeto": "<p>Aquisicao de material hospitalar.</p>",
                "dfd_justificativa": "<p>Reposicao urgente do estoque.</p>",
            }
        )

    def test_default_values_follow_selected_model(self):
        Wizard = self.env["gov.processo.doc.typst.wizard"].with_context(
            default_processo_id=self.processo.id,
            default_modelo_typst="dfd_padrao",
        )
        defaults = Wizard.default_get(
            [
                "processo_id",
                "modelo_typst",
                "doc_type",
                "name",
                "titulo",
                "subtitulo",
                "objeto",
                "incluir_peca_dfd",
            ]
        )
        wizard = Wizard.create(defaults)

        self.assertEqual(wizard.doc_type, "dfd")
        self.assertIn("Formalizacao de Demanda", wizard.titulo)
        self.assertIn(self.processo.name or "Novo", wizard.name)
        self.assertEqual(wizard.source_doc_id, self.source_doc)
        self.assertTrue(wizard.incluir_peca_dfd)
        self.assertEqual(wizard.area_requisitante, "Diretoria Administrativa")
        self.assertIn("Aquisicao de material hospitalar", wizard.objeto)
        self.assertIn("Reposicao urgente do estoque", wizard.justificativa)

    def test_create_document_persists_typst_source(self):
        wizard = self.env["gov.processo.doc.typst.wizard"].create(
            {
                "processo_id": self.processo.id,
                "source_doc_id": self.source_doc.id,
                "modelo_typst": "justificativa_emergencial",
                "doc_type": "outro",
                "name": "Justificativa Emergencial",
                "titulo": "Justificativa de Situacao Emergencial",
                "subtitulo": "Autoclave hospitalar",
                "objeto": "Aquisicao emergencial de autoclave hospitalar.",
                "justificativa": "A unidade esta sem equipamento funcional.",
                "fatos_relevantes": "O laudo tecnico aponta risco a continuidade assistencial.",
                "pontos_chave": "Risco assistencial\nUrgencia comprovada\nObjeto delimitado",
                "quadro_resumo": "Valor estimado: R$ 200.000,00\nFundamento: Art. 75, VIII",
                "encaminhamento": "Submeter a autoridade competente para autorizacao.",
                "incluir_peca_justificativa": True,
                "incluir_peca_despacho": True,
                "assinante_nome": "Servidor Responsavel",
                "assinante_cargo": "Diretor Administrativo",
                "gerar_pdf_imediatamente": False,
            }
        )

        action = wizard.action_criar_documento()
        doc = self.env["gov.processo.doc"].browse(action["res_id"])

        self.assertEqual(doc.processo_id, self.processo)
        self.assertEqual(doc.name, "Justificativa Emergencial")
        self.assertTrue(doc.typst_source)
        self.assertEqual(doc.latex_source, r"\section{DFD}")
        self.assertIn("#let dados = (", doc.typst_source)
        self.assertIn("justificativa(dados)", doc.typst_source)
        self.assertIn("despacho(dados)", doc.typst_source)
        self.assertIn("Urgencia comprovada", doc.typst_source)
        self.assertIn("Valor estimado", doc.typst_source)
        self.assertTrue(doc.dados_snapshot)

    def test_open_builder_creates_active_document_for_manual_typst(self):
        wizard = self.env["gov.processo.doc.typst.wizard"].create(
            {
                "processo_id": self.processo.id,
                "source_doc_id": self.source_doc.id,
                "edit_mode": "manual_typst",
                "doc_type": "outro",
                "name": "Minuta Manual",
                "titulo": "Minuta Manual",
                "objeto": "Objeto inicial.",
                "typst_source_manual": '= "Documento manual"\n',
                "gerar_pdf_imediatamente": False,
            }
        )

        action = wizard.action_abrir_builder()

        self.assertTrue(wizard.active_doc_id)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "gov_document_builder")
        self.assertEqual(action["params"]["doc_id"], wizard.active_doc_id.id)
        self.assertEqual(action["params"]["initial_mode"], "typst")
        self.assertEqual(action["params"]["return_action"]["res_model"], "gov.processo.doc.typst.wizard")
        self.assertEqual(action["params"]["return_action"]["res_id"], wizard.id)
        self.assertEqual(action["params"]["return_action"]["views"], [(False, "form")])
        self.assertEqual(wizard.active_doc_id.typst_source, '= "Documento manual"\n')

    def test_create_document_reuses_active_document_in_manual_mode(self):
        wizard = self.env["gov.processo.doc.typst.wizard"].create(
            {
                "processo_id": self.processo.id,
                "source_doc_id": self.source_doc.id,
                "edit_mode": "manual_typst",
                "doc_type": "outro",
                "name": "Documento Ativo Reutilizado",
                "titulo": "Documento Ativo Reutilizado",
                "objeto": "Objeto inicial.",
                "gerar_pdf_imediatamente": False,
            }
        )

        wizard.action_abrir_builder()
        active_doc = wizard.active_doc_id
        active_doc.write({"typst_source": '= "Alterado no builder"\n'})

        action = wizard.action_criar_documento()
        doc = self.env["gov.processo.doc"].browse(action["res_id"])

        self.assertEqual(doc, active_doc)
        self.assertEqual(doc.name, "Documento Ativo Reutilizado")
        self.assertEqual(doc.typst_source, '= "Alterado no builder"\n')

    def test_sync_manual_source_from_active_document(self):
        wizard = self.env["gov.processo.doc.typst.wizard"].create(
            {
                "processo_id": self.processo.id,
                "source_doc_id": self.source_doc.id,
                "edit_mode": "manual_typst",
                "doc_type": "outro",
                "name": "Sincronizar Documento Ativo",
                "titulo": "Sincronizar Documento Ativo",
                "objeto": "Objeto inicial.",
                "typst_source_manual": '= "Rascunho local"\n',
                "gerar_pdf_imediatamente": False,
            }
        )

        wizard.action_abrir_builder()
        wizard.active_doc_id.write({"typst_source": '= "Atualizado no builder"\n'})

        action = wizard.action_sincronizar_do_documento_ativo()

        self.assertEqual(action["res_model"], "gov.processo.doc.typst.wizard")
        self.assertEqual(action["res_id"], wizard.id)
        self.assertEqual(wizard.typst_source_manual, '= "Atualizado no builder"\n')
