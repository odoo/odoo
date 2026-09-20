from odoo import _, fields, models


class AccountReturn(models.Model):
    _inherit = "account.return"

    def _check_suite_annual_closing(self, check_codes_to_ignore):
        checks = super()._check_suite_annual_closing(check_codes_to_ignore)

        if "check_fixed_assets" not in check_codes_to_ignore:
            domain = [
                ("company_id", "in", self.company_ids.ids),
                ("depreciation_state", "=", "open"),
                (
                    "depreciation_move_ids",
                    "any",
                    [
                        ("date", ">=", fields.Date.to_string(self.date_from)),
                        ("date", "<=", fields.Date.to_string(self.date_to)),
                    ],
                ),
            ]
            fixed_assets_exist = (
                self.env["account.depreciation.board"]
                .sudo()
                .search_count(domain, limit=1)
            )
            if not fixed_assets_exist:
                checks.append(
                    {
                        "name": _("Fixed Assets"),
                        "message": _(
                            "Odoo manages depreciation for your fixed assets. No depreciation was recorded for this period. Ensure assets are properly registered for automatic depreciation calculation."
                        ),
                        "code": "check_fixed_assets",
                        "result": "todo",
                    }
                )
        return checks
