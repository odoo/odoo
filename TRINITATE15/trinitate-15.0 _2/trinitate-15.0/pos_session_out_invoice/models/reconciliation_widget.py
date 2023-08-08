# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class AccountReconciliation(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        res = super().get_data_for_manual_reconciliation(res_type, res_ids)
        if self._context.get("active_model") == "pos.session":
            query_operating = (
                """
                SELECT
                    aa.code AS account_code,
                    aa.id AS account_id,
                    aa.name AS account_name,
                    aml.operating_unit_id AS operating_unit_id,
                    MAX(aml.write_date) AS max_date
                FROM
                    account_move_line AS aml
                    RIGHT JOIN account_account AS aa ON aa.id = aml.account_id
                    RIGHT JOIN account_account_type AS aat ON aat.id = aa.user_type_id
                WHERE
                    aa.reconcile = True AND aml.operating_unit_id = {default_operating_unit_id}
                    AND aml.full_reconcile_id is null AND move_name != '/'
                GROUP BY aa. code ,aa.id,aa.name, aml.operating_unit_id
                ORDER BY aa.code
            """
            ).format(default_operating_unit_id=self._context.get("default_operating_unit_id"))
            self.env["account.move.line"].flush()
            self.env["account.account"].flush()
            self.env.cr.execute(query_operating, locals())
            account_account_id = self.env["account.account"]
            # Apply ir_rules by filtering out
            rows = self.env.cr.dictfetchall()

            aml_ids = (
                self._context.get("active_ids")
                and self._context.get("active_model") == "account.move.line"
                and tuple(self._context.get("active_ids"))
            )
            ids = [x["account_id"] for x in rows]
            allowed_ids = set(account_account_id.browse(ids).ids)
            rows = [row for row in rows if row["account_id"] in allowed_ids]
            # Keep mode for future use in JS
            if res_type == "account":
                mode = "accounts"
            else:
                mode = "customers" if account_type == "receivable" else "suppliers"

            # Fetch other data

            for row in rows:
                account = account_account_id.browse(row["account_id"])
                currency = account.currency_id or account.company_id.currency_id
                row["currency_id"] = currency.id
                partner_id = None
                rec_prop = (
                    aml_ids
                    and self.env["account.move.line"].browse(aml_ids)
                    or self._get_move_line_reconciliation_proposition(account.id, partner_id)
                )
                row["reconciliation_proposition"] = self._prepare_move_lines(rec_prop, target_currency=currency)
                row["mode"] = mode
                row["company_id"] = account.company_id.id
            return rows
        return res
