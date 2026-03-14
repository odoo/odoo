import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GovEmpenhoMoveWizard(models.TransientModel):
    _name = "gov.empenho.move.wizard"
    _description = "Wizard de Revisao de Lancamentos Contabeis - NE"

    empenho_id = fields.Many2one(
        "gov.empenho",
        string="Nota de Empenho",
        required=True,
        readonly=True,
    )
    empenho_name = fields.Char(related="empenho_id.name", readonly=True)
    empenho_state = fields.Selection(related="empenho_id.state", readonly=True)
    valor_empenho = fields.Monetary(
        related="empenho_id.valor_empenho",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    move_ne_id = fields.Many2one(
        related="empenho_id.move_ne_id",
        readonly=True,
        string="Lancamento NE",
    )
    move_ne_state = fields.Char(
        related="empenho_id.move_ne_state",
        readonly=True,
        string="Estado do Lancamento",
    )

    resumo_lancamentos = fields.Text(
        string="Historico de Lancamentos",
        compute="_compute_resumo",
        store=False,
    )
    total_debitado = fields.Monetary(
        string="Total Debitado",
        currency_field="currency_id",
        compute="_compute_totais",
        store=False,
    )
    total_creditado = fields.Monetary(
        string="Total Creditado",
        currency_field="currency_id",
        compute="_compute_totais",
        store=False,
    )
    saldo_liquido = fields.Monetary(
        string="Saldo Liquido (D-C)",
        currency_field="currency_id",
        compute="_compute_totais",
        store=False,
    )

    pode_confirmar = fields.Boolean(
        compute="_compute_acoes_disponiveis",
        store=False,
    )
    pode_estornar = fields.Boolean(
        compute="_compute_acoes_disponiveis",
        store=False,
    )
    pode_gerar = fields.Boolean(
        compute="_compute_acoes_disponiveis",
        store=False,
    )

    motivo_estorno = fields.Text(
        string="Motivo do Estorno",
        help="Obrigatorio para estorno manual.",
    )

    @api.depends("empenho_id", "empenho_id.move_ne_id")
    def _compute_resumo(self):
        for rec in self:
            if not rec.empenho_id:
                rec.resumo_lancamentos = ""
                continue

            moves = rec._get_all_moves()
            linhas = []
            for move in moves.sorted(lambda m: (m.date or fields.Date.today(), m.id)):
                tipo = "ESTORNO" if move.reversed_entry_id else "ORIGINAL"
                linhas.append(
                    f"{move.name or '?'} | {move.date} | {move.state.upper()} | {tipo}"
                )
                for line in move.line_ids:
                    sinal = f"D {line.debit:>12,.2f}" if line.debit else f"C {line.credit:>12,.2f}"
                    linhas.append(
                        f"  {line.account_id.code} - {line.account_id.name[:40]}  {sinal}"
                    )

            rec.resumo_lancamentos = (
                "\n".join(linhas) if linhas else "Nenhum lancamento contabil encontrado."
            )

    @api.depends("empenho_id", "empenho_id.move_ne_id", "empenho_id.move_ne_id.state")
    def _compute_totais(self):
        for rec in self:
            if not rec.empenho_id:
                rec.total_debitado = 0.0
                rec.total_creditado = 0.0
                rec.saldo_liquido = 0.0
                continue

            moves = rec._get_all_moves().filtered(lambda m: m.state == "posted")
            total_debito = sum(line.debit for move in moves for line in move.line_ids)
            total_credito = sum(line.credit for move in moves for line in move.line_ids)
            rec.total_debitado = total_debito
            rec.total_creditado = total_credito
            rec.saldo_liquido = total_debito - total_credito

    @api.depends(
        "empenho_id",
        "empenho_id.move_ne_id",
        "empenho_id.move_ne_id.state",
        "empenho_id.state",
        "empenho_id.natureza_despesa",
        "empenho_id.ug_id",
    )
    def _compute_acoes_disponiveis(self):
        Config = self.env.get("gov.account.config")
        for rec in self:
            ne = rec.empenho_id
            if not ne:
                rec.pode_confirmar = False
                rec.pode_estornar = False
                rec.pode_gerar = False
                continue

            move = ne.move_ne_id
            has_mapping = bool(
                Config is not None
                and ne.natureza_despesa
                and Config.get_config(ne.natureza_despesa, ne.ug_id.id)
            )

            rec.pode_confirmar = bool(move and move.state == "draft")
            rec.pode_estornar = bool(move and move.state == "posted" and ne.state != "anulado")
            rec.pode_gerar = bool(not move and ne.state == "emitido" and has_mapping)

    def _get_all_moves(self):
        """
        Retorna o move principal da NE e seus estornos.
        """
        self.ensure_one()
        if not self.empenho_id or not self.empenho_id.move_ne_id:
            return self.env["account.move"]

        original = self.empenho_id.move_ne_id
        estornos = self.env["account.move"].search([("reversed_entry_id", "=", original.id)])
        return original | estornos

    def action_confirmar_lancamento(self):
        self.ensure_one()
        move = self.empenho_id.move_ne_id
        if not move or move.state != "draft":
            raise UserError("Nenhum lancamento em rascunho para confirmar.")

        move.action_post()
        self.empenho_id.message_post(
            body=Markup(f"Lancamento <b>{move.name}</b> confirmado manualmente."),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return self._reabrir()

    def action_gerar_lancamento(self):
        self.ensure_one()
        ne = self.empenho_id
        if ne.move_ne_id:
            raise UserError(
                "Esta NE ja possui lancamento contabil. Estorne o existente antes de gerar um novo."
            )
        if ne.state != "emitido":
            raise UserError("So e possivel gerar lancamento para NEs emitidas.")

        move = ne._gerar_move_empenho()
        if not move:
            raise UserError(
                "Nao foi possivel gerar o lancamento. Verifique se existe mapeamento contabil "
                f"para a natureza {ne.natureza_despesa} em AGI Gov -> Configuracao -> Configuracao Contabil."
            )
        return self._reabrir()

    def action_estornar(self):
        self.ensure_one()
        if not (self.motivo_estorno or "").strip():
            raise UserError("Informe o motivo do estorno antes de prosseguir.")

        move = self.empenho_id.move_ne_id
        if not move or move.state != "posted":
            raise UserError("Nenhum lancamento confirmado para estornar.")

        motivo = self.motivo_estorno.strip()
        try:
            reversal = move._reverse_moves(
                default_values_list=[
                    {
                        "date": fields.Date.today(),
                        "ref": f"Estorno manual NE {self.empenho_id.name}: {motivo[:80]}",
                    }
                ],
                cancel=False,
            )
            if reversal:
                reversal.action_post()
        except Exception as exc:
            _logger.exception("Falha ao gerar estorno manual da NE %s", self.empenho_id.name)
            raise UserError(f"Erro ao gerar estorno: {exc}") from exc

        self.empenho_id.message_post(
            body=Markup(
                f"Estorno manual gerado por <b>{self.env.user.name}</b>.<br/>"
                f"Motivo: {motivo}<br/>"
                f"Move original: {move.name}"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        self.write({"motivo_estorno": ""})
        return self._reabrir()

    def action_abrir_move(self):
        self.ensure_one()
        move = self.empenho_id.move_ne_id
        if not move:
            raise UserError("Nenhum lancamento para abrir.")
        return {
            "type": "ir.actions.act_window",
            "name": f"Lancamento - {move.name}",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "new",
        }

    def _reabrir(self):
        self.invalidate_recordset()
        return {
            "type": "ir.actions.act_window",
            "res_model": "gov.empenho.move.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
