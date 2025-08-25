from odoo.addons.sms_twilio.tests.common import MockSmsTwilio
from odoo.tests import tagged, users


@tagged('post_install', '-at_install', 'twilio')
class TestSmsTwilio(MockSmsTwilio):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_sms_twilio(cls.user_admin.company_id)

    def test_assert_initial_values(self):
        self.assertEqual(self.valid_partner.phone, self.twilio_valid_phone_number)
        self.assertEqual(self.invalid_partner.phone, self.twilio_invalid_phone_number)

    @users('employee')
    def test_send_sms_composer_number(self):
        for number, expected_status, expected_failure_type, expected_to_delete in [
            (self.twilio_valid_phone_number, "pending", False, True),
            (self.twilio_invalid_phone_number, "error", "sms_number_format", False),
        ]:
            with self.subTest(number=number):
                with self.mock_sms_twilio_gateway(ok=(number != self.twilio_invalid_phone_number)):
                    body = f"Send SMS to {number}"
                    composer = self.env['sms.composer'].create({
                        'body': body,
                        'composition_mode': 'numbers',
                        'numbers': number,
                    })
                    composer._action_send_sms()
                    self.assertSMS(
                        self.env["res.partner"], number, expected_status,
                        content=body,
                        failure_type=expected_failure_type,
                        fields_values={
                            "to_delete": expected_to_delete,
                        },
                    )

    @users('employee')
    def test_send_sms_composer_partner(self):
        for partner, expected_status, expected_failure_type, expected_to_delete in [
            (self.valid_partner, "pending", False, True),
            (self.invalid_partner, "error", "sms_number_format", False),
        ]:
            with self.subTest(partner=partner, number=partner.phone):
                with self.mock_sms_twilio_gateway(ok=(partner != self.invalid_partner)):
                    body = f"Send SMS to {partner.name}"
                    composer = self.env['sms.composer'].with_context(
                        active_model='res.partner',
                        active_id=partner,
                    ).create({'body': body})
                    composer._action_send_sms()
                    self.assertSMS(
                        partner, partner.phone, expected_status,
                        content=body,
                        failure_type=expected_failure_type,
                        fields_values={
                            "to_delete": expected_to_delete,
                        },
                    )

    @users('employee')
    def test_send_with_multi_company(self):
        """Test that in a multi company environment where each company decides
        how it should send SMS that we respect this choice. """
        company_twilio = self.env.company
        company_twilio.sudo().write({
            "name": "Company 1 (Twilio)",
            "sms_provider": "twilio",
        })
        company_twilio_2 = self.env['res.company'].sudo().create({
            "name": "Company 2 (Twilio)",
            "sms_provider": "twilio",
            "sms_twilio_account_sid": "AC11111222223333344444555556666677",
            "sms_twilio_auth_token": "skarsnik",
        })
        company_iap = self.env['res.company'].sudo().create({
            "name": "Company 3 (IAP)",
            "sms_provider": "iap",
        })
        company_iap_2 = self.env['res.company'].sudo().create({
            "name": "Company 4 (IAP)",
            "sms_provider": "iap",
        })
        self.env.user.sudo().company_ids |= company_twilio_2 + company_iap + company_iap_2

        partners_twilio = self.env['res.partner'].create([{
            "name": f"Partner Twilio {i}",
            "phone": f"+1220215411{i}",
            "company_id": company_twilio.id
        } for i in range(2)])

        partners_twilio_2 = self.env['res.partner'].create([{
            "name": f"Partner Twilio2 {i}",
            "phone": f"+1220215422{i}",
            "company_id": company_twilio_2.id
        } for i in range(2)])

        partners_iap = self.env['res.partner'].create([{
            "name": f"Partner IAP {i}",
            "phone": f"+1220215433{i}",
            "company_id": company_iap.id
        } for i in range(2)])

        partners_iap_2 = self.env['res.partner'].create([{
            "name": f"Partner IAP2 {i}",
            "phone": f"+1220215444{i}",
            "company_id": company_iap_2.id
        } for i in range(2)])

        with (
            self.mockSMSGateway(),
            self.mock_sms_twilio_send(),
        ):
            composer_twilio = self.env['sms.composer'].create({
                "body": "Mixed SMS",
                "composition_mode": 'mass',
                "mass_force_send": True,
                "res_ids": (partners_twilio + partners_twilio_2 + partners_iap + partners_iap_2).ids,
                "res_model": "res.partner",
            })
            composer_twilio._action_send_sms()

            # should call twilio 4 times (4 partners, one number at a time) and IAP 1 time (batch, even different companies)
            self.assertEqual(self._sms_twilio_send_mock.call_count, 4)
            self.assertEqual(self._sms_api_contact_iap_mock.call_count, 1)

            # check SMS statuses
            # TDE FIXME: in mass mode without mailing, no sms_tracker are created hence
            # sms_twilio_sid is not stored ... meh
            for partner in partners_twilio:
                self.assertSMS(
                    partner, partner.phone, "pending",
                    content="Mixed SMS",
                    failure_type=False,
                    fields_values={
                        "record_company_id": company_twilio,
                    },
                )
            for partner in partners_twilio_2:
                self.assertSMS(
                    partner, partner.phone, "pending",
                    content="Mixed SMS",
                    failure_type=False,
                    fields_values={
                        "record_company_id": company_twilio_2,
                    },
                )
            for partner in partners_iap:
                self.assertSMS(
                    partner, partner.phone, "pending",
                    content="Mixed SMS",
                    failure_type=False,
                    fields_values={
                        "record_company_id": company_iap,
                    },
                )
            for partner in partners_iap_2:
                self.assertSMS(
                    partner, partner.phone, "pending",
                    content="Mixed SMS",
                    failure_type=False,
                    fields_values={
                        "record_company_id": company_iap_2,
                    },
                )
