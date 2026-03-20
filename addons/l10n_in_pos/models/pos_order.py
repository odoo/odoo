from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _grouping_function(self, line):
        res = super()._grouping_function(line)  # Returns mappingproxy (immutable)
        if self.config_id.company_id.l10n_in_is_gst_registered:
            res = dict(res)  # Convert to mutable dict
            res['l10n_in_hsn_code'] = line.get('l10n_in_hsn_code', '')
            res['product_uom_id'] = line.get('product_uom_id', '')
        return res

    def _prepare_account_move_line_data(self, aggregate=True):
        lines = super()._prepare_account_move_line_data(aggregate)
        if aggregate:
            return lines

        for line in lines:
            move = line.get('account.move.line')
            meta = line.get('metadata')

            if self.config_id.company_id.l10n_in_is_gst_registered and meta:
                pos_line = meta.get('line') if meta else None
                if not pos_line:
                    continue
                move["l10n_in_hsn_code"] = pos_line.l10n_in_hsn_code
                move["product_uom_id"] = pos_line.product_uom_id.id

        return lines
