import time
from datetime import datetime, timedelta
from openerp import api, fields, models, _
from openerp.exceptions import UserError

class MessageActivity(models.TransientModel):

    _name = 'message.activity'
    _description = 'Activity Report'

    date1 = fields.Date(string='Start Date' , required=True, default=lambda self: self._get_start_date())
    date2 = fields.Date(string='End Date' , required=True, default=lambda self: self._get_end_date())

    @api.model
    def _get_start_date(self):
        today = datetime.today().strftime('%Y-%m-%d')
        dt = datetime.strptime(today, '%Y-%m-%d')
        start = dt - timedelta(days=dt.weekday(), weeks=1)
        start_date =  start.strftime('%Y-%m-%d')
        return start_date

    @api.model
    def _get_end_date(self):
        today = datetime.today().strftime('%Y-%m-%d')
        dt = datetime.strptime(today, '%Y-%m-%d')
        start = dt - timedelta(days=dt.weekday(), weeks=1)
        end = start + timedelta(days=6)
        end_date = end.strftime('%Y-%m-%d')
        return end_date

    def _build_contexts(self, data):
        result = {}
        result['date1'] = data['form']['date1'] or False
        result['date2'] = data['form']['date2'] or False
        if result['date1'] and result['date2'] and result['date1'] > result['date2']:
            raise UserError(_('Start date must be before end date'))
        return result

    @api.multi
    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date1', 'date2'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report(data)


    def _print_report(self, data):
        return self.env['report'].with_context(landscape=True).get_action(self, 'sagawatransport.report_crm_activity_mail',
                                                                          data=data)
