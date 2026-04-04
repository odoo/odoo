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

    def test_apply_transformer_percentual_and_lista_br(self):
        self.assertEqual(self.resolver.apply_transformer(0.125, "percentual"), "12,50%")
        self.assertEqual(
            self.resolver.apply_transformer(
                ["Lei 14.133/2021", "regulamento local", "parecer jurídico"],
                "lista_br",
            ),
            "Lei 14.133/2021, regulamento local e parecer jurídico",
        )

    def test_resolve_binding_returns_fallback_for_missing_path(self):
        context = {"process": {"numero": "001/2026"}}
        binding = {
            "source": "process",
            "path": "objeto",
            "fallback": "não informado",
        }

        value = self.resolver.resolve_binding(binding, context)

        self.assertEqual(value, "não informado")


class TestContextResolverFinancialCycle(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Financeiro Teste",
                "code": "finance_context_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Financeiro Teste",
                "code": "template_finance_context_test",
                "document_type_id": self.document_type.id,
            }
        )
        self.process = self.env["gov.processo"].create(
            {
                "name": "SEMSA-2026-001",
                "subject": "Aquisição de medicamentos essenciais para UBS",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        self.env["gov.processo.parametro"].create(
            [
                {
                    "processo_id": self.process.id,
                    "key": "modalidade",
                    "name": "Modalidade da contratação",
                    "section": "required_by_law",
                    "fase": 2,
                    "value_type": "string",
                    "value_text": "Pregão Eletrônico",
                },
                {
                    "processo_id": self.process.id,
                    "key": "hipotese_dispensa",
                    "name": "Hipótese de dispensa",
                    "section": "required_by_law",
                    "fase": 1,
                    "value_type": "string",
                    "value_text": "Não se aplica",
                },
                {
                    "processo_id": self.process.id,
                    "key": "data_pesquisa_preco",
                    "name": "Data da pesquisa de preço",
                    "section": "optional",
                    "fase": 2,
                    "value_type": "date",
                    "value_text": "2026-04-04",
                },
            ]
        )
        self.env["gov.processo.planilha.item"].create(
            [
                {
                    "processo_id": self.process.id,
                    "lot_code": "1",
                    "item_number": 1,
                    "description": "Dipirona 500mg",
                    "unit": "un",
                    "annual_quantity": 200,
                    "unit_price": 45.50,
                },
                {
                    "processo_id": self.process.id,
                    "lot_code": "1",
                    "item_number": 2,
                    "description": "Amoxicilina 500mg",
                    "unit": "un",
                    "annual_quantity": 100,
                    "unit_price": 89.90,
                },
                {
                    "processo_id": self.process.id,
                    "lot_code": "1",
                    "item_number": 3,
                    "description": "Soro fisiológico 500ml",
                    "unit": "un",
                    "annual_quantity": 50,
                    "unit_price": 120.00,
                },
            ]
        )
        self.env["gov.processo.dotacao"].create(
            [
                {
                    "processo_id": self.process.id,
                    "programa": "10",
                    "acao": "2064",
                    "natureza_despesa": "3.3.90.39",
                    "fonte_recurso": "100",
                    "valor_estimado": 150000,
                    "exercicio": 2026,
                    "reservado": True,
                },
                {
                    "processo_id": self.process.id,
                    "programa": "10",
                    "acao": "2065",
                    "natureza_despesa": "3.3.90.30",
                    "fonte_recurso": "200",
                    "valor_estimado": 80000,
                    "exercicio": 2026,
                    "reservado": False,
                },
            ]
        )
        self.instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento Financeiro",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "process_id": self.process.id,
            }
        )
        self.resolver = self.env["gov.document.context.resolver"]

    def test_namespace_process_extracts_subject(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(
            context["process"]["subject"],
            "Aquisição de medicamentos essenciais para UBS",
        )

    def test_namespace_procurement_total_is_sum_of_items(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertAlmostEqual(context["procurement"]["valor_estimado_total"], 24090.0)

    def test_namespace_budget_empenhado_only_reserved(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(context["budget"]["valor_empenhado"], 150000)
        self.assertNotEqual(context["budget"]["valor_empenhado"], 230000)

    def test_namespace_reconciliation_is_computed(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertIn("reconciliation", context)
        self.assertIn(
            context["reconciliation"]["situacao_conciliacao"],
            {"regular", "pendente", "com_devolucao"},
        )

    def test_namespace_auction_returns_empty_dict_when_no_model(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(
            context["auction"],
            {
                "valor_arrematado": 0.0,
                "preco_unitario_final": 0.0,
                "fornecedor": "",
                "desconto_percentual": 0.0,
                "data_homologacao": "",
            },
        )

    def test_process_id_is_many2one_to_gov_processo(self):
        process_field = self.env["gov.document.instance"]._fields["process_id"]

        self.assertEqual(process_field.type, "many2one")
        self.assertEqual(process_field.comodel_name, "gov.processo")

    def test_resolve_instance_context_includes_financial_namespaces(self):
        context = self.resolver.resolve_instance_context(self.instance)

        for namespace in (
            "process",
            "legal",
            "procurement",
            "auction",
            "contract",
            "budget",
            "execution",
            "reconciliation",
        ):
            self.assertIn(namespace, context)

    def test_process_and_legal_namespaces_use_real_process_data(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(context["process"]["name"], self.process.name)
        self.assertEqual(
            context["process"]["subject"],
            "Aquisição de medicamentos essenciais para UBS",
        )
        self.assertEqual(context["legal"]["modalidade"], "Pregão Eletrônico")
        self.assertIn("Modalidade da contratação", context["legal"]["base_legal"])

    def test_procurement_namespace_aggregates_planilha_items(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertAlmostEqual(context["procurement"]["valor_estimado_total"], 24090.0)
        self.assertEqual(context["procurement"]["preco_unitario_referencia"], 45.50)
        self.assertEqual(context["procurement"]["quantidade_estimada_total"], 350)
        self.assertEqual(context["procurement"]["data_pesquisa_preco"], "2026-04-04")

    def test_budget_namespace_sums_only_reserved_dotacoes(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(context["budget"]["valor_empenhado"], 150000)
        self.assertEqual(context["budget"]["saldo_disponivel"], 0.0)
        self.assertEqual(context["budget"]["exercicio"], 2026)
        self.assertEqual(context["budget"]["natureza_despesa"], ["3.3.90.39", "3.3.90.30"])
        self.assertEqual(context["budget"]["fonte_recurso"], ["100", "200"])

    def test_legal_namespace_ignores_parameters_outside_required_by_law_filter(self):
        process = self.env["gov.processo"].create(
            {
                "name": "SEMSA-2026-002",
                "subject": "Aquisição de kits laboratoriais",
                "state": "execucao",
                "process_scope": "compras",
            }
        )
        self.env["gov.processo.parametro"].create(
            {
                "processo_id": process.id,
                "key": "modalidade",
                "name": "Modalidade fora da base legal",
                "section": "optional",
                "fase": 5,
                "value_type": "string",
                "value_text": "Registro de preços",
            }
        )
        instance = self.env["gov.document.instance"].create(
            {
                "name": "Documento sem base legal",
                "document_type_id": self.document_type.id,
                "template_id": self.template.id,
                "process_id": process.id,
            }
        )

        context = self.resolver.resolve_instance_context(instance)

        self.assertEqual(context["legal"]["base_legal"], [])
        self.assertEqual(context["legal"]["modalidade"], "")
        self.assertEqual(context["legal"]["hipotese_dispensa"], "")

    def test_contract_and_execution_namespaces_return_default_shapes_when_unavailable(self):
        context = self.resolver.resolve_instance_context(self.instance)

        self.assertEqual(
            context["contract"],
            {
                "valor_contratado": 0.0,
                "numero_contrato": "",
                "data_inicio_vigencia": "",
                "data_fim_vigencia": "",
                "quantidade_aditivos": 0,
                "saldo_restante": 0.0,
            },
        )
        self.assertEqual(
            context["execution"],
            {
                "valor_empenhado_acumulado": 0.0,
                "valor_liquidado_acumulado": 0.0,
                "ordens_fornecimento_count": 0,
                "quantidade_entregue": 0.0,
                "status_aceite_fiscal": "",
            },
        )

    def test_reconciliation_uses_liquidado_value_and_contract_deadline(self):
        context = self.resolver.resolve_instance_context(self.instance)
        context["auction"]["valor_arrematado"] = 21000.0
        context["contract"]["valor_contratado"] = 200000.0
        context["contract"]["data_fim_vigencia"] = "2026-05-31"
        context["execution"]["valor_liquidado_acumulado"] = 12500.0

        reconciliation = self.resolver.compute_reconciliation_namespace(context)

        self.assertEqual(reconciliation["valor_a_conciliar"], 137500.0)
        self.assertEqual(reconciliation["superavit"], 3090.0)
        self.assertEqual(reconciliation["deficit"], 0.0)
        self.assertEqual(reconciliation["situacao_conciliacao"], "pendente")
        self.assertEqual(reconciliation["prazo_conciliacao"], "2026-06-30")
