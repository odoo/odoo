# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, release, _
from odoo.exceptions import UserError

from datetime import datetime
from collections import defaultdict
from odoo.tools.float_utils import float_round
from odoo.tools import SQL

import calendar

class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'FR':
            return

        if options.get('export_mode') == 'file':
            options['l10n_fr_intrastat_wizard_id'] = previous_options.get('l10n_fr_intrastat_wizard_id')

        options.setdefault('buttons', []).append({
            'name': _('XML (DEBWEB2)'),
            'sequence': 30,
            'action': 'l10n_fr_intrastat_open_export_wizard',
            'file_export_type': 'XML',
        })

    def l10n_fr_intrastat_open_export_wizard(self, options):
        if self.env.company.currency_id.display_name != 'EUR':
            raise UserError(_('The currency of the company must be EUR to generate the XML export'))

        return {
            'name': _('XML (DEBWEB2)'),
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_model': 'l10n_fr_intrastat.export.wizard',
            'type': 'ir.actions.act_window',
            'res_id': False,
            'target': 'new',
            'context': dict(self._context, l10n_fr_intrastat_export_options=options),
        }

    @api.model
    def _retrieve_fr_intrastat_wizard(self, options):
        wizard_id = options.get('l10n_fr_intrastat_wizard_id')
        if not wizard_id:
            return False
        return self.env['l10n_fr_intrastat.export.wizard'].browse(wizard_id)

    def _get_exporting_query_data(self):
        res = super()._get_exporting_query_data()
        return SQL('%s %s', res, SQL("""
                code.supplementary_unit AS supplementary_units_code,
                account_move_line.product_id AS product_id,
                account_move_line.move_id AS move_id,
                account_move_line.partner_id AS partner_id,
        """))

    def _get_exporting_dict_data(self, result_dict, query_res):
        super()._get_exporting_dict_data(result_dict, query_res)
        if self.env.company.account_fiscal_country_id.code == 'FR':
            result_dict.update({
                'system': result_dict['system'][0:2],
                'supplementary_units_code': query_res['supplementary_units_code'],
                'product_id': query_res['product_id'],
                'move_id': query_res['move_id'],
                'partner_id': query_res['partner_id'],
                'grouping_key': query_res['grouping_key'],
            })
        return result_dict

    @api.model
    def l10n_fr_intrastat_export_to_xml(self, options):
        """Generate XML content of the French Intrastat declaration"""

        report = self.env['account.report'].browse(options['report_id'])
        options = report.get_options(previous_options={**options, 'export_mode': 'file'})
        fr_intrastat_wizard = self._retrieve_fr_intrastat_wizard(options)

        # Determine whether items with regime 21 should be detailed or not
        is_regime_21_short = (
            fr_intrastat_wizard.export_type == 'vat_summary_statement'
            or (
                fr_intrastat_wizard.export_type == 'statistical_survey_and_vat_summary_statement'
                and fr_intrastat_wizard.emebi_flow == 'arrivals'
            )
        )

        values = {'errors': {}}
        missing_required_values = {
            'transaction_code': [],
            'region_code': [],
            'transport_code': [],
            'intrastat_product_origin_country_code': [],
            'commodity_code': set(),
            'partner_vat': set()
        }

        if fr_intrastat_wizard:
            export_type = fr_intrastat_wizard.export_type
            emebi_flow = fr_intrastat_wizard.emebi_flow

            if export_type == 'statistical_survey' and emebi_flow == 'arrivals':
                options.setdefault('forced_domain', []).append(('move_type', 'in', self.env['account.move'].get_outbound_types(False)))

            if (
                    (export_type == 'statistical_survey' and emebi_flow == 'dispatches')
                    or (export_type == 'vat_summary_statement')
                    or (export_type == 'statistical_survey_and_vat_summary_statement' and emebi_flow == 'dispatches')
            ):
                options.setdefault('forced_domain', []).append(('move_type', 'in', self.env['account.move'].get_inbound_types(False)))

        self.env.flush_all()

        report._init_currency_table(options)
        expressions = report.line_ids.expression_ids
        results = self._report_custom_engine_intrastat(expressions, options, expressions[0].date_scope, 'id', None)

        # items are divided by regime (system)
        items = defaultdict(list)
        for _grouping_key, item in results:
            # Should never be True, but we make sure because so far we only handle regime 11 and 21
            if item['system'] not in ('11', '21'):
                continue

            is_detailed_item_required = not is_regime_21_short or item['system'] != '21'
            if is_detailed_item_required:
                self._check_missing_required_values(item, missing_required_values)
                self._pre_adjust_item_values(item)

            items[item['system']].append(item)

        if not any(items['11'] + items['21']):
            raise UserError(_("There is no line to export with the selected options"))

        self._fill_value_errors(options, values, missing_required_values)
        self._group_items(items, is_regime_21_short)
        self._post_adjust_items_values(items)
        self._generate_envelope_data(options, self.env.company, values)
        self._generate_declarations(items, self.env.company, fr_intrastat_wizard.export_type, values)

        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': values, 'template': 'l10n_fr_intrastat.intrastat_report_export_xml', 'file_type': 'xml'},
            values['errors'],
        )
        return file_data

    @api.model
    def _get_company_identifier(self, company_id, values):
        """ Return: FR (ISO code of the country) + VAT number key (2 alphanumeric) + SIREN number (9 digits) + SIRET complement (5 digits) """
        company_vat = company_id.vat or ''
        company_siret = company_id.siret[9:14] if company_id.siret and len(company_id.siret) >= 14 else ''
        if not company_vat or not company_siret:
            values['errors']['company_vat_or_siret_missing'] = {
                'message': _("The VAT or SIRET code is not properly set on the company."),
                'action_text': _("View Company/ies"),
                'action': company_id._get_records_action(name=_("Check Company Data")),
            }
        return f'{company_vat}{company_siret}'

    @api.model
    def _check_missing_required_values(self, item, missing_required_values):
        if not item['transaction_code']:
            missing_required_values['transaction_code'].append(item['grouping_key'])

        if not item['commodity_code']:
            missing_required_values['commodity_code'].add(item['product_id'])

        if not item['intrastat_product_origin_country_code'] or item['intrastat_product_origin_country_code'] == 'QU':
            missing_required_values['intrastat_product_origin_country_code'].append(item['grouping_key'])

        if not item['region_code']:
            missing_required_values['region_code'].append(item['grouping_key'])

        if not item['transport_code']:
            missing_required_values['transport_code'].append(item['move_id'])

        # default intrastat use QV OR QN for missing partner VAT code but France does not accept this notation
        if item['system'] == '21' and (not item['partner_vat'] or item['partner_vat'].startswith('QV') or item['partner_vat'].startswith('QN')):
            missing_required_values['partner_vat'].add(item['partner_id'])

    @api.model
    def _pre_adjust_item_values(self, item):
        """Pre-adjusts the values of the exported items to ensure compliance with expected formats."""
        item['nature_of_transaction_A_code'] = str(item['transaction_code'])[0]
        item['nature_of_transaction_B_code'] = str(item['transaction_code'])[1]
        item['additional_goods_code'] = str(item['commodity_code'][8]) if len(str(item['commodity_code'])) > 8 else None
        item['commodity_code'] = str(item['commodity_code'])[:8]
        item['SU_code'] = item['supplementary_units_code']

    @api.model
    def _fill_value_errors(self, options, values, missing_required_values):
        """Adds error messages to display to the user when certain required values are missing."""
        if missing_required_values['transaction_code']:
            move_lines = self.env['account.move.line'].browse(missing_required_values['transaction_code'])
            move_lines_view = self.env.ref("account_intrastat.account_move_line_tree_view_account_intrastat_transaction_codes")
            values['errors']['move_lines_transaction_code_missing'] = {
                'message': _("Missing transaction code for journal items"),
                'action_text': _("View journal item(s)"),
                'action': move_lines._get_records_action(
                    name=_('Invalid transaction intrastat code entries.'),
                    context={**self.env.context, 'create': False, 'delete': False, 'expand': True},
                    views=[(move_lines_view.id, "list"), (False, 'form')],
                    options=options,
                ),
            }

        if missing_required_values['commodity_code']:
            products = self.env['product.product'].browse(missing_required_values['commodity_code'])
            values['errors']['products_commodity_code_missing'] = {
                'message': _("Missing commodity code for some products"),
                'action_text': _("View Product(s)"),
                'action': products._get_records_action(
                    name=_('Products with no commodity code'),
                    options=options,
                ),
            }

        if missing_required_values['intrastat_product_origin_country_code']:
            move_lines = self.env['account.move.line'].browse(missing_required_values['intrastat_product_origin_country_code'])
            move_lines_view = self.env.ref("account_intrastat.account_move_line_tree_view_account_intrastat_product_origin_country_id")
            values['errors']['move_lines_country_of_origin_missing'] = {
                'message': _("Missing country of origin for journal items, 'QU' will be set as default value"),
                'action_text': _("View journal item(s)"),
                'action': move_lines._get_records_action(
                    name=_('Invalid transaction intrastat code entries.'),
                    context={**self.env.context, 'create': False, 'delete': False, 'expand': True},
                    views=[(move_lines_view.id, "list"), (False, 'form')],
                ),
            }

        if missing_required_values['region_code']:
            values['errors']['settings_region_id_missing'] = {
                'message': _("Missing department code for journal entries on the company"),
                'action_text': _("View Settings"),
                'action': {
                    'name': _("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#intrastat_statistics',
                }
            }

        if missing_required_values['transport_code']:
            move_lines = self.env['account.move.line'].browse(missing_required_values['transport_code'])
            move_lines_view = self.env.ref("account_intrastat.account_move_line_tree_view_account_intrastat_transaction_codes")
            values['errors']['move_lines_transport_code_missing'] = {
                'message': _("Missing transport code for journal entries"),
                'action_text': _("View journal item(s)"),
                'action': move_lines._get_records_action(
                    name=_('Invalid transaction intrastat code entries.'),
                    context={**self.env.context, 'create': False, 'delete': False, 'expand': True},
                    views=[(move_lines_view.id, "list"), (False, 'form')],
                ),
            }

        if missing_required_values['partner_vat']:
            partners = self.env['res.partner'].browse(missing_required_values['partner_vat'])
            values['errors']['partner_vat_missing'] = {
                'message': _("Missing partner VAT"),
                'action_text': _('View Partner(s)'),
                'action': partners._get_records_action(name=_("Invalid Partner(s)"))
            }

    @api.model
    def _group_items(self, items, is_regime_21_short):
        """
        Groups the items if they share some similar values
        - If export_type is statistical_survey and the flow is arrivals, group lines if they share the same values for the following properties:
        nomenclature, regime, transport mode, country of origin, country of provenance, department, nature of transaction
        - If export_type is statistical_survey and the flow is dispatch, group lines if they share the same values for the following properties:
        nomenclature, regime, transport mode, country of origin, country of provenance, department, nature of transaction, customer vat
        - If export_type is vat_summary_statement:
        regime, customer vat

        note:
            - nomenclature includes the 3 following properties: commodity_code, SU_code, additional_goods_code
            - nature of transaction is divided into 2: nature_of_transaction_A_code, nature_of_transaction_B_code
        """

        for regime in items:
            if regime == '11':
                grouping_key = ['commodity_code', 'SU_code', 'additional_goods_code', 'system', 'transport_code',
                                'intrastat_product_origin_country_code', 'country_code', 'region_code',
                                'nature_of_transaction_A_code', 'nature_of_transaction_B_code']
            elif regime == '21' and not is_regime_21_short:
                grouping_key = ['commodity_code', 'SU_code', 'additional_goods_code', 'system', 'transport_code',
                                'intrastat_product_origin_country_code', 'country_code', 'region_code',
                                'nature_of_transaction_A_code', 'nature_of_transaction_B_code', 'partner_vat']
            else:
                grouping_key = ['system', 'partner_vat']

            is_weight_required = not(regime == '21' and is_regime_21_short)

            # Determine values fields
            if is_weight_required:
                grouped_items = defaultdict(lambda: {'value': 0, 'weight': 0})
            else:
                grouped_items = defaultdict(lambda: {'value': 0})

            # Group items and sum their values and weights
            for item in items[regime]:
                item_group_key = tuple(item[prop] for prop in grouping_key)
                grouped_items[item_group_key]['value'] += item['value']
                if is_weight_required:
                    grouped_items[item_group_key]['weight'] += item['weight']

            # Convert the grouped_items dictionary back to a list of dictionaries
            items[regime] = [dict(zip(grouping_key, grouped_item_key)) | grouped_item_values
                             for grouped_item_key, grouped_item_values in grouped_items.items()]

    @api.model
    def _post_adjust_items_values(self, items):
        """Complete values with what is expected once they are grouped. Rounding is made once items grouped for correctness"""
        def round_half_up(value):
            return int(float_round(value, precision_digits=0, rounding_method='HALF-UP'))

        for regime in items:
            new_item_list = []
            for item in items[regime]:
                # The weight must be rounded off in kilograms.
                # Weights below 1 kilogram should be rounded off above.
                if item.get('weight'):
                    item['weight'] = round_half_up(item['weight']) or 1

                # Same logic as weight for supplementary units
                if item.get('supplementary_units'):
                    item['supplementary_units'] = round_half_up(item['supplementary_units']) or 1

                item['value'] = round_half_up(item['value'])
                if item['value'] > 0:
                    new_item_list.append(item)

            items[regime] = new_item_list

    @api.model
    def _generate_envelope_data(self, options, company, values):
        """Generates the data encoded in the envelope tag"""
        envelope_id = company.l10n_fr_intrastat_envelope_id
        if not envelope_id:
            values['errors']['settings_approval_number_missing'] = {
                'message': _("Please set the approval number issued by your local collection center in the Accounting settings"),
                'action_text': _("View Settings"),
                'action': {
                    'name': _("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#intrastat_statistics',
                }
            }

        # Software used, 14 character maximum allowed (must include the version too)
        software_used = 'Odoo ' + release.major_version

        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        expected_diff_days = calendar.monthrange(date_to.year, date_to.month)[1] - 1
        if date_from.day != 1 or (date_to - date_from).days != expected_diff_days:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))

        # Use the data of the accounting firm (fiduciary) if available, otherwise use the company data
        registrant = company.account_representative_id or company
        party_name = company.account_representative_id.name or company.name
        party_type = 'TDP' if company.account_representative_id else 'PSI'
        party_role = 'PSI'
        party_id = self._get_company_identifier(registrant, values)

        values.update({
            'envelope_id': envelope_id,
            'software_used': software_used,
            'date_from': date_from,
            'date_to': date_to,
            'party_id': party_id,
            'party_name': party_name,
            'envelope_date': datetime.now().strftime('%Y-%m-%d'),
            'envelope_time': datetime.now().strftime('%H:%M:%S'),
            'party_type': party_type,
            'party_role': party_role,
        })

    @api.model
    def _generate_declarations(self, items, company, export_type, values):
        common_declarations_map = self._get_common_declarations_data(company, export_type, values)
        declarations = []

        # Arrival flow declaration
        if items['11']:
            declarations.append({
                **common_declarations_map,
                'flow_code': 'A',
                'items': items['11'],
            })

        # Dispatch flow declaration
        if items['21']:
            declarations.append({
                **common_declarations_map,
                'flow_code': 'D',
                'items': items['21'],
            })

        values['declarations'] = declarations

    @api.model
    def _get_common_declarations_data(self, company, export_type, values):
        """Returns a declaration dictionary including common information for arrivals and dispatches"""
        psi_id = self._get_company_identifier(company, values)

        declaration_type_codes = {
            'statistical_survey': 1,
            'vat_summary_statement': 4,
            'statistical_survey_and_vat_summary_statement': 5,
        }

        return {
            'reference_period': values['date_from'].strftime('%Y-%m'),
            'PSI_id': psi_id,
            'function_code': 'O',  # only possible value according to French documentation
            'currency_code': 'EUR',  # only EUR is accepted for French XML documents
            'declaration_type_code': declaration_type_codes[export_type],
        }
