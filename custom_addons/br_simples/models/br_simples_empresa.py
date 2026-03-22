from odoo import fields, models


class BrSimplesEmpresa(models.Model):
    _name = "br.simples.empresa"
    _description = "Empresa no Simples Nacional"

    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    data_opcao = fields.Date()
    anexo_principal = fields.Many2one("br.simples.anexo", ondelete="restrict")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    rbt12 = fields.Monetary(currency_field="currency_id")
    sublimite_estadual = fields.Monetary(currency_field="currency_id")
    state = fields.Selection(
        [("ativa", "Ativa"), ("suspensa", "Suspensa"), ("excluida", "Excluida")],
        default="ativa",
    )

    _sql_constraints = [("br_simples_empresa_company_unique", "unique(company_id)", "A empresa ja possui cadastro do Simples.")]

