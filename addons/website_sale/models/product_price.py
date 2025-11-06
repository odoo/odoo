# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ProductPrice(models.Model):
    _name = 'product.price'
    _description = "Product Variant Price"
    _order = 'pricelist_id, price desc'

    product_product_id = fields.Many2one(
        comodel_name='product.product', ondelete='cascade', required=True
    )
    product_tmpl_id = fields.Many2one(
        related='product_product_id.product_tmpl_id', store=True, index=True
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one(comodel_name='res.company', required=True)
    pricelist_item_id = fields.Many2one(comodel_name='product.pricelist.item')
    price = fields.Float()


    # Caching mechanism (technical field)
    cache_expiry = fields.Date(
        readonly=True, default=lambda _self: fields.Date.today()-relativedelta(days=1)
    )

    _unique_product_pricelist = models.Constraint(
        'unique(product_product_id, pricelist_id)',
        'Only one product price allowed per product and pricelist!',
    )

    @api.model
    def _is_enabled(self):
        """Check if the cron is enabled and the product pricelist feature is enabled."""
        cron_enabled = self.env.ref(
            'website_sale.ir_cron_calculate_product_price', raise_if_not_found=False
        ).sudo().active
        pl_enabled = self.env['res.groups']._is_feature_enabled('product.group_product_pricelist')
        return pl_enabled and cron_enabled

    def _invalidate(self):
        self.cache_expiry = fields.Date.today() - relativedelta(days=1)

    @api.model
    def _recompute_prices_in_pricelists(self, pricelist_ids):
        """Invalidate the prices of the given pricelist."""
        if not pricelist_ids:
            return
        self.search([('pricelist_id', 'in', pricelist_ids)])._invalidate()
        # self.env.cr.execute(
        #     """
        #     UPDATE product_price AS ppp
        #     SET cache_expiry = CURRENT_DATE - INTERVAL '1 day'
        #     WHERE ppp.pricelist_id IN %s
        #     """, [tuple(pricelist_ids)]
        # )
        self._run_cron_calculate_price_for_pricelist_products()

    @api.model
    def _recompute_prices_based_on_cost(self, product_ids):
        """Invalidate the prices of the products with the corresponding pricelist rule based on the
        cost price."""
        if not product_ids:
            return
        # self.search([
        #     ('product_product_id', 'in', product_ids),
        #     ('pricelist_item_id.base', '=', 'standard_price')
        # ])._invalidate()
        self.env.cr.execute(
            """
            UPDATE product_price AS ppp
            SET cache_expiry = CURRENT_DATE - INTERVAL '1 day'
            FROM product_pricelist_item AS pli
            WHERE ppp.pricelist_item_id = pli.id
              AND ppp.product_product_id IN %s
              AND pli.base = 'standard_price';
            """, [tuple(product_ids)]
        )
        self._run_cron_calculate_price_for_pricelist_products()

    @api.model
    def _recompute_prices_based_on_sale_price(self, product_ids):
        """Invalidate the prices of the products with no pricelist rule or a pricelist rule based on
        the sale price."""
        if not product_ids:
            return
        # self.search([
        #     ('product_product_id', 'in', product_ids),
        #     ('pricelist_item_id.base', '!=', 'standard_price')
        # ])._invalidate()
        self.env.cr.execute(
            """
            UPDATE product_price AS ppp
            SET cache_expiry = CURRENT_DATE - INTERVAL '1 day'
            WHERE ppp.product_product_id IN %s
              AND (
                    ppp.pricelist_item_id IS NULL
                    OR pricelist_item_id IN (
                        SELECT ppi.id
                        FROM product_pricelist_item AS ppi
                        WHERE ppi.id = ppp.pricelist_item_id AND ppi.base <> 'standard_price')
                  )
            """, [tuple(product_ids)]
        )
        self._run_cron_calculate_price_for_pricelist_products()

    @api.model
    def _cron_calculate_product_price(self, batch_size=100):
        """Recompute the obsolete prices of all products."""
        if not self._is_enabled():
            return
        today = fields.Date.today()
        domain = [('cache_expiry', '<', today)]
        prices_to_update_by_pricelist = self._read_group(
            domain, groupby=['pricelist_id'], aggregates=['id:recordset']
        )
        self.env['ir.cron']._commit_progress(remaining=self.search_count(domain))
        for pricelist_id, prices_to_update in prices_to_update_by_pricelist:
            for offset in range(0, len(prices_to_update), batch_size):
                prices_batch = prices_to_update[offset : offset + batch_size]
                res = pricelist_id._compute_price_rule(prices_batch.product_product_id, 1)
                for product_price in prices_batch:
                    product_id = product_price.product_product_id.id
                    product_price.price, product_price.pricelist_item_id = res[product_id]
                prices_batch.cache_expiry = today + relativedelta(days=1)
                remaining_time = self.env['ir.cron']._commit_progress(processed=len(prices_batch))
                if not remaining_time:
                    break

    @api.model
    def _run_cron_calculate_price_for_pricelist_products(self):
        """Trigger the cron to recompute the price of all products."""
        if self._is_enabled():
            self.env.ref('website_sale.ir_cron_calculate_product_price').sudo()._trigger()
