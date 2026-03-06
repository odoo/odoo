from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GovNlEvento(models.Model):
    _name = "gov.nl.evento"
    _description = "Evento de Liquidacao (Destino do Saldo)"
    _order = "liquidacao_id, tipo_id"

    liquidacao_id = fields.Many2one(
        "gov.liquidacao",
        string="Nota de Liquidacao",
        required=True,
        ondelete="cascade",
        index=True,
    )
    nl_state = fields.Selection(
        related="liquidacao_id.state",
        string="Estado da Liquidacao",
        readonly=True,
    )

    tipo_id = fields.Many2one(
        "gov.nl.evento.tipo",
        string="Tipo de Evento",
        required=True,
        ondelete="restrict",
    )
    tipo_pagamento = fields.Selection(
        related="tipo_id.tipo_pagamento",
        readonly=True,
        string="Tipo de Pagamento",
    )
    norma = fields.Char(
        related="tipo_id.norma",
        readonly=True,
    )

    account_id = fields.Many2one(
        "account.account",
        string="Conta Contabil",
        help=(
            "Preenchida automaticamente pelo tipo. "
            "Pode ser ajustada manualmente."
        ),
    )

    destinatario_id = fields.Many2one(
        "res.partner",
        string="Destinatario",
        help="Fornecedor, RFB, Prefeitura, Juizo...",
    )

    valor = fields.Monetary(
        string="Valor",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="liquidacao_id.currency_id",
        readonly=True,
        store=True,
    )

    state = fields.Selection(
        [
            ("disponivel", "Disponivel"),
            ("vinculado", "Vinculado a PD"),
            ("cancelado", "Cancelado"),
        ],
        default="disponivel",
        string="Estado",
        required=True,
    )

    pd_name = fields.Char(
        string="N PD",
        readonly=True,
        copy=False,
    )

    observacao = fields.Text(string="Observacao")

    @api.onchange("tipo_id")
    def _onchange_tipo(self):
        if self.tipo_id:
            self.account_id = self.tipo_id.account_id

    @api.constrains("valor")
    def _check_valor(self):
        for rec in self:
            if rec.valor <= 0:
                raise ValidationError("O valor do evento deve ser maior que zero.")

    def vincular_pd(self, pd):
        """
        Vincula este evento a uma PD e o remove da disponibilidade.
        """
        self.ensure_one()
        if not pd:
            raise UserError("PD invalida para vinculo do evento.")
        if self.state != "disponivel":
            raise UserError(
                f"O evento {self.tipo_id.descricao} nao esta disponivel "
                f"(estado atual: {self.state})."
            )
        self.write(
            {
                "state": "vinculado",
                "pd_name": getattr(pd, "name", False) or str(getattr(pd, "id", "")),
            }
        )

    def liberar_pd(self):
        """
        Libera o evento de volta para disponivel.
        Chamado no cancelamento da PD.
        """
        self.ensure_one()
        if self.state != "vinculado" and not self.pd_name:
            return
        self.write(
            {
                "state": "disponivel",
                "pd_name": False,
            }
        )

    def cancelar(self):
        """
        Cancela o evento, bloqueando cancelamento direto quando vinculado.
        """
        self.ensure_one()
        if self.state == "vinculado":
            raise UserError(
                f"Evento {self.tipo_id.descricao} esta vinculado "
                f"a PD {self.pd_name}. Cancele a PD antes de cancelar o evento."
            )
        self.write({"state": "cancelado"})
