from odoo import fields, models
from odoo.tools import float_compare

from odoo.addons.l10n_ge_edi.tools.rsge_client import get_rsge_vat_type


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ge_edi_line_id = fields.Char(string="RS.ge Line Id", readonly=True, copy=False)

    def _l10n_ge_edi_drg_amount(self):
        self.ensure_one()
        chart_template = self.env["account.chart.template"].with_company(self.company_id)
        exempt_group = chart_template.ref("ge_tax_group_vat_exempt", raise_if_not_found=False)
        zero_rated_group = chart_template.ref("ge_tax_group_vat_0", raise_if_not_found=False)
        tax_group = self.tax_ids[:1].tax_group_id
        if tax_group == exempt_group:
            return -1
        if tax_group == zero_rated_group:
            return 0
        return self.price_total - self.price_subtotal

    def _l10n_ge_edi_matches_rsge(self, remote_line):
        self.ensure_one()
        quantity_digits = self.env["decimal.precision"].precision_get("Product Unit")
        currency = self.currency_id
        quantity = float(remote_line.get("G_NUMBER", "nan"))
        full_amount = float(remote_line.get("FULL_AMOUNT", "nan"))
        return (
            remote_line.get("GOODS") == (self.name or self.product_id.display_name)
            and remote_line.get("G_UNIT") == (self.product_uom_id.name or "pcs")
            and not float_compare(quantity, self.quantity, precision_digits=quantity_digits)
            and not currency.compare_amounts(full_amount, self.price_total)
            # RS.ge recomputes DRG_AMOUNT from FULL_AMOUNT, so only its VAT_TYPE is ours to compare
            and remote_line.get("VAT_TYPE") == get_rsge_vat_type(self._l10n_ge_edi_drg_amount())
        )
