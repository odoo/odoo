# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import time
import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from os.path import join as opj

from tools.translate import _
from osv import fields, osv
import netsvc
import tools
_logger = logging.getLogger(__name__)

class account_installer(osv.osv_memory):
    _name = 'account.installer'
    _inherit = 'res.config.installer'

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        # Looking for the module with the 'Account Charts' category
        category_name, category_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'module_category_localization_account_charts')
        ids = modules.search(cr, uid, [('category_id', '=', category_id)], context=context)
        charts = list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids, context=context)),
                   key=itemgetter(1)))
        charts.insert(0, ('configurable', 'Generic Chart Of Accounts'))
        return charts

    _columns = {
        # Accounting
        'charts': fields.selection(_get_charts, 'Chart of Accounts',
            required=True,
            help="Installs localized accounting charts to match as closely as "
                 "possible the accounting needs of your company based on your "
                 "country."),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period': fields.selection([('month', 'Monthly'), ('3months','3 Monthly')], 'Periods', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'has_default_company' : fields.boolean('Has Default Company', readonly=True),
    }

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id and user.company_id.id or False

    def _default_has_default_company(self, cr, uid, context=None):
        count = self.pool.get('res.company').search_count(cr, uid, [], context=context)
        return bool(count == 1)

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period': 'month',
        'company_id': _default_company,
        'has_default_company': _default_has_default_company,
        'charts': 'configurable'
    }
    
    def get_unconfigured_cmp(self, cr, uid, context=None):
        """ get the list of companies that have not been configured yet
        but don't care about the demo chart of accounts """
        cmp_select = []
        company_ids = self.pool.get('res.company').search(cr, uid, [], context=context)
        cr.execute("SELECT company_id FROM account_account WHERE active = 't' AND account_account.parent_id IS NULL AND name != %s", ("Chart For Automated Tests",))
        configured_cmp = [r[0] for r in cr.fetchall()]
        return list(set(company_ids)-set(configured_cmp))
    
    def check_unconfigured_cmp(self, cr, uid, context=None):
        """ check if there are still unconfigured companies """
        if not self.get_unconfigured_cmp(cr, uid, context=context):
            raise osv.except_osv(_('No unconfigured company !'), _("There is currently no company without chart of account. The wizard will therefore not be executed."))
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:context = {}
        res = super(account_installer, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        cmp_select = []
        # display in the widget selection only the companies that haven't been configured yet
        unconfigured_cmp = self.get_unconfigured_cmp(cr, uid, context=context)
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id','in',unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in self.pool.get('res.company').browse(cr, uid, unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    def on_change_start_date(self, cr, uid, id, start_date=False):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value': {'date_stop': end_date.strftime('%Y-%m-%d')}}
        return {}

    def execute(self, cr, uid, ids, context=None):
        self.execute_simple(cr, uid, ids, context)
        super(account_installer, self).execute(cr, uid, ids, context=context)

    def action_next(self, cr, uid, ids, context=None):
        next = self.execute(cr, uid, ids, context=context)
        for installer in self.browse(cr, uid, ids, context=context):
            if installer.charts == 'l10n_be':
                return {'type': 'ir.actions.act_window_close'}
            else :
                if next : return next
                return self.next(cr, uid, ids, context=context)

    def execute_simple(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        fy_obj = self.pool.get('account.fiscalyear')
        for res in self.read(cr, uid, ids, context=context):
            if 'date_start' in res and 'date_stop' in res:
                f_ids = fy_obj.search(cr, uid, [('date_start', '<=', res['date_start']), ('date_stop', '>=', res['date_stop']), ('company_id', '=', res['company_id'][0])], context=context)
                if not f_ids:
                    name = code = res['date_start'][:4]
                    if int(name) != int(res['date_stop'][:4]):
                        name = res['date_start'][:4] +'-'+ res['date_stop'][:4]
                        code = res['date_start'][2:4] +'-'+ res['date_stop'][2:4]
                    vals = {
                        'name': name,
                        'code': code,
                        'date_start': res['date_start'],
                        'date_stop': res['date_stop'],
                        'company_id': res['company_id'][0]
                    }
                    fiscal_id = fy_obj.create(cr, uid, vals, context=context)
                    if res['period'] == 'month':
                        fy_obj.create_period(cr, uid, [fiscal_id])
                    elif res['period'] == '3months':
                        fy_obj.create_period3(cr, uid, [fiscal_id])

    def modules_to_install(self, cr, uid, ids, context=None):
        modules = super(account_installer, self).modules_to_install(
            cr, uid, ids, context=context)
        chart = self.read(cr, uid, ids, ['charts'],
                          context=context)[0]['charts']
        _logger.debug('Installing chart of accounts %s', chart)
        return modules | set([chart])

account_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
