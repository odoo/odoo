# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
import logging
from operator import itemgetter
import time
import urllib2
import urlparse

try:
    import simplejson as json
except ImportError:
    import json     # noqa

from openerp.release import serie
from openerp import models, fields, api, _
from openerp.exceptions import Warning
_logger = logging.getLogger(__name__)


class account_installer(models.TransientModel):
    _name = 'account.installer'
    _inherit = 'res.config.installer'

    @api.model
    def _get_charts(self):
        ModuleObj = self.env['ir.module.module']

        # try get the list on apps server
        try:
            apps_server = ModuleObj.get_apps_server()

            up = urlparse.urlparse(apps_server)
            url = '{0.scheme}://{0.netloc}/apps/charts?serie={1}'.format(up, serie)

            j = urllib2.urlopen(url, timeout=3).read()
            apps_charts = json.loads(j)

            charts = dict(apps_charts)
        except Exception:
            charts = dict()

        # Looking for the module with the 'Account Charts' category
        category_id = self.env.ref('base.module_category_localization_account_charts')
        recs = ModuleObj.search([('category_id', '=', category_id.id)])
        if recs:
            charts.update((m.name, m.shortdesc) for m in recs)

        charts = sorted(charts.items(), key=itemgetter(1))
        charts.insert(0, ('configurable', _('Custom')))
        return charts


    # Accounting
    charts = fields.Selection(_get_charts, string='Accounting Package', required=True, default='configurable',
        help="Installs localized accounting charts to match as closely as "
             "possible the accounting needs of your company based on your "
             "country.")
    date_start = fields.Date(string='Start Date', required=True, default=lambda *a: time.strftime('%Y-01-01'))
    date_stop = fields.Date(string='End Date', required=True, default=lambda *a: time.strftime('%Y-12-31'))
    period = fields.Selection([('month', 'Monthly'), ('3months', '3 Monthly')], 
        string='Periods', required=True, default='month')
    company_id = fields.Many2one('res.company', string='Company', required=True, 
        default=lambda self: self.env.user.company_id or False)
    has_default_company = fields.Boolean(string='Has Default Company',
        readonly=True, default=lambda self: self._default_has_default_company())


    @api.model
    def _default_has_default_company(self):
        count = self.env['res.company'].search_count([])
        return bool(count == 1)

    @api.model
    def get_unconfigured_cmp(self):
        """ get the list of companies that have not been configured yet
        but don't care about the demo chart of accounts """
        company_ids = self.env['res.company'].search([])
        account_ids = self.env['account.account'].search([('deprecated', '=', False), ('name', '!=', 'Chart For Automated Tests')])
        configured_cmp = [account.company_id.id for account in account_ids]
        return list(set(company_ids.ids) - set(configured_cmp))

    @api.model
    def check_unconfigured_cmp(self):
        """ check if there are still unconfigured companies """
        if not self.get_unconfigured_cmp():
            raise Warning(_("There is currently no company without chart of account. The wizard will therefore not be executed."))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(account_installer, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        cmp_select = []
        CompanyObj = self.env['res.company']
        # display in the widget selection only the companies that haven't been configured yet
        unconfigured_cmp = self.get_unconfigured_cmp()
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id', 'in', unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in CompanyObj.browse(unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    @api.onchange('date_start')
    def on_change_start_date(self):
        if self.date_start:
            start_date = datetime.datetime.strptime(self.date_start, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            self.date_stop = end_date.strftime('%Y-%m-%d')

    @api.multi
    def execute(self):
        self.execute_simple()
        return super(account_installer, self).execute()

    @api.multi
    def execute_simple(self):
        fy_obj = self.env['account.fiscalyear']
        for res in self:
            if res.date_start and res.date_stop:
                fiscal_year = fy_obj.search([('date_start', '<=', res.date_start), ('date_stop', '>=', res.date_stop), ('company_id', '=', res.company_id.id)], limit=1)
                if not fiscal_year:
                    name = code = res.date_start[:4]
                    if int(name) != int(res.date_stop[:4]):
                        name = res.date_start[:4] + '-' + res.date_stop[:4]
                        code = resdate_start[2:4] + '-' + res.date_stop[2:4]
                    vals = {
                        'name': name,
                        'code': code,
                        'date_start': res.date_start,
                        'date_stop': res.date_stop,
                        'company_id': res.company_id.id
                    }
                    fiscal_year = fy_obj.create(vals)
                    if res.period == 'month':
                        fiscal_year.create_period()
                    elif res.period == '3months':
                        fiscal_year.create_period3()

    @api.multi
    def modules_to_install(self):
        modules = super(account_installer, self).modules_to_install()
        _logger.debug('Installing chart of accounts %s', self.charts)
        return (modules | set([self.charts])) - set(['has_default_company', 'configurable'])
