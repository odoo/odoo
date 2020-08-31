# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.web.controllers.main import clean_action


class analytic_report(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'account.analytic.report'
    _description = 'Account Analytic Report'

    # the line with this id will contain analytic accounts without a group
    DUMMY_GROUP_ID = 'group_for_accounts_with_no_group'

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_analytic = True
    filter_hierarchy = False
    filter_unfold_all = False

    def _get_columns_name(self, options):
        return [{'name': ''},
                {'name': _('Reference')},
                {'name': _('Partner')},
                {'name': _('Balance'), 'class': 'number'}]

    @api.model
    def _get_report_name(self):
        return _('Analytic Report')

    def open_analytic_entries(self, options, params):
        action = self.env.ref('analytic.account_analytic_line_action').read()[0]
        action = clean_action(action)
        action['context'] = {
            'active_id': int(params['id'].split('analytic_account_')[1]),
        }
        return action

    def _get_amount_of_parents(self, group):
        return self.env['account.analytic.group'].search_count([('id', 'parent_of', group.id)])

    def _get_balance_for_group(self, group, analytic_line_domain):
        analytic_line_domain_for_group = list(analytic_line_domain)
        if group:
            # take into account the hierarchy on account.analytic.line
            analytic_line_domain_for_group += [('group_id', 'child_of', group.id)]
        else:
            analytic_line_domain_for_group += [('group_id', '=', False)]

        currency_obj = self.env['res.currency']
        user_currency = self.env.company.currency_id
        analytic_lines = self.env['account.analytic.line'].read_group(analytic_line_domain_for_group, ['amount', 'currency_id'], ['currency_id'])
        balance = sum([currency_obj.browse(row['currency_id'][0])._convert(
            row['amount'], user_currency, self.env.company, fields.Date.today()) for row in analytic_lines])
        return balance

    def _generate_analytic_group_line(self, group, analytic_line_domain, unfolded=False):
        LOWEST_LEVEL = 1
        balance = self._get_balance_for_group(group, analytic_line_domain)

        line = {
            'columns': [{'name': ''},
                        {'name': ''},
                        {'name': self.format_value(balance)}],
            'unfoldable': True,
            'unfolded': unfolded,
        }

        if group:
            line.update({
                'id': group.id,
                'name': group.name,
                'level': LOWEST_LEVEL + self._get_amount_of_parents(group),
                'parent_id': group.parent_id.id,  # to make these fold when the original parent gets folded
            })
        else:
            line.update({
                'id': self.DUMMY_GROUP_ID,
                'name': _('Accounts without a group'),
                'level': LOWEST_LEVEL + 1,
                'parent_id': False,
            })

        return line

    def _generate_analytic_account_lines(self, analytic_accounts, parent_id=False):
        lines = []

        for account in analytic_accounts:
            lines.append({
                'id': 'analytic_account_%s' % account.id,
                'name': account.name,
                'columns': [{'name': account.code},
                            {'name': account.partner_id.display_name},
                            {'name': self.format_value(account.balance)}],
                'level': 4,  # todo check redesign financial reports, should be level + 1 but doesn't look good
                'unfoldable': False,
                'caret_options': 'account.analytic.account',
                'parent_id': parent_id,  # to make these fold when the original parent gets folded
            })

        return lines

    @api.model
    def _get_lines(self, options, line_id=None):
        AccountAnalyticGroup = self.env['account.analytic.group']
        lines = []
        parent_group = AccountAnalyticGroup
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        # context is set because it's used for the debit, credit and balance computed fields
        AccountAnalyticAccount = self.env['account.analytic.account'].with_context(from_date=date_from,
                                                                                   to_date=date_to)
        # The options refer to analytic entries. So first determine
        # the subset of analytic categories we have to search in.
        analytic_entries_domain = [('date', '>=', date_from),
                                   ('date', '<=', date_to)]
        analytic_account_domain = []
        analytic_account_ids = []
        analytic_tag_ids = []

        if options['analytic_accounts']:
            analytic_account_ids = [int(id) for id in options['analytic_accounts']]
            analytic_entries_domain += [('account_id', 'in', analytic_account_ids)]
            analytic_account_domain += [('id', 'in', analytic_account_ids)]

        if options.get('analytic_tags'):
            analytic_tag_ids = [int(id) for id in options['analytic_tags']]
            analytic_entries_domain += [('tag_ids', 'in', analytic_tag_ids)]
            AccountAnalyticAccount = AccountAnalyticAccount.with_context(tag_ids=analytic_tag_ids)

        if options.get('multi_company'):
            company_ids = [company['id'] for company in options['multi_company'] if company['selected']]
            if company_ids:
                analytic_entries_domain += [('company_id', 'in', company_ids)]
                analytic_account_domain += ['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]
                AccountAnalyticAccount = AccountAnalyticAccount.with_context(company_ids=company_ids)

        if not options['hierarchy']:
            return self._generate_analytic_account_lines(AccountAnalyticAccount.search(analytic_account_domain))

        # display all groups that have accounts
        analytic_accounts = AccountAnalyticAccount.search(analytic_account_domain)
        analytic_groups = analytic_accounts.mapped('group_id')

        # also include the parent analytic groups, even if they didn't have a child analytic line
        if analytic_groups:
            analytic_groups = AccountAnalyticGroup.search([('id', 'parent_of', analytic_groups.ids)])

        domain = [('id', 'in', analytic_groups.ids)]

        if line_id:
            parent_group = AccountAnalyticGroup if line_id == self.DUMMY_GROUP_ID else AccountAnalyticGroup.browse(int(line_id))
            domain += [('parent_id', '=', parent_group.id)]

            # the engine replaces line_id with what is returned so
            # first re-render the line that was just clicked
            lines.append(self._generate_analytic_group_line(parent_group, analytic_entries_domain, unfolded=True))

            # append analytic accounts part of this group, taking into account the selected options
            analytic_account_domain += [('group_id', '=', parent_group.id)]

            analytic_accounts = AccountAnalyticAccount.search(analytic_account_domain)
            lines += self._generate_analytic_account_lines(analytic_accounts, parent_group.id if parent_group else self.DUMMY_GROUP_ID)
        else:
            domain += [('parent_id', '=', False)]

        # append children groups unless the dummy group has been clicked, it has no children
        if line_id != self.DUMMY_GROUP_ID:
            for group in AccountAnalyticGroup.search(domain):
                if group.id in options.get('unfolded_lines') or options.get('unfold_all'):
                    lines += self._get_lines(options, line_id=str(group.id))
                else:
                    lines.append(self._generate_analytic_group_line(group, analytic_entries_domain))

        # finally append a 'dummy' group which contains the accounts that do not have an analytic group
        if not line_id and any(not account.group_id for account in analytic_accounts):
            if self.DUMMY_GROUP_ID in options.get('unfolded_lines'):
                lines += self._get_lines(options, line_id=self.DUMMY_GROUP_ID)
            else:
                lines.append(self._generate_analytic_group_line(AccountAnalyticGroup, analytic_entries_domain))

        return lines

    @api.model
    def _create_hierarchy(self, lines, options):
        # OVERRIDE because the hierarchy is managed in _get_lines.
        return lines
