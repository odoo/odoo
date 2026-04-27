# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopee_order_ref = fields.Char(
        string="Shopee Reference",
        help="The Shopee-defined order reference.",
        readonly=True,
        copy=False,
    )
    shopee_shop_id = fields.Many2one(
        string="Shopee Shop",
        help="The Shopee shop from which the order was placed.",
        comodel_name='shopee.shop',
        readonly=True,
    )
    shopee_fulfillment_type = fields.Selection(
        string="Shopee Fulfillment Type",
        selection=[
            ('fbm', "Fulfillment by Merchant"),
            ('fbs', "Fulfillment by Shopee"),
            ('hybrid', "Fulfillment by Cross Border Seller"),  # FBM sent through Shopee
        ],
    )
    shopee_delivery_status = fields.Selection(
        string="Shopee Status",
        help="The status of the delivery order on Shopee:\n"
             "- Ready to Ship: Seller can arrange shipment.\n"
             "- Shipment Arranged: Seller has arranged shipment online and got tracking number from 3PL.\n"
             "- Shipped: The parcel has been dropped at 3PL or picked up by 3PL.\n"
             "- Cancelled: The order has been cancelled.\n"
             "- Pickup Failed: 3PL parcel pickup failed. Need to rearrange shipment.",
        selection=[
            ('draft', "Ready to Ship"),
            ('confirmed', "Shipment Arranged"),
            ('done', "Shipped"),
            ('cancelled', "Cancelled"),
            ('error', "Pickup Failed"),
        ],
        readonly=True,
        default='draft',
    )

    _sql_constraints = [(
        'unique_shopee_order_ref_shopee_shop_id',
        'UNIQUE(shopee_order_ref, shopee_shop_id)',
        "There can only exist one sale order for a given Shopee Order Reference per Shop.",
    )]
