from odoo import api, models


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    @api.model
    def precision_get(self, application):
        stackmap = self.env.cr.cache.get('account_disable_recursion_stack', {})
        if stackmap.get('ignore_discount_precision') and application in ('Discount', 'Product Unit'):
            return 13
        return super().precision_get(application)
