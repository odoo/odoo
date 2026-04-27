# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from ast import literal_eval

from odoo import api, models, osv, _

_logger = logging.getLogger(__name__)

class IndianTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_in.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Indian Tax Report Custom Handler'

    @api.model
    def _get_invalid_intra_state_tax_on_lines(self, aml_domain):
        intra_state_sgst_cgst = self.env['account.move.line'].search(
            aml_domain +
            [
                ('move_id.l10n_in_transaction_type', '=', 'intra_state'),
                ('tax_tag_ids', 'in', self.env.ref('l10n_in.tax_tag_base_igst').id),
                ('move_id.l10n_in_gst_treatment', '!=', 'special_economic_zone')
            ]
        ).ids
        return 'l10n_in_reports.invalid_intra_state_warning', intra_state_sgst_cgst

    @api.model
    def _get_invalid_inter_state_tax_on_lines(self, aml_domain):
        inter_state_igst = self.env['account.move.line'].search(
            aml_domain +
            [
                ('move_id.l10n_in_transaction_type', '=', 'inter_state'),
                ('tax_tag_ids', 'in', (self.env.ref('l10n_in.tax_tag_base_cgst').id, self.env.ref('l10n_in.tax_tag_base_sgst').id)),
            ]
        ).ids
        return 'l10n_in_reports.invalid_inter_state_warning', inter_state_igst

    def _get_invalid_no_hsn_line_domain(self):
        return [
            ('l10n_in_hsn_code', '=', False),
            ('display_type', '!=', 'tax')
        ]

    @api.model
    def _get_invalid_no_hsn_products(self, aml_domain):
        missing_hsn = self.env['account.move.line'].search(
            aml_domain + self._get_invalid_no_hsn_line_domain()
        )
        return 'l10n_in_reports.missing_hsn_warning', missing_hsn.ids

    @api.model
    def _get_invalid_service_hsn_products(self, aml_domain):
        invalid_type_service_for_hsn = self.env['account.move.line'].search(
            aml_domain +
            [
                ('l10n_in_hsn_code', '!=', False),
                ('l10n_in_hsn_code', '=like', '99%'),
                ('product_id.type', '!=', 'service'),
            ]
        ).ids
        return 'l10n_in_reports.invalid_type_service_for_hsn_warning', invalid_type_service_for_hsn

    @api.model
    def _get_invalid_goods_hsn_products(self, aml_domain):
        invalid_hsn_for_service = self.env['account.move.line'].search(
            aml_domain +
            [
                ('l10n_in_hsn_code', '!=', False),
                ('product_id.type', '=', 'service'),
                '!', ('l10n_in_hsn_code', '=like', '99%'),
            ]
        ).ids
        return 'l10n_in_reports.invalid_hsn_for_service_warning', invalid_hsn_for_service

    @api.model
    def _get_invalid_uqc_codes(self, aml_domain):
        uqc_codes = [
            'BAG-BAGS',
            'BAL-BALE',
            'BDL-BUNDLES',
            'BKL-BUCKLES',
            'BOU-BILLION OF UNITS',
            'BOX-BOX',
            'BTL-BOTTLES',
            'BUN-BUNCHES',
            'CAN-CANS',
            'CBM-CUBIC METERS',
            'CCM-CUBIC CENTIMETERS',
            'CMS-CENTIMETERS',
            'CTN-CARTONS',
            'DOZ-DOZENS',
            'DRM-DRUMS',
            'GGK-GREAT GROSS',
            'GMS-GRAMMES',
            'GRS-GROSS',
            'GYD-GROSS YARDS',
            'KGS-KILOGRAMS',
            'KLR-KILOLITRE',
            'KME-KILOMETRE',
            'LTR-LITRES',
            'MLT-MILILITRE',
            'MTR-METERS',
            'MTS-METRIC TON',
            'NOS-NUMBERS',
            'PAC-PACKS',
            'PCS-PIECES',
            'PRS-PAIRS',
            'QTL-QUINTAL',
            'ROL-ROLLS',
            'SET-SETS',
            'SQF-SQUARE FEET',
            'SQM-SQUARE METERS',
            'SQY-SQUARE YARDS',
            'TBS-TABLETS',
            'TGM-TEN GROSS',
            'THD-THOUSANDS',
            'TON-TONNES',
            'TUB-TUBES',
            'UGS-US GALLONS',
            'UNT-UNITS',
            'YDS-YARDS',
            'OTH-OTHERS',
        ]
        invalid_uqc_codes = self.env['account.move.line'].search(
            aml_domain +
            [
                ('product_id.type', '!=', 'service'),
                ('product_id.uom_id.l10n_in_code', 'not in', uqc_codes),
            ]
        ).product_id.uom_id.ids
        return 'l10n_in_reports.invalid_uqc_code_warning', invalid_uqc_codes

    @api.model
    def _get_out_of_fiscal_year_reversed_moves(self, options):
        """This method is deprecated and will be removed in the next version (master).
        The warning is now displayed directly on each individual move until it is checked,
        instead of being shown at the report level.
        """
        return 'l10n_in_reports.out_of_fiscal_year_reversed_moves_warning', self.env['account.move']

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        if warnings is not None:
            hsn_base_line_expression = self.env.ref('l10n_in_reports.account_report_gstr1_hsn_taxable_amount_balance')
            options_domain = report._get_options_domain(options, date_scope='strict_range')

            if hsn_base_line_expression.engine != 'domain':
                _logger.warning("HSN Base line engine is not Domain")
                return []

            hsn_base_line_expression_domain = literal_eval(hsn_base_line_expression.formula)
            aml_domain = osv.expression.AND([
                options_domain,
                hsn_base_line_expression_domain,
            ])

            all_checks = [
                self._get_invalid_intra_state_tax_on_lines(aml_domain),
                self._get_invalid_inter_state_tax_on_lines(aml_domain),
                self._get_invalid_no_hsn_products(aml_domain),
                self._get_invalid_service_hsn_products(aml_domain),
                self._get_invalid_goods_hsn_products(aml_domain),
                self._get_invalid_uqc_codes(aml_domain),
                self._get_out_of_fiscal_year_reversed_moves(options)
            ]

            for warning_template_ref, wrong_data in all_checks:
                if wrong_data:
                    warnings[warning_template_ref] = {'ids': wrong_data, 'alert_type': 'warning'}
        return []

    def _l10n_in_open_action(self, name, res_model, views, params):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': res_model,
            'views': views,
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    @api.model
    def open_invalid_intra_state_lines(self, options, params):
        return self._l10n_in_open_action(_('Invalid tax for Intra State Transaction'), 'account.move.line', [(False, 'list')], params)

    @api.model
    def open_invalid_inter_state_lines(self, options, params):
        return self._l10n_in_open_action(_('Invalid tax for Inter State Transaction'), 'account.move.line', [(False, 'list')], params)

    @api.model
    def open_missing_hsn_products(self, options, params):
        return self._l10n_in_open_action(_('Missing HSN for Journal Items'), 'account.move.line', [(False, 'list'), (False, 'form')], params)

    @api.model
    def open_invalid_type_service_for_hsn_products(self, options, params):
        return self._l10n_in_open_action(_('Invalid Product Type'), 'account.move.line', [(False, 'list'), (False, 'form')], params)

    @api.model
    def open_invalid_hsn_for_service_products(self, options, params):
        return self._l10n_in_open_action(_('Invalid HSN Code'), 'account.move.line', [(False, 'list'), (False, 'form')], params)

    @api.model
    def open_invalid_uqc_codes(self, options, params):
        return self._l10n_in_open_action(_('Invalid UQC Code'), 'uom.uom', [(False, 'list'), (False, 'form')], params)

    @api.model
    def open_out_of_fiscal_year_reversed_moves(self, options, params):
        return self._l10n_in_open_action(_('Credit Notes'), 'account.move', [(False, 'list'), (False, 'form')], params)
