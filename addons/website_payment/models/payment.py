from openerp import models


class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _inherit = ['payment.acquirer','website.published.mixin']
