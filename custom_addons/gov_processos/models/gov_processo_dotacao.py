from odoo import api, fields, models


class GovProcessoDotacao(models.Model):
    _name = "gov.processo.dotacao"
    _description = "Indicação Orçamentária do Processo"
    _order = "exercicio desc, id desc"

    processo_id = fields.Many2one(
        "gov.processo",
        required=True,
        ondelete="cascade",
        index=True,
    )

    programa = fields.Char(string="Programa", required=True)
    acao = fields.Char(string="Ação")
    natureza_despesa = fields.Char(
        string="Natureza da Despesa",
        help="Ex: 3.3.90.39 — Outros Serviços de Terceiros PJ",
    )
    fonte_recurso = fields.Char(
        string="Fonte de Recurso",
        help="Ex: 100 — Recursos Ordinários",
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
    exercicio = fields.Integer(
        string="Exercício",
        default=lambda self: fields.Date.today().year,
        required=True,
    )

    reservado = fields.Boolean(
        string="Saldo Reservado",
        default=False,
        readonly=True,
        help="Marcado automaticamente quando o empenho é emitido.",
    )
    empenho_id = fields.Integer(
        string="ID do Empenho (NE)",
        help="Preenchido pelo gov_empenho na Onda 1.",
        readonly=True,
    )

    saldo_disponivel = fields.Monetary(
        string="Saldo Disponível",
        currency_field="currency_id",
        compute="_compute_saldo_disponivel",
        store=False,
    )
    alerta_saldo = fields.Boolean(
        string="Saldo Insuficiente",
        compute="_compute_saldo_disponivel",
        store=False,
    )
    observacao = fields.Text(string="Observação")

    @api.depends(
        "programa",
        "acao",
        "natureza_despesa",
        "fonte_recurso",
        "exercicio",
        "valor_estimado",
    )
    def _compute_saldo_disponivel(self):
        """
        Tenta buscar saldo em gov.budget.line (addon gov_budget).
        Se o modelo não existir, retorna 0 sem erro.
        """
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
