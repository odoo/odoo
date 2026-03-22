from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    regime_tributario = fields.Selection(
        [
            ("simples", "Simples Nacional"),
            ("presumido", "Lucro Presumido"),
            ("real", "Lucro Real"),
            ("mei", "MEI"),
        ],
        default="presumido",
    )
    certificado_id = fields.Many2one("br.certificado", ondelete="set null")

    def write(self, vals):
        tracked = "period_lock_date" in vals
        old_dates = {company.id: company.period_lock_date for company in self} if tracked else {}
        result = super().write(vals)
        if tracked:
            for company in self:
                old_date = old_dates.get(company.id)
                new_date = company.period_lock_date
                if old_date != new_date:
                    self.env["br.lock.date.log"].create(
                        {
                            "company_id": company.id,
                            "user_id": self.env.user.id,
                            "date_old": old_date,
                            "date_new": new_date,
                            "reason": "period_lock_date updated",
                        }
                    )
        return result

