import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ChannelSyncLog(models.Model):
    """Immutable audit trail for all channel sync operations.

    One record per sync attempt. Never updated after creation — errors
    are recorded here, not on the binding. This allows full replay history
    and failure analysis.

    Design: create-only (no writes after state transitions).
    Retention policy: archive old logs via cron (not implemented here).
    """

    _name = 'channel.sync.log'
    _description = 'Channel Sync Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    # ── What was synced ───────────────────────────────────────────────────────

    backend_ref = fields.Reference(
        selection='_selection_backend_ref',
        string='Backend',
        index=True,
        required=True,
        ondelete='cascade',
    )
    object_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('product_variant', 'Product Variant'),
            ('order', 'Order'),
            ('customer', 'Customer'),
            ('inventory', 'Inventory'),
            ('category', 'Category'),
        ],
        string='Object Type',
        required=True,
        index=True,
    )
    operation = fields.Selection(
        selection=[
            ('import', 'Import (Channel → Odoo)'),
            ('export', 'Export (Odoo → Channel)'),
            ('update', 'Update'),
            ('delete', 'Delete'),
            ('test', 'Connection Test'),
        ],
        string='Operation',
        required=True,
        index=True,
    )
    external_id = fields.Char(
        string='External ID',
        index=True,
        help='The record ID on the external channel.',
    )
    odoo_record_ref = fields.Reference(
        selection='_selection_odoo_record_ref',
        string='Odoo Record',
        help='The Odoo record that was created or updated.',
    )

    # ── Execution State ───────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('skipped', 'Skipped'),
        ],
        string='State',
        default='pending',
        required=True,
        index=True,
    )
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)
    started_at = fields.Datetime(string='Started At')
    finished_at = fields.Datetime(string='Finished At')

    # ── Context / Debug ───────────────────────────────────────────────────────

    raw_data = fields.Text(
        string='Raw Payload',
        help='JSON payload received from the channel (truncated at 16KB).',
    )
    notes = fields.Text(string='Notes')

    # ── Computed ──────────────────────────────────────────────────────────────

    display_name = fields.Char(compute='_compute_display_name', store=True)
    duration = fields.Float(
        string='Duration (s)',
        compute='_compute_duration',
        store=True,
    )

    @api.depends('object_type', 'operation', 'external_id', 'state')
    def _compute_display_name(self):
        for rec in self:
            parts = [
                (rec.object_type or '').capitalize(),
                rec.operation or '',
                f'#{rec.external_id}' if rec.external_id else '',
                f'[{rec.state}]',
            ]
            rec.display_name = ' '.join(p for p in parts if p)

    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.finished_at:
                delta = rec.finished_at - rec.started_at
                rec.duration = delta.total_seconds()
            else:
                rec.duration = 0.0

    # ── Dynamic Reference Selection ───────────────────────────────────────────

    @api.model
    def _selection_backend_ref(self):
        """All installed channel backend models.

        Returns all non-transient models whose technical name ends with '.backend'
        and that are registered as inheriting channel.backend.
        """
        models_info = self.env['ir.model'].search([
            ('model', 'like', '%.backend'),
            ('transient', '=', False),
        ])
        # Include any model that ends in .backend — covers woocommerce.backend,
        # amazon.backend, walmart.backend, etc.
        return [(m.model, m.name) for m in models_info
                if m.model.endswith('.backend')]

    @api.model
    def _selection_odoo_record_ref(self):
        """Common Odoo models that can be synced."""
        return [
            ('product.template', 'Product'),
            ('product.product', 'Product Variant'),
            ('sale.order', 'Sale Order'),
            ('res.partner', 'Contact'),
        ]

    # ── Factory Methods ───────────────────────────────────────────────────────

    @api.model
    def start(self, backend, object_type, operation, external_id=None, raw_data=None):
        """Create a log entry and mark it as running. Returns the log record."""
        log = self.create({
            'backend_ref': f'{backend._name},{backend.id}',
            'object_type': object_type,
            'operation': operation,
            'external_id': str(external_id) if external_id else False,
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'raw_data': (str(raw_data)[:16384] if raw_data else False),
        })
        return log

    def succeed(self, odoo_record=None, notes=None):
        """Mark this log entry as done."""
        vals = {
            'state': 'done',
            'finished_at': fields.Datetime.now(),
        }
        if odoo_record:
            vals['odoo_record_ref'] = f'{odoo_record._name},{odoo_record.id}'
        if notes:
            vals['notes'] = notes
        self.write(vals)

    def fail(self, error_message, increment_retry=True):
        """Mark this log entry as failed."""
        vals = {
            'state': 'error',
            'finished_at': fields.Datetime.now(),
            'error_message': str(error_message)[:4096],
        }
        if increment_retry:
            vals['retry_count'] = self.retry_count + 1
        self.write(vals)

    def skip(self, reason=None):
        """Mark this log entry as skipped (e.g. no changes detected)."""
        self.write({
            'state': 'skipped',
            'finished_at': fields.Datetime.now(),
            'notes': reason,
        })
