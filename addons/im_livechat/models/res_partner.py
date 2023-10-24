# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class Partners(models.Model):
    """Update of res.partner class to take into account the livechat username."""
    _inherit = 'res.partner'

    user_livechat_username = fields.Char(compute='_compute_user_livechat_username')

    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        result = super().search_for_channel_invite(search_term, channel_id, limit)
        channel = self.env['discuss.channel'].browse(channel_id)
        partners = self.browse([partner["id"] for partner in result['partners']])
        if channel.channel_type != 'livechat' or not partners:
            return result
        lang_name_by_code = {code: name for code, name in self.env['res.lang'].get_installed()}
        formatted_partner_by_id = {formatted_partner['id']: formatted_partner for formatted_partner in result['partners']}
        invite_by_self_count_by_partner_id = dict(
            self.env["discuss.channel.member"]._read_group(
                [["create_uid", "=", self.env.user.id], ["partner_id", "in", partners.ids]],
                groupby=["partner_id"],
                aggregates=['__count'],
            )
        )
        active_livechat_partner_ids = self.env['im_livechat.channel'].search([]).available_operator_ids.partner_id.ids
        for partner in partners:
            formatted_partner_by_id[partner.id].update({
                'lang_name': lang_name_by_code[partner.lang],
                'invite_by_self_count': invite_by_self_count_by_partner_id.get(partner, 0),
                'is_available': partner.id in active_livechat_partner_ids,
            })
        return result

    @api.depends('user_ids.livechat_username')
    def _compute_user_livechat_username(self):
        for partner in self:
            partner.user_livechat_username = next(iter(partner.user_ids.mapped('livechat_username')), False)
