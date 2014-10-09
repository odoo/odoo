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


class AccountReportsConfiguratorJournal(models.TransientModel):
    _name = 'configurator.journal'
    _inherit = 'configurator.common'

    amount_currency = fields.Boolean(default=False)

    def _specific_format(self, form_data):
        fy_ids = form_data['fiscalyear_id'] and [form_data['fiscalyear_id']] or self.env['account.fiscalyear'].search([('state', '=', 'draft')]).ids
        period_list = form_data['periods'] or self.env['account.period'].search([('fiscalyear_id', 'in', fy_ids)]).ids
        form_data['active_ids'] = self.env['account.journal.period'].search(
            [('journal_id', 'in', form_data['journal_ids']), ('period_id', 'in', period_list)]
        ).ids
        return form_data

    def _build_contexts(self, form_data):
        result = super(AccountReportsConfiguratorJournal, self)._build_contexts(form_data)

        cr = self.env.cr

        if form_data['filter'] == 'filter_date':
            cr.execute('SELECT period_id FROM account_move_line WHERE date >= %s AND date <= %s', (form_data['date_from'], form_data['date_to']))
            result['periods'] = map(lambda x: x[0], cr.fetchall())
        elif form_data['filter'] == 'filter_period':
            result['periods'] = self.env['account.period'].build_ctx_periods(form_data['period_from'], form_data['period_to'])
        return result
