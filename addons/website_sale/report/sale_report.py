# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    website_id = fields.Many2one("website", readonly=True)
    is_abandoned_cart = fields.Boolean(string="Abandoned Cart", readonly=True)
    public_categ_ids = fields.Many2many(
        string="eCommerce Categories", related="product_tmpl_id.public_categ_ids"
    )

    def _select_dict(self, table):
        return super()._select_dict(table) | {
            'website_id': table.order_id.website_id.id,
            'is_abandoned_cart': SQL(
                """
                %s <= (timezone('utc', now()) - ((COALESCE(%s, '1.0') || ' hour')::INTERVAL))
                AND %s IS NOT NULL
                AND %s = 'draft'
                AND %s != %s""",
                table.order_id.date_order, table.order_id.website_id.cart_abandoned_delay,
                table.order_id.website_id.id,
                table.order_id.state,
                table.order_id.partner_id, self.env.ref("base.public_partner").id,
            ),
        }

    def _groupby_list(self, table):
        return super()._groupby_list(table) + [table.order_id.website_id.id]
