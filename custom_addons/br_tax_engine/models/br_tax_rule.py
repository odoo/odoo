from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BrTaxRule(models.Model):
    _name = "br.tax.rule"
    _description = "Regra Tributaria BR"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    tax_type = fields.Selection(
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
        ],
        required=True,
    )
    regime_type = fields.Selection(
        [
            ("simples", "Simples Nacional"),
            ("presumido", "Lucro Presumido"),
            ("real", "Lucro Real"),
            ("mei", "MEI"),
            ("all", "Todos"),
        ],
        required=True,
        default="all",
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    rate = fields.Float(required=True)
    active = fields.Boolean(default=True)

    @api.constrains("date_from", "date_to", "tax_type", "regime_type", "active")
    def _check_overlap(self):
        for record in self.filtered("active"):
            upper_bound = record.date_to or fields.Date.to_date("2099-12-31")
            domain = [
                ("id", "!=", record.id),
                ("active", "=", True),
                ("tax_type", "=", record.tax_type),
                ("regime_type", "=", record.regime_type),
                ("date_from", "<=", upper_bound),
                "|",
                ("date_to", "=", False),
                ("date_to", ">=", record.date_from),
            ]
            if self.search_count(domain):
                raise ValidationError("Nao pode haver sobreposicao de regras para o mesmo imposto e regime.")

    @classmethod
    def get_active_rules(cls, env, date, regime, tax_types=None):
        domain = [
            ("date_from", "<=", date),
            "|",
            ("date_to", "=", False),
            ("date_to", ">=", date),
            ("regime_type", "in", [regime, "all"]),
            ("active", "=", True),
        ]
        if tax_types:
            domain.append(("tax_type", "in", tax_types))
        return env["br.tax.rule"].search(domain)
