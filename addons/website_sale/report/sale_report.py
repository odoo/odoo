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

    def _get_select_fields(self):
        """Add website_id and is_abandoned_cart to SELECT fields."""
        fields = super()._get_select_fields()
        fields['website_id'] = "o.website_id"
        fields['is_abandoned_cart'] = f"""
            o.date_order <= (timezone('utc', now()) - ((COALESCE(w.cart_abandoned_delay, '1.0') || ' hour')::INTERVAL))
            AND o.website_id IS NOT NULL
            AND o.state = 'draft'
            AND o.partner_id != {self.env.ref('base.public_partner').id}"""
        return fields

    def _get_from_tables(self):
        """Add website table JOIN to FROM clause."""
        tables = super()._get_from_tables()
        tables.append(("website", "w", "LEFT JOIN", "w.id = o.website_id"))
        return tables

    def _get_group_by_fields(self):
        """Add website_id and cart_abandoned_delay to GROUP BY fields."""
        fields = super()._get_group_by_fields()
        fields.extend([
            "o.website_id",
            "w.cart_abandoned_delay",
        ])
        return fields
