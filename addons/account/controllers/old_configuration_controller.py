# -*- coding: utf-8 -*-
from openerp.addons.web.http import Controller, route, request
import time


class configuration_controller(Controller):

    def _get_accounts(self, cr, uid, context=None):
        user = request.registry.get('res.users').browse(cr, uid, uid, context=context)
        domain = [('parent_id', '=', False), ('company_id', '=', user.company_id.id)]
        accounts = request.registry.get('account.account').search(cr, uid, domain)
        accounts = request.registry.get('account.account').read(cr, uid, accounts, ['name'])
        return accounts

    def _get_fiscalyears(self, cr, uid, context=None):
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'account.account':
            company_id = request.registry.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = request.registry.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = request.registry.get('account.fiscalyear').search(cr, uid, domain)
        fiscalyears = request.registry.get('account.fiscalyear').read(cr, uid, fiscalyears, ['name'])
        return fiscalyears

    def _get_periods(self, cr, uid, fiscalyear_id, context=None):
        domain = [('fiscalyear_id', '=', fiscalyear_id)]
        periods = request.registry.get('account.period').search(cr, uid, domain)
        periods = request.registry.get('account.period').read(cr, uid, periods, ['name'])
        return periods

    def _get_journals(self, cr, uid, context=None):
        journals = request.registry.get('account.journal').search(cr, uid ,[])
        return request.registry.get('account.journal').read(cr, uid, journals, ['name'])

    def _build_contexts(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter'] == 'filter_date':
            result['date_from'] = data['form']['date_from']
            result['date_to'] = data['form']['date_to']
        elif data['form']['filter'] == 'filter_period':
            result['period_from'] = data['form']['period_from']
            result['period_to'] = data['form']['period_to']
        return result

    def _prepare_data(self, cr, uid, report_name, chart_account_id, fiscalyear_id, target_move, filter, date_from,
                      date_to, period_from, period_to, add_journal, remove_journal, journal_id,
                      journal_ids, context=None):
        data = {}
        data['report_name'] = report_name
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['ids'] = context.get('active_ids', [])
        data['content'] = {}
        data['content']['accounts'] = self._get_accounts(cr, uid, context=context)
        data['content']['fiscalyears'] = self._get_fiscalyears(cr, uid, context=context)
        data['content']['journals'] = self._get_journals(cr, uid, context=context)
        data['form'] = {}
        data['form']['amount_currency'] = False
        if journal_ids:
            journal_ids = journal_ids.lstrip('[').rstrip(']')
            print journal_ids
            temp = journal_ids.split(',')
            data['form']['journal_ids'] = []
            for x in temp:
                data['form']['journal_ids'].append(int(str(x).lstrip(" u'").rstrip("'")))
        else:
            data['form']['journal_ids'] = []
            for x in data['content']['journals']:
                data['form']['journal_ids'].append(x['id'])
        if add_journal:
            data['form']['journal_ids'].append(int(str(journal_id).lstrip(" u'").rstrip("'")))
        if remove_journal:
            data['form']['journal_ids'].remove(int(remove_journal))
        if chart_account_id:
            data['form']['chart_account_id'] = int(chart_account_id)
        else:
            data['form']['chart_account_id'] = data['content']['accounts'][0]['id']
        if fiscalyear_id:
            data['form']['fiscalyear_id'] = int(fiscalyear_id)
        else:
            data['form']['fiscalyear_id'] = data['content']['fiscalyears'][0]['id']
        if target_move:
            data['form']['target_move'] = target_move
        else:
            data['form']['target_move'] = 'posted'
        if filter:
            data['form']['filter'] = filter
        else:
            data['form']['filter'] = 'filter_no'
        data['form']['date_to'] = date_to
        data['form']['date_from'] = date_from
        data['form']['period_from'] = int(period_from)
        data['form']['period_to'] = int(period_to)
        used_context = self._build_contexts(cr, uid, data, context=context)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
        fy_ids = data['form']['fiscalyear_id'] and [data['form']['fiscalyear_id']] or self.pool.get('account.fiscalyear').search(cr, uid, [('state', '=', 'draft')], context=context)
        period_list = data['form']['periods'] or request.registry.get('account.period').search(cr, uid, [('fiscalyear_id', 'in', fy_ids)], context=context)
        data['form']['active_ids'] = request.registry.get('account.journal.period').search(cr, uid, [('journal_id', 'in', data['form']['journal_ids']), ('period_id', 'in', period_list)], context=context)
        data['content']['periods'] = self._get_periods(cr, uid, data['form']['fiscalyear_id'], context=context)
        return data
