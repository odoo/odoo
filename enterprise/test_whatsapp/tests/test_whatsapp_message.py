# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product
from unittest.mock import patch


from odoo.addons.base.models.ir_cron import ir_cron as IrCronModel
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.whatsapp.models.whatsapp_message import WhatsAppMessage as WhatsappMessageModel
from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp
from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.tests import tagged, users


@tagged('wa_message')
class WhatsAppMessage(WhatsAppFullCase, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.public_user = mail_new_test_user(
            cls.env, login='public_test', groups='base.group_public',
            company_id=cls.company_admin.id, name='Public User'
        )
        # test records for sending messages
        cls.countries = (
            [cls.env.ref('base.be')] * 4 +
            [cls.env.ref('base.in'), cls.env.ref('base.ca'), cls.env.ref('base.us')] +
            [cls.env.ref('base.br')] * 2 +
            [cls.env.ref('base.ci')] * 2 +
            [cls.env.ref('base.mx')] * 3
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
            "0708151718",
            "+225 0708151719",
            "5585460749",
            "15585440749",
            "+52 15585440659",
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
            "2250708151718",
            "2250708151719",
            "525585460749",
            "525585440749",
            "525585440659",
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
            "+2250708151718",
            "+2250708151719",
            "+525585460749",
            "+525585440749",
            "+525585440659",
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
            "+225 07 08 151 718",
            "+225 07 08 151 719",
            "+52 55 8546 0749",
            "+52 55 8544 0749",
            "+52 55 8544 0659",
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

    def test_blacklist_enforcement_cross_country(self):
        """ Test that blacklist enforcement works correctly when the company country
        differs from the partner's phone number country."""
        company_de = self.env.ref('base.de')
        self.company_admin.write({'country_id': company_de.id})
        self.user_wa_admin.write({'country_id': False})

        phone_number_local = "+32456001122"
        phone_number_wa = "32456001122"

        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'country_id': False,
            'mobile': phone_number_local,
        })

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(self.whatsapp_account, "STOP", phone_number_wa)

        blacklist_entries = self.env['phone.blacklist'].sudo().search([('number', '=', phone_number_local)])
        self.assertTrue(blacklist_entries, "Blacklist entry should be created")

        composer = self._instanciate_wa_composer_from_records(
            self.simple_whatsapp_template, partner, with_user=self.user_wa_admin
        )

        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self.assertWAMessageFromRecord(
            partner,
            status='error',
            fields_values={
                'failure_type': 'blacklisted',
            }
        )

    @users('employee')
    def test_message_values_from_composer(self):
        """ Check values produced when sending a message using composer """
        test_records = self.test_base_records.with_env(self.env)
        template = self.test_template.with_env(self.env)
        partner_ids = self.env['whatsapp.account'].search([], limit=1).notify_user_ids.partner_id

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
                        'partner_ids': partner_ids,
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

    def test_receive_attachment(self):
        """Ensure incoming attachments are processed and attached to messages properly."""
        # Image
        with self.mockWhatsappGateway(), self.mock_mail_app():
            self._wa_document_store['image_doc_id'] = self.image_attachment_wa_admin.raw
            self._receive_whatsapp_message(
                self.whatsapp_account, 'Hello', '32499123456', message_type="image", content_values={
                    'mime_type': self.image_attachment_wa_admin.mimetype,
                    'sha256': '',  # currently not checked...
                    'id': 'image_doc_id',
                }
            )
        self.assertWhatsAppDiscussChannel(
            "32499123456",
            wa_msg_count=1, msg_count=1,
            wa_message_fields_values={
                'state': 'received',
            },
        )
        channel_message = self._new_msgs.filtered(lambda msg: msg.model == 'discuss.channel')
        self.assertEqual(len(channel_message.attachment_ids), 1)
        self.assertEqual(channel_message.attachment_ids.datas, self.image_attachment_wa_admin.datas)
        # Voice
        with self.mockWhatsappGateway(), self.mock_mail_app():
            self._wa_document_store['audio_doc_id'] = self.audio_attachment_wa_admin.raw
            self._receive_whatsapp_message(
                self.whatsapp_account, 'Hello', '32499123456', message_type="image", content_values={
                    'filename': 'audio.ogg',
                    'id': 'audio_doc_id',
                    'mime_type': self.audio_attachment_wa_admin.mimetype,
                    'sha256': '',
                    'voice': True,
                }
            )
        self.assertWhatsAppDiscussChannel(
            "32499123456",
            wa_msg_count=2, msg_count=2,
            wa_message_fields_values={
                'state': 'received',
            },
        )
        self.assertEqual(len(self._new_msgs), 1)
        attachment = self._new_msgs.attachment_ids
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.datas, self.audio_attachment_wa_admin.datas)
        self.assertEqual(attachment.name, "audio.ogg")
        self.assertTrue(attachment.voice_ids)

    @users('public_test')
    def test_send_as_public_user(self):
        """Check that public users creating a message properly sends it afterwards."""
        test_record = self.test_base_records[0].with_user(self.env.user)
        # clear cache to force fetch as user
        test_record.invalidate_recordset()

        original_trigger = IrCronModel._trigger

        def patched_cron_trigger(cron, at=None):
            """Immediately run the send message cron in the current thread if it is not scheduled."""
            if at is None and cron == self.env.ref('whatsapp.ir_cron_send_whatsapp_queue'):
                # clear test record as cron wouldn't have anything cached
                self.test_base_records.invalidate_recordset()
                cron.with_user(self.env.ref('base.user_root')).sudo(False).method_direct_trigger()
                return
            return original_trigger(cron, at=at)

        self.whatsapp_template.write({
            'body': 'Hi {{1}}, this is {{2}}',
            'status': 'approved',
            'variable_ids': [
                (5, 0, 0),
                (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'demo_value': 'Customer', 'field_name': 'name'}),
                (0, 0, {'name': '{{2}}', 'line_type': 'body', 'field_type': 'user_name', 'demo_value': 'Author'}),
            ],
        })

        with self.mockWhatsappGateway(), \
             patch('odoo.addons.base.models.ir_cron.ir_cron._trigger', patched_cron_trigger):
            self.env['whatsapp.composer'].sudo().create({
                'wa_template_id': self.whatsapp_template.id,
                'res_model': test_record._name,
                'res_ids': str(test_record.id),
            })._send_whatsapp_template(force_send_by_cron=True)
        self.assertWAMessageFromRecord(
            test_record,
            mail_message_values={
                'body': '<p>Hi Recipient-BE-0456001122, this is Public User</p>',
            },
            status='sent',
        )
