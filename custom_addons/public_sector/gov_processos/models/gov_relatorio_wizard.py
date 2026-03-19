import base64
import hashlib
import re
import unicodedata

from odoo import fields, models
from odoo.exceptions import UserError


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

    def _escape_latex(self, text):
        if not text:
            return ""
        escaped = (
            unicodedata.normalize("NFKD", str(text))
            .encode("ascii", "ignore")
            .decode("ascii")
        )
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
            escaped = escaped.replace(old, new)
        return escaped

    def _build_latex(self, data):
        self.ensure_one()
        e = self._escape_latex

        kpis = data.get("kpis", {})
        alertas = data.get("alertas", {})
        financeiro = data.get("financeiro", {})
        docs = data.get("docs", {})
        criticos = data.get("lista_criticos", [])
        mapa_inercia = data.get("mapa_inercia", [])

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (Timbre.get_default_for_company(self.ug_id.id) if Timbre else None)
        orgao_nome = e(timbre.orgao_nome if timbre and timbre.orgao_nome else self.ug_id.name)
        secretaria_nome = e(timbre.secretaria_nome if timbre else "")
        cnpj = e(
            timbre.cnpj
            if timbre and timbre.cnpj
            else (getattr(self.ug_id, "cnpj_ug", "") or "")
        )
        cor1 = (getattr(timbre, "rodape_cor_barra_superior", "") if timbre else "") or "1F4E79"
        cor2 = (getattr(timbre, "rodape_cor_barra_inferior", "") if timbre else "") or "2E75B6"
        esp1 = (getattr(timbre, "rodape_espessura_superior", 0.0) if timbre else 0.0) or 6.0
        esp2 = (getattr(timbre, "rodape_espessura_inferior", 0.0) if timbre else 0.0) or 2.0
        largura_logo = (getattr(timbre, "logo_width_mm", 0.0) if timbre else 0.0) or 30.0
        data_ref = self.data_referencia.strftime("%d/%m/%Y")
        titulo = e(self.titulo)

        total_ativos = kpis.get("total_ativos", 0) or 0

        lines = [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage{geometry}",
            r"\usepackage{booktabs}",
            r"\usepackage{array}",
            r"\usepackage{fancyhdr}",
            r"\usepackage{xcolor}",
            r"\usepackage{graphicx}",
            r"\geometry{top=2.5cm,bottom=3cm,left=3cm,right=2cm}",
            f"\\definecolor{{govblue}}{{HTML}}{{{cor1}}}",
            f"\\definecolor{{govblue2}}{{HTML}}{{{cor2}}}",
            r"\definecolor{alertred}{HTML}{C0392B}",
            r"\definecolor{alertyellow}{HTML}{F39C12}",
            r"\definecolor{okgreen}{HTML}{27AE60}",
            r"\pagestyle{fancy}",
            r"\fancyhf{}",
            f"\\lhead{{\\small\\color{{govblue}}\\textbf{{{orgao_nome}}}}}",
            f"\\rhead{{\\small Exercicio {self.exercicio}}}",
            r"\cfoot{\small \thepage}",
            r"\renewcommand{\headrulewidth}{0.4pt}",
            r"\begin{document}",
            r"\begin{center}",
            rf"  \IfFileExists{{logo.png}}{{\includegraphics[width={largura_logo}mm]{{logo.png}}}}{{}}",
            f"  {{\\large\\bfseries {orgao_nome}}}",
            r"  \par\vspace{0.2cm}",
            f"  {{\\normalsize {secretaria_nome}}}",
            r"  \par\vspace{0.1cm}",
            f"  {{\\small CNPJ: {cnpj}}}",
            r"  \par\vspace{0.4cm}",
            f"  \\textcolor{{govblue}}{{\\rule{{\\textwidth}}{{{esp1}pt}}}}",
            r"  \par\vspace{0.3cm}",
            f"  {{\\LARGE\\bfseries\\color{{govblue}} {titulo}}}",
            r"  \par\vspace{0.2cm}",
            f"  {{\\large Exercicio {self.exercicio} --- Referencia: {data_ref}}}",
            r"  \par\vspace{0.2cm}",
            f"  \\textcolor{{govblue2}}{{\\rule{{\\textwidth}}{{{esp2}pt}}}}",
            r"\end{center}",
            r"\vspace{0.5cm}",
        ]

        if self.incluir_kpis:
            def pct(value):
                return round((value / total_ativos) * 100) if total_ativos else 0

            lines.extend(
                [
                    r"\section{Processos por Fase}",
                    r"\begin{center}",
                    r"\begin{tabular}{l r r}",
                    r"  \toprule",
                    r"  \textbf{Fase} & \textbf{Processos} & \textbf{\%} \\",
                    r"  \midrule",
                    f"  Demanda & {kpis.get('em_demanda', 0)} & {pct(kpis.get('em_demanda', 0))}\\% \\\\",
                    f"  Instrucao & {kpis.get('em_instrucao', 0)} & {pct(kpis.get('em_instrucao', 0))}\\% \\\\",
                    f"  Planejamento & {kpis.get('em_planejamento', 0)} & {pct(kpis.get('em_planejamento', 0))}\\% \\\\",
                    f"  Licitacao & {kpis.get('em_licitacao', 0)} & {pct(kpis.get('em_licitacao', 0))}\\% \\\\",
                    f"  Contratacao & {kpis.get('em_contratacao', 0)} & {pct(kpis.get('em_contratacao', 0))}\\% \\\\",
                    f"  Execucao & {kpis.get('em_execucao', 0)} & {pct(kpis.get('em_execucao', 0))}\\% \\\\",
                    r"  \midrule",
                    f"  \\textbf{{Total Ativos}} & \\textbf{{{total_ativos}}} & \\textbf{{100\\%}} \\\\",
                    f"  Encerrados no Mes & {kpis.get('encerrados_mes', 0)} & --- \\\\",
                    r"  \bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                ]
            )

        if self.incluir_alertas:
            prazos_vencidos = alertas.get("prazos_vencidos", 0) or 0
            prazos_proximos = alertas.get("prazos_proximos", 0) or 0
            processos_inertes = alertas.get("processos_inertes", 0) or 0
            urgentes_ativos = alertas.get("urgentes_ativos", 0) or 0
            retroativos_ativos = alertas.get("retroativos_ativos", 0) or 0
            cor_venc = "alertred" if prazos_vencidos > 0 else "okgreen"
            cor_prox = "alertyellow" if prazos_proximos > 0 else "okgreen"
            cor_iner = "alertyellow" if processos_inertes > 0 else "okgreen"
            cor_urg = "alertred" if urgentes_ativos > 0 else "okgreen"
            lines.extend(
                [
                    r"\section{Alertas e Situacoes Criticas}",
                    r"\begin{center}",
                    r"\begin{tabular}{l r}",
                    r"  \toprule",
                    r"  \textbf{Indicador} & \textbf{Qtd.} \\",
                    r"  \midrule",
                    f"  \\textcolor{{{cor_venc}}}{{Prazos Vencidos}} & \\textcolor{{{cor_venc}}}{{\\textbf{{{prazos_vencidos}}}}} \\\\",
                    f"  \\textcolor{{{cor_prox}}}{{Vencendo em 7 dias}} & \\textcolor{{{cor_prox}}}{{\\textbf{{{prazos_proximos}}}}} \\\\",
                    f"  \\textcolor{{{cor_iner}}}{{Processos Parados (+21d)}} & \\textcolor{{{cor_iner}}}{{\\textbf{{{processos_inertes}}}}} \\\\",
                    f"  \\textcolor{{{cor_urg}}}{{Urgentes Ativos}} & \\textcolor{{{cor_urg}}}{{\\textbf{{{urgentes_ativos}}}}} \\\\",
                    f"  Retroativos Ativos & {retroativos_ativos} \\\\",
                    r"  \bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                ]
            )

        if self.incluir_financeiro:
            valor_total = financeiro.get("valor_total", 0.0) or 0.0
            lines.extend(
                [
                    r"\section{Resumo Financeiro e Documental}",
                    r"\begin{center}",
                    r"\begin{tabular}{l r}",
                    r"  \toprule",
                    r"  \textbf{Item} & \textbf{Valor / Qtd.} \\",
                    r"  \midrule",
                    f"  Valor Total Estimado em Andamento & R\\$ {valor_total:,.2f} \\\\",
                    f"  Documentos em Revisao & {docs.get('em_revisao', 0)} \\\\",
                ]
            )
            if self.incluir_docs_ia:
                lines.append(
                    f"  Documentos IA Pendentes de Aprovacao & {docs.get('ia_pendentes', 0)} \\\\"
                )
            lines.extend(
                [
                    r"  \bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                ]
            )

        if self.incluir_criticos and criticos:
            lines.extend(
                [
                    r"\section{Processos Criticos}",
                    r"\begin{center}",
                    r"\begin{tabular}{p{2cm} p{4.5cm} p{2cm} p{3cm} p{2cm} p{1.5cm}}",
                    r"  \toprule",
                    r"  \textbf{Processo} & \textbf{Objeto} & \textbf{Fase} & \textbf{Responsavel} & \textbf{Prazo} & \textbf{Alerta} \\",
                    r"  \midrule",
                ]
            )
            for item in criticos[: self.max_criticos]:
                alerta = "---"
                if item.get("prazo_vencido"):
                    alerta = r"\textcolor{alertred}{\textbf{VENCIDO}}"
                elif item.get("urgencia"):
                    alerta = r"\textcolor{alertyellow}{\textbf{URG}}"
                nome = e(item.get("name", ""))
                assunto = e((item.get("subject", "") or "")[:50])
                fase = e(item.get("state", ""))
                responsavel = e(item.get("responsible", "—"))
                prazo = e(item.get("prazo_resposta", "—"))
                lines.append(
                    f"  {nome} & {assunto} & {fase} & {responsavel} & {prazo} & {alerta} \\\\"
                )
            lines.extend(
                [
                    r"  \bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                ]
            )

        if self.incluir_inercia and mapa_inercia:
            lines.extend(
                [
                    r"\section{Mapa de Inercia por UG (Top 5)}",
                    r"\begin{center}",
                    r"\begin{tabular}{l r r r}",
                    r"  \toprule",
                    r"  \textbf{UG} & \textbf{Ativos} & \textbf{Parados} & \textbf{\%} \\",
                    r"  \midrule",
                ]
            )
            for item in mapa_inercia:
                pct = item.get("pct", 0) or 0
                cor = "alertred" if pct > 50 else "alertyellow"
                ug_nome = e(item.get("ug", ""))
                total = item.get("total", 0) or 0
                inertes = item.get("inertes", 0) or 0
                lines.append(
                    f"  {ug_nome} & {total} & \\textcolor{{{cor}}}{{\\textbf{{{inertes}}}}} & \\textcolor{{{cor}}}{{{pct}\\%}} \\\\"
                )
            lines.extend(
                [
                    r"  \bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                ]
            )

        if self.incluir_assinatura:
            nome_ass = e(self.assinante_nome or "")
            cargo_ass = e(self.assinante_cargo or "")
            assinatura_lines = [
                r"\vspace{2cm}",
                r"\begin{center}",
                r"  \rule{8cm}{0.4pt} \\[0.3cm]",
                f"  \\textbf{{{nome_ass}}} \\\\",
            ]
            if cargo_ass:
                assinatura_lines.append(f"  {cargo_ass} \\\\")
            assinatura_lines.extend(
                [
                    f"  {orgao_nome} \\\\[0.3cm]",
                    r"  \small Data: \underline{\hspace{4cm}}",
                    r"\end{center}",
                ]
            )
            lines.extend(assinatura_lines)

        lines.extend(
            [
                r"\vspace{1cm}",
                r"\begin{center}",
                r"\small\color{gray}",
                r"Relatorio gerado automaticamente pelo Sistema AGI Gov \\",
                f"{orgao_nome} --- Exercicio {self.exercicio} --- {data_ref}",
                r"\end{center}",
                r"\end{document}",
            ]
        )
        return "\n".join(lines)

    def action_gerar_relatorio(self):
        self.ensure_one()

        dashboard_data = self.env["gov.dashboard"].get_dashboard_data(ug_id=self.ug_id.id)
        latex_source = self._build_latex(dashboard_data)
        if not latex_source:
            raise UserError("Nao foi possivel gerar o conteudo LaTeX do relatorio.")

        from .gov_latex_service import GovLatexService

        Timbre = self.env.get("gov.timbre")
        timbre = self.timbre_id or (Timbre.get_default_for_company(self.ug_id.id) if Timbre else None)
        fallback_logo_binary = base64.b64decode(self.ug_id.logo) if self.ug_id.logo else None

        pdf_bytes = GovLatexService.compile_with_timbre(
            latex_source,
            timbre=timbre,
            fallback_logo_binary=fallback_logo_binary,
            timeout=120,
        )
        b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        ug_nome = re.sub(r"[^a-zA-Z0-9_-]+", "_", self.ug_id.name or "ug")
        filename = f"relatorio_executivo_{ug_nome}_{self.exercicio}_{self.data_referencia}.pdf"

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
