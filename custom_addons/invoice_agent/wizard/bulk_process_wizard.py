import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class InvoiceAgentBulkProcess(models.TransientModel):
    """Wizard to re-run AI extraction on selected bills in bulk.

    Triggered from the Action menu on list/kanban views of account.move.
    Uses TransientModel so records are auto-cleaned up by _transient_vacuum.

    Lifecycle:
    1. User selects records in list/kanban view
    2. Odoo sets active_ids / active_model in context
    3. default_get reads active_ids to pre-fill move_ids
    4. User clicks the action button
    5. action_process() resets extraction state on each bill
    6. A notification is returned showing processed vs skipped counts
    """
    _name = 'invoice.agent.bulk.process'
    _description = 'Bulk Re-Run AI Extraction'

    move_ids = fields.Many2many(
        comodel_name='account.move',
        string='Selected Bills',
        readonly=True,
        help='Bills to process. Pre-filled from the selection in the list/kanban view.',
    )
    processed_count = fields.Integer(
        string='Processed',
        default=0,
        readonly=True,
    )
    skipped_count = fields.Integer(
        string='Skipped',
        default=0,
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        """Pull active_ids from the context to pre-fill move_ids."""
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')
        if active_ids and active_model == 'account.move':
            moves = self.env['account.move'].browse(active_ids)
            if 'move_ids' in fields_list:
                res['move_ids'] = [(6, 0, moves.ids)]
        return res

    def action_process(self):
        """Reset extraction state on each selected bill.

        Each record is wrapped in try/except so one bad PDF cannot abort
        the entire batch. Returns a display_notification summarising results.
        """
        self.ensure_one()
        processed = 0
        skipped = 0

        for move in self.move_ids:
            try:
                move.write({
                    'ai_extraction_status': 'pending',
                    'ai_confidence': 0.0,
                    'ai_ocr_text': False,
                    'ai_extracted_json': False,
                    'ai_extracted_total': 0.0,
                    'ai_review_required': False,
                })
                # Also reset extraction lines
                move.extraction_line_ids.unlink()
                processed += 1
            except Exception:
                _logger.exception(
                    "Failed to reset AI extraction for move %s", move.display_name,
                )
                skipped += 1

        self.write({
            'processed_count': processed,
            'skipped_count': skipped,
        })

        notification_type = 'success' if not skipped else 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Re-Extraction Complete'),
                'message': _(
                    'Processed: %(processed)d, Skipped: %(skipped)d',
                ) % {'processed': processed, 'skipped': skipped},
                'sticky': True,
                'type': notification_type,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
