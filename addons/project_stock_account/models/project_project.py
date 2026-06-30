# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _lt
from odoo.fields import Domain


class Project(models.Model):
    _inherit = 'project.project'

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            'other_costs': _lt('Materials'),
        }

    def _get_profitability_sequence_per_invoice_type(self):
        return {
            **super()._get_profitability_sequence_per_invoice_type(),
            'other_costs': 12,
        }

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        aal_from_picking = self._get_items_from_aal_picking(with_action)
        if aal_from_picking:
            profitability_items['costs']['data'] += aal_from_picking
            profitability_items['costs']['total']['billed'] += aal_from_picking[0]['billed']
        return profitability_items

    def _get_items_from_aal_picking(self, with_action=True):
        domain = Domain(self._get_domain_aal_with_no_move_line()) & Domain('category', '=', 'picking_entry')
        aal_other_search = self.env['account.analytic.line'].sudo().search_read(domain, ['id', 'amount', 'currency_id'])
        if not aal_other_search:
            return False

        dict_amount_per_currency_id = {}
        set_currency_ids = {self.currency_id.id}
        cost_ids = []
        for aal in aal_other_search:
            set_currency_ids.add(aal['currency_id'][0])
            aal_amount = aal['amount']
            if not dict_amount_per_currency_id.get(aal['currency_id'][0]):
                dict_amount_per_currency_id[aal['currency_id'][0]] = aal_amount
            else:
                dict_amount_per_currency_id[aal['currency_id'][0]] += aal_amount
            cost_ids.append(aal['id'])

        total_costs = 0.0
        for currency_id, amounts in dict_amount_per_currency_id.items():
            currency = self.env['res.currency'].browse(currency_id).with_prefetch(dict_amount_per_currency_id)
            total_costs += currency._convert(amounts, self.currency_id, self.company_id)

        profitability_sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()
        costs = [{'id': 'other_costs', 'sequence': profitability_sequence_per_invoice_type['other_costs_aal'], 'billed': total_costs, 'to_bill': 0.0}]

        if with_action and self.env.user.has_group('account.group_account_readonly'):
            costs[0]['action'] = self._get_action_for_profitability_section(cost_ids, 'other_costs_aal')

        return costs
