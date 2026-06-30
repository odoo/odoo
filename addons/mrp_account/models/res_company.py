from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_valuation_product_domain(self):
        return super()._get_valuation_product_domain() + [('is_kits', '=', False)]
