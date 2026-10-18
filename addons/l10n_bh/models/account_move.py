from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_gcc_get_invoice_title(self):
        self.ensure_one()
        if (
            self.company_id.country_code != 'BH'
            or not self.company_id.vat
            or ('debit_origin_id' in self._fields and self.debit_origin_id)
        ):
            return super()._l10n_gcc_get_invoice_title()

        if not self.commercial_partner_id.vat:
            return self.env._('Simplified Tax Invoice')

        return self.env._('Tax Invoice')
