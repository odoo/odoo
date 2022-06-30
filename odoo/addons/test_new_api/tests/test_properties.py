# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import Form, TransactionCase
from odoo.tools import mute_logger


class PropertiesCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env.user
        cls.partner = cls.env['test_new_api.partner'].create({'name': 'Test Partner Properties'})
        cls.partner_2 = cls.env['test_new_api.partner'].create({'name': 'Test Partner Properties 2'})

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

    def test_properties_field(self):
        self.assertTrue(isinstance(self.message_1.attributes, list))
        # testing assigned value
        self.assertEqual(self.message_1.attributes, [{
            'name': 'discussion_color_code',
            'string': 'Color Code',
            'type': 'char',
            'default': 'blue',
            'value': 'Test',
        }, {
            'name': 'moderator_partner_id',
            'string': 'Partner',
            'type': 'many2one',
            'comodel': 'test_new_api.partner',
            'value': self.partner.id,
        }])

        self.assertEqual(self.message_2.attributes[0]['value'], 'blue')
        self.assertFalse(self.message_2.attributes[1]['value'])
        # testing default value
        self.assertEqual(
            self.message_3.attributes[0]['value'], 'draft',
            msg='Should have taken the default value')

        self.message_1.attributes = [
            {'name': 'discussion_color_code', 'value': 'red'},
            {'name': 'moderator_partner_id', 'value': self.partner_2.id},
        ]
        self.assertEqual(self.message_1.attributes[0]['value'], 'red')

        self.env.invalidate_all()

        self.assertEqual(self.message_1.attributes[0]['value'], 'red')
        self.assertEqual(self.message_1.attributes[1]['value'], self.partner_2.id)

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
            property_definition['value'] = None

        self.assertEqual(self.message_3.read(['attributes'])[0]['attributes'], expected)
        self.assertEqual(self.message_3.attributes, expected)

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

    def test_properties_field_read_batch(self):
        values = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]['type'], 'char')
        self.assertEqual(values[1]['type'], 'many2one')

        message_2_values = self.message_1.attributes
        message_2_values[1]['value'] = [self.partner_2.id, "Bob"]
        self.message_2.attributes = message_2_values

        expected_queries = [
            # read the properties field value
            'SELECT "test_new_api_message"."id" AS "id", "test_new_api_message"."attributes" AS "attributes" FROM "test_new_api_message" WHERE "test_new_api_message".id IN %s',
            'SELECT "test_new_api_message"."id" AS "id", "test_new_api_message"."discussion" AS "discussion", "test_new_api_message"."body" AS "body", "test_new_api_message"."author" AS "author", "test_new_api_message"."name" AS "name", "test_new_api_message"."important" AS "important", "test_new_api_message"."priority" AS "priority", "test_new_api_message"."create_uid" AS "create_uid", "test_new_api_message"."create_date" AS "create_date", "test_new_api_message"."write_uid" AS "write_uid", "test_new_api_message"."write_date" AS "write_date" FROM "test_new_api_message" WHERE "test_new_api_message".id IN %s',
            # read the definition on the definition record
            'SELECT "test_new_api_discussion"."id" AS "id", "test_new_api_discussion"."attributes_definition" AS "attributes_definition" FROM "test_new_api_discussion" WHERE "test_new_api_discussion".id IN %s',
            # check the many2one existence
            'SELECT "test_new_api_partner".id FROM "test_new_api_partner" WHERE "test_new_api_partner".id IN %s',
            'SELECT "test_new_api_partner"."id" AS "id", "test_new_api_partner"."name" AS "name", "test_new_api_partner"."create_uid" AS "create_uid", "test_new_api_partner"."create_date" AS "create_date", "test_new_api_partner"."write_uid" AS "write_uid", "test_new_api_partner"."write_date" AS "write_date" FROM "test_new_api_partner" WHERE "test_new_api_partner".id IN %s',
        ]

        self.env.invalidate_all()
        with self.assertQueryCount(5), self.assertQueries(expected_queries):
            self.message_1.read(['attributes'])

        self.env.invalidate_all()
        expected_queries += expected_queries[-2:]
        with self.assertQueryCount(7), self.assertQueries(expected_queries):
            # 2 more queries for message 2 to verify his partner existence / name_get
            (self.message_1 | self.message_2).read(['attributes'])

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
        self.assertEqual(self.message_1.attributes[0]['value'], 'purple')

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

        with self.assertQueryCount(9):
            messages = self.env['test_new_api.message'].create([{
                'name': 'Test Message',
                'discussion': self.discussion_1.id,
                'author': self.user.id,
                'attributes': [{
                    'name': 'discussion_color_code',
                    'string': 'New Label',
                    'type': 'char',
                    'default': 'blue',
                    'value': 'purple',
                }, {
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
                    'name': 'state',
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
        self.assertEqual(sql_definition, [
            {
                'name': 'discussion_color_code',
                'type': 'char', 'string':
                'New Label', 'default':
                'blue'
            }, {
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'string': 'Partner',
            }
        ])

        self.assertEqual(
            self.discussion_1.attributes_definition[0]['string'], 'New Label',
            msg='Should have updated the definition record')

        self.assertEqual(len(messages), 2)

        sql_properties_1 = self._get_sql_properties(messages[0])
        self.assertEqual(
            sql_properties_1,
            {'moderator_partner_id': self.partner.id,
             'discussion_color_code': 'purple'})
        sql_properties_2 = self._get_sql_properties(messages[1])
        self.assertEqual(
            sql_properties_2,
            {'state': 'draft'})

        properties_values_1 = messages[0].attributes
        properties_values_2 = messages[1].attributes

        self.assertEqual(len(properties_values_1), 2, msg='Discussion 1 has 2 properties')
        self.assertEqual(len(properties_values_2), 1, msg='Discussion 2 has 1 property')

        self.assertEqual(properties_values_1[0]['value'], 'purple')
        self.assertEqual(properties_values_1[1]['value'], self.partner.id)
        self.assertEqual(properties_values_2[0]['value'], 'draft',
                         msg='Should have taken the default value')

    def test_properties_field_default(self):
        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': self.discussion_2.id,
            'author': self.user.id,
        })
        self.assertEqual(
            message.attributes[0]['value'],
            'draft',
            msg='Should have taken the default value')

        message.attributes = [{'name': 'state', 'value': None}]
        self.assertFalse(
            message.attributes[0]['value'],
            msg='Writing None should not reset to the default value')

        # test the case where the definition record come from a default as well
        self.env['test_new_api.message']._fields['discussion'].default = lambda __: self.discussion_2.id
        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'author': self.user.id,
        })
        self.assertEqual(message.discussion, self.discussion_2)
        self.assertEqual(
            message.attributes[0]['value'],
            'draft',
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
        self.assertEqual(message.attributes, [{
            'name': 'test',
            'type': 'char',
            'default': 'default char',
            'value': 'default char',
        }])

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

        # read the default many2one and deactivate the name_get
        read_values = self.discussion_1.read(['attributes_definition'], load=None)[0]['attributes_definition']
        self.assertEqual(
            read_values[0]['default'],
            self.partner.id,
            msg='If the name_get is deactivate, it should not return the display name',
        )

        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'author': self.user.id,
            'discussion': self.discussion_1.id,
        })

        properties = message.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], (self.partner.id, self.partner.display_name))

        self.assertEqual(message.attributes[0]['value'], self.partner.id)

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
            message.attributes[0]['value'],
            self.partner_2.id,
            msg='Should not take the default value',
        )

    def test_properties_field_read(self):
        """Test the behavior of the read method.

        In comparison with a simple "record.properties", the read method should not
        record a recordset for the many2one, but a tuple with the record id and
        the record name_get.
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

        # disable the name_get
        properties_values = (self.message_1 | self.message_3).read(['attributes'], load=None)
        many2one_property = properties_values[0]['attributes'][1]

        self.assertEqual(
            many2one_property['value'], self.partner.id,
            msg='If name_get is disable, should only return the record id')

    def test_properties_field_many2one_basic(self):
        """Test the basic (read, write...) of the many2one property."""
        self.message_2.attributes = [
            {
                "name": "discussion_color_code",
                "type": "char",
                "string": "Color Code",
                "default": "blue",
                "value": None,
            }, {
                "name": "moderator_partner_id",
                "type": "many2one",
                "string": "Partner",
                "comodel": "test_new_api.partner",
                "value": self.partner_2.id,
            },
        ]

        self.assertFalse(self.message_2.attributes[0]['value'])
        self.assertEqual(self.message_2.attributes[1]['value'], self.partner_2.id)
        sql_values = self._get_sql_properties(self.message_2)
        self.assertEqual(
            sql_values,
            {'moderator_partner_id': self.partner_2.id,
             'discussion_color_code': False})

        # read the many2one
        properties = self.message_2.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[1]['value'], (self.partner_2.id, self.partner_2.display_name))
        self.assertEqual(properties[1]['comodel'], 'test_new_api.partner')

    @mute_logger('odoo.models.unlink')
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
            # 2 queries to check if the many2one still exists / name_get
            self.assertFalse(self.message_2.attributes[0]['value'])

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
                'value': None,
            }],
        )
        partner.unlink()
        self.assertEqual(
            self.message_2.read(['attributes'])[0]['attributes'],
            [{
                'name': 'moderator_partner_id',
                'type': 'many2one',
                'comodel': 'res.partner',
                'default': None,
                'value': None,
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
        self.assertFalse(self.message_1.attributes[0]['value'])

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

        domain = self.message_1.attributes[0]['domain']
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

        self.assertEqual(len(self.message_1.attributes), 3)
        self.assertEqual(self.message_1.attributes[0]['value'], 55555555555)
        self.assertEqual(self.message_1.attributes[1]['value'], 1.337)
        self.assertEqual(self.message_1.attributes[2]['value'], True)

        self.message_1.attributes = [{'name': 'boolean_value', 'value': 0}]
        self.assertEqual(
            self.message_1.attributes[2]['value'], False,
            msg='Boolean value must have been converted to False')

    def test_properties_field_selection(self):
        self.message_3.attributes = [{'name': 'state', 'value': 'done'}]
        self.env.invalidate_all()
        self.assertEqual(self.message_3.attributes[0]['value'], 'done')

        # the option might have been removed on the definition, write False
        self.message_3.attributes = [{'name': 'state', 'value': 'unknown_selection'}]
        self.env.invalidate_all()
        self.assertFalse(self.message_3.attributes[0]['value'])

        with self.assertRaises(ValueError):
            # check that 2 options can not have the same id
            self.discussion_1.attributes_definition = [
                {
                    'name': 'option',
                    'type': 'selection',
                    'selection': [['a', 'A'], ['b', 'B'], ['a', 'C']],
                }
            ]

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

        self.assertEqual(message.attributes[0]['value'], ['be', 'de'])
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

        self.assertEqual(
            message.attributes[0]['value'],
            ['be'],
            msg='The tag has been removed on the definition, should be removed when reading the child')
        self.assertEqual(
            message.attributes[0]['tags'],
            [['be', 'BE', 1], ['fr', 'FR', 2], ['it', 'IT', 1]])

        # next write on the child must update the value
        message.attributes = message.attributes

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

    @mute_logger('odoo.models.unlink')
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

        with self.assertQueryCount(5):
            self.message_1.attributes = [
                {
                    "name": "moderator_partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_new_api.partner",
                    "value": partners[:10].name_get(),
                }
            ]
            self.assertEqual(self.message_1.attributes[0]['value'], partners[:10].ids)

        partners[:5].unlink()
        with self.assertQueryCount(4):
            self.assertEqual(self.message_1.attributes[0]['value'], partners[5:10].ids)

        partners[5].unlink()
        with self.assertQueryCount(5):
            properties = self.message_1.read(['attributes'])[0]['attributes']
        self.assertEqual(properties[0]['value'], partners[6:10].name_get())

        # need to wait next write to clean data in database
        # a single read won't clean the removed many2many
        self.message_1.attributes = self.message_1.read(['attributes'])[0]['attributes']

        sql_values = self._get_sql_properties(self.message_1)
        self.assertEqual(sql_values, {'moderator_partner_ids': partners[6:10].ids})

        # read and disable name_get
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

    def test_properties_field_performance(self):
        with self.assertQueryCount(4):
            self.message_1.attributes

        expected = ['SELECT "test_new_api_partner".id FROM "test_new_api_partner" WHERE "test_new_api_partner".id IN %s']
        with self.assertQueryCount(1, msg='Must read value from cache'), self.assertQueries(expected):
            # still cost 1 SQL query to check existence because the ORM stores
            # the raw SQL response in cache (not the result of convert_to_cache)
            # so the value in cache is not verified (see models.py@_read)
            self.message_1.attributes

        expected = [
            'SELECT "test_new_api_emailmessage".id FROM "test_new_api_emailmessage" WHERE ("test_new_api_emailmessage"."message" in %s) ORDER BY  "test_new_api_emailmessage"."id"',
            'UPDATE "test_new_api_message" SET "attributes" = %s, "write_date" = %s, "write_uid" = %s WHERE id IN %s',
        ]

        with self.assertQueryCount(2), self.assertQueries(expected):
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
        self.assertFalse(self.message_1.attributes[0]['value'])

        # add a property on the definition record
        attributes_definition += [{'name': 'state', 'string': 'State', 'type': 'char'}]
        self.discussion_1.attributes_definition = attributes_definition
        self.message_1.attributes = [{'name': 'state', 'value': 'ready'}]

        self.env.invalidate_all()

        self.assertEqual(self.message_1.attributes[2]['value'], 'ready')

        # remove a property from the definition
        # the properties on the child should remain, until we write on it
        # when reading, the removed property must be filtered
        self.discussion_1.attributes_definition = attributes_definition[:-1]  # remove the state field

        self.assertFalse(self.message_1.attributes[0]['value'])

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

    def test_properties_field_onchange(self):
        """If we change the definition record, the onchange of the properties field must be triggered."""
        message_form = Form(self.env['test_new_api.message'])

        with self.assertQueryCount(11):
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
                    'value': None,
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

        with self.assertQueryCount(7):
            message = message_form.save()

        self.assertEqual(
            message.attributes[0]['value'],
            'draft',
            msg='Should take the default value',
        )

        # check cached value
        cached_value = self.env.cache.get(message, message._fields['attributes'])
        self.assertEqual(cached_value, {'state': 'draft'})

        # change the definition record, change the definition and add default values
        self.assertEqual(message.discussion, self.discussion_2)
        with self.assertQueryCount(7):
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
                'value': None,
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
            field_onchange={'attributes': '1'},
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
            field_onchange={'attributes': '1'},
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
            [{'name': 'new_property', 'type': 'char', 'value': 'test value'}])

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

    def test_properties_field_security(self):
        """Check the access right related to the Properties fields."""
        MultiTag = type(self.env['test_new_api.multi.tag'])

        def _mocked_check_access_rights(*args, **kwargs):
            raise AccessError('')

        # a user read a properties with a many2one to a record he doesn't have access to
        tag = self.env['test_new_api.multi.tag'].create({'name': 'Test Tag'})
        self.message_1.attributes = [{
            'name': 'test',
            'type': 'many2one',
            'comodel': 'test_new_api.multi.tag',
            'value': [tag.id, 'Tag'],
            'definition_changed': True,
        }]
        values = self.message_1.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values['value'], (tag.id, 'Test Tag'))
        self.env.invalidate_all()
        with patch.object(MultiTag, 'check_access_rights', side_effect=_mocked_check_access_rights):
            values = self.message_1.read(['attributes'])[0]['attributes'][0]
        self.assertEqual(values['value'], (tag.id, 'No Access'))

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
        self.assertTrue(value and value[0])
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
