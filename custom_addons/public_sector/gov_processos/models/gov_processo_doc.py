import base64
import hashlib
import html
import json
import os
import re

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import column_exists, create_column, table_exists

from .constants import (
    DOC_TYPE_SELECTION,
    PROCESS_SCOPE_SELECTION,
    PROCESS_TYPE_SELECTION,
    XLSX_PROFILE_SELECTION,
)
from .gov_ai_doc_service import GovAiDocService
from .gov_latex_service import GovHtmlPdfService, GovLatexService
from .gov_template_service import GovTemplateService
from .gov_typst_service import GovTypstService

CHECKLIST_MODE_SELECTION = [
    ("agu_estrito", "AGU Estrito"),
    ("ug_expandido", "UG Expandido"),
]


class GovProcessoDoc(models.Model):
    _name = "gov.processo.doc"
    _description = "Documento do Processo Administrativo"
    _order = "sequence asc, id asc"
    _inherit = ["mail.thread"]
    _VERSION_SUFFIX_RE = re.compile(r"\s*\(v(\d+)\)\s*$", re.IGNORECASE)
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _TYPST_ERROR_LOCATION_RE = re.compile(r"main\.typ:(\d+):(\d+)")
    _TYPST_ERROR_SUMMARY_RE = re.compile(r"error:\s*(.+)")
    _TYPST_CURRENCY_RE = re.compile(r"(?<!\\)R\$")

    def _auto_init(self):
        result = super()._auto_init()
        if table_exists(self.env.cr, "gov_processo_doc"):
            if not column_exists(self.env.cr, "gov_processo_doc", "xlsx_profile"):
                create_column(self.env.cr, "gov_processo_doc", "xlsx_profile", "varchar")
            if not column_exists(self.env.cr, "gov_processo_doc", "typst_source"):
                create_column(self.env.cr, "gov_processo_doc", "typst_source", "text")
            if not column_exists(self.env.cr, "gov_processo_doc", "ingest_target_format"):
                create_column(self.env.cr, "gov_processo_doc", "ingest_target_format", "varchar")
        self.env.cr.execute(
            """
            UPDATE gov_processo_doc doc
               SET xlsx_profile = COALESCE(
                    proc.xlsx_profile,
                    CASE
                        WHEN proc.process_scope = 'servicos_continuados' THEN 'service_continuous_labor'
                        ELSE 'procurement_reference'
                    END
               )
              FROM gov_processo proc
             WHERE doc.processo_id = proc.id
               AND doc.xlsx_profile IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_processo_doc
               SET xlsx_profile = 'procurement_reference'
             WHERE xlsx_profile IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_processo_doc
               SET ingest_target_format = 'latex'
             WHERE ingest_target_format IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_processo_doc
               SET render_mode = 'manual_source'
             WHERE render_mode IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE gov_processo_doc
               SET render_state = 'idle'
             WHERE render_state IS NULL
            """
        )
        return result

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="Título do Documento", required=True, tracking=True)
    sequence = fields.Integer(string="Ordem no Dossiê", default=10)
    doc_type = fields.Selection(
        DOC_TYPE_SELECTION,
        string="Tipo",
        required=True,
        default="dfd",
        tracking=True,
    )
    content_html = fields.Html(string="Conteúdo (HTML)")
    process_type = fields.Selection(related="processo_id.process_type", store=True, readonly=True)
    process_scope = fields.Selection(related="processo_id.process_scope", store=True, readonly=True)
    ai_template_id = fields.Many2one(
        "gov.ai.template",
        string="Template IA",
    )
    ai_last_run_id = fields.Many2one(
        "gov.ai.run",
        string="Última Execução IA",
        readonly=True,
        copy=False,
    )
    ai_provider_used = fields.Char(string="Provider IA", readonly=True, copy=False)
    ai_model_used = fields.Char(string="Modelo IA", readonly=True, copy=False)
    manual_checklist = fields.Boolean(
        string="Checklist Manual",
        default=False,
        help="Indica que este documento foi criado como checklist manual.",
    )
    checklist_mode = fields.Selection(
        CHECKLIST_MODE_SELECTION,
        string="Modo do Checklist",
        default="agu_estrito",
        help="AGU Estrito: somente estrutura normativa base. UG Expandido: inclui blocos locais extras.",
    )
    pesquisa_precos_html = fields.Html(string="Pesquisa de Preços (Planilha HTML)")
    pesquisa_precos_planilha = fields.Binary(
        string="Planilha de Pesquisa (XLSX/CSV)",
        attachment=True,
    )
    pesquisa_precos_planilha_filename = fields.Char()
    xlsx_profile = fields.Selection(
        selection=XLSX_PROFILE_SELECTION,
        string="Perfil XLSX",
        default="procurement_reference",
        help="Permite ajustar o layout de exportacao XLSX deste documento.",
    )
    typst_source = fields.Text(string="Fonte Typst")
    latex_source = fields.Text(string="Fonte LaTeX")
    render_mode = fields.Selection(
        [
            ("manual_source", "Fonte manual"),
            ("structured_typst", "Render estruturado Typst"),
        ],
        string="Modo de Render",
        default="manual_source",
        required=True,
        tracking=True,
    )
    dados_snapshot = fields.Text(
        string="Snapshot dados.typ",
        readonly=True,
        help="Snapshot congelado do payload do render estruturado.",
    )
    template_ref = fields.Many2one(
        "gov.ai.template",
        string="Template Typst Estruturado",
        domain=[("output_format", "=", "typst")],
        ondelete="restrict",
    )
    layout_json = fields.Text(
        string="Layout Build (JSON)",
        help="Armazena os blocos ordenados arrastados pelo usuário no Construtor Visual.",
    )
    is_visual_builder = fields.Boolean(
        string="Feito no Construtor Visual",
        default=False,
    )
    template_snapshot = fields.Text(
        string="Snapshot do Template",
        readonly=True,
        help="Copia congelada do template Typst usado no enqueue.",
    )
    template_sha256 = fields.Char(
        string="SHA-256 do Template",
        readonly=True,
        size=64,
    )
    render_state = fields.Selection(
        [
            ("idle", "Aguardando"),
            ("queued", "Na fila"),
            ("running", "Renderizando"),
            ("done", "Concluido"),
            ("error", "Erro"),
        ],
        string="Estado do Render",
        default="idle",
        readonly=True,
        tracking=True,
    )
    pdf_file = fields.Binary(string="PDF", attachment=True)
    pdf_filename = fields.Char(string="Nome do PDF")
    render_attachment_id = fields.Many2one(
        "ir.attachment",
        string="PDF Estruturado",
        readonly=True,
        ondelete="set null",
    )
    last_render_job_id = fields.Many2one(
        "gov.processo.doc.render.job",
        string="Ultimo Job de Render",
        readonly=True,
        ondelete="set null",
    )
    upload_externo = fields.Binary(
        string="Upload Externo (PDF/DOCX)",
        attachment=True,
    )
    upload_externo_filename = fields.Char()
    upload_externo_tipo = fields.Selection(
        [
            ("pdf", "PDF"),
            ("docx", "DOCX"),
            ("scan", "Documento Escaneado"),
            ("outro", "Outro"),
        ],
        string="Tipo do Upload",
    )
    ingest_target_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_target_format_selection(),
        string="Destino da Conversão",
        default="latex",
        help="Formato principal a ser priorizado quando o upload externo for convertido pelo worker.",
    )
    timbre_id = fields.Many2one(
        "gov.timbre",
        string="Timbre",
        help="Se vazio, usa o timbre padrão da UG",
    )
    clone_of_id = fields.Many2one(
        "gov.processo.doc",
        string="Clonado de",
        readonly=True,
        copy=False,
    )
    clone_ids = fields.One2many(
        "gov.processo.doc",
        "clone_of_id",
        string="Versões Clonadas",
        readonly=True,
    )
    clone_count = fields.Integer(
        string="Clones",
        compute="_compute_clone_count",
    )
    version = fields.Integer(string="Versão", default=1, readonly=True)
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("revisao", "Em Revisão"),
            ("aprovado", "Aprovado"),
            ("assinado", "Assinado"),
        ],
        string="Estado",
        default="rascunho",
        tracking=True,
    )
    ai_generated = fields.Boolean(string="Gerado por IA", default=False, readonly=True)
    signed_at = fields.Datetime(string="Assinado em", readonly=True)
    hash_sha256 = fields.Char(string="Hash SHA-256 do PDF", readonly=True, copy=False)

    dfd_area_requisitante = fields.Char(string="Área Requisitante")
    dfd_objeto = fields.Html(string="Descrição do Objeto")
    dfd_justificativa = fields.Html(string="Justificativa da Necessidade")
    dfd_quantidade = fields.Char(string="Quantidade / Unidade")
    dfd_valor_estimado = fields.Monetary(
        string="Valor Estimado",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    dfd_data_necessidade = fields.Date(string="Data de Necessidade")
    dfd_vinculo_ppa = fields.Char(
        string="Vínculo PPA/LOA",
        help="Programa e ação do PPA ao qual a demanda se vincula",
    )
    dfd_responsavel_tecnico = fields.Many2one(
        "res.users",
        string="Responsável Técnico pela Demanda",
    )
    versao_ids = fields.One2many(
        "gov.processo.versao",
        "doc_id",
        string="Histórico de Versões",
    )
    versao_count = fields.Integer(
        compute="_compute_versao_count",
        string="Versões",
    )
    template_parameter_ids = fields.Many2many(
        "gov.processo.parametro",
        string="Variáveis do Modelo",
        compute="_compute_template_parameters",
        store=False,
    )
    template_parameter_count = fields.Integer(
        string="Qtd. Variáveis do Modelo",
        compute="_compute_template_parameters",
        store=False,
    )
    xlsx_job_ids = fields.One2many(
        "gov.processo.planilha.job",
        "doc_id",
        string="Jobs de Planilha",
    )
    xlsx_job_count = fields.Integer(
        string="Jobs XLSX",
        compute="_compute_xlsx_job_count",
    )
    ingest_job_ids = fields.One2many(
        "gov.processo.doc.ingest.job",
        "doc_id",
        string="Jobs de Conversão de Upload",
    )
    ingest_job_count = fields.Integer(
        string="Jobs de Conversão",
        compute="_compute_ingest_job_count",
    )
    render_job_ids = fields.One2many(
        "gov.processo.doc.render.job",
        "doc_id",
        string="Historico de Render",
    )
    render_job_count = fields.Integer(
        string="Qtd. Jobs de Render",
        compute="_compute_render_job_count",
    )

    @api.depends("versao_ids")
    def _compute_versao_count(self):
        for rec in self:
            rec.versao_count = len(rec.versao_ids)

    @api.depends("clone_ids")
    def _compute_clone_count(self):
        for rec in self:
            rec.clone_count = len(rec.clone_ids)

    @api.depends("xlsx_job_ids")
    def _compute_xlsx_job_count(self):
        for rec in self:
            rec.xlsx_job_count = len(rec.xlsx_job_ids)

    @api.depends("ingest_job_ids")
    def _compute_ingest_job_count(self):
        for rec in self:
            rec.ingest_job_count = len(rec.ingest_job_ids)

    @api.depends("render_job_ids")
    def _compute_render_job_count(self):
        for rec in self:
            rec.render_job_count = len(rec.render_job_ids)

    @api.depends(
        "ai_template_id",
        "doc_type",
        "processo_id",
        "processo_id.parameter_ids",
        "processo_id.parameter_ids.value_text",
    )
    def _compute_template_parameters(self):
        for rec in self:
            template = rec.ai_template_id or rec._get_default_ai_template()
            if not rec.processo_id or not template:
                rec.template_parameter_ids = self.env["gov.processo.parametro"]
                rec.template_parameter_count = 0
                continue
            keys = set(template.get_parameter_keys())
            parameters = rec.processo_id.parameter_ids.filtered(lambda item: item.key in keys)
            rec.template_parameter_ids = parameters
            rec.template_parameter_count = len(parameters)

    @api.onchange("processo_id")
    def _onchange_processo_id_xlsx_profile(self):
        for rec in self:
            if rec.processo_id and (
                not rec.xlsx_profile or rec.xlsx_profile == "procurement_reference"
            ):
                rec.xlsx_profile = rec.processo_id.xlsx_profile or "procurement_reference"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("xlsx_profile"):
                continue
            processo = self.env["gov.processo"].browse(vals.get("processo_id")).exists()
            if processo:
                vals["xlsx_profile"] = processo.xlsx_profile or "procurement_reference"
        records = super().create(vals_list)
        records._sync_template_parameters_from_current_template()
        return records

    @api.constrains(
        "state",
        "content_html",
        "pesquisa_precos_html",
        "pesquisa_precos_planilha",
        "typst_source",
        "latex_source",
        "pdf_file",
    )
    def _check_assinado_imutavel(self):
        for rec in self:
            if rec.state == "assinado":
                pass

    def write(self, vals):
        vals = dict(vals)
        sync_template_parameters = bool({"ai_template_id", "doc_type", "processo_id"} & set(vals))
        skip_versao_snapshot = self.env.context.get("skip_versao_snapshot")
        campos_conteudo = {
            "content_html",
            "pesquisa_precos_html",
            "pesquisa_precos_planilha",
            "typst_source",
            "latex_source",
            "pdf_file",
        }
        Versao = self.env["gov.processo.versao"]
        change_reason = vals.pop("change_reason", "")

        for rec in self:
            if vals.get("state") == "assinado" and rec.ai_generated and rec.state != "aprovado":
                policy = self.env["gov.ai.orchestrator"].get_policy(
                    rec.doc_type,
                    rec.processo_id.process_type if rec.processo_id else None,
                )
                if policy and policy.exigir_aprovacao_humana:
                    raise ValidationError(
                        (
                            f'O documento "{rec.name}" foi gerado por IA e exige '
                            "aprovação humana antes da assinatura."
                        )
                    )

            if rec.state == "assinado" and campos_conteudo & set(vals):
                raise ValidationError(f'O documento "{rec.name}" já está assinado.')

            if (
                not skip_versao_snapshot
                and campos_conteudo & set(vals)
                and rec.state != "rascunho"
            ):
                Versao.create(
                    {
                        "doc_id": rec.id,
                        "version_number": rec.version,
                        "content_snapshot_html": rec.content_html,
                        "typst_snapshot": rec.typst_source,
                        "latex_snapshot": rec.latex_source,
                        "pdf_snapshot": rec.pdf_file,
                        "changed_by": self.env.user.id,
                        "changed_at": fields.Datetime.now(),
                        "change_reason": change_reason,
                        "ai_generated": rec.ai_generated,
                    }
                )

        result = super().write(vals)

        if not skip_versao_snapshot and campos_conteudo & set(vals):
            for rec in self:
                if rec.state != "assinado":
                    super(GovProcessoDoc, rec).write({"version": rec.version + 1})

        if vals.get("state") == "assinado":
            self._check_tr_avancar_fase()
        if sync_template_parameters:
            self._sync_template_parameters_from_current_template()
        return result

    def _check_tr_avancar_fase(self):
        """
        Se TR estiver assinado e o processo estiver em instrução,
        avança automaticamente para planejamento.
        """
        for doc in self:
            processo = doc.processo_id
            if (
                doc.doc_type == "tr"
                and doc.state == "assinado"
                and processo
                and processo.state == "instrucao"
            ):
                processo.write({"state": "planejamento"})
                processo.message_post(
                    body=Markup(
                        "📋 <b>TR assinado.</b> Processo avançado "
                        "automaticamente para <b>Planejamento Financeiro</b>."
                        f"<br/>Documento: {doc.name}"
                    ),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

    def action_aprovar(self):
        self.write({"state": "aprovado"})

    def action_abrir_construtor_visual(self):
        self.ensure_one()
        return self._build_construtor_visual_action()

    def _format_builder_currency(self, amount):
        value = float(amount or 0.0)
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    def _get_builder_legal_basis_default(self):
        self.ensure_one()
        defaults = {
            "dfd": "Lei nº 14.133/2021, art. 18, e regulamentos internos aplicáveis.",
            "tr": "Lei nº 14.133/2021, art. 6º, XXIII, art. 18 e demais dispositivos pertinentes.",
        }
        return defaults.get(
            self.doc_type,
            "Lei nº 14.133/2021 e normativos internos aplicáveis à instrução do processo.",
        )

    def _get_builder_routing_default(self):
        self.ensure_one()
        if self.doc_type == "dfd":
            return "Encaminhe-se para validação técnica e prosseguimento da instrução processual."
        if self.doc_type == "tr":
            return "Submeta-se o Termo de Referência à revisão jurídica e à autorização da autoridade competente."
        return "Encaminhe-se para análise e deliberação da autoridade competente."

    def _get_builder_summary_rows(self):
        self.ensure_one()
        processo = self.processo_id
        value_amount = self.dfd_valor_estimado or processo.valor_total_estimado or 0.0
        rows = [
            ("Processo", processo.name or ""),
            ("Objeto / Assunto", processo.subject or ""),
            ("Tipo", dict(PROCESS_TYPE_SELECTION).get(self.process_type, self.process_type or "")),
            ("Escopo", dict(PROCESS_SCOPE_SELECTION).get(self.process_scope, self.process_scope or "")),
            ("UG", processo.ug_id.name or ""),
            ("Valor estimado", self._format_builder_currency(value_amount)),
        ]
        if self.dfd_area_requisitante:
            rows.insert(4, ("Área requisitante", self.dfd_area_requisitante))
        if processo.responsible_id:
            rows.append(("Responsável", processo.responsible_id.name or ""))
        return [
            {"label": label, "value": value}
            for label, value in rows
            if value
        ]

    def _get_builder_record_context(self):
        self.ensure_one()
        processo = self.processo_id
        object_html = self.dfd_objeto or ""
        justification_html = self.dfd_justificativa or ""
        object_text = self._plain_text_from_html(object_html) or processo.subject or ""
        justification_text = self._plain_text_from_html(justification_html)
        summary_rows = self._get_builder_summary_rows()
        estimated_amount = self.dfd_valor_estimado or processo.valor_total_estimado or 0.0
        responsible_name = processo.responsible_id.name if processo.responsible_id else ""
        data_necessidade = (
            self.dfd_data_necessidade.strftime("%d/%m/%Y") if self.dfd_data_necessidade else ""
        )
        return {
            "record_model": self._name,
            "record_id": self.id,
            "process_id": processo.id,
            "process_number": processo.name or "",
            "process_subject": processo.subject or "",
            "process_type": self.process_type or "",
            "process_type_label": dict(PROCESS_TYPE_SELECTION).get(self.process_type, self.process_type or ""),
            "process_scope": self.process_scope or "",
            "process_scope_label": dict(PROCESS_SCOPE_SELECTION).get(self.process_scope, self.process_scope or ""),
            "process_state": processo.state or "",
            "company_name": processo.ug_id.name or "",
            "doc_name": self.name or "",
            "doc_type": self.doc_type or "",
            "doc_type_label": dict(DOC_TYPE_SELECTION).get(self.doc_type, self.doc_type or ""),
            "requesting_area": self.dfd_area_requisitante or "",
            "object_html": object_html or "",
            "object_text": object_text or "",
            "justification_html": justification_html or "",
            "justification_text": justification_text or "",
            "estimated_value": estimated_amount,
            "estimated_value_label": self._format_builder_currency(estimated_amount),
            "responsible_name": responsible_name or "",
            "responsible_role": "Responsável pelo Processo",
            "legal_basis_default": self._get_builder_legal_basis_default(),
            "routing_default": self._get_builder_routing_default(),
            "summary_rows": summary_rows,
            "summary_rows_text": "\n".join(
                f"{row['label']}: {row['value']}" for row in summary_rows if row.get("value")
            ),
            "data_necessidade": data_necessidade,
            "vinculo_ppa": self.dfd_vinculo_ppa or "",
        }

    def _sanitize_builder_blocks(self, blocks):
        sanitized = []
        for index, block in enumerate(blocks or [], start=1):
            if not isinstance(block, dict):
                continue
            block_type = (block.get("type") or "").strip()
            if not block_type:
                continue
            content = block.get("content") if isinstance(block.get("content"), dict) else {}
            sanitized.append(
                {
                    "id": block.get("id") or f"block_{index}",
                    "type": block_type,
                    "label": block.get("label") or "",
                    "editable": bool(block.get("editable", True)),
                    "content": content,
                }
            )
        return sanitized

    def action_builder_bootstrap(self):
        self.ensure_one()
        Template = self.env["gov.processo.doc.builder.template"]
        context = self._get_builder_record_context()
        try:
            layout_blocks = json.loads(self.layout_json or "[]")
        except json.JSONDecodeError:
            layout_blocks = []
        layout_blocks = self._sanitize_builder_blocks(layout_blocks)
        template_data = Template.get_rendered_payload_for_document(self, context)
        template = template_data.get("template")
        initial_blocks = layout_blocks or self._sanitize_builder_blocks(template_data.get("blocks"))
        return {
            "doc": {
                "id": self.id,
                "name": self.name or "",
                "layout_json": self.layout_json or "",
                "processo_id": self.processo_id.id,
                "doc_type": self.doc_type or "",
                "state": self.state or "",
                "typst_source": self.typst_source or "",
                "is_visual_builder": bool(self.is_visual_builder),
            },
            "record_context": context,
            "initial_blocks": initial_blocks,
            "builder_template": {
                "id": template.id if template else False,
                "name": template.name if template else "",
                "doc_type": template.doc_type if template else self.doc_type,
                "process_type": template.process_type if template else False,
                "process_scope": template.process_scope if template else False,
            },
            "assistant_info": self.action_typst_assistant_status(),
        }

    def action_builder_save_payload(self, layout_payload=None, typst_source=""):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode ser alterado no construtor visual.")

        if isinstance(layout_payload, str):
            try:
                layout_payload = json.loads(layout_payload or "[]")
            except json.JSONDecodeError as exc:
                raise UserError("O payload do construtor visual não está em JSON válido.") from exc

        blocks = self._sanitize_builder_blocks(layout_payload or [])
        generated_typst = (typst_source or "").strip()
        if not generated_typst:
            raise UserError("Nenhum Typst foi recebido do construtor visual.")

        vals = {
            "layout_json": json.dumps(blocks, ensure_ascii=False),
            "typst_source": generated_typst,
            "is_visual_builder": True,
            "change_reason": "Documento atualizado pelo construtor visual",
        }

        object_block = next((item for item in blocks if item["type"] == "objeto"), False)
        if object_block and object_block["content"].get("html"):
            vals["dfd_objeto"] = object_block["content"]["html"]
        justification_block = next((item for item in blocks if item["type"] == "justificativa"), False)
        if justification_block and justification_block["content"].get("html"):
            vals["dfd_justificativa"] = justification_block["content"]["html"]
        title_block = next((item for item in blocks if item["type"] == "titulo"), False)
        if title_block and title_block["content"].get("titulo"):
            title = (title_block["content"].get("titulo") or "").strip()
            subtitle = (title_block["content"].get("subtitulo") or "").strip()
            vals["name"] = f"{title} - {subtitle}" if subtitle else title

        self.write(vals)
        return {
            "ok": True,
            "doc_id": self.id,
            "doc_name": self.name or "",
            "typst_source": self.typst_source or generated_typst,
            "typst_filename": f"{self.name or 'documento'}.typ",
            "record_context": self._get_builder_record_context(),
        }

    def _build_act_window_views(self, view_mode):
        mode = (view_mode or "form").strip()
        return [(False, item.strip()) for item in mode.split(",") if item.strip()]

    def _build_act_window_action(self, *, view_mode="form", **kwargs):
        action = {
            "type": "ir.actions.act_window",
            "view_mode": view_mode,
            **kwargs,
        }
        action["views"] = self._build_act_window_views(view_mode)
        return action

    def _build_construtor_visual_action(self, initial_mode=False, extra_params=None):
        self.ensure_one()
        params = {
            "doc_id": self.id,
            "model": "gov.processo.doc",
        }
        if initial_mode:
            params["initial_mode"] = initial_mode
        if extra_params:
            params.update(extra_params)
        return {
            "type": "ir.actions.client",
            "tag": "gov_document_builder",
            "name": "Construtor Visual de Documento",
            "params": params,
            "target": "fullscreen",
        }

    def action_voltar_rascunho(self):
        for rec in self:
            if rec.state == "assinado":
                raise ValidationError("Documento assinado não pode ser revertido.")
        self.write({"state": "rascunho"})

    def action_regenerar_checklist_manual(self):
        self.ensure_one()
        if not self.manual_checklist:
            raise UserError("Este documento não está marcado como checklist manual.")
        if self.state == "assinado":
            raise UserError("Documento assinado não pode ser alterado.")
        if not self.processo_id:
            raise UserError("Checklist manual sem processo vinculado.")

        mode = self.checklist_mode or "agu_estrito"
        html = self.processo_id._build_manual_checklist_html(mode=mode)
        self.write({"content_html": html})
        mode_label = dict(CHECKLIST_MODE_SELECTION).get(mode, mode)
        self.message_post(
            body=Markup(
                "🧾 <b>Checklist manual regenerado.</b> "
                f"Modo aplicado: <b>{mode_label}</b>."
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Checklist regenerado",
                "message": f"Modo aplicado: {mode_label}",
                "type": "success",
            },
        }

    def _extract_base_and_version(self, name):
        clean_name = (name or "").strip()
        if not clean_name:
            return ("Checklist Manual", 0)
        match = self._VERSION_SUFFIX_RE.search(clean_name)
        if not match:
            return (clean_name, 0)
        base_name = clean_name[: match.start()].strip() or "Checklist Manual"
        return (base_name, int(match.group(1)))

    def _next_manual_clone_version(self):
        self.ensure_one()
        if not self.processo_id:
            return (2, "Checklist Manual")
        base_name, current_suffix = self._extract_base_and_version(self.name)
        max_version = max(current_suffix, self.version or 1)
        siblings = self.search(
            [
                ("processo_id", "=", self.processo_id.id),
                ("manual_checklist", "=", True),
            ]
        )
        for sibling in siblings:
            sibling_base, sibling_suffix = self._extract_base_and_version(sibling.name)
            if sibling_base == base_name:
                max_version = max(max_version, sibling_suffix, sibling.version or 1)
        return (max_version + 1, base_name)

    def action_clonar_checklist_como_nova_versao(self):
        self.ensure_one()
        if not self.manual_checklist:
            raise UserError("A clonagem rápida está disponível apenas para checklist manual.")
        if not self.processo_id:
            raise UserError("Checklist sem processo vinculado não pode ser clonado.")

        next_version, base_name = self._next_manual_clone_version()
        new_doc = self.copy(
            default={
                "name": f"{base_name} (v{next_version})",
                "state": "rascunho",
                "version": next_version,
                "clone_of_id": self.id,
                "signed_at": False,
                "hash_sha256": False,
                "pdf_file": False,
                "pdf_filename": False,
                "upload_externo": False,
                "upload_externo_filename": False,
            }
        )

        now = fields.Datetime.now()
        self.env["gov.processo.versao"].create(
            {
                "doc_id": self.id,
                "version_number": self.version,
                "content_snapshot_html": self.content_html,
                "typst_snapshot": self.typst_source,
                "latex_snapshot": self.latex_source,
                "pdf_snapshot": self.pdf_file,
                "changed_by": self.env.user.id,
                "changed_at": now,
                "change_reason": f"Clonado para nova versão: {new_doc.name}",
                "ai_generated": self.ai_generated,
            }
        )
        self.env["gov.processo.versao"].create(
            {
                "doc_id": new_doc.id,
                "version_number": new_doc.version,
                "content_snapshot_html": new_doc.content_html,
                "typst_snapshot": new_doc.typst_source,
                "latex_snapshot": new_doc.latex_source,
                "pdf_snapshot": new_doc.pdf_file,
                "changed_by": self.env.user.id,
                "changed_at": now,
                "change_reason": f"Versão inicial clonada de: {self.name}",
                "ai_generated": new_doc.ai_generated,
            }
        )

        self.message_post(
            body=Markup(
                "📑 <b>Checklist clonado para nova versão.</b> "
                f"Novo documento: <b>{new_doc.name}</b>."
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        new_doc.message_post(
            body=Markup(
                "📑 <b>Documento criado por clonagem.</b> "
                f"Origem: <b>{self.name}</b>."
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return self._build_act_window_action(
            name="Checklist Clonado",
            res_model="gov.processo.doc",
            res_id=new_doc.id,
            view_mode="form",
            target="current",
        )

    def _get_scope_values_for_ai(self):
        self.ensure_one()
        scope = self.process_scope or "compras"
        if scope == "servicos_continuados":
            return ["all", "servicos", "servicos_continuados"]
        return ["all", scope]

    def _sync_template_parameters_from_current_template(self):
        for rec in self:
            if not rec.processo_id:
                continue
            template = rec.ai_template_id or rec._get_default_ai_template()
            if template:
                template.sync_process_parameters(rec.processo_id)
        return True

    def _get_default_ai_template(self):
        self.ensure_one()
        if not self.process_type:
            return self.env["gov.ai.template"]

        domain = [
            ("active", "=", True),
            ("process_type", "=", self.process_type),
            ("process_scope", "in", self._get_scope_values_for_ai()),
            ("doc_type", "=", self.doc_type),
        ]
        if self.manual_checklist:
            domain.append(("is_checklist", "=", True))
            order = "process_scope desc, fase asc, id asc"
        else:
            order = "is_checklist asc, process_scope desc, fase asc, id asc"
        return self.env["gov.ai.template"].search(domain, order=order, limit=1)

    def _get_structured_typst_template(self):
        self.ensure_one()
        candidates = self.template_ref | self.ai_template_id
        template = candidates.filtered(lambda item: item.output_format == "typst")[:1]
        return template or self.env["gov.ai.template"]

    def _plain_text_from_html(self, html_text):
        text = self._HTML_TAG_RE.sub(" ", html_text or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_ai_context(self, template, memory_block):
        self.ensure_one()
        processo = self.processo_id
        company = processo.ug_id
        origin_label = dict(processo._fields["origin_type"].selection).get(processo.origin_type, processo.origin_type)
        doc_type_label = dict(self._fields["doc_type"].selection).get(self.doc_type, self.doc_type)
        scope_label = dict(PROCESS_SCOPE_SELECTION).get(self.process_scope, self.process_scope)
        type_label = dict(PROCESS_TYPE_SELECTION).get(self.process_type, self.process_type)
        context = {
            "ug_nome": company.name or "",
            "ug_cnpj": getattr(company, "cnpj_ug", "") or "",
            "exercicio": getattr(company, "exercicio_fiscal", fields.Date.today().year),
            "processo_numero": processo.name or "",
            "processo_assunto": processo.subject or "",
            "process_type": type_label or "",
            "process_scope": scope_label or "",
            "origem": origin_label or "",
            "doc_nome": self.name or "",
            "doc_tipo": doc_type_label or "",
            "area_requisitante": self.dfd_area_requisitante or "",
            "objeto": self.dfd_objeto or processo.subject or "",
            "justificativa": self.dfd_justificativa or "",
            "quantidade": self.dfd_quantidade or self._plain_text_from_html(self.pesquisa_precos_html or "")[:1200],
            "valor_estimado": self.dfd_valor_estimado or 0,
            "data_necessidade": self.dfd_data_necessidade.strftime("%d/%m/%Y") if self.dfd_data_necessidade else "",
            "vinculo_ppa": self.dfd_vinculo_ppa or "",
            "responsavel_tecnico": self.dfd_responsavel_tecnico.name if self.dfd_responsavel_tecnico else "",
            "responsavel_processo": processo.responsible_id.name if processo.responsible_id else "",
            "hoje": fields.Date.today().strftime("%d/%m/%Y"),
            "checklist_mode": dict(CHECKLIST_MODE_SELECTION).get(self.checklist_mode, self.checklist_mode or ""),
            "memoria_ug": memory_block or "",
            "template_nome": template.name if template else "",
            "guidance_text": template.guidance_text if template else "",
            "output_format": template.output_format if template else "",
            "versao_normativa": template.versao_normativa if template else "",
            "parameters_json": json.dumps(
                template.get_parameter_spec() if template else {},
                ensure_ascii=False,
                indent=2,
            ),
            "option_catalog_json": json.dumps(
                template.get_option_catalog() if template else {},
                ensure_ascii=False,
                indent=2,
            ),
        }
        if processo:
            context.update(processo.get_template_parameter_context(template=template))
        return context

    def _build_fallback_ai_config(self):
        return self.env["gov.ai.provider.config"].new(
            {
                "name": "Fallback Odoo Chat",
                "provider": "odoo_chat",
                "model_name": "odoo_chat_local",
                "temperature": 0.2,
                "max_tokens": 2000,
                "timeout_seconds": 60,
                "memory_top_k": 5,
            }
        )

    def _build_fallback_ollama_config(self):
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
        return self.env["gov.ai.provider.config"].new(
            {
                "name": "Fallback Ollama Local",
                "provider": "ollama",
                "model_name": "llama3.2:1b",
                "endpoint_url": f"{ollama_host}/api/generate",
                "temperature": 0.1,
                "max_tokens": 1800,
                "timeout_seconds": 90,
                "memory_top_k": 3,
            }
        )

    def _get_typst_ai_config(self):
        self.ensure_one()
        Config = self.env["gov.ai.provider.config"]
        company_id = self.processo_id.ug_id.id if self.processo_id and self.processo_id.ug_id else self.env.company.id
        search_orders = [
            [
                ("company_id", "=", company_id),
                ("active", "=", True),
                ("provider", "=", "ollama"),
                ("is_default", "=", True),
            ],
            [
                ("company_id", "=", company_id),
                ("active", "=", True),
                ("provider", "=", "ollama"),
            ],
            [
                ("active", "=", True),
                ("provider", "=", "ollama"),
                ("is_default", "=", True),
            ],
            [
                ("active", "=", True),
                ("provider", "=", "ollama"),
            ],
        ]
        for domain in search_orders:
            config = Config.search(domain, order="sequence, id", limit=1)
            if config:
                return config
        return self._build_fallback_ollama_config()

    def _strip_markdown_code_fences(self, text):
        cleaned = (text or "").strip()
        if not cleaned.startswith("```"):
            return cleaned
        lines = cleaned.splitlines()
        if not lines:
            return cleaned
        first_line = lines[0].strip()
        if not first_line.startswith("```"):
            return cleaned
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _format_typst_diagnostics_for_prompt(self, diagnostics):
        if not diagnostics:
            return "- Nenhum diagnóstico local encontrado."
        lines = []
        for item in diagnostics[:8]:
            location = ""
            if item.get("line"):
                location = f" linha {item['line']}"
                if item.get("column"):
                    location += f", coluna {item['column']}"
            hint = f" | dica: {item['hint']}" if item.get("hint") else ""
            lines.append(
                f"- [{item.get('severity', 'info')}] {item.get('source', 'local')}{location}: "
                f"{item.get('message', '')}{hint}"
            )
        return "\n".join(lines)

    def _build_typst_focus_context(
        self,
        source,
        cursor_position=0,
        selection_start=0,
        selection_end=0,
    ):
        text = source or ""
        length = len(text)
        cursor = max(0, min(int(cursor_position or 0), length))
        start = max(0, min(int(selection_start or cursor), length))
        end = max(start, min(int(selection_end or start), length))
        selection = text[start:end]
        before = text[max(0, start - 900):start]
        after = text[end:min(length, end + 900)]
        line_number = text[:cursor].count("\n") + 1 if text else 1
        current_line = ""
        if text:
            lines = text.splitlines()
            if 0 <= line_number - 1 < len(lines):
                current_line = lines[line_number - 1]
        return {
            "cursor_position": cursor,
            "selection_start": start,
            "selection_end": end,
            "selection_text": selection,
            "before_cursor": before,
            "after_cursor": after,
            "line_number": line_number,
            "current_line": current_line,
        }

    def _build_typst_local_diagnostics(self, source):
        diagnostics = []
        for line_number, line in enumerate((source or "").splitlines(), start=1):
            for match in self._TYPST_CURRENCY_RE.finditer(line):
                diagnostics.append(
                    {
                        "severity": "warning",
                        "source": "heuristica",
                        "code": "currency_escape",
                        "line": line_number,
                        "column": match.start() + 1,
                        "message": "Símbolo monetário 'R$' sem escape pode quebrar o parser do Typst.",
                        "hint": r"Use 'R\$' em valores monetários literais.",
                        "excerpt": line.strip(),
                    }
                )
        return diagnostics

    def _get_typst_extra_images(self):
        self.ensure_one()
        Timbre = self.env.get("gov.timbre")
        if not Timbre or not self.processo_id or not self.processo_id.ug_id:
            return {}

        timbre = self.timbre_id or Timbre.get_default_for_company(self.processo_id.ug_id.id)
        if not timbre or not hasattr(timbre, "get_imagens_para_latex"):
            return {}
        return timbre.get_imagens_para_latex() or {}

    def _build_typst_compile_diagnostics(self, source):
        try:
            GovTypstService.compile(
                source,
                extra_images=self._get_typst_extra_images(),
                timeout=45,
            )
            return {
                "compile_ok": True,
                "compile_message": "Typst validado com sucesso.",
                "diagnostics": [],
            }
        except UserError as exc:
            message = str(exc)
            location = self._TYPST_ERROR_LOCATION_RE.search(message or "")
            summary = self._TYPST_ERROR_SUMMARY_RE.search(message or "")
            line = int(location.group(1)) if location else False
            column = int(location.group(2)) if location else False
            excerpt = ""
            if line and source:
                lines = source.splitlines()
                if 0 <= line - 1 < len(lines):
                    excerpt = lines[line - 1].strip()
            diagnostic = {
                "severity": "error",
                "source": "compilador",
                "code": "typst_compile_error",
                "line": line,
                "column": column,
                "message": summary.group(1).strip() if summary else message[:240],
                "hint": "Revise o trecho apontado e tente gerar o PDF novamente.",
                "excerpt": excerpt,
            }
            return {
                "compile_ok": False,
                "compile_message": message,
                "diagnostics": [diagnostic],
            }

    def action_typst_assistant_status(self):
        self.ensure_one()
        config = self._get_typst_ai_config()
        return {
            "enabled": True,
            "provider": config.provider or "ollama",
            "model_name": config.model_name or "",
            "config_name": config.name or "",
            "endpoint_url": config.endpoint_url or "",
        }

    def action_typst_validate_source(self, source=None):
        self.ensure_one()
        text = source if source is not None else self.typst_source or ""
        stats = {
            "chars": len(text or ""),
            "lines": len((text or "").splitlines()) or (1 if text else 0),
        }
        if not (text or "").strip():
            return {
                "ok": False,
                "status": "empty",
                "compile_ok": False,
                "compile_message": "Nenhum conteúdo Typst informado.",
                "diagnostics": [
                    {
                        "severity": "warning",
                        "source": "heuristica",
                        "code": "empty_source",
                        "line": False,
                        "column": False,
                        "message": "Cole ou escreva um código Typst antes de validar.",
                        "hint": "Você pode começar do zero ou abrir um documento já existente.",
                        "excerpt": "",
                    }
                ],
                "stats": stats,
            }

        local_diagnostics = self._build_typst_local_diagnostics(text)
        compile_result = self._build_typst_compile_diagnostics(text)
        diagnostics = compile_result["diagnostics"] + local_diagnostics
        has_errors = any(item.get("severity") == "error" for item in diagnostics)
        has_warnings = any(item.get("severity") == "warning" for item in diagnostics)
        status = "success"
        if has_errors:
            status = "error"
        elif has_warnings:
            status = "warning"
        return {
            "ok": compile_result["compile_ok"] and not has_errors,
            "status": status,
            "compile_ok": compile_result["compile_ok"],
            "compile_message": compile_result["compile_message"],
            "diagnostics": diagnostics,
            "stats": stats,
        }

    def action_typst_ai_assist(
        self,
        source=None,
        mode="debug",
        user_instruction="",
        cursor_position=0,
        selection_start=0,
        selection_end=0,
    ):
        self.ensure_one()
        mode = (mode or "debug").strip().lower()
        if mode not in {"debug", "fix", "autocomplete"}:
            raise UserError("Modo do assistente Typst inválido.")

        text = source if source is not None else self.typst_source or ""
        if not text.strip() and mode != "autocomplete":
            raise UserError("Cole um código Typst antes de pedir diagnóstico ou correção.")

        validation = self.action_typst_validate_source(text)
        config = self._get_typst_ai_config()
        focus = self._build_typst_focus_context(
            text,
            cursor_position=cursor_position,
            selection_start=selection_start,
            selection_end=selection_end,
        )
        context = self._build_ai_context(template=False, memory_block="")
        diagnostics_block = self._format_typst_diagnostics_for_prompt(validation.get("diagnostics"))
        process_label = self.processo_id.name or self.processo_id.subject or ""
        instruction = (user_instruction or "").strip()

        system_prompt = (
            "Você é um assistente especialista em Typst para documentos administrativos brasileiros. "
            "Considere que o compilador recebe apenas um arquivo 'main.typ', sem imports externos. "
            "Preserve o estilo e o conteúdo jurídico-administrativo do usuário. "
            "Responda em português. "
            "No modo 'debug', explique a causa provável e a correção mínima. "
            "No modo 'fix', retorne apenas o Typst corrigido completo, sem markdown. "
            "No modo 'autocomplete', retorne apenas o snippet Typst a inserir no cursor/seleção, sem markdown."
        )

        source_block = text
        if mode == "autocomplete":
            source_block = (
                focus["before_cursor"][-2400:]
                + "\n/* ponto de inserção */\n"
                + (focus["selection_text"] or "")
                + "\n/* após o cursor */\n"
                + focus["after_cursor"][:1800]
            )
        elif mode == "debug" and len(source_block) > 9000:
            source_block = (
                focus["before_cursor"][-2000:]
                + "\n/* trecho focado */\n"
                + (focus["selection_text"] or focus["current_line"] or "")
                + "\n/* continuação */\n"
                + focus["after_cursor"][:2000]
            )

        user_prompt = (
            f"Modo: {mode}\n"
            f"Documento: {self.name or ''}\n"
            f"Processo: {process_label}\n"
            f"Modelo atual no Ollama: {config.model_name or ''}\n"
            f"Diagnósticos locais e de compilação:\n{diagnostics_block}\n\n"
            f"Estatísticas do código: {validation['stats']['lines']} linhas, {validation['stats']['chars']} caracteres.\n"
            f"Linha atual do cursor: {focus['line_number']}\n"
            f"Instrução adicional do usuário: {instruction or 'Nenhuma; aja de forma objetiva.'}\n\n"
            "Trecho antes do cursor:\n"
            f"{focus['before_cursor'][-1200:]}\n\n"
            "Seleção atual:\n"
            f"{focus['selection_text'] or '(sem seleção)'}\n\n"
            "Trecho depois do cursor:\n"
            f"{focus['after_cursor'][:1200]}\n\n"
            "Linha atual:\n"
            f"{focus['current_line'] or '(sem linha atual)'}\n\n"
            "Fonte Typst relevante:\n"
            f"{source_block}\n"
        )

        run_vals = {
            "name": f"Assistente Typst - {self.name or 'Documento'}",
            "company_id": self.processo_id.ug_id.id if self.processo_id and self.processo_id.ug_id else self.env.company.id,
            "processo_id": self.processo_id.id,
            "doc_id": self.id,
            "provider": config.provider or "ollama",
            "model_name": config.model_name or "ollama",
            "prompt_system": system_prompt,
            "prompt_user": user_prompt,
            "memory_snapshot": json.dumps(
                {
                    "mode": mode,
                    "cursor_position": focus["cursor_position"],
                    "selection_start": focus["selection_start"],
                    "selection_end": focus["selection_end"],
                },
                ensure_ascii=False,
            ),
        }

        try:
            result = GovAiDocService.generate_text(
                config=config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                template=False,
                context=context,
            )
            raw_text = (result.get("text") or "").strip()
            cleaned_text = self._strip_markdown_code_fences(raw_text)
            if not cleaned_text:
                raise UserError("A IA retornou conteúdo vazio.")

            apply_text = ""
            result_validation = False
            if mode == "fix":
                apply_text = cleaned_text
                result_validation = self.action_typst_validate_source(cleaned_text)
            elif mode == "autocomplete":
                apply_text = cleaned_text
                merged = (
                    text[:focus["selection_start"]]
                    + cleaned_text
                    + text[focus["selection_end"]:]
                )
                result_validation = self.action_typst_validate_source(merged)

            run = self.env["gov.ai.run"].create(
                {
                    **run_vals,
                    "status": "success",
                    "provider": result.get("provider", run_vals["provider"]),
                    "model_name": result.get("model_name", run_vals["model_name"]),
                    "response_text": cleaned_text,
                    "raw_response": result.get("raw_response", ""),
                    "duration_ms": result.get("duration_ms", 0),
                }
            )
            self.write(
                {
                    "ai_last_run_id": run.id,
                    "ai_provider_used": result.get("provider", ""),
                    "ai_model_used": result.get("model_name", ""),
                }
            )
            return {
                "mode": mode,
                "provider": result.get("provider", ""),
                "model_name": result.get("model_name", ""),
                "duration_ms": result.get("duration_ms", 0),
                "output_text": cleaned_text,
                "apply_text": apply_text,
                "source_validation": validation,
                "result_validation": result_validation,
                "selection_start": focus["selection_start"],
                "selection_end": focus["selection_end"],
            }
        except Exception as exc:
            self.env["gov.ai.run"].create(
                {
                    **run_vals,
                    "status": "error",
                    "error_message": str(exc),
                }
            )
            if isinstance(exc, UserError):
                raise
            raise UserError(f"Falha no assistente Typst: {str(exc)}") from exc

    def _retrieve_ai_memories(self, query, limit=5):
        self.ensure_one()
        ml_service = self.env.get("gov.ai.ml.service")
        if ml_service:
            return ml_service.retrieve_context(self.processo_id.ug_id.id, query, limit=limit)
        return self.env["gov.ai.memory"].search_relevant(
            self.processo_id.ug_id.id,
            query,
            limit=limit,
        )

    def action_gerar_conteudo_ia(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode receber novo conteúdo IA.")
        if not self.processo_id or not self.processo_id.ug_id:
            raise UserError("Documento sem UG vinculada ao processo.")

        template = self.ai_template_id or self._get_default_ai_template()
        if not template:
            raise UserError(
                "Nenhum template IA encontrado para este tipo de processo/escopo/documento."
            )

        config = self.env["gov.ai.provider.config"].get_active_for_company(self.processo_id.ug_id.id)
        if not config:
            config = self._build_fallback_ai_config()

        query = " ".join(
            [
                self.processo_id.subject or "",
                self.name or "",
                template.name or "",
                self._plain_text_from_html(self.content_html or "")[:500],
                self.latex_source or "",
            ]
        ).strip()
        memory_records = self._retrieve_ai_memories(query, limit=config.memory_top_k or 5)
        memory_block = GovAiDocService.build_memory_block(memory_records)
        context = self._build_ai_context(template, memory_block)
        system_prompt = template.prompt_system or (
            "Você é assistente de redação técnico-jurídica para gestão pública. "
            "Seja objetivo, normativo e não invente fatos."
        )
        user_prompt = GovAiDocService.render_placeholders(template.prompt_user_tpl or "", context)
        if memory_block:
            user_prompt += (
                "\n\n### Memória institucional da UG (use apenas se relevante):\n"
                f"{memory_block}"
            )

        run_vals = {
            "name": f"IA - {self.name or 'Documento'}",
            "company_id": self.processo_id.ug_id.id,
            "processo_id": self.processo_id.id,
            "doc_id": self.id,
            "template_id": template.id,
            "provider": config.provider if config else "odoo_chat",
            "model_name": config.model_name if config else "odoo_chat_local",
            "prompt_system": system_prompt,
            "prompt_user": user_prompt,
            "memory_snapshot": memory_block,
        }

        try:
            result = GovAiDocService.generate_text(
                config=config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                template=template,
                context=context,
            )
            generated_text = (result.get("text") or "").strip()
            if not generated_text:
                raise UserError("A IA retornou conteúdo vazio.")

            vals = {
                "ai_generated": True,
                "ai_template_id": template.id,
                "ai_provider_used": result.get("provider", ""),
                "ai_model_used": result.get("model_name", ""),
                "change_reason": f"Conteúdo gerado por IA via {result.get('provider', '')}",
            }

            if template.output_format == "latex":
                vals["latex_source"] = generated_text
            elif template.output_format == "typst":
                vals["typst_source"] = generated_text
            else:
                if "<" in generated_text and ">" in generated_text:
                    vals["content_html"] = generated_text
                else:
                    vals["content_html"] = (
                        "<h3>Rascunho IA</h3><pre style='white-space:pre-wrap'>"
                        f"{escape(generated_text)}</pre>"
                    )

            run = self.env["gov.ai.run"].create(
                {
                    **run_vals,
                    "status": "success",
                    "provider": result.get("provider", run_vals["provider"]),
                    "model_name": result.get("model_name", run_vals["model_name"]),
                    "response_text": generated_text,
                    "raw_response": result.get("raw_response", ""),
                    "duration_ms": result.get("duration_ms", 0),
                }
            )
            vals["ai_last_run_id"] = run.id
            self.write(vals)
            if memory_records:
                memory_records.mark_used()
            self.message_post(
                body=Markup(
                    "🤖 <b>Conteúdo gerado por IA.</b> "
                    f"Template: <b>{template.name}</b> | Provider: <b>{result.get('provider')}</b>."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Conteúdo IA gerado",
                    "message": f"Template: {template.name}",
                    "type": "success",
                },
            }
        except Exception as exc:
            error_message = str(exc)
            run = self.env["gov.ai.run"].create(
                {
                    **run_vals,
                    "status": "error",
                    "error_message": error_message,
                }
            )
            self.write({"ai_last_run_id": run.id})
            if isinstance(exc, UserError):
                raise
            raise UserError(f"Falha na geração IA: {error_message}") from exc

    def action_gerar_com_ia(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode ser regerado.")
        return self._build_act_window_action(
            name=f"Gerar com IA — {self.name}",
            res_model="gov.ai.generate.wizard",
            view_mode="form",
            target="new",
            context={
                "default_doc_id": self.id,
                "default_processo_id": self.processo_id.id,
                "default_doc_type": self.doc_type,
                "default_template_id": self.ai_template_id.id if self.ai_template_id else False,
            },
        )

    def action_sync_template_parameters(self):
        self.ensure_one()
        template = self.ai_template_id or self._get_default_ai_template()
        if not template:
            raise UserError("Nenhum template encontrado para sincronizar as variáveis.")

        previous_keys = set(self.processo_id.parameter_ids.mapped("key"))
        template.sync_process_parameters(self.processo_id)
        new_keys = set(self.processo_id.parameter_ids.mapped("key")) - previous_keys

        if not self.ai_template_id:
            self.write({"ai_template_id": template.id})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Variáveis sincronizadas",
                "message": (
                    f"Template: {template.name}. "
                    f"Novas variáveis: {len(new_keys)}."
                ),
                "type": "success",
            },
        }

    def action_open_template_parameters(self):
        self.ensure_one()
        template = self.ai_template_id or self._get_default_ai_template()
        if not template:
            raise UserError("Nenhum template encontrado para este documento.")

        template.sync_process_parameters(self.processo_id)
        keys = template.get_parameter_keys()
        return self._build_act_window_action(
            name=f"Variáveis do Modelo — {self.name}",
            res_model="gov.processo.parametro",
            view_mode="list,form",
            domain=[
                ("processo_id", "=", self.processo_id.id),
                ("key", "in", keys or [""]),
            ],
            context={
                "default_processo_id": self.processo_id.id,
            },
        )

    def action_apply_template_latex(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode receber novo template.")

        template = self.ai_template_id or self._get_default_ai_template()
        if not template:
            raise UserError("Nenhum template encontrado para aplicar ao documento.")

        if template.output_format == "typst":
            template_source = template.typst_template or template.source_native_text
        else:
            template_source = template.latex_template or template.latex_source
        if not template_source:
            raise UserError("O template selecionado não possui conteúdo fonte cadastrado.")

        template.sync_process_parameters(self.processo_id)
        context = self._build_ai_context(template, memory_block="")
        rendered = GovAiDocService.render_placeholders(template_source, context)
        if not rendered.strip():
            raise UserError("O resultado do template ficou vazio após aplicar as variáveis.")

        vals = {
            "ai_generated": False,
            "change_reason": f"Template {template.output_format.upper()} aplicado manualmente: {template.name}",
        }
        if template.output_format == "typst":
            vals["typst_source"] = rendered
            vals["latex_source"] = False
        else:
            vals["latex_source"] = rendered
            vals["typst_source"] = False
        if not self.ai_template_id:
            vals["ai_template_id"] = template.id
        self.write(vals)
        self.message_post(
            body=Markup(
                f"🧩 <b>Template {template.output_format.upper()} aplicado.</b> "
                f"Modelo: <b>{template.name}</b>."
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Template aplicado",
                "message": f"Modelo: {template.name}",
                "type": "success",
            },
        }

    def action_enqueue_structured_render(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado nao pode receber novo render estruturado.")
        if self.render_mode != "structured_typst":
            raise UserError("Ative o modo de render estruturado antes de enfileirar o PDF.")

        job = self.env["gov.processo.doc.render.job"].create_from_doc(self)
        self.last_render_job_id = job.id
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Render estruturado enfileirado",
                "message": f"Job criado: {job.name}",
                "type": "success",
            },
        }

    def action_enqueue_xlsx_worker(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode receber nova planilha.")
        if not self.processo_id:
            raise UserError("Documento sem processo vinculado.")

        self.processo_id.sync_planilha_structured_parameters()
        job = self.env["gov.processo.planilha.job"].create_from_doc(
            self,
            profile=self.xlsx_profile or self.processo_id.xlsx_profile,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Worker XLSX enfileirado",
                "message": f"Job criado: {job.name}",
                "type": "success",
            },
        }

    def action_enqueue_ingest_worker(self):
        self.ensure_one()
        if self.state == "assinado":
            raise UserError("Documento assinado não pode receber nova conversão de upload.")
        if not self.processo_id:
            raise UserError("Documento sem processo vinculado.")
        if not self.upload_externo:
            raise UserError("Envie um arquivo na aba Upload Externo antes de solicitar a conversão.")

        job = self.env["gov.processo.doc.ingest.job"].create_from_doc(
            self,
            target_format=self.ingest_target_format or "latex",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Conversão enfileirada",
                "message": f"Job criado: {job.name}",
                "type": "success",
            },
        }

    def action_open_process_planilha_items(self):
        self.ensure_one()
        if not self.processo_id:
            raise UserError("Documento sem processo vinculado.")
        return self.processo_id.action_open_planilha_items()

    def action_open_process_planilha_lots(self):
        self.ensure_one()
        if not self.processo_id:
            raise UserError("Documento sem processo vinculado.")
        return self.processo_id.action_open_planilha_lots()

    def action_open_xlsx_jobs(self):
        self.ensure_one()
        return self._build_act_window_action(
            name=f"Jobs XLSX — {self.name}",
            res_model="gov.processo.planilha.job",
            view_mode="list,form",
            domain=[("doc_id", "=", self.id)],
            context={
                "default_doc_id": self.id,
                "default_processo_id": self.processo_id.id,
            },
        )

    def action_open_ingest_jobs(self):
        self.ensure_one()
        return self._build_act_window_action(
            name=f"Conversões de Upload - {self.name}",
            res_model="gov.processo.doc.ingest.job",
            view_mode="list,form",
            domain=[("doc_id", "=", self.id)],
            context={
                "default_doc_id": self.id,
                "default_processo_id": self.processo_id.id,
            },
        )

    def action_open_render_jobs(self):
        self.ensure_one()
        return self._build_act_window_action(
            name=f"Jobs de Render - {self.name}",
            res_model="gov.processo.doc.render.job",
            view_mode="list,form",
            domain=[("doc_id", "=", self.id)],
            context={
                "default_doc_id": self.id,
                "default_processo_id": self.processo_id.id,
            },
        )

    def action_salvar_memoria_ia(self):
        self.ensure_one()
        if not self.processo_id or not self.processo_id.ug_id:
            raise UserError("Documento sem UG vinculada ao processo.")
        content = self.content_html or self.typst_source or self.latex_source or ""
        if self.latex_source:
            plain = GovTemplateService.plain_text_from_html(self.content_html or "")
            if not plain:
                plain = re.sub(r"\s+", " ", self.latex_source or "").strip()
        elif self.typst_source:
            plain = GovTemplateService.plain_text_from_typst(self.typst_source or "")
        else:
            plain = self._plain_text_from_html(content)
        if not plain:
            raise UserError("Documento sem conteúdo textual para salvar em memória.")

        memory = self.env["gov.ai.memory"].create(
            {
                "name": f"{self.name or 'Documento'} | {self.processo_id.name or 'Processo'}",
                "company_id": self.processo_id.ug_id.id,
                "source_type": "process_doc",
                "source_model": "gov.processo.doc",
                "source_res_id": self.id,
                "tags": f"doc:{self.doc_type},processo:{self.processo_id.name or ''}",
                "content_text": plain,
            }
        )
        self.message_post(
            body=Markup(
                "🧠 <b>Conteúdo salvo na memória da UG.</b> "
                f"Entrada: <b>{memory.name}</b>."
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return self._build_act_window_action(
            res_model="gov.ai.memory",
            res_id=memory.id,
            view_mode="form",
            target="current",
        )

    def action_compile_pdf(self):
        """
        Compila o latex_source do documento em PDF.
        Salva o binario em pdf_file e registra hash SHA-256.
        """
        self.ensure_one()

        if not self.latex_source and not self.typst_source:
            raise UserError(
                'Nenhum código LaTeX ou Typst encontrado. Preencha a aba correspondente antes de compilar.'
            )
        if self.state == "assinado":
            raise UserError("Documento assinado não pode ser recompilado.")

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (
            Timbre.get_default_for_company(self.processo_id.ug_id.id) if Timbre else None
        )
        fallback_logo_binary = (
            base64.b64decode(self.processo_id.ug_id.logo) if self.processo_id.ug_id.logo else None
        )
        if self.typst_source:
            pdf_bytes = GovTypstService.compile(
                self.typst_source,
                extra_images=self._get_typst_extra_images(),
                timeout=120,
            )
            change_reason = "PDF compilado via typst"
        else:
            pdf_bytes = GovLatexService.compile_with_timbre(
                self.latex_source,
                timbre=timbre,
                fallback_logo_binary=fallback_logo_binary,
                timeout=120,
            )
            change_reason = "PDF compilado via pdflatex"
        b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        self.with_context(skip_versao_snapshot=True).write(
            {
                "pdf_file": b64_pdf,
                "pdf_filename": f'{self.name or "documento"}.pdf',
                "hash_sha256": sha256,
            }
        )

        self.env["gov.processo.versao"].create(
            {
                "doc_id": self.id,
                "version_number": self.version,
                "typst_snapshot": self.typst_source,
                "latex_snapshot": self.latex_source,
                "pdf_snapshot": b64_pdf,
                "changed_by": self.env.user.id,
                "changed_at": fields.Datetime.now(),
                "change_reason": change_reason,
                "ai_generated": self.ai_generated,
            }
        )

        self.message_post(
            body=Markup(
                "📄 <b>PDF compilado com sucesso.</b><br/>"
                f"SHA-256: <code>{sha256[:16]}...</code>"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "PDF gerado com sucesso",
                "message": f"Hash: {sha256[:16]}...",
                "type": "success",
            },
        }

    def action_gerar_pdf(self):
        """
        Motor unificado de geracao de PDF.
        Prioridade: latex_source -> pdflatex
                    content_html  -> wkhtmltopdf
        """
        self.ensure_one()

        if self.state == "assinado":
            raise UserError("Documento assinado nao pode ser regerado.")
        if not self.typst_source and not self.latex_source and not self.content_html:
            raise UserError(
                'Nenhum conteúdo encontrado. Preencha a aba "Fonte Typst", "Fonte LaTeX" ou "Conteúdo (HTML)".'
            )

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (
            Timbre.get_default_for_company(self.processo_id.ug_id.id) if Timbre else None
        )

        if self.typst_source:
            pdf_bytes = GovTypstService.compile(
                self.typst_source,
                extra_images=self._get_typst_extra_images(),
                timeout=120,
            )
            b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()
            motor = "typst"
        elif self.latex_source:
            fallback_logo_binary = (
                base64.b64decode(self.processo_id.ug_id.logo) if self.processo_id.ug_id.logo else None
            )
            pdf_bytes = GovLatexService.compile_with_timbre(
                self.latex_source,
                timbre=timbre,
                fallback_logo_binary=fallback_logo_binary,
                timeout=120,
            )
            b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()
            motor = "pdflatex"
        else:
            if not GovHtmlPdfService.is_available():
                raise UserError(
                    "wkhtmltopdf nao encontrado e nao ha codigo LaTeX. "
                    "Instale wkhtmltopdf ou preencha a aba LaTeX."
                )

            html_body, header_html, footer_html = GovHtmlPdfService.build_html_with_timbre(
                self.content_html or "",
                timbre,
            )
            pdf_bytes = GovHtmlPdfService.compile(
                html_body,
                header_html=header_html,
                footer_html=footer_html,
            )
            b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()
            motor = "wkhtmltopdf"

        self.with_context(skip_versao_snapshot=True).write(
            {
                "pdf_file": b64_pdf,
                "pdf_filename": f'{self.name or "documento"}.pdf',
                "hash_sha256": sha256,
            }
        )

        self.env["gov.processo.versao"].create(
            {
                "doc_id": self.id,
                "version_number": self.version,
                "typst_snapshot": self.typst_source,
                "latex_snapshot": self.latex_source,
                "pdf_snapshot": b64_pdf,
                "changed_by": self.env.user.id,
                "changed_at": fields.Datetime.now(),
                "change_reason": f"PDF gerado via {motor}",
                "ai_generated": self.ai_generated,
            }
        )

        self.message_post(
            body=Markup(
                f"📄 <b>PDF gerado via {motor}.</b><br/>"
                f"SHA-256: <code>{sha256[:16]}...</code>"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": f"PDF gerado ({motor})",
                "message": f"Hash: {sha256[:16]}...",
                "type": "success",
            },
        }
