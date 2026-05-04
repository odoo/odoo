from odoo import models


class WebsiteQuickAddMixin(models.AbstractModel):
    _name = "website.quick.add.mixin"

    def _website_show_quick_add_common(self):
        self.ensure_one()
        if self._is_sold_out() or not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        if not self._get_available_uoms():
            return False
        website = self.env["website"].get_current_website()
        return not (
            website.prevent_sale
            and website._prevent_product_sale(self, not self._get_contextual_price())
        )
