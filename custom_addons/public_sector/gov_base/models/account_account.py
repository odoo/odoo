from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    natureza_pcasp = fields.Selection(
        selection=[
            ("ativo", "Ativo"),
            ("passivo", "Passivo"),
            ("vpa", "VPA - Variação Patrimonial Aumentativa"),
            ("vpd", "VPD - Variação Patrimonial Diminutiva"),
            ("controle", "Controle"),
        ],
        string="Natureza PCASP",
    )
    codigo_pcasp = fields.Char(
        string="Código PCASP",
        size=20,
        help="Código completo na hierarquia PCASP ex: 1.1.1.1.01.01",
    )

