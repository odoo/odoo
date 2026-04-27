# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results['vehicle_id'] = self._get_base_line_field_value_from_record(record, 'vehicle_id', kwargs, self.env['fleet.vehicle'])
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        results['vehicle_id'] = self._get_base_line_field_value_from_record(record, 'vehicle_id', kwargs, self.env['fleet.vehicle'])
        return results

    def _prepare_base_line_grouping_key(self, base_line):
        # EXTENDS 'account'
        results = super()._prepare_base_line_grouping_key(base_line)
        results['vehicle_id'] = base_line['vehicle_id'].id
        return results

    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        # EXTENDS 'account'
        results = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        results['vehicle_id'] = base_line_grouping_key['vehicle_id'] if not tax_rep_data['tax_rep'].use_in_tax_closing else False
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        results['vehicle_id'] = tax_line['vehicle_id'].id
        return results
