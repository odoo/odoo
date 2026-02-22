from odoo import fields
from odoo.addons.mail.tests.common import MailCommon


class TestMailTracking(MailCommon):
    def setUp(self):
        super().setUp()
        self.x_test_model = self.env['ir.model'].create({
            'name': 'Test Model',
            'model': 'x_test_model1',
            'is_mail_thread': True,
        })
        self.env['ir.model.fields'].create([
            {
                'name': 'x_boolean_field',
                'model_id': self.x_test_model.id,
                'ttype': 'boolean',
                'tracking': True,
            }, {
                'name': 'x_char_field',
                'model_id': self.x_test_model.id,
                'ttype': 'char',
                'tracking': True,
            }, {
                'name': 'x_date_field',
                'model_id': self.x_test_model.id,
                'ttype': 'date',
                'tracking': True,
            }, {
                'name': 'x_datetime_field',
                'model_id': self.x_test_model.id,
                'ttype': 'datetime',
                'tracking': True,
            }, {
                'name': 'x_float_field',
                'model_id': self.x_test_model.id,
                'ttype': 'float',
                'tracking': True,
            }, {
                'name': 'x_float_field_with_digits',
                'model_id': self.x_test_model.id,
                'ttype': 'float',
                'tracking': True,
            }, {
                'name': 'x_integer_field',
                'model_id': self.x_test_model.id,
                'ttype': 'integer',
                'tracking': True,
            }, {
                'name': 'x_text_field',
                'model_id': self.x_test_model.id,
                'ttype': 'text',
                'tracking': True,
            }, {
                'name': 'x_many2one_field_id',
                'model_id': self.x_test_model.id,
                'model': self.x_test_model.model,
                'ttype': 'many2one',
                'relation': 'res.partner',
                'tracking': True,
            }, {
                'name': 'x_currency_id',
                'model_id': self.x_test_model.id,
                'ttype': 'many2one',
                'relation': 'res.currency',
                'tracking': True,
            }, {
                'name': 'x_monetary_field',
                'model_id': self.x_test_model.id,
                'ttype': 'monetary',
                'currency_field': 'x_currency_id',
                'tracking': True,
            }, {
                'name': 'x_selection_field',
                'model_id': self.x_test_model.id,
                'ttype': 'selection',
                'selection': "[('first','First'),('second','Second')]",
                'tracking': True,
            },
        ])

        self.user_admin.tz = 'Asia/Kolkata'

    def test_mail_tracking_values_are_created_correctly(self):
        self.test_partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'email': 'test.partner@test.example.com',
            'name': 'Test Partner',
            'phone': '0456001122',
        })

        test_record = self.env[self.x_test_model.model].create({
            'x_char_field': 'test',
        })
        self.flush_tracking()
        messages = test_record.message_ids
        today = fields.Date.today()
        today_dt = fields.Datetime.to_datetime(today)
        now = fields.Datetime.now()

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

        new_message = test_record.message_ids - messages
        self.assertEqual(len(new_message), 1, 'Should have generated a tracking value')

        tracking_values = {tv.field_id.name: tv for tv in new_message.tracking_value_ids}

        tracking_value_list = [
            ('x_boolean_field', 'integer', False, True),
            ('x_char_field', 'char', 'test', 'char_value'),
            ('x_date_field', 'datetime', False, today_dt),
            ('x_datetime_field', 'datetime', False, now),
            ('x_float_field', 'float', 0, 3.22),
            ('x_float_field_with_digits', 'float', 0, 3.00001),
            ('x_integer_field', 'integer', 0, 42),
            ('x_many2one_field_id', 'char', '', self.test_partner.display_name),
            ('x_monetary_field', 'float', 0.0, 42.42),
            ('x_selection_field', 'char', '', 'First'),
            ('x_text_field', 'text', False, 'text_value'),
        ]

        for field_name, field_type, old, new in tracking_value_list:
            tracking = tracking_values[field_name]
            self.assertEqual(tracking[f"old_value_{field_type}"], old, f"Old value mismatch for field '{field_name}'")
            self.assertEqual(tracking[f"new_value_{field_type}"], new, f"New value mismatch for field '{field_name}'")

        self.assertEqual(len(tracking_values), len(tracking_value_list),
                         "Tracking values count mismatch")
