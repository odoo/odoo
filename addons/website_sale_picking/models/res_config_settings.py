from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    picking_site_ids = fields.Many2many(
        'delivery.carrier',
        related='website_id.picking_site_ids',
        readonly=False
    )

    default_picking_product_id = fields.Many2one('product.product',
                                                 default_model='product.product',
                                                 default=lambda self: self.env.ref('website_sale_picking.onsite_delivery_product'),
                                                 readonly=True)
