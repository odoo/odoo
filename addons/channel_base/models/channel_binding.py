import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ChannelBinding(models.AbstractModel):
    """Abstract bridge between an Odoo record and its external channel counterpart.

    Each concrete binding model:
    - Has a Many2one to the specific backend (e.g., woocommerce.backend)
    - Has a Many2one to the Odoo record (e.g., product.template)
    - Stores the external ID (e.g., WooCommerce product ID)
    - Tracks sync state and timestamps

    The pair (backend_id, external_id) must be unique — this is the
    deduplication key that prevents duplicate imports.
    """

    _name = 'channel.binding'
    _description = 'Channel Binding (Abstract)'

    # ── External Reference ────────────────────────────────────────────────────

    external_id = fields.Char(
        string='External ID',
        required=True,
        index=True,
        help='ID of this record on the external channel (e.g., WooCommerce product ID).',
    )

    # ── Sync State ────────────────────────────────────────────────────────────

    sync_state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('error', 'Error'),
            ('outdated', 'Outdated'),
        ],
        string='Sync State',
        default='pending',
        required=True,
        index=True,
        copy=False,
    )
    last_sync = fields.Datetime(
        string='Last Synced',
        copy=False,
        readonly=True,
    )
    sync_error = fields.Text(
        string='Last Sync Error',
        copy=False,
        readonly=True,
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def mark_synced(self):
        self.write({
            'sync_state': 'synced',
            'last_sync': fields.Datetime.now(),
            'sync_error': False,
        })

    def mark_error(self, message):
        self.write({
            'sync_state': 'error',
            'sync_error': str(message)[:2048],
        })

    @api.model
    def _get_binding(self, backend, external_id):
        """Return the binding for the given backend + external_id, or False."""
        return self.search([
            ('backend_id', '=', backend.id),
            ('external_id', '=', str(external_id)),
        ], limit=1)
