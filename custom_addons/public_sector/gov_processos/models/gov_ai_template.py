import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column, table_exists

from .constants import DOC_TYPE_SELECTION, PROCESS_TYPE_SELECTION, TEMPLATE_SCOPE_SELECTION
from .gov_template_service import GovTemplateService


class GovAiTemplate(models.Model):
    _name = "gov.ai.template"
    _description = "Template de IA para Geração de Documentos"
    _order = "doc_type, fase, id"
    _BUILTIN_CONTEXT_KEYS = {
        "ug_nome",
        "ug_cnpj",
        "exercicio",
        "processo_numero",
        "processo_assunto",
        "process_type",
        "process_scope",
        "origem",
        "doc_nome",
        "doc_tipo",
        "area_requisitante",
        "objeto",
        "justificativa",
        "quantidade",
        "valor_estimado",
        "data_necessidade",
        "vinculo_ppa",
        "responsavel_tecnico",
        "responsavel_processo",
        "hoje",
        "checklist_mode",
        "memoria_ug",
        "template_nome",
        "guidance_text",
        "output_format",
        "versao_normativa",
        "parameters_json",
        "option_catalog_json",
    }

    name = fields.Char(string="Nome", required=True)
    process_type = fields.Selection(
        PROCESS_TYPE_SELECTION,
        string="Tipo de Processo",
        default="compras_servicos",
        required=True,
    )
    process_scope = fields.Selection(
        TEMPLATE_SCOPE_SELECTION,
        string="Escopo (Compras/Serviços)",
        default="all",
        required=True,
        help=(
            "Permite segregar modelos por compras, serviços e serviços continuados. "
            "Use 'Todos os Escopos' para modelos genéricos."
        ),
    )
    is_checklist = fields.Boolean(
        string="É Checklist",
        help="Marque quando o template é uma lista de verificação.",
    )
    source_document = fields.Char(
        string="Documento de Origem",
        help="Arquivo/modelo normativo utilizado como referência didática.",
    )
    source_filename = fields.Char(string="Arquivo de Origem")
    source_input_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_source_format_selection(),
        string="Formato da Fonte Original",
        default="unknown",
        help="Formato original carregado no Knowledge ou por upload.",
    )
    source_native_text = fields.Text(
        string="Fonte Original",
        help="Conteúdo fonte preservado quando o arquivo for textual ou texto extraído da ingestão.",
    )
    guidance_text = fields.Text(
        string="Orientações de Preenchimento",
        help="Instruções didáticas para montagem do documento.",
    )
    parameter_spec_json = fields.Text(
        string="Parâmetros (JSON)",
        help="Esquema de parâmetros esperados para gerar o documento.",
    )
    option_catalog_json = fields.Text(
        string="Catálogo de Opções (JSON)",
        help="Opções orientadas do template (campos com escolhas).",
    )

    doc_type = fields.Selection(
        DOC_TYPE_SELECTION,
        string="Tipo de Documento",
        required=True,
    )
    fase = fields.Integer(string="Fase do Processo")
    versao_normativa = fields.Char(string="Base Normativa")
    prompt_system = fields.Text(string="Prompt Sistema")
    prompt_user_tpl = fields.Text(string="Prompt Usuário (template)")
    latex_source = fields.Text(string="Fonte LaTeX (compat)")
    latex_template = fields.Text(string="Template LaTeX")
    typst_template = fields.Text(string="Template Typst")
    output_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_target_format_selection(),
        default="latex",
    )
    active = fields.Boolean(default=True)

    def _auto_init(self):
        result = super()._auto_init()
        if table_exists(self.env.cr, "gov_ai_template"):
            if not column_exists(self.env.cr, "gov_ai_template", "source_filename"):
                create_column(self.env.cr, "gov_ai_template", "source_filename", "varchar")
            if not column_exists(self.env.cr, "gov_ai_template", "source_input_format"):
                create_column(self.env.cr, "gov_ai_template", "source_input_format", "varchar")
            if not column_exists(self.env.cr, "gov_ai_template", "source_native_text"):
                create_column(self.env.cr, "gov_ai_template", "source_native_text", "text")
            if not column_exists(self.env.cr, "gov_ai_template", "typst_template"):
                create_column(self.env.cr, "gov_ai_template", "typst_template", "text")
        return result

    def init(self):
        # Backfill de registros legados criados antes do campo "name" obrigatório.
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = COALESCE(NULLIF(TRIM(name), ''), CONCAT('Template #', id)),
                   process_type = COALESCE(process_type, 'compras_servicos'),
                   process_scope = COALESCE(process_scope, 'all'),
                   source_input_format = COALESCE(source_input_format, 'unknown')
             WHERE name IS NULL
                OR TRIM(name) = ''
                OR process_type IS NULL
                OR process_scope IS NULL
                OR source_input_format IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'DFD AGU - Lei 14.133 (Compras)'
             WHERE doc_type = 'dfd'
               AND name LIKE 'Template #%'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET process_scope = 'all'
             WHERE doc_type = 'dfd'
               AND name = 'DFD AGU - Lei 14.133 (Compras)'
            """
        )
        # Padronização AGU dos três modelos base de COMPRAS.
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Termo de Referência Compras Lei 14.133 (dezembro/2025)',
                   process_type = 'compras_servicos',
                   process_scope = 'compras'
             WHERE source_document = 'modelo-de-termo-de-referencia-compras-lei-no-14-133-dez-25.docx'
               AND COALESCE(process_type, 'compras_servicos') = 'compras_servicos'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Compras Lei 14.133 (dezembro/2025)',
                   process_type = 'compras_servicos',
                   process_scope = 'compras'
             WHERE source_document = 'modelo-de-termo-de-contrato-compras-lei-no-14-133-dez-25.docx'
               AND COALESCE(process_type, 'compras_servicos') = 'compras_servicos'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Lista de Verificação Compras e Serviços sem Mão de Obra exclusiva - Lei 14.133 (Set/24)',
                    process_type = 'compras_servicos',
                    process_scope = 'compras'
              WHERE source_document = 'modelo-de-lista-de-verificacao-compras-e-servicos-sem-mao-de-obra-exclusiva-lei-no-14-133-set-24.docx'
               AND COALESCE(process_scope, 'all') IN ('all', 'compras')
            """
        )
        # Padronização AGU para pacote SERVIÇOS SEM MÃO DE OBRA EXCLUSIVA.
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Termo de Referência único serviços (com, sem, engenharia) e obras Lei 14.133 (dezembro/2025)',
                   process_type = 'compras_servicos',
                   process_scope = 'servicos'
             WHERE source_document = 'modelo-de-termo-de-referencia-servicos-e-obras-lei-no-14-133-dez-25.docx'
               AND COALESCE(process_type, 'compras_servicos') = 'compras_servicos'
               AND COALESCE(process_scope, 'all') IN ('all', 'servicos')
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Serviços Sem Mão de Obra Lei 14.133 (dezembro/2025)',
                   process_type = 'compras_servicos',
                   process_scope = 'servicos'
             WHERE source_document = 'modelo-de-termo-de-contrato-servico-sem-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx'
               AND COALESCE(process_type, 'compras_servicos') = 'compras_servicos'
               AND COALESCE(process_scope, 'all') IN ('all', 'servicos')
            """
        )
        # Padronização AGU para pacote CONTRATAÇÕES DIRETAS (comum compras/serviços).
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Aviso de Contratação Direta Lei 14.133 (setembro/2025)',
                   process_type = 'contratacao_direta',
                   process_scope = 'all'
             WHERE source_document = 'modelo-de-aviso-de-contratacao-direta-lei-no-14-133-set-25.docx'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Edital Credenciamento Lei 14.133 (setembro/2025)',
                   process_type = 'contratacao_direta',
                   process_scope = 'all'
             WHERE source_document = 'modelo-de-edital-credenciamento-lei-no-14-133-set-25.docx'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Lista de Verificação Contratações Diretas Lei 14.133 (setembro/2024)',
                   process_type = 'contratacao_direta',
                   process_scope = 'all'
             WHERE source_document = 'modelo-de-lista-de-verificacao-contratacoes-diretas-lei-no-14-133-set-24.docx'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Termo de Referência Compras - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'compras'
             WHERE source_document = 'modelo-de-termo-de-referencia-compras-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
               AND COALESCE(process_scope, 'compras') = 'compras'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Compras - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'compras'
             WHERE source_document = 'modelo-de-termo-de-contrato-compras-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
               AND COALESCE(process_scope, 'compras') = 'compras'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Termo de Referência único serviços (com, sem, engenharia) e obras - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'servicos'
             WHERE source_document = 'modelo-de-termo-de-referencia-servicos-e-obras-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
               AND COALESCE(process_scope, 'servicos') = 'servicos'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Serviço Sem Mão de Obra - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'servicos'
             WHERE source_document = 'modelo-de-termo-de-contrato-servico-sem-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
               AND COALESCE(process_scope, 'servicos') = 'servicos'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Serviço com Mão de Obra Exclusiva - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'servicos_continuados'
             WHERE source_document = 'modelo-de-termo-de-contrato-servico-com-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET name = 'Modelo Contrato Obras e Serviços de Engenharia - Contratação Direta Lei 14.133 (dezembro/2025)',
                   process_scope = 'servicos'
             WHERE source_document = 'modelo-de-termo-de-contrato-obras-e-servicos-de-engenharia-lei-no-14-133-dez-25.docx'
              AND process_type = 'contratacao_direta'
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_ai_template
               SET process_type = 'contratacao_direta',
                   process_scope = 'servicos_continuados'
             WHERE source_document = 'modelo-de-termo-de-contrato-servico-com-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx'
               AND process_type = 'contratacao_direta'
            """
        )

        # Normalização dos três templates de COMPRAS para estrutura:
        # required_by_law / optional / additional_fields.
        source_docs = [
            "modelo-de-termo-de-referencia-compras-lei-no-14-133-dez-25.docx",
            "modelo-de-termo-de-contrato-compras-lei-no-14-133-dez-25.docx",
            "modelo-de-lista-de-verificacao-compras-e-servicos-sem-mao-de-obra-exclusiva-lei-no-14-133-set-24.docx",
            "modelo-de-termo-de-referencia-servicos-e-obras-lei-no-14-133-dez-25.docx",
            "modelo-de-termo-de-contrato-servico-sem-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx",
            "modelo-de-aviso-de-contratacao-direta-lei-no-14-133-set-25.docx",
            "modelo-de-edital-credenciamento-lei-no-14-133-set-25.docx",
            "modelo-de-lista-de-verificacao-contratacoes-diretas-lei-no-14-133-set-24.docx",
            "modelo-de-termo-de-contrato-servico-com-mao-de-obra-exclusiva-lei-no-14-133-dez-25.docx",
            "modelo-de-termo-de-contrato-obras-e-servicos-de-engenharia-lei-no-14-133-dez-25.docx",
        ]
        defaults_by_source = {
            source_docs[0]: {
                "optional": [
                    {"key": "descricao_solucao_como_um_todo", "type": "string"},
                    {"key": "requisitos_sustentabilidade", "type": "string"},
                    {"key": "garantia_tecnica_objeto", "type": "string"},
                    {"key": "cronograma_entrega", "type": "string"},
                    {"key": "matriz_risco_resumo", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "campo_adicional_1",
                        "type": "string",
                        "description": "Campo livre para exigência específica do órgão",
                    },
                    {
                        "key": "campo_adicional_2",
                        "type": "string",
                        "description": "Campo livre para condicionante local/normativa interna",
                    },
                ],
            },
            source_docs[1]: {
                "optional": [
                    {"key": "fiscal_titular_nome", "type": "string"},
                    {"key": "fiscal_substituto_nome", "type": "string"},
                    {"key": "rotina_reajuste_detalhada", "type": "string"},
                    {"key": "conta_vinculada_info", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "clausula_adicional_1",
                        "type": "string",
                        "description": "Cláusula adicional específica do órgão",
                    },
                    {
                        "key": "clausula_adicional_2",
                        "type": "string",
                        "description": "Condição operacional complementar",
                    },
                ],
            },
            source_docs[2]: {
                "optional": [
                    {"key": "numero_sessao", "type": "string"},
                    {"key": "auditor_revisor", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "bloco_local_1",
                        "type": "array",
                        "description": "Checklist adicional definido pela UG",
                    }
                ],
            },
            source_docs[3]: {
                "optional": [
                    {"key": "metodologia_execucao_servicos", "type": "string"},
                    {"key": "instrumento_medicao_resultado", "type": "string"},
                    {"key": "perfil_equipe_minima", "type": "string"},
                    {"key": "vistoria_regras", "type": "string"},
                    {"key": "cronograma_execucao", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "clausula_operacional_adicional_1",
                        "type": "string",
                        "description": "Campo livre para exigência técnica específica do serviço",
                    },
                    {
                        "key": "clausula_operacional_adicional_2",
                        "type": "string",
                        "description": "Campo livre para adequação local de execução",
                    },
                ],
            },
            source_docs[4]: {
                "optional": [
                    {"key": "fiscal_tecnico_nome", "type": "string"},
                    {"key": "fiscal_admin_nome", "type": "string"},
                    {"key": "regra_glosa_desempenho", "type": "string"},
                    {"key": "procedimento_reajuste", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "clausula_servico_adicional_1",
                        "type": "string",
                        "description": "Condição especial de execução de serviço sem dedicação exclusiva",
                    },
                    {
                        "key": "clausula_servico_adicional_2",
                        "type": "string",
                        "description": "Condição complementar definida pela UG",
                    },
                ],
            },
            source_docs[5]: {
                "optional": [
                    {"key": "admite_registro_precos", "type": "boolean"},
                    {"key": "disputa_por", "type": "string"},
                    {"key": "reserva_me_epp", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "regra_local_1",
                        "type": "string",
                        "description": "Campo livre para particularidade local do aviso",
                    },
                    {
                        "key": "regra_local_2",
                        "type": "string",
                        "description": "Campo livre para condição adicional da UG",
                    },
                ],
            },
            source_docs[6]: {
                "optional": [
                    {"key": "criterio_distribuicao_demandas", "type": "string"},
                    {"key": "vigencia_edital", "type": "string"},
                    {"key": "requisitos_tecnicos_especificos", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "regra_local_credenciamento_1",
                        "type": "string",
                        "description": "Regra operacional adicional do credenciamento",
                    },
                    {
                        "key": "regra_local_credenciamento_2",
                        "type": "string",
                        "description": "Regra local complementar",
                    },
                ],
            },
            source_docs[7]: {
                "optional": [
                    {"key": "auditor_revisor", "type": "string"},
                    {"key": "numero_sessao", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "bloco_local_1",
                        "type": "array",
                        "description": "Checklist adicional definido pela UG",
                    },
                ],
            },
            source_docs[8]: {
                "optional": [
                    {"key": "regras_substituicao_pessoal", "type": "string"},
                    {"key": "controle_encargos", "type": "string"},
                    {"key": "conta_vinculada", "type": "string"},
                    {"key": "criterios_glosa", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "clausula_adicional_com_mao_1",
                        "type": "string",
                        "description": "Cláusula específica para serviços com mão de obra exclusiva",
                    },
                    {
                        "key": "clausula_adicional_com_mao_2",
                        "type": "string",
                        "description": "Condição complementar definida pela UG",
                    },
                ],
            },
            source_docs[9]: {
                "optional": [
                    {"key": "cronograma_fisico_financeiro", "type": "string"},
                    {"key": "matriz_risco", "type": "string"},
                    {"key": "metodologia_medicao", "type": "string"},
                ],
                "additional_fields": [
                    {
                        "key": "clausula_adicional_engenharia_1",
                        "type": "string",
                        "description": "Condição específica de engenharia/obras",
                    },
                    {
                        "key": "clausula_adicional_engenharia_2",
                        "type": "string",
                        "description": "Condição complementar definida pela UG",
                    },
                ],
            },
        }

        templates = self.sudo().search([("source_document", "in", source_docs)])
        for template in templates:
            spec = template._json_field_as_obj("parameter_spec_json")
            if not isinstance(spec, dict):
                spec = {}
            changed_spec = False

            if "required_by_law" not in spec and "required" in spec:
                spec["required_by_law"] = spec.pop("required")
                changed_spec = True
            elif "required_by_law" not in spec:
                spec["required_by_law"] = []
                changed_spec = True

            source_defaults = defaults_by_source.get(template.source_document, {})
            if "optional" not in spec:
                spec["optional"] = source_defaults.get("optional", [])
                changed_spec = True
            if "additional_fields" not in spec:
                spec["additional_fields"] = source_defaults.get("additional_fields", [])
                changed_spec = True

            options = template._json_field_as_obj("option_catalog_json")
            if not isinstance(options, dict):
                options = {}
            changed_options = False
            if "segregacao_objeto" not in options:
                options["segregacao_objeto"] = [
                    "compras",
                    "servicos",
                    "servicos_prestacao_continuada",
                ]
                changed_options = True
            if template.source_document in [source_docs[2], source_docs[7]] and "blocos" in options:
                required_blocos = [
                    "fundamentacao_legal",
                    "pesquisa_precos",
                    "publicidade",
                    "formalizacao_contratual",
                    "controle_riscos",
                ]
                if template.source_document == source_docs[2]:
                    if template.process_type == "contratacao_direta":
                        required_blocos = [
                            "fundamentacao_legal",
                            "pesquisa_precos",
                            "metrica_medicao",
                            "formalizacao_contratual",
                            "controle_riscos",
                        ]
                    else:
                        required_blocos = [
                            "verificacao_comum",
                            "pesquisa_precos_orcamento",
                            "compras",
                            "servicos",
                            "servicos_prestacao_continuada",
                        ]
                if options.get("blocos") != required_blocos:
                    options["blocos"] = required_blocos
                    changed_options = True

            vals = {}
            if changed_spec:
                vals["parameter_spec_json"] = json.dumps(spec, ensure_ascii=False, indent=2)
            if changed_options:
                vals["option_catalog_json"] = json.dumps(options, ensure_ascii=False, indent=2)
            if vals:
                template.sudo().write(vals)

    @api.constrains("parameter_spec_json", "option_catalog_json")
    def _check_json_fields(self):
        for rec in self:
            for field_name in ("parameter_spec_json", "option_catalog_json"):
                raw = (rec[field_name] or "").strip()
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        f"JSON inválido no campo {field_name}: {exc}"
                    ) from exc
                if not isinstance(parsed, (dict, list)):
                    raise ValidationError(
                        f"O campo {field_name} deve conter objeto ou lista JSON."
                    )

    def _json_field_as_obj(self, field_name):
        self.ensure_one()
        raw = (self[field_name] or "").strip()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def get_parameter_spec(self):
        self.ensure_one()
        return self._json_field_as_obj("parameter_spec_json")

    def get_option_catalog(self):
        self.ensure_one()
        return self._json_field_as_obj("option_catalog_json")

    def get_parameter_entries(self):
        self.ensure_one()
        spec = self.get_parameter_spec()
        entries_by_key = {}
        sections = [
            ("required_by_law", True),
            ("required", True),
            ("optional", False),
            ("additional_fields", False),
            ("conditional", False),
        ]

        def _coerce_phase(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return int(self.fase or 0)

        for section_name, required in sections:
            raw_items = spec.get(section_name) if isinstance(spec, dict) else []
            if not isinstance(raw_items, list):
                continue
            for index, item in enumerate(raw_items, start=1):
                if isinstance(item, str):
                    item = {"key": item}
                if not isinstance(item, dict):
                    continue
                key = (item.get("key") or "").strip()
                if not key:
                    continue
                value_type = (item.get("type") or "string").strip()
                render_mode = (item.get("render_mode") or "").strip() or (
                    "latex" if value_type == "latex" else "text"
                )
                existing = entries_by_key.get(key, {})
                entries_by_key[key] = {
                    "key": key,
                    "label": item.get("label")
                    or item.get("name")
                    or existing.get("label")
                    or key.replace("_", " ").strip().capitalize(),
                    "description": item.get("description") or existing.get("description") or "",
                    "type": value_type or existing.get("type") or "string",
                    "render_mode": render_mode or existing.get("render_mode") or "text",
                    "section": existing.get("section")
                    if existing
                    and existing.get("section") == "required_by_law"
                    else ("required_by_law" if required else section_name),
                    "required": bool(required or existing.get("required")),
                    "phase": min(existing.get("phase", 999), _coerce_phase(item.get("fase")))
                    if existing
                    else _coerce_phase(item.get("fase")),
                    "doc_type": item.get("doc_type") or existing.get("doc_type") or self.doc_type,
                    "sequence": item.get("sequence") or existing.get("sequence") or (index * 10),
                }

        placeholder_text = "\n".join(
            part
            for part in [
                self.latex_template,
                self.typst_template,
                self.latex_source,
                self.source_native_text,
                self.prompt_user_tpl,
            ]
            if part
        )
        for index, key in enumerate(GovTemplateService.extract_placeholders(placeholder_text), start=1):
            if key in entries_by_key or key in self._BUILTIN_CONTEXT_KEYS:
                continue
            entries_by_key[key] = {
                "key": key,
                "label": key.replace("_", " ").strip().capitalize(),
                "description": "",
                "type": "string",
                "render_mode": "text",
                "section": "inferred",
                "required": False,
                "phase": int(self.fase or 0),
                "doc_type": self.doc_type,
                "sequence": index * 10,
            }

        return sorted(
            entries_by_key.values(),
            key=lambda entry: (
                entry.get("phase", 0),
                self.env["gov.processo.parametro"]._get_section_priority(entry.get("section")),
                entry.get("sequence", 10),
                entry.get("label", ""),
            ),
        )

    def get_parameter_keys(self):
        self.ensure_one()
        return [entry["key"] for entry in self.get_parameter_entries()]

    def sync_process_parameters(self, processo):
        self.ensure_one()
        processo.ensure_one()
        Parameter = self.env["gov.processo.parametro"]
        existing_by_key = {rec.key: rec for rec in processo.parameter_ids}

        for entry in self.get_parameter_entries():
            values = {
                "processo_id": processo.id,
                "key": entry["key"],
                "name": entry["label"],
                "description": entry["description"],
                "fase": entry["phase"],
                "doc_type": entry["doc_type"],
                "section": entry["section"],
                "required": entry["required"],
                "value_type": entry["type"],
                "render_mode": entry["render_mode"],
                "sequence": entry["sequence"],
            }
            current = existing_by_key.get(entry["key"])
            if current:
                values["fase"] = min(current.fase or 0, entry["phase"])
                values["template_ids"] = [(4, self.id)]
                current.with_context(skip_phase_lock=True).write(values)
            else:
                values["template_ids"] = [(6, 0, [self.id])]
                created = Parameter.with_context(skip_phase_lock=True).create(values)
                existing_by_key[created.key] = created
        return True
