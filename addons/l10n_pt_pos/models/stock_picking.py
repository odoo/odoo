from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        # The goods of a PoS sale leave with the receipt or invoice the PoS issues; the picking is linked
        # to its order only once created and validated.
        pickings = super(StockPicking, self.with_context(l10n_pt_pos_sale=True))._create_picking_from_pos_order_lines(
            location_dest_id, lines, picking_type, partner=partner,
        )
        return pickings.with_env(self.env)

    def _l10n_pt_documented_elsewhere(self):
        # A PoS sale is documented by its receipt or invoice: its picking is not reported as leaving
        # without a transport document, and issues a GT only if the PoS operation type has an AT series.
        # A delivery shipped later goes through the warehouse's own delivery type.
        if self.env.context.get('l10n_pt_pos_sale'):
            return self
        return super()._l10n_pt_documented_elsewhere() | self.filtered(lambda p: p.pos_order_id or p.pos_session_id)
