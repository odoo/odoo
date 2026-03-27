import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GovAccountConfig(models.Model):
    _name = "gov.account.config"
    _description = "Mapeamento Natureza de Despesa -> Conta Contábil"
    _order = "natureza_despesa"
    _rec_name = "natureza_despesa"

    natureza_despesa = fields.Char(
        string="Natureza da Despesa",
        required=True,
        help=(
            "Codigo da natureza de despesa. "
            "Ex: 3.3.90.39 ou 3.3.90 (prefixo aceito)."
        ),
    )
    descricao = fields.Char(
        string="Descricao",
        help="Descricao da natureza de despesa para referencia.",
    )

    account_despesa_id = fields.Many2one(
        "account.account",
        string="Conta de Despesa (debito NE)",
        required=True,
        ondelete="cascade",
        domain="[('account_type','in',['expense','off_balance'])]",
        help="Conta debitada na emissao da Nota de Empenho.",
    )
    account_empenho_pagar_id = fields.Many2one(
        "account.account",
        string="Conta Empenho a Pagar (credito NE)",
        required=True,
        ondelete="cascade",
        domain="[('account_type','=','liability_current')]",
        help=(
            "Conta creditada na emissao da NE. "
            "Padrao MCASP: 2.1.1.2.01."
        ),
    )
    account_liquidacao_pagar_id = fields.Many2one(
        "account.account",
        string="Conta Liquidacao a Pagar (credito NL)",
        ondelete="cascade",
        domain="[('account_type','=','liability_current')]",
        help=(
            "Conta creditada na liquidacao. "
            "Padrao MCASP: 2.1.1.2.02. "
            "Vazio = usa account_empenho_pagar_id."
        ),
    )
    account_banco_id = fields.Many2one(
        "account.account",
        string="Conta Bancaria (debito OP)",
        ondelete="cascade",
        domain="[('account_type','in',['asset_cash','asset_current'])]",
        help=(
            "Conta debitada no pagamento (Ordem de Pagamento). "
            "Vazio = usa conta bancaria padrao da UG."
        ),
    )

    ug_id = fields.Many2one(
        "res.company",
        string="UG (vazio = padrao global)",
        help=(
            "Vazio = mapeamento global para todas as UGs. "
            "Preenchido = sobrepoe o global para esta UG."
        ),
    )
    active = fields.Boolean(default=True)

    _unique_natureza_ug = models.Constraint(
        "unique(natureza_despesa, ug_id)",
        (
            "Ja existe mapeamento para esta natureza de despesa nesta UG. "
            "Use o mapeamento existente ou crie um especifico para a UG."
        ),
    )

    @api.model
    def get_config(self, natureza_despesa, ug_id=None):
        """
        Retorna o mapeamento mais especifico para natureza e UG.

        Prioridade:
        1) natureza exata + UG
        2) natureza exata + global
        3) prefixo + UG
        4) prefixo + global
        """
        if not natureza_despesa:
            return None

        natureza = natureza_despesa.strip()
        candidatos = [natureza]
        partes = natureza.split(".")
        for n in range(len(partes) - 1, 0, -1):
            candidatos.append(".".join(partes[:n]))

        for codigo in candidatos:
            if ug_id:
                cfg_ug = self.search(
                    [
                        ("natureza_despesa", "=", codigo),
                        ("ug_id", "=", ug_id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if cfg_ug:
                    return cfg_ug

            cfg_global = self.search(
                [
                    ("natureza_despesa", "=", codigo),
                    ("ug_id", "=", False),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if cfg_global:
                return cfg_global

        return None

    @api.model
    def get_accounts(self, natureza_despesa, ug_id=None):
        """
        Retorna as contas mapeadas para a natureza informada.
        Sempre retorna dict, mesmo sem mapeamento.
        """
        cfg = self.get_config(natureza_despesa, ug_id)
        if not cfg:
            _logger.warning(
                "GRP Contabil: sem mapeamento para natureza %s / UG %s",
                natureza_despesa,
                ug_id,
            )
            return {
                "despesa": None,
                "empenho_pagar": None,
                "liquidacao_pagar": None,
                "banco": None,
                "config": None,
            }

        return {
            "despesa": cfg.account_despesa_id or None,
            "empenho_pagar": cfg.account_empenho_pagar_id or None,
            "liquidacao_pagar": cfg.account_liquidacao_pagar_id or cfg.account_empenho_pagar_id or None,
            "banco": cfg.account_banco_id or None,
            "config": cfg,
        }
