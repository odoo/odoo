from odoo import models, fields, api, _
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

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        # Set base domain for same default_code
        domain = [('default_code', '=', self.default_code)]

        # Exclude current record during editing
        if self.id:
            domain.append(('id', '!=', self.id))

        # Check if any existing product has same default_code AND same tenant_id
        if self.tenant_id:
            domain.append(('tenant_id', '=', self.tenant_id.id))

        # If such a product exists — show warning
        if self.env['product.product'].search(domain, limit=1):
            return {
                'warning': {
                    'title': _("Note:"),
                    'message': _("The Internal Reference '%s' already exists for this tenant." % self.default_code),
                }
            }
