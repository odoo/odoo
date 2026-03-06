import base64
import hashlib
import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .gov_cnab_service import GovCnabService

_logger = logging.getLogger(__name__)


class GovPagamento(models.Model):
    _name = "gov.pagamento"
    _description = "Ordem de Pagamento (OP)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        string="Numero OP",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("aprovado", "Aprovado"),
            ("enviado", "Enviado ao Banco"),
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
    )

    pd_id = fields.Many2one(
        "gov.pd",
        string="Programacao de Desembolso",
        required=True,
        ondelete="restrict",
        domain="[('state','=','confirmado')]",
        tracking=True,
    )
    pd_name = fields.Char(
        related="pd_id.name",
        readonly=True,
        string="PD",
    )
    pd_tipo_pagamento = fields.Selection(
        related="pd_id.tipo_pagamento",
        readonly=True,
    )
    pd_valor = fields.Monetary(
        related="pd_id.valor",
        currency_field="currency_id",
        readonly=True,
        string="Valor da PD",
    )

    destinatario_id = fields.Many2one(
        related="pd_id.destinatario_id",
        readonly=True,
        string="Destinatario",
    )
    tipo_pagamento = fields.Selection(
        related="pd_id.tipo_pagamento",
        readonly=True,
        string="Tipo",
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

    data_pagamento = fields.Date(
        string="Data de Pagamento",
        default=fields.Date.today,
    )
    banco_codigo = fields.Char(string="Banco Destino")
    agencia_dest = fields.Char(string="Agencia Destino")
    conta_dest = fields.Char(string="Conta Destino")
    pix_chave = fields.Char(string="Chave PIX")
    darf_codigo = fields.Char(string="Codigo DARF")
    codigo_barras = fields.Char(string="Codigo de Barras")
    competencia = fields.Char(string="Competencia")
    numero_doc = fields.Char(string="Numero Documento")

    move_op_id = fields.Many2one(
        "account.move",
        string="Lancamento Contabil OP",
        readonly=True,
        copy=False,
    )

    cnab_file = fields.Binary(
        string="Arquivo CNAB240",
        readonly=True,
    )
    cnab_filename = fields.Char(readonly=True)
    hash_sha256 = fields.Char(readonly=True)
    observacao = fields.Text(string="Observacao")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pd = self.env["gov.pd"].browse(vals.get("pd_id")) if vals.get("pd_id") else False
            self._precheck_create_vals(vals, pd)
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = self.env["ir.sequence"].next_by_code("gov.pagamento") or "Novo"
            if pd:
                if "ug_id" not in vals:
                    vals["ug_id"] = pd.ug_id.id
                if "exercicio" not in vals:
                    vals["exercicio"] = pd.exercicio
                if "valor" not in vals:
                    vals["valor"] = pd.valor

        recs = super().create(vals_list)
        for rec in recs:
            if rec.pd_id:
                rec.pd_id.write({"op_id": rec.id})
        return recs

    def _precheck_create_vals(self, vals, pd):
        if not pd or not pd.exists():
            raise ValidationError("Informe uma PD valida para criar a OP.")
        if pd.state != "confirmado":
            raise ValidationError(
                f"A PD {pd.name} deve estar em estado confirmado para gerar OP."
            )

        existente = self.search(
            [
                ("pd_id", "=", pd.id),
                ("state", "not in", ["cancelado"]),
            ],
            limit=1,
        )
        if existente:
            raise ValidationError(
                f"A PD {pd.name} ja possui uma OP ativa: {existente.name}. "
                "Cancele a OP existente antes de criar outra."
            )

        valor = vals.get("valor", pd.valor)
        if (valor or 0.0) <= 0:
            raise ValidationError("O valor da OP deve ser maior que zero.")
        if abs((valor or 0.0) - (pd.valor or 0.0)) > 0.01:
            raise ValidationError(
                f"O valor da OP (R$ {valor:,.2f}) deve ser igual ao valor da PD "
                f"(R$ {pd.valor:,.2f})."
            )

    @api.constrains("pd_id")
    def _check_pd_unica(self):
        for rec in self:
            outras = self.search(
                [
                    ("pd_id", "=", rec.pd_id.id),
                    ("state", "not in", ["cancelado"]),
                    ("id", "!=", rec.id),
                ]
            )
            if outras:
                raise ValidationError(
                    f"A PD {rec.pd_id.name} ja possui uma OP ativa: {outras[0].name}. "
                    "Cancele a OP existente antes de criar outra."
                )

    @api.constrains("valor", "pd_id")
    def _check_valor(self):
        for rec in self:
            if rec.valor <= 0:
                raise ValidationError("O valor da OP deve ser maior que zero.")
            if rec.pd_id and abs(rec.valor - rec.pd_id.valor) > 0.01:
                raise ValidationError(
                    f"O valor da OP (R$ {rec.valor:,.2f}) deve ser igual ao valor da PD "
                    f"(R$ {rec.pd_id.valor:,.2f})."
                )

    def action_aprovar(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas OPs em rascunho podem ser aprovadas.")
        self.write({"state": "aprovado"})
        self.message_post(
            body=Markup(
                f"<b>OP aprovada:</b> {self.name}<br/>"
                f"Valor: R$ {self.valor:,.2f}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_enviar_banco(self):
        self.ensure_one()
        if self.state != "aprovado":
            raise UserError("Apenas OPs aprovadas podem ser enviadas ao banco.")
        self._gerar_cnab()
        self.write({"state": "enviado"})
        self.message_post(
            body=Markup(
                f"<b>OP enviada ao banco:</b> {self.name}<br/>"
                f"Arquivo: {self.cnab_filename or '-'}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_confirmar_pagamento(self):
        self.ensure_one()
        if self.state not in ("aprovado", "enviado"):
            raise UserError(
                "Apenas OPs aprovadas ou enviadas podem ser confirmadas como pagas."
            )

        move = self._gerar_move_pagamento()
        self.write({"state": "pago"})
        if self.pd_id:
            self.pd_id.action_marcar_pago()

        info_move = (
            f"<br/>Lancamento: <b>{move.name}</b>"
            if move
            else "<br/>Sem lancamento contabil (mapeamento ausente)."
        )
        self.message_post(
            body=Markup(
                f"<b>Pagamento confirmado:</b> {self.name}<br/>"
                f"Valor: R$ {self.valor:,.2f}<br/>"
                f"Data: {self.data_pagamento}"
                f"{info_move}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_cancelar(self):
        self.ensure_one()
        if self.state == "pago":
            raise UserError(
                "OPs pagas nao podem ser canceladas diretamente. "
                "Realize um estorno contabil manual."
            )

        if self.move_op_id and self.move_op_id.state == "posted":
            self._estornar_move_pagamento()

        if self.pd_id and self.pd_id.state != "cancelado":
            vals_pd = {"op_id": False}
            if self.pd_id.state == "pago":
                vals_pd["state"] = "confirmado"
            self.pd_id.write(vals_pd)

        self.write({"state": "cancelado"})
        self.message_post(
            body=Markup(f"<b>OP cancelada:</b> {self.name}"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _gerar_move_pagamento(self):
        self.ensure_one()

        conta_debito = self.pd_id.evento_id.account_id if self.pd_id and self.pd_id.evento_id else None
        if not conta_debito:
            Config = self.env.get("gov.account.config")
            if Config is not None and self.pd_id and self.pd_id.liquidacao_id:
                contas = Config.get_accounts(self.pd_id.liquidacao_id.natureza_despesa, self.ug_id.id)
                conta_debito = contas.get("liquidacao_pagar")

        conta_banco = self.env.ref("gov_empenho.account_1_1_1_2_01", raise_if_not_found=False)
        if not conta_banco:
            conta_banco = self.env["account.account"].search(
                [("code", "=", "1.1.1.2.01"), ("company_ids", "in", self.ug_id.id)],
                limit=1,
            ) or self.env["account.account"].search([("code", "=", "1.1.1.2.01")], limit=1)

        if not conta_debito or not conta_banco:
            _logger.warning(
                "GRP Contabil OP: contas nao encontradas para OP %s. Sem lancamento.",
                self.name,
            )
            return None

        Journal = self.env["account.journal"]
        journal = Journal.search(
            [
                ("company_id", "=", self.ug_id.id),
                ("type", "in", ["bank", "cash", "general"]),
            ],
            limit=1,
        ) or Journal.search([("type", "in", ["bank", "cash", "general"])], limit=1)
        if not journal:
            _logger.warning("GRP Contabil OP: sem journal para OP %s.", self.name)
            return None

        move = self.env["account.move"].create(
            {
                "ref": f"OP {self.name} - PD {self.pd_id.name}",
                "journal_id": journal.id,
                "date": self.data_pagamento or fields.Date.today(),
                "company_id": self.ug_id.id,
                "move_type": "entry",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": conta_debito.id,
                            "name": f"OP {self.name} - Baixa a Pagar",
                            "debit": self.valor,
                            "credit": 0.0,
                            "partner_id": self.destinatario_id.id if self.destinatario_id else False,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": conta_banco.id,
                            "name": f"OP {self.name} - Saida Caixa",
                            "debit": 0.0,
                            "credit": self.valor,
                            "partner_id": self.destinatario_id.id if self.destinatario_id else False,
                        },
                    ),
                ],
            }
        )

        try:
            move.action_post()
        except Exception as exc:
            _logger.warning(
                "GRP Contabil OP: erro ao postar move da OP %s: %s",
                self.name,
                exc,
            )

        self.write({"move_op_id": move.id})
        return move

    def _estornar_move_pagamento(self):
        self.ensure_one()
        if not self.move_op_id:
            return
        try:
            reversal = self.move_op_id._reverse_moves(
                default_values_list=[
                    {
                        "date": fields.Date.today(),
                        "ref": f"Estorno da OP {self.name}",
                    }
                ],
                cancel=False,
            )
            if reversal:
                reversal.action_post()
        except Exception as exc:
            _logger.warning(
                "GRP Contabil OP: erro ao estornar OP %s: %s",
                self.name,
                exc,
            )

    def _op_to_dict(self):
        self.ensure_one()
        pd = self.pd_id
        dest = self.destinatario_id
        bank = self.ug_id.bank_ids[:1] if self.ug_id.bank_ids else False
        banco_pagador = "001"
        if bank and bank.bank_id and bank.bank_id.bic:
            banco_pagador = (bank.bank_id.bic or "001")[:3]

        return {
            "numero_op": self.name,
            "numero_doc": self.numero_doc or self.name,
            "tipo_pagamento": self.tipo_pagamento,
            "valor": self.valor,
            "data_pagamento": self.data_pagamento,
            "banco_pagador": banco_pagador,
            "banco_dest": self.banco_codigo or "",
            "agencia_dest": self.agencia_dest or "",
            "agencia_dest_dv": "",
            "conta_dest": self.conta_dest or "",
            "conta_dest_dv": "",
            "nome_dest": dest.name[:30] if dest else "",
            "cnpj_dest": (dest.vat or "") if dest else "",
            "pix_chave": self.pix_chave or "",
            "darf_codigo": self.darf_codigo or "",
            "codigo_barras": self.codigo_barras or "",
            "competencia": (self.competencia or "").replace("/", ""),
            "historico": f"OP {self.name} PD {pd.name if pd else ''}",
        }

    def _gerar_cnab(self):
        self.ensure_one()
        company = self.ug_id
        bank = company.bank_ids[:1] if company.bank_ids else False
        bank_bic = "001"
        if bank and bank.bank_id and bank.bank_id.bic:
            bank_bic = (bank.bank_id.bic or "001")[:3]

        empresa = {
            "banco": bank_bic,
            "agencia": (getattr(bank, "branch_number", "") or "0001") if bank else "0001",
            "agencia_dv": "0",
            "conta": (getattr(bank, "acc_number", "") or "00000000") if bank else "00000000",
            "conta_dv": "0",
            "nome": (company.name or "")[:30].upper(),
            "cnpj": (company.vat or "00000000000000"),
            "convenio": "",
            "logradouro": getattr(company, "street", "") or "",
            "numero": "",
            "complemento": getattr(company, "street2", "") or "",
            "cidade": getattr(company, "city", "") or "",
            "cep": getattr(company, "zip", "") or "",
            "estado": company.state_id.code if company.state_id else "AM",
        }

        cnab_bytes = GovCnabService.gerar_arquivo([self._op_to_dict()], empresa)
        sha256 = hashlib.sha256(cnab_bytes).hexdigest()
        filename = f"CNAB240_{self.name}_{fields.Date.today()}.txt".replace(" ", "_")
        self.write(
            {
                "cnab_file": base64.b64encode(cnab_bytes).decode("ascii"),
                "cnab_filename": filename,
                "hash_sha256": sha256,
            }
        )

    def action_gerar_cnab_individual(self):
        self.ensure_one()
        self._gerar_cnab()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "CNAB240 gerado",
                "message": self.cnab_filename or "",
                "type": "success",
            },
        }
