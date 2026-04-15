from odoo import fields, models


class AccountMoveEventProcess(models.Model):
    _name = 'account.move.event.process'
    _description = 'Account Move Event Process'

    event_code = fields.Char(required=True, index=True)
    state = fields.Selection([
        ('new', 'New'),
        ('process', 'Processing'),
    ], default='new', required=True, copy=False)
    scheduled_at = fields.Datetime(default=fields.Datetime.now, required=True)
    data = fields.Json(default={})
    move_id = fields.Many2one('account.move', required=True)

    _state_event_code_scheduled_at_idx = models.Index('(state, event_code, scheduled_at)')
    _unique_model_id_res_id_event_code = models.UniqueIndex(
        "(move_id, event_code)",
        "Can not schedule more than one event per move at a time.",
    )

    def get_batch_to_process(self, event_code, batch_size=100):
        """Gets a batch of pending events and locks them for processing."""
        events = self.search(
            [
                ('event_code', '=', event_code),
                ('state', '=', 'new'),
            ],
            order='scheduled_at asc',
            limit=batch_size,
        ).try_lock_for_update()
        events.state = 'process'
        return events
