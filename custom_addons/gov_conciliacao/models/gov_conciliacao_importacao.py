import base64
import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


FORMATO_SEL = [
    ("cnab240_bb", "CNAB240 Retorno - Banco do Brasil"),
    ("cnab240_cef", "CNAB240 Retorno - Caixa Economica Federal"),
    ("ofx", "OFX / Open Financial Exchange"),
    ("ofx_xml", "OFX 2.x (XML)"),
]

BANCO_SEL = [
    ("001", "Banco do Brasil"),
    ("104", "Caixa Economica Federal"),
    ("outros", "Outros"),
]


class GovConciliacaoImportacao(models.Model):
    _name = "gov.conciliacao.importacao"
    _description = "Importacao de Extrato para Conciliacao Bancaria"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "data_importacao desc, id desc"

    name = fields.Char(
        string="Referencia",
        copy=False,
        readonly=True,
        default="Novo",
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("processado", "Processado"),
            ("conciliado", "Conciliado"),
            ("cancelado", "Cancelado"),
        ],
        default="rascunho",
        required=True,
        tracking=True,
        string="Estado",
    )

    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
    )
    conta_bancaria_id = fields.Many2one(
        "account.account",
        string="Conta Bancaria",
        domain="[('code', 'like', '1.1.1.2')]",
        required=True,
        help="Conta contabil bancaria (1.1.1.2.xx).",
    )
    banco = fields.Selection(BANCO_SEL, string="Banco", required=True, default="001")
    formato = fields.Selection(FORMATO_SEL, string="Formato do Arquivo", required=True, default="cnab240_bb")

    arquivo = fields.Binary(string="Arquivo", required=True)
    arquivo_nome = fields.Char(string="Nome do Arquivo")
    data_importacao = fields.Datetime(
        string="Data de Importacao",
        default=fields.Datetime.now,
        readonly=True,
    )
    operador_id = fields.Many2one(
        "res.users",
        string="Operador",
        default=lambda self: self.env.user,
        readonly=True,
    )

    data_extrato_ini = fields.Date(string="Extrato - Data Inicio", readonly=True)
    data_extrato_fim = fields.Date(string="Extrato - Data Fim", readonly=True)
    saldo_extrato = fields.Monetary(
        string="Saldo Final do Extrato",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    total_linhas = fields.Integer(string="Total de Registros", readonly=True)
    total_aceitos = fields.Integer(string="Aceitos", readonly=True)
    total_rejeitados = fields.Integer(string="Rejeitados", readonly=True)
    total_divergentes = fields.Integer(string="Divergentes", readonly=True)
    total_nao_identificados = fields.Integer(string="Nao Identificados", readonly=True)

    pendencia_ids = fields.One2many(
        "gov.conciliacao.pendencia",
        "importacao_id",
        string="Pendencias",
        readonly=True,
    )
    pendencia_count = fields.Integer(
        compute="_compute_pendencia_count",
        string="Total de Pendencias",
    )

    observacao = fields.Text(string="Observacoes")
    log_processamento = fields.Text(string="Log de Processamento", readonly=True)

    @api.depends("pendencia_ids")
    def _compute_pendencia_count(self):
        for rec in self:
            rec.pendencia_count = len(rec.pendencia_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Novo") == "Novo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("gov.conciliacao.importacao") or "Novo"
                )
        return super().create(vals_list)

    @api.onchange("banco")
    def _onchange_banco(self):
        mapa = {
            "001": "cnab240_bb",
            "104": "cnab240_cef",
        }
        if self.banco in mapa:
            self.formato = mapa[self.banco]

    def action_processar(self):
        self.ensure_one()
        if self.state != "rascunho":
            raise UserError("Apenas importacoes em rascunho podem ser processadas.")
        if not self.arquivo:
            raise UserError("Nenhum arquivo carregado.")

        conteudo = base64.b64decode(self.arquivo)
        log = []

        try:
            if "ofx" in (self.formato or ""):
                resultado = self._parse_ofx(conteudo, log)
            else:
                resultado = self._parse_cnab(conteudo, log)
        except Exception as exc:
            raise UserError(f"Erro ao processar arquivo: {exc}") from exc

        valores = {
            "state": "processado",
            "log_processamento": "\n".join(log),
        }

        if hasattr(resultado, "linhas"):
            linhas = resultado.linhas
            valores.update(
                {
                    "total_linhas": len(linhas),
                    "total_aceitos": sum(1 for linha in linhas if linha.status == "aceito"),
                    "total_rejeitados": sum(
                        1 for linha in linhas if linha.status == "rejeitado"
                    ),
                    "total_divergentes": sum(
                        1 for linha in linhas if linha.status in ("divergencia", "devolvido")
                    ),
                    "total_nao_identificados": sum(
                        1
                        for linha in linhas
                        if linha.status in ("debito_nao_id", "credito_nao_id", "informativo")
                    ),
                    "data_extrato_ini": resultado.data_arquivo,
                    "data_extrato_fim": resultado.data_arquivo,
                    "saldo_extrato": resultado.total_aceito,
                }
            )
            self.write(valores)
            self._criar_pendencias_cnab(linhas, log)
        else:
            transacoes = resultado.transacoes
            valores.update(
                {
                    "total_linhas": len(transacoes),
                    "total_aceitos": sum(
                        1 for transacao in transacoes if transacao.natureza == "debito"
                    ),
                    "total_rejeitados": 0,
                    "total_divergentes": 0,
                    "total_nao_identificados": sum(
                        1 for transacao in transacoes if transacao.natureza == "credito"
                    ),
                    "data_extrato_ini": resultado.data_inicio,
                    "data_extrato_fim": resultado.data_fim,
                    "saldo_extrato": resultado.saldo_final,
                }
            )
            self.write(valores)
            self._criar_pendencias_ofx(transacoes, log)

        self.write({"log_processamento": "\n".join(log)})
        self.message_post(
            body=Markup(
                f"<b>Arquivo processado:</b> {self.arquivo_nome or '-'}<br/>"
                f"Total: {self.total_linhas} | Aceitos: {self.total_aceitos} | "
                f"Rejeitados: {self.total_rejeitados} | Pendencias: {self.pendencia_count}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return self._reabrir()

    def _parse_cnab(self, conteudo: bytes, log: list):
        from ..parsers.gov_cnab240_retorno import get_parser

        banco_codigo = "001" if self.banco == "001" else "104" if self.banco == "104" else "999"
        parser = get_parser(banco_codigo)
        resultado = parser.parse(conteudo)
        log.append(
            f"CNAB240 retorno - banco {banco_codigo} - {len(resultado.linhas)} linha(s) de detalhe."
        )
        if resultado.erros:
            log.extend(resultado.erros)
        return resultado

    def _parse_ofx(self, conteudo: bytes, log: list):
        from ..parsers.gov_ofx_parser import GovOfxParser

        parser = GovOfxParser()
        resultado = parser.parse(conteudo)
        log.append(
            f"OFX - conta {resultado.conta or '-'} - {len(resultado.transacoes)} transacao(oes)."
        )
        if resultado.erros:
            log.extend(resultado.erros)
        return resultado

    def _criar_pendencias_cnab(self, linhas, log):
        pend_model = self.env["gov.conciliacao.pendencia"]
        criadas = 0
        for linha in linhas:
            if linha.status == "informativo":
                continue
            pend_model.create(
                {
                    "importacao_id": self.id,
                    "ug_id": self.ug_id.id,
                    "conta_bancaria_id": self.conta_bancaria_id.id,
                    "tipo": self._status_to_tipo(linha.status),
                    "state": "aberta",
                    "numero_doc": linha.numero_doc,
                    "valor_banco": linha.valor_pago,
                    "valor_sistema": linha.valor_original,
                    "diferenca": abs((linha.valor_pago or 0.0) - (linha.valor_original or 0.0)),
                    "data_ocorrencia": linha.data_pagamento or fields.Date.today(),
                    "ocorrencia_banco": linha.ocorrencia,
                    "historico": f"{linha.segmento} | Ocorrencia: {linha.ocorrencia} | {linha.nome_beneficiario}",
                    "banco": self.banco,
                    "segmento": linha.segmento,
                }
            )
            criadas += 1
        log.append(f"{criadas} pendencia(s) criada(s) a partir de CNAB.")

    def _criar_pendencias_ofx(self, transacoes, log):
        pend_model = self.env["gov.conciliacao.pendencia"]
        criadas = 0
        for transacao in transacoes:
            tipo = (
                "debito_nao_identificado"
                if transacao.natureza == "debito"
                else "credito_nao_identificado"
            )
            pend_model.create(
                {
                    "importacao_id": self.id,
                    "ug_id": self.ug_id.id,
                    "conta_bancaria_id": self.conta_bancaria_id.id,
                    "tipo": tipo,
                    "state": "aberta",
                    "numero_doc": transacao.fitid,
                    "valor_banco": transacao.valor,
                    "valor_sistema": 0.0,
                    "diferenca": transacao.valor,
                    "data_ocorrencia": transacao.data or fields.Date.today(),
                    "historico": transacao.memo or transacao.tipo,
                    "banco": self.banco,
                    "segmento": "OFX",
                }
            )
            criadas += 1
        log.append(f"{criadas} pendencia(s) criada(s) a partir de OFX.")

    @staticmethod
    def _status_to_tipo(status):
        return {
            "aceito": "pagamento_confirmado",
            "rejeitado": "pagamento_rejeitado",
            "divergencia": "divergencia_valor",
            "devolvido": "pagamento_devolvido",
            "debito_nao_id": "debito_nao_identificado",
            "credito_nao_id": "credito_nao_identificado",
        }.get(status, "outros")

    def action_ver_pendencias(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Pendencias - {self.name}",
            "res_model": "gov.conciliacao.pendencia",
            "view_mode": "list,form",
            "domain": [("importacao_id", "=", self.id)],
            "context": {
                "default_importacao_id": self.id,
                "default_ug_id": self.ug_id.id,
                "default_conta_bancaria_id": self.conta_bancaria_id.id,
            },
        }

    def action_cancelar(self):
        self.ensure_one()
        abertas = self.pendencia_ids.filtered(lambda pend: pend.state == "aberta")
        if abertas:
            raise UserError(
                f"Existem {len(abertas)} pendencia(s) aberta(s). Resolva antes de cancelar."
            )
        self.write({"state": "cancelado"})

    def _reabrir(self):
        self.invalidate_recordset()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.conciliacao.importacao",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
