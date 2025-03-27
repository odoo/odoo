from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_product_aml_dict(self, base_line_vals, update_base_line_vals, rate, sign):
        res = super()._prepare_product_aml_dict(base_line_vals, update_base_line_vals, rate, sign)
        if self.company_id.account_fiscal_country_id.code == 'IN':
            res.update({
                'l10n_in_hsn_code': base_line_vals['l10n_in_hsn_code'],
            })
        return res
