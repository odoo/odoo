from odoo import fields, models

class ResPartnerExtension(models.Model):
    _inherit = 'res.partner'

    # item_delivery_lead = fields.Integer(
    #     string='Días de entrega',
    #     readOnly=False,
    #     store=True,
    #     help='Tiempo estimado de entrega para este producto en días.',
    #     default=0
    # )