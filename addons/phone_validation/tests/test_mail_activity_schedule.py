# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import exceptions
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged


@tagged("phone_validation")
class TestMailActivitySchedule(ActivityScheduleCase):

    def test_call_activity_phone(self):
        """Only Call activities copy the target's phone number."""
        partner = self.env["res.partner"].create({
            "name": "Partner with phone",
            "phone": "+1 202 555 0182",
        })

        call_activity = partner.activity_schedule("mail.mail_activity_data_call")
        todo_activity = partner.activity_schedule("mail.mail_activity_data_todo")

        self.assertEqual(call_activity.phone, partner.phone)
        self.assertFalse(todo_activity.phone)

    def test_call_activity_schedule_phone(self):
        """Call scheduling saves its phone and only fills an empty partner phone."""
        cases = [
            {
                "name": "fill empty partner",
                "input_partner_phone": False,
                "input_activity_phone": "+1 202 555 0182",
                "expected_partner_phone": "+1 202 555 0182",
            }, {
                "name": "keep existing partner",
                "input_partner_phone": "+1 202 555 0100",
                "input_activity_phone": "+1 202 555 0182",
                "expected_partner_phone": "+1 202 555 0100",
            }, {
                "name": "clear activity phone",
                "input_partner_phone": "+1 202 555 0100",
                "input_activity_phone": False,
                "expected_partner_phone": "+1 202 555 0100",
            },
        ]
        for case in cases:
            with self.subTest(case=case["name"]):
                partner = self.env["res.partner"].create({
                    "name": case["name"],
                    "phone": case["input_partner_phone"],
                })
                with self._instantiate_activity_schedule_wizard(partner) as form:
                    form.activity_type_id = self.activity_type_call
                wizard = form.save()

                self.assertEqual(wizard.phone, case["input_partner_phone"])

                wizard.phone = case["input_activity_phone"]
                activity = wizard._action_schedule_activities()

                self.assertEqual(activity.phone, case["input_activity_phone"])
                self.assertEqual(partner.phone, case["expected_partner_phone"])

    def test_call_activity_schedule_keeps_record_phones_in_batch(self):
        """Batch scheduling keeps each record's own phone on its activity."""
        partners = self.env["res.partner"].create([
            {"name": "First partner", "phone": "+1 202 555 0101"},
            {"name": "Second partner", "phone": "+1 202 555 0102"},
        ])
        with self._instantiate_activity_schedule_wizard(partners) as form:
            form.activity_type_id = self.activity_type_call
        wizard = form.save()

        self.assertFalse(wizard.phone)

        activities = wizard._action_schedule_activities()

        self.assertEqual(
            set(activities.mapped("phone")),
            {"+1 202 555 0101", "+1 202 555 0102"},
        )
        self.assertEqual(
            set(partners.mapped("phone")),
            {"+1 202 555 0101", "+1 202 555 0102"},
        )

    def test_call_activity_schedule_does_not_update_multiple_related_partners(self):
        """Scheduling a Call cannot guess which of several partners to update."""
        partners = self.env["res.partner"].create([
            {"name": "First related partner"},
            {"name": "Second related partner"},
        ])
        target = self.user_employee
        with patch.object(
            self.env.registry[target._name],
            "_mail_get_partners",
            return_value={target.id: partners},
        ):
            with self._instantiate_activity_schedule_wizard(target) as form:
                form.activity_type_id = self.activity_type_call
            wizard = form.save()
            wizard.phone = "+1 202 555 0182"
            activity = wizard._action_schedule_activities()

        self.assertEqual(activity.phone, "+1 202 555 0182")
        self.assertFalse(any(partners.mapped("phone")))

    def test_call_activity_schedule_does_not_expose_inaccessible_phone(self):
        """Scheduling cannot expose a phone from an inaccessible record."""
        target = self.env["res.partner"].create({
            "name": "Restricted target",
            "company_id": self.company_2.id,
            "phone": "+1 202 555 0199",
        })
        wizard_model = self.env["mail.activity.schedule"].with_user(self.user_employee)
        with self.assertRaises(exceptions.AccessError):
            wizard_model.with_context(
                active_id=target.id,
                active_ids=target.ids,
                active_model=target._name,
            ).create({
                "res_model": target._name,
                "res_ids": str(target.ids),
                "activity_type_id": self.activity_type_call.id,
            }).read(["phone"])

    def test_activity_schedule_formats_prefilled_phone(self):
        """The scheduling wizard displays a localized phone number."""
        partner = self.env["res.partner"].create({
            "name": "US Partner",
            "country_id": self.env.ref("base.us").id,
            "phone": "6504193846",
        })
        wizard = self.env["mail.activity.schedule"].with_context(
            active_id=partner.id,
            active_ids=partner.ids,
            active_model=partner._name,
        ).create({
            "res_model": partner._name,
            "res_ids": str(partner.ids),
            "activity_type_id": self.env.ref("mail.mail_activity_data_call").id,
        })

        self.assertEqual(wizard.phone, "6504193846")
        self.assertEqual(wizard.phone_formatted, "+1 650-419-3846")
