from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cinetpay_status = fields.Selection([
        ('PENDING', 'En attente'),
        ('ACCEPTED', 'Accepté'),
        ('REFUSED', 'Refusé'),
        ('CANCELLED', 'Annulé'),
    ], string='Statut Paiement CinetPay', default='PENDING')
