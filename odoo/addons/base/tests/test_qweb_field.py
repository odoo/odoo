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


class TestQwebFieldFloatConverter(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.float'].value_to_html(value, options)

    def test_float_value_to_html_no_precision(self):
        self.assertEqual(self.value_to_html(3), '3.0')
        self.assertEqual(self.value_to_html(3.1), '3.1')
        self.assertEqual(self.value_to_html(3.1231239), '3.123124')

    def test_float_value_to_html_with_precision(self):
        options = {'precision': 3}
        self.assertEqual(self.value_to_html(3, options), '3.000')
        self.assertEqual(self.value_to_html(3.1, options), '3.100')
        self.assertEqual(self.value_to_html(3.123, options), '3.123')
        self.assertEqual(self.value_to_html(3.1239, options), '3.124')

    def test_float_value_to_html_with_min_precision(self):
        options = {'min_precision': 3}
        self.assertEqual(self.value_to_html(3, options), '3.000')
        self.assertEqual(self.value_to_html(3.1, options), '3.100')
        self.assertEqual(self.value_to_html(3.123, options), '3.123')
        self.assertEqual(self.value_to_html(3.1239, options), '3.1239')
        self.assertEqual(self.value_to_html(3.1231239, options), '3.123124')

    def test_float_value_to_html_with_precision_and_min_precision(self):
        options = {'min_precision': 3, 'precision': 4}
        self.assertEqual(self.value_to_html(3, options), '3.000')
        self.assertEqual(self.value_to_html(3.1, options), '3.100')
        self.assertEqual(self.value_to_html(3.123, options), '3.123')
        self.assertEqual(self.value_to_html(3.1239, options), '3.1239')
        self.assertEqual(self.value_to_html(3.12349, options), '3.1235')


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


class TestQwebFieldOne2Many(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.one2many'].value_to_html(value, options)

    def test_one2many_empty(self):
        partner = self.env['res.partner'].create({'name': 'Test Parent'})
        self.assertFalse(self.value_to_html(partner.child_ids))

    def test_one2many_with_values(self):
        parent = self.env['res.partner'].create({'name': 'Parent'})
        self.env['res.partner'].create({'name': 'Child', 'parent_id': parent.id})
        self.assertEqual(self.value_to_html(parent.child_ids), "Parent, Child")


class TestQwebFieldMany2Many(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.many2many'].value_to_html(value, options)

    def test_many2many_empty(self):
        user = self.env['res.users'].create({'name': 'UserTest', 'login': 'usertest@example.com', 'groups_id': None})
        self.assertFalse(self.value_to_html(user.groups_id))

    def test_many2many_with_values(self):
        user = self.env['res.users'].create({
            'name': 'User2',
            'login': 'user2@example.com',
        })
        self.assertEqual(
            self.value_to_html(user.groups_id[:2]),
            'Technical / Access to export feature, Extra Rights / Contact Creation'
        )


class TestQwebFieldMany2One(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env['ir.qweb.field.many2one'].value_to_html(value, options)

    def test_many2one_empty(self):
        partner = self.env['res.partner'].create({'name': 'Lonely'})
        self.assertFalse(self.value_to_html(partner.parent_id))

    def test_many2one_with_value(self):
        parent = self.env['res.partner'].create({'name': 'BigBoss'})
        child = self.env['res.partner'].create({'name': 'Minion', 'parent_id': parent.id})
        self.assertEqual(self.value_to_html(child.parent_id), 'BigBoss')
