from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _is_exempt_jo_tax(self):
        self.ensure_one()
        cid = self.company_id.id
        exempted_taxes_refs = ['jo_zero_sale_exempted']
        return self in [self.env.ref(f'account.{cid}_{tax_ref}') for tax_ref in exempted_taxes_refs]

    def get_tax_jo_ubl_code(self):
        self.ensure_one()
        if self._is_exempt_jo_tax():
            return "Z"
        if self.amount:
            return "S"
        return "O"

    def get_jo_tax_type(self):
        self.ensure_one()
        if self.amount_type == 'percent':
            return 'general'
        elif self.amount_type == 'fixed':
            return 'special'
