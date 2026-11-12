# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tools.discuss import Store
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('phone_validation', 'post_install', '-at_install')
class TestResPartnerAvatarCard(TransactionCase):

    def test_avatar_card_phone_fields_only_for_internal_users(self):
        partner = self.env['res.partner'].sudo().create({
            'name': 'John Jane',
            'phone': '0456 99 88 77',
            'country_id': self.env.ref('base.be').id,
        })
        internal = new_test_user(self.env, 'internal_avatar_card', groups='base.group_user')
        portal = new_test_user(self.env, 'portal_avatar_card', groups='base.group_portal')

        data = Store().add(partner.with_user(internal).sudo(), "_store_avatar_card_fields")._build_result()
        values = data['res.partner'][0]
        self.assertEqual(values['phone_sanitized'], '+32456998877')
        self.assertEqual(values['phone_formatted'], '+32 456 99 88 77')

        data = Store().add(partner.with_user(portal).sudo(), "_store_avatar_card_fields")._build_result()
        values = data['res.partner'][0]
        self.assertNotIn('phone', values)
        self.assertNotIn('phone_sanitized', values)
        self.assertNotIn('phone_formatted', values)
