import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


TIPO_PEND_SEL = [
    ("pagamento_confirmado", "Pagamento Confirmado (match pendente)"),
    ("pagamento_rejeitado", "Pagamento Rejeitado pelo Banco"),
    ("pagamento_devolvido", "Pagamento Devolvido"),
    ("divergencia_valor", "Divergencia de Valor"),
    ("debito_nao_identificado", "Debito Nao Identificado"),
    ("credito_nao_identificado", "Credito Nao Identificado"),
    ("tarifa_bancaria", "Tarifa / Taxa Bancaria"),
    ("outros", "Outros"),
]


class GovConciliacaoPendencia(models.Model):
    _name = "gov.conciliacao.pendencia"
    _description = "Pendencia de Conciliacao Bancaria"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "data_ocorrencia desc, id desc"

    name = fields.Char(
        string="Referencia",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("aberta", "Aberta"),
            ("justificada", "Justificada"),
            ("baixada", "Baixada"),
            ("ignorada", "Ignorada"),
        ],
        default="aberta",
        required=True,
        tracking=True,
        string="Estado",
    )
    tipo = fields.Selection(TIPO_PEND_SEL, string="Tipo", required=True)

    importacao_id = fields.Many2one(
        "gov.conciliacao.importacao",
        string="Importacao",
        ondelete="cascade",
        index=True,
    )
    ug_id = fields.Many2one("res.company", string="UG", required=True)
    conta_bancaria_id = fields.Many2one("account.account", string="Conta Bancaria")
    banco = fields.Char(string="Banco")
    segmento = fields.Char(string="Segmento")
    ocorrencia_banco = fields.Char(
        string="Ocorrencia Banco",
        help="Codigo de ocorrencia retornado pelo banco.",
    )

    numero_doc = fields.Char(string="Numero Documento")
    data_ocorrencia = fields.Date(string="Data Ocorrencia", required=True)
    historico = fields.Text(string="Historico / Memo")
    valor_banco = fields.Monetary(string="Valor Banco", currency_field="currency_id")
    valor_sistema = fields.Monetary(string="Valor Sistema", currency_field="currency_id")
    diferenca = fields.Monetary(string="Diferenca", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    op_id = fields.Many2one("gov.pagamento", string="OP Vinculada", readonly=True)
    op_extra_id = fields.Many2one("gov.pagamento", string="OP Extra de Regularizacao", readonly=True)
    move_id = fields.Many2one("account.move", string="Lancamento Contabil", readonly=True)

    justificativa = fields.Text(string="Justificativa")
    justificado_por = fields.Many2one("res.users", string="Justificado por", readonly=True)
    data_justificativa = fields.Date(string="Data Justificativa", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("gov.conciliacao.pendencia") or "Novo"
                )
        return super().create(vals_list)
