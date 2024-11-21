# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_utils, formatLang
from odoo.tools.misc import format_duration


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        template_values = super(ProjectUpdate, self)._get_template_values(project)
        profitability_values = self._get_profitability_values(project)
        show_profitability = bool(profitability_values and profitability_values.get('account_id') and (profitability_values.get('costs') or profitability_values.get('revenues')))
        return {
            **template_values,
            'show_profitability': show_profitability,
            'show_activities': template_values['show_activities'] or show_profitability,
            'profitability': profitability_values,
            'format_value': lambda value, is_hour: str(round(value, 2)) if not is_hour else format_duration(value),
        }

    @api.model
    def _get_profitability_values(self, project):
        costs_revenues = project.account_id and project.allow_billable
        if not (self.env.user.has_group('project.group_project_manager') and costs_revenues):
            return {}
        profitability_items = project._get_profitability_items(False)
        if project._get_profitability_sequence_per_invoice_type() and profitability_items and 'revenues' in profitability_items and 'costs' in profitability_items:  # sort the data values
            profitability_items['revenues']['data'] = sorted(profitability_items['revenues']['data'], key=lambda k: k['sequence'])
            profitability_items['costs']['data'] = sorted(profitability_items['costs']['data'], key=lambda k: k['sequence'])
        costs = sum(profitability_items['costs']['total'].values())
        revenues = sum(profitability_items['revenues']['total'].values())
        margin = revenues + costs
        to_bill_to_invoice = profitability_items['costs']['total']['to_bill'] + profitability_items['revenues']['total']['to_invoice']
        billed_invoiced = profitability_items['costs']['total']['billed'] + profitability_items['revenues']['total']['invoiced']
        expected_percentage, to_bill_to_invoice_percentage, billed_invoiced_percentage = 0, 0, 0
        if revenues:
            expected_percentage = formatLang(self.env, (margin / revenues) * 100, digits=0)
        if profitability_items['revenues']['total']['to_invoice']:
            to_bill_to_invoice_percentage = formatLang(self.env, (to_bill_to_invoice / profitability_items['revenues']['total']['to_invoice']) * 100, digits=0)
        if profitability_items['revenues']['total']['invoiced']:
            billed_invoiced_percentage = formatLang(self.env, (billed_invoiced / profitability_items['revenues']['total']['invoiced']) * 100, digits=0)
        return {
            'account_id': project.account_id,
            'costs': profitability_items['costs'],
            'revenues': profitability_items['revenues'],
            'expected_percentage': expected_percentage,
            'to_bill_to_invoice_percentage': to_bill_to_invoice_percentage,
            'billed_invoiced_percentage': billed_invoiced_percentage,
            'total': {
                'costs': costs,
                'revenues': revenues,
                'margin': margin,
                'margin_percentage': formatLang(self.env,
                                                not float_utils.float_is_zero(costs, precision_digits=2) and (margin / -costs) * 100 or 0.0,
                                                digits=0),
            },
            'labels': project._get_profitability_labels(),
        }
