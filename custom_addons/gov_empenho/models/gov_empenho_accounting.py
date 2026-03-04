import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GovEmpenhoAccounting(models.AbstractModel):
    _name = "gov.empenho.accounting"
    _description = "Mixin Contabil - NE"

    move_ne_id = fields.Many2one(
        "account.move",
        string="Lancamento Contabil NE",
        readonly=True,
        copy=False,
        help="account.move gerado na emissao da Nota de Empenho.",
    )
    move_ne_state = fields.Char(
        string="Estado do Lancamento",
        compute="_compute_move_ne_state",
        store=False,
    )
    contabil_configurado = fields.Boolean(
        string="Contabilidade Configurada",
        compute="_compute_contabil_configurado",
        store=False,
        help=(
            "True se existe mapeamento contabil para a "
            "natureza de despesa desta NE."
        ),
    )

    @api.depends("move_ne_id", "move_ne_id.state")
    def _compute_move_ne_state(self):
        for rec in self:
            rec.move_ne_state = rec.move_ne_id.state if rec.move_ne_id else "sem lancamento"

    @api.depends("natureza_despesa", "ug_id")
    def _compute_contabil_configurado(self):
        Config = self.env.get("gov.account.config")
        for rec in self:
            if Config is None or not rec.natureza_despesa:
                rec.contabil_configurado = False
                continue
            cfg = Config.get_config(rec.natureza_despesa, rec.ug_id.id)
            rec.contabil_configurado = bool(cfg)

    def _gerar_move_empenho(self):
        """
        Gera account.move da emissao da NE.
        Graceful: sem mapeamento/journal, nao bloqueia a emissao.
        """
        self.ensure_one()

        Config = self.env.get("gov.account.config")
        if Config is None:
            _logger.warning(
                "GRP Contabil: gov.account.config nao disponivel. "
                "NE %s emitida sem lancamento contabil.",
                self.name,
            )
            return None

        contas = Config.get_accounts(self.natureza_despesa, self.ug_id.id)
        if not contas["despesa"] or not contas["empenho_pagar"]:
            _logger.warning(
                "GRP Contabil: sem mapeamento para natureza %s / UG %s. "
                "NE %s emitida sem lancamento contabil.",
                self.natureza_despesa,
                self.ug_id.name,
                self.name,
            )
            return None

        Journal = self.env["account.journal"]
        journal = Journal.search(
            [
                ("company_id", "=", self.ug_id.id),
                ("type", "in", ["general", "purchase"]),
            ],
            limit=1,
        )
        if not journal:
            journal = Journal.search([("type", "in", ["general", "purchase"])], limit=1)
        if not journal:
            _logger.warning(
                "GRP Contabil: nenhum journal disponivel. "
                "NE %s emitida sem lancamento.",
                self.name,
            )
            return None

        move_vals = {
            "ref": f"NE {self.name} - {(self.objeto or '')[:60]}",
            "journal_id": journal.id,
            "date": self.data_empenho or fields.Date.today(),
            "company_id": self.ug_id.id,
            "move_type": "entry",
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": contas["despesa"].id,
                        "name": f"Empenho {self.name} - Despesa",
                        "debit": self.valor_empenho,
                        "credit": 0.0,
                        "partner_id": self.credor_id.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": contas["empenho_pagar"].id,
                        "name": f"Empenho {self.name} - A Pagar",
                        "debit": 0.0,
                        "credit": self.valor_empenho,
                        "partner_id": self.credor_id.id,
                    },
                ),
            ],
        }

        try:
            move = self.env["account.move"].create(move_vals)
        except Exception as exc:
            _logger.warning(
                "GRP Contabil: falha ao criar account.move da NE %s: %s",
                self.name,
                exc,
            )
            return None

        try:
            move.action_post()
        except Exception as exc:
            _logger.warning(
                "GRP Contabil: nao foi possivel postar account.move da NE %s: %s",
                self.name,
                exc,
            )

        self.write({"move_ne_id": move.id})
        _logger.info(
            "GRP Contabil: account.move %s criado para NE %s.",
            move.name,
            self.name,
        )
        return move

    def _gerar_move_estorno_empenho(self):
        """
        Gera estorno do account.move na anulacao da NE.
        """
        self.ensure_one()
        if not self.move_ne_id:
            _logger.info("GRP Contabil: NE %s sem lancamento para estornar.", self.name)
            return None

        try:
            reversal_vals = {
                "date": fields.Date.today(),
                "ref": f"Estorno da NE {self.name}",
            }
            reversal = self.move_ne_id._reverse_moves(default_values_list=[reversal_vals], cancel=False)
            if reversal:
                reversal.action_post()
                _logger.info(
                    "GRP Contabil: estorno %s gerado para NE %s.",
                    reversal[0].name if len(reversal) == 1 else reversal.mapped("name"),
                    self.name,
                )
                return reversal[0] if len(reversal) == 1 else reversal
        except Exception as exc:
            _logger.warning(
                "GRP Contabil: falha ao gerar estorno da NE %s: %s",
                self.name,
                exc,
            )
        return None
