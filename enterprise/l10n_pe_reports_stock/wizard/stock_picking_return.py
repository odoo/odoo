from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_picking_default_values(self):
        # EXTENDS stock
        vals = super()._prepare_picking_default_values()
        if self.picking_id.country_code != 'PE':
            return vals

        l10n_pe_operation_type = {
            'outgoing': '24',
            'incoming': '25',
            'internal': '21',
        }.get(self.picking_id.picking_type_code)

        if l10n_pe_operation_type:
            vals['l10n_pe_operation_type'] = l10n_pe_operation_type
        return vals
