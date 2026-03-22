from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    tipo_imposto = fields.Selection(
        [
            ("icms", "ICMS"),
            ("ipi", "IPI"),
            ("pis", "PIS"),
            ("cofins", "COFINS"),
            ("iss", "ISS"),
            ("irpj", "IRPJ"),
            ("csll", "CSLL"),
            ("cbs", "CBS"),
            ("ibs", "IBS"),
            ("is", "IS"),
        ]
    )
    cst = fields.Char()
    cfop = fields.Char(size=5)

