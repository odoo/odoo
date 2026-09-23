from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestRecurrenceWeekStart(TransactionCase):
    def test_a_user_without_a_language_still_gets_a_real_week_start(self):
        user = new_test_user(self.env, login="rrule_no_lang")
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET lang = NULL WHERE id = %s", [user.partner_id.id]
        )
        self.env.invalidate_all()
        self.assertFalse(user.lang)

        week_start = (
            self.env["mixin.recurrence.rrule"].with_user(user)._get_lang_week_start()
        )

        self.assertIn(week_start.weekday, range(7))

    def test_repeating_until_no_date_is_refused_as_a_user_error(self):
        rule = self.env["mixin.recurrence.rrule"].new(
            {
                "repeat_interval": 1,
                "repeat_unit": "day",
                "repeat_type": "until",
                "repeat_until": False,
            }
        )
        with self.assertRaises(UserError):
            rule._rrule_serialize()
