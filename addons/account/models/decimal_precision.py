from odoo import models

class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    def precision_get(self, application):
        if application == 'Discount' and self.env.context.get('ignore_discount_precision'):
            return 100
        return super().precision_get(application)
