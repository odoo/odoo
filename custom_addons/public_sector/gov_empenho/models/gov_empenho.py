import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GovEmpenho(models.Model):
    _name = "gov.empenho"
    _description = "Nota de Empenho (NE)"
    _inherit = ["mail.thread", "mail.activity.mixin", "gov.empenho.accounting"]
    _order = "data_empenho desc, name desc"

    name = fields.Char(
        string="Número NE",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("aprovado", "Aprovado"),
            ("emitido", "Emitido"),
            ("anulado", "Anulado"),
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
        string="Exercício",
        default=lambda self: fields.Date.today().year,
        required=True,
    )

    programa = fields.Char(string="Programa")
    acao = fields.Char(string="Ação")
    natureza_despesa = fields.Char(
        string="Natureza da Despesa",
        help="Ex: 3.3.90.39",
    )
    fonte_recurso = fields.Char(
        string="Fonte de Recurso",
        help="Ex: 100",
    )

    dotacao_id = fields.Many2one(
        "gov.processo.dotacao",
        string="Dotação do Processo",
        help="Indicação orçamentária do processo que originou este empenho.",
        ondelete="restrict",
    )

    credor_id = fields.Many2one(
        "res.partner",
        string="Credor (Fornecedor)",
        required=True,
        tracking=True,
    )
    cnpj_credor = fields.Char(
        string="CNPJ do Credor",
        related="credor_id.vat",
        readonly=True,
    )

    valor_empenho = fields.Monetary(
        string="Valor do Empenho",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    valor_anulado = fields.Monetary(
        string="Valor Anulado",
        currency_field="currency_id",
        default=0.0,
        readonly=True,
    )
    valor_liquido = fields.Monetary(
        string="Valor Líquido",
        currency_field="currency_id",
        compute="_compute_valor_liquido",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends("valor_empenho", "valor_anulado")
    def _compute_valor_liquido(self):
        for rec in self:
            rec.valor_liquido = (rec.valor_empenho or 0.0) - (rec.valor_anulado or 0.0)

    data_empenho = fields.Date(
        string="Data do Empenho",
        default=fields.Date.today,
    )
    data_vencimento = fields.Date(string="Vencimento")

    tipo_empenho = fields.Selection(
        [
            ("ordinario", "Ordinário"),
            ("estimativo", "Estimativo"),
            ("global", "Global"),
        ],
        string="Tipo de Empenho",
        default="ordinario",
        required=True,
    )

    objeto = fields.Text(
        string="Objeto do Empenho",
        required=True,
    )

    processo_id_ref = fields.Integer(
        string="ID do Processo AGI Gov",
        help=(
            "Referência ao gov.processo. "
            "Vínculo formal via gov.processo.vinculo."
        ),
    )
    processo_numero = fields.Char(
        string="Número do Processo",
        compute="_compute_processo_info",
        store=False,
    )
    processo_subject = fields.Char(
        string="Objeto do Processo",
        compute="_compute_processo_info",
        store=False,
    )

    @api.depends("processo_id_ref")
    def _compute_processo_info(self):
        Processo = self.env.get("gov.processo")
        for rec in self:
            if rec.processo_id_ref and Processo is not None:
                processo = Processo.sudo().browse(rec.processo_id_ref)
                if processo.exists():
                    rec.processo_numero = processo.name
                    rec.processo_subject = processo.subject
                    continue
            rec.processo_numero = ""
            rec.processo_subject = ""

    retroativo = fields.Boolean(
        string="Empenho Retroativo (NE Indenizatória)",
        default=False,
        tracking=True,
    )
    urgencia = fields.Boolean(
        string="Empenho de Urgência (OS)",
        default=False,
        tracking=True,
    )

    observacao = fields.Text(string="Observação")
    liquidacao_count = fields.Integer(
        string="Total de Liquidações",
        compute="_compute_liquidacao_count",
    )

    def _compute_liquidacao_count(self):
        Liq = self.env.get("gov.liquidacao")
        for rec in self:
            if Liq is not None:
                rec.liquidacao_count = Liq.search_count([("empenho_id", "=", rec.id)])
            else:
                rec.liquidacao_count = 0

    @api.constrains("valor_empenho")
    def _check_valor_empenho(self):
        for rec in self:
            if rec.valor_empenho is None:
                continue
            if rec.valor_empenho < 0:
                raise ValidationError("Valor do empenho não pode ser negativo.")

    @api.constrains("valor_empenho", "valor_anulado")
    def _check_valor_anulado(self):
        for rec in self:
            if (rec.valor_anulado or 0.0) > (rec.valor_empenho or 0.0):
                raise ValidationError("Valor anulado não pode exceder o valor do empenho.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = self.env["ir.sequence"].next_by_code("gov.empenho") or "Novo"
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            rec._criar_vinculo_processo(processo_id_ref=vals.get("processo_id_ref"))
        return records

    def _criar_vinculo_processo(self, processo_id_ref=None):
        self.ensure_one()
        target_processo_id = processo_id_ref or self.processo_id_ref
        if not target_processo_id:
            return

        Processo = self.env.get("gov.processo")
        if Processo is None:
            return

        processo = Processo.sudo().browse(target_processo_id)
        if not processo.exists():
            _logger.warning("Processo %s não encontrado para vincular empenho %s", target_processo_id, self.id)
            return

        Vinculo = self.env["gov.processo.vinculo"]
        existente = Vinculo.search(
            [
                ("processo_id", "=", processo.id),
                ("model_name", "=", "gov.empenho"),
                ("record_id", "=", self.id),
                ("vinculo_type", "=", "gera"),
            ],
            limit=1,
        )
        if not existente:
            Vinculo.create(
                {
                    "processo_id": processo.id,
                    "model_name": "gov.empenho",
                    "record_id": self.id,
                    "vinculo_type": "gera",
                }
            )

    def action_aprovar(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas rascunhos podem ser aprovados.")

        self.write({"state": "aprovado"})
        self.message_post(
            body=Markup("<b>Empenho aprovado.</b>"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_emitir(self):
        self.ensure_one()
        if self.state != "aprovado":
            raise UserError("Apenas empenhos aprovados podem ser emitidos.")
        if (self.valor_empenho or 0.0) <= 0:
            raise UserError("Valor do empenho deve ser maior que zero.")

        self.write({"state": "emitido"})

        if self.dotacao_id:
            self.dotacao_id.write(
                {
                    "reservado": True,
                    "empenho_id": self.id,
                }
            )

        move = self._gerar_move_empenho()

        self._criar_vinculo_processo()
        self._notificar_processo_emitido()

        info_contabil = ""
        if move:
            info_contabil = f"<br/>Lancamento contabil: <b>{move.name}</b> ({move.state})"
        elif self.natureza_despesa:
            info_contabil = (
                "<br/>Sem mapeamento contabil para "
                f"{self.natureza_despesa} - lancamento nao gerado."
            )

        self.message_post(
            body=Markup(
                f"<b>NE emitida:</b> {self.name}<br/>"
                f"Valor: R$ {self.valor_liquido:,.2f}<br/>"
                f"Credor: {self.credor_id.name}"
                f"{info_contabil}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_anular(self):
        self.ensure_one()
        if self.state not in ("aprovado", "emitido"):
            raise UserError("Apenas empenhos aprovados ou emitidos podem ser anulados.")
        if (self.valor_anulado or 0.0) >= (self.valor_empenho or 0.0):
            raise UserError("Empenho já totalmente anulado.")

        estorno = self._gerar_move_estorno_empenho()

        self.write(
            {
                "state": "anulado",
                "valor_anulado": self.valor_empenho,
            }
        )

        if self.dotacao_id and self.dotacao_id.reservado:
            self.dotacao_id.write({"reservado": False})

        info_estorno = ""
        if estorno:
            estorno_name = estorno.name if hasattr(estorno, "name") else str(estorno)
            info_estorno = f"<br/>Estorno contabil: <b>{estorno_name}</b>"

        self.message_post(
            body=Markup(f"<b>NE anulada:</b> {self.name}{info_estorno}"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _notificar_processo_emitido(self):
        if not self.processo_id_ref:
            return

        Processo = self.env.get("gov.processo")
        if Processo is None:
            return

        processo = Processo.sudo().browse(self.processo_id_ref)
        if not processo.exists():
            return

        processo.message_post(
            body=Markup(
                f"<b>Nota de Empenho emitida</b>: {self.name}<br/>"
                f"Valor: R$ {self.valor_liquido:,.2f}<br/>"
                f"Credor: {self.credor_id.name}<br/>"
                f"Natureza: {self.natureza_despesa or '-'}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_open_liquidacoes(self):
        self.ensure_one()
        Liq = self.env.get("gov.liquidacao")
        if Liq is None:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Módulo não instalado",
                    "message": "gov_liquidacao será instalado na Onda 2.",
                    "type": "info",
                },
            }
        return {
            "type": "ir.actions.act_window",
            "name": f"Liquidações - {self.name}",
            "res_model": "gov.liquidacao",
            "view_mode": "list,form",
            "domain": [("empenho_id", "=", self.id)],
            "context": {"default_empenho_id": self.id},
        }

    def action_open_move_wizard(self):
        self.ensure_one()
        wizard = self.env["gov.empenho.move.wizard"].create({"empenho_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": f"Lancamentos - {self.name}",
            "res_model": "gov.empenho.move.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
