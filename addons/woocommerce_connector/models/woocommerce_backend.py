import logging
import json
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from ..api import WooCommerceClient, WooCommerceAPIError

_logger = logging.getLogger(__name__)

# WooCommerce order statuses to import (exclude trash/spam)
_DEFAULT_ORDER_STATUSES = ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']


class WooCommerceBackend(models.Model):
    """WooCommerce store connection and sync configuration.

    One record per WooCommerce store. Stores API credentials, sync settings,
    and provides the entry point for all sync operations.

    Credentials are stored in the database. For production deployments,
    consider using Odoo's vault/keychain integration.
    """

    _name = 'woocommerce.backend'
    _description = 'WooCommerce Backend'
    _inherit = ['channel.backend']
    _order = 'name'

    _channel_type = 'woocommerce'
    _check_company_auto = True

    # ── WooCommerce Credentials ───────────────────────────────────────────────

    url = fields.Char(
        string='Store URL',
        required=True,
        tracking=True,
        help='Base URL of your WooCommerce store, e.g. https://mystore.com',
    )
    consumer_key = fields.Char(
        string='Consumer Key',
        required=True,
        copy=False,
        groups='woocommerce_connector.group_woocommerce_manager',
        help='WooCommerce REST API Consumer Key (starts with ck_)',
    )
    consumer_secret = fields.Char(
        string='Consumer Secret',
        required=True,
        copy=False,
        groups='woocommerce_connector.group_woocommerce_manager',
        help='WooCommerce REST API Consumer Secret (starts with cs_)',
    )
    verify_ssl = fields.Boolean(
        string='Verify SSL',
        default=True,
        help='Disable only for self-signed certificates in dev environments.',
    )

    # ── Sync Configuration ────────────────────────────────────────────────────

    import_products = fields.Boolean(string='Import Products', default=True)
    import_orders = fields.Boolean(string='Import Orders', default=True)
    import_customers = fields.Boolean(string='Import Customers', default=True)
    export_inventory = fields.Boolean(string='Export Inventory Levels', default=True)

    order_statuses_to_import = fields.Char(
        string='Order Statuses to Import',
        default=','.join(_DEFAULT_ORDER_STATUSES),
        help='Comma-separated WooCommerce order statuses to import.',
    )
    product_as_storable = fields.Boolean(
        string='Import as Storable Products',
        default=False,
        help='If enabled, imported products will be storable (tracked inventory). '
             'Otherwise imported as consumable.',
    )
    default_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Default Pricelist',
        help='Pricelist to assign to WooCommerce orders. Leave empty for Odoo default.',
        check_company=True,
    )
    default_sales_team_id = fields.Many2one(
        comodel_name='crm.team',
        string='Default Sales Team',
        help='Sales team to assign to imported WooCommerce orders.',
        check_company=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Default Warehouse',
        help='Warehouse used for stock levels and order fulfillment.',
        check_company=True,
    )
    default_product_categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Default Product Category',
        help='Fallback product category when WC category cannot be matched.',
    )

    # ── Webhook Configuration ─────────────────────────────────────────────────

    webhook_secret = fields.Char(
        string='Webhook Secret',
        copy=False,
        groups='woocommerce_connector.group_woocommerce_manager',
        help='Secret used to verify incoming WooCommerce webhook payloads.',
    )
    webhook_base_url = fields.Char(
        string='Webhook Base URL',
        help='Base URL where Odoo is accessible from the internet. '
             'Used to register webhooks on WooCommerce.',
    )

    # ── Computed / Stats ──────────────────────────────────────────────────────

    product_binding_count = fields.Integer(
        string='Synced Products',
        compute='_compute_binding_counts',
    )
    order_binding_count = fields.Integer(
        string='Synced Orders',
        compute='_compute_binding_counts',
    )
    customer_binding_count = fields.Integer(
        string='Synced Customers',
        compute='_compute_binding_counts',
    )

    # ── Constraints ───────────────────────────────────────────────────────────

    _unique_url_company = models.Constraint(
        'UNIQUE(url, company_id)',
        'A backend for this store URL already exists for this company.',
    )

    # ── Computes ──────────────────────────────────────────────────────────────

    def _compute_binding_counts(self):
        for rec in self:
            rec.product_binding_count = self.env['woocommerce.product.binding'].search_count(
                [('backend_id', '=', rec.id)]
            )
            rec.order_binding_count = self.env['woocommerce.order.binding'].search_count(
                [('backend_id', '=', rec.id)]
            )
            rec.customer_binding_count = self.env['woocommerce.customer.binding'].search_count(
                [('backend_id', '=', rec.id)]
            )

    # ── API Client Factory ────────────────────────────────────────────────────

    def _get_client(self):
        """Instantiate and return a WooCommerceClient for this backend.

        :returns: WooCommerceClient instance
        :raises UserError: if credentials are incomplete
        """
        self.ensure_one()
        if not self.url or not self.consumer_key or not self.consumer_secret:
            raise UserError(
                'WooCommerce backend "%s" is missing URL, Consumer Key, or Consumer Secret.' % self.name
            )
        return WooCommerceClient(
            url=self.url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            verify_ssl=self.verify_ssl,
        )

    # ── Connection Test ───────────────────────────────────────────────────────

    def action_test_connection(self):
        """Test API connectivity and update backend state."""
        self.ensure_one()
        log = self.env['channel.sync.log'].start(
            self, 'product', 'test',
        )
        try:
            client = self._get_client()
            info = client.test_connection()
            self.write({
                'state': 'connected',
                'last_connection_error': False,
            })
            log.succeed(notes=f"Connected to: {info.get('name')} ({info.get('url')})")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful',
                    'message': f"Connected to WooCommerce store: {info.get('name')}",
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as exc:
            error_msg = str(exc)
            self.write({
                'state': 'error',
                'last_connection_error': error_msg,
            })
            log.fail(error_msg, increment_retry=False)
            raise UserError(f'Connection failed: {error_msg}') from exc

    # ── Wizard Launchers ──────────────────────────────────────────────────────

    def action_open_sync_wizard(self):
        """Open the manual sync wizard pre-populated with this backend."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sync WooCommerce Now',
            'res_model': 'woocommerce.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_backend_id': self.id},
        }

    def action_open_retry_wizard(self):
        """Open the retry-errors wizard pre-populated with this backend."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Retry Failed Syncs',
            'res_model': 'woocommerce.sync.retry.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_backend_id': self.id},
        }

    # ── Product Sync ──────────────────────────────────────────────────────────

    def action_sync_products(self):
        """Trigger immediate product sync from WooCommerce."""
        self.ensure_one()
        return self.env['woocommerce.product.binding']._run_import(self)

    def _cron_sync_products(self):
        """Called by cron job. Syncs products for all active backends."""
        backends = self.search([('state', '=', 'connected'), ('import_products', '=', True)])
        for backend in backends:
            try:
                backend.env['woocommerce.product.binding']._run_import(backend)
            except Exception as exc:
                _logger.error(
                    '[WooCommerce] Product sync failed for backend %s: %s',
                    backend.name, exc, exc_info=True,
                )

    # ── Order Sync ────────────────────────────────────────────────────────────

    def action_sync_orders(self):
        """Trigger immediate order sync from WooCommerce."""
        self.ensure_one()
        return self.env['woocommerce.order.binding']._run_import(self)

    def _cron_sync_orders(self):
        """Called by cron job. Syncs orders for all active backends."""
        backends = self.search([('state', '=', 'connected'), ('import_orders', '=', True)])
        for backend in backends:
            try:
                backend.env['woocommerce.order.binding']._run_import(backend)
            except Exception as exc:
                _logger.error(
                    '[WooCommerce] Order sync failed for backend %s: %s',
                    backend.name, exc, exc_info=True,
                )

    # ── Inventory Push ────────────────────────────────────────────────────────

    def _cron_export_inventory(self):
        """Called by cron job. Pushes stock levels to WooCommerce."""
        backends = self.search([('state', '=', 'connected'), ('export_inventory', '=', True)])
        for backend in backends:
            try:
                backend.env['woocommerce.inventory.sync']._run_export(backend)
            except Exception as exc:
                _logger.error(
                    '[WooCommerce] Inventory sync failed for backend %s: %s',
                    backend.name, exc, exc_info=True,
                )

    # ── Smart Buttons ─────────────────────────────────────────────────────────

    def action_view_product_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Products',
            'res_model': 'woocommerce.product.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_view_order_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Orders',
            'res_model': 'woocommerce.order.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    def action_view_customer_bindings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Customers',
            'res_model': 'woocommerce.customer.binding',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
        }

    # ── Webhook Registration ──────────────────────────────────────────────────

    def action_register_webhooks(self):
        """Register all required webhooks on WooCommerce."""
        self.ensure_one()
        if not self.webhook_base_url or not self.webhook_secret:
            raise UserError(
                'Please set both Webhook Base URL and Webhook Secret before registering webhooks.'
            )
        client = self._get_client()
        base = self.webhook_base_url.rstrip('/')
        token = self._get_webhook_token()

        topics = [
            'order.created',
            'order.updated',
            'product.created',
            'product.updated',
            'product.deleted',
        ]
        registered = []
        for topic in topics:
            try:
                result = client.create_webhook(
                    topic=topic,
                    delivery_url=f'{base}/woocommerce/webhook/{token}',
                    secret=self.webhook_secret,
                )
                registered.append(topic)
                _logger.info('[WooCommerce] Registered webhook: %s (id=%s)', topic, result.get('id'))
            except Exception as exc:
                _logger.warning('[WooCommerce] Failed to register webhook %s: %s', topic, exc)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webhooks Registered',
                'message': f'Registered {len(registered)}/{len(topics)} webhooks.',
                'type': 'success' if len(registered) == len(topics) else 'warning',
                'sticky': False,
            },
        }

    def _get_webhook_token(self):
        """Return a stable, unique token for this backend's webhook URL."""
        import hashlib
        raw = f'{self.id}:{self.url}:{self.consumer_key}'
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @api.model
    def _find_by_webhook_token(self, token):
        """Reverse-lookup a backend from its webhook token."""
        for backend in self.search([]):
            if backend._get_webhook_token() == token:
                return backend
        return self.browse()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_order_statuses(self):
        """Return list of order statuses to import."""
        raw = (self.order_statuses_to_import or '').strip()
        if not raw:
            return _DEFAULT_ORDER_STATUSES
        return [s.strip() for s in raw.split(',') if s.strip()]
