from odoo import fields, models


class BrSimplesCalcularDasWizard(models.TransientModel):
    _name = "br.simples.calcular.das"
    _description = "Wizard de Calculo DAS"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    period = fields.Date(required=True)
    receita_mes = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")

    def action_calcular(self):
        self.ensure_one()
        empresa = self.env["br.simples.empresa"].search([("company_id", "=", self.company_id.id)], limit=1)
        anexo = empresa.anexo_principal
        aliquota = self.env["br.simples.aliquota"].search(
            [
                ("anexo_id", "=", anexo.id),
                ("receita_min", "<=", empresa.rbt12),
                ("receita_max", ">=", empresa.rbt12),
            ],
            limit=1,
        )
        return self.env["br.simples.das"].create(
            {
                "company_id": self.company_id.id,
                "period": self.period,
                "rbt12": empresa.rbt12,
                "receita_mes": self.receita_mes,
                "fator_r": 0.0,
                "state": "calculado",
                "anexo_id": anexo.id,
                "aliquota_id": aliquota.id,
            }
        )

