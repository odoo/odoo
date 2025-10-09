# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestImLivechatChannelRating(HttpCase):
    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_im_livechat_channel_rating(self):
        new_test_user(self.env, login="operator", groups="base.group_user,im_livechat.im_livechat_group_user")
        agent = new_test_user(self.env, login="agent", name="Livechat Agent")
        livechat_channel = self.env['im_livechat.channel'].create({'name': "Support Session"})
        channel = self.env['discuss.channel'].create({
            'name': "Livechat Session for Rating",
            'channel_type': 'livechat',
            'livechat_channel_id': livechat_channel.id,
            'livechat_operator_id': agent.partner_id.id
        })
        self.env['rating.rating'].create({
            'res_model_id': self.env['ir.model']._get('discuss.channel').id,
            'res_id': channel.id,
            'parent_res_model_id': self.env['ir.model']._get('im_livechat.channel').id,
            'parent_res_id': channel.id,
            'rated_partner_id': agent.partner_id.id,
            'partner_id': agent.partner_id.id,
            'rating': 5,
            'consumed': True
        })
        self.start_tour("/odoo", "im_livechat_channel_rating", login="operator")
