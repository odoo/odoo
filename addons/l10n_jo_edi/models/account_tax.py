from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _is_exempt_jo_tax(self):
        self.ensure_one()
        cid = self.company_id.id
        exempted_taxes_refs = ['jo_zero_sale_exempted']
        return self in [self.env.ref(f'account.{cid}_{tax_ref}') for tax_ref in exempted_taxes_refs]
