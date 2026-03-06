import base64
import hashlib
import html
import re

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .constants import DOC_TYPE_SELECTION, PROCESS_SCOPE_SELECTION, PROCESS_TYPE_SELECTION
from .gov_ai_doc_service import GovAiDocService
from .gov_latex_service import GovHtmlPdfService, GovLatexService

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
    latex_source = fields.Text(string="Fonte LaTeX")
    pdf_file = fields.Binary(string="PDF", attachment=True)
    pdf_filename = fields.Char(string="Nome do PDF")
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

    @api.depends("versao_ids")
    def _compute_versao_count(self):
        for rec in self:
            rec.versao_count = len(rec.versao_ids)

    @api.depends("clone_ids")
    def _compute_clone_count(self):
        for rec in self:
            rec.clone_count = len(rec.clone_ids)

    @api.constrains(
        "state",
        "content_html",
        "pesquisa_precos_html",
        "pesquisa_precos_planilha",
        "latex_source",
        "pdf_file",
    )
    def _check_assinado_imutavel(self):
        for rec in self:
            if rec.state == "assinado":
                pass

    def write(self, vals):
        vals = dict(vals)
        skip_versao_snapshot = self.env.context.get("skip_versao_snapshot")
        campos_conteudo = {
            "content_html",
            "pesquisa_precos_html",
            "pesquisa_precos_planilha",
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

        return {
            "type": "ir.actions.act_window",
            "name": "Checklist Clonado",
            "res_model": "gov.processo.doc",
            "res_id": new_doc.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_scope_values_for_ai(self):
        self.ensure_one()
        scope = self.process_scope or "compras"
        if scope == "servicos_continuados":
            return ["all", "servicos", "servicos_continuados"]
        return ["all", scope]

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
        return {
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
        }

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
        return {
            "type": "ir.actions.act_window",
            "name": f"Gerar com IA — {self.name}",
            "res_model": "gov.ai.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_doc_id": self.id,
                "default_processo_id": self.processo_id.id,
                "default_doc_type": self.doc_type,
                "default_template_id": self.ai_template_id.id if self.ai_template_id else False,
            },
        }

    def action_salvar_memoria_ia(self):
        self.ensure_one()
        if not self.processo_id or not self.processo_id.ug_id:
            raise UserError("Documento sem UG vinculada ao processo.")
        content = self.content_html or self.latex_source or ""
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
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.ai.memory",
            "res_id": memory.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_compile_pdf(self):
        """
        Compila o latex_source do documento em PDF.
        Salva o binario em pdf_file e registra hash SHA-256.
        """
        self.ensure_one()

        if not self.latex_source:
            raise UserError(
                'Nenhum código LaTeX encontrado. Preencha a aba "Fonte LaTeX" antes de compilar.'
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
        pdf_bytes = GovLatexService.compile_with_timbre(
            self.latex_source,
            timbre=timbre,
            fallback_logo_binary=fallback_logo_binary,
            timeout=120,
        )
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
                "latex_snapshot": self.latex_source,
                "pdf_snapshot": b64_pdf,
                "changed_by": self.env.user.id,
                "changed_at": fields.Datetime.now(),
                "change_reason": "PDF compilado via pdflatex",
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
        if not self.latex_source and not self.content_html:
            raise UserError(
                'Nenhum conteúdo encontrado. Preencha a aba "Fonte LaTeX" ou "Conteúdo (HTML)".'
            )

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (
            Timbre.get_default_for_company(self.processo_id.ug_id.id) if Timbre else None
        )

        if self.latex_source:
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
