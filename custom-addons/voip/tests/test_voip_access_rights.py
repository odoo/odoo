# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import common, tagged


@tagged("voip")
class TestVoipCall(common.TransactionCase):
    def test_voip_call_access_rights_crud_on_others_records(self):
        """
        Asserts that users cannot perform CRUD operations on other users' call records.
        """
        shrek_data = {"login": "what_are_you_doing_in_my_swamp", "name": "💠 Shrek 💠"}
        shrek = self.env["res.users"].create(shrek_data)
        bowser_data = {"login": "so_long", "name": "Bowser 😤😤😤"}
        bowser = self.env["res.users"].create(bowser_data)
        call_made_by_shrek = self.env["voip.call"].create({"user_id": shrek.id, "phone_number": "+246 532 4846"})
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            self.env["voip.call"].with_user(bowser).create({"user_id": shrek.id, "phone_number": "+244 0915 050 7017"})
        with self.assertRaises(AccessError):
            call_made_by_shrek.with_user(bowser).read()
        with self.assertRaises(AccessError):
            call_made_by_shrek.with_user(bowser).write({})
        with self.assertRaises(AccessError):
            call_made_by_shrek.with_user(bowser).unlink()

    def test_voip_call_access_rights_crud_on_their_own_records(self):
        """
        Asserts that access rights are working correctly for CRUD operations on users' own records.
        """
        wario = self.env["res.users"].create(
            {
                "login": "waaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "name": "$$𝕎𝔸ℝ𝕀𝕆$$",
            }
        )
        self.env.invalidate_all()

        call_made_by_wario = self.env["voip.call"].with_user(wario).create({"user_id": wario.id, "phone_number": "2"})
        self.assertTrue(call_made_by_wario)
        call_made_by_wario.read()
        call_made_by_wario.write({"activity_name": "Team building (Extreme Ironing)"})
        self.assertEqual(call_made_by_wario.activity_name, "Team building (Extreme Ironing)")
        with self.assertRaises(AccessError):
            call_made_by_wario.unlink()
