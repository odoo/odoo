import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GovLiquidacao(models.Model):
    _name = "gov.liquidacao"
    _description = "Nota de Liquidacao (NL)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "data_liquidacao desc, name desc"

    name = fields.Char(
        string="Numero NL",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("atestado", "Atestado"),
            ("liquidado", "Liquidado"),
            ("cancelado", "Cancelado"),
        ],
        default="rascunho",
        string="Estado",
        tracking=True,
        required=True,
    )

    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    exercicio = fields.Integer(
        string="Exercicio",
        default=lambda self: fields.Date.today().year,
        required=True,
    )

    empenho_id = fields.Many2one(
        "gov.empenho",
        string="Nota de Empenho",
        required=True,
        domain="[('state','=','emitido'),('ug_id','=',ug_id)]",
        ondelete="restrict",
        tracking=True,
    )
    empenho_name = fields.Char(
        related="empenho_id.name",
        readonly=True,
        string="Numero da NE",
    )
    natureza_despesa = fields.Char(
        related="empenho_id.natureza_despesa",
        readonly=True,
    )
    processo_id_ref = fields.Integer(
        related="empenho_id.processo_id_ref",
        readonly=True,
        string="ID do Processo",
    )

    credor_id = fields.Many2one(
        related="empenho_id.credor_id",
        readonly=True,
        string="Credor",
    )

    valor_liquidado = fields.Monetary(
        string="Valor Liquidado",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    evento_ids = fields.One2many(
        "gov.nl.evento",
        "liquidacao_id",
        string="Eventos de Liquidacao",
    )
    valor_eventos = fields.Monetary(
        string="Soma Eventos",
        currency_field="currency_id",
        compute="_compute_valor_eventos",
        store=True,
    )
    eventos_conferidos = fields.Boolean(
        string="Eventos Conferidos",
        compute="_compute_valor_eventos",
        store=True,
        help="Verdadeiro quando a soma dos eventos confere com o valor liquidado.",
    )

    valor_empenho_liquido = fields.Monetary(
        related="empenho_id.valor_liquido",
        currency_field="currency_id",
        readonly=True,
        string="Valor Liquido da NE",
    )
    valor_ja_liquidado = fields.Monetary(
        string="Ja Liquidado nesta NE",
        currency_field="currency_id",
        compute="_compute_valor_ja_liquidado",
        store=True,
    )
    valor_disponivel = fields.Monetary(
        string="Saldo Disponivel para Liquidacao",
        currency_field="currency_id",
        compute="_compute_valor_ja_liquidado",
        store=True,
    )

    @api.depends(
        "empenho_id",
        "empenho_id.liquidacao_ids.valor_liquidado",
        "empenho_id.liquidacao_ids.state",
    )
    def _compute_valor_ja_liquidado(self):
        for rec in self:
            if not rec.empenho_id:
                rec.valor_ja_liquidado = 0.0
                rec.valor_disponivel = 0.0
                continue

            outras = rec.empenho_id.liquidacao_ids.filtered(
                lambda nl: nl.state in ("atestado", "liquidado") and nl.id != rec.id
            )
            ja_liquidado = sum(outras.mapped("valor_liquidado"))
            rec.valor_ja_liquidado = ja_liquidado
            rec.valor_disponivel = (rec.empenho_id.valor_liquido or 0.0) - ja_liquidado

    @api.depends("evento_ids.valor", "evento_ids.state", "valor_liquidado")
    def _compute_valor_eventos(self):
        for rec in self:
            ativos = rec.evento_ids.filtered(lambda e: e.state != "cancelado")
            soma = sum(ativos.mapped("valor"))
            rec.valor_eventos = soma
            rec.eventos_conferidos = (
                abs(soma - rec.valor_liquidado) < 0.01 if rec.valor_liquidado else False
            )

    nf_numero = fields.Char(string="Numero da NF/Fatura")
    nf_data = fields.Date(string="Data da NF/Fatura")
    nf_valor = fields.Monetary(
        string="Valor da NF/Fatura",
        currency_field="currency_id",
    )
    nf_chave_nfe = fields.Char(
        string="Chave NF-e (44 digitos)",
        size=44,
    )

    objeto_liquidacao = fields.Text(
        string="Objeto da Liquidacao",
        required=True,
        help=(
            "Descreva o que esta sendo liquidado: "
            "servico prestado, material entregue, etc."
        ),
    )
    data_liquidacao = fields.Date(
        string="Data da Liquidacao",
        default=fields.Date.today,
    )
    data_vencimento = fields.Date(string="Vencimento")

    atestante_id = fields.Many2one(
        "res.users",
        string="Atestante",
        help="Usuario responsavel pelo ateste de recebimento.",
        tracking=True,
    )
    data_ateste = fields.Date(string="Data do Ateste")
    observacao_ateste = fields.Text(string="Observacao do Ateste")

    move_nl_id = fields.Many2one(
        "account.move",
        string="Lancamento Contabil NL",
        readonly=True,
        copy=False,
    )

    pdf_nl_file = fields.Binary("PDF da NL", readonly=True)
    pdf_nl_filename = fields.Char(readonly=True)
    hash_sha256 = fields.Char(readonly=True)

    pagamento_count = fields.Integer(
        string="Pagamentos",
        compute="_compute_pagamento_count",
    )

    def _compute_pagamento_count(self):
        Pag = self.env.get("gov.pagamento")
        for rec in self:
            if Pag is not None:
                rec.pagamento_count = Pag.search_count([("liquidacao_id", "=", rec.id)])
            else:
                rec.pagamento_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = self.env["ir.sequence"].next_by_code("gov.liquidacao") or "Novo"
        return super().create(vals_list)

    @api.constrains("valor_liquidado", "empenho_id")
    def _check_valor_liquidado(self):
        for rec in self:
            if not rec.empenho_id:
                continue
            if (rec.valor_liquidado or 0.0) <= 0:
                raise ValidationError("O valor liquidado deve ser maior que zero.")

            outras = rec.empenho_id.liquidacao_ids.filtered(
                lambda nl: nl.state in ("atestado", "liquidado") and nl.id != rec.id
            )
            total = sum(outras.mapped("valor_liquidado"))
            saldo = (rec.empenho_id.valor_liquido or 0.0) - total
            if total + (rec.valor_liquidado or 0.0) > (rec.empenho_id.valor_liquido or 0.0):
                raise ValidationError(
                    "Valor liquidado excede o saldo disponivel da NE "
                    f"{rec.empenho_id.name}. Saldo: R$ {saldo:,.2f}. "
                    f"Tentando liquidar: R$ {rec.valor_liquidado:,.2f}"
                )

    def action_abrir_wizard_ateste(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas liquidacoes em rascunho podem ser atestadas.")

        wizard = self.env["gov.ateste.wizard"].create(
            {
                "liquidacao_id": self.id,
                "atestante_id": self.atestante_id.id if self.atestante_id else self.env.user.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": f"Ateste - {self.name}",
            "res_model": "gov.ateste.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_atestar(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas liquidacoes em rascunho podem ser atestadas.")
        if not self.atestante_id:
            raise UserError("Informe o atestante antes de atestar.")

        self.write(
            {
                "state": "atestado",
                "data_ateste": fields.Date.today(),
            }
        )
        self._notificar_empenho("atestado")
        self.message_post(
            body=Markup(f"Liquidacao <b>atestada</b> por {self.atestante_id.name}."),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_liquidar(self):
        self.ensure_one()
        if self.state != "atestado":
            raise UserError("Apenas liquidacoes atestadas podem ser liquidadas.")
        if self.evento_ids and not self.eventos_conferidos:
            raise UserError(
                "Os eventos da NL nao conferem com o valor liquidado.\n"
                f"Soma dos eventos: R$ {self.valor_eventos:,.2f}\n"
                f"Valor liquidado: R$ {self.valor_liquidado:,.2f}\n"
                "Ajuste os eventos antes de confirmar a liquidacao."
            )

        self.write(
            {
                "state": "liquidado",
                "data_liquidacao": fields.Date.today(),
            }
        )
        move = self._gerar_move_liquidacao()
        self._notificar_empenho("liquidado")
        self._notificar_processo()
        info_contabil = ""
        if move:
            info_contabil = f"<br/>Lancamento: <b>{move.name}</b> ({move.state})"
        self.message_post(
            body=Markup(
                f"Liquidacao confirmada: <b>{self.name}</b><br/>"
                f"Valor: R$ {self.valor_liquidado:,.2f}<br/>"
                f"NE: {self.empenho_id.name}"
                f"{info_contabil}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_cancelar(self):
        self.ensure_one()
        self._check_pode_cancelar_cascata()
        if self.state == "liquidado":
            raise UserError(
                "Liquidacoes confirmadas nao podem ser canceladas diretamente. "
                "Gere um estorno contabil primeiro."
            )
        self._gerar_move_estorno_liquidacao()
        self.write({"state": "cancelado"})
        self._notificar_empenho("cancelado")
        self.message_post(
            body=Markup(f"Liquidacao cancelada: <b>{self.name}</b>"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _check_pode_cancelar_cascata(self):
        """
        Bloqueia o cancelamento da NL quando ainda existem eventos vinculados.
        """
        self.ensure_one()
        eventos_vinculados = self.evento_ids.filtered(lambda e: e.state == "vinculado")
        if not eventos_vinculados:
            return True

        linhas = []
        for evento in eventos_vinculados:
            descricao = evento.tipo_id.descricao or evento.tipo_id.codigo or "sem tipo"
            if evento.pd_name:
                linhas.append(f" - {evento.pd_name} (evento: {descricao})")
            else:
                linhas.append(f" - Evento sem PD: {descricao}")

        detalhes = "\n".join(linhas)
        raise UserError(
            "Nao e possivel cancelar esta NL porque existem eventos vinculados:\n"
            f"{detalhes}\n\n"
            "Cancele as PDs relacionadas (ou libere os eventos) antes de cancelar a NL."
        )

    def _gerar_move_liquidacao(self):
        self.ensure_one()

        Config = self.env.get("gov.account.config")
        if Config is None:
            _logger.warning(
                "GRP Contabil NL: gov.account.config indisponivel. "
                "NL %s liquidada sem lancamento.",
                self.name,
            )
            return None

        contas = Config.get_accounts(self.natureza_despesa, self.ug_id.id)
        conta_debito = contas.get("empenho_pagar")
        conta_credito = contas.get("liquidacao_pagar")
        if not conta_debito or not conta_credito:
            _logger.warning(
                "GRP Contabil NL: contas nao mapeadas para natureza %s / UG %s. "
                "NL %s sem lancamento.",
                self.natureza_despesa,
                self.ug_id.name,
                self.name,
            )
            return None

        Journal = self.env["account.journal"]
        journal = Journal.search(
            [
                ("company_id", "=", self.ug_id.id),
                ("type", "in", ["general", "purchase"]),
            ],
            limit=1,
        ) or Journal.search([("type", "in", ["general", "purchase"])], limit=1)
        if not journal:
            _logger.warning(
                "GRP Contabil NL: sem journal. NL %s sem lancamento.",
                self.name,
            )
            return None

        move_vals = {
            "ref": f"NL {self.name} - {self.empenho_name}",
            "journal_id": journal.id,
            "date": self.data_liquidacao or fields.Date.today(),
            "company_id": self.ug_id.id,
            "move_type": "entry",
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": conta_debito.id,
                        "name": f"NL {self.name} - Baixa Empenho a Pagar",
                        "debit": self.valor_liquidado,
                        "credit": 0.0,
                        "partner_id": self.credor_id.id if self.credor_id else False,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": conta_credito.id,
                        "name": f"NL {self.name} - Fornecedor a Pagar",
                        "debit": 0.0,
                        "credit": self.valor_liquidado,
                        "partner_id": self.credor_id.id if self.credor_id else False,
                    },
                ),
            ],
        }

        try:
            move = self.env["account.move"].create(move_vals)
        except Exception as exc:
            _logger.warning(
                "GRP Contabil NL: falha ao criar account.move da NL %s: %s",
                self.name,
                exc,
            )
            return None

        try:
            move.action_post()
        except Exception as exc:
            _logger.warning(
                "GRP Contabil NL: nao foi possivel postar account.move da NL %s: %s",
                self.name,
                exc,
            )

        self.write({"move_nl_id": move.id})
        _logger.info("GRP Contabil NL: move %s criado para NL %s.", move.name, self.name)
        return move

    def _gerar_move_estorno_liquidacao(self):
        self.ensure_one()
        if not self.move_nl_id:
            return None
        try:
            reversal = self.move_nl_id._reverse_moves(
                default_values_list=[
                    {
                        "date": fields.Date.today(),
                        "ref": f"Estorno da NL {self.name}",
                    }
                ],
                cancel=False,
            )
            if reversal:
                reversal.action_post()
                return reversal[0] if len(reversal) == 1 else reversal
        except Exception as exc:
            _logger.warning(
                "GRP Contabil NL: falha ao estornar NL %s: %s",
                self.name,
                exc,
            )
        return None

    def _notificar_empenho(self, evento):
        if not self.empenho_id:
            return

        mensagens = {
            "atestado": (
                f"Liquidacao <b>{self.name}</b> atestada por "
                f"{self.atestante_id.name if self.atestante_id else '-'}."
            ),
            "liquidado": (
                f"Liquidacao <b>{self.name}</b> confirmada. "
                f"Valor: R$ {self.valor_liquidado:,.2f}."
            ),
            "cancelado": f"Liquidacao <b>{self.name}</b> cancelada.",
        }
        self.empenho_id.message_post(
            body=Markup(mensagens.get(evento, f"Liquidacao {self.name}: {evento}")),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _notificar_processo(self):
        if not self.empenho_id or not self.empenho_id.processo_id_ref:
            return

        Processo = self.env.get("gov.processo")
        if Processo is None:
            return
        processo = Processo.sudo().browse(self.empenho_id.processo_id_ref)
        if not processo.exists():
            return

        processo.message_post(
            body=Markup(
                f"Nota de Liquidacao emitida: <b>{self.name}</b><br/>"
                f"NE: {self.empenho_id.name}<br/>"
                f"Valor: R$ {self.valor_liquidado:,.2f}<br/>"
                f"Credor: {self.credor_id.name if self.credor_id else '-'}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_open_pagamentos(self):
        self.ensure_one()
        Pag = self.env.get("gov.pagamento")
        if Pag is None:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Modulo nao instalado",
                    "message": "gov_pagamento sera instalado no Bloco 14.",
                    "type": "info",
                },
            }
        return {
            "type": "ir.actions.act_window",
            "name": f"Pagamentos - {self.name}",
            "res_model": "gov.pagamento",
            "view_mode": "list,form",
            "domain": [("liquidacao_id", "=", self.id)],
            "context": {"default_liquidacao_id": self.id},
        }

    def _escape_latex(self, text):
        if not text:
            return ""
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
            text = text.replace(old, new)
        return text

    def _build_latex_nl(self):
        self.ensure_one()
        e = self._escape_latex

        Timbre = self.env.get("gov.timbre")
        timbre = Timbre.get_default_for_company(self.ug_id.id) if Timbre else None

        orgao = e(timbre.orgao_nome if timbre and timbre.orgao_nome else self.ug_id.name)
        secretaria = e(timbre.secretaria_nome if timbre and timbre.secretaria_nome else "")
        cnpj = e(timbre.cnpj if timbre and timbre.cnpj else (getattr(self.ug_id, "cnpj_ug", "") or ""))

        nl_num = e(self.name or "—")
        ne_num = e(self.empenho_name or "—")
        credor = e(self.credor_id.name if self.credor_id else "—")
        cnpj_cred = e((getattr(self.credor_id, "vat", "") if self.credor_id else "") or "—")
        valor_str = f"R\\$ {self.valor_liquidado:,.2f}"
        valor_ne = (
            f"R\\$ {self.empenho_id.valor_liquido:,.2f}" if self.empenho_id else "—"
        )
        objeto = e(self.objeto_liquidacao or "—")
        nat_desp = e(self.natureza_despesa or "—")
        data_liq = self.data_liquidacao.strftime("%d/%m/%Y") if self.data_liquidacao else "—"
        data_ateste = self.data_ateste.strftime("%d/%m/%Y") if self.data_ateste else "—"
        atestante = e(self.atestante_id.name if self.atestante_id else "—")
        nf_num = e(self.nf_numero or "—")
        nf_data = self.nf_data.strftime("%d/%m/%Y") if self.nf_data else "—"
        nf_val = f"R\\$ {self.nf_valor:,.2f}" if self.nf_valor else "—"
        exercicio = str(self.exercicio)
        obs = e(self.observacao_ateste or "")
        if timbre:
            bloco_cabecalho = timbre.get_latex_cabecalho()
            bloco_rodape = timbre.get_latex_rodape()
        else:
            linhas = [r"\begin{center}", rf"  {{\large\bfseries {orgao}}} \\[0.2cm]"]
            if secretaria:
                linhas.append(rf"  {{\normalsize {secretaria}}} \\[0.1cm]")
            if cnpj:
                linhas.append(rf"  {{\small CNPJ: {cnpj}}} \\[0.2cm]")
            linhas.extend([r"\end{center}", r"\vspace{0.3cm}"])
            bloco_cabecalho = "\n".join(linhas)
            bloco_rodape = (
                r"\begin{center}"
                + rf"{{\small\color{{gray}} {orgao}}}"
                + r"\end{center}"
            )

        latex = rf"""
\documentclass[12pt,a4paper]{{article}}
\usepackage[brazil]{{babel}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{geometry}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{fancyhdr}}
\usepackage{{xcolor}}
\usepackage{{graphicx}}

\geometry{{top=2.5cm,bottom=3cm,left=3cm,right=2cm}}
\definecolor{{govblue}}{{HTML}}{{1F4E79}}
\definecolor{{govblue2}}{{HTML}}{{2E75B6}}

\pagestyle{{fancy}}
\fancyhf{{}}
\lhead{{\small\color{{govblue}}\textbf{{{orgao}}}}}
\rhead{{\small Exercicio {exercicio}}}
\cfoot{{\small\thepage}}
\renewcommand{{\headrulewidth}}{{0.4pt}}

\begin{{document}}

\vspace*{{0.2cm}}
{bloco_cabecalho}

\begin{{center}}
  {{\LARGE\bfseries\color{{govblue}} NOTA DE LIQUIDAÇÃO}} \\[0.1cm]
  {{\large\bfseries N.º {nl_num}}} \\[0.2cm]
\end{{center}}

\vspace{{0.4cm}}
\section{{Identificacao}}

\begin{{center}}
\begin{{tabular}}{{p{{4cm}} p{{11cm}}}}
  \toprule
  \textbf{{Campo}} & \textbf{{Valor}} \\
  \midrule
  Numero da NL     & \textbf{{{nl_num}}} \\
  Nota de Empenho  & {ne_num} \\
  Exercicio        & {exercicio} \\
  UG               & {orgao} \\
  Natureza Despesa & {nat_desp} \\
  \bottomrule
\end{{tabular}}
\end{{center}}

\section{{Credor}}

\begin{{center}}
\begin{{tabular}}{{p{{4cm}} p{{11cm}}}}
  \toprule
  \textbf{{Campo}} & \textbf{{Valor}} \\
  \midrule
  Credor / Fornecedor & \textbf{{{credor}}} \\
  CNPJ / CPF          & {cnpj_cred} \\
  \bottomrule
\end{{tabular}}
\end{{center}}

\section{{Valores}}

\begin{{center}}
\begin{{tabular}}{{p{{4cm}} p{{11cm}}}}
  \toprule
  \textbf{{Campo}} & \textbf{{Valor}} \\
  \midrule
  Valor da NE (liquido)  & {valor_ne} \\
  \textbf{{Valor Liquidado}} & \textbf{{{valor_str}}} \\
  \midrule
  NF / Fatura n.o        & {nf_num} \\
  Data da NF             & {nf_data} \\
  Valor da NF            & {nf_val} \\
  \bottomrule
\end{{tabular}}
\end{{center}}

\section{{Objeto da Liquidacao}}

\begin{{quote}}
  {objeto}
\end{{quote}}
"""

        if obs:
            latex += rf"""
\section{{Observacao do Ateste}}

\begin{{quote}}
  {obs}
\end{{quote}}
"""

        latex += rf"""
\section{{Ateste de Recebimento}}

\begin{{center}}
\begin{{tabular}}{{p{{4cm}} p{{11cm}}}}
  \toprule
  \textbf{{Campo}} & \textbf{{Valor}} \\
  \midrule
  Data da Liquidacao & {data_liq} \\
  Data do Ateste     & {data_ateste} \\
  Atestante          & {atestante} \\
  \bottomrule
\end{{tabular}}
\end{{center}}

\vspace{{2cm}}
\begin{{center}}
  \rule{{8cm}}{{0.4pt}} \\[0.3cm]
  \textbf{{{atestante}}} \\
  Fiscal / Gestor do Contrato \\
  {orgao} \\[0.3cm]
  \small Data: \underline{{\hspace{{4cm}}}}
\end{{center}}

\vspace{{1cm}}
{bloco_rodape}
\vspace{{0.2cm}}
\begin{{center}}
  \small\color{{gray}}
  Documento gerado automaticamente pelo Sistema AGI Gov \\
  {orgao} --- Exercicio {exercicio} --- {data_liq}
\end{{center}}

\end{{document}}
"""
        return latex

    def action_gerar_nl_pdf(self):
        self.ensure_one()
        if self.state not in ("atestado", "liquidado"):
            raise UserError(
                "O PDF da NL so pode ser gerado apos o ateste. "
                "Ateste a liquidacao antes de gerar o documento."
            )

        try:
            from odoo.addons.gov_processos.models.gov_latex_service import GovLatexService
        except ImportError as exc:
            raise UserError(
                "Servico LaTeX nao disponivel. "
                "Verifique se o modulo gov_processos esta instalado."
            ) from exc

        import base64
        import hashlib

        latex_source = self._build_latex_nl()

        Timbre = self.env.get("gov.timbre")
        timbre = Timbre.get_default_for_company(self.ug_id.id) if Timbre else None
        fallback_logo_binary = base64.b64decode(self.ug_id.logo) if self.ug_id.logo else None

        pdf_bytes = GovLatexService.compile_with_timbre(
            latex_source,
            timbre=timbre,
            fallback_logo_binary=fallback_logo_binary,
            timeout=120,
        )
        b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        filename = f"NL_{self.name}_{self.ug_id.name}.pdf".replace(" ", "_").replace("/", "-")

        self.write(
            {
                "pdf_nl_file": b64_pdf,
                "pdf_nl_filename": filename,
                "hash_sha256": sha256,
            }
        )

        self.message_post(
            body=Markup(
                f"<b>PDF da NL gerado:</b> {filename}<br/>"
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
                "message": f"{filename} - {len(pdf_bytes):,} bytes",
                "type": "success",
            },
        }
