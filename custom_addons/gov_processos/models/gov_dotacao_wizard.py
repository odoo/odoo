from markupsafe import Markup

from odoo import api, fields, models


class GovDotacaoWizard(models.TransientModel):
    _name = "gov.dotacao.wizard"
    _description = "Wizard de Indicação de Dotação Orçamentária"

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        readonly=True,
    )
    programa = fields.Char(string="Programa", required=True)
    acao = fields.Char(string="Ação")
    natureza_despesa = fields.Char(string="Natureza da Despesa")
    fonte_recurso = fields.Char(string="Fonte de Recurso")
    exercicio = fields.Integer(
        string="Exercício",
        default=lambda self: fields.Date.today().year,
        required=True,
    )
    valor_estimado = fields.Monetary(
        string="Valor Estimado",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    observacao = fields.Text(string="Observação")

    saldo_disponivel = fields.Monetary(
        string="Saldo Disponível",
        currency_field="currency_id",
        compute="_compute_saldo",
        store=False,
    )
    alerta_saldo = fields.Boolean(
        compute="_compute_saldo",
        store=False,
    )

    @api.depends(
        "programa",
        "acao",
        "natureza_despesa",
        "fonte_recurso",
        "exercicio",
        "valor_estimado",
    )
    def _compute_saldo(self):
        try:
            BudgetLine = self.env["gov.budget.line"]
        except KeyError:
            BudgetLine = None

        for rec in self:
            saldo = 0.0
            if BudgetLine is not None:
                try:
                    domain = [("exercicio", "=", rec.exercicio)]
                    if rec.programa:
                        domain.append(("programa", "=", rec.programa))
                    if rec.fonte_recurso:
                        domain.append(("fonte_recurso", "=", rec.fonte_recurso))
                    linha = BudgetLine.sudo().search(domain, limit=1)
                    if linha:
                        saldo = linha.saldo_disponivel
                except Exception:
                    saldo = 0.0
            rec.saldo_disponivel = saldo
            rec.alerta_saldo = bool(saldo > 0 and rec.valor_estimado > saldo)

    def action_confirmar(self):
        self.ensure_one()
        self.env["gov.processo.dotacao"].create(
            {
                "processo_id": self.processo_id.id,
                "programa": self.programa,
                "acao": self.acao,
                "natureza_despesa": self.natureza_despesa,
                "fonte_recurso": self.fonte_recurso,
                "exercicio": self.exercicio,
                "valor_estimado": self.valor_estimado,
                "observacao": self.observacao,
            }
        )

        processo = self.processo_id
        if processo.state in ("demanda", "instrucao"):
            processo.write({"state": "planejamento"})

        alerta = (
            "<br/>⚠️ <b>Atenção:</b> saldo disponível insuficiente. "
            "Verifique com o setor orçamentário."
            if self.alerta_saldo
            else ""
        )
        processo.message_post(
            body=Markup(
                f"<b>Dotação indicada</b><br/>"
                f"Programa: {self.programa} / Ação: {self.acao or '—'}<br/>"
                f"Natureza: {self.natureza_despesa or '—'} | "
                f"Fonte: {self.fonte_recurso or '—'}<br/>"
                f"Exercício: {self.exercicio} | "
                f"Valor estimado: R$ {self.valor_estimado:,.2f}"
                f"{alerta}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        processo.invalidate_recordset(["message_ids"])

        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.processo",
            "res_id": processo.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_confirmar_e_fechar(self):
        self.action_confirmar()
        return {"type": "ir.actions.act_window_close"}
