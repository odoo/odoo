# -*- coding: utf-8 -*-

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.tests import common


class TestQwebFieldTime(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.time'].value_to_html(value, options)

    def test_time_value_to_html(self):
        default_fmt = {'format': 'h:mm a'}
        self.assertEqual(
            self.value_to_html(0, default_fmt),
            "12:00 AM"
        )

        self.assertEqual(
            self.value_to_html(11.75, default_fmt),
            "11:45 AM"
        )

        self.assertEqual(
            self.value_to_html(12, default_fmt),
            "12:00 PM"
        )

        self.assertEqual(
            self.value_to_html(14.25, default_fmt),
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

class TestQwebFieldContact(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.partner = cls.env['res.partner'].create({
            'name': 'Wood Corner',
            'email': 'wood.corner26@example.com',
            'phone': '(623)-853-7197',
            'website': 'http://www.wood-corner.com',
        })

    def test_value_to_html_with_website_and_phone(self):
        Contact = self.env["ir.qweb.field.contact"]
        result = Contact.value_to_html(self.partner, {"fields": ["phone", "website"]})
        self.assertIn('itemprop="website"', result)
        self.assertIn(self.partner.website, result)
        self.assertIn('itemprop="telephone"', result)
        self.assertIn(self.partner.phone, result)
        self.assertNotIn('itemprop="email"', result)

    def test_value_to_html_without_phone(self):
        Contact = self.env["ir.qweb.field.contact"]
        result = Contact.value_to_html(self.partner, {"fields": ["name", "website"]})
        self.assertIn('itemprop="website"', result)
        self.assertIn(self.partner.website, result)
        self.assertNotIn(self.partner.phone, result)
        self.assertIn('itemprop="telephone"', result, "Empty telephone itemprop should be added to prevent issue with iOS Safari")
