import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WooCommerceInventorySync(models.Model):
    """Pushes Odoo stock levels to WooCommerce.

    Triggered by:
    1. Cron job (_cron_export_inventory) — full push for all bound products
    2. Stock move post hook (_on_stock_move_done) — incremental push for affected SKUs
    """

    _name = 'woocommerce.inventory.sync'
    _description = 'WooCommerce Inventory Sync'

    # ── Cron Entry Point ──────────────────────────────────────────────────────

    @api.model
    def _run_export(self, backend):
        """Push stock levels for all WooCommerce-bound products to WooCommerce."""
        if not backend.warehouse_id:
            _logger.warning(
                '[WooCommerce] No warehouse configured for backend %s — skipping inventory export.',
                backend.name,
            )
            return

        client = backend._get_client()
        location = backend.warehouse_id.lot_stock_id

        # Fetch all product bindings for this backend
        bindings = self.env['woocommerce.product.binding'].search([
            ('backend_id', '=', backend.id),
            ('sync_state', '=', 'synced'),
        ])

        _logger.info(
            '[WooCommerce] Starting inventory export for backend %s (%d products)',
            backend.name, len(bindings),
        )

        pushed = errors = skipped = 0

        for binding in bindings:
            template = binding.odoo_id
            if template.type != 'product':
                # Only push storable products
                skipped += 1
                continue

            try:
                result = self._push_template_stock(client, backend, binding, template, location)
                if result:
                    pushed += 1
            except Exception as exc:
                errors += 1
                _logger.error(
                    '[WooCommerce] Inventory push failed for product #%s: %s',
                    binding.external_id, exc, exc_info=True,
                )

        _logger.info(
            '[WooCommerce] Inventory export complete for %s: %d pushed, %d skipped, %d errors',
            backend.name, pushed, skipped, errors,
        )

    @api.model
    def _push_template_stock(self, client, backend, binding, template, location):
        """Push stock for a single product template binding.

        For simple products: push template's total stock.
        For variable products: push each variant's stock.

        :returns: True if at least one push was made
        """
        wc_type = binding.wc_type or 'simple'
        pushed_any = False

        if wc_type == 'variable':
            # Push per-variant stock
            variant_bindings = self.env['woocommerce.product.variant.binding'].search([
                ('backend_id', '=', backend.id),
                ('product_binding_id', '=', binding.id),
            ])
            for vb in variant_bindings:
                variant = vb.odoo_id
                qty = self._get_stock_qty(variant.id, location.id)
                log = self.env['channel.sync.log'].start(
                    backend, 'inventory', 'export',
                    external_id=f'{binding.external_id}/{vb.external_id}',
                )
                try:
                    client.update_variation_stock(
                        int(binding.external_id),
                        int(vb.external_id),
                        qty,
                    )
                    log.succeed(odoo_record=variant)
                    pushed_any = True
                except Exception as exc:
                    log.fail(str(exc))
                    raise
        else:
            # Simple product: sum across all variants (usually just one)
            qty = sum(
                self._get_stock_qty(v.id, location.id)
                for v in template.product_variant_ids
            )
            log = self.env['channel.sync.log'].start(
                backend, 'inventory', 'export',
                external_id=binding.external_id,
            )
            try:
                client.update_product_stock(int(binding.external_id), qty)
                log.succeed(odoo_record=template)
                pushed_any = True
            except Exception as exc:
                log.fail(str(exc))
                raise

        return pushed_any

    @api.model
    def _run_export_all(self):
        """Cron entry point: export inventory for all connected backends."""
        backends = self.env['woocommerce.backend'].search([
            ('state', '=', 'connected'),
            ('export_inventory', '=', True),
        ])
        for backend in backends:
            try:
                self._run_export(backend)
            except Exception as exc:
                _logger.error(
                    '[WooCommerce] Inventory export failed for backend %s: %s',
                    backend.name, exc, exc_info=True,
                )

    # ── Incremental Stock Push ────────────────────────────────────────────────

    @api.model
    def push_stock_for_products(self, product_ids):
        """Push inventory for specific product.product IDs.

        Called after stock moves are confirmed (see stock_move.py hook).

        :param product_ids: list of product.product IDs
        """
        if not product_ids:
            return

        # Find all backends that are active and export inventory
        backends = self.env['woocommerce.backend'].search([
            ('state', '=', 'connected'),
            ('export_inventory', '=', True),
        ])

        for backend in backends:
            if not backend.warehouse_id:
                continue
            location = backend.warehouse_id.lot_stock_id
            client = backend._get_client()

            # Find bindings that cover these product variants
            for product_id in product_ids:
                product = self.env['product.product'].browse(product_id)
                template = product.product_tmpl_id

                # Try variant binding first
                vb = self.env['woocommerce.product.variant.binding'].search([
                    ('backend_id', '=', backend.id),
                    ('odoo_id', '=', product_id),
                ], limit=1)

                if vb:
                    parent_binding = vb.product_binding_id
                    qty = self._get_stock_qty(product_id, location.id)
                    try:
                        client.update_variation_stock(
                            int(parent_binding.external_id),
                            int(vb.external_id),
                            qty,
                        )
                        _logger.debug(
                            '[WooCommerce] Pushed variant stock: product_id=%s qty=%s',
                            product_id, qty,
                        )
                    except Exception as exc:
                        _logger.error(
                            '[WooCommerce] Failed incremental inventory push for variant %s: %s',
                            product_id, exc,
                        )
                    continue

                # Try product template binding
                pb = self.env['woocommerce.product.binding'].search([
                    ('backend_id', '=', backend.id),
                    ('odoo_id', '=', template.id),
                ], limit=1)

                if pb:
                    qty = sum(
                        self._get_stock_qty(v.id, location.id)
                        for v in template.product_variant_ids
                    )
                    try:
                        client.update_product_stock(int(pb.external_id), qty)
                        _logger.debug(
                            '[WooCommerce] Pushed template stock: template_id=%s qty=%s',
                            template.id, qty,
                        )
                    except Exception as exc:
                        _logger.error(
                            '[WooCommerce] Failed incremental inventory push for template %s: %s',
                            template.id, exc,
                        )

    # ── Stock Quantity Helper ─────────────────────────────────────────────────

    @api.model
    def _get_stock_qty(self, product_id, location_id):
        """Return the available quantity for a product.product at a location."""
        quant = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
        ])
        # Sum reserved_quantity deducted from quantity
        total = sum(q.quantity - q.reserved_quantity for q in quant)
        return max(0.0, total)
