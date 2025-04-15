# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestLiveChatDigest(TestDigestCommon):

    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()

        other_partner = cls.env['res.partner'].create({'name': 'Other Partner'})

        cls.channels = cls.env['discuss.channel'].create([{
            'name': 'Channel 1',
            'livechat_operator_id': cls.env.user.partner_id.id,
            'channel_type': 'livechat',
        }, {
            'name': 'Channel 2',
            'livechat_operator_id': cls.env.user.partner_id.id,
            'channel_type': 'livechat',
        }, {
            'name': 'Channel 3',
            'livechat_operator_id': other_partner.id,
            'channel_type': 'livechat',
        }])

        cls.env['rating.rating'].search([]).unlink()

        cls.env['rating.rating'].create([{
            'rated_partner_id': cls.env.user.partner_id.id,
            'res_id': cls.channels[0].id,
            'res_model_id': cls.env['ir.model']._get('discuss.channel').id,
            'consumed': True,
            'rating': 5,
        }, {
            'rated_partner_id': cls.env.user.partner_id.id,
            'res_id': cls.channels[0].id,
            'res_model_id': cls.env['ir.model']._get('discuss.channel').id,
            'consumed': True,
            'rating': 0,
        }, {
            'rated_partner_id': cls.env.user.partner_id.id,
            'res_id': cls.channels[0].id,
            'res_model_id': cls.env['ir.model']._get('discuss.channel').id,
            'consumed': True,
            'rating': 3,
        }, {
            'rated_partner_id': cls.env.user.partner_id.id,
            'res_id': cls.channels[0].id,
            'res_model_id': cls.env['ir.model']._get('discuss.channel').id,
            'consumed': True,
            'rating': 3,
        }])

    def test_kpi_livechat_rating_value(self):
        # 1/3 of the ratings have 5/5 note (0 are ignored)
        self.assertEqual(round(self.digest_1.kpi_livechat_rating_value, 2), 33.33)
