# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    amazon_item_ref = fields.Char(help="The Amazon-defined item reference.")
    amazon_offer_id = fields.Many2one(
        string="Amazon Offer", comodel_name='amazon.offer', ondelete='set null'
    )

    _sql_constraints = [(
        'unique_amazon_item_ref',
        'UNIQUE(amazon_item_ref)',
        "There can only exist one sale order line for a given Amazon Item Reference."
    )]
