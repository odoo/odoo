# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError

class AccountAccount(models.Model):
    _inherit = ["account.account"]

    @api.model
    def load(self, fields, data):
        """ Overridden to add an id to a row to update an account if it already exists
        instead of trying to create it.
        """
        if "import_file" in self.env.context:
            if 'code' not in fields:
                raise UserError(_("The import file must contain the 'code' column"))
            accounts_codes_ids = {}
            fields.append(".id")
            code_index = fields.index("code")
            account_codes = self.search_read(
                domain=self._check_company_domain(self.env.company),
                fields=["code"]
            )
            for account in account_codes:
                accounts_codes_ids[account["code"]] = account["id"]
            for row in data:
                account_code = row[code_index]
                account_id = accounts_codes_ids.get(account_code)
                if account_id:
                    row.append(account_id)
        return super().load(fields, data)
