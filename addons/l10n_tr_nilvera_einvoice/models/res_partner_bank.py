from odoo import models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def _find_or_create_bank_account(self, account_number, partner, company, *, allow_company_account_creation=False, extra_create_vals=None):
        if self.env.context.get("parse_for_ubl_tr"):
            allow_company_account_creation = True
        return super()._find_or_create_bank_account(
            account_number,
            partner,
            company,
            allow_company_account_creation=allow_company_account_creation,
            extra_create_vals=extra_create_vals,
        )
