import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..mappers import OrderMapper

_logger = logging.getLogger(__name__)


class WooCommerceOrderBinding(models.Model):
    """Bridge between WooCommerce orders and Odoo sale.order records.

    One binding per (backend, WooCommerce order ID) pair.
    Unique constraint prevents duplicate imports on retry.
    """

    _name = 'woocommerce.order.binding'
    _description = 'WooCommerce Order Binding'
    _inherit = ['channel.binding']
    _order = 'backend_id, external_id desc'
    _rec_name = 'display_name'

    # ── Relations ─────────────────────────────────────────────────────────────

    backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        required=True,
        ondelete='cascade',
        index=True,
    )
    odoo_id = fields.Many2one(
        comodel_name='sale.order',
        string='Odoo Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ── WooCommerce Metadata ──────────────────────────────────────────────────

    wc_status = fields.Char(
        string='WC Status',
        help='WooCommerce order status at time of last sync.',
    )
    wc_number = fields.Char(
        string='WC Order Number',
        help='Human-readable WooCommerce order number (e.g. #1234)',
    )
    wc_payment_method = fields.Char(string='Payment Method')
    wc_total = fields.Float(string='WC Order Total')

    # ── Computed ──────────────────────────────────────────────────────────────

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('backend_id', 'external_id', 'wc_number', 'odoo_id')
    def _compute_display_name(self):
        for rec in self:
            wc_ref = f'WC#{rec.wc_number or rec.external_id}'
            odoo_ref = rec.odoo_id.name if rec.odoo_id else '?'
            rec.display_name = f'[{rec.backend_id.name}] {wc_ref} → {odoo_ref}'

    # ── Constraints ───────────────────────────────────────────────────────────

    _sql_constraints = [
        ('unique_backend_external', 'UNIQUE(backend_id, external_id)',
         'A binding for this WooCommerce order already exists on this backend.'),
    ]

    # ── Import Orchestration ──────────────────────────────────────────────────

    @api.model
    def _run_import(self, backend):
        """Import new/updated orders from WooCommerce.

        Uses last_orders_sync as incremental cursor.
        """
        client = backend._get_client()
        since = None

        if backend.last_orders_sync:
            import datetime
            dt = backend.last_orders_sync - datetime.timedelta(minutes=5)
            since = dt.strftime('%Y-%m-%dT%H:%M:%S')
        elif backend.sync_orders_from_date:
            since = backend.sync_orders_from_date.strftime('%Y-%m-%dT%H:%M:%S')

        statuses = backend._get_order_statuses()
        _logger.info(
            '[WooCommerce] Starting order import for backend %s (since=%s, statuses=%s)',
            backend.name, since, statuses,
        )

        imported = skipped = errors = 0
        sync_start = fields.Datetime.now()

        for wc_order in client.get_all_orders(after=since, statuses=statuses):
            try:
                result = self._import_one_order(backend, wc_order)
                if result in ('created', 'updated'):
                    imported += 1
                elif result == 'skipped':
                    skipped += 1
            except Exception as exc:
                errors += 1
                _logger.error(
                    '[WooCommerce] Failed to import order #%s: %s',
                    wc_order.get('id'), exc, exc_info=True,
                )

        backend.write({'last_orders_sync': sync_start})

        _logger.info(
            '[WooCommerce] Order import complete for %s: %d imported, %d skipped, %d errors',
            backend.name, imported, skipped, errors,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Order Sync Complete',
                'message': f'{imported} imported/updated, {skipped} skipped, {errors} errors.',
                'type': 'success' if errors == 0 else 'warning',
                'sticky': False,
            },
        }

    @api.model
    def _import_one_order(self, backend, wc_order):
        """Import or update a single WooCommerce order.

        :returns: 'created', 'updated', or 'skipped'
        """
        wc_id = str(wc_order.get('id'))
        wc_status = wc_order.get('status', 'pending')

        log = self.env['channel.sync.log'].start(
            backend, 'order', 'import', external_id=wc_id,
            raw_data=str(wc_order)[:4096],
        )

        try:
            binding = self._get_binding(backend, wc_id)

            # ── Already synced: check for status changes only ─────────────────
            if binding:
                action = self._update_existing_order(binding, wc_order, wc_status)
                log.succeed(odoo_record=binding.odoo_id, notes=f'action={action}')
                return action

            # ── New order: full import ────────────────────────────────────────
            # 1. Resolve / create customer and shipping address
            CustomerBinding = self.env['woocommerce.customer.binding']
            billing_partner, shipping_partner = CustomerBinding.find_or_create_for_order(
                backend, wc_order,
            )

            # 2. Create sale.order
            pricelist_id = backend.default_pricelist_id.id if backend.default_pricelist_id else False
            order_vals = OrderMapper.to_order_vals(
                wc_order,
                partner_id=billing_partner.id,
                partner_shipping_id=shipping_partner.id,
                pricelist_id=pricelist_id,
            )
            if backend.default_sales_team_id:
                order_vals['team_id'] = backend.default_sales_team_id.id
            if backend.company_id:
                order_vals['company_id'] = backend.company_id.id

            order = self.env['sale.order'].create(order_vals)

            # 3. Create order lines
            self._create_order_lines(backend, order, wc_order)

            # 4. Add shipping line(s) as additional order lines
            self._create_shipping_lines(backend, order, wc_order)

            # 5. Confirm if WC status warrants it
            if OrderMapper.should_confirm(wc_status) and order.state == 'draft':
                order.action_confirm()

            # 6. Create binding
            self.create({
                'backend_id': backend.id,
                'external_id': wc_id,
                'odoo_id': order.id,
                'wc_status': wc_status,
                'wc_number': str(wc_order.get('number') or wc_id),
                'wc_payment_method': wc_order.get('payment_method_title'),
                'wc_total': float(wc_order.get('total') or 0.0),
                'sync_state': 'synced',
                'last_sync': fields.Datetime.now(),
            })

            # 7. Tag the sale.order with WooCommerce metadata
            order.write({
                'woo_order_id': wc_id,
                'woo_backend_id': backend.id,
            })

            log.succeed(odoo_record=order)
            return 'created'

        except Exception as exc:
            log.fail(str(exc))
            raise

    # ── Update Existing Order ─────────────────────────────────────────────────

    @api.model
    def _update_existing_order(self, binding, wc_order, wc_status):
        """Handle status changes on an already-imported order.

        :returns: 'updated' or 'skipped'
        """
        if binding.wc_status == wc_status:
            return 'skipped'

        order = binding.odoo_id
        old_status = binding.wc_status

        _logger.info(
            '[WooCommerce] Order #%s status changed: %s → %s',
            binding.external_id, old_status, wc_status,
        )

        # Cancel in Odoo if WC order is cancelled/refunded/failed
        if wc_status in ('cancelled', 'refunded', 'failed', 'trash'):
            if order.state not in ('cancel',):
                try:
                    order.action_cancel()
                except Exception as exc:
                    _logger.warning(
                        '[WooCommerce] Cannot cancel order %s (state=%s): %s',
                        order.name, order.state, exc,
                    )

        # Confirm in Odoo if WC order is now processing/completed
        elif wc_status in ('processing', 'completed') and order.state == 'draft':
            order.action_confirm()

        binding.write({
            'wc_status': wc_status,
            'last_sync': fields.Datetime.now(),
            'sync_state': 'synced',
        })
        return 'updated'

    # ── Order Lines ───────────────────────────────────────────────────────────

    @api.model
    def _create_order_lines(self, backend, order, wc_order):
        """Create sale.order.line records for each WC line item."""
        ProductBinding = self.env['woocommerce.product.binding']
        VariantBinding = self.env['woocommerce.product.variant.binding']

        for item in wc_order.get('line_items', []):
            product = self._resolve_product(backend, item, ProductBinding, VariantBinding)
            if not product:
                # Create a placeholder product for unresolved items
                product = self._get_or_create_placeholder_product(item)

            line_vals = OrderMapper.to_order_line_vals(
                item,
                product_id=product.id,
            )
            line_vals['order_id'] = order.id
            self.env['sale.order.line'].create(line_vals)

    @api.model
    def _resolve_product(self, backend, line_item, ProductBinding, VariantBinding):
        """Find the Odoo product.product for a WC order line item.

        Lookup order:
        1. WC variation_id → woocommerce.product.variant.binding
        2. WC product_id → woocommerce.product.binding (take first variant)
        3. SKU match on product.product
        4. SKU match on product.template
        5. Return None (caller creates placeholder)
        """
        wc_variation_id = line_item.get('variation_id')
        wc_product_id = str(line_item.get('product_id') or '')
        sku = (line_item.get('sku') or '').strip()

        # 1. Variant binding
        if wc_variation_id:
            vb = VariantBinding.search([
                ('backend_id', '=', backend.id),
                ('external_id', '=', str(wc_variation_id)),
            ], limit=1)
            if vb:
                return vb.odoo_id

        # 2. Product binding
        if wc_product_id:
            pb = ProductBinding.search([
                ('backend_id', '=', backend.id),
                ('external_id', '=', wc_product_id),
            ], limit=1)
            if pb and pb.odoo_id.product_variant_id:
                return pb.odoo_id.product_variant_id

        # 3. SKU on product.product
        if sku:
            pp = self.env['product.product'].search(
                [('default_code', '=', sku)], limit=1
            )
            if pp:
                return pp

        # 4. SKU on product.template (take first variant)
        if sku:
            tmpl = self.env['product.template'].search(
                [('default_code', '=', sku)], limit=1
            )
            if tmpl and tmpl.product_variant_id:
                return tmpl.product_variant_id

        _logger.warning(
            '[WooCommerce] Cannot resolve product for line item: sku=%s, wc_id=%s',
            sku, wc_product_id,
        )
        return None

    @api.model
    def _get_or_create_placeholder_product(self, line_item):
        """Create a placeholder consumable product for unresolved WC line items."""
        name = line_item.get('name') or 'WooCommerce Product'
        sku = (line_item.get('sku') or '').strip()

        domain = [('name', '=', name), ('default_code', '=', sku or False)]
        existing = self.env['product.product'].search(domain, limit=1)
        if existing:
            return existing

        template = self.env['product.template'].create({
            'name': name,
            'default_code': sku or False,
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': False,
        })
        _logger.warning(
            '[WooCommerce] Created placeholder product "%s" for unresolved order line', name
        )
        return template.product_variant_id

    @api.model
    def _create_shipping_lines(self, backend, order, wc_order):
        """Add WooCommerce shipping costs as a service order line."""
        shipping_lines = OrderMapper.extract_shipping_lines(wc_order)
        if not shipping_lines:
            return

        # Find or create a "WooCommerce Shipping" service product
        shipping_product = self._get_shipping_product()

        for sl in shipping_lines:
            total = sl.get('total', 0.0)
            if total <= 0:
                continue
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': shipping_product.id,
                'name': sl.get('method_title') or 'Shipping',
                'product_uom_qty': 1.0,
                'price_unit': total,
                'tax_id': [],  # Shipping tax handled separately if needed
            })

    @api.model
    def _get_shipping_product(self):
        """Return the canonical shipping service product, creating it if needed."""
        ref = 'woocommerce_connector.product_shipping'
        product = self.env.ref(ref, raise_if_not_found=False)
        if product:
            return product.product_variant_id if hasattr(product, 'product_variant_id') else product

        template = self.env['product.template'].create({
            'name': 'WooCommerce Shipping',
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'invoice_policy': 'order',
        })
        # Register the external ID so we find it next time
        self.env['ir.model.data'].create({
            'name': 'product_shipping',
            'module': 'woocommerce_connector',
            'model': 'product.template',
            'res_id': template.id,
            'noupdate': True,
        })
        return template.product_variant_id
