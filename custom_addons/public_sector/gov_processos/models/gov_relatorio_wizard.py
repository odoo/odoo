import base64
import hashlib
import re

from odoo import fields, models
from odoo.exceptions import UserError

from ..services.gov_latex_jinja_service import GovLatexJinjaService


class GovRelatorioWizard(models.TransientModel):
    _name = "gov.relatorio.wizard"
    _description = "Wizard de Relatorio Executivo AGI Gov"

    titulo = fields.Char(
        string="Titulo do Relatorio",
        default="Relatorio Executivo de Processos Administrativos",
        required=True,
    )
    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        default=lambda self: self.env.company,
        required=True,
    )
    exercicio = fields.Integer(
        string="Exercicio",
        default=lambda self: fields.Date.today().year,
        required=True,
    )
    timbre_id = fields.Many2one(
        "gov.timbre",
        string="Timbre",
        help="Se vazio, usa o timbre padrao da UG.",
    )
    data_referencia = fields.Date(
        string="Data de Referencia",
        default=fields.Date.today,
        required=True,
    )

    incluir_kpis = fields.Boolean("KPIs por Fase", default=True)
    incluir_alertas = fields.Boolean("Alertas e Urgencias", default=True)
    incluir_financeiro = fields.Boolean("Resumo Financeiro", default=True)
    incluir_criticos = fields.Boolean("Processos Criticos", default=True)
    incluir_inercia = fields.Boolean("Mapa de Inercia", default=True)
    incluir_docs_ia = fields.Boolean("Documentos IA Pendentes", default=False)
    max_criticos = fields.Integer("Max. processos criticos", default=15)

    assinante_nome = fields.Char(
        string="Nome do Assinante",
        default=lambda self: self.env.user.name,
    )
    assinante_cargo = fields.Char(string="Cargo / Funcao")
    incluir_assinatura = fields.Boolean(
        "Incluir Campo de Assinatura",
        default=True,
    )

    pdf_file = fields.Binary("PDF Gerado", readonly=True)
    pdf_filename = fields.Char(readonly=True)
    hash_sha256 = fields.Char(readonly=True)
    gerado = fields.Boolean(default=False)

    def _build_relatorio_context(self, data):
        """Monta o dicionario de contexto para o template relatorio.tex.j2."""
        self.ensure_one()

        kpis_raw = data.get("kpis", {})
        alertas_raw = data.get("alertas", {})
        financeiro_raw = data.get("financeiro", {})
        docs_raw = data.get("docs", {})
        criticos_raw = data.get("lista_criticos", [])
        mapa_raw = data.get("mapa_inercia", [])

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (
            Timbre.get_default_for_company(self.ug_id.id) if Timbre else None
        )

        cor1 = (
            getattr(timbre, "rodape_cor_barra_superior", "") if timbre else ""
        ) or "1F4E79"
        cor2 = (
            getattr(timbre, "rodape_cor_barra_inferior", "") if timbre else ""
        ) or "2E75B6"
        esp1 = (
            getattr(timbre, "rodape_espessura_superior", 0.0) if timbre else 0.0
        ) or 6.0
        esp2 = (
            getattr(timbre, "rodape_espessura_inferior", 0.0) if timbre else 0.0
        ) or 2.0
        largura_logo = (
            getattr(timbre, "logo_width_mm", 0.0) if timbre else 0.0
        ) or 30.0

        total_ativos = kpis_raw.get("total_ativos", 0) or 0

        def pct(value):
            return round((value / total_ativos) * 100) if total_ativos else 0

        kpis = {
            "total_ativos": total_ativos,
            "encerrados_mes": kpis_raw.get("encerrados_mes", 0) or 0,
            "em_demanda": kpis_raw.get("em_demanda", 0) or 0,
            "pct_demanda": pct(kpis_raw.get("em_demanda", 0)),
            "em_instrucao": kpis_raw.get("em_instrucao", 0) or 0,
            "pct_instrucao": pct(kpis_raw.get("em_instrucao", 0)),
            "em_planejamento": kpis_raw.get("em_planejamento", 0) or 0,
            "pct_planejamento": pct(kpis_raw.get("em_planejamento", 0)),
            "em_licitacao": kpis_raw.get("em_licitacao", 0) or 0,
            "pct_licitacao": pct(kpis_raw.get("em_licitacao", 0)),
            "em_contratacao": kpis_raw.get("em_contratacao", 0) or 0,
            "pct_contratacao": pct(kpis_raw.get("em_contratacao", 0)),
            "em_execucao": kpis_raw.get("em_execucao", 0) or 0,
            "pct_execucao": pct(kpis_raw.get("em_execucao", 0)),
        }

        def _cor_alerta(val, limiar=1):
            return "alertred" if val >= limiar else "okgreen"

        prazos_vencidos = alertas_raw.get("prazos_vencidos", 0) or 0
        prazos_proximos = alertas_raw.get("prazos_proximos", 0) or 0
        processos_inertes = alertas_raw.get("processos_inertes", 0) or 0
        urgentes_ativos = alertas_raw.get("urgentes_ativos", 0) or 0
        alertas = {
            "prazos_vencidos": prazos_vencidos,
            "cor_venc": _cor_alerta(prazos_vencidos),
            "prazos_proximos": prazos_proximos,
            "cor_prox": "alertyellow" if prazos_proximos > 0 else "okgreen",
            "processos_inertes": processos_inertes,
            "cor_iner": "alertyellow" if processos_inertes > 0 else "okgreen",
            "urgentes_ativos": urgentes_ativos,
            "cor_urg": _cor_alerta(urgentes_ativos),
            "retroativos_ativos": alertas_raw.get("retroativos_ativos", 0) or 0,
        }

        criticos = []
        for item in criticos_raw[: self.max_criticos]:
            if item.get("prazo_vencido"):
                alerta_latex = r"\textcolor{alertred}{\textbf{VENCIDO}}"
            elif item.get("urgencia"):
                alerta_latex = r"\textcolor{alertyellow}{\textbf{URG}}"
            else:
                alerta_latex = "---"
            criticos.append(
                {
                    "name": item.get("name", ""),
                    "subject": (item.get("subject", "") or "")[:50],
                    "state": item.get("state", ""),
                    "responsible": item.get("responsible", "\u2014"),
                    "prazo_resposta": item.get("prazo_resposta", "\u2014"),
                    "alerta_latex": alerta_latex,
                }
            )

        mapa_inercia = [
            {
                "ug": item.get("ug", ""),
                "total": item.get("total", 0) or 0,
                "inertes": item.get("inertes", 0) or 0,
                "pct": item.get("pct", 0) or 0,
                "cor": "alertred" if (item.get("pct", 0) or 0) > 50 else "alertyellow",
            }
            for item in mapa_raw
        ]

        return {
            "orgao_nome": (
                timbre.orgao_nome if timbre and timbre.orgao_nome else self.ug_id.name
            ),
            "secretaria_nome": getattr(timbre, "secretaria_nome", "") if timbre else "",
            "cnpj": (
                timbre.cnpj
                if timbre and timbre.cnpj
                else (getattr(self.ug_id, "cnpj_ug", "") or "")
            ),
            "cor1": cor1,
            "cor2": cor2,
            "esp1": esp1,
            "esp2": esp2,
            "largura_logo": largura_logo,
            "titulo": self.titulo,
            "exercicio": self.exercicio,
            "data_ref": self.data_referencia.strftime("%d/%m/%Y"),
            "incluir_kpis": self.incluir_kpis,
            "incluir_alertas": self.incluir_alertas,
            "incluir_financeiro": self.incluir_financeiro,
            "incluir_criticos": self.incluir_criticos,
            "incluir_inercia": self.incluir_inercia,
            "incluir_docs_ia": self.incluir_docs_ia,
            "incluir_assinatura": self.incluir_assinatura,
            "assinante_nome": self.assinante_nome or "",
            "assinante_cargo": self.assinante_cargo or "",
            "kpis": kpis,
            "alertas": alertas,
            "financeiro": {
                "valor_total": financeiro_raw.get("valor_total", 0.0) or 0.0,
                "docs_em_revisao": docs_raw.get("em_revisao", 0),
                "ia_pendentes": docs_raw.get("ia_pendentes", 0),
            },
            "criticos": criticos,
            "mapa_inercia": mapa_inercia,
        }

    def action_gerar_relatorio(self):
        self.ensure_one()
        dashboard_data = self.env["gov.dashboard"].get_dashboard_data(
            ug_id=self.ug_id.id
        )
        ctx = self._build_relatorio_context(dashboard_data)

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (
            Timbre.get_default_for_company(self.ug_id.id) if Timbre else None
        )
        fallback_logo = (
            base64.b64decode(self.ug_id.logo) if self.ug_id.logo else None
        )
        extra_images = {}
        if timbre and hasattr(timbre, "get_imagens_para_latex"):
            try:
                extra_images = timbre.get_imagens_para_latex() or {}
            except Exception:
                pass

        pdf_bytes = GovLatexJinjaService.render_and_compile(
            "relatorio.tex.j2",
            ctx,
            logo_binary=fallback_logo,
            extra_images=extra_images,
            timeout=120,
        )

        b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        ug_nome = re.sub(r"[^a-zA-Z0-9_-]+", "_", self.ug_id.name or "ug")
        filename = (
            f"relatorio_executivo_{ug_nome}"
            f"_{self.exercicio}_{self.data_referencia}.pdf"
        )
        self.write(
            {
                "pdf_file": b64_pdf,
                "pdf_filename": filename,
                "hash_sha256": sha256,
                "gerado": True,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.relatorio.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
