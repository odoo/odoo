import base64
import hashlib
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

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

    def _build_latex(self, linhas):
        def esc(text):
            if not text:
                return ""
            txt = str(text)
            replacements = [
                ("\\", r"\textbackslash{}"),
                ("&", r"\&"),
                ("%", r"\%"),
                ("$", r"\$"),
                ("#", r"\#"),
                ("{", r"\{"),
                ("}", r"\}"),
                ("~", r"\textasciitilde{}"),
                ("^", r"\textasciicircum{}"),
                ("_", r"\_"),
            ]
            for old, new in replacements:
                txt = txt.replace(old, new)
            return txt

        Timbre = self.env["gov.timbre"] if "gov.timbre" in self.env else False
        timbre = Timbre.get_default_for_company(self.ug_id.id) if Timbre else None

        bloco_cabecalho = (
            timbre.get_latex_cabecalho()
            if timbre
            else (
                rf"\begin{{center}}{{\large\bfseries {esc(self.ug_id.name)}}}\end{{center}}"
                rf"\vspace{{0.3cm}}"
            )
        )
        bloco_rodape = (
            timbre.get_latex_rodape()
            if timbre
            else (
                rf"\begin{{center}}{{\small\color{{gray}} {esc(self.ug_id.name)}}}\end{{center}}"
            )
        )

        exercicio = str(self.exercicio)
        data_ini = self.data_ini.strftime("%d/%m/%Y")
        data_fim = self.data_fim.strftime("%d/%m/%Y")
        agrupamento = (
            "Natureza de Despesa"
            if self.agrupar_por == "natureza"
            else "Credor / Fornecedor"
        )

        total_dot = sum(item["dotacao"] for item in linhas)
        total_emp = sum(item["empenhado"] for item in linhas)
        total_liq = sum(item["liquidado"] for item in linhas)
        total_pag = sum(item["pago"] for item in linhas)
        pct_geral = round(total_emp / total_dot * 100, 1) if total_dot else 0.0

        rows = ""
        for item in linhas:
            grupo_fmt = esc(item["grupo"])[:40]
            rows += (
                rf"{grupo_fmt} & "
                rf"R\$ {item['dotacao']:>12,.2f} & "
                rf"R\$ {item['empenhado']:>12,.2f} & "
                rf"{item['pct_emp']:>5.1f}\% & "
                rf"R\$ {item['liquidado']:>12,.2f} & "
                rf"{item['pct_liq']:>5.1f}\% & "
                rf"R\$ {item['pago']:>12,.2f} & "
                rf"{item['pct_pag']:>5.1f}\% "
                r"\\ \hline" + "\n"
            )

        top5 = sorted(linhas, key=lambda item: item["empenhado"], reverse=True)[:5]
        max_val = max((item["empenhado"] for item in top5), default=1.0) or 1.0
        tikz_bars = ""
        for index, item in enumerate(top5):
            y = (len(top5) - index) * 1.2
            width_emp = (item["empenhado"] / max_val) * 8
            width_pag = (item["pago"] / max_val) * 8
            label = esc(item["grupo"])[:20]
            tikz_bars += (
                rf"\draw[fill=govblue!70] (0,{y-0.3:.1f}) rectangle ({width_emp:.2f},{y+0.3:.1f});"
                + "\n"
                rf"\draw[fill=govgreen!70] (0,{y-0.55:.1f}) rectangle ({width_pag:.2f},{y-0.05:.1f});"
                + "\n"
                rf"\node[anchor=east,font=\tiny] at (-0.1,{y:.1f}) {{{label}}};"
                + "\n"
                rf"\node[anchor=west,font=\tiny] at ({width_emp:.2f},{y:.1f}) {{R\$ {item['empenhado']:,.0f}}};"
                + "\n"
            )

        return rf"""
\documentclass[12pt,a4paper]{{article}}
\usepackage[brazil]{{babel}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{geometry}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{longtable}}
\usepackage{{xcolor}}
\usepackage{{fancyhdr}}
\usepackage{{tikz}}
\usepackage{{graphicx}}
\usepackage{{colortbl}}

\geometry{{top=2.5cm,bottom=3cm,left=2cm,right=2cm,headheight=1.5cm}}
\definecolor{{govblue}}{{HTML}}{{1F4E79}}
\definecolor{{govgreen}}{{HTML}}{{1E7A1E}}
\definecolor{{lightgray}}{{HTML}}{{F0F0F0}}

\pagestyle{{fancy}}
\fancyhf{{}}
\lhead{{\small\color{{govblue}}\textbf{{{esc(self.ug_id.name)}}}}}
\rhead{{\small Exercicio {exercicio}}}
\cfoot{{\small\thepage}}
\renewcommand{{\headrulewidth}}{{0.4pt}}

\begin{{document}}

{bloco_cabecalho}

\begin{{center}}
  {{\Large\bfseries\color{{govblue}} RELATORIO DE EXECUCAO ORCAMENTARIA}} \\[0.2cm]
  {{\normalsize Exercicio {exercicio} - Periodo: {data_ini} a {data_fim}}} \\[0.1cm]
  {{\small Agrupado por: {agrupamento}}}
\end{{center}}

\textcolor{{govblue}}{{\rule{{\textwidth}}{{1.5pt}}}}
\vspace{{0.4cm}}

\begin{{center}}
\begin{{tabular}}{{|c|c|c|c|c|}}
\hline
\rowcolor{{govblue!20}}
\textbf{{Dotacao}} & \textbf{{Empenhado}} & \textbf{{Liquidado}} & \textbf{{Pago}} & \textbf{{\% Exec.}} \\
\hline
R\$ {total_dot:,.2f} & R\$ {total_emp:,.2f} & R\$ {total_liq:,.2f} & R\$ {total_pag:,.2f} & \textbf{{{pct_geral:.1f}\%}} \\
\hline
\end{{tabular}}
\end{{center}}

\vspace{{0.5cm}}

\begin{{center}}
\begin{{tikzpicture}}
  \tikzstyle{{every node}}=[font=\small]
  {tikz_bars}
  \draw[govblue,thick] (0,0) -- (8,0);
  \node[anchor=north,font=\footnotesize,color=govblue] at (4,-0.3) {{Valor Empenhado (Top 5)}};
  \draw[fill=govblue!70] (0,-0.9) rectangle (0.4,-0.6);
  \node[anchor=west,font=\tiny] at (0.5,-0.75) {{Empenhado}};
  \draw[fill=govgreen!70] (2,-0.9) rectangle (2.4,-0.6);
  \node[anchor=west,font=\tiny] at (2.5,-0.75) {{Pago}};
\end{{tikzpicture}}
\end{{center}}

\vspace{{0.4cm}}

\begin{{center}}
{{\small
\begin{{longtable}}{{|p{{3.5cm}}|r|r|r|r|r|r|r|}}
\hline
\rowcolor{{govblue!20}}
\textbf{{Grupo}} & \textbf{{Dotacao}} & \textbf{{Empenhado}} & \textbf{{\%E}} & \textbf{{Liquidado}} & \textbf{{\%L}} & \textbf{{Pago}} & \textbf{{\%P}} \\
\hline
\endhead
{rows}
\hline
\rowcolor{{lightgray}}
\textbf{{TOTAL}} &
\textbf{{R\$ {total_dot:,.2f}}} &
\textbf{{R\$ {total_emp:,.2f}}} &
\textbf{{{pct_geral:.1f}\%}} &
\textbf{{R\$ {total_liq:,.2f}}} &
- &
\textbf{{R\$ {total_pag:,.2f}}} &
- \\
\hline
\end{{longtable}}
}}
\end{{center}}

\vspace{{1cm}}
{bloco_rodape}
\begin{{center}}
  \small\color{{gray}}
  Gerado em \today\ pelo Sistema AGI Gov - Dados sujeitos a conferencia com documentos originais.
\end{{center}}

\end{{document}}
"""

    def action_gerar_pdf(self):
        self.ensure_one()

        try:
            from odoo.addons.gov_processos.models.gov_latex_service import GovLatexService
        except ImportError as exc:
            raise UserError(
                "GovLatexService nao disponivel. Verifique o modulo gov_processos."
            ) from exc

        linhas = self._consolidar()
        if not linhas:
            raise UserError("Nenhum dado encontrado para o periodo informado.")

        latex_source = self._build_latex(linhas)

        extra_images = {}
        if "gov.timbre" in self.env:
            timbre = self.env["gov.timbre"].get_default_for_company(self.ug_id.id)
            if timbre:
                extra_images = timbre.get_imagens_para_latex()

        pdf_bytes = GovLatexService.compile(
            latex_source,
            extra_images=extra_images,
            timeout=120,
        )
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        filename = (
            f"ExecucaoOrcamentaria_{self.ug_id.name}_{self.exercicio}_{fields.Date.today()}.pdf"
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
