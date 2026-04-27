#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_fields_stock_barcode(self):
        fields = super()._get_fields_stock_barcode()
        fields.append('check_state')
        return fields

    def _is_checkable_from_context(self):
        if self.env.context.get('barcode_trigger'):
            if not self.picked:
                return False
        return super()._is_checkable_from_context()
