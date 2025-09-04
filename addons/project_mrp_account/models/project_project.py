# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['manufacturing_order'] = self.env._('Manufacturing Orders')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['manufacturing_order'] = 12
        return sequence_per_invoice_type

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            [('category', '!=', 'manufacturing_order')],
        ])

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        mrp_category = 'manufacturing_order'
        aal_domain = [("auto_account_id", "in", self.account_id.ids), ("category", "=", mrp_category)]

        all_project_mos = self.env['mrp.production'].sudo().search([
            ('project_id', 'in', self.ids)
        ])
        child_mos = self.env['mrp.production']
        if all_project_mos:
            child_mos = all_project_mos.filtered(lambda mo: mo._get_sources() & all_project_mos)

            if child_mos:
                child_moves = child_mos.move_raw_ids | child_mos.move_finished_ids
                if child_moves.analytic_account_line_ids:
                    aal_domain = expression.AND([
                        aal_domain,
                        [("id", "not in", child_moves.analytic_account_line_ids.ids)],
                    ])

        mrp_aal_read_group = self.env["account.analytic.line"].sudo()._read_group(
            aal_domain, ["currency_id"], ["amount:sum"]
        )
        if mrp_aal_read_group:
            can_see_manufactoring_order = with_action and len(self) == 1 and self.env.user.has_group('mrp.group_mrp_user')
            total_amount = 0
            for currency, amount_summed in mrp_aal_read_group:
                total_amount += currency._convert(amount_summed, self.currency_id, self.company_id)

            mrp_costs = {
                'id': mrp_category,
                'sequence': self._get_profitability_sequence_per_invoice_type()[mrp_category],
                'billed': total_amount,
                'to_bill': 0.0,
            }
            if can_see_manufactoring_order:
                mrp_costs['action'] = {'name': 'action_view_mrp_production', 'type': 'object'}
            costs = profitability_items['costs']
            costs['data'].append(mrp_costs)
            costs['total']['billed'] += mrp_costs['billed']
        return profitability_items
