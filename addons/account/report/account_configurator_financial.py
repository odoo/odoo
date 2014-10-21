# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import models, fields


class AccountReportsConfiguratorFinancial(models.TransientModel):
    _name = 'configurator.financial'
    _inherit = 'configurator.account'

    def _get_account_reports(self):
        return self.env['account.financial.report'].search_read(fields=['name'])

    def _get_default_report(self):
        return self._get_account_reports()[0]['id']

    enable_filter = fields.Boolean(default=False)
    account_report_id = fields.Integer(default=_get_default_report)
    debit_credit = fields.Boolean(default=False)
    label_filter = fields.Char(default='Label')
    fiscalyear_id_cmp = fields.Integer(default=-1)
    filter_cmp = fields.Char(default='filter_no')
    period_from_cmp = fields.Integer(default=False)
    period_to_cmp = fields.Integer(default=False)
    date_from_cmp = fields.Date(default=False)
    date_to_cmp = fields.Date(default=False)
    balance_filter = fields.Boolean(default=False)
    balance_from = fields.Float(default=0.0)
    balance_to = fields.Float(default=0.0)
    balance_absolute = fields.Boolean(default=False)

    def _get_content_data(self, fiscalyear_id):
        content_data = super(AccountReportsConfiguratorFinancial, self)._get_content_data(fiscalyear_id)
        content_data['account_reports'] = self._get_account_reports()
        return content_data

    def _build_comparison_context(self, form_data):
        result = {}
        result['fiscalyear'] = 'fiscalyear_id_cmp' in form_data and form_data['fiscalyear_id_cmp'] or False
        result['journal_ids'] = 'journal_ids' in form_data and form_data['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in form_data and form_data['chart_account_id'] or False
        result['state'] = 'target_move' in form_data and form_data['target_move'] or ''
        if form_data['filter_cmp'] == 'filter_date':
            result['date_from'] = form_data['date_from_cmp']
            result['date_to'] = form_data['date_to_cmp']
        elif form_data['filter_cmp'] == 'filter_period':
            result['period_from'] = form_data['period_from_cmp']
            result['period_to'] = form_data['period_to_cmp']
        return result

    def _specific_format(self, form_data):
        # Configuring filter option "Same period, another year"
        form_data['filter_cmp_extended'] = form_data['filter_cmp']
        if form_data['filter_cmp'] == 'same_period':
            form_data['filter_cmp'] = form_data['filter']
            if form_data['filter'] == 'filter_period':
                form_data['period_from_cmp'] = form_data['period_from']
                form_data['period_to_cmp'] = form_data['period_to']
            elif form_data['filter'] == 'filter_date':
                form_data['date_from_cmp'] = form_data['date_from']
                form_data['date_to_cmp'] = form_data['date_to']

        comparison_context = self._build_comparison_context(form_data)
        form_data['comparison_context'] = comparison_context
        report_name = self.env['account.financial.report'].browse(form_data['account_report_id'])[0]['name']
        form_data['account_report_id'] = [form_data['account_report_id'], report_name]
        return form_data
