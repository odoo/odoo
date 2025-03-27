from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_sale_key(self, base_line):
        res = super()._get_sale_key(base_line)
        if self.config_id.company_id.l10n_in_is_gst_registered:
            res.update({
                'uom_id': base_line['uom_id'].id,
                'l10n_in_hsn_code': base_line['l10n_in_hsn_code'],
            })
        return res

    def _get_sale_vals(self, key, sale_vals):
        res = super()._get_sale_vals(key, sale_vals)
        if self.config_id.company_id.l10n_in_is_gst_registered:
            res.update({
                'l10n_in_hsn_code': key['l10n_in_hsn_code'],
                'product_uom_id': key['uom_id'],
            })
        return res
