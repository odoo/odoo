from odoo import _, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def unlink(self):
        for id_, xmlids in self._get_external_ids():
            if 'product_product_fixed_cost' in xmlids:
                raise UserError(_("This product cannot be removed. It is required by the hr_expense module."))
        return super().unlink()
