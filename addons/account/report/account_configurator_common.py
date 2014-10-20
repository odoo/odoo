from openerp import models, fields
import time


class AccountReportsConfigurator(models.AbstractModel):
    _name = 'account.report.configurator'

    def get_configurator(self, reportname):
        return self.env['configurator.%s' % reportname]


class AccountReportsConfiguratorCommon(models.TransientModel):
    _name = 'configurator.common'

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Default methods
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def _get_default_account(self):
        return self._get_accounts()[0]['id']

    def _get_accounts(self):
        user = self.env['res.users'].browse(self.env.uid)
        domain = [('parent_id', '=', False), ('company_id', '=', user.company_id.id)]
        return self.env['account.account'].search_read(fields=['name'], domain=domain)

    def _get_default_fiscalyear(self):
        return self._get_fiscalyears()[0]['id']

    def _get_fiscalyears(self):
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self.env.context.get('active_ids', [])
        if ids and self.env.context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env.user.company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        return self.env['account.fiscalyear'].search_read(domain=domain, fields=['name'])

    def _get_default_journals(self):
        return self.env['account.journal'].search([])

    chart_account_id = fields.Integer(default=_get_default_account)
    fiscalyear_id = fields.Integer(default=_get_default_fiscalyear)
    filter = fields.Char(default='filter_no')
    period_from = fields.Integer(default=False)
    period_to = fields.Integer(default=False)
    journal_ids = fields.Many2many('account.journal', default=_get_default_journals)
    date_from = fields.Date(default=False)
    date_to = fields.Date(default=False)
    target_move = fields.Char(default='posted')

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Others methods
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def _get_periods(self, fiscalyear_id):
        domain = [('fiscalyear_id', '=', fiscalyear_id)]
        periods = self.env['account.period'].search_read(domain=domain, fields=['name'])
        return periods

    def _get_journals(self):
        return self.env['account.journal'].search_read(domain=[], fields=['name', 'code'])

    def _build_contexts(self, form_data):
        result = {}
        result['fiscalyear'] = 'fiscalyear_id' in form_data and form_data['fiscalyear_id'] or False
        result['journal_ids'] = 'journal_ids' in form_data and form_data['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in form_data and form_data['chart_account_id'] or False
        result['state'] = 'target_move' in form_data and form_data['target_move'] or ''
        if form_data['filter'] == 'filter_date':
            result['date_from'] = form_data['date_from']
            result['date_to'] = form_data['date_to']
        elif form_data['filter'] == 'filter_period':
            result['period_from'] = form_data['period_from']
            result['period_to'] = form_data['period_to']
        return result

    def _get_content_data(self, fiscalyear_id):
        content_data = {}
        content_data['accounts'] = self._get_accounts()
        content_data['fiscalyears'] = self._get_fiscalyears()
        content_data['journals'] = self._get_journals()
        content_data['periods'] = self._get_periods(fiscalyear_id)
        return content_data

    def _specific_format(self, form_data):
        return form_data

    def to_report_sxw_dict(self, **kwargs):
        context = self.env.context

        form_data = {}
        for field in self.fields_get().keys():
            if field in kwargs:
                form_data[field] = kwargs[field]
                if form_data[field] == 'True':
                    form_data[field] = True
                try:
                    form_data[field] = int(form_data[field])
                except ValueError:
                    pass
            else:
                res = self.default_get([field])
                if field in res:
                    form_data[field] = res[field]

        form_data['filter_extended'] = form_data['filter']
        if form_data['filter_extended'] == 'ytd':
            form_data['filter'] = 'filter_date'
            form_data['date_from'] = self.env['account.fiscalyear'].browse(form_data['fiscalyear_id']).date_start
            form_data['date_to'] = time.strftime('%Y-%m-%d')

        if isinstance(form_data['journal_ids'][0], tuple):
            form_data['journal_ids'] = form_data['journal_ids'][0][2]
        if 'journal_ids' in kwargs and kwargs['journal_ids']:
            journal_ids = kwargs['journal_ids'].lstrip('[').rstrip(']')
            temp = journal_ids.split(',')
            form_data['journal_ids'] = []
            for x in temp:
                form_data['journal_ids'].append(int(str(x).lstrip(" u'").rstrip("'")))

        if 'add_journal' in kwargs and 'add_journal_id' in kwargs:
            form_data['journal_ids'].append(int(str(kwargs['add_journal_id']).lstrip(" u'").rstrip("'")))
        if 'remove_journal' in kwargs and 'remove_journal_id' in kwargs:
            form_data['journal_ids'].remove(int(kwargs['remove_journal_id']))

        used_context = self._build_contexts(form_data)
        form_data['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        form_data['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        form_data['content'] = self._get_content_data(form_data['fiscalyear_id'])

        form_data = self._specific_format(form_data)

        return {'model': context.get('active_model', 'ir.ui.menu'), 'ids': context.get('active_ids', []), 'form': form_data}
