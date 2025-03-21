from unittest.mock import patch

from odoo.tests import common, tagged

from odoo.addons.sms.tests.common import SMSCase
from odoo.addons.sms.models.sms_sms import SmsSms
from odoo.addons.sms_twilio.tests.common import MockSmsTwilioApi


@tagged('post_install', '-at_install')
class TestSmsTwilio(MockSmsTwilioApi, SMSCase, common.TransactionCase):
    def test_send_sms_composer(self):
        with self.setup_and_mock_sms_twilio_gateway():
            for partner, number, body, expected_status, expected_failure_type, expected_to_delete in [
                (self.valid_partner, self.twilio_valid_phone_number, "Valid phone number", "pending", False, True),
                (self.invalid_partner, self.twilio_invalid_phone_number, "Invalid phone number", "error", "sms_number_format", False),
            ]:
                with self.subTest(
                    partner=partner, number=number, body=body,
                expected_status=expected_status, expected_failure_type=expected_failure_type, expected_to_delete=expected_to_delete
                ):
                    composer = self.env['sms.composer'].with_context(
                        active_model='res.partner',
                        active_id=partner,
                    ).create({'body': body})
                    composer._action_send_sms()
                    self.assertSMS(
                        partner, number, expected_status,
                        failure_type=expected_failure_type,
                        content=body,
                        fields_values={"to_delete": expected_to_delete},
                    )

    def test_multi_company_diff_providers(self):
        """Test that in a multi company environement, where each company decides how it should send SMS, that we respect this choice"""
        company_twilio = self.env.company
        company_twilio.write({
            "name": "Company 1 (Twilio)",
            "sms_provider": "twilio",
        })
        company_iap = self.env['res.company'].create({
            'name': "Company 2 (IAP)",
            "sms_provider": "iap",
        })
        self.env.user.company_ids |= company_iap

        partners_twilio = self.env['res.partner'].create([{
            "name": f"Partner Twilio {i}",
            "phone": f"+1220215415{i}",
            "company_id": company_twilio.id
        } for i in range(4)])

        partners_iap = self.env['res.partner'].create([{
            "name": f"Partner IAP {i}",
            "phone": f"+1220215415{i}",
            "company_id": company_iap.id
        } for i in range(4)])

        def patch_send(*args, **kwargs):
            pass  # Don't send so we can allow the cron to do its job (the SMS are therefore created but stay in outgoing state)

        with (
            self.setup_and_mock_sms_twilio_gateway(),
            patch.object(SmsSms, 'send', autospec=True, wraps=SmsSms, side_effect=patch_send)
        ):
            composer_twilio = self.env['sms.composer'].create({
                'body': "Sms via Twilio",
                'res_model': "res.partner",
                'res_ids': partners_twilio.ids,
                'composition_mode': 'mass',
            })
            composer_twilio._action_send_sms()

            for i in range(4):
                self.assertSMS(partners_twilio[i], f"+1220215415{i}", "outgoing", failure_type=False, content="Sms via Twilio")

            sms_twilio = self.env['sms.sms'].sudo().search([], order="id desc", limit=4)
            self.assertEqual(sms_twilio.record_company_id, company_twilio)

            composer_iap = self.env['sms.composer'].with_company(company_iap).create({
                'body': "Sms via IAP",
                'res_model': "res.partner",
                'res_ids': partners_iap.ids,
                'composition_mode': 'mass',
            })
            composer_iap._action_send_sms()

            for i in range(4):
                self.assertSMS(partners_iap[i], f"+1220215415{i}", "outgoing", failure_type=False, content="Sms via IAP")

            sms_iap = self.env['sms.sms'].sudo().search([], order="id desc", limit=4)
            self.assertEqual(sms_iap.record_company_id, company_iap)
