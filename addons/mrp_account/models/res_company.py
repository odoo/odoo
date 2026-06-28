from odoo import models, fields
from odoo.addons.base.models.res_company import company_default_for


class ResCompany(models.Model):
    _inherit = 'res.company'

    stock_account_production_cost_id = fields.Many2one(
        'account.account',
        string='Production Account',
        **company_default_for('stock_account_production_cost_id', 'product.category', 'property_stock_account_production_cost_id'),
        check_company=True,
    )

    def _get_valuation_product_domain(self):
        return super()._get_valuation_product_domain() + [('is_kits', '=', False)]
