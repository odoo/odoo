# -*- coding: utf-8 -*-

from odoo.tests import common


class TestQwebFieldTime(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.time'].value_to_html(value, options)

    def test_time_value_to_html(self):

        self.assertEqual(
            self.value_to_html(0),
            "12:00 AM"
        )

        self.assertEqual(
            self.value_to_html(11.75),
            "11:45 AM"
        )

        self.assertEqual(
            self.value_to_html(12),
            "12:00 PM"
        )

        self.assertEqual(
            self.value_to_html(14.25),
            "2:15 PM"
        )

        self.assertEqual(
            self.value_to_html(15.1, {'format': 'HH:mm:SS'}),
            "15:06:00"
        )

        # Only positive values can be used
        with self.assertRaises(ValueError):
            self.value_to_html(-6.5)

        # Only values inferior to 24 can be used
        with self.assertRaises(ValueError):
            self.value_to_html(24)


class TestQwebFieldInteger(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.integer'].value_to_html(value, options)

    def test_integer_value_to_html(self):
        self.assertEqual(self.value_to_html(1000), "1,000")
        self.assertEqual(self.value_to_html(1000000, {'format_decimalized_number': True}), "1M")
        self.assertEqual(
            self.value_to_html(125125, {'format_decimalized_number': True, 'precision_digits': 3}),
            "125.125k"
        )
