
from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_overdue_followup = fields.Monetary(
        compute='_compute_total_due_followup',
        groups='account.group_account_readonly,account.group_account_invoice'
    )

    def action_open_overdue_entries(self):
        action = super().action_open_overdue_entries()
        action.pop('view_mode', None)
        action['views'] = [(self.env.ref('account_no_followup.view_followup_invoice_list').id, 'list'), (None, 'form')]
        return action

    @api.depends('invoice_ids.line_ids.no_followup')
    def _compute_total_due_followup(self):
        receivable_overdue_followup_data = defaultdict(float)

        for account_type, overdue, partner, no_followup, amount_residual_sum in self.env['account.move.line']._read_group(
            domain=self._get_unreconciled_aml_domain(),
            groupby=['account_type', 'followup_overdue', 'partner_id', 'no_followup'],
            aggregates=['amount_residual:sum'],
        ):
            if account_type == 'asset_receivable' and overdue and not no_followup:
                receivable_overdue_followup_data[partner] += amount_residual_sum
        for partner in self:
            partner.total_overdue_followup = receivable_overdue_followup_data.get(partner, 0.0)

    def _get_followup_data_query_extra_join_conditions(self):
        return super()._get_followup_data_query_extra_join_conditions() + 'AND line.no_followup IS NOT TRUE\n'
