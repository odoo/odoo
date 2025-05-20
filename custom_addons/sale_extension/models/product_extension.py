from odoo import fields, models


class ProductExtension(models.Model):
    _inherit = "product.template"

    item_brand = fields.Char(
        string='Marca',
        readOnly=False,
        store=True,
        help='Marca de este producto',
        default=""
    )

    item_model = fields.Char(
        string='Modelo',
        readOnly=False,
        store=True,
        help='Modelo de este producto',
        default=""
    )

    item_delivery_lead = fields.Integer(
        string='Días de entrega',
        readOnly=False,
        store=True,
        help='Tiempo estimado de entrega para este producto en días.',
        default=0
    )

    item_stock = fields.Integer(
        string='Stock',
        readOnly=True,
        store=False,
        help='Stock de este producto',
        default=0
    )

    item_amount = fields.Integer(
        string='Cantidad a fabricar',
        readOnly=False,
        store=True,
        help='Cantidad a fabricar',
        default=0
    )