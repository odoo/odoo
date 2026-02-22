from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AccountEventProcess(models.Model):
    _name = 'account.event.process'
    _description = 'Account Event Process'

    event_code = fields.Char(required=True, index=True)
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
    ], default='new', required=True)
    scheduled_at = fields.Datetime(default=fields.Datetime.now, required=True)
    data = fields.Json()

    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    res_id = fields.Integer(required=True)

    def init(self):
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS account_event_process_model_res_scheduled_idx
                                    ON account_event_process (model_id, res_id, scheduled_at)
            """,
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS account_event_process_state_scheduled_idx
                                    ON account_event_process (state, event_code, scheduled_at)
            """,
        )
        return super().init()

    @api.model
    def get_record_active_event_data(self, record):
        if event := self.search(
            domain=[
                ('state', '=', 'new'),
                *self._get_record_search_domain(record),
            ],
            order='scheduled_at desc',
            limit=1,
        ):
            return event.data
        return None

    @api.model
    def _get_record_search_domain(self, records):
        return [
            ('model_id', '=', self.env['ir.model']._get_id(records._name)),
            ('res_id', 'in', records.ids)
        ]

    def get_batch_to_process(self, event_code, batch_size=100):
        events = self.search(
            [
                ('event_code', '=', event_code),
                ('state', '=', 'new'),
            ],
            order='scheduled_at asc',
            limit=batch_size,
        )
        events.lock_for_update()
        return events

    @api.model
    def schedule_events(self, values):
        vals_list = [
            {
                'model_id': self.env['ir.model']._get_id(val['record']._name),
                'res_id': val['record'].id,
                'event_code': val['event_code'],
                'data': val.get('data', {}),
                'scheduled_at': val.get('scheduled_at', fields.Datetime.now()),
            } for val in values
        ]
        self.create(vals_list)

    @api.model
    def _cron_clean_events(self):
        self.search([('state', 'in', ['done', 'cancel', 'fail']), ('scheduled_at', '<', fields.Datetime.now() - relativedelta(months=1))]).unlink()
