# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from datetime import datetime
from collections import defaultdict
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import format_date, format_datetime


class res_company(models.Model):
    _inherit = 'res.company'

    l10n_au_kp_enable = fields.Boolean(string='Enable Employment Hero Integration')
    l10n_au_kp_identifier = fields.Char(string='Business Id')
    l10n_au_kp_lock_date = fields.Date(string='Fetch Payrun After', help="Import payruns paied after this date. This date cannot be prior to Lock Date)")
    l10n_au_kp_journal_id = fields.Many2one('account.journal', string='Payroll Journal')

    @api.onchange('fiscalyear_lock_date', 'l10n_au_kp_lock_date')
    def _onchange_exclude_before(self):
        self.l10n_au_kp_lock_date = max(self.l10n_au_kp_lock_date, self.fiscalyear_lock_date)

    def _kp_get_key_and_url(self):
        key = self.env['ir.config_parameter'].get_param('l10n_au_keypay.l10n_au_kp_api_key')
        l10n_au_kp_base_url = self.env['ir.config_parameter'].get_param('l10n_au_keypay.l10n_au_kp_base_url')
        return (key, l10n_au_kp_base_url)

    def _kp_payroll_fetch_journal_entries(self, kp_payrun):
        self.ensure_one()
        key, l10n_au_kp_base_url = self._kp_get_key_and_url()
        # Fetch the journal details: https://api.keypay.com.au/australia/reference/pay-run/au-journal--get
        url = url_join(l10n_au_kp_base_url, 'api/v2/business/%s/journal/%s' % (self.l10n_au_kp_identifier, kp_payrun['id']))
        response = requests.get(url, auth=(key, ''), timeout=10)
        response.raise_for_status()

        line_ids_commands = []
        tax_results = defaultdict(lambda: {'debit': 0, 'credit': 0})
        for kp_journal_item in response.json():
            item_account = self.env['account.account'].search([
                *self.env['account.account']._check_company_domain(self),
                ('deprecated', '=', False),
                '|', ('l10n_au_kp_account_identifier', '=', kp_journal_item['accountCode']), ('code', '=', kp_journal_item['accountCode'])
            ], limit=1, order='l10n_au_kp_account_identifier')
            if not item_account:
                raise UserError(_("Account not found: %s, either create an account with that code or link an existing one to that Employment Hero code", kp_journal_item['accountCode']))

            tax = False
            if kp_journal_item.get('taxCode'):
                tax = self.env['account.tax'].search([
                    *self.env['account.tax']._check_company_domain(self),
                    ('l10n_au_kp_tax_identifier', '=', kp_journal_item['taxCode'])], limit=1)

            if tax:
                tax_compute_result = self.currency_id.round(tax.with_context(force_price_include=True)._compute_amount(abs(kp_journal_item['amount']), 1.0))
                tax_results[tax.id]['debit' if kp_journal_item['isDebit'] else 'credit'] += tax_compute_result
                amount = abs(kp_journal_item['amount']) - tax_compute_result
            else:
                amount = abs(kp_journal_item['amount'])

            line_ids_commands.append((0, 0, {
                'account_id': item_account.id,
                'name': kp_journal_item['reference'],
                'debit': amount if kp_journal_item['isDebit'] else 0,
                'credit': amount if kp_journal_item['isCredit'] else 0,
                'tax_ids': [(4, tax.id, 0)] if tax else False,
            }))

        period_ending_date = datetime.strptime(kp_payrun["payPeriodEnding"], "%Y-%m-%dT%H:%M:%S")

        move = self.env['account.move'].create({
            'journal_id': self.l10n_au_kp_journal_id.id,
            'ref': _("Pay period ending %s (#%s)", format_date(self.env, period_ending_date), kp_payrun['id']),
            'date': datetime.strptime(kp_payrun["datePaid"], "%Y-%m-%dT%H:%M:%S"),
            'line_ids': line_ids_commands,
            'l10n_au_kp_payrun_identifier': kp_payrun['id'],
        })
        move_update_vals = []
        for move_line in move.line_ids.filtered(lambda l: l.tax_line_id):
            line_val = {}
            if move_line.debit:
                line_val['debit'] = tax_results[move_line.tax_line_id.id]['debit']
            else:
                line_val['credit'] = tax_results[move_line.tax_line_id.id]['credit']
            move_update_vals.append((1, move_line.id, line_val))
        move.write({'line_ids': move_update_vals})

        return move

    def _kp_payroll_fetch_payrun(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(_("You don't have the access rights to fetch Employment Hero payrun."))
        key, l10n_au_kp_base_url = self._kp_get_key_and_url()
        if not key or not self.l10n_au_kp_identifier or not self.l10n_au_kp_journal_id:
            raise UserError(_("Company %s does not have the apikey, business_id or the journal_id set", self.name))

        from_formatted_datetime = self.l10n_au_kp_lock_date and datetime.combine(self.l10n_au_kp_lock_date, datetime.min.time()).replace(hour=23, minute=59, second=59)
        from_formatted_datetime = format_datetime(self.env, from_formatted_datetime, dt_format="yyyy-MM-dd'T'HH:mm:ss", tz='UTC')
        keypay_filter = "$filter=DatePaid gt datetime'%s'&" % (from_formatted_datetime) if from_formatted_datetime else ''
        skip = 0
        top = 100
        kp_payruns = []
        while True:
            # Fetch the pay runs: https://api.keypay.com.au/australia/reference/pay-run/au-pay-run--get-pay-runs
            # Use Odata filtering (can only fetch 100 entries at a time): https://api.keypay.com.au/guides/ODataFiltering
            # There is a limit of 5 requests per second but the api do not discard the requests it just waits every 5 answers: https://api.keypay.com.au/guides/Usage
            url = url_join(l10n_au_kp_base_url, "api/v2/business/%s/payrun?%s$skip=%d&$top=%d" % (self.l10n_au_kp_identifier, keypay_filter, skip, top))
            response = requests.get(url, auth=(key, ''), timeout=10)
            response.raise_for_status()
            entries = response.json()
            kp_payruns += entries
            if len(entries) < 100:
                break
            skip += 100
            top += 100

        # We cannot filter using the API as we might run into a 414 Client Error: Request-URI Too Large
        payrun_ids = [kp_payrun['id'] for kp_payrun in kp_payruns]
        processed_payrun_ids = self.env['account.move'].search([('company_id', '=', self.id), ('l10n_au_kp_payrun_identifier', 'in', payrun_ids)])
        processed_payruns = processed_payrun_ids.mapped('l10n_au_kp_payrun_identifier')

        account_moves = self.env['account.move']
        for kp_payrun in kp_payruns:
            # Entry needs to be finalized to have a journal entry
            # Currently no way to filter on boolean via the API...
            if not kp_payrun['isFinalised'] or kp_payrun['id'] in processed_payruns:
                continue

            move = self._kp_payroll_fetch_journal_entries(kp_payrun)
            account_moves += move
        return account_moves

    def _kp_payroll_cron_fetch_payrun(self):
        for company in self.search([('l10n_au_kp_enable', '=', True)]):
            company._kp_payroll_fetch_payrun()
