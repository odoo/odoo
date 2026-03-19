from odoo import fields, models


TIPO_PAGAMENTO_SEL = [
    ("transferencia", "Transferencia Bancaria"),
    ("darf", "DARF"),
    ("guia_iss", "Guia ISS"),
    ("gps", "GPS / INSS"),
    ("judicial", "Bloqueio Judicial / Precatorio"),
    ("ajuste", "Ajuste / Taxa Bancaria"),
    ("outros", "Outros"),
]


class GovNlEventoTipo(models.Model):
    _name = "gov.nl.evento.tipo"
    _description = "Tipo de Evento de Liquidacao"
    _order = "codigo"

    codigo = fields.Char(
        string="Codigo",
        required=True,
        help="Identificador unico. Ex: pagamento_fornecedor",
    )
    descricao = fields.Char(
        string="Descricao",
        required=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Conta Contabil Padrao",
        help=(
            "Conta MCASP padrao para este evento. "
            "Pode ser sobreposta no evento individual."
        ),
    )
    tipo_pagamento = fields.Selection(
        TIPO_PAGAMENTO_SEL,
        string="Tipo de Pagamento Padrao",
        required=True,
    )
    norma = fields.Char(
        string="Referencia Normativa",
        help="Ex: IN RFB 1.234/2012, Lei 9.430/1996",
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Observacoes / Instrucao de Uso")

    _unique_codigo = models.Constraint(
        "UNIQUE(codigo)",
        "Ja existe um tipo de evento com este codigo.",
    )
