# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import unittest
from unittest.mock import patch

from odoo import Command

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import Form, TransactionCase, users
from odoo.tools import mute_logger


class TestPropertiesMixin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env.user
        cls.partner = cls.env['test_new_api.partner'].create({'name': 'Test Partner Properties'})
        cls.partner_2 = cls.env['test_new_api.partner'].create({'name': 'Test Partner Properties 2'})

        cls.test_user = cls.env['res.users'].create({
            'name': 'Test',
            'login': 'test',
            'company_id': cls.env.company.id,
        })

        attributes_definition_1 = [{
            'name': 'discussion_color_code',
            'string': 'Color Code',
            'type': 'char',
            'default': 'blue',
        }, {
            'name': 'moderator_partner_id',
            'string': 'Partner',
            'type': 'many2one',
            'comodel': 'test_new_api.partner',
        }]

        attributes_definition_2 = [{
            'name': 'state',
            'type': 'selection',
            'string': 'Status',
            'selection': [('draft', 'Draft'), ('progress', 'In Progress'), ('done', 'Done')],
            'default': 'draft',
        }]

        cls.discussion_1 = cls.env['test_new_api.discussion'].create({
            'name': 'Test Discussion',
            'attributes_definition': attributes_definition_1,
            'participants': [Command.link(cls.user.id)],
        })
        cls.discussion_2 = cls.env['test_new_api.discussion'].create({
            'name': 'Test Discussion',
            'attributes_definition': attributes_definition_2,
            'participants': [Command.link(cls.user.id)],
        })

        cls.message_1 = cls.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': cls.discussion_1.id,
            'author': cls.user.id,
            'attributes': {
                'discussion_color_code': 'Test',
                'moderator_partner_id': cls.partner.id,
            },
        })

        cls.message_2 = cls.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': cls.discussion_1.id,
            'author': cls.user.id,
        })
        cls.message_3 = cls.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': cls.discussion_2.id,
            'author': cls.user.id,
        })

    def _get_sql_properties(self, message):
        self.env.flush_all()

        self.env.cr.execute(
            """
            SELECT attributes
              FROM test_new_api_message
             WHERE id = %s
            """, (message.id, ),
        )
        value = self.env.cr.fetchone()
        self.assertTrue(value)
        return value[0]

    def _get_sql_definition(self, discussion):
        self.env.flush_all()

        self.env.cr.execute(
            """
            SELECT attributes_definition
              FROM test_new_api_discussion
             WHERE id = %s
            """, (discussion.id, ),
        )
        value = self.env.cr.fetchone()
        self.assertTrue(value and value[0])
        return value[0]


class PropertiesCase(TestPropertiesMixin):

    def test_properties_field(self):
        self.assertTrue(isinstance(self.message_1.attributes, dict))
        # testing assigned value
        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': 'Test',
            'moderator_partner_id': self.partner.id,
        })

        self.assertEqual(self.message_2.attributes, {
            'discussion_color_code': 'blue',
            'moderator_partner_id': False,
        })
        # testing default value
        self.assertEqual(
            self.message_3.attributes, {'state': 'draft'},
            msg='Should have taken the default value')

        self.message_1.attributes = [
            {'name': 'discussion_color_code', 'value': 'red'},
            {'name': 'moderator_partner_id', 'value': self.partner_2.id},
        ]
        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': 'red',
            'moderator_partner_id': self.partner_2.id,
        })

        self.env.invalidate_all()

        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': 'red',
            'moderator_partner_id': self.partner_2.id,
        })

        # check that the value has been updated in the database
        database_values = self._get_sql_properties(self.message_1)
        self.assertTrue(isinstance(database_values, dict))
        self.assertEqual(
            database_values.get('discussion_color_code'), 'red',
            msg='Value must be updated in the database')

        # if we write False on the field, it should still
        # return the properties definition for the web client
        self.message_3.attributes = False
        self.env.invalidate_all()

        expected = self.discussion_2.attributes_definition
        for property_definition in expected:
            property_definition['value'] = False

        self.assertEqual(self.message_3.read(['attributes'])[0]['attributes'], expected)
        self.assertEqual(self.message_3.attributes, {
            definition['name']: definition['value']
            for definition in expected
        })

    def test_properties_field_parameters_cleanup(self):
        # check that the keys not valid for the given type are removed
        self.message_1.attributes = [{
            'name': 'discussion_color_code',
            'string': 'Color Code',
            'type': 'char',
            'default': 'blue',
            'value': 'Test',
            'definition_changed': True,
            'selection': [['a', 'A']],  # selection key is not valid for char type
        }]
        values = self._get_sql_definition(self.message_1.discussion)
        self.assertEqual(values, [{
            'name': 'discussion_color_code',
            'string': 'Color Code',
            'type': 'char',
            'default': 'blue',
        }])

    @mute_logger('odoo.fields')
    def test_properties_field_write_batch(self):
        """Test the behavior of the write called in batch.

        Simulate a write operation done by the web client.
        """
        # mix both properties
        properties_values = (self.message_1 | self.message_3).read(['attributes'])
        properties_values = properties_values[0]['attributes'] + properties_values[1]['attributes']

        for properties in properties_values:
            if properties['name'] == 'discussion_color_code':
                properties['value'] = 'orange'
            elif properties['name'] == 'state':
                properties['value'] = 'done'
            elif properties['name'] == 'moderator_partner_id':
                properties['value'] = self.partner_2.id
            properties['definition_changed'] = True

        (self.message_1 | self.message_3).write({'attributes': properties_values})

        sql_values_1 = self._get_sql_properties(self.message_1)
        sql_values_3 = self._get_sql_properties(self.message_3)

        # definition of both child has been changed
        self.assertEqual(sql_values_1, {'discussion_color_code': 'orange', 'moderator_partner_id': self.partner_2.id, 'state': 'done'})
        self.assertEqual(sql_values_3, {'discussion_color_code': 'orange', 'moderator_partner_id': self.partner_2.id, 'state': 'done'})

    @mute_logger('odoo.models.unlink', 'odoo.fields')
    def test_properties_field_read_batch(self):
        values = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]['type'], 'char')
        self.assertEqual(values[1]['type'], 'many2one')

        self.message_2.attributes = [{
            'name': 'discussion_color_code',
            'type': 'char',
            'string': 'Color Code',
            'default': 'blue',
            'value': 'Test',
        }, {
            'name': 'moderator_partner_id',
            'type': 'many2one',
            'string': 'Partner',
            'comodel': 'test_new_api.partner',
            'value': (self.partner_2.id, "Bob"),
        }]

        expected_queries = [
            # read the properties field value
            ''' SELECT "test_new_api_message"."id",
                       "test_new_api_message"."attributes"
                FROM "test_new_api_message"
                WHERE ("test_new_api_message"."id" IN %s)
            ''',
            ''' SELECT "test_new_api_message"."id",
                       "test_new_api_message"."discussion",
                       "test_new_api_message"."body",
                       "test_new_api_message"."author",
                       "test_new_api_message"."name",
                       "test_new_api_message"."important",
                       "test_new_api_message"."label"->>'en_US',
                       "test_new_api_message"."priority",
                       "test_new_api_message"."active",
                       "test_new_api_message"."create_uid",
                       "test_new_api_message"."create_date",
                       "test_new_api_message"."write_uid",
                       "test_new_api_message"."write_date"
                FROM "test_new_api_message"
                WHERE ("test_new_api_message"."id" IN %s)
            ''',
            # read the definition on the definition record
            ''' SELECT "test_new_api_discussion"."id",
                       "test_new_api_discussion"."name",
                       "test_new_api_discussion"."moderator",
                       "test_new_api_discussion"."message_concat",
                       "test_new_api_discussion"."history",
                       "test_new_api_discussion"."attributes_definition",
                       "test_new_api_discussion"."create_uid",
                       "test_new_api_discussion"."create_date",
                       "test_new_api_discussion"."write_uid",
                       "test_new_api_discussion"."write_date"
                FROM "test_new_api_discussion"
                WHERE ("test_new_api_discussion"."id" IN %s)
            ''',
            # check the many2one existence
            ''' SELECT "test_new_api_partner"."id"
                FROM "test_new_api_partner"
                WHERE "test_new_api_partner".id IN %s
            ''',
            ''' SELECT "test_new_api_partner"."id",
                       "test_new_api_partner"."name",
                       "test_new_api_partner"."create_uid",
                       "test_new_api_partner"."create_date",
                       "test_new_api_partner"."write_uid",
                       "test_new_api_partner"."write_date"
                FROM "test_new_api_partner"
                WHERE ("test_new_api_partner"."id" IN %s)
            ''',
        ]

        self.env.invalidate_all()
        with self.assertQueryCount(5), self.assertQueries(expected_queries):
            self.message_1.read(['attributes'])

        # read in batch a lot of records
        discussions = [self.discussion_1, self.discussion_2]
        partners = self.env['test_new_api.partner'].create([{'name': f'Test {i}'} for i in range(50)])
        messages = self.env['test_new_api.message'].create([{
            'name': f'Test Message {i}',
            'discussion': discussions[i % 2].id,
            'author': self.user.id,
            'attributes': [{
                'name': 'partner_id',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'value': partner.id,
                'definition_changed': True,
            }]
        } for i, partner in enumerate(partners)])

        self.env.invalidate_all()

        with self.assertQueryCount(5), self.assertQueries(expected_queries):
            values = messages.read(['attributes'])

        # remove some partners in the list
        partners[:20].unlink()
        self.env.invalidate_all()
        # 5 queries instead of 25 queries, thanks to the cache values that has been
        # cleaned (the properties field can trust the cached value, the deleted ids
        # are not in the cache even if they still exists in the database)
        with self.assertQueryCount(5):
            values = messages.read(['attributes'])

    @mute_logger('odoo.fields')
    def test_properties_field_delete(self):
        """Test to delete a property using the flag "definition_deleted"."""
        self.message_1.attributes = [{
            'name': 'discussion_color_code',
            'string': 'Test color code',
            'type': 'char',
            'default': 'blue',
            'value': 'purple',
        }, {
            'name': 'moderator_partner_id',
            'string': 'Partner',
            'type': 'many2one',
            'comodel': 'test_new_api.partner',
            'value': [self.partner.id, 'Bob'],
            'definition_deleted': True,
        }]

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition, [{
                'name': 'discussion_color_code',
                'type': 'char',
                'string': 'Test color code',
                'default': 'blue',
            }])

        self.assertEqual(len(self.message_1.attributes), 1)
        self.assertEqual(self.message_1.attributes, {'discussion_color_code': 'purple'})

    @mute_logger('odoo.fields')
    def test_properties_field_create_batch(self):
        # first create to cache the access rights
        self.env['test_new_api.message'].create({'name': 'test'})

        with self.assertQueryCount(2):
            messages = self.env['test_new_api.message'].create([{
                'name': 'Test Message',
                'discussion': False,
                'author': self.user.id,
            }, {
                'name': 'Test Message',
                'discussion': False,
                'author': self.user.id,
            }])
            self.env.invalidate_all()

        with self.assertQueryCount(8):
            messages = self.env['test_new_api.message'].create([{
                'name': 'Test Message',
                'discussion': self.discussion_1.id,
                'author': self.user.id,
                'attributes': [{
                    # no name, should be automatically generated
                    'string': 'Discussion Color code',
                    'type': 'char',
                    'default': 'blue',
                    'value': 'purple',
                    'definition_changed': True,
                }, {
                    # the name is already set and shouldn't be re-generated
                    'name': 'moderator_partner_id',
                    'string': 'Partner',
                    'type': 'many2one',
                    'comodel': 'test_new_api.partner',
                    'value': self.partner.id,
                    'definition_changed': True,
                }],
            }, {
                'name': 'Test Message',
                'discussion': self.discussion_2.id,
                'author': self.user.id,
                'attributes': [{
                    'type': 'selection',
                    'string': 'Status',
                    'selection': [
                        ('draft', 'Draft'),
                        ('progress', 'In Progress'),
                        ('done', 'Done'),
                    ],
                    'default': 'draft',
                    'definition_changed': True,
                }],
            }])
            self.env.invalidate_all()

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(len(sql_definition), 2)

        # check the generated name
        property_color_name = sql_definition[0]['name']
        self.assertTrue(property_color_name, msg="Property name must have been generated")

        self.assertEqual(sql_definition, [
            {
                'name': property_color_name,
                'default': 'blue',
                'string': 'Discussion Color code',
                'type': 'char',
            }, {
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'string': 'Partner',
            }
        ])

        self.assertEqual(
            self.discussion_1.attributes_definition[0]['string'], 'Discussion Color code',
            msg='Should have updated the definition record')

        self.assertEqual(len(messages), 2)

        sql_properties_1 = self._get_sql_properties(messages[0])
        self.assertEqual(
            sql_properties_1,
            {'moderator_partner_id': self.partner.id,
             property_color_name: 'purple'})
        sql_properties_2 = self._get_sql_properties(messages[1])
        status_name = self.discussion_2.attributes_definition[0]['name']
        self.assertEqual(
            sql_properties_2,
            {status_name: 'draft'})

        properties_values_1 = messages[0].attributes
        properties_values_2 = messages[1].attributes

        self.assertEqual(len(properties_values_1), 2, msg='Discussion 1 has 2 properties')
        self.assertEqual(len(properties_values_2), 1, msg='Discussion 2 has 1 property')

        self.assertEqual(properties_values_1, {
            'moderator_partner_id': self.partner.id,
            property_color_name: 'purple',
        })
        self.assertEqual(properties_values_2, {status_name: 'draft'},
                         msg='Should have taken the default value')

    def test_properties_field_default(self):
        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': self.discussion_2.id,
            'author': self.user.id,
        })
        self.assertEqual(
            message.attributes,
            {'state': 'draft'},
            msg='Should have taken the default value')

        message.attributes = [{'name': 'state', 'value': None}]
        self.assertEqual(
            message.attributes,
            {'state': False},
            msg='Writing None should not reset to the default value')

        # test the case where the definition record come from a default as well
        def default_discussion(_record):
            return self.discussion_2.id

        with patch.object(self.env['test_new_api.message']._fields['discussion'], 'default', default_discussion):
            message = self.env['test_new_api.message'].create({
                'name': 'Test Message',
                'author': self.user.id,
            })
            self.assertEqual(message.discussion, self.discussion_2)
            self.assertEqual(
                message.attributes,
                {'state': 'draft'},
                msg='Should have taken the default value')

            # the definition record come from a default value
            self.discussion_2.attributes_definition = [{
                'name': 'test',
                'type': 'char',
                'default': 'default char',
            }]
            message = self.env['test_new_api.message'] \
                .with_context(default_discussion=self.discussion_2) \
                .create({'name': 'Test Message', 'author': self.user.id})
            self.assertEqual(message.discussion, self.discussion_2)
            self.assertEqual(message.attributes, {'test': 'default char'})

        # test a default many2one
        self.discussion_1.attributes_definition = [
            {
                'name': 'my_many2one',
                'string': 'Partner',
                'comodel': 'test_new_api.partner',
                'type': 'many2one',
                # send the value like the web client does
                'default': [self.partner.id, 'Bob'],
            },
        ]
        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(sql_definition[0]['default'], self.partner.id)

        read_values = self.discussion_1.read(['attributes_definition'])[0]['attributes_definition']
        self.assertEqual(
            read_values[0]['default'],
            (self.partner.id, self.partner.display_name),
            msg='When reading many2one default, it should return the display name',
        )

        # read the default many2one and deactivate the display_name
        read_values = self.discussion_1.read(['attributes_definition'], load=None)[0]['attributes_definition']
        self.assertEqual(
            read_values[0]['default'],
            self.partner.id,
            msg='If the display_name is deactivate, it should not return the display name',
        )

        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'author': self.user.id,
            'discussion': self.discussion_1.id,
        })

        properties = message.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], (self.partner.id, self.partner.display_name))

        self.assertEqual(message.attributes, {'my_many2one': self.partner.id})

        # give a default value and a value for a many2one
        # the default value must be ignored
        property_definition = self.discussion_1.read(['attributes_definition'])[0]['attributes_definition']
        property_definition[0]['value'] = (self.partner_2.id, 'Alice')
        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'author': self.user.id,
            'discussion': self.discussion_1.id,
            'attributes': property_definition,
        })
        self.assertEqual(
            message.attributes,
            {'my_many2one': self.partner_2.id},
            msg='Should not take the default value',
        )

        # default value but no parent are set
        record = self.env['test_new_api.message'].create({
            'attributes': {'my_many2one': self.partner_2.id},
        })
        self.assertFalse(self._get_sql_properties(record))

        # default value but the parent has no definition
        self.discussion_1.attributes_definition = []
        record = self.env['test_new_api.message'].create({
            'discussion': self.discussion_1.id,
            'attributes': {'my_many2one': self.partner_2.id},
        })
        self.assertFalse(self._get_sql_properties(record))

        # default value but the parent has no definition and we create a new property
        self.discussion_1.attributes_definition = []
        record = self.env['test_new_api.message'].create({
            'discussion': self.discussion_1.id,
            'attributes': [{
                'name': 'test',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'default': self.partner_2.id,
                'definition_changed': True,
            }],
        })
        self.assertEqual(self._get_sql_properties(record), {'test': self.partner_2.id})

        # default value, a parent is set and change the definition
        record = self.env['test_new_api.message'].create({
            'discussion': self.discussion_1.id,
            'attributes': [{
                'name': 'test',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'default': self.partner_2.id,
            }, {
                'name': 'my_char',
                'type': 'char',
                'default': 'my char',
                'definition_changed': True,
            }],
        })
        self.assertEqual(self._get_sql_properties(record), {'my_char': 'my char', 'test': self.partner_2.id})

    def test_properties_field_read(self):
        """Test the behavior of the read method.

        In comparison with a simple "record.properties", the read method should not
        record a recordset for the many2one, but a tuple with the record id and
        the record display_name.
        """
        properties_values = (self.message_1 | self.message_3).read(['attributes'])

        self.assertEqual(len(properties_values), 2)

        properties_message_1 = properties_values[0]['attributes']
        properties_message_3 = properties_values[1]['attributes']

        self.assertTrue(isinstance(properties_message_1, list))
        self.assertTrue(isinstance(properties_message_3, list))

        self.assertEqual(len(properties_message_1), 2, msg="Message 1 has 2 properties")
        self.assertEqual(len(properties_message_3), 1, msg="Message 3 has 1 property")

        self.assertEqual(
            properties_message_1[0]['name'], 'discussion_color_code',
            msg='First message 1 property should be "discussion_color_code"')
        self.assertEqual(
            properties_message_1[1]['name'], 'moderator_partner_id',
            msg='Second message 1 property should be "moderator_partner_id"')
        self.assertEqual(
            properties_message_3[0]['name'], 'state',
            msg='First message 3 property should be "state"')

        many2one_property = properties_message_1[1]
        self.assertEqual(
            many2one_property['string'], 'Partner',
            msg='Definition must be present when reading child')
        self.assertEqual(
            many2one_property['type'], 'many2one',
            msg='Definition must be present when reading child')
        self.assertEqual(
            many2one_property['comodel'], 'test_new_api.partner',
            msg='Definition must be present when reading child')
        self.assertEqual(many2one_property['value'], (self.partner.id, self.partner.display_name))

        # disable the display_name
        properties_values = (self.message_1 | self.message_3).read(['attributes'], load=None)
        many2one_property = properties_values[0]['attributes'][1]

        self.assertEqual(
            many2one_property['value'], self.partner.id,
            msg='If display_name is disable, should only return the record id')

    def test_properties_field_many2one_basic(self):
        """Test the basic (read, write...) of the many2one property."""
        self.message_2.attributes = [
            {
                "name": "discussion_color_code",
                "type": "char",
                "string": "Color Code",
                "default": "blue",
                "value": False,
            }, {
                "name": "moderator_partner_id",
                "type": "many2one",
                "string": "Partner",
                "comodel": "test_new_api.partner",
                "value": self.partner_2.id,
            },
        ]

        self.assertFalse(self.message_2.attributes['discussion_color_code'])
        self.assertEqual(self.message_2.attributes['moderator_partner_id'], self.partner_2.id)
        sql_values = self._get_sql_properties(self.message_2)
        self.assertEqual(
            sql_values,
            {'moderator_partner_id': self.partner_2.id,
             'discussion_color_code': False})

        # read the many2one
        properties = self.message_2.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[1]['value'], (self.partner_2.id, self.partner_2.display_name))
        self.assertEqual(properties[1]['comodel'], 'test_new_api.partner')

    @mute_logger('odoo.models.unlink', 'odoo.fields')
    def test_properties_field_many2one_unlink(self):
        """Test the case where we unlink the many2one record."""
        self.message_2.attributes = [{
            'name': 'moderator_partner_id',
            'value': self.partner.id,
        }]

        # remove the partner on message 2
        self.partner.unlink()
        with self.assertQueryCount(4):
            # 1 query to read the field
            # 1 query to read the definition
            # 2 queries to check if the many2one still exists / display_name
            self.assertFalse(self.message_2.read(['attributes'])[0]['attributes'][0]['value'])

        # remove the partner, and use the read method
        self.message_2.attributes = [{
            'name': 'moderator_partner_id',
            'value': self.partner_2.id,
        }]
        self.partner_2.unlink()

        with self.assertQueryCount(4):
            value = self.message_2.read(['attributes'])
            value = value[0]['attributes']
            self.assertFalse(value[1]['value'])
            self.assertEqual(value[1]['comodel'], 'test_new_api.partner')

        # many2one properties in a default value
        partner = self.env['res.partner'].create({'name': 'test unlink'})
        self.message_2.attributes = [{
            'name': 'moderator_partner_id',
            'type': 'many2one',
            'comodel': 'res.partner',
            'default': [partner.id, 'Bob'],
            'definition_changed': True,
        }]
        self.assertEqual(
            self.message_2.read(['attributes'])[0]['attributes'],
            [{
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'comodel': 'res.partner',
                'default': (partner.id, partner.display_name),
                'value': False,
            }],
        )
        partner.unlink()
        self.assertEqual(
            self.message_2.read(['attributes'])[0]['attributes'],
            [{
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'comodel': 'res.partner',
                'default': False,
                'value': False,
            }],
        )

    def test_properties_field_many2one_model_removed(self):
        """Test the case where we uninstall a module, and the model does not exist anymore."""
        # simulate a module uninstall, the model is not available now
        # when reading the model / many2one, it should return False
        self.message_1.attributes = [{
            'name': 'message',
            'value': self.message_3.id,
        }]

        self.env.flush_all()
        self.env.cr.execute(
            """
            UPDATE test_new_api_discussion
               SET attributes_definition = '[{"name": "message", "comodel": "wrong_model", "type": "many2one"}]'
             WHERE id = %s
            """, (self.discussion_1.id, ),
        )
        self.env.invalidate_all()

        values = self.discussion_1.read(['attributes_definition'])[0]
        self.assertFalse(values['attributes_definition'][0]['comodel'])

        attributes_definition = self.discussion_1.attributes_definition
        self.assertEqual(
            attributes_definition,
            [{'name': 'message', 'comodel': False, 'type': 'many2one'}],
            msg='The model does not exist anymore, it should return false',
        )

        # read the many2one on the child, should return False as well
        self.assertFalse(self.message_1.attributes.get('message'))

        values = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(values[0]['type'], 'many2one', msg='Property type should be preserved')
        self.assertFalse(values[0]['value'])
        self.assertFalse(values[0]['comodel'])

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [{'name': 'message', 'comodel': 'wrong_model', 'type': 'many2one'}],
            msg='Do not clean the definition until we write on the field'
        )

        # write on the properties definition must clean the wrong model name
        self.discussion_1.attributes_definition = self.discussion_1.attributes_definition

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [{'name': 'message', 'comodel': False, 'type': 'many2one'}],
            msg='Should have cleaned the model key',
        )

    def test_properties_field_domain(self):
        self.discussion_1.attributes_definition = [{
            'name': 'message',
            'comodel': 'test_new_api.message',
            'type': 'many2one',
            'domain': "[('name', 'ilike', 'message')]",
        }]

        domain = self.message_1.read(['attributes'])[0]['attributes'][0]['domain']
        self.assertEqual(domain, "[('name', 'ilike', 'message')]")

        # set a wrong domain, it can happen if we uninstall a module
        # and if a field defined in this module was used in the domain
        self.env.flush_all()
        new_properties = json.dumps([{
            'name': 'message',
            'comodel': 'test_new_api.message',
            'type': 'many2one',
            'domain': "[('wrong_field', 'ilike', 'test')]",
        }])
        self.env.cr.execute(
            """
            UPDATE test_new_api_discussion
               SET attributes_definition = %s
             WHERE id = %s
            """, (new_properties, self.discussion_1.id, ),
        )
        self.env.flush_all()
        self.env.invalidate_all()

        definition = self.discussion_1.read(['attributes_definition'])[0]['attributes_definition']
        self.assertNotIn('domain', definition)

        properties = self.message_1.read(['attributes'])[0]['attributes']
        self.assertNotIn('domain', properties)

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertIn(
            'domain',
            sql_definition[0],
            msg='The domain should remain in database until we write on the properties definition',
        )

    def test_properties_field_integer_float_boolean(self):
        self.discussion_1.attributes_definition = [
            {
                'name': 'int_value',
                'string': 'Int Value',
                'type': 'integer',
            }, {
                'name': 'float_value',
                'string': 'Float Value',
                'type': 'float',
            }, {
                'name': 'boolean_value',
                'string': 'Boolean Value',
                'type': 'boolean',
            },
        ]

        self.message_1.attributes = [{
            'name': 'int_value',
            'value': 55555555555,
        }, {
            'name': 'float_value',
            'value': 1.337,
        }, {
            'name': 'boolean_value',
            'value': 77777,  # should be converted into True
        }]

        self.env.invalidate_all()

        self.assertEqual(self.message_1.attributes, {
            'int_value': 55555555555,
            'float_value': 1.337,
            'boolean_value': True,
        })

        self.message_1.attributes = [{'name': 'boolean_value', 'value': 0}]
        self.assertEqual(
            self.message_1.attributes['boolean_value'], False,
            msg='Boolean value must have been converted to False')

        # When the user sets the value 0 for the property fields of type integer
        # and float, the system should store the value 0 and shouldn't transform
        # 0 to False (-> unset value).

        self.message_1.attributes = {'int_value': 0, 'float_value': 0}
        self.assertEqual(self.message_1.attributes, {
            'int_value': 0,
            'float_value': 0,
            'boolean_value': False,
        })
        self.assertTrue(isinstance(self.message_1.attributes['int_value'], int))
        self.assertTrue(isinstance(self.message_1.attributes['float_value'], int))
        self.assertTrue(isinstance(self.message_1.attributes['boolean_value'], bool))
        self.assertEqual(self._get_sql_properties(self.message_1), {'int_value': 0, 'float_value': 0, 'boolean_value': False})

    def test_properties_field_integer_float_falsy_value_edge_cases(self):
        self.discussion_1.attributes_definition = [
            {
                'name': 'int_value',
                'string': 'Int Value',
                'type': 'integer',
                'default': 42
            }, {
                'name': 'float_value',
                'string': 'Float Value',
                'type': 'float',
                'default': 0.42
            }
        ]
        message_1 = self.env['test_new_api.message'].create({
            'discussion': self.discussion_1.id,
            'author': self.user.id,
            'attributes': {'int_value': 0, 'float_value': 0}
        })

        # When the user sets the value 0 for the property fields of type integer
        # and float, the system shouldn't consider 0 as a falsy value and fallback
        # to the default value.

        self.assertEqual(message_1.attributes, {
            'int_value': 0,
            'float_value': 0,
        })
        self.assertTrue(isinstance(message_1.attributes['int_value'], int))
        self.assertTrue(isinstance(message_1.attributes['float_value'], int))
        self.assertEqual(self._get_sql_properties(message_1), {'int_value': 0, 'float_value': 0})

    def test_properties_field_selection(self):
        self.message_3.attributes = [{'name': 'state', 'value': 'done'}]
        self.env.invalidate_all()
        self.assertEqual(self.message_3.attributes, {'state': 'done'})

        # the option might have been removed on the definition, write False
        self.message_3.attributes = [{'name': 'state', 'value': 'unknown_selection'}]
        self.env.invalidate_all()
        self.assertEqual(self.message_3.attributes, {'state': False})

        with self.assertRaises(ValueError):
            # check that 2 options can not have the same id
            self.discussion_1.attributes_definition = [
                {
                    'name': 'option',
                    'type': 'selection',
                    'selection': [['a', 'A'], ['b', 'B'], ['a', 'C']],
                }
            ]

        self.message_3.attributes = [{
            'type': 'selection',
            'name': 'new_selection',
            'string': 'My Selection',
            'definition_changed': True,
        }]
        values = self.message_3.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values.get('name'), 'new_selection')
        self.assertEqual(values.get('selection'), [], 'Selection key should be at least an empty array (never False)')

    def test_properties_field_tags(self):
        """Test the behavior of the tag property.

        The tags properties is basically the same as the selection property,
        but you can select multiple values. It should work like the selection
        (if we remove a value on the definition record, it should remove the value on each
        child the next time we read, etc).

        Each tags has a color index defined on the definition record.
        """
        self.discussion_1.attributes_definition = [
            {
                'name': 'my_tags',
                'string': 'My Tags',
                'type': 'tags',
                'tags': [
                    ('be', 'BE', 1),
                    ('fr', 'FR', 2),
                    ('de', 'DE', 3),
                    ('it', 'IT', 1),
                ],
                'default': ['be', 'de'],
            },
        ]
        message = self.env['test_new_api.message'].create(
            {'discussion': self.discussion_1.id, 'author': self.user.id})

        self.assertEqual(message.attributes, {'my_tags': ['be', 'de']})
        self.assertEqual(self._get_sql_properties(message), {'my_tags': ['be', 'de']})

        self.env.invalidate_all()

        # remove the DE tags on the definition
        self.discussion_1.attributes_definition = [
            {
                'name': 'my_tags',
                'string': 'My Tags',
                'type': 'tags',
                'tags': [
                    ('be', 'BE', 1),
                    ('fr', 'FR', 2),
                    ('it', 'IT', 1),
                ],
                'default': ['be', 'de'],
            },
        ]

        # the value must remain in the database until the next write on the child
        self.assertEqual(self._get_sql_properties(message), {'my_tags': ['be', 'de']})
        attributes = message.read(['attributes'])[0]['attributes']
        self.assertEqual(
            attributes[0]['value'],
            ['be'],
            msg='The tag has been removed on the definition, should be removed when reading the child')
        self.assertEqual(
            message.attributes,
            {'my_tags': ['be', 'de']})

        # next write on the child must update the value
        message.attributes = message.read(['attributes'])[0]['attributes']

        self.assertEqual(self._get_sql_properties(message), {'my_tags': ['be']})

        with self.assertRaises(ValueError):
            # it should detect that the tag is duplicated
            self.discussion_1.attributes_definition = [
                {
                    'name': 'my_tags',
                    'type': 'tags',
                    'tags': [
                        ('be', 'BE', 1),
                        ('be', 'FR', 2),
                    ],
                },
            ]

        self.message_3.attributes = [{
            'type': 'tags',
            'name': 'new_tags',
            'string': 'My tags',
            'definition_changed': True,
        }]
        values = self.message_3.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values.get('name'), 'new_tags')
        self.assertEqual(values.get('tags'), [], 'Tags key should be at least an empty array (never False)')

    @mute_logger('odoo.models.unlink', 'odoo.fields')
    def test_properties_field_many2many_basic(self):
        """Test the basic operation on a many2many properties (read, write...).

        Check also that if we remove some record,
        those are filtered when we read the child.
        """
        partners = self.env['test_new_api.partner'].create([
            {'name': f'Partner {i}'}
            for i in range(20)
        ])

        self.discussion_1.attributes_definition = [{
            'name': 'moderator_partner_ids',
            'string': 'Partners',
            'type': 'many2many',
            'comodel': 'test_new_api.partner',
        }]

        with self.assertQueryCount(4):
            self.message_1.attributes = [
                {
                    "name": "moderator_partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_new_api.partner",
                    "value": list(zip(partners[:10]._ids, partners[:10].mapped('display_name'))),
                }
            ]
            attributes = self.message_1.read(['attributes'], load=None)[0]['attributes']
            self.assertEqual(attributes[0]['value'], partners[:10].ids)

        partners[:5].unlink()
        with self.assertQueryCount(4):
            attributes = self.message_1.read(['attributes'], load=None)[0]['attributes']
            self.assertEqual(attributes[0]['value'], partners[5:10].ids)

        partners[5].unlink()
        with self.assertQueryCount(5):
            properties = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], list(zip(partners[6:10]._ids, partners[6:10].mapped('display_name'))))

        # need to wait next write to clean data in database
        # a single read won't clean the removed many2many
        attributes = self.message_1.read(['attributes'])[0]['attributes']
        self.message_1.invalidate_recordset()
        self.message_1.attributes = attributes

        sql_values = self._get_sql_properties(self.message_1)
        self.assertEqual(sql_values, {'moderator_partner_ids': partners[6:10].ids})

        # read and disable display_name
        properties = self.message_1.read(['attributes'], load=None)[0]['attributes']
        self.assertEqual(
            properties[0]['value'],
            partners[6:10].ids,
            msg='Should not return the partners name',
        )

        # Check that duplicated ids are removed
        self.env.flush_all()
        moderator_partner_ids = partners[6:10].ids
        moderator_partner_ids += moderator_partner_ids[2:]
        new_value = json.dumps({"moderator_partner_ids": moderator_partner_ids})
        self.env.cr.execute(
            """
            UPDATE test_new_api_message
               SET attributes = %s
             WHERE id = %s
            """, (new_value, self.message_1.id, ),
        )
        self.env.invalidate_all()

        properties = self.message_1.read(['attributes'], load=None)[0]['attributes']
        self.assertEqual(
            properties[0]['value'],
            partners[6:10].ids,
            msg='Should removed duplicated ids',
        )

        # write a list with many2many values
        self.message_1.attributes = [{
            'name': 'partner_ids',
            'string': 'Partners',
            'type': 'many2many',
            'comodel': 'test_new_api.partner',
            'default': [(partners[8].id, 'Alice')],
            'value': [(partners[9].id, 'Bob')],
            'definition_changed': True,
        }]
        sql_properties = self._get_sql_properties(self.message_1)
        self.assertEqual(sql_properties, {'partner_ids': [partners[9].id]})
        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(sql_definition, [{
            'name': 'partner_ids',
            'string': 'Partners',
            'type': 'many2many',
            'comodel': 'test_new_api.partner',
            'default': [partners[8].id],
        }])

        properties = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(
            properties,
            [{
                'name': 'partner_ids',
                'string': 'Partners',
                'type': 'many2many',
                'comodel': 'test_new_api.partner',
                'default': [(partners[8].id, partners[8].display_name)],
                'value': [(partners[9].id, partners[9].display_name)],
            }])

    @users('test')
    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.fields')
    def test_properties_field_many2many_filtering(self):
        # a user read a properties with a many2many and he doesn't have access to all records
        tags = self.env['test_new_api.multi.tag'].create(
            [{'name': f'Test Tag {i}'} for i in range(10)])

        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': self.discussion_1.id,
            'author': self.user.id,
            'attributes': [{
                'name': 'my_tags',
                'type': 'many2many',
                'comodel': 'test_new_api.multi.tag',
                'value': tags.ids,
                'definition_changed': True,
            }],
        })

        self.env['ir.rule'].sudo().create({
            'name': 'test_rule_tags',
            'model_id': self.env['ir.model']._get('test_new_api.multi.tag').id,
            'domain_force': [('name', 'not in', tags[5:].mapped('name'))],
            'perm_read': True,
            'perm_create': True,
            'perm_write': True,
        })

        self.env.invalidate_all()

        values = message.read(['attributes'])[0]['attributes'][0]['value']
        self.assertEqual(values, [(tag.id, None if i >= 5 else tag.name) for i, tag in enumerate(tags.sudo())])

    def test_properties_field_performance(self):
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # read to put the partner name in cache
            self.message_1.read(['attributes'])

        with self.assertQueryCount(0, msg='Must read value from cache'):
            self.message_1.attributes

        expected = ['UPDATE "test_new_api_message" SET "attributes" = %s, "write_date" = %s, "write_uid" = %s WHERE id IN %s']
        with self.assertQueryCount(1), self.assertQueries(expected):
            self.message_1.attributes = [
                {
                    "name": "discussion_color_code",
                    "type": "char",
                    "string": "Color Code",
                    "default": "blue",
                    "value": "red"
                },
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "string": "Partner",
                    "comodel": "test_new_api.partner",
                    "value": None
                },
            ]
            self.message_1.flush_recordset()

        last_message_id = self.env['test_new_api.message'].search([], order="id DESC", limit=1).id
        # based on batch optimization, _read_format should not crash on non existing records
        values = self.env['test_new_api.message'].browse((self.message_1.id, last_message_id + 1))._read_format(['attributes'])
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['id'], self.message_1.id)

    def test_properties_field_change_definition(self):
        """Test the behavior of the field when changing the definition."""

        attributes_definition = self.discussion_1.attributes_definition
        self.message_1.attributes = [
            {
                "name": "discussion_color_code",
                "value": None,
            },
            {
                "name": "moderator_partner_id",
                "value": None,
            }
        ]
        self.env.invalidate_all()
        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': False,
            'moderator_partner_id': False,
        })

        # add a property on the definition record
        attributes_definition += [{'name': 'state', 'string': 'State', 'type': 'char'}]
        self.discussion_1.attributes_definition = attributes_definition
        self.message_1.attributes = [{'name': 'state', 'value': 'ready'}]

        self.env.invalidate_all()

        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': False,
            'moderator_partner_id': False,
            'state': 'ready',
        })

        # remove a property from the definition
        # the properties on the child should remain, until we write on it
        # when reading, the removed property must be filtered
        self.discussion_1.attributes_definition = attributes_definition[:-1]  # remove the state field

        self.assertEqual(self.message_1.attributes, {
            'discussion_color_code': False,
            'moderator_partner_id': False,
            'state': 'ready',
        })

        value = self._get_sql_properties(self.message_1)
        self.assertEqual(value.get('state'), 'ready', msg='The field should be in database')

        self.message_1.attributes = [{'name': 'name', 'value': 'Test name'}]
        value = self._get_sql_properties(self.message_1)
        self.assertFalse(
            value.get('state'),
            msg='After updating an other property, the value must be cleaned')

        # check that we can only set a allowed list of properties type
        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [{'name': 'state', 'type': 'wrong_type'}]

        # check the property ID unicity
        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {'name': 'state', 'type': 'char'},
                {'name': 'state', 'type': 'datetime'},
            ]

    @mute_logger('odoo.fields')
    def test_properties_field_onchange(self):
        """If we change the definition record, the onchange of the properties field must be triggered."""
        message_form = Form(self.env['test_new_api.message'])

        with self.assertQueryCount(10):
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
                    'comodel': 'test_new_api.partner',
                    'value': False,
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

        self.assertEqual(
            message.attributes,
            {'state': 'draft'},
            msg='Should take the default value',
        )

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
                    'comodel': 'test_new_api.partner',
                }],
            )
        self.assertEqual(
            message.attributes,
            {'discussion_color_code': 'blue', 'moderator_partner_id': False},
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
        onchange_values = message.onchange(
            values={
                'discussion': self.discussion_1.id,
                'attributes': [{
                    'name': 'test',
                    'type': 'char',
                    'default': 'Default',
                    'value': 'Test',
                }],
            },
            field_name=['discussion'],
            field_onchange={'discussion': '1', 'attributes': '1'},
        )
        self.assertTrue(
            'attributes' in onchange_values['value'],
            msg='Should have detected the definition record change')
        self.assertEqual(
            onchange_values['value']['attributes'], [],
            msg='Should have reset the properties definition')

        # change the message discussion to add new properties
        # discussion 2 -> discussion 1
        message.discussion = self.discussion_1
        onchange_values = message.onchange(
            values={
                'discussion': self.discussion_2.id,
                'attributes': [],
            },
            field_name=['discussion'],
            field_onchange={'discussion': '1', 'attributes': '1'},
        )
        self.assertTrue(
            'attributes' in onchange_values['value'],
            msg='Should have detected the definition record change')
        self.assertEqual(
            onchange_values['value']['attributes'],
            [{'name': 'test', 'type': 'char', 'default': 'Default', 'value': 'Default'}],
            msg='Should have reset the properties definition to the discussion 1 definition')

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

    @mute_logger('odoo.fields')
    def test_properties_field_onchange2(self):
        """If we change the definition record, the onchange of the properties field must be triggered."""
        message_form = Form(self.env['test_new_api.message'])

        with self.assertQueryCount(10):
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
                    'comodel': 'test_new_api.partner',
                    'value': False,
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
                    'comodel': 'test_new_api.partner',
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
                'comodel': 'test_new_api.partner',
                'value': False,
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
        result = message.onchange2(values, ['discussion'], fields_spec)
        self.assertIn('attributes', result['value'], 'Should have detected the definition record change')
        self.assertEqual(result['value']['attributes'], [], 'Should have reset the properties definition')

        # change the message discussion to add new properties
        # discussion 2 -> discussion 1
        message.discussion = self.discussion_1
        values = {
            'discussion': self.discussion_2.id,
            'attributes': [],
        }
        result = message.onchange2(values, ['discussion'], fields_spec)
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

    @mute_logger('odoo.fields')
    def test_properties_field_definition_update(self):
        """Test the definition update from the child."""
        self.discussion_1.attributes_definition = []

        self.message_1.attributes = [
            {
                'name': 'my_many2one',
                'string': 'Partner',
                'comodel': 'test_new_api.partner',
                'type': 'many2one',
                # send the value like the web client does
                'default': [self.partner.id, 'Bob'],
                'value': [self.partner_2.id, "Test"],
            }, {
                'name': 'my_many2many',
                'string': 'Partner',
                'comodel': 'test_new_api.partner',
                'type': 'many2many',
                # send the value like the web client does
                'default': [[self.partner.id, 'Bob'], [self.partner_2.id, 'Test']],
                'value': [[self.partner_2.id, "Test"]],
                'definition_changed': True,
            },
        ]
        self.env.invalidate_all()

        sql_definition = self._get_sql_definition(self.discussion_1)
        expected_definition = [
            {
                'name': 'my_many2one',
                'string': 'Partner',
                'comodel': 'test_new_api.partner',
                'type': 'many2one',
                'default': self.partner.id,
            }, {
                'name': 'my_many2many',
                'string': 'Partner',
                'comodel': 'test_new_api.partner',
                'type': 'many2many',
                'default': [self.partner.id, self.partner_2.id],
            },
        ]
        self.assertEqual(sql_definition, expected_definition)

        sql_properties = self._get_sql_properties(self.message_1)
        expected_properties = {
            'my_many2one': self.partner_2.id,
            'my_many2many': [self.partner_2.id],
        }
        self.assertEqual(expected_properties, sql_properties)

    @mute_logger('odoo.fields')
    @users('test')
    def test_properties_field_security(self):
        """Check the access right related to the Properties fields."""
        def _mocked_check_access_rights(records, operation, raise_exception=True):
            if records.env.su:  # called with SUDO
                return True
            if raise_exception:
                raise AccessError('')
            return False

        message = self.message_1.with_user(self.test_user)

        # a user read a properties with a many2one to a record he doesn't have access to
        tag = self.env['test_new_api.multi.tag'].create({'name': 'Test Tag'})

        message.attributes = [{
            'name': 'test',
            'type': 'many2one',
            'comodel': 'test_new_api.multi.tag',
            'value': [tag.id, 'Tag'],
            'definition_changed': True,
        }]
        values = message.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values['value'], (tag.id, 'Test Tag'))
        self.env.invalidate_all()
        with patch('odoo.addons.test_new_api.models.test_new_api.MultiTag.check_access_rights', _mocked_check_access_rights):
            values = message.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values['value'], (tag.id, None))

        # a user read a properties with a many2one to a record
        # but doesn't have access to its parent
        self.env.invalidate_all()
        with patch('odoo.addons.test_new_api.models.test_new_api.Discussion.check_access_rights', _mocked_check_access_rights):
            values = message.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values['value'], (tag.id, 'Test Tag'))


class PropertiesSearchCase(TestPropertiesMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.messages = cls.message_1 | cls.message_2 | cls.message_3
        cls.env['test_new_api.message'].search([('id', 'not in', cls.messages.ids)]).unlink()

    @mute_logger('odoo.fields')
    def test_properties_field_search_boolean(self):
        # search on boolean
        self.message_1.attributes = [{
            'name': 'myboolean',
            'type': 'boolean',
            'value': True,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myboolean': False}
        messages = self.env['test_new_api.message'].search([('attributes.myboolean', '=', True)])
        self.assertEqual(messages, self.message_1)
        messages = self.env['test_new_api.message'].search([('attributes.myboolean', '!=', False)])
        self.assertEqual(messages, self.message_1)
        messages = self.env['test_new_api.message'].search([('attributes.myboolean', '=', False)])
        # message 2 has a falsy boolean properties
        # message 3 doesn't have the properties (key in dict doesn't exist)
        self.assertEqual(messages, self.message_2 | self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.myboolean', '!=', True)])
        self.assertEqual(messages, self.message_2 | self.message_3)

    @mute_logger('odoo.fields')
    def test_properties_field_search_char(self):
        # search on text properties
        self.message_1.attributes = [{
            'name': 'mychar',
            'type': 'char',
            'value': 'Test',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mychar': 'TeSt'}

        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', 'Test')])
        self.assertEqual(messages, self.message_1, "Should be able to search on a properties field")
        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', '"Test"')])
        self.assertFalse(messages)
        messages = self.env['test_new_api.message'].search([('attributes.mychar', 'ilike', 'test')])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mychar', 'not ilike', 'test')])
        self.assertFalse(messages)
        messages = self.env['test_new_api.message'].search([('attributes.mychar', 'ilike', '"test"')])
        self.assertFalse(messages)

        for forbidden_char in '! ()"\'.':
            searches = (
                f'mychar{forbidden_char}',
                f'my{forbidden_char}char',
                f'{forbidden_char}mychar',
            )
            for search in searches:
                with self.assertRaises(ValueError), self.assertQueryCount(0):
                    self.env['test_new_api.message'].search([(f'attributes.{search}', '=', 'Test')])

        # search falsy properties
        self.message_3.discussion = self.message_2.discussion
        self.message_3.attributes = [{'name': 'mychar', 'value': False}]
        self.assertEqual(self._get_sql_properties(self.message_3), {'mychar': False})
        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', False)])
        self.assertEqual(messages, self.message_3)

        # search falsy properties when the key doesn't exist in the dict
        # message 2 properties is False, message 3 properties doesn't exist in database
        self.message_2.attributes = [{'name': 'mychar', 'value': False}]
        self.env.cr.execute(
            "UPDATE test_new_api_message SET attributes = '{}' WHERE id = %s",
            [self.message_3.id],
        )
        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', False)])
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self.env['test_new_api.message'].search([('attributes.mychar', '!=', False)])
        self.assertEqual(messages, self.message_1)

        # message 1 property contain a string but is not falsy so it's not returned
        messages = self.env['test_new_api.message'].search([('attributes.mychar', '!=', True)])
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', True)])
        self.assertEqual(messages, self.message_1)

        # message 3 is now null instead of being an empty dict
        self.env.cr.execute(
            "UPDATE test_new_api_message SET attributes = NULL WHERE id = %s",
            [self.message_3.id],
        )

        messages = self.env['test_new_api.message'].search([('attributes.mychar', '=', False)])
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self.env['test_new_api.message'].search([('attributes.mychar', '!=', False)])
        self.assertEqual(messages, self.message_1)

    @mute_logger('odoo.fields')
    def test_properties_field_search_float(self):
        # search on float
        self.message_1.attributes = [{
            'name': 'myfloat',
            'type': 'float',
            'value': 3.14,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myfloat': 5.55}
        messages = self.env['test_new_api.message'].search([('attributes.myfloat', '>', 4.4)])
        self.assertEqual(messages, self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.myfloat', '<', 4.4)])
        self.assertEqual(messages, self.message_1)
        messages = self.env['test_new_api.message'].search([('attributes.myfloat', '>', 1.1)])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.myfloat', '<=', 1.1)])
        self.assertFalse(messages)
        messages = self.env['test_new_api.message'].search([('attributes.myfloat', '=', 3.14)])
        self.assertEqual(messages, self.message_1)

    @mute_logger('odoo.fields')
    def test_properties_field_search_integer(self):
        # search on integer
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'myint',
            'type': 'integer',
            'value': 33,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myint': 111}
        self.message_3.attributes = {'myint': -2}

        messages = self.env['test_new_api.message'].search([('attributes.myint', '>', 4)])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.myint', '<', 4)])
        self.assertEqual(messages, self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.myint', '=', 111)])
        self.assertEqual(messages, self.message_2)
        # search on the JSONified value (operator "->>")
        messages = self.env['test_new_api.message'].search([('attributes.myint', 'ilike', '1')])
        self.assertEqual(messages, self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.myint', 'not ilike', '1')])
        self.assertEqual(messages, self.message_1 | self.message_3)

    @mute_logger('odoo.fields')
    def test_properties_field_search_many2many(self):
        self.messages.discussion = self.discussion_1
        partners = self.env['res.partner'].create([{'name': 'A'}, {'name': 'B'}, {'name': 'C'}])
        self.message_1.attributes = [{
            'name': 'mymany2many',
            'type': 'many2many',
            'comodel': 'res.partner',
            'value': partners.ids,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mymany2many': [partners[1].id]}
        self.message_3.attributes = {'mymany2many': [partners[2].id]}
        messages = self.env['test_new_api.message'].search(
            [('attributes.mymany2many', 'in', partners[0].id)])
        self.assertEqual(messages, self.message_1)
        messages = self.env['test_new_api.message'].search(
            [('attributes.mymany2many', 'in', partners[1].id)])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search(
            [('attributes.mymany2many', 'in', partners[2].id)])
        self.assertEqual(messages, self.message_1 | self.message_3)
        messages = self.env['test_new_api.message'].search(
            [('attributes.mymany2many', 'not in', partners[0].id)])
        self.assertEqual(messages, self.message_2 | self.message_3)

        # IN operator (not supported on many2many and return weird results)
        messages = self.env['test_new_api.message'].search(
            [('attributes.mymany2many', 'in', [partners[0].id, partners[1].id])])
        self.assertEqual(messages, self.message_2)  # should be self.message_1 | self.message_2

    @mute_logger('odoo.fields')
    def test_properties_field_search_many2one(self):
        # many2one are just like integer
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'mypartner',
            'type': 'integer',
            'value': self.partner.id,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mypartner': self.partner_2.id}
        self.message_3.attributes = {'mypartner': False}

        messages = self.env['test_new_api.message'].search(
            [('attributes.mypartner', 'in', [self.partner.id, self.partner_2.id])])
        self.assertEqual(messages, self.message_1 | self.message_2)

        messages = self.env['test_new_api.message'].search(
            [('attributes.mypartner', 'not in', [self.partner.id, self.partner_2.id])])
        self.assertEqual(messages, self.message_3)

        messages = self.env['test_new_api.message'].search(
            [('attributes.mypartner', 'ilike', self.partner.display_name)])
        self.assertFalse(messages, "The ilike on relational properties is not supported")

    @mute_logger('odoo.fields')
    def test_properties_field_search_tags(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'mytags',
            'type': 'tags',
            'value': ['a', 'b'],
            'tags': [['a', 'A', 1], ['b', 'B', 2], ['aa', 'AA', 3]],
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mytags': ['b']}
        self.message_3.attributes = {'mytags': ['aa']}

        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', 'a')])
        self.assertEqual(messages, self.message_1)
        # the search is done on the JSONified value (operator "->>")
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'ilike', 'a')])
        self.assertEqual(messages, self.message_1 | self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'not ilike', 'a')])
        self.assertEqual(messages, self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', 'b')])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', 'aa')])
        self.assertEqual(messages, self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'not in', 'b')])
        self.assertEqual(messages, self.message_3)
        # the search is done on the JSONified value (operator "->>")
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'ilike', '["aa"]')])
        self.assertEqual(messages, self.message_3)

        # IN operator on array
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', [])])
        self.assertFalse(messages)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'not in', [])])
        self.assertEqual(messages, self.message_1 | self.message_2 | self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', ['a', 'b'])])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', ['b', 'a'])])
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', ['aa'])])
        self.assertEqual(messages, self.message_3)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'in', ['aa', 'b'])])
        self.assertEqual(messages, self.message_3 | self.message_2)
        messages = self.env['test_new_api.message'].search([('attributes.mytags', 'not in', ['a', 'b'])])
        self.assertEqual(messages, self.message_3)

    @mute_logger('odoo.fields')
    def test_properties_field_search_unaccent(self):
        if not self.registry.has_unaccent:
            # To enable unaccent feature:
            # CREATE EXTENSION unaccent;
            raise unittest.SkipTest("unaccent not enabled")

        Model = self.env['test_new_api.message']
        (self.message_1 | self.message_2).discussion = self.discussion_1
        # search on text properties
        self.message_1.attributes = [{
            'name': 'mychar',
            'type': 'char',
            'value': 'Hélène',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mychar': 'Helene'}

        result = Model.search([('attributes.mychar', 'ilike', 'Helene')])
        self.assertEqual(self.message_1 | self.message_2, result)

        result = Model.search([('attributes.mychar', 'ilike', 'hélène')])
        self.assertEqual(self.message_1 | self.message_2, result)

        result = Model.search([('attributes.mychar', 'not ilike', 'Helene')])
        self.assertNotIn(self.message_1, result)
        self.assertNotIn(self.message_2, result)

        result = Model.search([('attributes.mychar', 'not ilike', 'hélène')])
        self.assertNotIn(self.message_1, result)
        self.assertNotIn(self.message_2, result)

    @mute_logger('odoo.fields')
    def test_properties_field_search_orderby_string(self):
        """Test that we can order record by properties string values."""
        (self.message_1 | self.message_2 | self.message_3).discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'mychar',
            'type': 'char',
            'value': 'BB',
            'definition_changed': True,
        }]
        self.message_2.attributes = {'mychar': 'AA'}
        self.message_3.attributes = {'mychar': 'CC'}

        self.env.flush_all()

        result = self.env['test_new_api.message'].search(
            domain=[['attributes.mychar', '!=', False]],
            order='attributes.mychar ASC')
        self.assertEqual(result[0], self.message_2)
        self.assertEqual(result[1], self.message_1)
        self.assertEqual(result[2], self.message_3)

        result = self.env['test_new_api.message'].search(
            domain=[['attributes.mychar', '!=', False]],
            order='attributes.mychar DESC')
        self.assertEqual(result[0], self.message_3)
        self.assertEqual(result[1], self.message_1)
        self.assertEqual(result[2], self.message_2)

    @mute_logger('odoo.fields')
    def test_properties_field_search_orderby_integer(self):
        """Test that we can order record by properties integer values."""
        (self.message_1 | self.message_2 | self.message_3).discussion = self.discussion_1
        self.message_1.attributes = [{
            'name': 'myinteger',
            'type': 'integer',
            'value': 22,
            'definition_changed': True,
        }]
        self.message_2.attributes = {'myinteger': 111}
        self.message_3.attributes = {'myinteger': 33}

        self.env.flush_all()

        result = self.env['test_new_api.message'].search(
            domain=[['attributes.myinteger', '!=', False]],
            order='attributes.myinteger ASC')
        self.assertEqual(result[0], self.message_1)
        self.assertEqual(result[1], self.message_3)
        self.assertEqual(result[2], self.message_2)

        result = self.env['test_new_api.message'].search(
            domain=[['attributes.myinteger', '!=', False]],
            order='attributes.myinteger DESC')
        self.assertEqual(result[0], self.message_2)
        self.assertEqual(result[1], self.message_3)
        self.assertEqual(result[2], self.message_1)

    @mute_logger('odoo.fields')
    def test_properties_field_search_orderby_injection(self):
        """Check the restriction on the property name."""
        self.message_1.attributes = [{
            'name': 'myinteger',
            'type': 'integer',
            'value': 22,
            'definition_changed': True,
        }]

        for c in '! ()"\'.':
            orders = (
                f'attributes.myinteger{c} ASC',
                f'attributes.my{c}integer ASC',
                f'attribut{c}es.myinteger ASC',
            )

            if c == ' ':
                # allow multiple spaces after the property name
                orders = orders[1:]

            for order in orders:
                with self.assertRaises(UserError), self.assertQueryCount(0):
                    self.env['test_new_api.message'].search(domain=[], order=order)
