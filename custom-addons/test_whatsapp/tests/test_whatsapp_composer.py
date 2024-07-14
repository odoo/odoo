# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp, WhatsAppCommon
from odoo.tests import tagged, users


@tagged('wa_composer')
class WhatsAppComposerCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test records for sending messages
        cls.test_base_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': cls.env.ref('base.in').id,
                'name': 'Recipient-IN',
                'phone': "+91 12345 67891",
            }, {
                'country_id': cls.env.ref('base.be').id,
                'name': 'Recipient-BE',
                'phone': "0456001122",
            }
        ])

        # templates (considered as approved)
        cls.template_basic, cls.template_dynamic, cls.template_dynamic_cplx = cls.env['whatsapp.template'].create([
            {
                'body': 'Hello World',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-basic',
                'status': 'approved',
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': 'Hello {{1}}',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-dynamic',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'demo_value': 'Customer', 'field_name': 'name'}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
You are coming from {{3}}.
Welcome to {{4}} office''',
                'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
                'name': 'Test-dynamic-complex',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Jigar"}),
                    (0, 0, {'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
                    (0, 0, {'name': "{{3}}", 'line_type': "body", 'field_type': "field", 'demo_value': "sample country", 'field_name': 'country_id'}),
                    (0, 0, {'name': "{{4}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "Odoo In"}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }
        ])


@tagged('wa_composer')
class WhatsAppComposerRendering(WhatsAppComposerCase, WhatsAppFullCase, CronMixinCase, MockIncomingWhatsApp):
    """ Test rendering based on various templates, notably using static or
    dynamic content, headers, ... """

    def test_assert_initial_data(self):
        """ Ensure base data for tests, to ease understanding them """
        self.assertEqual(self.company_admin.country_id, self.env.ref('base.us'))
        self.assertEqual(self.user_admin.country_id, self.env.ref('base.be'))

    @users('employee')
    def test_composer_tpl_base(self):
        """ Test basic sending, with template, without rendering """
        template = self.template_basic.with_user(self.env.user)
        test_record = self.test_base_records[0]
        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            fields_values={
                'body': f'<p>{template.body}</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_base_rendering(self):
        """ Test sending with template and rendering """
        free_text = 'Odoo In'
        template = self.template_dynamic_cplx.with_user(self.env.user)
        test_record = self.test_base_records[0]
        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            fields_values={
                'body': f'<p>Hello I am {self.env.user.name},<br>Here my mobile number: {self.env.user.mobile},'
                        f'<br>You are coming from {test_record.country_id.name}.<br>Welcome to {free_text} office</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_base_rendering_datetime(self):
        """ Specific case involving datetimes """
        #template setup
        self.template_basic.write({
            'body' : 'Hello, your dates are here {{1}}',
            'variable_ids' : [
                (5, 0, 0),
                (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "field", 'demo_value': "2023-11-15 19:00:00", 'field_name': 'datetime'})
            ],
        })
        test_template = self.template_basic.with_user(self.env.user)

        #record setup without timezone field
        self.test_base_records[0].datetime = datetime(2024, 1, 19, 0, 0, 0)

        #record setup with timezone field
        test_record_with_tz = self.env['whatsapp.test.timezone'].create({
            'country_id': self.env.ref('base.be').id,
            'name': 'Recipient-IN',
            'phone': "+91 12345 67891",
            'datetime' : datetime(2024, 1, 19, 0, 0, 0),
            'tz' : 'Europe/Brussels',
        })

        #model setup
        wa_base_model_id = self.env['ir.model']._get_id('whatsapp.test.base')
        wa_tz_model_id = self.env['ir.model']._get_id('whatsapp.test.timezone')

        #record setup with timezone field with false value
        test_record_with_tz_false = test_record_with_tz.copy({'tz': False})
        test_record_with_datetime_false = test_record_with_tz.copy({'datetime': False})

        for test_record, user_tz, tmpl_model, expected_formatted_date in [
            (self.test_base_records[0], 'Asia/Kolkata', wa_base_model_id, 'Jan 19, 2024, 5:30:00 AM Asia/Kolkata'),
            (self.test_base_records[0], False, wa_base_model_id, 'Jan 19, 2024, 12:00:00 AM UTC'),
            (test_record_with_tz, 'Asia/Kolkata', wa_tz_model_id, 'Jan 19, 2024, 1:00:00 AM Europe/Brussels'),
            (test_record_with_tz, False, wa_tz_model_id, 'Jan 19, 2024, 1:00:00 AM Europe/Brussels'),
            (test_record_with_tz_false, 'Asia/Kolkata', wa_tz_model_id, 'Jan 19, 2024, 5:30:00 AM Asia/Kolkata'),
            (test_record_with_tz_false, False, wa_tz_model_id, 'Jan 19, 2024, 12:00:00 AM UTC'),
            (test_record_with_datetime_false, 'Asia/Kolkata', wa_tz_model_id, ''),
        ]:
            with self.subTest(test_record=test_record, user_tz=user_tz, tmpl_model=tmpl_model):
                self.env.user.tz = user_tz
                test_template.with_user(self.user_admin).model_id = tmpl_model
                composer = self._instanciate_wa_composer_from_records(test_template, test_record)
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()
                self.assertWAMessageFromRecord(
                    test_record,
                    fields_values={
                        'body': f'<p>Hello, your dates are here {expected_formatted_date}</p>',
                    },
                )

    @users('employee')
    def test_composer_tpl_base_rendering_selection(self):
        """ Specific case involving selections """
        # template setup
        self.template_basic.write({
            'body': 'Base model is here ({{1}}) and selection through m2o is here ({{2}})',
            'variable_ids': [
                (5, 0, 0),
                (0, 0, {
                    'name': '{{1}}',
                    'line_type': 'body',
                    'field_type': 'field',
                    'demo_value': 'Selection Demo Value 1',
                    'field_name': 'selection_field'
                }),
                (0, 0, {
                    'name': '{{2}}',
                    'line_type': 'body',
                    'field_type': 'field',
                    'demo_value': 'Selection Demo Value 4',
                    'field_name': 'selection_id.selection_field'
                })
            ],
        })
        test_template = self.template_basic.with_user(self.env.user)

        # record setup with selection field
        test_selection = self.env['whatsapp.test.selection'].create({
            'selection_field': 'selection_key_4',
        })
        test_base_selection_id = self.env['whatsapp.test.base'].create({
            "country_id": self.env.ref("base.be").id,
            "name": "Recipient-IN",
            "phone": "+91 12345 67891",
            "selection_id": test_selection.id,
        })

        # Check whether selection field values are sent and not keys
        composer = self._instanciate_wa_composer_from_records(test_template, test_base_selection_id)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_base_selection_id,
            fields_values={
                'body': '<p>Base model is here (Selection Value 1) and selection through m2o is here (Selection Value 4)</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_header_attachments(self):
        """ Send a template with a header attachment set through the composer."""
        doc_attach_clone = self.document_attachment.copy({'name': 'pdf_clone.pdf'})
        self.template_dynamic.write({
            'header_attachment_ids': [(6, 0, self.document_attachment.ids)],
            'header_type': 'document',
        })

        test_record = self.test_base_records[0].with_env(self.env)
        composer = self._instanciate_wa_composer_from_records(self.template_dynamic, test_record)
        composer.attachment_id = doc_attach_clone
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            attachment_values={
                'name': 'pdf_clone.pdf',
            },
            fields_values={
                'body': f'<p>Hello {test_record.name}</p>',
            },
        )

    @users('employee')
    def test_composer_tpl_header_report_resend(self):
        """ In case of resend and reports, it has to be generated again, so
        it deserves its own test. """
        # template setup with report
        self.template_basic.write({
            'header_type': 'document',
            'report_id': self.test_wa_base_report.id,
        })
        test_template = self.template_basic.with_user(self.env.user)
        test_record = self.test_base_records[0].with_env(self.env)

        composer = self._instanciate_wa_composer_from_records(test_template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessageFromRecord(
            test_record,
            attachment_values={
                'name': f'TestReport for {test_record.name}.html',
            },
            fields_values={
                'body': '<p>Hello World</p>',
            },
        )
        message = self._new_wa_msg
        old_attachment_ids = message.mail_message_id.attachment_ids

        # fail the message using the webhook
        self._receive_message_update(
            account=self.whatsapp_account,
            display_phone_number=self.test_base_records[0].phone,
            extra_value={
                "statuses": [{
                    "id": message.msg_uid,
                    "status": "failed",
                    "errors": [{
                        "code": 131000,
                        "title": "Message failed to send due to an unknown error."
                    }],
                }],
            },
        )

        # retry the failed message
        with self.capture_triggers('whatsapp.ir_cron_send_whatsapp_queue') as capt:
            message.button_resend()
        self.assertEqual(len(capt.records), 1)
        with self.mockWhatsappGateway():
            message._send_message()
        self._assertWAMessage(
            message,
            attachment_values={
                'name': f'TestReport for {test_record.name}.html',
            },
            fields_values={
                'body': '<p>Hello World</p>',
            },
        )
        self.assertFalse(old_attachment_ids.exists())
        self.assertTrue(message.mail_message_id.attachment_ids)

    @users('employee')
    def test_composer_tpl_header_various(self):
        """ Test sending with rendering, including header """
        sample_text = 'Header Free Text'

        base_variable_ids = [
            (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'demo_value': 'Customer', 'field_name': 'name'}),
        ]

        for header_type, template_upd_values, exp_att_values, exp_field_values in zip(
            (
                'text', 'text', 'text', 'text',
                'image',
                'video',
                'document', 'document', 'document',
                'location',
            ),
            (
                # text
                {'header_text': 'Header World'},
                {'header_text': 'Header {{1}}',
                 'variable_ids': [
                    (5, 0),
                    (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'free_text', 'demo_value': sample_text})
                 ] + base_variable_ids,
                 },
                {'header_text': 'Header {{1}}',
                 'variable_ids': [
                    (5, 0),
                    (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'user_name', 'demo_value': sample_text})
                 ] + base_variable_ids,
                 },
                {'header_text': 'Header {{1}}',
                 'variable_ids': [
                    (5, 0),
                    (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'user_mobile', 'demo_value': sample_text})
                 ] + base_variable_ids,
                 },
                # image
                {'header_attachment_ids': [(6, 0, self.image_attachment.ids)]},
                # video
                {'header_attachment_ids': [(6, 0, self.video_attachment.ids)]},
                # document
                {'header_attachment_ids': [(6, 0, self.document_attachment.ids)]},
                {'report_id': self.test_wa_base_report.id},
                {
                    'header_attachment_ids': [(6, 0, self.document_attachment.ids)],
                    'report_id': self.test_wa_base_report.id,
                },
                # location
                {'variable_ids': [
                    (0, 0, {'name': 'name', 'line_type': 'location', 'demo_value': 'LocName'}),
                    (0, 0, {'name': 'address', 'line_type': 'location', 'demo_value': 'Gandhinagar, Gujarat'}),
                    (0, 0, {'name': 'latitude', 'line_type': 'location', 'demo_value': '23.192985'}),
                    (0, 0, {'name': 'longitude', 'line_type': 'location', 'demo_value': '72.6366633'})],
                 },
            ), (
                # text
                {},
                {},
                {},
                {},
                # image
                {'name': self.image_attachment.name, 'datas': self.image_attachment.datas},
                # video
                {'name': self.video_attachment.name, 'datas': self.video_attachment.datas},
                # document
                {'name': self.document_attachment.name, 'datas': self.document_attachment.datas},
                {
                    'name': f'TestReport for {self.test_base_records[0].name}.html',
                    'raw': b'<div><p>External report for %s</p></div>' % self.test_base_records[0].name.encode(),
                },
                {
                    'name': f'TestReport for {self.test_base_records[0].name}.html',
                    'raw': b'<div><p>External report for %s</p></div>' % self.test_base_records[0].name.encode("utf-8"),
                },
                # location
                {},
            ), (
                # text
                {'body': f'<p><b>Header World</b></p><p>Hello {self.test_base_records[0].name}</p>'},
                {'body': f'<p><b>Header {sample_text}</b></p><p>Hello {self.test_base_records[0].name}</p>'},
                {'body': f'<p><b>Header {self.env.user.name}</b></p><p>Hello {self.test_base_records[0].name}</p>'},
                {'body': f'<p><b>Header {self.env.user.mobile}</b></p><p>Hello {self.test_base_records[0].name}</p>'},
                # image
                {},
                # video
                {},
                # document
                {},
                {},
                {},
                # location
                {},
            ),
        ):
            with self.subTest(header_type=header_type):
                self.template_dynamic.write({
                    'header_attachment_ids': [(5, 0, 0)],
                    'header_type': header_type,
                    'report_id': False,
                    **template_upd_values,
                })
                template = self.template_dynamic.with_user(self.env.user)
                composer = self._instanciate_wa_composer_from_records(template, self.test_base_records[0])
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()

                fields_values = {
                    'body': f'<p>Hello {self.test_base_records[0].name}</p>',
                }
                fields_values.update(**(exp_field_values or {}))
                self.assertWAMessageFromRecord(
                    self.test_base_records[0],
                    attachment_values=exp_att_values,
                    fields_values=fields_values,
                )
