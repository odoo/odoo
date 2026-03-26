import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ChannelBackend(models.AbstractModel):
    """Abstract base for all channel backends (WooCommerce, Amazon, etc.).

    Concrete backend models inherit from this and add channel-specific
    credentials, API client methods, and sync configuration.

    Each backend record represents one store/account on a given channel,
    scoped to a single company.
    """

    _name = 'channel.backend'
    _description = 'Channel Backend (Abstract)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Identity ──────────────────────────────────────────────────────────────

    name = fields.Char(
        string='Backend Name',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    # ── Connection State ──────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ('draft', 'Not Connected'),
            ('connected', 'Connected'),
            ('error', 'Connection Error'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    last_connection_error = fields.Text(
        string='Last Connection Error',
        copy=False,
        readonly=True,
    )

    # ── Sync Timestamps ───────────────────────────────────────────────────────

    last_products_sync = fields.Datetime(
        string='Products Last Synced',
        copy=False,
        readonly=True,
    )
    last_orders_sync = fields.Datetime(
        string='Orders Last Synced',
        copy=False,
        readonly=True,
    )
    last_customers_sync = fields.Datetime(
        string='Customers Last Synced',
        copy=False,
        readonly=True,
    )

    # ── Sync Configuration ────────────────────────────────────────────────────

    sync_orders_from_date = fields.Datetime(
        string='Import Orders From',
        help='Only import orders created after this date. '
             'Leave empty to import all orders on first run.',
    )
    # warehouse_id is defined in concrete backends that depend on stock module

    # ── Computed ──────────────────────────────────────────────────────────────

    sync_log_count = fields.Integer(
        string='Sync Logs',
        compute='_compute_sync_log_count',
    )

    # ── Overridable by subclasses ─────────────────────────────────────────────

    _channel_type = 'generic'  # Override: 'woocommerce', 'amazon', etc.

    # ── Computes ──────────────────────────────────────────────────────────────

    def _compute_sync_log_count(self):
        for rec in self:
            rec.sync_log_count = self.env['channel.sync.log'].search_count([
                ('backend_ref', '=', f'{rec._name},{rec.id}'),
            ])

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_test_connection(self):
        """Override in concrete backend to test API connectivity."""
        raise NotImplementedError

    def action_sync_products(self):
        """Trigger an immediate product sync. Override in concrete backend."""
        raise NotImplementedError

    def action_sync_orders(self):
        """Trigger an immediate order sync. Override in concrete backend."""
        raise NotImplementedError

    def action_view_sync_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sync Logs',
            'res_model': 'channel.sync.log',
            'view_mode': 'list,form',
            'domain': [('backend_ref', '=', f'{self._name},{self.id}')],
            'context': {'default_backend_ref': f'{self._name},{self.id}'},
        }
