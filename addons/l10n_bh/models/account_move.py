from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_base_document_title(self):
        self.ensure_one()

        if (
            self.company_id.country_code == 'BH'
            and self.company_id.vat
            and self.state == 'posted'
            and self.move_type == 'out_invoice'
            and not self.is_debit_note()
        ):
            if not self.commercial_partner_id.vat:
                return self.env._("Simplified Tax Invoice")
            return self.env._("Tax Invoice")

        return super()._get_base_document_title()
