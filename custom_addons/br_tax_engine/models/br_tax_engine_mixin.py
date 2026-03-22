from odoo import fields, models


class BrTaxEngineMixin(models.AbstractModel):
    _name = "br.tax.engine.mixin"
    _description = "Mixin do Motor Tributario BR"

    engine_date = fields.Date()
    regime_tributario = fields.Selection(
        [
            ("simples", "Simples Nacional"),
            ("presumido", "Lucro Presumido"),
            ("real", "Lucro Real"),
            ("mei", "MEI"),
        ]
    )
    tax_engine_mode = fields.Selection(
        [("legacy", "Regime Antigo"), ("dual", "Dual - Transicao 2026"), ("new", "Regime Novo CBS/IBS")],
        default="legacy",
    )

    def _get_applicable_rules(self):
        self.ensure_one()
        rule_model = self.env["br.tax.rule"]
        date = self.engine_date or getattr(self, "invoice_date", False) or fields.Date.context_today(self)
        regime = self.regime_tributario or getattr(self.company_id, "regime_tributario", "presumido")
        if self.tax_engine_mode == "legacy":
            types = ["icms", "ipi", "pis", "cofins", "iss", "irpj", "csll"]
        elif self.tax_engine_mode == "new":
            types = ["cbs", "ibs", "is"]
        else:
            types = ["icms", "ipi", "pis", "cofins", "iss", "irpj", "csll", "cbs", "ibs", "is"]
        rules = rule_model.get_active_rules(self.env, date, regime, tax_types=types)
        grouped = {}
        for rule in rules:
            grouped.setdefault(rule.tax_type, self.env["br.tax.rule"])
            grouped[rule.tax_type] |= rule
        return grouped

