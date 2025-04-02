# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common_controllers import MailControllerCommon


class TestMailFollowersController(MailControllerCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record = cls.env['res.partner'].create({'name': 'Test Thread'})
        cls.subtype_internal = cls.env.ref('mail.mt_note')
        cls.subtype_public = cls.env.ref('mail.mt_comment')

    def test_read_subscription_data_hides_internal_for_external_follower(self):
        """Internal subtypes must not be available subscription options for an external partner follower."""
        follower = self.env['mail.followers'].create({
            'partner_id': self.partner_portal.id,
            'res_model': 'res.partner',
            'res_id': self.test_record.id,
        })
        self.authenticate(self.user_employee.login, self.user_employee.login)
        result = self.make_jsonrpc_request(
            '/mail/read_subscription_data',
            {'follower_id': follower.id},
        )
        self.assertNotIn(self.subtype_internal.id, result['subtype_ids'])
        self.assertIn(self.subtype_public.id, result['subtype_ids'])

    def test_read_subscription_data_shows_internal_for_internal_follower(self):
        """Internal subtypes must be available subscription options for an internal user follower."""
        follower = self.env['mail.followers'].create({
            'partner_id': self.partner_employee.id,
            'res_model': 'res.partner',
            'res_id': self.test_record.id,
        })
        self.authenticate(self.user_employee.login, self.user_employee.login)
        result = self.make_jsonrpc_request(
            '/mail/read_subscription_data',
            {'follower_id': follower.id},
        )
        self.assertIn(self.subtype_internal.id, result['subtype_ids'])
        self.assertIn(self.subtype_public.id, result['subtype_ids'])
