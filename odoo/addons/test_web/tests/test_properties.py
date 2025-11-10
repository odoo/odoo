import datetime
import json


import babel.dates

from odoo.addons.test_orm.tests.test_properties import TestPropertiesMixin
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tests import tagged, Form
from odoo.tools import get_lang, mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
class PropertiesCase(TestPropertiesMixin):
    def test_properties_web_read(self):
        """Test the web_read method when reading properties field."""
        self.message_1.write({
            'attributes': [{
                'name': 'discussion_color_code',
                'string': 'Test color code',
                'type': 'char',
                'default': 'blue',
                'value': 'purple',
                'definition_changed': True,
            }, {
                'name': 'selection',
                'string': 'Selection',
                'type': 'selection',
                'selection': [['a', 'A'], ['b', 'B']],
                'value': 'b',
                'definition_changed': True,
            }, {
                'name': 'moderator_partner_id',
                'string': 'Partner',
                'type': 'many2one',
                'comodel': 'test_orm.partner',
                'value': [self.partner.id, 'Bob'],
                'definition_changed': True,
            }, {
                'name': 'moderator_partner_ids',
                'string': 'Partners',
                'type': 'many2many',
                'comodel': 'test_orm.partner',
                'value': [[self.partner.id, 'Bob'], [self.partner_2.id, "Alice"]],
                'definition_changed': True,
            }],
        })

        result = self.message_1.web_read({
            'attributes': {
                'fields': {
                    'moderator_partner_id': {'fields': {'name': {}}},
                    'moderator_partner_ids': {'fields': {'name': {}}},
                    'selection': {},
                },
            },
        })
        self.assertEqual(result[0]['attributes'], [{
            'name': 'moderator_partner_id',
            'string': 'Partner',
            'type': 'many2one',
            'comodel': 'test_orm.partner',
            'value': [{'id': self.partner.id, 'name': 'Test Partner Properties'}],
        }, {
            'name': 'moderator_partner_ids',
            'string': 'Partners',
            'type': 'many2many',
            'comodel': 'test_orm.partner',
            'value': [
                {'id': self.partner.id, 'name': 'Test Partner Properties'},
                {'id': self.partner_2.id, 'name': 'Test Partner Properties 2'},
            ],
        }, {
            'name': 'selection',
            'string': 'Selection',
            'type': 'selection',
            'selection': [['a', 'A'], ['b', 'B']],
            'value': 'b',
        }])

    def test_properties_field_html(self):
        """Test that the HTML values are sanitized."""
        xss_payload = "<img src='x' onerror='alert(1)'/>"
        expected = '<img src="x">'
        self.message_2.attributes = [
            {
                "name": "test_html",
                "type": "html",
                "string": "HTML",
                "default": xss_payload,
                "value": xss_payload,
                "definition_changed": True,
            },
        ]

        sql_values = self._get_sql_properties(self.message_2)
        self.assertEqual(sql_values.get("test_html"), expected)

        self.assertEqual(dict(self.message_2.attributes)['test_html'], expected)
        self.assertEqual(self.message_2.attributes['test_html'], expected)

        with self.assertRaises(UserError):
            self.env['test_orm.message']._read_group([], ['attributes.test_html'])

        with self.assertRaises(UserError):
            self.env['test_orm.message'].web_read_group([], ['attributes.test_html'])

        properties = self.message_2.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], expected)
        self.assertEqual(properties[0]['default'], expected)

        definition = self.message_2.discussion.attributes_definition
        self.assertEqual(definition[0]['default'], expected)

        definition = self.message_2.discussion.read(['attributes_definition'])[0]['attributes_definition']
        self.assertEqual(definition[0]['default'], expected)

        # write a dict on the record
        self.message_2.attributes = {'test_html': xss_payload}
        self.assertEqual(self.message_2.attributes['test_html'], expected)
        properties = self.message_2.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], expected)

        with self.assertRaises(ValueError):
            self.message_2.attributes = [
                {
                    "name": "text_html",
                    "type": "text",
                    "string": "HTML",
                    "default": xss_payload,
                    "value": xss_payload,
                    "definition_changed": True,
                },
            ]

        with self.assertRaises(ValueError):
            self.message_2.discussion.attributes_definition = [
                {
                    "name": "text_html",
                    "type": "text",
                    "string": "HTML",
                    "default": xss_payload,
                    "definition_changed": True,
                },
            ]

        message = self.env['test_orm.message'].with_context(default_attributes_test_html=xss_payload).create({'discussion': self.discussion_1.id})
        self.assertEqual(message.attributes['test_html'], expected)
        sql_values = self._get_sql_properties(message)
        self.assertEqual(sql_values.get("test_html"), expected)

    @mute_logger('odoo.fields')
    def test_properties_field_onchange2(self):
        """If we change the definition record, the onchange of the properties field must be triggered."""
        message_form = Form(self.env['test_orm.message'])

        with self.assertQueryCount(8):
            message_form.discussion = self.discussion_1
            message_form.author = self.user

            self.assertEqual(
                message_form.attributes,
                [{
                    'name': 'discussion_color_code',
                    'string': 'Color Code',
                    'type': 'char',
                    'default': 'blue',
                    'value': 'blue',
                }, {
                    'name': 'moderator_partner_id',
                    'string': 'Partner',
                    'type': 'many2one',
                    'comodel': 'test_orm.partner',
                }],
                msg='Should take the new definition when changing the definition record',
            )

            # change the discussion field
            message_form.discussion = self.discussion_2

            properties = message_form.attributes

            self.assertEqual(len(properties), 1)
            self.assertEqual(
                properties[0]['name'],
                'state',
                msg='Should take the values of the new definition record',
            )

        with self.assertQueryCount(6):
            message = message_form.save()

        self.assertEqual(message.attributes, {'state': 'draft'})

        # check cached value
        cached_value = self.env.cache.get(message, message._fields['attributes'])
        self.assertEqual(cached_value, {'state': 'draft'})

        # change the definition record, change the definition and add default values
        self.assertEqual(message.discussion, self.discussion_2)

        with self.assertQueryCount(4):
            message.discussion = self.discussion_1
        self.assertEqual(
            self.discussion_1.attributes_definition,
            [{
                'name': 'discussion_color_code',
                'type': 'char',
                'string': 'Color Code',
                'default': 'blue',
                }, {
                    'name': 'moderator_partner_id',
                    'type': 'many2one',
                    'string': 'Partner',
                    'comodel': 'test_orm.partner',
                }],
            )
        self.assertEqual(
            message.read()[0]['attributes'],
            [{
                'name': 'discussion_color_code',
                'type': 'char',
                'string': 'Color Code',
                'default': 'blue',
                'value': 'blue',
            }, {
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'string': 'Partner',
                'comodel': 'test_orm.partner',
            }],
        )

        self.discussion_1.attributes_definition = False
        self.discussion_2.attributes_definition = [{
            'name': 'test',
            'type': 'char',
            'default': 'Default',
        }]

        # change the message discussion to remove the properties
        # discussion 1 -> discussion 2
        message.discussion = self.discussion_2
        message.attributes = [{'name': 'test', 'value': 'Test'}]
        fields_spec = message._get_fields_spec()
        self.assertIn('discussion', fields_spec)
        self.assertIn('attributes', fields_spec)
        values = {
            'discussion': self.discussion_1.id,
            'attributes': [{
                'name': 'test',
                'type': 'char',
                'default': 'Default',
                'value': 'Test',
            }],
        }
        result = message.onchange(values, ['discussion'], fields_spec)
        self.assertIn('attributes', result['value'], 'Should have detected the definition record change')
        self.assertEqual(result['value']['attributes'], [], 'Should have reset the properties definition')

        # change the message discussion to add new properties
        # discussion 2 -> discussion 1
        message.discussion = self.discussion_1
        values = {
            'discussion': self.discussion_2.id,
            'attributes': [],
        }
        result = message.onchange(values, ['discussion'], fields_spec)
        self.assertIn('attributes', result['value'], 'Should have detected the definition record change')
        self.assertEqual(
            result['value']['attributes'],
            [{'name': 'test', 'type': 'char', 'default': 'Default', 'value': 'Default'}],
            'Should have reset the properties definition to the discussion 1 definition',
        )

        # change the definition record and the definition at the same time
        message_form = Form(message)
        message_form.discussion = self.discussion_2
        message_form.attributes = [{
            'name': 'new_property',
            'type': 'char',
            'value': 'test value',
            'definition_changed': True,
        }]
        message = message_form.save()
        self.assertEqual(
            self.discussion_2.attributes_definition,
            [{'name': 'new_property', 'type': 'char'}])
        self.assertEqual(
            message.attributes,
            {'new_property': 'test value'})

        # re-write the same parent again and check that value are not reset
        message.discussion = message.discussion
        self.assertEqual(
            message.attributes,
            {'new_property': 'test value'})

        # trigger a other onchange after setting the properties
        # and check that it does not impact the properties
        message.discussion.attributes_definition = []
        message_form = Form(message)
        message.attributes = [{
            'name': 'new_property',
            'type': 'char',
            'value': 'test value',
            'definition_changed': True,
        }]
        message_form.body = "a" * 42
        message = message_form.save()
        self.assertEqual(
            message.attributes,
            {'new_property': 'test value'})


@tagged('at_install', '-post_install')  # LEGACY at_install
class PropertiesGroupByCase(TestPropertiesMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_4 = cls.env['test_orm.message'].create({
            'name': 'Test Message',
            'discussion': cls.discussion_1.id,
            'author': cls.user.id,
        })

        cls.messages = cls.message_1 | cls.message_2 | cls.message_3 | cls.message_4
        cls.env['test_orm.message'].search([('id', 'not in', cls.messages.ids)]).unlink()

        cls.wrong_discussion_id = cls.env['test_orm.discussion'].search(
            [], order="id DESC", limit=1).id + 1000

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_basic(self):
        Model = self.env['test_orm.message']

        self.messages.discussion = self.discussion_1
        # search on text properties
        self.message_1.attributes = [{
            'name': 'mychar',
            'type': 'char',
            'value': 'qsd',
            'definition_changed': True,
        }, {
            'name': 'myinteger',
            'type': 'integer',
            'value': 1337,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mychar': 'qsd', 'myinteger': 5}
        self.message_3.attributes = {'mychar': 'boum', 'myinteger': 1337}

        # group by the char property
        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.mychar'],
            )

        self.assertEqual(len(result), 3)

        # check counts
        count_by_values = {
            value['attributes.mychar']: value['__count']
            for value in result
        }
        self.assertEqual(count_by_values['boum'], 1)
        self.assertEqual(count_by_values['qsd'], 2)
        self.assertEqual(count_by_values[False], 1)

        # check domains
        domain_by_values = {
            value['attributes.mychar']: value['__extra_domain']
            for value in result
        }
        self.assertEqual(domain_by_values['boum'], [('attributes.mychar', '=', 'boum')])
        self.assertEqual(domain_by_values['qsd'], [('attributes.mychar', '=', 'qsd')])
        self._check_domains_count(result)

        # group by the integer property
        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger'],
            )

        self.assertEqual(len(result), 3)
        count_by_values = {
            value['attributes.myinteger']: value['__count']
            for value in result
        }

        self.assertEqual(count_by_values[5], 1)
        self.assertEqual(count_by_values[1337], 2)
        self.assertEqual(count_by_values[False], 1)

        # falsy properties
        self.message_3.attributes = {'mychar': False, 'myinteger': False}
        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger'],
            )

        self.assertEqual(result[-1]['__count'], 2)
        self.assertEqual(result[-1]['__extra_domain'], [('attributes.myinteger', '=', False)])
        self._check_domains_count(result)

        # non existing keys in the dict values should be grouped with False value
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = '{}'
             WHERE id = %s
            """,
            [self.message_2.id],
        )
        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger'],
            )

        self.assertEqual(result[-1]['__count'], 3)
        self.assertEqual(result[-1]['__extra_domain'], [('attributes.myinteger', '=', False)])
        result = Model.search(result[-1]['__extra_domain'])  # check the domain is correct for the search
        self.assertEqual(result, self.message_2 | self.message_3 | self.message_4)

        # test the order by
        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.myinteger'],
            order='attributes.myinteger ASC',
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['attributes.myinteger'], 1337)
        self.assertEqual(result[1]['attributes.myinteger'], False)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.myinteger'],
            order='attributes.myinteger DESC',
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['attributes.myinteger'], False)
        self.assertEqual(result[1]['attributes.myinteger'], 1337)
        self._check_domains_count(result)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.myinteger', 'name'],
            order='attributes.myinteger DESC',
        )
        self.assertEqual(
            result[0]['__extra_domain'],
            ['&', ('attributes.myinteger', '=', False), ('name', '=', self.message_1.name)],
        )
        self._check_domains_count(result)

    def test_properties_field_web_read_group(self):
        self.messages.discussion = self.discussion_1
        # search on text properties
        self.message_1.attributes = [{
            'name': 'mychar',
            'type': 'char',
            'value': 'qsd',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mychar': 'qsd'}
        self.message_3.attributes = {'mychar': 'boum'}

        Model = self.env['test_orm.message']
        with self.assertQueryCount(6):  # 3 for formatted_read_group + 1 query by group opened
            result = Model.web_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.mychar'],
                auto_unfold=True,
                unfold_read_specification={'id': {}},
            )
        groups = result['groups']

        self.assertEqual(len(groups), 3)

        # check counts
        count_by_values = {
            value['attributes.mychar']: value['__count']
            for value in groups
        }
        self.assertEqual(count_by_values['boum'], 1)
        self.assertEqual(count_by_values['qsd'], 2)
        self.assertEqual(count_by_values[False], 1)

        # check domains
        domain_by_values = {
            value['attributes.mychar']: value['__extra_domain']
            for value in groups
        }
        self.assertEqual(domain_by_values['boum'], [('attributes.mychar', '=', 'boum')])
        self.assertEqual(domain_by_values['qsd'], [('attributes.mychar', '=', 'qsd')])
        self._check_domains_count(groups)

        # group boum
        self.assertEqual(groups[0]['__records'], [{'id': self.message_3.id}])
        # group qsd
        self.assertEqual(groups[1]['__records'], [{'id': self.message_1.id}, {'id': self.message_2.id}])
        # group False
        self.assertEqual(groups[2]['__records'], [{'id': self.message_4.id}])

    def test_properties_tags_field_web_read_group(self):
        self.discussion_1.attributes_definition = [
            {
                'name': 'my_tags',
                'string': 'My Tags',
                'type': 'tags',
                'tags': [
                    ('be', 'BE', 1),
                    ('it', 'IT', 2),
                ],
                'default': ['be'],
            },
        ]
        self.env['test_orm.message'].create(
            {'discussion': self.discussion_1.id, 'author': self.user.id})

        self.env.flush_all()
        result = self.env['test_orm.message'].web_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.my_tags'],
            opening_info=[{'folded': True, 'value': '1'}],
            unfold_read_specification={'id': {}},
        )

        self.assertEqual(len(result['groups']), 2)
        self.assertEqual(result['groups'][0]['attributes.my_tags'], ('be', 'BE', 1))
        self.assertEqual(result['groups'][1]['attributes.my_tags'], False)

    @mute_logger('odoo.fields')
    def test_properties_field_read_progress_bar(self):
        """Test "_read_progress_bar" with a properties field."""
        Model = self.env['test_orm.message']

        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'myinteger',
            'type': 'integer',
            'value': 1337,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myinteger': 5}
        self.message_3.attributes = {'myinteger': 1337}

        result = Model.read_progress_bar(
            domain=[],
            group_by='attributes.myinteger',
            progress_bar={'field': 'priority', 'colors': [0]},
        )
        self.assertEqual(result, {'1337': {0: 2}, '5': {0: 1}, 'False': {0: 1}})

    def _properties_field_read_group_date_prepare(self, date_type='date'):
        # Format in database: 2023-03-29 09:30:16
        self.messages.discussion = self.discussion_1
        self.discussion_1.attributes_definition = [{
            'type': date_type,
            'name': 'mydate',
        }]
        hour = ' 13:05:34' if date_type == 'datetime' else ''
        # message 5 has a different year
        # message 6 has a False value
        # message 7 is in a different discussion
        self.message_5, self.message_6, self.message_7 = self.env['test_orm.message'].create([
                {'discussion': self.discussion_1.id, 'attributes': {'mydate': f'2077-05-02{hour}'}},
                {'discussion': self.discussion_1.id, 'attributes': {'mydate': False}},
                {'discussion': self.discussion_2.id},
        ])
        self.message_1.attributes = {'mydate': f'2023-01-02{hour}'}
        self.message_2.attributes = {'mydate': f'2023-02-03{hour}'}
        self.message_3.attributes = {'mydate': f'2023-01-02{hour}'}
        self.message_4.attributes = {'mydate': f'2023-02-05{hour}'}

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_date_day(self, date_type='date'):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env['test_orm.message']

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:day'],
            order='attributes.mydate:day DESC',
        )

        self.assertEqual(len(result), 5)
        # check values and count
        self.assertEqual(result[0]['__count'], 2)
        self.assertEqual(result[0]['attributes.mydate:day'], False)
        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mydate:day'][1], '02 May 2077')
        self.assertEqual(result[2]['__count'], 1)
        self.assertEqual(result[2]['attributes.mydate:day'][1], '05 Feb 2023')
        self.assertEqual(result[3]['__count'], 1)
        self.assertEqual(result[3]['attributes.mydate:day'][1], '03 Feb 2023')
        self.assertEqual(result[4]['__count'], 2)
        self.assertEqual(result[4]['attributes.mydate:day'][1], '02 Jan 2023')
        # check domain
        self.assertEqual(Model.search(result[0]['__extra_domain']), self.message_6 | self.message_7)
        self.assertEqual(Model.search(result[1]['__extra_domain']), self.message_5)
        self.assertEqual(Model.search(result[2]['__extra_domain']), self.message_4)
        self.assertEqual(Model.search(result[3]['__extra_domain']), self.message_2)
        self.assertEqual(Model.search(result[4]['__extra_domain']), self.message_1 | self.message_3)
        self._check_domains_count(result)

        # when the order is not specified, the ORM will generate one
        # based on "attributes.mydate ASC", make sure it works
        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:year'],
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['attributes.mydate:year'][1], '2023')
        self.assertEqual(result[1]['attributes.mydate:year'][1], '2077')
        self.assertEqual(result[2]['attributes.mydate:year'], False)

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_date_quarter(self, date_type='date'):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env['test_orm.message']

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:quarter'],
            order='attributes.mydate:quarter DESC',
        )

        self.assertEqual(len(result), 3)
        # check values and count
        self.assertEqual(result[0]['__count'], 2)
        self.assertEqual(result[0]['attributes.mydate:quarter'], False)
        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mydate:quarter'][1], 'Q2 2077')
        self.assertEqual(result[2]['__count'], 4)
        self.assertEqual(result[2]['attributes.mydate:quarter'][1], 'Q1 2023')
        # check domain
        self.assertEqual(Model.search(result[0]['__extra_domain']), self.message_6 | self.message_7)
        self.assertEqual(Model.search(result[1]['__extra_domain']), self.message_5)
        self.assertEqual(
            Model.search(result[2]['__extra_domain']),
            self.message_1 | self.message_2 | self.message_3 | self.message_4)
        self._check_domains_count(result)

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_date_month(self, date_type='date'):
        self._properties_field_read_group_date_prepare()
        Model = self.env['test_orm.message']

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:month'],
            order='attributes.mydate:month DESC',
        )

        self.assertEqual(len(result), 4)
        # check values and count
        self.assertEqual(result[0]['__count'], 2)
        self.assertEqual(result[0]['attributes.mydate:month'], False)
        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mydate:month'][1], 'May 2077')
        self.assertEqual(result[2]['__count'], 2)
        self.assertEqual(result[2]['attributes.mydate:month'][1], 'February 2023')
        self.assertEqual(result[3]['__count'], 2)
        self.assertEqual(result[3]['attributes.mydate:month'][1], 'January 2023')
        # check domain
        self.assertEqual(Model.search(result[0]['__extra_domain']), self.message_6 | self.message_7)
        self.assertEqual(Model.search(result[1]['__extra_domain']), self.message_5)
        self.assertEqual(Model.search(result[2]['__extra_domain']), self.message_2 | self.message_4)
        self.assertEqual(Model.search(result[3]['__extra_domain']), self.message_1 | self.message_3)
        self._check_domains_count(result)

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_date_week(self, date_type='date'):
        first_week_day = int(get_lang(self.env).week_start) - 1
        self.assertEqual(first_week_day, 6, "First day of the week must be Sunday")

        self._properties_field_read_group_date_prepare()
        Model = self.env['test_orm.message']

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:week'],
            order='attributes.mydate:week DESC',
        )

        self.assertEqual(len(result), 5)
        # check values and count
        self.assertEqual(result[0]['__count'], 2)
        self.assertEqual(result[0]['attributes.mydate:week'], False)
        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mydate:week'][1], 'W19 2077')
        self.assertEqual(result[2]['__count'], 1)
        self.assertEqual(result[2]['attributes.mydate:week'][1], 'W6 2023')
        self.assertEqual(result[3]['__count'], 1)
        self.assertEqual(result[3]['attributes.mydate:week'][1], 'W5 2023')
        self.assertEqual(result[4]['__count'], 2)
        # Babel issue mitigation
        # https://github.com/python-babel/babel/pull/621 -- introduced a new bug
        # https://github.com/python-babel/babel/pull/887 -- proposed a fix but finally closed
        # https://sources.debian.org/patches/python-babel/2.10.3-1/ -- Debian reverted 621
        # so this ugly fix is made to have the test working in patched and non patched versions of Babel
        babel_year = babel.dates.format_date(datetime.datetime(2023, 1, 1), "YYYY", "en_US")  # non patched: '2022' patched: '2023'
        if babel_year == '2022':  # Broken unpatched babel
            self.assertEqual(result[4]['attributes.mydate:week'][1], 'W1 2022')
        else:  # Patched babel
            self.assertEqual(result[4]['attributes.mydate:week'][1], 'W1 2023')
        # check domain
        self.assertEqual(Model.search(result[0]['__extra_domain']), self.message_6 | self.message_7)
        self.assertEqual(Model.search(result[1]['__extra_domain']), self.message_5)
        self.assertEqual(Model.search(result[2]['__extra_domain']), self.message_4)
        self.assertEqual(Model.search(result[3]['__extra_domain']), self.message_2)
        self.assertEqual(Model.search(result[4]['__extra_domain']), self.message_1 | self.message_3)
        self._check_domains_count(result)

        # test that the first day of the week in the domain care about the local
        # (based on the lang, the first day of the week might change)
        for line in result[1:]:
            self.assertEqual(line['__extra_domain'][1][1], ">=")
            self.assertEqual(line['__extra_domain'][2][1], "<")
            start = datetime.datetime.strptime(line['__extra_domain'][1][2], "%Y-%m-%d")
            end = datetime.datetime.strptime(line['__extra_domain'][2][2], "%Y-%m-%d")
            self.assertEqual(start.weekday(), first_week_day)
            self.assertEqual(end.weekday(), first_week_day)

        # now, first day of the week is "Wednesday"
        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'fr_FR')])
        self.assertEqual(len(lang), 1)
        lang.write({'active': True, 'week_start': '3'})
        result = Model.with_context(lang='fr_FR').formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:week'],
            order='attributes.mydate:week DESC',
        )
        for line in result[1:]:
            self.assertEqual(line['__extra_domain'][1][1], ">=")
            self.assertEqual(line['__extra_domain'][2][1], "<")
            start = datetime.datetime.strptime(line['__extra_domain'][1][2], "%Y-%m-%d")
            end = datetime.datetime.strptime(line['__extra_domain'][2][2], "%Y-%m-%d")
            self.assertEqual(start.weekday(), 2, "First day of the week must be Wednesday")
            self.assertEqual(end.weekday(), 2, "First day of the week must be Wednesday")

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_date_year(self, date_type='date'):
        self._properties_field_read_group_date_prepare()
        Model = self.env['test_orm.message']

        result = Model.formatted_read_group(
            domain=[],
            aggregates=['__count'],
            groupby=['attributes.mydate:year'],
            order='attributes.mydate:year DESC',
        )

        self.assertEqual(len(result), 3)
        # check values and count
        self.assertEqual(result[0]['__count'], 2)
        self.assertEqual(result[0]['attributes.mydate:year'], False)
        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mydate:year'][1], '2077')
        self.assertEqual(result[2]['__count'], 4)
        self.assertEqual(result[2]['attributes.mydate:year'][1], '2023')
        # check domain
        self.assertEqual(Model.search(result[0]['__extra_domain']), self.message_6 | self.message_7)
        self.assertEqual(Model.search(result[1]['__extra_domain']), self.message_5)
        self.assertEqual(
            Model.search(result[2]['__extra_domain']),
            self.message_1 | self.message_2 | self.message_3 | self.message_4)
        self._check_domains_count(result)

    def test_properties_field_read_group_datetime_day(self):
        self.test_properties_field_read_group_date_day('datetime')

    def test_properties_field_read_group_datetime_quarter(self):
        self.test_properties_field_read_group_date_quarter('datetime')

    def test_properties_field_read_group_datetime_month(self):
        self.test_properties_field_read_group_date_month('datetime')

    def test_properties_field_read_group_datetime_week(self):
        self.test_properties_field_read_group_date_week('datetime')

    def test_properties_field_read_group_datetime_year(self):
        self.test_properties_field_read_group_date_year('datetime')

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_injection(self):
        Model = self.env['test_orm.message']
        self.message_1.attributes = [{
            'name': 'myinteger',
            'type': 'integer',
            'value': 1337,
            'definition_changed': True,
        }]

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger'],
                order='attributes.myinteger OR 1=1 DESC',
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger OR 1=1'],
                order='attributes.myinteger DESC',
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=['__count'],
                groupby=['attributes.myinteger:wrongfunction'],
                order='attributes.myinteger DESC',
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=['attributes.myinteger:sum'],  # Aggregate is not supported
            )

    @mute_logger('odoo.fields', 'odoo.models.unlink')
    def test_properties_field_read_group_many2many(self):
        Model = self.env['test_orm.message']

        partners = self.env['test_orm.partner'].create([
            {'name': f'Partner {i}'}
            for i in range(10)
        ])

        self.discussion_1.attributes_definition = [{
            'name': 'mypartners',
            'string': 'Partners',
            'type': 'many2many',
            'comodel': 'test_orm.partner',
        }]

        self.messages.discussion = self.discussion_1

        self.message_1.attributes = {'mypartners': partners[:5].ids}
        self.message_2.attributes = {'mypartners': partners[3:8].ids}
        self.message_3.attributes = {'mypartners': partners[8:].ids}

        (partners[4] | partners[7] | partners[9]).unlink()

        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                aggregates=['__count'],
                groupby=['attributes.mypartners'],
            )

        self.assertEqual(len(result), 8)
        existing_partners = partners.exists()
        self.assertEqual(len(existing_partners), 7)
        for partner, line in zip(existing_partners, result):
            self.assertEqual(partner.id, line['attributes.mypartners'][0])
            self.assertEqual(partner.display_name, line['attributes.mypartners'][1])
            self.assertEqual(
                line['__extra_domain'],
                [('attributes.mypartners', 'in', partner.id)],
            )
            # only the fourth partner is in 2 messages
            self.assertEqual(line['__count'], 2 if partner == partners[3] else 1)

        # message 4 is in a different discussion, so it's value is False
        self.assertEqual(Model.search(result[-1]['__extra_domain']), self.message_4)
        self._check_many_falsy_group('mypartners', result)
        self._check_domains_count(result)

        # now message 1 and 2 will also be in the falsy group
        partners[:8].unlink()
        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                aggregates=['__count'],
                groupby=['attributes.mypartners'],
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(Model.search(result[-1]['__extra_domain']), self.message_1 | self.message_2 | self.message_4)
        self._check_many_falsy_group('mypartners', result)
        self._check_domains_count(result)

        # special case, no partner exists
        existing_partners.unlink()
        result = Model.formatted_read_group(
            domain=[('discussion', '!=', self.wrong_discussion_id)],
            aggregates=['__count'],
            groupby=['attributes.mypartners'],
        )
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['attributes.mypartners'])
        self.assertEqual(result[0]['__count'], 4)
        self._check_domains_count(result)

        # test an invalid model name (e.g. if we uninstalled the module of the model)
        for invalid_model_name in ("invalid_model_name", "test_orm.transient_model"):
            self.env.cr.execute(
                """
                UPDATE test_orm_discussion
                   SET attributes_definition
                       = jsonb_set(attributes_definition, '{0,comodel}', %s)
                 WHERE id = %s
                """,
                [json.dumps(invalid_model_name), self.discussion_1.id],
            )  # bypass the ORM to set an invalid model name
            definition = self._get_sql_definition(self.discussion_1)
            self.assertEqual(definition[0]['comodel'], invalid_model_name)
            error_message = f"You cannot use “Partners” because the linked “{invalid_model_name}” model doesn't exist or is invalid"
            with self.assertRaisesRegex(UserError, error_message):
                result = Model.formatted_read_group(
                    domain=[('discussion', '!=', self.wrong_discussion_id)],
                    aggregates=['__count'],
                    groupby=['attributes.mypartners'],
                )

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_many2one(self):
        Model = self.env['test_orm.message']

        # group by many2one property
        self.message_1.attributes = [{
            'name': 'mypartner',
            'string': 'My Partner',
            'type': 'many2one',
            'value': self.partner_2.id,
            'comodel': 'test_orm.partner',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mypartner': self.partner.id}
        self.message_4.attributes = {'mypartner': False}  # explicit False value

        # this partner id doesn't exist
        unexisting_record_id = self.env['test_orm.partner'].search(
            [], order="id DESC", limit=1).id + 1
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = '{"mypartner": %s}'
             WHERE id = %s
            """,
            [unexisting_record_id, self.message_3.id],
        )

        self.env.invalidate_all()
        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[],
                groupby=['attributes.mypartner'],
                aggregates=['__count'],
            )

        self.assertEqual(len(result), 3, 'Should ignore the partner that has been removed')

        self.assertEqual(result[0]['__count'], 1)
        self.assertEqual(result[0]['attributes.mypartner'][0], self.partner.id)
        self.assertEqual(result[0]['attributes.mypartner'][1], self.partner.display_name)
        self.assertEqual(result[0]['__extra_domain'], [('attributes.mypartner', '=', self.partner.id)])

        self.assertEqual(result[1]['__count'], 1)
        self.assertEqual(result[1]['attributes.mypartner'][0], self.partner_2.id)
        self.assertEqual(result[1]['attributes.mypartner'][1], self.partner_2.display_name)
        self.assertEqual(result[1]['__extra_domain'], [('attributes.mypartner', '=', self.partner_2.id)])

        # falsy domain, automatically generated, contains the false value
        # and the ids of the records that doesn't exist in the database
        self.assertEqual(result[2]['__count'], 2)
        self.assertEqual(result[2]['attributes.mypartner'], False)
        self.assertEqual(
            result[2]['__extra_domain'],
            [
                '|',
                ('attributes.mypartner', '=', False),
                ('attributes.mypartner', 'not in', [self.partner.id, self.partner_2.id]),
            ],
        )

        # when there's no "('property', '=', False)" domain, it should be created
        self.message_4.attributes = {'mypartner': self.partner.id}
        result = Model.formatted_read_group(
            domain=[],
            groupby=['attributes.mypartner'],
            aggregates=['__count'],
        )
        self.assertEqual(result[2]['__count'], 1)
        self.assertEqual(
            result[2]['__extra_domain'],
            [
                '|',
                ('attributes.mypartner', '=', False),
                ('attributes.mypartner', 'not in', [self.partner.id, self.partner_2.id]),
            ],
        )

        # test an invalid model name (e.g. if we uninstalled the module of the model)
        # should have only one group with the value "False", and all records
        for invalid_model_name in ("invalid_model_name", "test_orm.transient_model"):
            self.env.cr.execute(
                """
                UPDATE test_orm_discussion
                   SET attributes_definition
                       = jsonb_set(attributes_definition, '{0,comodel}', %s::jsonb)
                 WHERE id = %s
                """,
                [json.dumps(invalid_model_name), self.discussion_1.id],
            )  # bypass the ORM to set an invalid model name
            definition = self._get_sql_definition(self.discussion_1)
            self.assertEqual(definition[0]['comodel'], invalid_model_name)
            error_message = f"You cannot use “My Partner” because the linked “{invalid_model_name}” model doesn't exist or is invalid"
            with self.assertRaisesRegex(UserError, error_message):
                result = Model.formatted_read_group(
                    domain=[('discussion', '!=', self.wrong_discussion_id)],
                    aggregates=['__count'],
                    groupby=['attributes.mypartner'],
                )

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_selection(self):
        Model = self.env['test_orm.message']

        # group by selection property
        self.message_1.attributes = [{
            'name': 'myselection',
            'type': 'selection',
            'value': 'optionA',
            'selection': [['optionA', 'A'], ['optionB', 'B']],
            'definition_changed': True,
        }, {
            'name': 'mychar2',
            'type': 'char',
            'value': 'qsd',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myselection': False}

        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = '{"myselection": "invalid_option"}'
             WHERE id = %s
            """,
            [self.message_3.id],
        )

        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                groupby=['attributes.myselection'],
                aggregates=['__count'],
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['__count'], 1)
        self.assertEqual(
            result[0]['__extra_domain'],
            [('attributes.myselection', '=', 'optionA')],
        )
        self.assertEqual(result[0]['attributes.myselection'], 'optionA')

        # check that the option that is not valid is included in the "False" domain
        # the count should be updated as well
        self.assertEqual(result[1]['__count'], 3)
        self.assertEqual(
            result[1]['__extra_domain'],
            [
                '|',
                ('attributes.myselection', '=', False),
                ('attributes.myselection', 'not in', ['optionA', 'optionB']),
            ],
        )
        self.assertEqual(result[1]['attributes.myselection'], False)
        # double check that the returned domain filter the right record
        self.assertEqual(
            self.env['test_orm.message'].search(result[1]['__extra_domain']),
            self.message_2 | self.message_3 | self.message_4,
        )

        # special case, there's no option
        self.message_1.attributes = [{
            'name': 'myselection',
            'type': 'selection',
            'value': 'optionA',
            'selection': [],
            'definition_changed': True,
        }]
        result = Model.formatted_read_group(
            domain=[],
            groupby=['attributes.myselection'],
            aggregates=['__count'],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['__count'], 4)
        self._check_domains_count(result)

    @mute_logger('odoo.fields')
    def test_properties_field_read_group_tags(self):
        Model = self.env['test_orm.message']

        (self.message_1 | self.message_2 | self.message_3).discussion = self.discussion_1

        # group by tags property
        self.message_1.attributes = [{
            'name': 'mytags',
            'type': 'tags',
            'value': ['a', 'c', 'g'],
            'tags': [[x.lower(), x, i] for i, x in enumerate('ABCDEFG')],
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mytags': ['a', 'e', 'g']}
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = '{"mytags": ["a", "d", "invalid", "e"]}'
             WHERE id = %s
            """,
            [self.message_3.id],
        )
        self.env.invalidate_all()

        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                aggregates=['__count'],
                groupby=['attributes.mytags'],
            )

        self.assertNotIn('invalid', str(result))
        self.assertEqual(len(result), 6)

        all_tags = self.message_1.read(['attributes'])[0]['attributes'][0]['tags']
        all_tags = {tag[0]: tuple(tag) for tag in all_tags}

        for group, (tag, count) in zip(result, (('a', 3), ('c', 1), ('d', 1), ('e', 2), ('g', 2))):
            self.assertEqual(group['attributes.mytags'], all_tags[tag])
            self.assertEqual(group['__count'], count)
            self.assertEqual(
                group['__extra_domain'],
                [('attributes.mytags', 'in', tag)],
            )
            # check that the value when we read the record match the value of the group
            property_values = [
                next(pro['value'] for pro in values['attributes'])
                for values in Model.search(group['__extra_domain']).read(['attributes'])
            ]
            self.assertTrue(all(tag in property_value for property_value in property_values))

        self.assertEqual(Model.search(result[-1]['__extra_domain']), self.message_4)
        self._check_many_falsy_group('mytags', result)
        self._check_domains_count(result)

        # now message 3 has *only* invalid tags, so it should be in the falsy group
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = '{"mytags": ["invalid 1", "invalid 2", "invalid 3"]}'
             WHERE id = %s
            """,
            [self.message_3.id],
        )
        self.env.invalidate_all()

        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                aggregates=['__count'],
                groupby=['attributes.mytags'],
            )
        self.assertEqual(Model.search(result[-1]['__extra_domain']), self.message_3 | self.message_4)
        self._check_many_falsy_group('mytags', result)
        self._check_domains_count(result)

        # special case, there's no tag
        for tags in ([], False, None):
            self.message_1.attributes = [{
                'name': 'mytags',
                'type': 'tags',
                'value': tags,
                'tags': tags,
                'definition_changed': True,
            }]
            result = Model.formatted_read_group(
                domain=[('discussion', '!=', self.wrong_discussion_id)],
                aggregates=['__count'],
                groupby=['attributes.mytags'],
            )
            self.assertEqual(len(result), 1)
            self.assertFalse(result[0]['attributes.mytags'])
            self.assertEqual(result[0]['__count'], 4)
            self._check_domains_count(result)

    def _check_domains_count(self, result):
        """Check that the domains in the result match the __count key."""
        for line in result:
            records = self.env['test_orm.message'].search(line['__extra_domain'])
            count_key = next(key for key in line if "_count" in key)
            self.assertEqual(len(records), line[count_key])

    def _check_many_falsy_group(self, property_name, result):
        """Check the falsy group from the many2many and tags read group result.

        - if a record is in the falsy group, it can't be in a other group
          (that sentence is not true for non-falsy group, a record
          with a non-falsy value can be in many other groups)
        - read the value of all records and check if they belongs to the correct group
        """
        Model = self.env['test_orm.message']
        falsy_group = result[-1]
        self.assertFalse(falsy_group[f'attributes.{property_name}'])
        falsy_records = Model.search(falsy_group['__extra_domain'])
        nonfalsy_records = Model.search(Domain.OR(line['__extra_domain'] for line in result[:-1]))
        self.assertEqual(Model.search_count([]), len(falsy_records) + len(nonfalsy_records))
        for falsy_record in falsy_records:
            self.assertNotIn(falsy_record, nonfalsy_records)

        def _get_records_values(records):
            return [
                next(
                    (pro.get('value') for pro in properties['attributes']
                     if pro['name'] == property_name),
                )
                for properties in records.read(['attributes'])
            ]

        self.assertTrue(not any(_get_records_values(falsy_records)))
        self.assertTrue(all(_get_records_values(nonfalsy_records)))

    def subtest_properties_field_web_read_group_date_like(self, date_type='date'):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env['test_orm.message']

        hour_min = " 00:00:00" if date_type == "datetime" else ""

        # Initial web_read_group everything folded (list view)
        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["attributes.mydate:year"],
                aggregates=[],
            ),
            {
                "groups": [
                    {
                        "__extra_domain": ['&', ('attributes.mydate', '>=', f'2023-01-01{hour_min}'), ('attributes.mydate', '<', f'2024-01-01{hour_min}')],
                        "attributes.mydate:year": (f'2023-01-01{hour_min}', "2023"),
                        "__count": 4,
                    },
                    {
                        "__extra_domain": ['&', ('attributes.mydate', '>=', f'2077-01-01{hour_min}'), ('attributes.mydate', '<', f'2078-01-01{hour_min}')],
                        "attributes.mydate:year": (f'2077-01-01{hour_min}', "2077"),
                        "__count": 1,
                    },
                    {
                        "__extra_domain": [('attributes.mydate', '=', False)],
                        "attributes.mydate:year": False,
                        "__count": 2,
                    },
                ],
                "length": 3,
            },
        )
        # Second web_read_group year 2077 unfolded
        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["attributes.mydate:year"],
                aggregates=[],
                opening_info=[
                    {
                        "value": f'2077-01-01{hour_min}',
                        "folded": False,
                        "limit": 80,
                        "offset": 0,
                        "progressbar_domain": False,
                        "groups": [],
                    },
                    {"value": f"2023-01-01{hour_min}", "folded": True},
                    {"value": False, "folded": True},
                ],
                unfold_read_specification={'id': {}},
            ),
            {
                "groups": [
                    {
                        "__extra_domain": ['&', ('attributes.mydate', '>=', f'2023-01-01{hour_min}'), ('attributes.mydate', '<', f'2024-01-01{hour_min}')],
                        "attributes.mydate:year": (f'2023-01-01{hour_min}', "2023"),
                        "__count": 4,
                    },
                    {
                        "__extra_domain": ['&', ('attributes.mydate', '>=', f'2077-01-01{hour_min}'), ('attributes.mydate', '<', f'2078-01-01{hour_min}')],
                        "attributes.mydate:year": (f'2077-01-01{hour_min}', "2077"),
                        '__records': [{'id': self.message_5.id}],
                        "__count": 1,
                    },
                    {
                        "__extra_domain": [('attributes.mydate', '=', False)],
                        "attributes.mydate:year": False,
                        "__count": 2,
                    },
                ],
                "length": 3,
            },
        )

    def test_properties_field_read_group_date(self):
        self.subtest_properties_field_web_read_group_date_like('date')

    def test_properties_field_read_group_datetime(self):
        self.subtest_properties_field_web_read_group_date_like('datetime')
