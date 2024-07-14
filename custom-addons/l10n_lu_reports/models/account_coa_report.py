# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from ..models.coa_data import ACCOUNTS_2020, ACCOUNTS_2019

class AccountChartOfAccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def l10n_lu_get_xml_2_0_report_coa_values(self, options, avg_nb_employees=1, size='small',
                                      pl='full', bs='full', coa_only=False, optional_remarks=''):
        """
        Returns the formatted report values for LU's Chart of Accounts financial report.
        (2020: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_PLANCOMPTA/2020/en/2/preview)
        (2019: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_PLANCOMPTA/2019/en/1/preview)
        """

        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        values = {
            '01': {'value': date_from.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '02': {'value': date_to.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '03': {'value': self.env.company.currency_id.name, 'field_type': 'char'}
        }

        # Get the appropriate mapping account-fields
        account_dict = None
        if date_from.year >= 2020:
            account_dict = ACCOUNTS_2020
        elif date_from.year == 2019:
            account_dict = ACCOUNTS_2019
        else:
            raise ValidationError(_("CoA report for Luxembourg not supported for years previous to 2019."))

        # Stores the values for the account fields (debit/credit)
        account_fields = self.l10n_lu_coa_report_get_account_fields(options, account_dict, date_from.year)

        # The fields 0161/0162, corresponding to the accounts 142xxx (results for the financial year)
        # have to be manually filled in in 2019 to balance the report
        if date_from.year <= 2019:
            update_fields, net142 = self.l10n_lu_coa_report_assemble_results_financial_year(account_fields)
            account_fields.update(update_fields)
            # Update class total 1-5 and set net debit or credit only
            net1to5 = account_fields.get('1111', 0.00) - account_fields.get('1112', 0.00) + net142
            if float_compare(net1to5, 0.0, 2) > 0:
                account_fields['1111'] = net1to5
                account_fields.pop('1112', None)
            else:
                account_fields['1112'] = -net1to5
                account_fields.pop('1111', None)

        # 2020 new totals
        if date_from.year >= 2020:
            account_fields['2957'] = account_fields.get('1111', 0.00) + account_fields.get('2257', 0.00)
            account_fields['2958'] = account_fields.get('1112', 0.00) + account_fields.get('2258', 0.00)
            account_fields['0161'] = account_fields.get('1111', 0.00) - account_fields.get('1112', 0.00)

        # Default required fields to 0.00
        for val in account_dict.values():
            if val.get("required", False) and val["debit"] not in account_fields and val["credit"] not in account_fields:
                account_fields[val["credit"]] = 0.00

        # Value for fields 2259-60: must be manually computed here since the value of "106 Account of the owner or the co-owners"
        # is asked twice (once in the report at fields 0117-8, once in the annex in fields 2259-60)
        if account_fields.get('2261') or account_fields.get('2262') or account_fields.get('2347') or account_fields.get('2348'):
            net106 = account_fields.get('2261', 0.00) - account_fields.get('2262', 0.00) + account_fields.get('2347', 0.00) - account_fields.get('2348', 0.00)
            if float_compare(net106, 0.0, 2) > 0:
                account_fields['2259'] = net106
            else:
                account_fields['2260'] = - net106

        # Format everything
        for key in account_fields:
            account_fields[key] = {'value': account_fields[key], 'field_type': 'float'}
        # and add to values
        values.update(account_fields)

        # Average number of employees (from wizard)
        values['2939'] = {'value': avg_nb_employees, 'field_type': 'float'}

        # Optional remarks
        if optional_remarks:
            values['2385'] = {'value': optional_remarks, 'field_type': 'char'}

        # Size and abridged/non abridged fields
        if date_from.year >= 2020 and not coa_only:
            values.update(self.l10n_lu_coa_report_get_size_and_abr_versions_fields(size, pl, bs))

        # Chart of Accounts only
        if coa_only and date_from.year >= 2020:
            values['2952'] = {'value': '1', 'field_type': 'boolean'}

        model = 2 if date_from.year == 2020 else 1

        return {
            'declaration_type': "CA_PLANCOMPTA",
            'year': date_from.year,
            'period': "1",
            'field_values': values,
            'model': model
        }

    def l10n_lu_coa_report_get_account_fields(self, options, account_dict, year):
        """ Get the account fields.

            :param options: the context options
            :param account_dict: the dictionary mapping accounts to fields
            :return: a dictionary in which the values for the different fields (dict keys) are filled in
        """
        account_fields = {}
        lines = self._get_lines(self.get_options(options))
        # Read the debit and credit from all accounts and add the values to the corresponding fields.
        # Name hierarchy allows easy calculation of the totals.
        # eg the debit from account 106284 will be added to the fields: 106284, 10628, 1062, 106, 10
        # Account data lines have as id the id of the account.account record;
        # total report line has 'grouped_accounts_total' string as id and must be filtered out
        for line in [ln for ln in lines if self._get_model_info_from_id(ln.get('id'))[0] == 'account.account']:
            code = line.get('name').split()[0]
            # Code of account being reported in the P&L: result for the year
            p_l_code = code[0] in ('6', '7')
            if p_l_code:
                debit = float(line['columns'][2]['no_format'])
                credit = float(line['columns'][3]['no_format'])
            # Code of account being reported in the Balance Sheet: total
            else:
                debit = float(line['columns'][4]['no_format'])
                credit = float(line['columns'][5]['no_format'])
            # 142 (results for the financial year) will be manually calculated to balance as required
            if code[:3] == '142' and year <= 2019:
                continue
            for i in range(len(code)):
                acc = account_dict.get(code[:i + 1])
                balance = debit - credit
                if acc:
                    if balance > 0.00:
                        account_fields[acc["debit"]] = account_fields.get(acc["debit"], 0.00) + balance
                    # Accounts at 0.00 not counted because they might be accounts from an old CoA
                    # being moved to another account
                    elif balance < 0.00:
                        account_fields[acc["credit"]] = account_fields.get(acc["credit"], 0.00) - balance

        # Fields are mandatory from 2020 on
        if year >= 2020:
            account_fields['1111'] = 0.00
            account_fields['1112'] = 0.00
            account_fields['2257'] = 0.00
            account_fields['2258'] = 0.00

        # Calculate net debit/credit, and only fill the column with a positive value
        for account_code in account_dict:
            # The account 513001 isn't "natively" supported anymore, since accounts like 513% have to be further divided into 5131% and 5132%
            # Hence, its debit is redirected onto field 2533 (debit of 5131) and its credit onto field 2536 (credit of 5132);
            # these are however 2 different lines and they should NOT be balanced!
            if (account_fields.get(account_dict[account_code]["debit"]) or account_fields.get(account_dict[account_code]["credit"])) \
                    and not (account_dict[account_code]["debit"] == '2533' and account_dict[account_code]["credit"] == '2536'):
                net = account_fields.get(account_dict[account_code]["debit"], 0.00) - account_fields.get(account_dict[account_code]["credit"], 0.00)
                if float_compare(net, 0.0, 2) > 0:
                    account_fields[account_dict[account_code]["debit"]] = net
                    if account_dict[account_code]["credit"] in account_fields:
                        del account_fields[account_dict[account_code]["credit"]]
                else:
                    account_fields[account_dict[account_code]["credit"]] = -net
                    if account_dict[account_code]["debit"] in account_fields:
                        del account_fields[account_dict[account_code]["debit"]]
                # Total classes (as opposed to child lines, not balanced; sum of debits and sum of credits)
                if len(account_code) == 2:
                    if account_code[0] in ['1', '2', '3', '4', '5']:
                        if net > 0.00:
                            account_fields['1111'] = account_fields.get('1111', 0.00) + net
                        else:
                            account_fields['1112'] = account_fields.get('1112', 0.00) - net
                    elif account_code[0] in ['6', '7']:
                        if net > 0.00:
                            account_fields['2257'] = account_fields.get('2257', 0.00) + net
                        else:
                            account_fields['2258'] = account_fields.get('2258', 0.00) - net

        # If the report is for a year earlier than 2020, calculate net debit/credit for the total of classes 6-7
        # and only fill the column with a positive value.
        # The same will be done for classes 1-5 later, when the result for the financial year 142 is calculated.
        if year <= 2019:
            net6to7 = account_fields.get('2257', 0.00) - account_fields.get('2258', 0.00)
            if float_compare(net6to7, 0.0, 2) > 0:
                account_fields['2257'] = net6to7
                account_fields.pop('2258', None)
            else:
                account_fields['2258'] = -net6to7
                account_fields.pop('2257', None)

        return account_fields

    @api.model
    def l10n_lu_coa_report_assemble_results_financial_year(self, account_fields):
        """ Gets the fields corresponding to the result for the financial year (142).
            This is computed as the total debit for classes 6 to 7 minus the total credit for classes 6 to 7.
            Updates the values of the totals of classes 1-5.

            :param account_fields: the dictionary with the values for the different report fields.
            :returns: a dictionary with the evaluated fields with the results for the financial year and classes 1-5 total,
                      + the value of the net result for the financial year
        """
        update_fields = {}
        net142 = account_fields.get('2257', 0.00) - account_fields.get('2258', 0.00)
        if float_compare(net142, 0.0, 2) > 0:
            update_fields['0161'] = net142
        else:
            update_fields['0162'] = - net142
            net142 = account_fields.get('2257', 0.00) - account_fields.get('2258', 0.00)
        net14 = (account_fields.get('0159', 0.00) + update_fields.get('0161', 0.00)) - (account_fields.get('0160', 0.00) + update_fields.get('0162', 0.00))
        if float_compare(net14, 0.0, 2) > 0:
            update_fields['0157'] = net14
        else:
            update_fields['0158'] = -net14
        return update_fields, net142

    @api.model
    def l10n_lu_coa_report_get_size_and_abr_versions_fields(self, size, pl, bs):
        """ Gets the fields corresponding to the company size and report versions (full or abridged).

            :param size: the size of the report's company
            :param pl: the version of the profit and loss report (full or abridged)
            :param bs: the version of the balance sheet report (full or abridged)
            :return: a dictionary with the formatted values for the size and report type sections
        """
        update_values = {}
        if size == 'large':
            update_values['2940'] = {'value': '1', 'field_type': 'boolean'}
            update_values['2941'] = {'value': '1', 'field_type': 'boolean'}
            update_values['2942'] = {'value': '1', 'field_type': 'boolean'}
        elif size == 'medium':
            update_values['2943'] = {'value': '1', 'field_type': 'boolean'}
            update_values['2944'] = {'value': '1', 'field_type': 'boolean'}
            if pl == 'abr':
                update_values['2945'] = {'value': '1', 'field_type': 'boolean'}
            else:
                update_values['2946'] = {'value': '1', 'field_type': 'boolean'}
        elif size == 'small':
            update_values['2947'] = {'value': '1', 'field_type': 'boolean'}
            if bs == 'abr':
                update_values['2948'] = {'value': '1', 'field_type': 'boolean'}
            else:
                update_values['2950'] = {'value': '1', 'field_type': 'boolean'}
            if pl == 'abr':
                update_values['2949'] = {'value': '1', 'field_type': 'boolean'}
            else:
                update_values['2951'] = {'value': '1', 'field_type': 'boolean'}
        return update_values
