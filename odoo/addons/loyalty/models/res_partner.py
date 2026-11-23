# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_card_count = fields.Integer(
        string="Active loyalty cards",
        compute='_compute_count_active_cards',
        compute_sudo=True,
        groups='base.group_user')

    def _compute_count_active_cards(self):
        loyalty_groups = self.env['loyalty.card']._read_group(
            domain=[
                '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids),
                ('partner_id', 'in', self.with_context(active_test=False)._search([('id', 'child_of', self.ids)])),
                ('points', '>', '0'),
                ('program_id.active', '=', 'True'),
                '|',
                    ('expiration_date', '>=', fields.Date().context_today(self)),
                    ('expiration_date', '=', False),
            ],
            groupby=['partner_id'],
            aggregates=['__count'],
        )
        self.loyalty_card_count = 0
        for partner, count in loyalty_groups:
            while partner:
                if partner in self:
                    partner.loyalty_card_count += count
                partner = partner.parent_id

    def action_view_loyalty_cards(self):
        action = self.env['ir.actions.act_window']._for_xml_id('loyalty.loyalty_card_action')
        all_child = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        action['domain'] = [('partner_id', 'in', all_child.ids)]
        action['context'] = {'search_default_active' : True, 'create': False}
        return action
