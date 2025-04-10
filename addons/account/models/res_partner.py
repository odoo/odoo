from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    move_count = fields.Integer(
        string="Journal Entry Count",
        groups='account.group_account_user',
        compute='_compute_move_count',
    )
    move_ids = fields.One2many('account.move', 'partner_id', 'Journal Entries')

    def _compute_activity_counts(self):
        # OVERRIDE
        super()._compute_activity_counts()
        if not self.env.user.has_group('account.group_account_user'):
            return
        for partner in self:
            count = {
                'title': 'Journal Entries',
                'count': partner.move_count,
                'icon_name': 'fa-pencil-square-o',
                'action_name': 'open_partner_moves',
                'groups': 'account.group_account_user',
            }
            if not isinstance(partner.activity_counts, list):
                partner.activity_counts = [count]
            else:
                partner.activity_counts.append(count)

    def _compute_move_count(self):
        self.move_count = 0
        if not self.env.user.has_group('account.group_account_user'):
            return

        # Retrieve all children partners and prefetch 'parent_id' on them.
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        move_groups = self.env['account.move']._read_group(
            domain=[
                ('partner_id', 'in', all_partners.ids),
                ('move_type', 'in', ['in_invoice', 'out_invoice', 'in_refund', 'out_refund']),
            ],
            groupby=['partner_id'], aggregates=['__count']
        )

        self_ids = set(self._ids)
        for partner, count in move_groups:
            while partner:
                if partner.id in self_ids:
                    partner.move_count += count
                partner = partner.parent_id

    def open_partner_moves(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('partner_id', 'child_of', self.ids), ('move_type', 'in', ['in_invoice', 'out_invoice', 'in_refund', 'out_refund'])],
            'context': self.env.context,
        }
