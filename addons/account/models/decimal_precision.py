from odoo import models
from odoo.addons import base

class DecimalPrecision(models.Model, base.DecimalPrecision):

    def precision_get(self, application):
        if application == 'Discount' and self.env.context.get('ignore_discount_precision'):
            return 100
        return super().precision_get(application)
