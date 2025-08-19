from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for order in self:
            if order.partner_id.name and self.env.context.get('formatted_display_name'):
                order.display_name = f"{order.name} \t --{order.partner_id.name}--"
