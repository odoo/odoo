import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    """Extend stock.move to trigger WooCommerce inventory push after moves are done.

    When a stock move is validated (state = 'done'), we check if any of the
    affected products are bound to a WooCommerce backend and push updated
    stock levels immediately.

    This provides real-time inventory accuracy without waiting for the cron job.
    The cron job remains the authoritative full-reconciliation pass.

    Performance: we only push products that are actually WooCommerce-bound,
    and we deduplicate product IDs so bulk moves trigger one push per product.
    """

    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """Override to trigger inventory push after moves complete."""
        result = super()._action_done(cancel_backorder=cancel_backorder)

        # Collect product.product IDs from all moves that just became 'done'
        done_moves = self.filtered(lambda m: m.state == 'done')
        if not done_moves:
            return result

        product_ids = list({m.product_id.id for m in done_moves if m.product_id})
        if not product_ids:
            return result

        # Check if any WooCommerce backends are active and export inventory
        # before hitting the DB for every move — fast path
        backends_exist = self.env['woocommerce.backend'].search_count([
            ('state', '=', 'connected'),
            ('export_inventory', '=', True),
        ])
        if not backends_exist:
            return result

        # Check if any of these products are actually bound to WooCommerce
        # before doing per-product lookups
        bound_count = self.env['woocommerce.product.binding'].search_count([
            ('odoo_id.product_variant_ids', 'in', product_ids),
        ])
        variant_bound_count = self.env['woocommerce.product.variant.binding'].search_count([
            ('odoo_id', 'in', product_ids),
        ])

        if not bound_count and not variant_bound_count:
            return result

        _logger.debug(
            '[WooCommerce] Triggering inventory push for %d product(s) after stock move',
            len(product_ids),
        )

        try:
            self.env['woocommerce.inventory.sync'].push_stock_for_products(product_ids)
        except Exception as exc:
            # Never let inventory push failures block stock move processing
            _logger.error(
                '[WooCommerce] Inventory push after stock move failed: %s', exc, exc_info=True,
            )

        return result
