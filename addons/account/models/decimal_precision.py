from odoo import models

class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    def precision_get(self, application):
        stackmap = self.env.cr.cache.get('account_disable_recursion_stack', {})
        if application in ('Discount', 'Product Unit of Measure') and stackmap.get('ignore_discount_precision'):
            return 13
        return super().precision_get(application)
