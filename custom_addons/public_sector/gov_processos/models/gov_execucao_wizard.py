import base64
import hashlib
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.gov_latex_jinja_service import GovLatexJinjaService

_logger = logging.getLogger(__name__)


class GovExecucaoWizard(models.TransientModel):
    _name = "gov.execucao.wizard"
    _description = "Relatorio de Execucao Orcamentaria - PDF"

    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    exercicio = fields.Integer(
        string="Exercicio",
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    data_ini = fields.Date(
        string="Data Inicio",
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1),
    )
    data_fim = fields.Date(
        string="Data Fim",
        required=True,
        default=fields.Date.today,
    )
    agrupar_por = fields.Selection(
        [
            ("natureza", "Natureza de Despesa"),
            ("credor", "Credor / Fornecedor"),
        ],
        default="natureza",
        required=True,
        string="Agrupar por",
    )

    preview_resumo = fields.Text(
        string="Resumo",
        compute="_compute_preview",
        store=False,
    )

    pdf_file = fields.Binary(string="PDF", readonly=True)
    pdf_filename = fields.Char(readonly=True)
    hash_sha256 = fields.Char(readonly=True)
    gerado = fields.Boolean(default=False)

    @api.depends("ug_id", "exercicio", "data_ini", "data_fim", "agrupar_por")
    def _compute_preview(self):
        for rec in self:
            try:
                linhas = rec._consolidar()
                total_emp = sum(item["empenhado"] for item in linhas)
                total_liq = sum(item["liquidado"] for item in linhas)
                total_pag = sum(item["pago"] for item in linhas)
                rec.preview_resumo = (
                    f"Grupos encontrados: {len(linhas)}\n"
                    f"Total empenhado: R$ {total_emp:,.2f}\n"
                    f"Total liquidado: R$ {total_liq:,.2f}\n"
                    f"Total pago:      R$ {total_pag:,.2f}"
                )
            except Exception as exc:
                rec.preview_resumo = f"Erro no preview: {exc}"

    def _consolidar(self):
        self.ensure_one()

        if "gov.empenho" not in self.env:
            return []

        has_nl = "gov.liquidacao" in self.env
        has_op = "gov.pagamento" in self.env
        has_dot = "gov.processo.dotacao" in self.env

        NE = self.env["gov.empenho"]
        NL = self.env["gov.liquidacao"] if has_nl else False
        OP = self.env["gov.pagamento"] if has_op else False
        DOT = self.env["gov.processo.dotacao"] if has_dot else False

        nes = NE.search(
            [
                ("ug_id", "=", self.ug_id.id),
                ("exercicio", "=", self.exercicio),
                ("state", "in", ["emitido"]),
            ]
        )

        nls = (
            NL.search(
                [
                    ("ug_id", "=", self.ug_id.id),
                    ("exercicio", "=", self.exercicio),
                    ("state", "=", "liquidado"),
                    ("data_liquidacao", ">=", self.data_ini),
                    ("data_liquidacao", "<=", self.data_fim),
                ]
            )
            if has_nl
            else []
        )

        ops = (
            OP.search(
                [
                    ("ug_id", "=", self.ug_id.id),
                    ("exercicio", "=", self.exercicio),
                    ("state", "=", "pago"),
                    ("data_pagamento", ">=", self.data_ini),
                    ("data_pagamento", "<=", self.data_fim),
                ]
            )
            if has_op
            else []
        )

        def key_ne(ne):
            if self.agrupar_por == "natureza":
                return ne.natureza_despesa or "SEM NATUREZA"
            return ne.credor_id.name if ne.credor_id else "SEM CREDOR"

        def key_nl(nl):
            if self.agrupar_por == "natureza":
                return nl.natureza_despesa or "SEM NATUREZA"
            return nl.credor_id.name if nl.credor_id else "SEM CREDOR"

        def key_op(op):
            if self.agrupar_por == "natureza":
                pd = op.pd_id
                if pd and pd.liquidacao_id:
                    return pd.liquidacao_id.natureza_despesa or "SEM NATUREZA"
                return "SEM NATUREZA"
            return op.destinatario_id.name if op.destinatario_id else "SEM CREDOR"

        grupos = {}

        def _touch_group(key):
            if key not in grupos:
                grupos[key] = {
                    "grupo": key,
                    "dotacao": 0.0,
                    "empenhado": 0.0,
                    "liquidado": 0.0,
                    "pago": 0.0,
                }
            return grupos[key]

        for ne in nes:
            grupo = _touch_group(key_ne(ne))
            grupo["empenhado"] += float(ne.valor_empenho or 0.0)

        for nl in nls:
            grupo = _touch_group(key_nl(nl))
            grupo["liquidado"] += float(nl.valor_liquidado or 0.0)

        for op in ops:
            grupo = _touch_group(key_op(op))
            grupo["pago"] += float(op.valor or 0.0)

        if has_dot:
            domain_dot = [("exercicio", "=", self.exercicio)]
            if "processo_id" in DOT._fields:
                domain_dot.append(("processo_id.ug_id", "=", self.ug_id.id))
            dotacoes = DOT.search(domain_dot)

            for dot in dotacoes:
                key = (
                    dot.natureza_despesa or "SEM NATUREZA"
                    if self.agrupar_por == "natureza"
                    else "SEM CREDOR"
                )
                grupo = _touch_group(key)
                grupo["dotacao"] += float(dot.valor_estimado or 0.0)

        resultado = []
        for _, grupo in sorted(grupos.items(), key=lambda item: item[0]):
            base = grupo["dotacao"] or grupo["empenhado"] or 1.0
            grupo["pct_emp"] = min(round(grupo["empenhado"] / base * 100, 1), 999.9)
            grupo["pct_liq"] = min(round(grupo["liquidado"] / base * 100, 1), 999.9)
            grupo["pct_pag"] = min(round(grupo["pago"] / base * 100, 1), 999.9)
            resultado.append(grupo)

        return resultado

    def _build_execucao_context(self, linhas):
        """Monta o contexto para o template execucao.tex.j2."""
        self.ensure_one()
        Timbre = self.env["gov.timbre"] if "gov.timbre" in self.env else False
        timbre = (
            Timbre.get_default_for_company(self.ug_id.id) if Timbre else None
        )

        bloco_cabecalho = (
            timbre.get_latex_cabecalho()
            if timbre
            else (
                r"\begin{center}{\large\bfseries "
                + self.ug_id.name
                + r"}\end{center}\vspace{0.3cm}"
            )
        )
        bloco_rodape = (
            timbre.get_latex_rodape()
            if timbre
            else (
                r"\begin{center}{\small\color{gray} "
                + self.ug_id.name
                + r"}\end{center}"
            )
        )

        total_dot = sum(item["dotacao"] for item in linhas)
        total_emp = sum(item["empenhado"] for item in linhas)
        total_liq = sum(item["liquidado"] for item in linhas)
        total_pag = sum(item["pago"] for item in linhas)
        pct_geral = round(total_emp / total_dot * 100, 1) if total_dot else 0.0

        top5 = sorted(linhas, key=lambda item: item["empenhado"], reverse=True)[:5]
        max_val = max((item["empenhado"] for item in top5), default=1.0) or 1.0
        top5_bars = []
        for index, item in enumerate(top5):
            y_mid = (len(top5) - index) * 1.2
            w_emp = round((item["empenhado"] / max_val) * 8, 2)
            w_pag = round((item["pago"] / max_val) * 8, 2)
            top5_bars.append(
                {
                    "y_low_emp": round(y_mid - 0.3, 1),
                    "y_high_emp": round(y_mid + 0.3, 1),
                    "y_low_pag": round(y_mid - 0.55, 2),
                    "y_high_pag": round(y_mid - 0.05, 2),
                    "y_mid": round(y_mid, 1),
                    "w_emp": w_emp,
                    "w_pag": w_pag,
                    "label": item["grupo"][:20],
                    "emp_fmt": f"{item['empenhado']:,.0f}",
                }
            )

        agrupamento = (
            "Natureza de Despesa"
            if self.agrupar_por == "natureza"
            else "Credor / Fornecedor"
        )

        return {
            "ug_nome": self.ug_id.name or "",
            "exercicio": str(self.exercicio),
            "data_ini": self.data_ini.strftime("%d/%m/%Y"),
            "data_fim": self.data_fim.strftime("%d/%m/%Y"),
            "agrupamento": agrupamento,
            "bloco_cabecalho": bloco_cabecalho,
            "bloco_rodape": bloco_rodape,
            "total_dot": total_dot,
            "total_emp": total_emp,
            "total_liq": total_liq,
            "total_pag": total_pag,
            "pct_geral": f"{pct_geral:.1f}",
            "linhas": [
                {
                    "grupo": item["grupo"],
                    "dotacao": item["dotacao"],
                    "empenhado": item["empenhado"],
                    "liquidado": item["liquidado"],
                    "pago": item["pago"],
                    "pct_emp": f"{item['pct_emp']:.1f}",
                    "pct_liq": f"{item['pct_liq']:.1f}",
                    "pct_pag": f"{item['pct_pag']:.1f}",
                }
                for item in linhas
            ],
            "top5": top5_bars,
            "top5_bars": top5_bars,
        }

    def action_gerar_pdf(self):
        self.ensure_one()
        linhas = self._consolidar()
        if not linhas:
            raise UserError("Nenhum dado encontrado para o periodo informado.")

        ctx = self._build_execucao_context(linhas)

        extra_images = {}
        if "gov.timbre" in self.env:
            timbre = self.env["gov.timbre"].get_default_for_company(
                self.ug_id.id
            )
            if timbre:
                extra_images = timbre.get_imagens_para_latex()

        pdf_bytes = GovLatexJinjaService.render_and_compile(
            "execucao.tex.j2",
            ctx,
            extra_images=extra_images,
            timeout=120,
            two_passes=True,  # longtable precisa de 2 passagens
        )
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        filename = (
            f"ExecucaoOrcamentaria_{self.ug_id.name}"
            f"_{self.exercicio}_{fields.Date.today()}.pdf"
        ).replace(" ", "_")

        self.write(
            {
                "pdf_file": base64.b64encode(pdf_bytes).decode("ascii"),
                "pdf_filename": filename,
                "hash_sha256": sha256,
                "gerado": True,
            }
        )
        return self._reabrir()

    def _reabrir(self):
        self.invalidate_recordset()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.execucao.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
