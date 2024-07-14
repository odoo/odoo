# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import parse_date
from odoo.tools.float_utils import float_round

class AssetsReport(models.Model):
    _inherit = 'account.report'
    def assets_init_custom_options(self, options, previous_options=None):
        super().assets_init_custom_options(options, previous_options)
        if self.env.company.country_id.code == 'LU':
            options.setdefault('buttons', []).append({
                'name': _('XML'), 'sequence': 30, 'action': 'l10n_lu_export_asset_report_to_xml', 'file_export_type': _('XML')
            })

    def l10n_lu_export_asset_report_to_xml(self, options):
        new_context = self.env.context.copy()
        new_context['report_generation_options'] = options
        new_context['report_generation_options']['report_id'] = self.id
        generate_xml = self.env['l10n_lu.generate.asset.report'].with_context(new_context).create({})
        return generate_xml.get_xml()

    def l10n_lu_asset_report_get_xml_2_0_report_values(self, options):
        """
        Returns the formatted values for the LU eCDF declaration "Tables of acquisitions / amortisable expenditures".
        (https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/AN_TABACAM_TYPE/2020/en/1/preview)
        """
        def _get_assets_data(lines):
            """
            Retrieves additional data (VAT paid, depreciable values) needed for the eCDF declaration
            "Tables of acquisitions / amortisable expenditures", that is not present in the result from _get_lines.
            The information about the VAT paid for the asset is retrieved from the tax's account.move.line
            of the account.move, taken in proportion to the price of the asset.

            :param lines: the result from _get_lines (the various assets)
            :return a dictionary containing:
                * 'tax_amounts': The VAT paid for each asset
                * 'depreciable_values': The depreciable value of each asset
            """
            # ids of asset lines are in the form <account_group>_<asset_id>
            asset_ids = {}
            for line in lines:
                res_model, model_id = self._get_model_info_from_id(line['id'])
                if res_model == 'account.asset':
                    asset_ids[model_id] = line['id']
            assets = self.env['account.asset'].search([('id', 'in', list(asset_ids.keys()))])
            # Check that all assets are in EUR and that the company has EUR as its currency;
            asset_currencies = assets.mapped('currency_id')
            if any([curr != self.env.ref('base.EUR') for curr in list(asset_currencies) + [self.env.company.currency_id]]):
                raise ValidationError(_("Only assets having EUR currency for companies using EUR currency can be reported."))
            depreciable_values = {
                asset_ids.get(asset_id): float(original_value) - float(salvage_value)
                for (asset_id, salvage_value, original_value) in assets.mapped(
                    lambda r: (r.id, r.salvage_value, r.original_value)
                )
            }
            # The tax paid for the products in the asset must be retrieved from the original_move_line_ids
            tax_amounts = {}
            for asset in assets:
                total_tax = 0.00
                for ml in asset.original_move_line_ids:
                    balance = ml.balance
                    if asset.account_asset_id.multiple_assets_per_line and len(asset.original_move_line_ids) == 1:
                        balance /= max(1, int(ml.quantity))
                    for tax in ml.tax_ids:
                        # Take the corresponding tax account.move.line on the account.move if the tax is VAT and debit
                        tax_line = ml.move_id.line_ids.filtered(lambda r: r.tax_line_id == tax and r.tax_repartition_line_id and r.debit)
                        if tax_line:
                            total_tax += tax_line.balance * balance / tax_line.tax_base_amount
                if total_tax:  # only keep taxes with amounts different from 0
                    tax_amounts[asset_ids.get(asset['id'])] = total_tax
            return depreciable_values, tax_amounts

        lu_template_values = self.env['l10n_lu.report.handler'].get_electronic_report_values(options)

        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        values = {
            '233': {'field_type': 'number', 'value': date_from.day},
            '234': {'field_type': 'number', 'value': date_from.month},
            '235': {'field_type': 'number', 'value': date_to.day},
            '236': {'field_type': 'number', 'value': date_to.month}
        }
        options.update({'filter_unfolded_lines': True})
        lines = self._get_lines(options)
        # get additional data not shown in the assets report (tax paid, depreciable value)
        depreciable_values, tax_amounts = _get_assets_data(lines)
        # format the values for XML report
        update_values, expenditures_table, depreciations_table = self._l10n_lu_get_expenditures_and_depreciations_tables(
            lines, tax_amounts, depreciable_values
        )
        values.update(update_values)
        # only add the tables if they contain data
        tables = [table for table in (expenditures_table, depreciations_table) if table]

        lu_template_values.update({
            'forms': [{
                'declaration_type': 'AN_TABACAM',
                'year': date_from.year,
                'period': '1',
                'currency': self.env.company.currency_id.name,
                'model': '1',
                'field_values': values,
                'tables': tables
            }]
        })
        return lu_template_values

    def _l10n_lu_get_expenditures_and_depreciations_tables(self, lines, tax_amounts, depreciable_values):
        """
        Returns the table to fill in the LU declaration "Tables of acquisitions / amortisable expenditures".

        :param lines: the lines from account.report's _get_lines
        :param tax_amounts: dict containing the total tax paid on each asset
        :param depreciable_values: dict containing the depreciable amounts for each asset
        :return the formatted "Table of acquisitions", "Table of amortisable expenditures", and the table totals
        """
        update_values = {}
        expenditures_table = []
        depreciations_table = []

        n_expenditure = 0
        for line in lines:
            acquisition_date = parse_date(self.env, parse_date(self.env, line['columns'][0].get('name', '')))
            if self._get_model_info_from_id(line['id'])[0] != 'account.asset' or isinstance(acquisition_date, (str, type(None))):
                # only 2 levels are  possible, level 0 are totals
                continue
            acquisition_date = acquisition_date.strftime('%d%m%Y')
            # Update expenditures table
            n_expenditure += 1
            name = line['name']
            acquisition_cost_no_vat = float(line['columns'][4].get('no_format', 0)) + float(line['columns'][5].get('no_format', 0))
            vat = float(tax_amounts.get(line['id'], 0.))
            value_to_be_depreciated = float(depreciable_values.get(line['id'], 0))
            expenditures_line = {
                '501': {'field_type': 'number', 'value': str(n_expenditure)},
                '502': {'field_type': 'char', 'value': acquisition_date},
                '503': {'field_type': 'char', 'value': name}
            }
            if vat:
                expenditures_line.update({
                    '504': {'field_type': 'float', 'value': float_round((acquisition_cost_no_vat + vat), 2)},
                    '505': {'field_type': 'float', 'value': float_round(vat, 2)},
                })
            expenditures_line['506'] = {'field_type': 'float', 'value': float_round(acquisition_cost_no_vat, 2)}
            expenditures_line['508'] = {'field_type': 'float', 'value': float_round(value_to_be_depreciated, 2)}
            expenditures_table.append(expenditures_line)

            # Update Depreciation/amortisation table
            depreciation_or_amortisation = float(line['columns'][3].get('name', '')[:-2] or 0)  # remove ' %' sign
            # Book value at the beginning of the reported accounting period (not reported by super's _get_lines)
            # asset_opening (acquisition price at the beginning of the accounting period)
            #  - depreciation_opening (depreciated value at the beginning of the accounting period)
            book_value_beginning = float(line['columns'][4].get('no_format', 0)) - float(line['columns'][8].get('no_format', 0))
            acquisitions = float(line['columns'][5].get('no_format', 0))
            sales = float(line['columns'][6].get('no_format', 0))
            # Depreciation reported from _get_lines divided in value decrease (+) and value increase (-);
            # depreciation is the net difference
            depreciation = float(line['columns'][9].get('no_format', 0)) - float(line['columns'][10].get('no_format', 0))
            book_value_end = float(line['columns'][12].get('no_format', 0))
            depreciations_line = {
                '617': {'field_type': 'number', 'value': str(n_expenditure)},
                '602': {'field_type': 'char', 'value': acquisition_date},
                '601': {'field_type': 'char', 'value': name},
                '603': {'field_type': 'float', 'value': float_round(value_to_be_depreciated, 2)},
                '604': {'field_type': 'float', 'value': float_round(depreciation_or_amortisation, 2)},
                '605': {'field_type': 'float', 'value': float_round(book_value_beginning, 2)},
                '606': {'field_type': 'float', 'value': float_round(acquisitions, 2)},
                '607': {'field_type': 'float', 'value': float_round(sales, 2)},
                '608': {'field_type': 'float', 'value': float_round(depreciation, 2)},
                '609': {'field_type': 'float', 'value': float_round(book_value_end, 2)}
            }
            # the following fields are not required in the report; only report if they are different from 0
            for key in range(604, 610):
                if depreciations_line.get(str(key)) and depreciations_line[str(key)]['value'] == 0.00:
                    depreciations_line.pop(str(key))
            depreciations_table.append(depreciations_line)

        # Expenditures table totals
        total_vat = sum([i.get('505', {'value': 0.00})['value'] for i in expenditures_table])
        total_acquisition_cost = sum([i['506']['value'] for i in expenditures_table])
        totals_expenditures_table = {
            '509': {'field_type': 'float', 'value': total_vat},
            '510': {'field_type': 'float', 'value': total_acquisition_cost}
        }
        # Depreciations table totals
        total_book_value_beginning = sum([i.get('605') and i['605']['value'] or 0.0 for i in depreciations_table])
        total_acquisitions = sum([i.get('606') and i['606']['value'] or 0.0 for i in depreciations_table])
        total_sales = sum([i.get('607') and i['607']['value'] or 0.0 for i in depreciations_table])
        total_depreciation = sum([i.get('608') and i['608']['value'] or 0.0 for i in depreciations_table])
        total_book_value_end = sum([i.get('609') and i['609']['value'] or 0.0 for i in depreciations_table])
        totals_depreciations_table = {
            '610': {'field_type': 'float', 'value': total_book_value_beginning},
            '611': {'field_type': 'float', 'value': total_acquisitions},
            '612': {'field_type': 'float', 'value': total_sales},
            '613': {'field_type': 'float', 'value': total_depreciation},
            '614': {'field_type': 'float', 'value': total_book_value_end}
        }
        # for now, everything is considered business portion; so no private part => 615 not filled in
        if totals_depreciations_table['613']['value'] != 0.00:
            totals_depreciations_table['616'] = {'field_type': 'float', 'value': totals_depreciations_table['613']['value']}

        update_values.update(totals_expenditures_table)
        update_values.update(totals_depreciations_table)
        return update_values, expenditures_table, depreciations_table
