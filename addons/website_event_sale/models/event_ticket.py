from odoo import models


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    def _show_discount(self):
        """Determine if the discount should be shown on the website for this ticket."""
        self.ensure_one()
        if not self.price:
            return False

        product_sudo = self.product_id.sudo()
        pricelist = product_sudo.product_tmpl_id._get_contextual_pricelist()
        if not pricelist:
            return False

        rule_id = pricelist._get_product_rule(
            product=product_sudo,
            quantity=1.0,
        )
        pricelist_item = self.env['product.pricelist.item'].browse(rule_id)
        return pricelist_item._show_discount_on_shop() and (self.price - self.price_reduce) > 0
