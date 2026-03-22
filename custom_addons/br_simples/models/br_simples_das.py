from odoo import api, fields, models


class BrSimplesDas(models.Model):
    _name = "br.simples.das"
    _description = "Apuracao de DAS"

    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    period = fields.Date(required=True)
    rbt12 = fields.Monetary(currency_field="currency_id")
    receita_mes = fields.Monetary(currency_field="currency_id")
    aliquota_efetiva = fields.Float(compute="_compute_totals", store=True)
    valor_das = fields.Monetary(compute="_compute_totals", store=True, currency_field="currency_id")
    fator_r = fields.Float()
    state = fields.Selection([("rascunho", "Rascunho"), ("calculado", "Calculado"), ("pago", "Pago")], default="rascunho")
    account_payment_id = fields.Many2one("account.payment")
    anexo_id = fields.Many2one("br.simples.anexo", ondelete="restrict")
    aliquota_id = fields.Many2one("br.simples.aliquota", ondelete="restrict")

    @api.depends("rbt12", "receita_mes", "aliquota_id")
    def _compute_totals(self):
        for record in self:
            if record.aliquota_id and record.rbt12:
                record.aliquota_efetiva = record.aliquota_id.calcular_aliquota_efetiva(record.rbt12)
                record.valor_das = record.receita_mes * record.aliquota_efetiva
            else:
                record.aliquota_efetiva = 0.0
                record.valor_das = 0.0

