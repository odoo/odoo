from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Product(models.Model):
    _inherit = 'product.product'

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super()._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        Move = self.env['stock.move'].with_context(active_test=False)

        domain_quant_loc, domain_move_in_loc, _ = self._get_domain_locations()
        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc + [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))]

        # fetch remaining_qty
        incoming_moves = Move.read_group(domain_move_in, ['product_id', 'remaining_qty:sum'], ['product_id'])
        incoming_map = {m['product_id'][0]: m['remaining_qty'] for m in incoming_moves}

        for product in self:
            if product.id in res:
                res[product.id]['incoming_qty'] = incoming_map.get(product.id, 0.0)
                res[product.id]['virtual_available'] = res[product.id]['qty_available'] + res[product.id]['incoming_qty'] - res[product.id]['outgoing_qty']

        return res
