from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # `fiscalyear_lock_date` already exists in core `account`.
    # It is intentionally not redeclared in this module.

    def _find_fiscal_year_for_date(self, dt):
        self.ensure_one()
        date_value = fields.Date.to_date(dt) if dt else fields.Date.context_today(self)
        return self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_value),
                ("date_to", ">=", date_value),
                ("active", "=", True),
            ],
            order="date_from desc",
            limit=1,
        )

