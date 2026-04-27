from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_mx_edi_get_cfdi_line_name(self):
        self.ensure_one()
        if self.product_id.display_name:
            if self.name:
                if self.product_id.display_name in self.name or self.name in self.product_id.display_name:
                    return self.name
                return f"{self.product_id.display_name} {self.name}"
            return self.product_id.display_name
        return self.name

    def _get_product_unspsc_code(self):
        self.ensure_one()

        return (
            "84111506"
            if self in self._get_downpayment_lines()
            else self.product_id.unspsc_code_id.code
        )

    def _get_uom_unspsc_code(self):
        self.ensure_one()

        return (
            "ACT"
            if self in self._get_downpayment_lines()
            else self.product_uom_id.unspsc_code_id.code
        )

    def _filter_aml_lot_valuation(self):
        # EXTENDS account
        return super()._filter_aml_lot_valuation() and not self.move_id.l10n_mx_edi_cfdi_cancel_id
