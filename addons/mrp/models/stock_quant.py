from odoo import models, _
from odoo.exceptions import RedirectWarning


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        if self.sudo().product_id.filtered("is_kits"):
            raise RedirectWarning(
                _('You should update the components quantity instead of directly updating the quantity of the kit product.'),
                self.env.ref('stock.action_view_inventory_tree').id,
                _("Return to Inventory"),
            )
        return super().action_apply_inventory()
