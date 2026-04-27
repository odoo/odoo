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
            if len({'code_mapping_ids/company_id', 'code_mapping_ids/code'} & set(fields)) == 1:
                raise UserError(_(
                    "You must provide both the `code_mapping_ids/company_id` "
                    "and the `code_mapping_ids/code` columns."
                ))

            # If the accounts are referenced by their code, retrieve database IDs for them.
            if not {'id', '.id'} & set(fields) and 'code' in fields:

                accounts = self.search_fetch(
                    domain=self._check_company_domain(self.env.company),
                    field_names=['code'],
                )
                account_id_by_code = {account.code: account.id for account in accounts}

                fields.append('.id')
                code_index = fields.index('code')
                for row in data:
                    account_code = row[code_index]
                    row.append(account_id_by_code.get(account_code, False))

        return super().load(fields, data)
