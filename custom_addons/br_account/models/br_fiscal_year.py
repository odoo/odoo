from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BrFiscalYear(models.Model):
    _name = "br.fiscal.year"
    _description = "Exercicio Fiscal BR"
    _order = "date_from desc"

    # ref: public_sector/gov_account_fiscal_year/models/account_fiscal_year.py
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection([("draft", "Aberto"), ("done", "Fechado")], default="draft")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError("A data inicial deve ser anterior ou igual a data final.")

    @api.constrains("date_from", "date_to", "company_id")
    def _check_overlap(self):
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("date_from", "<=", record.date_to),
                ("date_to", ">=", record.date_from),
            ]
            if record.date_from and record.date_to and self.search_count(domain):
                raise ValidationError("Nao e permitido sobrepor exercicios fiscais na mesma empresa.")

    @api.model
    def get_fiscal_year(self, company_id, date):
        return self.search(
            [("company_id", "=", company_id), ("date_from", "<=", date), ("date_to", ">=", date)],
            limit=1,
        )

