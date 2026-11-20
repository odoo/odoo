from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_picking_default_values_based_on(self, picking):
        # EXTENDS 'stock'
        values = super()._prepare_picking_default_values_based_on(picking)
        if picking.is_greek_company:
            values.update({
                'l10n_gr_edi_move_purpose': '5',  # Return
                # The goods travel back: they are loaded where they were delivered, and the other way around
                'l10n_gr_edi_loading_address_street': picking.l10n_gr_edi_delivery_address_street,
                'l10n_gr_edi_loading_address_number': picking.l10n_gr_edi_delivery_address_number,
                'l10n_gr_edi_loading_address_zip': picking.l10n_gr_edi_delivery_address_zip,
                'l10n_gr_edi_loading_address_city': picking.l10n_gr_edi_delivery_address_city,
                'l10n_gr_edi_delivery_address_street': picking.l10n_gr_edi_loading_address_street,
                'l10n_gr_edi_delivery_address_number': picking.l10n_gr_edi_loading_address_number,
                'l10n_gr_edi_delivery_address_zip': picking.l10n_gr_edi_loading_address_zip,
                'l10n_gr_edi_delivery_address_city': picking.l10n_gr_edi_loading_address_city,
            })
        return values
