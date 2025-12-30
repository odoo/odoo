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

    def set_missing_hsn_codes_in_pos_orders(self):
        PosOrderLine = self.env['pos.order.line']
        base_domain = [
            ('order_id.session_id', '=', self.id),
            ('l10n_in_hsn_code', '=', False),
            ('tax_ids', '!=', False),
        ]

        # Lines where product already has HSN
        lines_with_product_hsn = PosOrderLine.search(
            base_domain + [('product_id.l10n_in_hsn_code', '!=', False)]
        )
        for line in lines_with_product_hsn:
            line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

        # Lines where product itself is missing HSN
        missing_hsn_lines = PosOrderLine.search(
            base_domain + [('product_id.l10n_in_hsn_code', '=', False)]
        )
        return missing_hsn_lines.mapped('product_id.product_tmpl_id')
