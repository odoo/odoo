from odoo import api, fields, models, _


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    linked_loans_ids = fields.One2many(related='asset_group_id.linked_loan_ids')
    count_linked_loans = fields.Integer(compute="_compute_count_linked_loans")

    @api.depends('linked_loans_ids')
    def _compute_count_linked_loans(self):
        for asset in self:
            asset.count_linked_loans = len(asset.linked_loans_ids)

    def action_open_linked_loans(self):
        return {
            'name': _('Linked loans'),
            'view_mode': 'list,form',
            'res_model': 'account.loan',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.linked_loans_ids.ids)],
        }
