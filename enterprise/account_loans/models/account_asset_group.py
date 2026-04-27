from odoo import fields, models, api


class AccountAssetGroup(models.Model):
    _inherit = 'account.asset.group'

    linked_loan_ids = fields.One2many('account.loan', 'asset_group_id', string='Related Loans')
    count_linked_loans = fields.Integer(compute="_compute_count_linked_loans")

    @api.depends('linked_loan_ids')
    def _compute_count_linked_loans(self):
        count_per_asset_group = {
            asset_group.id: count
            for asset_group, count in self.env['account.loan']._read_group(
                domain=[
                    ('asset_group_id', 'in', self.ids),
                ],
                groupby=['asset_group_id'],
                aggregates=['__count'],
            )
        }
        for asset_group in self:
            asset_group.count_linked_loans = count_per_asset_group.get(asset_group.id, 0)

    def action_open_linked_loans(self):
        self.ensure_one()
        return {
            'name': self.name,
            'view_mode': 'list,form',
            'res_model': 'account.loan',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.linked_loan_ids.ids)],
        }
