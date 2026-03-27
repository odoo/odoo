"""WooCommerce manual sync and retry wizard.

Provides:
1. ManualSync — admin-triggered immediate sync with scope selection
2. SyncRetry  — retry all 'error' sync logs for a backend

Both wizards return a notification with counts on completion.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceSyncWizard(models.TransientModel):
    """Wizard: trigger an immediate, scoped sync for a WooCommerce backend.

    Lets the admin choose which object types to sync and from when,
    without waiting for the cron jobs.
    """

    _name = 'woocommerce.sync.wizard'
    _description = 'WooCommerce Manual Sync Wizard'

    # ── Fields ────────────────────────────────────────────────────────────────

    backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        required=True,
        domain=[('state', '=', 'connected')],
        default=lambda self: self._default_backend(),
    )

    sync_products = fields.Boolean(string='Sync Products', default=True)
    sync_orders = fields.Boolean(string='Sync Orders', default=True)
    sync_customers = fields.Boolean(string='Sync Customers', default=False)
    export_inventory = fields.Boolean(string='Export Inventory to WooCommerce', default=False)

    force_full_sync = fields.Boolean(
        string='Force Full Re-sync',
        default=False,
        help='If enabled, ignores last sync timestamp and re-imports everything. '
             'WARNING: this can take a long time for large catalogs.',
    )
    orders_from_date = fields.Datetime(
        string='Import Orders From',
        help='Override: only import orders after this date. '
             'Leave empty to use the backend\'s last sync timestamp.',
    )

    # ── State / Progress ──────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[('draft', 'Configure'), ('done', 'Done')],
        default='draft',
        readonly=True,
    )
    result_summary = fields.Text(string='Result', readonly=True)

    # ── Defaults ──────────────────────────────────────────────────────────────

    @api.model
    def _default_backend(self):
        backends = self.env['woocommerce.backend'].search(
            [('state', '=', 'connected')], limit=1
        )
        return backends.id if backends else False

    # ── Action ────────────────────────────────────────────────────────────────

    def action_run_sync(self):
        """Execute the selected sync operations."""
        self.ensure_one()
        backend = self.backend_id

        if not backend:
            raise UserError('Please select a WooCommerce backend.')
        if backend.state != 'connected':
            raise UserError(
                f'Backend "{backend.name}" is not connected. '
                'Please test the connection first.'
            )

        results = []

        # ── Temporarily override last_sync timestamps for full re-sync ─────
        original_product_sync = backend.last_products_sync
        original_order_sync = backend.last_orders_sync
        original_customer_sync = backend.last_customers_sync

        if self.force_full_sync:
            backend.write({
                'last_products_sync': False,
                'last_orders_sync': False,
                'last_customers_sync': False,
            })
        if self.orders_from_date and not self.force_full_sync:
            backend.write({'last_orders_sync': self.orders_from_date})

        try:
            if self.sync_products and backend.import_products:
                _logger.info('[WC Wizard] Starting product sync for %s', backend.name)
                self.env['woocommerce.product.binding']._run_import(backend)
                results.append('Products: synced')

            if self.sync_customers and backend.import_customers:
                _logger.info('[WC Wizard] Starting customer sync for %s', backend.name)
                self.env['woocommerce.customer.binding']._run_import(backend)
                results.append('Customers: synced')

            if self.sync_orders and backend.import_orders:
                _logger.info('[WC Wizard] Starting order sync for %s', backend.name)
                self.env['woocommerce.order.binding']._run_import(backend)
                results.append('Orders: synced')

            if self.export_inventory and backend.export_inventory:
                _logger.info('[WC Wizard] Starting inventory export for %s', backend.name)
                self.env['woocommerce.inventory.sync']._run_export(backend)
                results.append('Inventory: exported to WooCommerce')

        except Exception as exc:
            # Restore timestamps on failure so we don't lose sync position
            if self.force_full_sync:
                backend.write({
                    'last_products_sync': original_product_sync,
                    'last_orders_sync': original_order_sync,
                    'last_customers_sync': original_customer_sync,
                })
            raise UserError(f'Sync failed: {exc}') from exc

        summary = '\n'.join(results) if results else 'Nothing to sync (check configuration).'
        self.write({'state': 'done', 'result_summary': summary})

        # Keep wizard open to show results
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}


class WooCommerceSyncRetryWizard(models.TransientModel):
    """Wizard: retry all failed sync log entries for a backend.

    Identifies records in 'error' state from channel.sync.log and
    re-triggers the appropriate import/export for each.
    """

    _name = 'woocommerce.sync.retry.wizard'
    _description = 'WooCommerce Retry Failed Syncs'

    backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        required=True,
        domain=[('state', '=', 'connected')],
        default=lambda self: self.env['woocommerce.backend'].search(
            [('state', '=', 'connected')], limit=1,
        ),
    )
    object_type = fields.Selection(
        selection=[
            ('all', 'All Types'),
            ('product', 'Products'),
            ('order', 'Orders'),
            ('customer', 'Customers'),
            ('inventory', 'Inventory'),
        ],
        string='Object Type',
        default='all',
        required=True,
    )

    # Computed: how many errors exist
    error_count = fields.Integer(
        string='Error Count',
        compute='_compute_error_count',
    )
    state = fields.Selection(
        selection=[('draft', 'Review'), ('done', 'Done')],
        default='draft',
        readonly=True,
    )
    result_summary = fields.Text(string='Result', readonly=True)

    @api.depends('backend_id', 'object_type')
    def _compute_error_count(self):
        for rec in self:
            if not rec.backend_id:
                rec.error_count = 0
                continue
            domain = [
                ('backend_ref', '=', f'woocommerce.backend,{rec.backend_id.id}'),
                ('state', '=', 'error'),
            ]
            if rec.object_type and rec.object_type != 'all':
                domain.append(('object_type', '=', rec.object_type))
            rec.error_count = self.env['channel.sync.log'].search_count(domain)

    def action_retry(self):
        """Re-trigger import for all error-state log entries."""
        self.ensure_one()
        backend = self.backend_id

        domain = [
            ('backend_ref', '=', f'woocommerce.backend,{backend.id}'),
            ('state', '=', 'error'),
            ('operation', '=', 'import'),
            ('external_id', '!=', False),
        ]
        if self.object_type and self.object_type != 'all':
            domain.append(('object_type', '=', self.object_type))

        failed_logs = self.env['channel.sync.log'].search(domain, order='object_type, id')

        if not failed_logs:
            self.write({
                'state': 'done',
                'result_summary': 'No failed sync logs found.',
            })
            return self._reopen()

        client = backend._get_client()
        retried = succeeded = still_failed = 0

        for log in failed_logs:
            retried += 1
            try:
                self._retry_one(backend, client, log)
                succeeded += 1
            except Exception as exc:
                still_failed += 1
                _logger.error(
                    '[WC Retry] Failed again for %s #%s: %s',
                    log.object_type, log.external_id, exc,
                )

        summary = (
            f'Retried {retried} failed records:\n'
            f'  Succeeded: {succeeded}\n'
            f'  Still failing: {still_failed}'
        )
        self.write({'state': 'done', 'result_summary': summary})
        return self._reopen()

    def _retry_one(self, backend, client, log):
        """Re-run the import for a single failed log entry."""
        obj_type = log.object_type
        ext_id = log.external_id

        if obj_type in ('product', 'product_variant'):
            wc_product = client.get_product(int(ext_id))
            self.env['woocommerce.product.binding']._import_one_product(
                backend, wc_product, client
            )
        elif obj_type == 'order':
            wc_order = client.get_order(int(ext_id))
            self.env['woocommerce.order.binding']._import_one_order(backend, wc_order)
        elif obj_type == 'customer':
            wc_customer = client.get_customer(int(ext_id))
            self.env['woocommerce.customer.binding']._import_one_customer(
                backend, wc_customer
            )
        else:
            _logger.debug('[WC Retry] No retry handler for object_type=%s', obj_type)

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
