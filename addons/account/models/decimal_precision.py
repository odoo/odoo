from odoo import models

class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    def precision_get(self, application):
        stackmap = self.env.cr.cache.get('account_disable_recursion_stack', {})
        if stackmap.get('ignore_discount_precision'):
            if application == 'Discount':
                return 13
            if application == 'Product Unit of Measure':
                return 10
        return super().precision_get(application)
