# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form, tagged


@tagged("voip", "post_install", "-at_install")
class TestVoipUserConfig(common.TransactionCase):
    def test_voip_user_config_access_rights(self):
        """
        Tests that users cannot read VoIP configuration of other users.
        """
        user_data_1 = {"login": "i_love_voip", "name": "Handsome VoIP User 😎"}
        voip_user = self.env["res.users"].create(user_data_1).sudo(False)
        settings = voip_user.env["res.users.settings"]._find_or_create_for_user(voip_user)
        settings.write({"voip_secret": "Top Secret 🤫"})
        user_data_2 = {"login": "i_hate_voip", "name": "Evil Password Stealer 👺"}
        evil_password_stealer = self.env["res.users"].create(user_data_2).sudo(False)
        self.env.invalidate_all()

        self.assertFalse(voip_user.with_user(evil_password_stealer).voip_secret)

    def test_update_voip_user_config_from_user_form(self):
        """
        Asserts that changes made to the VoIP Config in the res.users forms are reflected in res.users.settings.
        """
        form = Form(self.env["res.users"], view="base.view_users_form")
        form.name = "钟离"
        form.login = "摩拉克斯"
        form.external_device_number = "110"
        user = form.save()
        settings = user.res_users_settings_id
        self.assertEqual(settings.how_to_call_on_mobile, "ask")
        self.assertEqual(settings.external_device_number, "110")

        form = Form(user, view="base.view_users_form")
        form.how_to_call_on_mobile = "voip"
        form.external_device_number = "911"
        form.save()
        self.assertEqual(settings.how_to_call_on_mobile, "voip")
        self.assertEqual(settings.external_device_number, "911")
