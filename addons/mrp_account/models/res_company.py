from odoo import models, fields
from odoo.addons.base.models.res_company import company_default_for


class ResCompany(models.Model):
<<<<<<< 7e8e1b64328d566d09e102cad5abca63479b6531
    _inherit = 'res.company'

    stock_account_production_cost_id = fields.Many2one(
        'account.account',
        string='Production Account',
        **company_default_for('stock_account_production_cost_id', 'product.category', 'property_stock_account_production_cost_id'),
        check_company=True,
    )

    def _get_valuation_product_domain(self):
        return super()._get_valuation_product_domain() + [('is_kits', '=', False)]
||||||| fcca50363798ab5c4dcdafef9d82ed3c02d0a4c1
    _inherit = "res.company"

    def _get_valuation_product_domain(self):
        return super()._get_valuation_product_domain() + [('is_kits', '=', False)]
=======
    _inherit = "res.company"
>>>>>>> 1cdb0cc33cca45d736d7ea617e39cdcda4f5abc9
