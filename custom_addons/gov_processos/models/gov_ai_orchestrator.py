import json
import logging
import re
import time

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError

from .gov_ai_doc_service import GovAiDocService


_logger = logging.getLogger(__name__)


class GovAiOrchestrator(models.AbstractModel):
    _name = "gov.ai.orchestrator"
    _description = "Orquestrador de Geração IA"

    _PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _WORD_RE = re.compile(r"\w+", flags=re.UNICODE)

    @api.model
    def _retrieve_memory_records(self, company_id, query, limit=5):
        ml_service = self.env.get("gov.ai.ml.service")
        if ml_service:
            return ml_service.retrieve_context(company_id, query, limit=limit)
        return self.env["gov.ai.memory"].search_relevant(company_id, query, limit=limit)

    @api.model
    def get_policy(self, doc_type, process_type=None):
        Policy = self.env["gov.ai.quality.policy"]
        if process_type:
            policy = Policy.search(
                [
                    ("doc_type", "=", doc_type),
                    ("process_type", "=", process_type),
                    ("active", "=", True),
                ],
                order="sequence, id",
                limit=1,
            )
            if policy:
                return policy
        return Policy.search(
            [
                ("doc_type", "=", doc_type),
                ("process_type", "=", False),
                ("active", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )

    @api.model
    def _build_context_vars(self, doc):
        processo = doc.processo_id
        ug = processo.ug_id
        valor_estimado = ""
        if doc.dfd_valor_estimado:
            valor_estimado = f"R$ {doc.dfd_valor_estimado:,.2f}"
        quantidade = doc.dfd_quantidade or self._plain_text(doc.pesquisa_precos_html or "")[:1200]
        return {
            "processo_numero": processo.name or "",
            "exercicio": str(getattr(ug, "exercicio_fiscal", fields.Date.today().year)),
            "ug_nome": ug.name or "",
            "ug_cnpj": getattr(ug, "cnpj_ug", "") or "",
            "area_requisitante": doc.dfd_area_requisitante or "",
            "responsavel_tecnico": doc.dfd_responsavel_tecnico.name if doc.dfd_responsavel_tecnico else "",
            "objeto": doc.dfd_objeto or "",
            "justificativa": doc.dfd_justificativa or "",
            "quantidade": quantidade,
            "valor_estimado": valor_estimado,
            "data_necessidade": doc.dfd_data_necessidade.strftime("%d/%m/%Y") if doc.dfd_data_necessidade else "",
            "vinculo_ppa": doc.dfd_vinculo_ppa or "",
            "doc_type": doc.doc_type or "",
            "doc_nome": doc.name or "",
            "process_type": processo.process_type or "",
            "process_scope": processo.process_scope or "",
            "assunto": processo.subject or "",
        }

    @api.model
    def _substituir_variaveis(self, template_text, vars_ctx):
        def replacer(match):
            key = match.group(1).lower()
            return str(vars_ctx.get(key, match.group(0)))

        return self._PLACEHOLDER_RE.sub(replacer, template_text or "")

    @api.model
    def _plain_text(self, text):
        plain = self._HTML_TAG_RE.sub(" ", text or "")
        return re.sub(r"\s+", " ", plain).strip()

    @api.model
    def _validar_conformidade(self, conteudo, policy, vars_ctx):
        itens = []
        pontos = 0
        total = 0

        plain = self._plain_text(conteudo)
        num_palavras = len(self._WORD_RE.findall(plain.lower()))
        min_palavras = (policy.min_palavras or 0) if policy else 0

        total += 1
        if num_palavras >= min_palavras:
            pontos += 1
        else:
            itens.append(
                f"Documento com {num_palavras} palavras (mínimo esperado: {min_palavras})."
            )

        if policy and policy.validar_artigos_lei:
            total += 1
            lowered = plain.lower()
            if "14.133" in lowered or "14133" in lowered:
                pontos += 1
            else:
                itens.append("Lei 14.133/2021 não encontrada no conteúdo.")

        if policy and policy.validar_campos_obrigatorios:
            required_keys = []
            template = self.env["gov.ai.template"].browse(self.env.context.get("quality_template_id"))
            if template and template.parameter_spec_json:
                try:
                    spec = json.loads(template.parameter_spec_json)
                    required_keys = list(spec.get("required_by_law", [])) or list(spec.get("required", []))
                except Exception:
                    required_keys = []
            if not required_keys:
                required_keys = ["objeto", "justificativa", "area_requisitante"]

            for key in required_keys:
                value = (vars_ctx.get(key) or "").strip()
                if not value:
                    continue
                total += 1
                probe = value[:50].lower()
                if probe and probe in plain.lower():
                    pontos += 1
                else:
                    itens.append(f'Campo obrigatório "{key}" não foi identificado no texto final.')

        if policy and policy.validar_valores_monetarios:
            total += 1
            has_value_in_context = bool((vars_ctx.get("valor_estimado") or "").strip())
            lowered = plain.lower()
            has_value_in_text = ("r$" in lowered) or ("valor estimado" in lowered)
            if (not has_value_in_context) or has_value_in_text:
                pontos += 1
            else:
                itens.append("Valor monetário esperado não foi encontrado no documento.")

        score = round((pontos / total) * 100) if total else 100
        return {
            "ok": not itens,
            "itens": itens,
            "score": score,
            "num_palavras": num_palavras,
        }

    @api.model
    def _run_pass(
        self,
        doc,
        template,
        provider_config,
        system_prompt,
        user_prompt,
        memory_block,
        pass_number,
        pass_label,
        ai_context=None,
    ):
        run_base = {
            "name": f"IA {pass_label} - {doc.name or 'Documento'}",
            "company_id": doc.processo_id.ug_id.id,
            "processo_id": doc.processo_id.id,
            "doc_id": doc.id,
            "template_id": template.id if template else False,
            "provider": provider_config.provider if provider_config else "odoo_chat",
            "model_name": provider_config.model_name if provider_config else "odoo_chat_local",
            "prompt_system": system_prompt,
            "prompt_user": user_prompt,
            "memory_snapshot": memory_block or "",
        }
        try:
            result = GovAiDocService.generate_text(
                config=provider_config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                template=template,
                context=ai_context,
            )
            run = self.env["gov.ai.run"].create(
                {
                    **run_base,
                    "status": "success",
                    "provider": result.get("provider", run_base["provider"]),
                    "model_name": result.get("model_name", run_base["model_name"]),
                    "response_text": result.get("text", ""),
                    "raw_response": result.get("raw_response", ""),
                    "duration_ms": result.get("duration_ms", 0),
                }
            )
            text = (result.get("text") or "").strip()
            if not text:
                raise UserError(f"Passagem {pass_number} retornou conteúdo vazio.")
            return text, run, result
        except Exception as exc:
            self.env["gov.ai.run"].create(
                {
                    **run_base,
                    "status": "error",
                    "error_message": str(exc),
                }
            )
            if isinstance(exc, UserError):
                raise
            raise UserError(f"Falha na passagem {pass_number}: {exc}") from exc

    @api.model
    def gerar_documento(self, doc_id, template_id=None, instrucao_extra=None):
        doc = self.env["gov.processo.doc"].browse(doc_id)
        if not doc.exists():
            raise UserError("Documento não encontrado.")
        if doc.state == "assinado":
            raise UserError("Documento assinado não pode ser regerado.")

        processo = doc.processo_id
        template = False
        if template_id:
            template = self.env["gov.ai.template"].browse(template_id)
            if not template.exists():
                raise UserError("Template IA selecionado não encontrado.")
        if not template:
            template = doc.ai_template_id or doc._get_default_ai_template()
        if not template and self.env.get("gov.ai.ml.service"):
            ranked = self.env["gov.ai.ml.service"].rank_templates(doc, limit=1)
            if ranked:
                template = ranked[0]
        if not template:
            raise UserError("Nenhum template IA disponível para este documento.")

        policy = self.get_policy(doc.doc_type, processo.process_type)
        provider = self.env["gov.ai.provider.config"].get_active_for_company(processo.ug_id.id)
        if not provider:
            provider = doc._build_fallback_ai_config()

        query = " ".join(
            [
                processo.subject or "",
                doc.name or "",
                template.name or "",
                doc._plain_text_from_html(doc.content_html or "")[:500],
                doc.latex_source or "",
            ]
        ).strip()
        memory_records = self._retrieve_memory_records(
            processo.ug_id.id,
            query,
            limit=provider.memory_top_k or 5,
        )
        memory_block = GovAiDocService.build_memory_block(memory_records)

        vars_ctx = self._build_context_vars(doc)
        if memory_block:
            vars_ctx["memoria_ug"] = memory_block
        if instrucao_extra:
            vars_ctx["instrucao_extra"] = instrucao_extra

        system_prompt = (
            template.prompt_system
            or "Você é especialista em contratações públicas brasileiras. "
            "Redija com linguagem formal e precisão jurídica sem inventar dados."
        )
        user_prompt_base = self._substituir_variaveis(template.prompt_user_tpl or "", vars_ctx).strip()
        if not user_prompt_base:
            user_prompt_base = (
                f"Gere documento do tipo {doc.doc_type} para o processo {processo.name or ''}. "
                f"Assunto: {processo.subject or ''}. Objeto: {vars_ctx.get('objeto') or ''}."
            )
        if instrucao_extra:
            user_prompt_base += f"\n\nInstrução adicional do gestor:\n{instrucao_extra}"
        if memory_block:
            user_prompt_base += (
                "\n\n### Memória institucional da UG (use quando pertinente):\n"
                f"{memory_block}"
            )

        passagens = []
        t0 = time.time()
        num_passagens = policy.num_passagens if policy else 1
        last_run = False

        prompt_p1 = user_prompt_base
        if policy and policy.passagem_1_instrucao:
            prompt_p1 += f"\n\n{policy.passagem_1_instrucao}"
        if template.output_format == "latex" and template.latex_template:
            prompt_p1 += (
                "\n\nUse o template LaTeX abaixo como base e preencha as variáveis:\n\n"
                f"{template.latex_template}"
            )
        elif template.output_format == "typst" and template.typst_template:
            prompt_p1 += (
                "\n\nUse o template Typst abaixo como base e preencha as variáveis:\n\n"
                f"{template.typst_template}"
            )
        conteudo, run, info = self._run_pass(
            doc,
            template,
            provider,
            system_prompt,
            prompt_p1,
            memory_block,
            pass_number=1,
            pass_label="Passagem 1 - Rascunho",
            ai_context=vars_ctx,
        )
        last_run = run
        passagens.append({"numero": 1, "tipo": "rascunho", "chars": len(conteudo)})

        if num_passagens >= 2:
            instrucao = (
                policy.passagem_2_instrucao
                if policy and policy.passagem_2_instrucao
                else (
                    "Revise juridicamente o documento, eliminando lacunas e "
                    "corrigindo linguagem normativa."
                )
            )
            prompt_p2 = f"Documento atual:\n\n{conteudo}\n\n{instrucao}"
            conteudo, run, info = self._run_pass(
                doc,
                template,
                provider,
                system_prompt,
                prompt_p2,
                memory_block,
                pass_number=2,
                pass_label="Passagem 2 - Revisão Jurídica",
                ai_context=vars_ctx,
            )
            last_run = run
            passagens.append({"numero": 2, "tipo": "revisao_juridica", "chars": len(conteudo)})

        if num_passagens >= 3:
            instrucao = (
                policy.passagem_3_instrucao
                if policy and policy.passagem_3_instrucao
                else "Faça ajuste final de clareza e coesão textual mantendo o rigor técnico."
            )
            prompt_p3 = f"Documento atual:\n\n{conteudo}\n\n{instrucao}"
            conteudo, run, info = self._run_pass(
                doc,
                template,
                provider,
                system_prompt,
                prompt_p3,
                memory_block,
                pass_number=3,
                pass_label="Passagem 3 - Ajuste Final",
                ai_context=vars_ctx,
            )
            last_run = run
            passagens.append({"numero": 3, "tipo": "ajuste_final", "chars": len(conteudo)})

        validacao_extra = {}
        if policy and policy.prompt_validacao:
            prompt_val = (
                "Avalie o conteúdo abaixo e retorne JSON com "
                '{"score": 0-100, "itens": ["..."]}.\n\n'
                f"{conteudo}\n\n"
                f"{policy.prompt_validacao}"
            )
            val_text, run, info = self._run_pass(
                doc,
                template,
                provider,
                system_prompt,
                prompt_val,
                memory_block,
                pass_number=99,
                pass_label="Passagem Extra - Auto-validação",
                ai_context=vars_ctx,
            )
            last_run = run
            try:
                validacao_extra = json.loads(val_text)
            except Exception:
                validacao_extra = {
                    "score": 0,
                    "itens": [f"Auto-validação retornou formato inválido: {escape(val_text[:280])}"],
                }

        conformidade = self.with_context(quality_template_id=template.id)._validar_conformidade(
            conteudo,
            policy,
            vars_ctx,
        )
        if validacao_extra:
            extra_itens = validacao_extra.get("itens") or []
            if isinstance(extra_itens, list):
                conformidade["itens"].extend([str(item) for item in extra_itens])
            extra_score = validacao_extra.get("score")
            if isinstance(extra_score, (int, float)):
                conformidade["score"] = round((conformidade["score"] + int(extra_score)) / 2)

        e_latex = (
            conteudo.strip().startswith("\\documentclass")
            or "\\begin{document}" in conteudo
        )
        e_typst = template.output_format == "typst"
        vals = {
            "ai_generated": True,
            "ai_template_id": template.id,
            "ai_provider_used": provider.provider if provider else "odoo_chat",
            "ai_model_used": provider.model_name if provider else "odoo_chat_local",
            "ai_last_run_id": last_run.id if last_run else False,
            "change_reason": f"Gerado por orquestrador IA ({len(passagens)} passagem(ns))",
        }
        if e_typst:
            vals["typst_source"] = conteudo
            vals["latex_source"] = False
            vals["content_html"] = False
        elif e_latex:
            vals["latex_source"] = conteudo
        else:
            if "<" in conteudo and ">" in conteudo:
                vals["content_html"] = conteudo
            else:
                vals["content_html"] = (
                    "<h3>Rascunho IA Orquestrado</h3><pre style='white-space:pre-wrap'>"
                    f"{escape(conteudo)}</pre>"
                )

        estado_destino = policy.estado_apos_geracao if policy else "revisao"
        if estado_destino and doc.state == "rascunho":
            vals["state"] = estado_destino

        doc.write(vals)
        if memory_records:
            memory_records.mark_used()

        duracao = round(time.time() - t0, 1)
        badge = "🟢" if conformidade["score"] >= 80 else "🟡" if conformidade["score"] >= 50 else "🔴"
        itens_html = "".join(f"<li>{escape(item)}</li>" for item in conformidade["itens"])
        if not itens_html:
            itens_html = "<li>Nenhum problema identificado.</li>"
        processo.message_post(
            body=Markup(
                f"🤖 <b>Documento gerado por IA</b>: {escape(doc.name or '')}<br/>"
                f"Passagens: {len(passagens)} | Motor: <b>{escape(provider.provider if provider else 'odoo_chat')}</b> | "
                f"Duração: {duracao}s<br/>"
                f"Score de conformidade: {badge} <b>{conformidade['score']}%</b><br/>"
                f"<ul>{Markup(itens_html)}</ul>"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        if policy and policy.notificar_responsavel and processo.responsible_id:
            processo.message_post(
                body=Markup(
                    f"📬 Documento <b>{escape(doc.name or '')}</b> gerado por IA aguarda revisão."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=processo.responsible_id.mapped("partner_id").ids,
            )

        return {
            "conteudo": conteudo,
            "e_latex": e_latex,
            "output_format": "typst" if e_typst else ("latex" if e_latex else "html"),
            "score": conformidade["score"],
            "itens_conformidade": conformidade["itens"],
            "passagens": passagens,
            "duracao_segundos": duracao,
            "estado": estado_destino,
        }
