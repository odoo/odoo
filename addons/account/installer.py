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

from openerp import api, fields, models, _
from openerp.exceptions import UserError

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
        self._cr.execute("SELECT company_id FROM account_account WHERE deprecated = 'f' AND name != 'Chart For Automated Tests' AND name NOT LIKE '%(test)'")
        configured_cmp = [r[0] for r in self._cr.fetchall()]
        return list(set(company_ids.ids) - set(configured_cmp))

    @api.model
    def check_unconfigured_cmp(self):
        """ check if there are still unconfigured companies """
        if not self.get_unconfigured_cmp():
            raise UserError(_("There is currently no company without chart of account. The wizard will therefore not be executed."))

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

    @api.multi
    def execute(self):
        return super(account_installer, self).execute()

    @api.multi
    def modules_to_install(self):
        modules = super(account_installer, self).modules_to_install()
        _logger.debug('Installing chart of accounts %s', self.charts)
        return (modules | set([self.charts])) - set(['has_default_company', 'configurable'])
