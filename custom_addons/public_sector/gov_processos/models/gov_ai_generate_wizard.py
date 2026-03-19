import json

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError

class GovAiGenerateWizard(models.TransientModel):
    _name = "gov.ai.generate.wizard"
    _description = "Wizard de Geração IA Orquestrada"

    doc_id = fields.Many2one(
        "gov.processo.doc",
        required=True,
        readonly=True,
    )
    processo_id = fields.Many2one(
        "gov.processo",
        related="doc_id.processo_id",
        readonly=True,
    )
    doc_type = fields.Selection(related="doc_id.doc_type", readonly=True)
    template_id = fields.Many2one(
        "gov.ai.template",
        string="Template",
        domain="[('doc_type','=',doc_type),('active','=',True)]",
        help="Deixe vazio para seleção automática.",
    )
    instrucao_extra = fields.Text(
        string="Instrução em Linguagem Natural",
        help="Descreva em linguagem livre o contexto adicional que deve entrar no documento.",
    )
    policy_preview = fields.Text(
        string="Política de Qualidade Aplicada",
        compute="_compute_policy_preview",
    )

    step = fields.Selection(
        [
            ("input", "Configuração"),
            ("result", "Resultado"),
        ],
        string="Etapa",
        default="input",
    )

    resultado_conteudo = fields.Text(
        string="Conteúdo Gerado",
        help="Conteúdo LaTeX ou HTML gerado pela IA.",
    )
    resultado_e_latex = fields.Boolean(default=False)
    resultado_formato = fields.Selection(
        [
            ("latex", "LaTeX"),
            ("typst", "Typst"),
            ("html", "HTML"),
        ],
        string="Formato do Resultado",
        default="html",
    )
    resultado_score = fields.Integer(
        string="Score de Conformidade",
        default=0,
    )
    resultado_itens = fields.Text(string="Itens de Conformidade")
    resultado_passagens = fields.Text(string="Passagens Executadas (JSON)")
    resultado_duracao = fields.Float(string="Duração (s)", default=0.0)
    resultado_estado = fields.Char(string="Estado Definido")
    score_badge = fields.Char(
        string="Badge de Score",
        compute="_compute_score_badge",
    )

    @api.depends("doc_id", "template_id")
    def _compute_policy_preview(self):
        orch = self.env["gov.ai.orchestrator"]
        for rec in self:
            if not rec.doc_id:
                rec.policy_preview = "—"
                continue
            processo = rec.doc_id.processo_id
            policy = orch.get_policy(rec.doc_id.doc_type, processo.process_type)
            if not policy:
                rec.policy_preview = "Nenhuma política ativa. Pipeline com 1 passagem."
                continue
            rec.policy_preview = (
                f"{policy.name}\n"
                f"Passagens: {policy.num_passagens} | "
                f"Estado após geração: {policy.estado_apos_geracao}\n"
                f"Validação Lei 14.133: {'sim' if policy.validar_artigos_lei else 'não'} | "
                f"Mínimo de palavras: {policy.min_palavras}"
            )

    @api.depends("resultado_score")
    def _compute_score_badge(self):
        for rec in self:
            score = int(rec.resultado_score or 0)
            if score >= 80:
                rec.score_badge = f"🟢 {score}% - Excelente"
            elif score >= 50:
                rec.score_badge = f"🟡 {score}% - Atenção necessária"
            else:
                rec.score_badge = f"🔴 {score}% - Revisão obrigatória"

    def action_gerar(self):
        """Executa geração e transita para a etapa de resultado."""
        self.ensure_one()
        if not self.doc_id:
            raise UserError("Documento não informado para geração IA.")

        resultado = self.env["gov.ai.orchestrator"].gerar_documento(
            doc_id=self.doc_id.id,
            template_id=self.template_id.id if self.template_id else None,
            instrucao_extra=self.instrucao_extra,
        )
        self.write(
            {
                "step": "result",
                "resultado_conteudo": resultado.get("conteudo") or "",
                "resultado_e_latex": bool(resultado.get("e_latex")),
                "resultado_formato": resultado.get("output_format") or (
                    "latex" if resultado.get("e_latex") else "html"
                ),
                "resultado_score": int(resultado.get("score", 0) or 0),
                "resultado_itens": "\n".join(resultado.get("itens_conformidade") or [])
                or "Nenhum problema identificado.",
                "resultado_passagens": json.dumps(
                    resultado.get("passagens") or [],
                    ensure_ascii=False,
                ),
                "resultado_duracao": float(resultado.get("duracao_segundos", 0) or 0),
                "resultado_estado": resultado.get("estado", "revisao"),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.ai.generate.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_aceitar(self):
        """Aceita o resultado: salva no documento e fecha o wizard."""
        self.ensure_one()
        doc = self.doc_id
        if not doc:
            raise UserError("Documento não encontrado para aceitar resultado.")
        if not self.resultado_conteudo:
            raise UserError("Não há conteúdo gerado para aceitar.")

        vals = {"ai_generated": True}
        if self.resultado_formato == "typst":
            vals["typst_source"] = self.resultado_conteudo
            vals["latex_source"] = False
            vals["content_html"] = False
        elif self.resultado_e_latex or self.resultado_formato == "latex":
            vals["latex_source"] = self.resultado_conteudo
        else:
            vals["content_html"] = self.resultado_conteudo
        if self.resultado_estado and doc.state == "rascunho":
            vals["state"] = self.resultado_estado

        doc.with_context(skip_versao_snapshot=True).write(vals)
        ml_service = self.env.get("gov.ai.ml.service")
        if ml_service:
            ml_service.log_feedback(
                doc=doc,
                accepted=True,
                score_manual=int(self.resultado_score or 0),
                notes="Aceito no wizard de geracao IA.",
                run=doc.ai_last_run_id,
                template=self.template_id or doc.ai_template_id,
            )
        doc.message_post(
            body=Markup(
                "✅ <b>Conteúdo IA aceito</b> por "
                f"{escape(self.env.user.name)}.<br/>"
                f"Score: {int(self.resultado_score or 0)}%"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {"type": "ir.actions.act_window_close"}

    def action_rejeitar(self):
        """Rejeita o resultado e retorna para etapa de configuração."""
        self.ensure_one()
        if self.doc_id:
            ml_service = self.env.get("gov.ai.ml.service")
            if ml_service:
                ml_service.log_feedback(
                    doc=self.doc_id,
                    accepted=False,
                    score_manual=0,
                    notes="Rejeitado no wizard de geracao IA. Nova tentativa solicitada.",
                    run=self.doc_id.ai_last_run_id,
                    template=self.template_id or self.doc_id.ai_template_id,
                )
            self.doc_id.message_post(
                body=Markup(
                    "❌ <b>Geração IA rejeitada</b> por "
                    f"{escape(self.env.user.name)}. Nova tentativa solicitada."
                ),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        self.write(
            {
                "step": "input",
                "resultado_conteudo": False,
                "resultado_e_latex": False,
                "resultado_formato": "html",
                "resultado_score": 0,
                "resultado_itens": False,
                "resultado_passagens": False,
                "resultado_duracao": 0.0,
                "resultado_estado": False,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.ai.generate.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_aceitar_e_compilar(self):
        """Aceita e, quando LaTeX, compila PDF automaticamente."""
        self.ensure_one()
        self.action_aceitar()
        if self.resultado_formato in {"latex", "typst"} and self.doc_id:
            self.doc_id.action_gerar_pdf()
        return {"type": "ir.actions.act_window_close"}
