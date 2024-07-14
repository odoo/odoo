# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product

from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp
from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.tests import tagged, users


@tagged('wa_message')
class WhatsAppMessage(WhatsAppFullCase, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test records for sending messages
        cls.countries = (
            [cls.env.ref('base.be')] * 4 +
            [cls.env.ref('base.in'), cls.env.ref('base.ca'), cls.env.ref('base.us')] +
            [cls.env.ref('base.br')] * 2
        )
        cls.mobile_numbers = [
            "0456001122",
            "32456001133",
            "+32456001144",
            "+32456001155",
            "+91 1325 537171",
            "+1-613-555-0177",  # canada, same phone_code as US
            "+1-202-555-0124",  # us, same phone_code as CA
            "11 6123 4560",
            "+55 11 6123 4561",
        ]
        cls.test_base_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': country.id,
                'name': f'Recipient-{country.code}-{phone}',
                'phone': phone,
            } for country, phone in zip(cls.countries, cls.mobile_numbers)
        ])
        # WhatsApp formatting
        cls.mobile_numbers_formatted_wa = [
            "32456001122",
            "32456001133",
            "32456001144",
            "32456001155",
            "911325537171",
            "16135550177",
            "12025550124",
            "5511961234560",
            "5511961234561",
        ]
        # E164 (+ sign) formatting
        cls.mobile_numbers_formatted = [
            "+32456001122",
            "+32456001133",
            "+32456001144",
            "+32456001155",
            "+911325537171",
            "+16135550177",
            "+12025550124",
            "+5511961234560",
            "+5511961234561",
        ]
        # International formatting
        cls.mobile_numbers_formatted_intl = [
            "+32 456 00 11 22",
            "+32 456 00 11 33",
            "+32 456 00 11 44",
            "+32 456 00 11 55",
            "+91 1325 537 171",
            "+1 613-555-0177",
            "+1 202-555-0124",
            "+55 11 96123-4560",
            "+55 11 96123-4561",
        ]

        # test templates
        cls.test_template = cls.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'Test-basic',
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        })

    def test_assert_initial_values(self):
        """ Ensure base values used in tests """
        self.assertEqual(self.test_partner.country_id, self.env.ref('base.be'))
        self.assertEqual(self.test_partner.mobile, "0485001122")
        self.assertEqual(self.test_partner.phone, "0485221100")

        self.assertEqual(self.company_admin.country_id, self.env.ref('base.us'))
        self.assertEqual(self.user_admin.country_id, self.env.ref('base.be'))

        self.assertEqual(self.whatsapp_account.notify_user_ids, self.user_wa_admin)
        self.assertEqual(self.whatsapp_account_2.notify_user_ids, self.user_wa_admin)

    @users('employee')
    def test_message_values_from_composer(self):
        """ Check values produced when sending a message using composer """
        test_records = self.test_base_records.with_env(self.env)
        template = self.test_template.with_env(self.env)

        composer = self._instanciate_wa_composer_from_records(template, test_records)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        for record, exp_mobile_nbr, exp_mobile_nbr_formatted_wa in zip(
            test_records, self.mobile_numbers, self.mobile_numbers_formatted_wa
        ):
            with self.subTest(record=record, exp_mobile_nbr=exp_mobile_nbr):
                self.assertWAMessageFromRecord(
                    record,
                    status='outgoing',
                    fields_values={
                        'mobile_number': exp_mobile_nbr,
                        'mobile_number_formatted': exp_mobile_nbr_formatted_wa,
                        'wa_template_id': template,
                        'wa_account_id': self.whatsapp_account,
                    },
                    mail_message_values={
                        'message_type': 'whatsapp_message',
                        'partner_ids': self.user_wa_admin.partner_id,  # wa account responsible
                        'record_name': False,
                        'subtype_id': self.env.ref('mail.mt_note'),
                    },
                )

    def test_message_values_from_receive_new_number(self):
        """ Check values produced when receiving a new message from a new
        number. """
        for mobile_number, exp_mobile_nbr_formatted, _exp_mobile_nbr_formatted_intl, exp_country in zip(
            self.mobile_numbers_formatted_wa,
            self.mobile_numbers_formatted,
            self.mobile_numbers_formatted_intl,
            self.countries,
        ):
            with self.subTest(mobile_number=mobile_number):
                with self.mockWhatsappGateway():
                    self._receive_whatsapp_message(
                        self.whatsapp_account,
                        f"Hello from {mobile_number}",
                        mobile_number,
                    )

                new_partner = self._new_partners
                self.assertWhatsAppDiscussChannel(
                    mobile_number,
                    new_partner_values={
                        'country_id': exp_country,
                        'mobile': exp_mobile_nbr_formatted,
                        'name': exp_mobile_nbr_formatted,
                    },
                    channel_values={
                        'channel_type': 'whatsapp',
                        'name': mobile_number,
                        'wa_account_id': self.whatsapp_account,
                        'whatsapp_number': mobile_number,
                        'whatsapp_partner_id': new_partner,
                    },
                    wa_message_fields_values={
                        'message_type': 'inbound',
                        'mobile_number': exp_mobile_nbr_formatted,
                        'mobile_number_formatted': mobile_number,
                        'state': 'received',
                        'wa_template_id': self.env['whatsapp.template'],
                        'wa_account_id': self.whatsapp_account,
                    },
                    wa_mail_message_values={
                        'message_type': 'whatsapp_message',
                        'model': 'discuss.channel',
                        'partner_ids': self.env['res.partner'],
                        'record_name': mobile_number,  # probably due to channel name
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                )

    def test_message_values_from_receive_partner(self):
        """ Check values produced when receiving a new message from a number
        linked to a partner; check formatting / country support. """
        country_be_id = self.env.ref('base.be').id
        country_us_id = self.env.ref('base.us').id
        # note that we should never receive local numbers as input, not supported
        # hence not tested (e.g. 0485221100)
        incoming_numbers = [
            "32485221100",  # this is normally what we expect from WA
            "+32485221100",  # this is not what we expect but hey, people do stupid things everyday
        ]
        for (mobile, country_id), incoming_number in product(
            [
                ("0485221100", country_be_id),
                ("+32485221100", country_be_id),
                ("32485221100", country_be_id),
                ("+32 485 221 100", country_be_id),
                # wrong configurations
                ("0485221100", country_us_id),
            ], incoming_numbers
        ):
            with self.subTest(mobile=mobile, country_id=country_id, incoming_number=incoming_number):
                self.test_partner.write({
                    'country_id': country_id,
                    'mobile': mobile,
                    'phone': False,  # just test mobile here
                })
                with self.mockWhatsappGateway():
                    self._receive_whatsapp_message(
                        self.whatsapp_account,
                        f"Hello from {incoming_number}",
                        incoming_number,
                    )
                    self.assertFalse(self._new_partners, 'Should find partner even when formatting differs')
                    discuss_channel = self.assertWhatsAppDiscussChannel(
                        "32485221100",  # never keep "+"
                        channel_values={
                            'whatsapp_number': '32485221100',  # never keep "+"
                            'whatsapp_partner_id': self.test_partner,
                        },
                        wa_message_fields_values={
                            'mobile_number': '+32485221100',  # always with +
                            'mobile_number_formatted': '32485221100',  # never keep "+"
                        }
                    )

                    if self._new_partners:
                        self._new_partners.unlink()
                    discuss_channel.unlink()

    def test_message_values_from_forwarded_message(self):
        """ Check values produced when receiving a new forwarded message with missing "id" """
        template = self.whatsapp_template.with_user(self.env.user)
        test_record = self.test_base_record_nopartner.with_env(self.env)

        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        composer = self._instanciate_wa_composer_from_records(template, self.test_base_records)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, 'Hello', '32499123456', additional_message_values={"context": {"forwarded": True}}
            )

        self.assertWhatsAppDiscussChannel(
            "32499123456",
            wa_msg_count=1, msg_count=2,
            wa_message_fields_values={
                'state': 'received',
            },
        )
