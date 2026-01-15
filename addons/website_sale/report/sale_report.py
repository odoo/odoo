# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    website_id = fields.Many2one('website', readonly=True)
    is_abandoned_cart = fields.Boolean(string="Abandoned Cart", readonly=True)
    public_categ_ids = fields.Many2many(
        string="eCommerce Categories",
        related='product_tmpl_id.public_categ_ids',
    )

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['website_id'] = "s.website_id"
        res['is_abandoned_cart'] = """
            s.date_order <= (timezone('utc', now()) - ((COALESCE(w.cart_abandoned_delay, '1.0') || ' hour')::INTERVAL))
            AND s.website_id IS NOT NULL
            AND s.state = 'draft'
            AND s.partner_id != %s""" % self.env.ref('base.public_partner').id
        return res

    def _from_sale(self):
        res = super()._from_sale()
        res += """
            LEFT JOIN website w ON w.id = s.website_id"""
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.website_id,
            w.cart_abandoned_delay"""
        return res
