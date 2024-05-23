# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _lt, api
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    workorder_count = fields.Integer(related="analytic_account_id.workorder_count", groups='mrp.group_mrp_user', export_string_translation=False)

    @api.depends('analytic_account_id.production_count')
    def _compute_production_count(self):
        for project in self:
            project.production_count = len(project.production_ids | project.analytic_account_id.production_ids)

    @api.depends('analytic_account_id.bom_count')
    def _compute_bom_count(self):
        for project in self:
            project.bom_count = len(project.bom_ids | project.analytic_account_id.bom_ids)

    def action_view_mrp_production(self):
        action = super().action_view_mrp_production()
        action['domain'][0][2] += self.analytic_account_id.production_ids.ids
        return action

    def action_view_mrp_bom(self):
        action = super().action_view_mrp_bom()
        action['domain'][0][2] += self.analytic_account_id.bom_ids.ids
        return action

    def action_view_workorder(self):
        self.ensure_one()
        action = self.analytic_account_id.action_view_workorder()
        if self.workorder_count > 1:
            action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph'
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['manufacturing_order'] = _lt('Manufacturing Orders')
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
        mrp_aal_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [('auto_account_id', 'in', self.analytic_account_id.ids), ('category', '=', mrp_category)],
            ['currency_id'],
            ['amount:sum'],
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
