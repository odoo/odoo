from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, users


@tagged('mail_track')
class TestMailTracking(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.x_test_model = cls.env['ir.model'].create({
            'name': 'Test Model',
            'model': 'x_test_model1',
            'is_mail_thread': True,
        })
        cls.env['ir.access'].create({
            'name': 'Employee Access',
            'model_id': cls.x_test_model.id,
            'group_id': cls.env.ref('base.group_user').id,
            'operation': 'cru',
        })
        cls.env['ir.model.fields'].create([
            {
                'name': 'x_boolean_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'boolean',
                'tracking': True,
            }, {
                'name': 'x_char_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'char',
                'tracking': True,
            }, {
                'name': 'x_date_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'date',
                'tracking': True,
            }, {
                'name': 'x_datetime_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'datetime',
                'tracking': True,
            }, {
                'name': 'x_float_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'float',
                'tracking': True,
            }, {
                'name': 'x_float_field_with_digits',
                'model_id': cls.x_test_model.id,
                'ttype': 'float',
                'tracking': True,
            }, {
                'name': 'x_integer_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'integer',
                'tracking': True,
            }, {
                'name': 'x_text_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'text',
                'tracking': True,
            }, {
                'name': 'x_many2one_field_id',
                'model_id': cls.x_test_model.id,
                'model': cls.x_test_model.model,
                'ttype': 'many2one',
                'relation': 'res.partner',
                'tracking': True,
            }, {
                'name': 'x_currency_id',
                'model_id': cls.x_test_model.id,
                'ttype': 'many2one',
                'relation': 'res.currency',
                'tracking': True,
            }, {
                'name': 'x_monetary_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'monetary',
                'currency_field': 'x_currency_id',
                'tracking': True,
            }, {
                'name': 'x_selection_field',
                'model_id': cls.x_test_model.id,
                'ttype': 'selection',
                'selection': "[('first','First'),('second','Second')]",
                'tracking': True,
            },
        ])
        cls.user_admin.tz = 'Asia/Kolkata'

    @users('employee')
    def test_mail_tracking_values_creation(self):
        """ Quick sanity check on mail.tracking.values creatien when posting
        a message with tracking values, now that base behavior is to have them
        as html. Other tests are defined in 'test_mail' module. """
        self.test_partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'email': 'test.partner@test.example.com',
            'name': 'Test Partner',
            'phone': '0456001122',
        })

        test_record = self.env[self.x_test_model.model].create({
            'x_char_field': 'test',
            'x_currency_id': self.env.company.currency_id.id,
        })
        self.flush_tracking()
        today = fields.Date.today()
        today_dt = fields.Datetime.to_datetime(today)
        now = fields.Datetime.now()

        with self.mock_mail_gateway(), self.mock_mail_app():
            test_record.with_user(self.user_admin).sudo().write({
                'x_boolean_field': True,
                'x_char_field': 'char_value',
                'x_date_field': today,
                'x_datetime_field': now,
                'x_float_field': 3.22,
                'x_float_field_with_digits': 3.00001,
                'x_integer_field': 42,
                'x_many2one_field_id': self.test_partner.id,
                'x_monetary_field': 42.42,
                'x_selection_field': 'first',
                'x_text_field': 'text_value',
            })
            self.flush_tracking()

        self.assertEqual(len(self._new_msgs), 1, 'Should have generated a tracking value')

        tracking_value_list = [
            ('x_boolean_field', 'boolean', False, True),
            ('x_char_field', 'char', 'test', 'char_value'),
            ('x_date_field', 'date', False, today_dt),
            ('x_datetime_field', 'datetime', False, now),
            ('x_float_field', 'float', 0, 3.22),
            ('x_float_field_with_digits', 'float', 0, 3.00001),
            ('x_integer_field', 'integer', 0, 42),
            ('x_many2one_field_id', 'many2one', self.env['res.partner'], self.test_partner),
            ('x_monetary_field', 'monetary', 0.0, 42.42, {'currency': self.env.ref('base.USD')}),
            ('x_selection_field', 'selection', '', 'First'),
            ('x_text_field', 'text', False, 'text_value'),
        ]
        self.assertMessageFields(self._new_msgs, {
            'body': '',
            'tracking_values': tracking_value_list,
        })

    @users('employee')
    def test_message_copy(self):
        partner = self.env['res.partner'].create({'name': 'Test'})
        self.flush_tracking()

        with self.mock_mail_gateway(), self.mock_mail_app():
            partner.name = 'New Test'
            self.flush_tracking()

        tracking_message = self._new_msgs.with_user(self.env.user)
        self.assertMessageFields(
            tracking_message, {
                'message_type': 'tracking',
                'tracking_values': [
                    ('name', 'char', 'Test', 'New Test'),
                    ('commercial_company_name', 'char', 'Test', 'New Test'),
                ],
            }
        )

        with self.assertRaises(UserError):
            tracking_message.copy({
                'message_type': 'notification',
            })

        new_tracking_message = tracking_message.copy()
        self.assertMessageFields(
            new_tracking_message, {
                'message_type': 'tracking',
                'tracking_values': [
                    ('name', 'char', 'Test', 'New Test'),
                    ('commercial_company_name', 'char', 'Test', 'New Test'),
                ],
            }
        )
        self.assertEqual(len((tracking_message + new_tracking_message).sudo().tracking_value_ids), 4, 'Not the same trackings')
