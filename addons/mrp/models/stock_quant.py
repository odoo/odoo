from odoo import models, _
from odoo.exceptions import RedirectWarning


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        bom_kits = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')
        for record in self:
            if record.product_id in bom_kits:
                raise RedirectWarning(
                    _('You should update the components quantity instead of directly updating the quantity of the kit product.'),
                    self.env.ref('stock.action_view_inventory_tree').id,
                    _("Return to Inventory"),
                )
        return super().action_apply_inventory()
