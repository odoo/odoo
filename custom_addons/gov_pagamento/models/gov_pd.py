import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


TIPO_PAGAMENTO_SEL = [
    ("transferencia", "Transferencia Bancaria"),
    ("darf", "DARF"),
    ("guia_iss", "Guia ISS"),
    ("gps", "GPS / INSS"),
    ("judicial", "Bloqueio Judicial / Precatorio"),
    ("ajuste", "Ajuste / Taxa Bancaria"),
    ("outros", "Outros"),
]


class GovPd(models.Model):
    _name = "gov.pd"
    _description = "Programacao de Desembolso"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        string="Numero PD",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("confirmado", "Confirmado"),
            ("pago", "Pago"),
            ("cancelado", "Cancelado"),
        ],
        default="rascunho",
        required=True,
        tracking=True,
        string="Estado",
    )

    ug_id = fields.Many2one(
        "res.company",
        string="UG",
        required=True,
        default=lambda self: self.env.company,
    )
    exercicio = fields.Integer(
        string="Exercicio",
        default=lambda self: fields.Date.today().year,
        required=True,
    )

    liquidacao_id = fields.Many2one(
        "gov.liquidacao",
        string="Nota de Liquidacao",
        domain="[('state','in',['atestado','liquidado']),('ug_id','=',ug_id)]",
        ondelete="restrict",
        tracking=True,
        help="Vazio apenas para ajustes bancarios/contabeis (restrito a admin).",
    )
    nl_name = fields.Char(
        related="liquidacao_id.name",
        readonly=True,
        string="Numero NL",
    )
    nl_valor = fields.Monetary(
        related="liquidacao_id.valor_liquidado",
        currency_field="currency_id",
        readonly=True,
        string="Valor NL",
    )

    evento_id = fields.Many2one(
        "gov.nl.evento",
        string="Evento da NL",
        domain="[('liquidacao_id','=',liquidacao_id),('state','=','disponivel')]",
        ondelete="restrict",
        tracking=True,
        help="Evento que esta PD consome.",
    )
    evento_tipo_codigo = fields.Char(
        related="evento_id.tipo_id.codigo",
        readonly=True,
        string="Tipo de Evento",
    )

    tipo_pagamento = fields.Selection(
        TIPO_PAGAMENTO_SEL,
        string="Tipo de Pagamento",
        required=True,
        tracking=True,
    )
    destinatario_id = fields.Many2one(
        "res.partner",
        string="Destinatario",
        tracking=True,
    )

    banco_codigo = fields.Char(string="Banco")
    agencia = fields.Char(string="Agencia")
    conta_corrente = fields.Char(string="Conta Corrente")
    pix_chave = fields.Char(string="Chave PIX")
    darf_codigo = fields.Char(
        string="Codigo DARF/Receita",
        help="Ex: 5952 (CSLL/PIS/COFINS), 1708 (IRRF servicos)",
    )
    competencia = fields.Char(
        string="Competencia",
        help="Mes/ano de referencia. Ex: 02/2026",
    )

    valor = fields.Monetary(
        string="Valor",
        required=True,
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    saldo_disponivel_nl = fields.Monetary(
        string="Saldo Disponivel na NL",
        currency_field="currency_id",
        compute="_compute_saldo_disponivel",
    )

    op_id = fields.Many2one(
        "gov.pagamento",
        string="Ordem de Pagamento",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    op_name = fields.Char(
        related="op_id.name",
        readonly=True,
        string="N OP",
    )

    observacao = fields.Text(string="Observacao")
    is_ajuste = fields.Boolean(
        string="Ajuste sem processo",
        help="PD de ajuste bancario/contabil sem NL vinculada.",
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._precheck_create_vals(vals)
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = self.env["ir.sequence"].next_by_code("gov.pd") or "Novo"
        return super().create(vals_list)

    def _precheck_create_vals(self, vals):
        valor = vals.get("valor", 0.0) or 0.0
        if valor <= 0:
            raise ValidationError("O valor da PD deve ser maior que zero.")

        liquidacao_id = vals.get("liquidacao_id")
        is_ajuste = bool(vals.get("is_ajuste"))
        evento_id = vals.get("evento_id")

        if not liquidacao_id and not is_ajuste:
            raise ValidationError(
                "Informe a Nota de Liquidacao ou marque como Ajuste sem processo."
            )
        if not liquidacao_id and is_ajuste:
            if not self.env.user.has_group("gov_base.group_gov_admin"):
                raise ValidationError(
                    "Apenas administradores podem criar PDs de ajuste sem NL."
                )
        if liquidacao_id and not is_ajuste and not evento_id:
            raise ValidationError("Selecione um evento da NL para a PD.")

        nl = False
        if liquidacao_id:
            nl = self.env["gov.liquidacao"].browse(liquidacao_id)
            if not nl.exists():
                raise ValidationError("A Nota de Liquidacao informada nao existe.")

        if evento_id:
            evt = self.env["gov.nl.evento"].browse(evento_id)
            if not evt.exists():
                raise ValidationError("O evento informado nao existe.")
            if nl and evt.liquidacao_id != nl:
                raise ValidationError("O evento selecionado nao pertence a NL informada.")

        if nl:
            pds = self.search(
                [
                    ("liquidacao_id", "=", nl.id),
                    ("state", "!=", "cancelado"),
                ]
            )
            consumido = sum(pds.mapped("valor"))
            saldo = (nl.valor_liquidado or 0.0) - consumido
            if consumido + valor > (nl.valor_liquidado or 0.0) + 0.01:
                raise ValidationError(
                    "Valor da PD excede o saldo disponivel da NL "
                    f"{nl.name}.\n"
                    f"Saldo: R$ {saldo:,.2f}\n"
                    f"Tentando programar: R$ {valor:,.2f}"
                )

    def write(self, vals):
        editable_when_locked = {"state", "op_id"}
        blocked_fields = set(vals.keys()) - editable_when_locked
        if blocked_fields:
            locked = self.filtered(lambda rec: rec.state in ("confirmado", "pago", "cancelado"))
            if locked:
                raise UserError("PDs confirmadas, pagas ou canceladas nao podem ser editadas.")
        return super().write(vals)

    @api.depends("liquidacao_id", "liquidacao_id.valor_liquidado")
    def _compute_saldo_disponivel(self):
        for rec in self:
            if not rec.liquidacao_id:
                rec.saldo_disponivel_nl = 0.0
                continue
            pds = self.search(
                [
                    ("liquidacao_id", "=", rec.liquidacao_id.id),
                    ("state", "!=", "cancelado"),
                ]
            )
            consumido = sum(pds.mapped("valor"))
            rec.saldo_disponivel_nl = (rec.liquidacao_id.valor_liquidado or 0.0) - consumido

    @api.onchange("evento_id")
    def _onchange_evento(self):
        if self.evento_id:
            evt = self.evento_id
            if evt.tipo_id and evt.tipo_id.tipo_pagamento:
                self.tipo_pagamento = evt.tipo_id.tipo_pagamento
            if evt.destinatario_id:
                self.destinatario_id = evt.destinatario_id
            self.valor = evt.valor

    @api.onchange("liquidacao_id")
    def _onchange_liquidacao(self):
        self.evento_id = False
        if self.liquidacao_id:
            self.ug_id = self.liquidacao_id.ug_id
            self.exercicio = self.liquidacao_id.exercicio

    @api.constrains("valor", "liquidacao_id")
    def _check_valor(self):
        for rec in self:
            if rec.valor <= 0:
                raise ValidationError("O valor da PD deve ser maior que zero.")
            if not rec.liquidacao_id:
                continue
            pds = self.search(
                [
                    ("liquidacao_id", "=", rec.liquidacao_id.id),
                    ("state", "!=", "cancelado"),
                    ("id", "!=", rec.id),
                ]
            )
            consumido = sum(pds.mapped("valor"))
            saldo = (rec.liquidacao_id.valor_liquidado or 0.0) - consumido
            if consumido + rec.valor > (rec.liquidacao_id.valor_liquidado or 0.0) + 0.01:
                raise ValidationError(
                    "Valor da PD excede o saldo disponivel da NL "
                    f"{rec.liquidacao_id.name}.\n"
                    f"Saldo: R$ {saldo:,.2f}\n"
                    f"Tentando programar: R$ {rec.valor:,.2f}"
                )

    @api.constrains("liquidacao_id", "is_ajuste")
    def _check_nl_obrigatoria(self):
        for rec in self:
            if not rec.liquidacao_id and not rec.is_ajuste:
                raise ValidationError(
                    "Informe a Nota de Liquidacao ou marque como Ajuste sem processo."
                )
            if not rec.liquidacao_id and rec.is_ajuste:
                if not rec.env.user.has_group("gov_base.group_gov_admin"):
                    raise ValidationError(
                        "Apenas administradores podem criar PDs de ajuste sem NL."
                    )

    @api.constrains("liquidacao_id", "evento_id", "is_ajuste")
    def _check_evento_consistencia(self):
        for rec in self:
            if rec.is_ajuste:
                continue
            if rec.liquidacao_id and not rec.evento_id:
                raise ValidationError("Selecione um evento da NL para a PD.")
            if rec.evento_id and rec.liquidacao_id and rec.evento_id.liquidacao_id != rec.liquidacao_id:
                raise ValidationError("O evento selecionado nao pertence a NL informada.")

    def action_confirmar(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas PDs em rascunho podem ser confirmadas.")
        if not self.is_ajuste and self.liquidacao_id and not self.evento_id:
            raise UserError("Selecione um evento da NL antes de confirmar a PD.")

        if self.evento_id:
            self.evento_id.vincular_pd(self)
            vals_evt = {}
            if "pd_id" in self.evento_id._fields:
                vals_evt["pd_id"] = self.id
            if "pd_name" in self.evento_id._fields:
                vals_evt["pd_name"] = self.name
            if vals_evt:
                self.evento_id.write(vals_evt)

        self.write({"state": "confirmado"})
        tipo_label = dict(self._fields["tipo_pagamento"].selection).get(self.tipo_pagamento, "-")
        self.message_post(
            body=Markup(
                f"<b>PD confirmada:</b> {self.name}<br/>"
                f"Valor: R$ {self.valor:,.2f}<br/>"
                f"Tipo: {tipo_label}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_cancelar(self):
        self.ensure_one()
        if self.state == "pago":
            raise UserError(
                "PDs pagas nao podem ser canceladas diretamente. "
                "Cancele a Ordem de Pagamento antes."
            )
        if self.state == "cancelado":
            raise UserError("Esta PD ja esta cancelada.")

        if self.evento_id and self.evento_id.state == "vinculado":
            self.evento_id.liberar_pd()
            vals_evt = {}
            if "pd_id" in self.evento_id._fields:
                vals_evt["pd_id"] = False
            if "pd_name" in self.evento_id._fields:
                vals_evt["pd_name"] = False
            if vals_evt:
                self.evento_id.write(vals_evt)

        self.write({"state": "cancelado"})
        msg = f"<b>PD cancelada:</b> {self.name}"
        if self.evento_id:
            msg += f"<br/>Evento liberado: {self.evento_id.tipo_id.descricao or '-'}"
        self.message_post(
            body=Markup(msg),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_marcar_pago(self):
        self.ensure_one()
        if self.state != "confirmado":
            raise UserError("Apenas PDs confirmadas podem ser marcadas como pagas.")
        self.write({"state": "pago"})

    def action_open_op(self):
        self.ensure_one()
        GovPag = self.env.get("gov.pagamento")
        if not GovPag:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Em desenvolvimento",
                    "message": "gov.pagamento (OP) sera criado no Step 14.3.",
                    "type": "info",
                },
            }
        if self.op_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "gov.pagamento",
                "res_id": self.op_id.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.pagamento",
            "view_mode": "form",
            "target": "current",
            "context": {"default_pd_id": self.id},
        }
