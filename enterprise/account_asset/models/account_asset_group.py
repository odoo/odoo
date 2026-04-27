from odoo import fields, models, api


class AccountAssetGroup(models.Model):
    _name = 'account.asset.group'
    _description = 'Asset Group'
    _order = 'name'

    name = fields.Char("Name", index="trigram")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    linked_asset_ids = fields.One2many('account.asset', 'asset_group_id', string='Related Assets')
    count_linked_assets = fields.Integer(compute='_compute_count_linked_asset')

    @api.depends('linked_asset_ids')
    def _compute_count_linked_asset(self):
        count_per_asset_group = {
            asset_group.id: count
            for asset_group, count in self.env['account.asset']._read_group(
                domain=[
                    ('asset_group_id', 'in', self.ids),
                ],
                groupby=['asset_group_id'],
                aggregates=['__count'],
            )
        }
        for asset_group in self:
            asset_group.count_linked_assets = count_per_asset_group.get(asset_group.id, 0)

    def action_open_linked_assets(self):
        self.ensure_one()
        return {
            'name': self.name,
            'view_mode': 'list,form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.linked_asset_ids.ids)],
        }
