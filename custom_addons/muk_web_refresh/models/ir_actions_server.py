from __future__ import annotations

from odoo import _, fields, models


class IrActionsServer(models.Model):
    """Add a server action type that broadcasts view reload requests."""

    _inherit = 'ir.actions.server'

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    state = fields.Selection(
        selection_add=[
            ('refresh', 'Reload Views'),
        ],
        ondelete={'refresh': 'cascade'},
    )

    refresh_view_types = fields.Char(
        string='View Types',
        help=(
            'Comma-separated list of view types to reload (e.g. list, kanban). '
            'Leave empty to reload all view types.'
        ),
    )

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _generate_action_name(self) -> str:
        """Return the default name for a reload-views action."""
        if self.state == 'refresh':
            return _('Reload Views')
        return super()._generate_action_name()

    def _run_action_refresh_multi(self, eval_context=None) -> None:
        """Broadcast a view reload request over the bus."""
        records = eval_context.get('records') or eval_context.get('record')
        message = {
            'model': self.model_id.model,
            'view_types': [
                vt.strip()
                for vt in (self.refresh_view_types or '').split(',')
                if vt.strip()
            ],
            'rec_ids': records.ids if records else [],
        }
        self.env['bus.bus']._sendone('broadcast', 'muk_web_refresh.reload', message)
