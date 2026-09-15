import datetime
import json
import unittest
from collections import OrderedDict as _OrderedDict
from collections import abc
from unittest.mock import patch

import psycopg

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tests import Form, TransactionCase, users
from odoo.tools import get_lang, mute_logger

from odoo.addons.base.tests.test_expression import TransactionExpressionCase


class TestPropertiesMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env.user
        cls.partner = cls.env["test_orm.partner"].create(
            {"name": "Test Partner Properties"}
        )
        cls.partner_2 = cls.env["test_orm.partner"].create(
            {"name": "Test Partner Properties 2"}
        )

        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test",
                "login": "test",
                "company_id": cls.env.company.id,
            }
        )

        attributes_definition_1 = [
            {
                "name": "discussion_color_code",
                "string": "Color Code",
                "type": "char",
                "default": "blue",
            },
            {
                "name": "moderator_partner_id",
                "string": "Partner",
                "type": "many2one",
                "comodel": "test_orm.partner",
            },
        ]

        attributes_definition_2 = [
            {
                "name": "state",
                "type": "selection",
                "string": "Status",
                "selection": [
                    ("draft", "Draft"),
                    ("progress", "In Progress"),
                    ("done", "Done"),
                ],
                "default": "draft",
            }
        ]

        cls.discussion_1 = cls.env["test_orm.discussion"].create(
            {
                "name": "Test Discussion",
                "attributes_definition": attributes_definition_1,
                "participants": [Command.link(cls.user.id)],
            }
        )
        cls.discussion_2 = cls.env["test_orm.discussion"].create(
            {
                "name": "Test Discussion",
                "attributes_definition": attributes_definition_2,
                "participants": [Command.link(cls.user.id)],
            }
        )

        cls.message_1 = cls.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": cls.discussion_1.id,
                "author": cls.user.id,
                "attributes": {
                    "discussion_color_code": "Test",
                    "moderator_partner_id": cls.partner.id,
                },
            }
        )

        cls.message_2 = cls.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": cls.discussion_1.id,
                "author": cls.user.id,
            }
        )
        cls.message_3 = cls.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": cls.discussion_2.id,
                "author": cls.user.id,
            }
        )

    def _get_sql_properties(self, message):
        self.env.flush_all()

        self.env.cr.execute(
            """
            SELECT attributes
              FROM test_orm_message
             WHERE id = %s
            """,
            (message.id,),
        )
        value = self.env.cr.fetchone()
        self.assertTrue(value)
        return value[0]

    def _get_sql_definition(self, discussion):
        self.env.flush_all()

        self.env.cr.execute(
            """
            SELECT attributes_definition
              FROM test_orm_discussion
             WHERE id = %s
            """,
            (discussion.id,),
        )
        value = self.env.cr.fetchone()
        self.assertTrue(value and value[0])
        return value[0]

    def get_read_dict(self, record, field_name):
        read_value = record.read([field_name])[0][field_name]
        field = record._fields[field_name]
        field._remove_display_name(read_value)
        return field._list_to_dict(read_value)


class PropertiesCase(TestPropertiesMixin):
    @mute_logger("odoo.db")
    def test_base_properties_model_access(self):
        with self.assertRaises(AccessError):
            self.env["res.partner"].with_user(self.test_user).create(
                {
                    "name": "test",
                    "properties": [
                        {
                            "name": "test",
                            "type": "char",
                            "definition_changed": True,
                        }
                    ],
                }
            )

        definition_record = self.env[
            "properties.base.definition"
        ]._get_definition_for_property_field("res.partner", "properties")
        self.assertEqual(definition_record.properties_definition, [])

        field = (
            self.env["ir.model.fields"]
            .sudo()
            ._get("test_orm.emailmessage", "properties")
        )
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.env["properties.base.definition"].create(
                {"properties_field_id": field.id}
            )

        with self.assertRaises(AccessError):
            definition_record.sudo().properties_field_id = field.id

        with self.assertRaises(AccessError):
            definition_record.with_user(self.test_user).unlink()

        record_0 = self.env["res.partner"].create(
            [
                {
                    "properties": [
                        {
                            "name": "test",
                            "type": "char",
                            "definition_changed": True,
                            "value": "test",
                        }
                    ],
                    "name": "test",
                },
                {"name": "test"},
            ]
        )[0]
        self.assertEqual(record_0.properties_base_definition_id, definition_record)
        self.assertEqual(
            definition_record.properties_definition,
            [{"name": "test", "type": "char"}],
        )

        record_2 = self.env["test_orm.emailmessage"].create([{}, {}])[0]
        record_2.write(
            {
                "properties": [
                    {
                        "name": "test_2",
                        "type": "char",
                        "definition_changed": True,
                        "value": "test",
                    }
                ]
            }
        )
        self.assertNotEqual(definition_record, record_2.properties_base_definition_id)
        self.assertEqual(
            record_2.properties_base_definition_id.properties_definition,
            [{"name": "test_2", "type": "char"}],
        )
        self.assertEqual(
            definition_record.properties_definition,
            [{"name": "test", "type": "char"}],
        )

        with self.assertRaises(AccessError):
            self.env["res.partner"].with_user(self.test_user).create(
                {
                    "name": "test",
                    "properties": [
                        {
                            "name": "test",
                            "type": "char",
                            "definition_deleted": True,
                        }
                    ],
                }
            )

    def test_properties_field(self):
        self.assertIsInstance(self.message_1.attributes, abc.Mapping)
        self.assertEqual(
            self.message_1.attributes,
            {
                "discussion_color_code": "Test",
                "moderator_partner_id": self.partner.id,
            },
        )

        self.assertEqual(self.message_1.attributes["discussion_color_code"], "Test")
        self.assertEqual(self.message_2.attributes["discussion_color_code"], "blue")

        self.assertEqual(self.message_2.attributes, {"discussion_color_code": "blue"})

        self.assertEqual(
            self.message_3.attributes,
            {"state": "draft"},
            msg="Should have taken the default value",
        )

        self.message_1.attributes = [
            {"name": "discussion_color_code", "value": "red"},
            {"name": "moderator_partner_id", "value": self.partner_2.id},
        ]
        self.assertEqual(
            self.message_1.attributes,
            {
                "discussion_color_code": "red",
                "moderator_partner_id": self.partner_2.id,
            },
        )

        self.env.invalidate_all()

        self.assertEqual(
            self.message_1.attributes,
            {
                "discussion_color_code": "red",
                "moderator_partner_id": self.partner_2.id,
            },
        )

        database_values = self._get_sql_properties(self.message_1)
        self.assertTrue(isinstance(database_values, dict))
        self.assertEqual(
            database_values.get("discussion_color_code"),
            "red",
            msg="Value must be updated in the database",
        )

        self.message_3.attributes = False
        self.env.invalidate_all()

        expected = self.discussion_2.attributes_definition
        self.assertEqual(self.message_3.read(["attributes"])[0]["attributes"], expected)
        self.assertEqual(
            self.get_read_dict(self.message_3, "attributes"),
            {
                definition["name"]: definition["value"]
                for definition in expected
                if "value" in definition
            },
        )

        with self.assertRaises(ValueError):
            self.message_1.attributes = [
                {
                    "name": "12     301",
                    "type": "char",
                    "definition_changed": True,
                }
            ]

        with self.assertRaises(ValueError):
            self.message_1.attributes = [
                {
                    "name": "name" * 1000,
                    "type": "char",
                    "definition_changed": True,
                }
            ]

        with self.assertRaises(ValueError):
            self.message_1.attributes = [{"name": "name", "definition_changed": True}]

    def test_properties_web_read(self):
        self.message_1.write(
            {
                "attributes": [
                    {
                        "name": "discussion_color_code",
                        "string": "Test color code",
                        "type": "char",
                        "default": "blue",
                        "value": "purple",
                        "definition_changed": True,
                    },
                    {
                        "name": "selection",
                        "string": "Selection",
                        "type": "selection",
                        "selection": [["a", "A"], ["b", "B"]],
                        "value": "b",
                        "definition_changed": True,
                    },
                    {
                        "name": "moderator_partner_id",
                        "string": "Partner",
                        "type": "many2one",
                        "comodel": "test_orm.partner",
                        "value": [self.partner.id, "Bob"],
                        "definition_changed": True,
                    },
                    {
                        "name": "moderator_partner_ids",
                        "string": "Partners",
                        "type": "many2many",
                        "comodel": "test_orm.partner",
                        "value": [
                            [self.partner.id, "Bob"],
                            [self.partner_2.id, "Alice"],
                        ],
                        "definition_changed": True,
                    },
                ],
            }
        )

        result = self.message_1.web_read(
            {
                "attributes": {
                    "fields": {
                        "moderator_partner_id": {"fields": {"name": {}}},
                        "moderator_partner_ids": {"fields": {"name": {}}},
                        "selection": {},
                    },
                },
            }
        )
        self.assertEqual(
            result[0]["attributes"],
            [
                {
                    "name": "moderator_partner_id",
                    "string": "Partner",
                    "type": "many2one",
                    "comodel": "test_orm.partner",
                    "value": [
                        {
                            "id": self.partner.id,
                            "name": "Test Partner Properties",
                        }
                    ],
                },
                {
                    "name": "moderator_partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_orm.partner",
                    "value": [
                        {
                            "id": self.partner.id,
                            "name": "Test Partner Properties",
                        },
                        {
                            "id": self.partner_2.id,
                            "name": "Test Partner Properties 2",
                        },
                    ],
                },
                {
                    "name": "selection",
                    "string": "Selection",
                    "type": "selection",
                    "selection": [["a", "A"], ["b", "B"]],
                    "value": "b",
                },
            ],
        )

    def test_properties_field_parameters_raised(self):
        with self.assertRaises(ValueError):
            self.message_1.attributes = [
                {
                    "name": "discussion_color_code",
                    "string": "Color Code",
                    "type": "char",
                    "default": "blue",
                    "value": "Test",
                    "definition_changed": True,
                    "selection": [["a", "A"]],
                }
            ]

    def test_properties_field_injection(self):
        for c in "!#\"'- |+/\\":
            with self.assertRaises(ValueError):
                self.message_1.attributes = [
                    {
                        "name": f"discussion_color_code{c}",
                        "type": "char",
                        "definition_changed": True,
                    }
                ]

            with self.assertRaises(ValueError):
                self.discussion_1.attributes_definition = [
                    {
                        "name": f"discussion_color_code{c}",
                        "type": "char",
                    }
                ]

        with self.assertRaises(ValueError):
            self.message_1.attributes = [
                {
                    "name": "a" * 513,
                    "type": "char",
                    "definition_changed": True,
                }
            ]

        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {
                    "name": "a" * 513,
                    "type": "char",
                }
            ]

    @mute_logger("odoo.fields")
    def test_properties_field_write_batch(self):
        properties_values = (self.message_1 | self.message_3).read(["attributes"])
        properties_values = (
            properties_values[0]["attributes"] + properties_values[1]["attributes"]
        )

        for properties in properties_values:
            if properties["name"] == "discussion_color_code":
                properties["value"] = "orange"
            elif properties["name"] == "state":
                properties["value"] = "done"
            elif properties["name"] == "moderator_partner_id":
                properties["value"] = self.partner_2.id
            properties["definition_changed"] = True

        with self.assertRaises(UserError):
            (self.message_1 | self.message_3).write({"attributes": properties_values})

        self.message_3.discussion = self.message_1.discussion

        (self.message_1 | self.message_3).write({"attributes": properties_values})

        sql_values_1 = self._get_sql_properties(self.message_1)
        sql_values_3 = self._get_sql_properties(self.message_3)

        self.assertEqual(
            sql_values_1,
            {
                "discussion_color_code": "orange",
                "moderator_partner_id": self.partner_2.id,
                "state": "done",
            },
        )
        self.assertEqual(
            sql_values_3,
            {
                "discussion_color_code": "orange",
                "moderator_partner_id": self.partner_2.id,
                "state": "done",
            },
        )

    @mute_logger("odoo.models.unlink", "odoo.fields")
    def test_properties_field_read_batch(self):
        values = self.message_1.read(["attributes"])[0]["attributes"]
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]["type"], "char")
        self.assertEqual(values[1]["type"], "many2one")

        self.message_2.attributes = [
            {
                "name": "discussion_color_code",
                "type": "char",
                "string": "Color Code",
                "default": "blue",
                "value": "Test",
            },
            {
                "name": "moderator_partner_id",
                "type": "many2one",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "value": (self.partner_2.id, "Bob"),
            },
        ]

        body_field = self.env["test_orm.message"]._fields["body"]
        body_col = (
            '"test_orm_message"."body"->>%s'
            if body_field.translate
            else '"test_orm_message"."body"'
        )

        expected_queries = [
            """ SELECT "test_orm_message"."id",
                       "test_orm_message"."attributes"
                FROM "test_orm_message"
                WHERE "test_orm_message"."id" IN (%s)
            """,
            f""" SELECT "test_orm_message"."id",
                       "test_orm_message"."discussion",
                       {body_col},
                       "test_orm_message"."author",
                       "test_orm_message"."name",
                       "test_orm_message"."important",
                       "test_orm_message"."label"->>%s,
                       "test_orm_message"."plain_text",
                       "test_orm_message"."priority",
                       "test_orm_message"."active",
                       "test_orm_message"."create_uid",
                       "test_orm_message"."create_date",
                       "test_orm_message"."write_uid",
                       "test_orm_message"."write_date"
                FROM "test_orm_message"
                WHERE "test_orm_message"."id" IN (%s)
            """,
            """ SELECT "test_orm_discussion"."id",
                       "test_orm_discussion"."name",
                       "test_orm_discussion"."moderator",
                       "test_orm_discussion"."message_concat",
                       "test_orm_discussion"."history",
                       "test_orm_discussion"."attributes_definition",
                       "test_orm_discussion"."create_uid",
                       "test_orm_discussion"."create_date",
                       "test_orm_discussion"."write_uid",
                       "test_orm_discussion"."write_date"
                FROM "test_orm_discussion"
                WHERE "test_orm_discussion"."id" IN (%s)
            """,
            """ SELECT "test_orm_partner"."id"
                FROM "test_orm_partner"
                WHERE "test_orm_partner"."id" = ANY(%s)
            """,
            """ SELECT "test_orm_partner"."id",
                       "test_orm_partner"."name",
                       "test_orm_partner"."create_uid",
                       "test_orm_partner"."create_date",
                       "test_orm_partner"."write_uid",
                       "test_orm_partner"."write_date"
                FROM "test_orm_partner"
                WHERE "test_orm_partner"."id" IN (%s)
            """,
        ]

        self.env.invalidate_all()
        # the first read above verified the partner: the cursor remembers the
        # pair, so the existence statement does not run again
        exists_query = expected_queries[3]
        with (
            self.assertQueryCount(4),
            self.assertQueries([q for q in expected_queries if q is not exists_query]),
        ):
            self.message_1.read(["attributes"])

        discussions = [self.discussion_1, self.discussion_2]
        partners = self.env["test_orm.partner"].create(
            [{"name": f"Test {i}"} for i in range(50)]
        )
        messages = self.env["test_orm.message"].create(
            [
                {
                    "name": f"Test Message {i}",
                    "discussion": discussions[i % 2].id,
                    "author": self.user.id,
                    "attributes": [
                        {
                            "name": "partner_id",
                            "type": "many2one",
                            "comodel": "test_orm.partner",
                            "value": partner.id,
                            "definition_changed": True,
                        }
                    ],
                }
                for i, partner in enumerate(partners)
            ]
        )

        self.env.invalidate_all()

        with self.assertQueryCount(5), self.assertQueries(expected_queries):
            values = messages.read(["attributes"])

        partners[:20].unlink()
        self.env.invalidate_all()
        # the unlink discards the verified pairs of its model: verified again
        with self.assertQueryCount(5):
            values = messages.read(["attributes"])
        self.assertEqual(
            sorted(value["attributes"][0]["value"] for value in values[:20]),
            [False] * 20,
        )

    def test_a_property_read_record_by_record_verifies_the_siblings_at_once(self):
        partners = self.env["test_orm.partner"].create(
            [{"name": f"Batch {i}"} for i in range(30)]
        )
        messages = self.env["test_orm.message"].create(
            [
                {
                    "name": f"Batch message {i}",
                    "discussion": self.discussion_1.id,
                    "author": self.user.id,
                    "attributes": [
                        {
                            "name": "partner_id",
                            "type": "many2one",
                            "comodel": "test_orm.partner",
                            "value": partner.id,
                            "definition_changed": True,
                        },
                        {"name": "size", "type": "integer", "value": i},
                    ],
                }
                for i, partner in enumerate(partners)
            ]
        )
        self.env.invalidate_all()
        # the column, the messages, the discussion, one existence check over
        # the prefetch set, the partners' names: not one statement per record
        with self.assertQueryCount(5):
            sizes = [message.attributes["size"] for message in messages]
            peers = [message.attributes["partner_id"] for message in messages]
        self.assertEqual(sizes, list(range(30)))
        self.assertEqual(peers, list(partners))
        partners[:5].unlink()
        self.env.invalidate_all()
        peers = [message.attributes["partner_id"] for message in messages]
        self.assertEqual(peers[:5], [self.env["test_orm.partner"]] * 5)
        self.assertEqual(peers[5:], list(partners[5:]))

    @mute_logger("odoo.fields")
    def test_properties_field_delete(self):
        self.message_1.attributes = [
            {
                "name": "discussion_color_code",
                "string": "Test color code",
                "type": "char",
                "default": "blue",
                "value": "purple",
            },
            {
                "name": "moderator_partner_id",
                "string": "Partner",
                "type": "many2one",
                "comodel": "test_orm.partner",
                "value": [self.partner.id, "Bob"],
                "definition_deleted": True,
            },
        ]

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [
                {
                    "name": "discussion_color_code",
                    "type": "char",
                    "string": "Test color code",
                    "default": "blue",
                }
            ],
        )

        self.assertEqual(len(self.message_1.attributes), 1)
        self.assertEqual(self.message_1.attributes, {"discussion_color_code": "purple"})

    @mute_logger("odoo.fields")
    def test_properties_field_create_batch(self):
        self.env["test_orm.message"].create({"name": "test"})

        with self.assertQueryCount(2):
            messages = self.env["test_orm.message"].create(
                [
                    {
                        "name": "Test Message",
                        "discussion": False,
                        "author": self.user.id,
                    },
                    {
                        "name": "Test Message",
                        "discussion": False,
                        "author": self.user.id,
                    },
                ]
            )

        self.env.invalidate_all()
        with self.assertQueryCount(7):
            messages = self.env["test_orm.message"].create(
                [
                    {
                        "name": "Test Message",
                        "discussion": self.discussion_1.id,
                        "author": self.user.id,
                        "attributes": [
                            {
                                "string": "Discussion Color code",
                                "type": "char",
                                "default": "blue",
                                "value": "purple",
                                "definition_changed": True,
                            },
                            {
                                "name": "moderator_partner_id",
                                "string": "Partner",
                                "type": "many2one",
                                "comodel": "test_orm.partner",
                                "value": self.partner.id,
                                "definition_changed": True,
                            },
                        ],
                    },
                    {
                        "name": "Test Message",
                        "discussion": self.discussion_2.id,
                        "author": self.user.id,
                        "attributes": [
                            {
                                "type": "selection",
                                "string": "Status",
                                "selection": [
                                    ("draft", "Draft"),
                                    ("progress", "In Progress"),
                                    ("done", "Done"),
                                ],
                                "default": "draft",
                                "definition_changed": True,
                            }
                        ],
                    },
                ]
            )

        self.env.invalidate_all()
        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(len(sql_definition), 2)

        property_color_name = sql_definition[0]["name"]
        self.assertTrue(
            property_color_name, msg="Property name must have been generated"
        )

        self.assertEqual(
            sql_definition,
            [
                {
                    "name": property_color_name,
                    "default": "blue",
                    "string": "Discussion Color code",
                    "type": "char",
                },
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "comodel": "test_orm.partner",
                    "string": "Partner",
                },
            ],
        )

        self.assertEqual(
            self.discussion_1.attributes_definition[0]["string"],
            "Discussion Color code",
            msg="Should have updated the definition record",
        )

        self.assertEqual(len(messages), 2)

        sql_properties_1 = self._get_sql_properties(messages[0])
        self.assertEqual(
            sql_properties_1,
            {
                "moderator_partner_id": self.partner.id,
                property_color_name: "purple",
            },
        )
        sql_properties_2 = self._get_sql_properties(messages[1])
        status_name = self.discussion_2.attributes_definition[0]["name"]
        self.assertEqual(sql_properties_2, {status_name: "draft"})

        properties_values_1 = messages[0].attributes
        properties_values_2 = messages[1].attributes

        self.assertEqual(
            len(properties_values_1), 2, msg="Discussion 1 has 2 properties"
        )
        self.assertEqual(len(properties_values_2), 1, msg="Discussion 2 has 1 property")

        self.assertEqual(
            properties_values_1,
            {
                "moderator_partner_id": self.partner.id,
                property_color_name: "purple",
            },
        )
        self.assertEqual(
            properties_values_2,
            {status_name: "draft"},
            msg="Should have taken the default value",
        )

    def test_properties_field_default(self):
        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": self.discussion_2.id,
                "author": self.user.id,
            }
        )
        self.assertEqual(
            message.attributes,
            {"state": "draft"},
            msg="Should have taken the default value",
        )

        message.attributes = [{"name": "state", "value": None}]
        self.assertEqual(
            message.attributes,
            {},
            msg="Writing None should not reset to the default value",
        )

        def default_discussion(_record):
            return self.discussion_2.id

        with patch.object(
            self.env["test_orm.message"]._fields["discussion"],
            "default",
            default_discussion,
        ):
            message = self.env["test_orm.message"].create(
                {
                    "name": "Test Message",
                    "author": self.user.id,
                }
            )
            self.assertEqual(message.discussion, self.discussion_2)
            self.assertEqual(
                message.attributes,
                {"state": "draft"},
                msg="Should have taken the default value",
            )

            self.discussion_2.attributes_definition = [
                {
                    "name": "test",
                    "type": "char",
                    "default": "default char",
                }
            ]
            message = (
                self.env["test_orm.message"]
                .with_context(default_discussion=self.discussion_2)
                .create({"name": "Test Message", "author": self.user.id})
            )
            self.assertEqual(message.discussion, self.discussion_2)
            self.assertEqual(message.attributes, {"test": "default char"})

        self.discussion_1.attributes_definition = [
            {
                "name": "my_many2one",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "type": "many2one",
                "default": [self.partner.id, "Bob"],
            },
        ]
        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(sql_definition[0]["default"], self.partner.id)

        read_values = self.discussion_1.read(["attributes_definition"])[0][
            "attributes_definition"
        ]
        self.assertEqual(
            read_values[0]["default"],
            (self.partner.id, self.partner.display_name),
            msg="When reading many2one default, it should return the display name",
        )

        read_values = self.discussion_1.read(["attributes_definition"], load=None)[0][
            "attributes_definition"
        ]
        self.assertEqual(
            read_values[0]["default"],
            self.partner.id,
            msg="If the display_name is deactivate, it should not return the display name",
        )

        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "author": self.user.id,
                "discussion": self.discussion_1.id,
            }
        )

        properties = message.read(["attributes"])[0]["attributes"]
        self.assertEqual(
            properties[0]["value"], (self.partner.id, self.partner.display_name)
        )

        self.assertEqual(message.attributes, {"my_many2one": self.partner.id})

        property_definition = self.discussion_1.read(["attributes_definition"])[0][
            "attributes_definition"
        ]
        property_definition[0]["value"] = (self.partner_2.id, "Alice")
        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "author": self.user.id,
                "discussion": self.discussion_1.id,
                "attributes": property_definition,
            }
        )
        self.assertEqual(
            message.attributes,
            {"my_many2one": self.partner_2.id},
            msg="Should not take the default value",
        )

        record = self.env["test_orm.message"].create(
            {
                "attributes": {"my_many2one": self.partner_2.id},
            }
        )
        self.assertFalse(self._get_sql_properties(record))

        self.discussion_1.attributes_definition = []
        record = self.env["test_orm.message"].create(
            {
                "discussion": self.discussion_1.id,
                "attributes": {"my_many2one": self.partner_2.id},
            }
        )
        self.assertFalse(self._get_sql_properties(record))

        self.discussion_1.attributes_definition = []
        record = self.env["test_orm.message"].create(
            {
                "discussion": self.discussion_1.id,
                "attributes": [
                    {
                        "name": "test",
                        "type": "many2one",
                        "comodel": "test_orm.partner",
                        "default": self.partner_2.id,
                        "definition_changed": True,
                    }
                ],
            }
        )
        self.assertEqual(self._get_sql_properties(record), {"test": self.partner_2.id})

        record = self.env["test_orm.message"].create(
            {
                "discussion": self.discussion_1.id,
                "attributes": [
                    {
                        "name": "test",
                        "type": "many2one",
                        "comodel": "test_orm.partner",
                        "default": self.partner_2.id,
                    },
                    {
                        "name": "my_char",
                        "type": "char",
                        "default": "my char",
                        "definition_changed": True,
                    },
                ],
            }
        )
        self.assertEqual(
            self._get_sql_properties(record),
            {"my_char": "my char", "test": self.partner_2.id},
        )

        del property_definition[0]["value"]
        self.discussion_1.attributes_definition = property_definition
        partner = self.env["test_orm.partner"].create({"name": "Test Default"})
        message = (
            self.env["test_orm.message"]
            .with_context({"default_attributes.my_many2one": partner.id})
            .create(
                {
                    "name": "Test Message",
                    "author": self.user.id,
                    "discussion": self.discussion_1.id,
                    "attributes": property_definition,
                }
            )
        )

        sql_values = self._get_sql_properties(message)
        self.assertEqual(sql_values, {"my_many2one": partner.id})
        properties = message.read(["attributes"])[0]["attributes"]
        self.assertEqual(properties[0]["value"], (partner.id, partner.display_name))

        del property_definition[0]["value"]
        message = (
            self.env["test_orm.message"]
            .with_context({"default_attributes.my_many2one": None})
            .create(
                {
                    "name": "Test Message",
                    "author": self.user.id,
                    "discussion": self.discussion_1.id,
                    "attributes": property_definition,
                }
            )
        )

        sql_values = self._get_sql_properties(message)
        self.assertEqual(sql_values, {})
        properties = message.read(["attributes"])[0]["attributes"]
        self.assertNotIn("value", properties[0])

    def test_properties_field_read(self):
        properties_values = (self.message_1 | self.message_3).read(["attributes"])

        self.assertEqual(len(properties_values), 2)

        properties_message_1 = properties_values[0]["attributes"]
        properties_message_3 = properties_values[1]["attributes"]

        self.assertTrue(isinstance(properties_message_1, list))
        self.assertTrue(isinstance(properties_message_3, list))

        self.assertEqual(len(properties_message_1), 2, msg="Message 1 has 2 properties")
        self.assertEqual(len(properties_message_3), 1, msg="Message 3 has 1 property")

        self.assertEqual(
            properties_message_1[0]["name"],
            "discussion_color_code",
            msg='First message 1 property should be "discussion_color_code"',
        )
        self.assertEqual(
            properties_message_1[1]["name"],
            "moderator_partner_id",
            msg='Second message 1 property should be "moderator_partner_id"',
        )
        self.assertEqual(
            properties_message_3[0]["name"],
            "state",
            msg='First message 3 property should be "state"',
        )

        many2one_property = properties_message_1[1]
        self.assertEqual(
            many2one_property["string"],
            "Partner",
            msg="Definition must be present when reading child",
        )
        self.assertEqual(
            many2one_property["type"],
            "many2one",
            msg="Definition must be present when reading child",
        )
        self.assertEqual(
            many2one_property["comodel"],
            "test_orm.partner",
            msg="Definition must be present when reading child",
        )
        self.assertEqual(
            many2one_property["value"],
            (self.partner.id, self.partner.display_name),
        )

    def test_properties_field_html(self):
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

        self.assertEqual(dict(self.message_2.attributes)["test_html"], expected)
        self.assertEqual(self.message_2.attributes["test_html"], expected)

        with self.assertRaises(UserError):
            self.env["test_orm.message"]._read_group([], ["attributes.test_html"])

        with self.assertRaises(UserError):
            self.env["test_orm.message"].web_read_group([], ["attributes.test_html"])

        properties = self.message_2.read(["attributes"])[0]["attributes"]
        self.assertEqual(properties[0]["value"], expected)
        self.assertEqual(properties[0]["default"], expected)

        definition = self.message_2.discussion.attributes_definition
        self.assertEqual(definition[0]["default"], expected)

        definition = self.message_2.discussion.read(["attributes_definition"])[0][
            "attributes_definition"
        ]
        self.assertEqual(definition[0]["default"], expected)

        self.message_2.attributes = {"test_html": xss_payload}
        self.assertEqual(self.message_2.attributes["test_html"], expected)
        properties = self.message_2.read(["attributes"])[0]["attributes"]
        self.assertEqual(properties[0]["value"], expected)

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

        message = (
            self.env["test_orm.message"]
            .with_context(default_attributes_test_html=xss_payload)
            .create({"discussion": self.discussion_1.id})
        )
        self.assertEqual(message.attributes["test_html"], expected)
        sql_values = self._get_sql_properties(message)
        self.assertEqual(sql_values.get("test_html"), expected)

    def test_properties_field_many2one_basic(self):
        self.message_2.attributes = [
            {
                "name": "discussion_color_code",
                "type": "char",
                "string": "Color Code",
                "default": "blue",
                "value": False,
            },
            {
                "name": "moderator_partner_id",
                "type": "many2one",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "value": self.partner_2.id,
            },
        ]

        self.assertFalse(self.message_2.attributes["discussion_color_code"])
        self.assertEqual(
            self.message_2.attributes["moderator_partner_id"], self.partner_2
        )
        sql_values = self._get_sql_properties(self.message_2)
        self.assertEqual(
            sql_values,
            {
                "moderator_partner_id": self.partner_2.id,
                "discussion_color_code": False,
            },
        )

        properties = self.message_2.read(["attributes"])[0]["attributes"]
        self.assertEqual(
            properties[1]["value"],
            (self.partner_2.id, self.partner_2.display_name),
        )
        self.assertEqual(properties[1]["comodel"], "test_orm.partner")

        with self.assertRaises(ValueError):
            self.message_2.attributes = [
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "comodel": "test_orm.transient_model",
                    "definition_changed": True,
                }
            ]
        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "comodel": "test_orm.transient_model",
                }
            ]

    @mute_logger("odoo.models.unlink", "odoo.fields")
    def test_properties_field_many2one_unlink(self):
        self.message_2.attributes = [
            {
                "name": "moderator_partner_id",
                "value": self.partner.id,
            }
        ]

        self.partner.unlink()
        with self.assertQueryCount(2):
            self.assertIs(
                self.message_2.read(["attributes"])[0]["attributes"][0].get("value"),
                None,
            )

        self.message_2.attributes = [
            {
                "name": "moderator_partner_id",
                "value": self.partner_2.id,
            }
        ]
        self.partner_2.unlink()

        with self.assertQueryCount(1):
            value = self.message_2.read(["attributes"])
            value = value[0]["attributes"]
            self.assertFalse(value[1]["value"])
            self.assertEqual(value[1]["comodel"], "test_orm.partner")

        partner = self.env["res.partner"].create({"name": "test unlink"})
        self.message_2.attributes = [
            {
                "name": "moderator_partner_id",
                "type": "many2one",
                "comodel": "res.partner",
                "default": [partner.id, "Bob"],
                "definition_changed": True,
            }
        ]
        self.assertEqual(
            self.message_2.read(["attributes"])[0]["attributes"],
            [
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "comodel": "res.partner",
                    "default": (partner.id, partner.display_name),
                }
            ],
        )
        partner.unlink()
        self.assertEqual(
            self.message_2.read(["attributes"])[0]["attributes"],
            [
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "comodel": "res.partner",
                    "default": False,
                }
            ],
        )

    def test_properties_field_many2one_model_removed(self):
        self.message_1.attributes = [
            {
                "name": "message",
                "value": self.message_3.id,
            }
        ]

        self.env.flush_all()
        self.env.cr.execute(
            """
            UPDATE test_orm_discussion
               SET attributes_definition = '[{"name": "message", "comodel": "wrong_model", "type": "many2one"}]'
             WHERE id = %s
            """,
            (self.discussion_1.id,),
        )
        self.env.invalidate_all()

        values = self.discussion_1.read(["attributes_definition"])[0]
        self.assertFalse(values["attributes_definition"][0]["comodel"])

        attributes_definition = self.discussion_1.attributes_definition
        self.assertEqual(
            attributes_definition,
            [{"name": "message", "comodel": False, "type": "many2one"}],
            msg="The model does not exist anymore, it should return false",
        )

        self.assertFalse(
            self.get_read_dict(self.message_1, "attributes").get("message")
        )

        values = self.message_1.read(["attributes"])[0]["attributes"]
        self.assertEqual(
            values[0]["type"],
            "many2one",
            msg="Property type should be preserved",
        )
        self.assertFalse(values[0]["value"])
        self.assertFalse(values[0]["comodel"])

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [{"name": "message", "comodel": "wrong_model", "type": "many2one"}],
            msg="Do not clean the definition until we write on the field",
        )

        self.discussion_1.attributes_definition = (
            self.discussion_1.attributes_definition
        )

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [{"name": "message", "comodel": False, "type": "many2one"}],
            msg="Should have cleaned the model key",
        )

    def test_properties_field_domain(self):
        self.discussion_1.attributes_definition = [
            {
                "name": "message",
                "comodel": "test_orm.message",
                "type": "many2one",
                "domain": "[('name', 'ilike', 'message')]",
            }
        ]

        domain = self.message_1.read(["attributes"])[0]["attributes"][0]["domain"]
        self.assertEqual(domain, "[('name', 'ilike', 'message')]")

        self.env.flush_all()
        new_properties = json.dumps(
            [
                {
                    "name": "message",
                    "comodel": "test_orm.message",
                    "type": "many2one",
                    "domain": "[('wrong_field', 'ilike', 'test')]",
                }
            ]
        )
        self.env.cr.execute(
            """
            UPDATE test_orm_discussion
               SET attributes_definition = %s
             WHERE id = %s
            """,
            (new_properties, self.discussion_1.id),
        )
        self.env.invalidate_all()

        definition = self.discussion_1.read(["attributes_definition"])[0][
            "attributes_definition"
        ]
        self.assertNotIn("domain", definition)

        properties = self.message_1.read(["attributes"])[0]["attributes"]
        self.assertNotIn("domain", properties)

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertIn(
            "domain",
            sql_definition[0],
            msg="The domain should remain in database until we write on the properties definition",
        )

    def test_properties_field_integer_float_boolean(self):
        self.discussion_1.attributes_definition = [
            {
                "name": "int_value",
                "string": "Int Value",
                "type": "integer",
            },
            {
                "name": "float_value",
                "string": "Float Value",
                "type": "float",
            },
            {
                "name": "boolean_value",
                "string": "Boolean Value",
                "type": "boolean",
            },
        ]

        self.message_1.attributes = [
            {
                "name": "int_value",
                "value": 55555555555,
            },
            {
                "name": "float_value",
                "value": 1.337,
            },
            {
                "name": "boolean_value",
                "value": 77777,
            },
        ]

        self.env.invalidate_all()

        self.assertEqual(
            self.get_read_dict(self.message_1, "attributes"),
            {
                "int_value": 55555555555,
                "float_value": 1.337,
                "boolean_value": True,
            },
        )

        self.message_1.attributes = [{"name": "boolean_value", "value": 0}]
        self.assertEqual(
            self.message_1.attributes["boolean_value"],
            False,
            msg="Boolean value must have been converted to False",
        )

        self.message_1.attributes = {"int_value": 0, "float_value": 0}
        data = self.get_read_dict(self.message_1, "attributes")
        self.assertEqual(
            data,
            {
                "int_value": 0,
                "float_value": 0,
            },
        )
        self.assertEqual(
            self._get_sql_properties(self.message_1),
            {"int_value": 0, "float_value": 0},
        )

        self.message_1.attributes = {
            "int_value": 0,
            "float_value": 0,
            "boolean_value": False,
        }
        data = self.get_read_dict(self.message_1, "attributes")
        self.assertEqual(
            data,
            {
                "int_value": 0,
                "float_value": 0,
                "boolean_value": False,
            },
        )
        self.assertTrue(isinstance(data["int_value"], int))
        self.assertTrue(isinstance(data["float_value"], int))
        self.assertTrue(isinstance(data["boolean_value"], bool))
        self.assertEqual(
            self._get_sql_properties(self.message_1),
            {"int_value": 0, "float_value": 0, "boolean_value": False},
        )

    def test_properties_field_integer_float_falsy_value_edge_cases(self):
        self.discussion_1.attributes_definition = [
            {
                "name": "int_value",
                "string": "Int Value",
                "type": "integer",
                "default": 42,
            },
            {
                "name": "float_value",
                "string": "Float Value",
                "type": "float",
                "default": 0.42,
            },
        ]
        message_1 = self.env["test_orm.message"].create(
            {
                "discussion": self.discussion_1.id,
                "author": self.user.id,
                "attributes": {"int_value": 0, "float_value": 0},
            }
        )

        self.assertEqual(
            message_1.attributes,
            {
                "int_value": 0,
                "float_value": 0,
            },
        )
        self.assertTrue(isinstance(message_1.attributes["int_value"], int))
        self.assertTrue(isinstance(message_1.attributes["float_value"], int))
        self.assertEqual(
            self._get_sql_properties(message_1),
            {"int_value": 0, "float_value": 0},
        )

    def test_properties_field_selection(self):
        self.message_3.attributes = [{"name": "state", "value": "done"}]
        self.env.invalidate_all()
        self.assertEqual(self.message_3.attributes, {"state": "done"})

        self.message_3.attributes = [{"name": "state", "value": "unknown_selection"}]
        self.env.invalidate_all()
        self.assertEqual(
            self.get_read_dict(self.message_3, "attributes"), {"state": False}
        )

        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {
                    "name": "option",
                    "type": "selection",
                    "selection": [["a", "A"], ["b", "B"], ["a", "C"]],
                },
            ]

        self.message_3.attributes = [
            {
                "type": "selection",
                "name": "new_selection",
                "string": "My Selection",
                "definition_changed": True,
            }
        ]
        values = self.message_3.read(["attributes"])[0]["attributes"][0]
        self.assertEqual(values.get("name"), "new_selection")
        self.assertEqual(
            values.get("selection"),
            [],
            "Selection key should be at least an empty array (never False)",
        )

        self.discussion_1.attributes_definition = [
            {
                "name": "option",
                "type": "selection",
                "selection": [["a", "Label"], ["b", "Label"], ["c", "Label"]],
            },
        ]

        (
            self.message_1 | self.message_2 | self.message_3
        ).discussion = self.discussion_1
        (self.message_1 | self.message_2).attributes = [
            {
                "value": "a",
                "name": "option",
            }
        ]
        self.message_3.attributes = [
            {
                "value": "b",
                "name": "option",
            }
        ]
        self.assertEqual(
            (self.message_1 | self.message_2 | self.message_3).filtered_domain(
                [("attributes.option", "=", "b")]
            ),
            self.message_3,
        )
        self.assertEqual(
            (self.message_1 | self.message_2 | self.message_3).filtered_domain(
                [("attributes.option", "=", "a")]
            ),
            self.message_1 | self.message_2,
        )
        self.assertFalse(
            (self.message_1 | self.message_2 | self.message_3).filtered_domain(
                [("attributes.option", "=", "Label")]
            )
        )

    def test_properties_field_separator(self):
        self.message_1.attributes = [
            {
                "name": "boolean_value",
                "value": 0,
                "type": "boolean",
                "definition_changed": True,
            },
            {"type": "separator", "name": "separator", "string": "Group 1"},
            {"name": "int_value", "value": 0, "type": "integer"},
        ]

        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [
                {"name": "boolean_value", "type": "boolean"},
                {"name": "separator", "type": "separator", "string": "Group 1"},
                {"name": "int_value", "type": "integer"},
            ],
        )

        sql_values = self._get_sql_properties(self.message_1)
        self.assertEqual(
            sql_values,
            {"int_value": False, "boolean_value": False},
            msg="Separator should never be stored on the children, only in the definition record",
        )

    def test_properties_field_tags(self):
        self.discussion_1.attributes_definition = [
            {
                "name": "my_tags",
                "string": "My Tags",
                "type": "tags",
                "tags": [
                    ("be", "BE", 1),
                    ("fr", "FR", 2),
                    ("de", "DE", 3),
                    ("it", "IT", 1),
                ],
                "default": ["be", "de"],
            },
        ]
        message = self.env["test_orm.message"].create(
            {"discussion": self.discussion_1.id, "author": self.user.id}
        )

        self.assertEqual(message.attributes, {"my_tags": ["be", "de"]})
        self.assertEqual(self._get_sql_properties(message), {"my_tags": ["be", "de"]})

        self.env.invalidate_all()

        self.discussion_1.attributes_definition = [
            {
                "name": "my_tags",
                "string": "My Tags",
                "type": "tags",
                "tags": [
                    ("be", "BE", 1),
                    ("fr", "FR", 2),
                    ("it", "IT", 1),
                ],
                "default": ["be", "de"],
            },
        ]

        self.assertEqual(self._get_sql_properties(message), {"my_tags": ["be", "de"]})
        attributes = message.read(["attributes"])[0]["attributes"]
        self.assertEqual(
            attributes[0]["value"],
            ["be"],
            msg="The tag has been removed on the definition, should be removed when reading the child",
        )
        self.assertEqual(message.attributes, {"my_tags": ["be", "de"]})

        message.attributes = message.read(["attributes"])[0]["attributes"]

        self.assertEqual(self._get_sql_properties(message), {"my_tags": ["be"]})

        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {
                    "name": "my_tags",
                    "type": "tags",
                    "tags": [
                        ("be", "BE", 1),
                        ("be", "FR", 2),
                    ],
                },
            ]

        self.message_3.attributes = [
            {
                "type": "tags",
                "name": "new_tags",
                "string": "My tags",
                "definition_changed": True,
            }
        ]
        values = self.message_3.read(["attributes"])[0]["attributes"][0]
        self.assertEqual(values.get("name"), "new_tags")
        self.assertEqual(
            values.get("tags"),
            [],
            "Tags key should be at least an empty array (never False)",
        )

    @mute_logger("odoo.models.unlink", "odoo.fields")
    def test_properties_field_many2many_basic(self):
        partners = self.env["test_orm.partner"].create(
            [{"name": f"Partner {i}"} for i in range(20)]
        )

        self.discussion_1.attributes_definition = [
            {
                "name": "moderator_partner_ids",
                "string": "Partners",
                "type": "many2many",
                "comodel": "test_orm.partner",
            }
        ]

        def id_name_pairs(records):
            return list(zip(records._ids, records.mapped("display_name"), strict=False))

        with self.assertQueryCount(3):
            self.message_1.attributes = [
                {
                    "name": "moderator_partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_orm.partner",
                    "value": list(
                        zip(
                            partners[:10]._ids,
                            partners[:10].mapped("display_name"),
                            strict=False,
                        )
                    ),
                },
            ]
            attributes = self.message_1.read(["attributes"])[0]["attributes"]
            self.assertEqual(attributes[0]["value"], id_name_pairs(partners[:10]))

        self.assertIsInstance(hash(self.message_1.attributes), int)

        partners[:5].unlink()
        with self.assertQueryCount(2):
            attributes = self.message_1.read(["attributes"])[0]["attributes"]
            self.assertEqual(attributes[0]["value"], id_name_pairs(partners[5:10]))

        partners[5].unlink()
        with self.assertQueryCount(2):
            properties = self.message_1.read(["attributes"])[0]["attributes"]
        self.assertEqual(properties[0]["value"], id_name_pairs(partners[6:10]))

        attributes = self.message_1.read(["attributes"])[0]["attributes"]
        self.message_1.invalidate_recordset()
        self.message_1.attributes = attributes

        sql_values = self._get_sql_properties(self.message_1)
        self.assertEqual(sql_values, {"moderator_partner_ids": partners[6:10].ids})

        self.env.flush_all()
        moderator_partner_ids = partners[6:10].ids
        moderator_partner_ids += moderator_partner_ids[2:]
        new_value = json.dumps({"moderator_partner_ids": moderator_partner_ids})
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = %s
             WHERE id = %s
            """,
            (new_value, self.message_1.id),
        )
        self.env.invalidate_all()

        properties = self.message_1.read(["attributes"], load=None)[0]["attributes"]
        self.assertEqual(
            properties[0]["value"],
            id_name_pairs(partners[6:10]),
            msg="Should removed duplicated ids",
        )

        self.message_1.attributes = [
            {
                "name": "partner_ids",
                "string": "Partners",
                "type": "many2many",
                "comodel": "test_orm.partner",
                "default": [(partners[8].id, "Alice")],
                "value": [(partners[9].id, "Bob")],
                "definition_changed": True,
            }
        ]
        sql_properties = self._get_sql_properties(self.message_1)
        self.assertEqual(sql_properties, {"partner_ids": [partners[9].id]})
        sql_definition = self._get_sql_definition(self.discussion_1)
        self.assertEqual(
            sql_definition,
            [
                {
                    "name": "partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_orm.partner",
                    "default": [partners[8].id],
                }
            ],
        )

        properties = self.message_1.read(["attributes"])[0]["attributes"]
        self.assertEqual(
            properties,
            [
                {
                    "name": "partner_ids",
                    "string": "Partners",
                    "type": "many2many",
                    "comodel": "test_orm.partner",
                    "default": [(partners[8].id, partners[8].display_name)],
                    "value": [(partners[9].id, partners[9].display_name)],
                }
            ],
        )

        with self.assertRaises(ValueError):
            self.message_2.attributes = [
                {
                    "name": "partner_ids",
                    "type": "many2many",
                    "comodel": "test_orm.transient_model",
                    "definition_changed": True,
                }
            ]
        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {
                    "name": "partner_ids",
                    "type": "many2many",
                    "comodel": "test_orm.transient_model",
                }
            ]

    @users("test")
    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.fields")
    def test_properties_field_many2many_filtering(self):
        tags = self.env["test_orm.multi.tag"].create(
            [{"name": f"Test Tag {i}"} for i in range(10)]
        )

        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": self.discussion_1.id,
                "author": self.user.id,
                "attributes": [
                    {
                        "name": "my_tags",
                        "type": "many2many",
                        "comodel": "test_orm.multi.tag",
                        "value": tags.ids,
                        "definition_changed": True,
                    }
                ],
            }
        )

        self.env["ir.rule"].sudo().create(
            {
                "name": "test_rule_tags",
                "model_id": self.env["ir.model"]._get("test_orm.multi.tag").id,
                "domain_force": [("name", "not in", tags[5:].mapped("name"))],
                "perm_read": True,
                "perm_create": True,
                "perm_write": True,
            }
        )

        self.env.invalidate_all()

        values = message.read(["attributes"])[0]["attributes"][0]["value"]
        self.assertEqual(
            values,
            [
                (tag.id, None if i >= 5 else tag.name)
                for i, tag in enumerate(tags.sudo())
            ],
        )

        self.assertEqual(message["attributes"]["my_tags"], tags)

    def test_properties_field_performance(self):
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.message_1.read(["attributes"])

        with self.assertQueryCount(0, msg="Must read value from cache"):
            self.message_1.attributes

        expected = [
            """
            UPDATE "test_orm_message"
            SET "attributes" = "__tmp"."attributes"::jsonb,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES (%s)) AS "__tmp"("id", "attributes", "write_date", "write_uid")
            WHERE "test_orm_message"."id" = "__tmp"."id"
        """
        ]
        with self.assertQueryCount(1), self.assertQueries(expected):
            self.message_1.attributes = [
                {
                    "name": "discussion_color_code",
                    "type": "char",
                    "string": "Color Code",
                    "default": "blue",
                    "value": "red",
                },
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "string": "Partner",
                    "comodel": "test_orm.partner",
                    "value": None,
                },
            ]
            self.message_1.flush_recordset()

        last_message_id = (
            self.env["test_orm.message"].search([], order="id DESC", limit=1).id
        )
        values = (
            self.env["test_orm.message"]
            .browse((self.message_1.id, last_message_id + 1))
            ._read_format(["attributes"])
        )
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["id"], self.message_1.id)

    def test_properties_field_change_definition(self):

        attributes_definition = self.discussion_1.attributes_definition
        self.message_1.attributes = [
            {
                "name": "discussion_color_code",
                "value": None,
            },
            {
                "name": "moderator_partner_id",
                "value": None,
            },
        ]
        self.env.invalidate_all()
        self.assertEqual(self.get_read_dict(self.message_1, "attributes"), {})

        attributes_definition += [{"name": "state", "string": "State", "type": "char"}]
        self.discussion_1.attributes_definition = attributes_definition
        self.message_1.attributes = [{"name": "state", "value": "ready"}]

        self.env.invalidate_all()

        self.assertEqual(
            self.get_read_dict(self.message_1, "attributes"), {"state": "ready"}
        )

        self.discussion_1.attributes_definition = attributes_definition[:-1]

        self.assertEqual(
            self.message_1.attributes,
            {
                "state": "ready",
            },
        )

        value = self._get_sql_properties(self.message_1)
        self.assertEqual(
            value.get("state"), "ready", msg="The field should be in database"
        )

        self.message_1.attributes = [{"name": "name", "value": "Test name"}]
        value = self._get_sql_properties(self.message_1)
        self.assertFalse(
            value.get("state"),
            msg="After updating an other property, the value must be cleaned",
        )

        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {"name": "state", "type": "wrong_type"}
            ]

        with self.assertRaises(ValueError):
            self.discussion_1.attributes_definition = [
                {"name": "state", "type": "char"},
                {"name": "state", "type": "datetime"},
            ]

    @mute_logger("odoo.fields")
    def test_properties_field_onchange2(self):
        message_form = Form(self.env["test_orm.message"])

        with self.assertQueryCount(8):
            message_form.discussion = self.discussion_1
            message_form.author = self.user

            self.assertEqual(
                message_form.attributes,
                [
                    {
                        "name": "discussion_color_code",
                        "string": "Color Code",
                        "type": "char",
                        "default": "blue",
                        "value": "blue",
                    },
                    {
                        "name": "moderator_partner_id",
                        "string": "Partner",
                        "type": "many2one",
                        "comodel": "test_orm.partner",
                    },
                ],
                msg="Should take the new definition when changing the definition record",
            )

            message_form.discussion = self.discussion_2

            properties = message_form.attributes

            self.assertEqual(len(properties), 1)
            self.assertEqual(
                properties[0]["name"],
                "state",
                msg="Should take the values of the new definition record",
            )

        with self.assertQueryCount(6):
            message = message_form.save()

        self.assertEqual(message.attributes, {"state": "draft"})

        cached_value = self.env.core.get_value(
            message._fields["attributes"], message.id
        )
        self.assertEqual(cached_value, {"state": "draft"})

        self.assertEqual(message.discussion, self.discussion_2)

        with self.assertQueryCount(4):
            message.discussion = self.discussion_1
        self.assertEqual(
            self.discussion_1.attributes_definition,
            [
                {
                    "name": "discussion_color_code",
                    "type": "char",
                    "string": "Color Code",
                    "default": "blue",
                },
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "string": "Partner",
                    "comodel": "test_orm.partner",
                },
            ],
        )
        self.assertEqual(
            message.read()[0]["attributes"],
            [
                {
                    "name": "discussion_color_code",
                    "type": "char",
                    "string": "Color Code",
                    "default": "blue",
                    "value": "blue",
                },
                {
                    "name": "moderator_partner_id",
                    "type": "many2one",
                    "string": "Partner",
                    "comodel": "test_orm.partner",
                },
            ],
        )

        self.discussion_1.attributes_definition = False
        self.discussion_2.attributes_definition = [
            {
                "name": "test",
                "type": "char",
                "default": "Default",
            }
        ]

        message.discussion = self.discussion_2
        message.attributes = [{"name": "test", "value": "Test"}]
        fields_spec = message._get_fields_spec()
        self.assertIn("discussion", fields_spec)
        self.assertIn("attributes", fields_spec)
        values = {
            "discussion": self.discussion_1.id,
            "attributes": [
                {
                    "name": "test",
                    "type": "char",
                    "default": "Default",
                    "value": "Test",
                }
            ],
        }
        result = message.onchange(values, ["discussion"], fields_spec)
        self.assertIn(
            "attributes",
            result["value"],
            "Should have detected the definition record change",
        )
        self.assertEqual(
            result["value"]["attributes"],
            [],
            "Should have reset the properties definition",
        )

        message.discussion = self.discussion_1
        values = {
            "discussion": self.discussion_2.id,
            "attributes": [],
        }
        result = message.onchange(values, ["discussion"], fields_spec)
        self.assertIn(
            "attributes",
            result["value"],
            "Should have detected the definition record change",
        )
        self.assertEqual(
            result["value"]["attributes"],
            [
                {
                    "name": "test",
                    "type": "char",
                    "default": "Default",
                    "value": "Default",
                }
            ],
            "Should have reset the properties definition to the discussion 1 definition",
        )

        message_form = Form(message)
        message_form.discussion = self.discussion_2
        message_form.attributes = [
            {
                "name": "new_property",
                "type": "char",
                "value": "test value",
                "definition_changed": True,
            }
        ]
        message = message_form.save()
        self.assertEqual(
            self.discussion_2.attributes_definition,
            [{"name": "new_property", "type": "char"}],
        )
        self.assertEqual(message.attributes, {"new_property": "test value"})

        message.discussion = message.discussion
        self.assertEqual(message.attributes, {"new_property": "test value"})

        message.discussion.attributes_definition = []
        message_form = Form(message)
        message.attributes = [
            {
                "name": "new_property",
                "type": "char",
                "value": "test value",
                "definition_changed": True,
            }
        ]
        message_form.body = "a" * 42
        message = message_form.save()
        self.assertEqual(message.attributes, {"new_property": "test value"})

    @mute_logger("odoo.fields")
    def test_properties_field_definition_update(self):
        self.discussion_1.attributes_definition = []

        self.message_1.attributes = [
            {
                "name": "my_many2one",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "type": "many2one",
                "default": [self.partner.id, "Bob"],
                "value": [self.partner_2.id, "Test"],
            },
            {
                "name": "my_many2many",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "type": "many2many",
                "default": [
                    [self.partner.id, "Bob"],
                    [self.partner_2.id, "Test"],
                ],
                "value": [[self.partner_2.id, "Test"]],
                "definition_changed": True,
            },
        ]
        self.env.invalidate_all()

        sql_definition = self._get_sql_definition(self.discussion_1)
        expected_definition = [
            {
                "name": "my_many2one",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "type": "many2one",
                "default": self.partner.id,
            },
            {
                "name": "my_many2many",
                "string": "Partner",
                "comodel": "test_orm.partner",
                "type": "many2many",
                "default": [self.partner.id, self.partner_2.id],
            },
        ]
        self.assertEqual(sql_definition, expected_definition)

        sql_properties = self._get_sql_properties(self.message_1)
        expected_properties = {
            "my_many2one": self.partner_2.id,
            "my_many2many": [self.partner_2.id],
        }
        self.assertEqual(expected_properties, sql_properties)

    @mute_logger("odoo.fields")
    @users("test")
    def test_properties_field_security(self):

        def _mocked_check_access(records, operation):
            if records.env.su:
                return
            msg = ""
            raise AccessError(msg)

        message = self.message_1.with_user(self.test_user)

        tag = self.env["test_orm.multi.tag"].create({"name": "Test Tag"})

        message.attributes = [
            {
                "name": "test",
                "type": "many2one",
                "comodel": "test_orm.multi.tag",
                "value": [tag.id, "Tag"],
                "definition_changed": True,
            }
        ]
        values = message.read(["attributes"])[0]["attributes"][0]
        self.assertEqual(values["value"], (tag.id, "Test Tag"))
        self.env.invalidate_all()
        with patch(
            "odoo.addons.test_orm.models.test_orm.TestOrmMultiTag.check_access",
            _mocked_check_access,
        ):
            values = message.read(["attributes"])[0]["attributes"][0]
        self.assertEqual(values["value"], (tag.id, None))

        self.env.invalidate_all()
        with patch(
            "odoo.addons.test_orm.models.test_orm.TestOrmDiscussion.check_access",
            _mocked_check_access,
        ):
            values = message.read(["attributes"])[0]["attributes"][0]
        self.assertEqual(values["value"], (tag.id, "Test Tag"))

    @users("test")
    def test_properties_field_update_parent(self):
        self.env["ir.rule"].sudo().create(
            {
                "name": "only discussion_1",
                "model_id": self.env["ir.model"]._get("test_orm.message").id,
                "domain_force": [("discussion", "=", self.discussion_1.id)],
            }
        )

        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": self.discussion_1.id,
                "author": self.user.id,
            }
        )
        self.env.invalidate_all()

        message.discussion = self.discussion_2
        self.env.flush_all()
        self.assertEqual(message.attributes, {"state": "draft"})

    @users("test")
    def test_properties_field_no_parent_access(self):

        def _mocked_check_access(records, operation):
            if records.env.su:
                return
            msg = ""
            raise AccessError(msg)

        self.env.invalidate_all()
        with patch(
            "odoo.addons.test_orm.models.test_orm.TestOrmDiscussion.check_access",
            _mocked_check_access,
        ):
            message = self.env["test_orm.message"].create(
                {
                    "name": "Test Message",
                    "discussion": self.discussion_1.id,
                    "author": self.user.id,
                    "attributes": {
                        "moderator_partner_id": self.partner.id,
                    },
                }
            )
            self.assertEqual(
                message.attributes,
                {
                    "discussion_color_code": "blue",
                    "moderator_partner_id": self.partner.id,
                },
            )

    def test_properties_inherits(self):
        email = self.env["test_orm.emailmessage"].create(
            {
                "discussion": self.discussion_1.id,
                "attributes": [
                    {
                        "name": "discussion_color_code",
                        "type": "char",
                        "string": "Color Code",
                        "default": "blue",
                        "value": "red",
                    }
                ],
            }
        )
        email.invalidate_recordset()

        values = email.read(["attributes"])
        self.assertEqual(values[0]["attributes"][0]["value"], "red")
        values = email.message.read(["attributes"])
        self.assertEqual(values[0]["attributes"][0]["value"], "red")

    def test_properties_server_action_path_traversal(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "TestAction",
                "model_id": self.env["ir.model"]
                .search(
                    [
                        ("model", "=", "test_orm.emailmessage"),
                    ]
                )
                .id,
                "model_name": "test_orm.emailmessage",
                "state": "object_write",
            }
        )
        with self.assertRaises(ValidationError) as ve:
            action.update_path = "attributes.discussion_color_code"
        self.assertEqual(
            ve.exception.args[0],
            "The path in field 'Field to Update Path' contains a non-relational "
            "field (Discussion Properties) that is not the last segment. Only the "
            "last field in a path may be non-relational.",
        )

    def test_getitem_property(self):
        with self.assertRaises(KeyError):
            self.message_3["attributes"]["____"]

        with self.assertRaises(KeyError):
            self.message_3["attributes"]["moderator_partner_id"]

        self.assertEqual(self.message_1["attributes"]["discussion_color_code"], "Test")
        self.assertEqual(
            self.message_1["attributes"]["moderator_partner_id"], self.partner
        )

        self.assertEqual(self.message_2["attributes"]["discussion_color_code"], "blue")
        self.assertEqual(
            self.message_2["attributes"]["moderator_partner_id"],
            self.env["test_orm.partner"],
        )

        with self.assertRaises(KeyError):
            self.message_1["attributes"]["state"]
        with self.assertRaises(KeyError):
            self.message_2["attributes"]["state"]
        self.assertEqual(self.message_3["attributes"]["state"], "Draft")

        self.message_1.attributes = [
            {
                "name": "tags",
                "type": "tags",
                "tags": [["a", "A", 0], ["b", "B", 1], ["c", "C", 2]],
                "value": ["a", "b", "e"],
                "definition_changed": True,
            }
        ]
        self.assertEqual(self.message_1["attributes"]["tags"], "A, B")
        self.assertEqual(self.message_2["attributes"]["tags"], False)
        with self.assertRaises(KeyError):
            self.message_3["attributes"]["tags"]

        self.message_1.attributes = [
            {
                "name": "many2many",
                "type": "many2many",
                "comodel": "test_orm.partner",
                "value": (self.partner | self.partner_2).ids,
                "definition_changed": True,
            }
        ]
        self.assertEqual(
            self.message_1["attributes"]["many2many"],
            self.partner | self.partner_2,
        )
        self.assertEqual(
            self.message_2["attributes"]["many2many"],
            self.env["test_orm.partner"],
        )
        with self.assertRaises(KeyError):
            self.message_3["attributes"]["many2many"]

        self.message_1.attributes = [
            {
                "name": "many2many",
                "type": "many2many",
                "value": (self.partner | self.partner_2).ids,
                "definition_changed": True,
            }
        ]
        self.assertEqual(self.message_1["attributes"]["many2many"], False)
        self.assertEqual(self.message_2["attributes"]["many2many"], False)
        with self.assertRaises(KeyError):
            self.message_3["attributes"]["many2many"]

        self.assertEqual(self.env["test_orm.message"]["attributes"]["many2many"], False)

        partner_3 = self.env["test_orm.partner"].create({})
        self.message_1.attributes = [
            {
                "name": "many2many",
                "comodel": "test_orm.partner",
                "type": "many2many",
                "value": self.partner.ids,
                "default": partner_3.ids,
                "definition_changed": True,
            }
        ]
        self.message_2["attributes"] = [
            {
                "name": "many2many",
                "comodel": "test_orm.partner",
                "type": "many2many",
                "value": self.partner_2.ids,
            }
        ]
        messages = self.message_1 | self.message_2 | self.message_3
        self.env.invalidate_all()

        with self.assertQueryCount(5):
            messages[0]["attributes"]["many2many"]
            messages[1]["attributes"]["many2many"]


class PropertiesSearchCase(TransactionExpressionCase, TestPropertiesMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.messages = cls.message_1 | cls.message_2 | cls.message_3
        cls.env["test_orm.message"].search(
            [("id", "not in", cls.messages.ids)]
        ).unlink()

    def test_properties_field_search_boolean(self):
        self.message_1.attributes = [
            {
                "name": "myboolean",
                "type": "boolean",
                "value": True,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myboolean": False}
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myboolean", "=", True)]
        )
        self.assertEqual(messages, self.message_1)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.myboolean", "!=", False)],
        )
        self.assertEqual(messages, self.message_1)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myboolean", "=", False)]
        )
        self.assertEqual(messages, self.message_2 | self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myboolean", "!=", True)]
        )
        self.assertEqual(messages, self.message_2 | self.message_3)

    def test_properties_field_search_char(self):
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "Test",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mychar": "TeSt"}

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "=", "Test")]
        )
        self.assertEqual(
            messages,
            self.message_1,
            "Should be able to search on a properties field",
        )
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "=", '"Test"')]
        )
        self.assertFalse(messages)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mychar", "ilike", "test")],
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mychar", "not ilike", "test")],
        )
        self.assertEqual(messages, self.message_3)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mychar", "ilike", '"test"')],
        )
        self.assertFalse(messages)

        for forbidden_char in "! ()\"'.":
            searches = (
                f"mychar{forbidden_char}",
                f"my{forbidden_char}char",
                f"{forbidden_char}mychar",
            )
            for search in searches:
                with self.assertRaises(ValueError), self.assertQueryCount(0):
                    self.env["test_orm.message"].search(
                        [(f"attributes.{search}", "=", "Test")]
                    )

        self.message_3.discussion = self.message_2.discussion
        self.message_3.attributes = [{"name": "mychar", "value": False}]
        self.assertEqual(self._get_sql_properties(self.message_3), {"mychar": False})
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "=", False)]
        )
        self.assertEqual(messages, self.message_3)

        self.message_2.attributes = [{"name": "mychar", "value": False}]
        self.env.cr.execute(
            "UPDATE test_orm_message SET attributes = '{}' WHERE id = %s",
            [self.message_3.id],
        )
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "=", False)]
        )
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "!=", False)]
        )
        self.assertEqual(messages, self.message_1)

        messages = self.env["test_orm.message"].search(
            [("attributes.mychar", "!=", True)]
        )
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self.env["test_orm.message"].search(
            [("attributes.mychar", "=", True)]
        )
        self.assertEqual(messages, self.message_1)

        self.env.cr.execute(
            "UPDATE test_orm_message SET attributes = NULL WHERE id = %s",
            [self.message_3.id],
        )

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "=", False)]
        )
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mychar", "!=", False)]
        )
        self.assertEqual(messages, self.message_1)

    def test_properties_field_search_unset_values(self):
        # an unset property is stored as json false; ->> renders it as the
        # text 'false' and jsonb orders a boolean above every number
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "false",
                "definition_changed": True,
            },
            {
                "name": "myint",
                "type": "integer",
                "value": 3,
                "definition_changed": True,
            },
        ]
        self.message_2.attributes = {"mychar": False, "myint": 0}
        self.message_3.attributes = {"mychar": False, "myint": False}
        Message = self.env["test_orm.message"]

        for domain, expected in [
            ([("attributes.mychar", "ilike", "als")], self.message_1),
            ([("attributes.mychar", "like", "a")], self.message_1),
            ([("attributes.mychar", "=", "false")], self.message_1),
            ([("attributes.mychar", "!=", "false")], self.message_2 | self.message_3),
            ([("attributes.mychar", "<", "g")], self.message_1),
            ([("attributes.mychar", ">=", "")], self.message_1),
            ([("attributes.myint", "=", 0)], self.message_2),
            ([("attributes.myint", "=", False)], self.message_3),
            ([("attributes.myint", "in", [0, 3])], self.message_1 | self.message_2),
            ([("attributes.myint", "!=", 3)], self.message_2 | self.message_3),
            ([("attributes.myint", "!=", 7)], self.messages),
            ([("attributes.myint", ">", 2)], self.message_1),
            ([("attributes.myint", ">", -1)], self.message_1 | self.message_2),
            ([("attributes.myint", "<=", 0)], self.message_2),
        ]:
            with self.subTest(domain=domain):
                self.assertEqual(self._search(Message, domain), expected)

        self.env.cr.execute(
            "UPDATE test_orm_message SET attributes = NULL WHERE id = %s",
            [self.message_3.id],
        )
        self.assertEqual(
            self._search(Message, [("attributes.mychar", "!=", "false")]),
            self.message_2 | self.message_3,
        )
        self.assertEqual(
            self._search(Message, [("attributes.myint", "=", False)]),
            self.message_3,
        )

    def test_properties_field_search_float(self):
        self.message_1.attributes = [
            {
                "name": "myfloat",
                "type": "float",
                "value": 3.14,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myfloat": 5.55}
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myfloat", ">", 4.4)]
        )
        self.assertEqual(messages, self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myfloat", "<", 4.4)]
        )
        self.assertEqual(messages, self.message_1)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myfloat", ">", 1.1)]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myfloat", "<=", 1.1)]
        )
        self.assertFalse(messages)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myfloat", "=", 3.14)]
        )
        self.assertEqual(messages, self.message_1)

    def test_properties_field_search_date_relative(self):
        self.message_1.attributes = [
            {
                "name": "mydate",
                "type": "date",
                "value": "2020-01-01",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mydate": "2099-12-31"}
        Message = self.env["test_orm.message"]

        past = self._search(Message, [("attributes.mydate", "<", "today")])
        self.assertEqual(past, self.message_1)
        future = self._search(Message, [("attributes.mydate", ">", "today")])
        self.assertEqual(future, self.message_2)
        both = self._search(Message, [("attributes.mydate", "<", "2100-01-01")])
        self.assertEqual(both, self.message_1 | self.message_2)

    def test_properties_field_search_integer(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "myint",
                "type": "integer",
                "value": 33,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myint": 111}
        self.message_3.attributes = {"myint": -2}

        messages = self._search(
            self.env["test_orm.message"], [("attributes.myint", ">", 4)]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myint", "<", 4)]
        )
        self.assertEqual(messages, self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myint", "=", 111)]
        )
        self.assertEqual(messages, self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.myint", "ilike", "1")]
        )
        self.assertEqual(messages, self.message_2)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.myint", "not ilike", "1")],
        )
        self.assertEqual(messages, self.message_1 | self.message_3)

    def test_properties_field_search_many2many(self):
        self.messages.discussion = self.discussion_1
        partners = self.env["res.partner"].create(
            [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        )
        self.message_1.attributes = [
            {
                "name": "mymany2many",
                "type": "many2many",
                "comodel": "res.partner",
                "value": partners.ids,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mymany2many": [partners[1].id]}
        self.message_3.attributes = {"mymany2many": [partners[2].id]}

        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mymany2many", "in", partners[0].ids)],
        )
        self.assertEqual(messages, self.message_1)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mymany2many", "in", partners[1].ids)],
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mymany2many", "in", partners[2].ids)],
        )
        self.assertEqual(messages, self.message_1 | self.message_3)
        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mymany2many", "not in", partners[0].ids)],
        )
        self.assertEqual(messages, self.message_2 | self.message_3)

        messages = self._search(
            self.env["test_orm.message"],
            [("attributes.mymany2many", "in", partners[0:2].ids)],
        )
        self.assertEqual(messages, self.message_1 | self.message_2)

    def test_properties_field_search_many2one(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mypartner",
                "type": "many2one",
                "comodel": "res.partner",
                "value": self.partner.id,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mypartner": self.partner_2.id}
        self.message_3.attributes = {"mypartner": False}

        Message = self.env["test_orm.message"]
        messages = Message.search(
            [
                (
                    "attributes.mypartner",
                    "in",
                    [self.partner.id, self.partner_2.id],
                )
            ]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)

        messages = Message.search(
            [
                (
                    "attributes.mypartner",
                    "not in",
                    [self.partner.id, self.partner_2.id],
                )
            ]
        )
        self.assertEqual(messages, self.message_3)

        messages = Message.search(
            [("attributes.mypartner", "ilike", self.partner.display_name)]
        )
        self.assertFalse(
            messages, "The ilike on relational properties is not supported"
        )

    def test_properties_field_search_tags(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mytags",
                "type": "tags",
                "value": ["a", "b"],
                "tags": [["a", "A", 1], ["b", "B", 2], ["aa", "AA", 3]],
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mytags": ["b"]}
        self.message_3.attributes = {"mytags": ["aa"]}

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", "a")]
        )
        self.assertEqual(messages, self.message_1)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "ilike", "a")]
        )
        self.assertEqual(messages, self.message_1 | self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "not ilike", "a")]
        )
        self.assertEqual(messages, self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", "b")]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", "aa")]
        )
        self.assertEqual(messages, self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "not in", "b")]
        )
        self.assertEqual(messages, self.message_3)
        messages = self.env["test_orm.message"].search(
            [("attributes.mytags", "ilike", '["aa"]')]
        )
        self.assertEqual(messages, self.message_3)

        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", [])]
        )
        self.assertFalse(messages)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "not in", [])]
        )
        self.assertEqual(messages, self.message_1 | self.message_2 | self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", ["a", "b"])]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", ["b", "a"])]
        )
        self.assertEqual(messages, self.message_1 | self.message_2)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", ["aa"])]
        )
        self.assertEqual(messages, self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "in", ["aa", "b"])]
        )
        self.assertEqual(messages, self.message_1 | self.message_2 | self.message_3)
        messages = self._search(
            self.env["test_orm.message"], [("attributes.mytags", "not in", ["a", "b"])]
        )
        self.assertEqual(messages, self.message_3)

    def test_properties_field_search_unaccent(self):
        if not self.registry.has_unaccent:
            msg = "unaccent not enabled"
            raise unittest.SkipTest(msg)

        Model = self.env["test_orm.message"]
        (self.message_1 | self.message_2).discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "Hélène",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mychar": "Helene"}

        result = self._search(Model, [("attributes.mychar", "ilike", "Helene")])
        self.assertEqual(self.message_1 | self.message_2, result)

        result = self._search(Model, [("attributes.mychar", "ilike", "hélène")])
        self.assertEqual(self.message_1 | self.message_2, result)

        result = self._search(Model, [("attributes.mychar", "=ilike", "hél%")])
        self.assertEqual(self.message_1 | self.message_2, result)

        result = self._search(Model, [("attributes.mychar", "not ilike", "Helene")])
        self.assertNotIn(self.message_1, result)
        self.assertNotIn(self.message_2, result)

        result = self._search(Model, [("attributes.mychar", "not ilike", "hélène")])
        self.assertNotIn(self.message_1, result)
        self.assertNotIn(self.message_2, result)

        result = self._search(Model, [("attributes.mychar", "not ilike", "")])
        self.assertFalse(result)

    def test_properties_field_search_orderby_string(self):
        (
            self.message_1 | self.message_2 | self.message_3
        ).discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "BB",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mychar": "AA"}
        self.message_3.attributes = {"mychar": "CC"}

        result = self.env["test_orm.message"].search(
            domain=[["attributes.mychar", "!=", False]],
            order="attributes.mychar ASC",
        )
        self.assertEqual(result[0], self.message_2)
        self.assertEqual(result[1], self.message_1)
        self.assertEqual(result[2], self.message_3)

        result = self.env["test_orm.message"].search(
            domain=[["attributes.mychar", "!=", False]],
            order="attributes.mychar DESC",
        )
        self.assertEqual(result[0], self.message_3)
        self.assertEqual(result[1], self.message_1)
        self.assertEqual(result[2], self.message_2)

    def test_properties_field_search_order_integer(self):
        (
            self.message_1 | self.message_2 | self.message_3
        ).discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "myinteger",
                "type": "integer",
                "value": 22,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myinteger": 111}
        self.message_3.attributes = {"myinteger": 33}

        result = self.env["test_orm.message"].search(
            domain=[["attributes.myinteger", "!=", False]],
            order="attributes.myinteger ASC",
        )
        self.assertEqual(result[0], self.message_1)
        self.assertEqual(result[1], self.message_3)
        self.assertEqual(result[2], self.message_2)

        result = self.env["test_orm.message"].search(
            domain=[["attributes.myinteger", "!=", False]],
            order="attributes.myinteger DESC",
        )
        self.assertEqual(result[0], self.message_2)
        self.assertEqual(result[1], self.message_3)
        self.assertEqual(result[2], self.message_1)

    def test_properties_field_search_order_injection(self):
        self.message_1.attributes = [
            {
                "name": "myinteger",
                "type": "integer",
                "value": 22,
                "definition_changed": True,
            }
        ]

        for c in "! ()\"'.":
            orders = (
                f"attributes.myinteger{c} ASC",
                f"attributes.my{c}integer ASC",
                f"attribut{c}es.myinteger ASC",
            )

            if c == " ":
                orders = orders[1:]

            for order in orders:
                with self.assertRaises(UserError), self.assertQueryCount(0):
                    self.env["test_orm.message"].search(domain=[], order=order)

    def test_properties_field_search(self):
        with self.assertRaises(ValueError):
            self.env["test_orm.message"].search([("attributes", "=", '"Test"')])

    def test_properties_field_search_read_false(self):
        Model = self.env["test_orm.message"]

        discussion = self.env["test_orm.discussion"].create(
            {
                "name": "Test Discussion",
                "participants": [Command.link(self.user.id)],
            }
        )

        message = self.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": discussion.id,
                "author": self.user.id,
            }
        )

        discussion.attributes_definition = [
            {
                "name": "discussion_test",
                "string": "Discussion Test",
                "type": "char",
            }
        ]

        message_values = Model.search_read([("id", "=", message.id)])
        self.assertNotIn(
            "value",
            message_values[0]["attributes"][0],
            "Value should not be set",
        )


class PropertiesGroupByCase(TestPropertiesMixin):
    def setUp(self):
        super().setUp()
        model_cls = type(self.env["base"])
        original = model_cls.web_read_group

        def _strip_version(records, *args, **kwargs):
            result = original(records, *args, **kwargs)
            if isinstance(result, dict):
                result.pop("__version", None)
            return result

        patcher = patch.object(model_cls, "web_read_group", _strip_version)
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_4 = cls.env["test_orm.message"].create(
            {
                "name": "Test Message",
                "discussion": cls.discussion_1.id,
                "author": cls.user.id,
            }
        )

        cls.messages = cls.message_1 | cls.message_2 | cls.message_3 | cls.message_4
        cls.env["test_orm.message"].search(
            [("id", "not in", cls.messages.ids)]
        ).unlink()

        cls.wrong_discussion_id = (
            cls.env["test_orm.discussion"].search([], order="id DESC", limit=1).id
            + 1000
        )

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_basic(self):
        Model = self.env["test_orm.message"]

        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "qsd",
                "definition_changed": True,
            },
            {
                "name": "myinteger",
                "type": "integer",
                "value": 1337,
                "definition_changed": True,
            },
        ]
        self.message_2.attributes = {"mychar": "qsd", "myinteger": 5}
        self.message_3.attributes = {"mychar": "boum", "myinteger": 1337}

        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.mychar"],
            )

        self.assertEqual(len(result), 3)

        count_by_values = {
            value["attributes.mychar"]: value["__count"] for value in result
        }
        self.assertEqual(count_by_values["boum"], 1)
        self.assertEqual(count_by_values["qsd"], 2)
        self.assertEqual(count_by_values[False], 1)

        domain_by_values = {
            value["attributes.mychar"]: value["__extra_domain"] for value in result
        }
        self.assertEqual(domain_by_values["boum"], [("attributes.mychar", "=", "boum")])
        self.assertEqual(domain_by_values["qsd"], [("attributes.mychar", "=", "qsd")])
        self._check_domains_count(result)

        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.myinteger"],
            )

        self.assertEqual(len(result), 3)
        count_by_values = {
            value["attributes.myinteger"]: value["__count"] for value in result
        }

        self.assertEqual(count_by_values[5], 1)
        self.assertEqual(count_by_values[1337], 2)
        self.assertEqual(count_by_values[False], 1)

        self.message_3.attributes = {"mychar": False, "myinteger": False}
        with self.assertQueryCount(3):
            result = Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.myinteger"],
            )

        self.assertEqual(result[-1]["__count"], 2)
        self.assertEqual(
            result[-1]["__extra_domain"], [("attributes.myinteger", "=", False)]
        )
        self._check_domains_count(result)

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
                aggregates=["__count"],
                groupby=["attributes.myinteger"],
            )

        self.assertEqual(result[-1]["__count"], 3)
        self.assertEqual(
            result[-1]["__extra_domain"], [("attributes.myinteger", "=", False)]
        )
        result = Model.search(result[-1]["__extra_domain"])
        self.assertEqual(result, self.message_2 | self.message_3 | self.message_4)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.myinteger"],
            order="attributes.myinteger ASC",
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["attributes.myinteger"], 1337)
        self.assertEqual(result[1]["attributes.myinteger"], False)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.myinteger"],
            order="attributes.myinteger DESC",
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["attributes.myinteger"], False)
        self.assertEqual(result[1]["attributes.myinteger"], 1337)
        self._check_domains_count(result)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.myinteger", "name"],
            order="attributes.myinteger DESC",
        )
        self.assertEqual(
            result[0]["__extra_domain"],
            [
                "&",
                ("attributes.myinteger", "=", False),
                ("name", "=", self.message_1.name),
            ],
        )
        self._check_domains_count(result)

    def test_properties_field_web_read_group(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mychar",
                "type": "char",
                "value": "qsd",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mychar": "qsd"}
        self.message_3.attributes = {"mychar": "boum"}

        Model = self.env["test_orm.message"]
        with self.assertQueryCount(7):
            result = Model.web_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.mychar"],
                auto_unfold=True,
                unfold_read_specification={"id": {}},
            )
        groups = result["groups"]

        self.assertEqual(len(groups), 3)

        count_by_values = {
            value["attributes.mychar"]: value["__count"] for value in groups
        }
        self.assertEqual(count_by_values["boum"], 1)
        self.assertEqual(count_by_values["qsd"], 2)
        self.assertEqual(count_by_values[False], 1)

        domain_by_values = {
            value["attributes.mychar"]: value["__extra_domain"] for value in groups
        }
        self.assertEqual(domain_by_values["boum"], [("attributes.mychar", "=", "boum")])
        self.assertEqual(domain_by_values["qsd"], [("attributes.mychar", "=", "qsd")])
        self._check_domains_count(groups)

        self.assertEqual(groups[0]["__records"], [{"id": self.message_3.id}])
        self.assertEqual(
            groups[1]["__records"],
            [{"id": self.message_1.id}, {"id": self.message_2.id}],
        )
        self.assertEqual(groups[2]["__records"], [{"id": self.message_4.id}])

    def test_properties_tags_field_web_read_group(self):
        self.discussion_1.attributes_definition = [
            {
                "name": "my_tags",
                "string": "My Tags",
                "type": "tags",
                "tags": [
                    ("be", "BE", 1),
                    ("it", "IT", 2),
                ],
                "default": ["be"],
            },
        ]
        self.env["test_orm.message"].create(
            {"discussion": self.discussion_1.id, "author": self.user.id}
        )

        self.env.flush_all()
        result = self.env["test_orm.message"].web_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.my_tags"],
            opening_info=[{"folded": True, "value": "1"}],
            unfold_read_specification={"id": {}},
        )

        self.assertEqual(len(result["groups"]), 2)
        self.assertEqual(result["groups"][0]["attributes.my_tags"], ("be", "BE", 1))
        self.assertEqual(result["groups"][1]["attributes.my_tags"], False)

    @mute_logger("odoo.fields")
    def test_properties_field_read_progress_bar(self):
        Model = self.env["test_orm.message"]

        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "myinteger",
                "type": "integer",
                "value": 1337,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myinteger": 5}
        self.message_3.attributes = {"myinteger": 1337}

        result = Model.read_progress_bar(
            domain=[],
            group_by="attributes.myinteger",
            progress_bar={"field": "priority", "colors": [0]},
        )
        self.assertEqual(result, {"1337": {0: 2}, "5": {0: 1}, "False": {0: 1}})

    def _properties_field_read_group_date_prepare(self, date_type="date"):
        self.messages.discussion = self.discussion_1
        self.discussion_1.attributes_definition = [
            {
                "type": date_type,
                "name": "mydate",
            }
        ]
        hour = " 13:05:34" if date_type == "datetime" else ""
        self.message_5, self.message_6, self.message_7 = self.env[
            "test_orm.message"
        ].create(
            [
                {
                    "discussion": self.discussion_1.id,
                    "attributes": {"mydate": f"2077-05-02{hour}"},
                },
                {
                    "discussion": self.discussion_1.id,
                    "attributes": {"mydate": False},
                },
                {"discussion": self.discussion_2.id},
            ]
        )
        self.message_1.attributes = {"mydate": f"2023-01-02{hour}"}
        self.message_2.attributes = {"mydate": f"2023-02-03{hour}"}
        self.message_3.attributes = {"mydate": f"2023-01-02{hour}"}
        self.message_4.attributes = {"mydate": f"2023-02-05{hour}"}

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_date_day(self, date_type="date"):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:day"],
            order="attributes.mydate:day DESC",
        )

        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["__count"], 2)
        self.assertEqual(result[0]["attributes.mydate:day"], False)
        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mydate:day"][1], "02 May 2077")
        self.assertEqual(result[2]["__count"], 1)
        self.assertEqual(result[2]["attributes.mydate:day"][1], "05 Feb 2023")
        self.assertEqual(result[3]["__count"], 1)
        self.assertEqual(result[3]["attributes.mydate:day"][1], "03 Feb 2023")
        self.assertEqual(result[4]["__count"], 2)
        self.assertEqual(result[4]["attributes.mydate:day"][1], "02 Jan 2023")
        self.assertEqual(
            Model.search(result[0]["__extra_domain"]),
            self.message_6 | self.message_7,
        )
        self.assertEqual(Model.search(result[1]["__extra_domain"]), self.message_5)
        self.assertEqual(Model.search(result[2]["__extra_domain"]), self.message_4)
        self.assertEqual(Model.search(result[3]["__extra_domain"]), self.message_2)
        self.assertEqual(
            Model.search(result[4]["__extra_domain"]),
            self.message_1 | self.message_3,
        )
        self._check_domains_count(result)

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:year"],
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["attributes.mydate:year"][1], "2023")
        self.assertEqual(result[1]["attributes.mydate:year"][1], "2077")
        self.assertEqual(result[2]["attributes.mydate:year"], False)

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_date_quarter(self, date_type="date"):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:quarter"],
            order="attributes.mydate:quarter DESC",
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["__count"], 2)
        self.assertEqual(result[0]["attributes.mydate:quarter"], False)
        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mydate:quarter"][1], "Q2 2077")
        self.assertEqual(result[2]["__count"], 4)
        self.assertEqual(result[2]["attributes.mydate:quarter"][1], "Q1 2023")
        self.assertEqual(
            Model.search(result[0]["__extra_domain"]),
            self.message_6 | self.message_7,
        )
        self.assertEqual(Model.search(result[1]["__extra_domain"]), self.message_5)
        self.assertEqual(
            Model.search(result[2]["__extra_domain"]),
            self.message_1 | self.message_2 | self.message_3 | self.message_4,
        )
        self._check_domains_count(result)

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_date_month(self, date_type="date"):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:month"],
            order="attributes.mydate:month DESC",
        )

        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["__count"], 2)
        self.assertEqual(result[0]["attributes.mydate:month"], False)
        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mydate:month"][1], "May 2077")
        self.assertEqual(result[2]["__count"], 2)
        self.assertEqual(result[2]["attributes.mydate:month"][1], "February 2023")
        self.assertEqual(result[3]["__count"], 2)
        self.assertEqual(result[3]["attributes.mydate:month"][1], "January 2023")
        self.assertEqual(
            Model.search(result[0]["__extra_domain"]),
            self.message_6 | self.message_7,
        )
        self.assertEqual(Model.search(result[1]["__extra_domain"]), self.message_5)
        self.assertEqual(
            Model.search(result[2]["__extra_domain"]),
            self.message_2 | self.message_4,
        )
        self.assertEqual(
            Model.search(result[3]["__extra_domain"]),
            self.message_1 | self.message_3,
        )
        self._check_domains_count(result)

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_date_week(self, date_type="date"):
        first_week_day = int(get_lang(self.env).week_start) - 1
        self.assertEqual(first_week_day, 6, "First day of the week must be Sunday")

        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:week"],
            order="attributes.mydate:week DESC",
        )

        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["__count"], 2)
        self.assertEqual(result[0]["attributes.mydate:week"], False)
        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mydate:week"][1], "W19 2077")
        self.assertEqual(result[2]["__count"], 1)
        self.assertEqual(result[2]["attributes.mydate:week"][1], "W6 2023")
        self.assertEqual(result[3]["__count"], 1)
        self.assertEqual(result[3]["attributes.mydate:week"][1], "W5 2023")
        self.assertEqual(result[4]["__count"], 2)
        self.assertEqual(result[4]["attributes.mydate:week"][1], "W1 2023")
        self.assertEqual(
            Model.search(result[0]["__extra_domain"]),
            self.message_6 | self.message_7,
        )
        self.assertEqual(Model.search(result[1]["__extra_domain"]), self.message_5)
        self.assertEqual(Model.search(result[2]["__extra_domain"]), self.message_4)
        self.assertEqual(Model.search(result[3]["__extra_domain"]), self.message_2)
        self.assertEqual(
            Model.search(result[4]["__extra_domain"]),
            self.message_1 | self.message_3,
        )
        self._check_domains_count(result)

        boundary_format = "%Y-%m-%d %H:%M:%S" if date_type == "datetime" else "%Y-%m-%d"
        for line in result[1:]:
            self.assertEqual(line["__extra_domain"][1][1], ">=")
            self.assertEqual(line["__extra_domain"][2][1], "<")
            start = datetime.datetime.strptime(
                line["__extra_domain"][1][2], boundary_format
            )
            end = datetime.datetime.strptime(
                line["__extra_domain"][2][2], boundary_format
            )
            self.assertEqual(start.weekday(), first_week_day)
            self.assertEqual(end.weekday(), first_week_day)

        lang = (
            self.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "fr_FR")])
        )
        self.assertEqual(len(lang), 1)
        lang.write({"active": True, "week_start": "3"})
        result = Model.with_context(lang="fr_FR").formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:week"],
            order="attributes.mydate:week DESC",
        )
        for line in result[1:]:
            self.assertEqual(line["__extra_domain"][1][1], ">=")
            self.assertEqual(line["__extra_domain"][2][1], "<")
            start = datetime.datetime.strptime(
                line["__extra_domain"][1][2], boundary_format
            )
            end = datetime.datetime.strptime(
                line["__extra_domain"][2][2], boundary_format
            )
            self.assertEqual(
                start.weekday(), 2, "First day of the week must be Wednesday"
            )
            self.assertEqual(
                end.weekday(), 2, "First day of the week must be Wednesday"
            )

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_date_year(self, date_type="date"):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        result = Model.formatted_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["attributes.mydate:year"],
            order="attributes.mydate:year DESC",
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["__count"], 2)
        self.assertEqual(result[0]["attributes.mydate:year"], False)
        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mydate:year"][1], "2077")
        self.assertEqual(result[2]["__count"], 4)
        self.assertEqual(result[2]["attributes.mydate:year"][1], "2023")
        self.assertEqual(
            Model.search(result[0]["__extra_domain"]),
            self.message_6 | self.message_7,
        )
        self.assertEqual(Model.search(result[1]["__extra_domain"]), self.message_5)
        self.assertEqual(
            Model.search(result[2]["__extra_domain"]),
            self.message_1 | self.message_2 | self.message_3 | self.message_4,
        )
        self._check_domains_count(result)

    def test_properties_field_read_group_datetime_day(self):
        self.test_properties_field_read_group_date_day("datetime")

    def test_properties_field_read_group_datetime_quarter(self):
        self.test_properties_field_read_group_date_quarter("datetime")

    def test_properties_field_read_group_datetime_month(self):
        self.test_properties_field_read_group_date_month("datetime")

    def test_properties_field_read_group_datetime_week(self):
        self.test_properties_field_read_group_date_week("datetime")

    def test_properties_field_read_group_datetime_year(self):
        self.test_properties_field_read_group_date_year("datetime")

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_injection(self):
        Model = self.env["test_orm.message"]
        self.message_1.attributes = [
            {
                "name": "myinteger",
                "type": "integer",
                "value": 1337,
                "definition_changed": True,
            }
        ]

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.myinteger"],
                order="attributes.myinteger OR 1=1 DESC",
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.myinteger OR 1=1"],
                order="attributes.myinteger DESC",
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=["__count"],
                groupby=["attributes.myinteger:wrongfunction"],
                order="attributes.myinteger DESC",
            )

        with self.assertRaises(ValueError), self.assertQueryCount(0):
            Model.formatted_read_group(
                domain=[],
                aggregates=["attributes.myinteger:sum"],
            )

    @mute_logger("odoo.fields", "odoo.models.unlink")
    def test_properties_field_read_group_many2many(self):
        Model = self.env["test_orm.message"]

        partners = self.env["test_orm.partner"].create(
            [{"name": f"Partner {i}"} for i in range(10)]
        )

        self.discussion_1.attributes_definition = [
            {
                "name": "mypartners",
                "string": "Partners",
                "type": "many2many",
                "comodel": "test_orm.partner",
            }
        ]

        self.messages.discussion = self.discussion_1

        self.message_1.attributes = {"mypartners": partners[:5].ids}
        self.message_2.attributes = {"mypartners": partners[3:8].ids}
        self.message_3.attributes = {"mypartners": partners[8:].ids}

        (partners[4] | partners[7] | partners[9]).unlink()

        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                aggregates=["__count"],
                groupby=["attributes.mypartners"],
            )

        self.assertEqual(len(result), 8)
        existing_partners = partners.exists()
        self.assertEqual(len(existing_partners), 7)
        for partner, line in zip(existing_partners, result, strict=False):
            self.assertEqual(partner.id, line["attributes.mypartners"][0])
            self.assertEqual(partner.display_name, line["attributes.mypartners"][1])
            self.assertEqual(
                line["__extra_domain"],
                [("attributes.mypartners", "in", [partner.id])],
            )
            self.assertEqual(line["__count"], 2 if partner == partners[3] else 1)

        self.assertEqual(Model.search(result[-1]["__extra_domain"]), self.message_4)
        self._check_many_falsy_group("mypartners", result)
        self._check_domains_count(result)

        partners[:8].unlink()
        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                aggregates=["__count"],
                groupby=["attributes.mypartners"],
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            Model.search(result[-1]["__extra_domain"]),
            self.message_1 | self.message_2 | self.message_4,
        )
        self._check_many_falsy_group("mypartners", result)
        self._check_domains_count(result)

        existing_partners.unlink()
        result = Model.formatted_read_group(
            domain=[("discussion", "!=", self.wrong_discussion_id)],
            aggregates=["__count"],
            groupby=["attributes.mypartners"],
        )
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["attributes.mypartners"])
        self.assertEqual(result[0]["__count"], 4)
        self._check_domains_count(result)

        for invalid_model_name in (
            "invalid_model_name",
            "test_orm.transient_model",
        ):
            self.env.cr.execute(
                """
                UPDATE test_orm_discussion
                   SET attributes_definition
                       = jsonb_set(attributes_definition, '{0,comodel}', %s)
                 WHERE id = %s
                """,
                [json.dumps(invalid_model_name), self.discussion_1.id],
            )
            definition = self._get_sql_definition(self.discussion_1)
            self.assertEqual(definition[0]["comodel"], invalid_model_name)
            error_message = f'You cannot use "Partners" because the linked "{invalid_model_name}" model doesn\'t exist or is invalid'
            with self.assertRaisesRegex(UserError, error_message):
                result = Model.formatted_read_group(
                    domain=[("discussion", "!=", self.wrong_discussion_id)],
                    aggregates=["__count"],
                    groupby=["attributes.mypartners"],
                )

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_many2one(self):
        Model = self.env["test_orm.message"]

        self.message_1.attributes = [
            {
                "name": "mypartner",
                "string": "My Partner",
                "type": "many2one",
                "value": self.partner_2.id,
                "comodel": "test_orm.partner",
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mypartner": self.partner.id}
        self.message_4.attributes = {"mypartner": False}

        unexisting_record_id = (
            self.env["test_orm.partner"].search([], order="id DESC", limit=1).id + 1
        )
        self.env.cr.execute(
            """
            UPDATE test_orm_message
               SET attributes = %s::jsonb
             WHERE id = %s
            """,
            [
                json.dumps({"mypartner": unexisting_record_id}),
                self.message_3.id,
            ],
        )

        self.env.invalidate_all()
        with self.assertQueryCount(4):
            result = Model.formatted_read_group(
                domain=[],
                groupby=["attributes.mypartner"],
                aggregates=["__count"],
            )

        self.assertEqual(
            len(result), 3, "Should ignore the partner that has been removed"
        )

        self.assertEqual(result[0]["__count"], 1)
        self.assertEqual(result[0]["attributes.mypartner"][0], self.partner.id)
        self.assertEqual(
            result[0]["attributes.mypartner"][1], self.partner.display_name
        )
        self.assertEqual(
            result[0]["__extra_domain"],
            [("attributes.mypartner", "=", self.partner.id)],
        )

        self.assertEqual(result[1]["__count"], 1)
        self.assertEqual(result[1]["attributes.mypartner"][0], self.partner_2.id)
        self.assertEqual(
            result[1]["attributes.mypartner"][1], self.partner_2.display_name
        )
        self.assertEqual(
            result[1]["__extra_domain"],
            [("attributes.mypartner", "=", self.partner_2.id)],
        )

        self.assertEqual(result[2]["__count"], 2)
        self.assertEqual(result[2]["attributes.mypartner"], False)
        self.assertEqual(
            result[2]["__extra_domain"],
            [
                "|",
                ("attributes.mypartner", "=", False),
                (
                    "attributes.mypartner",
                    "not in",
                    [self.partner.id, self.partner_2.id],
                ),
            ],
        )

        self.message_4.attributes = {"mypartner": self.partner.id}
        result = Model.formatted_read_group(
            domain=[],
            groupby=["attributes.mypartner"],
            aggregates=["__count"],
        )
        self.assertEqual(result[2]["__count"], 1)
        self.assertEqual(
            result[2]["__extra_domain"],
            [
                "|",
                ("attributes.mypartner", "=", False),
                (
                    "attributes.mypartner",
                    "not in",
                    [self.partner.id, self.partner_2.id],
                ),
            ],
        )

        for invalid_model_name in (
            "invalid_model_name",
            "test_orm.transient_model",
        ):
            self.env.cr.execute(
                """
                UPDATE test_orm_discussion
                   SET attributes_definition
                       = jsonb_set(attributes_definition, '{0,comodel}', %s::jsonb)
                 WHERE id = %s
                """,
                [json.dumps(invalid_model_name), self.discussion_1.id],
            )
            definition = self._get_sql_definition(self.discussion_1)
            self.assertEqual(definition[0]["comodel"], invalid_model_name)
            error_message = f'You cannot use "My Partner" because the linked "{invalid_model_name}" model doesn\'t exist or is invalid'
            with self.assertRaisesRegex(UserError, error_message):
                result = Model.formatted_read_group(
                    domain=[("discussion", "!=", self.wrong_discussion_id)],
                    aggregates=["__count"],
                    groupby=["attributes.mypartner"],
                )

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_selection(self):
        Model = self.env["test_orm.message"]

        self.message_1.attributes = [
            {
                "name": "myselection",
                "type": "selection",
                "value": "optionA",
                "selection": [["optionA", "A"], ["optionB", "B"]],
                "definition_changed": True,
            },
            {
                "name": "mychar2",
                "type": "char",
                "value": "qsd",
                "definition_changed": True,
            },
        ]
        self.message_2.attributes = {"myselection": False}

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
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                groupby=["attributes.myselection"],
                aggregates=["__count"],
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["__count"], 1)
        self.assertEqual(
            result[0]["__extra_domain"],
            [("attributes.myselection", "=", "optionA")],
        )
        self.assertEqual(result[0]["attributes.myselection"], "optionA")

        self.assertEqual(result[1]["__count"], 3)
        self.assertEqual(
            result[1]["__extra_domain"],
            [
                "|",
                ("attributes.myselection", "=", False),
                ("attributes.myselection", "not in", ["optionA", "optionB"]),
            ],
        )
        self.assertEqual(result[1]["attributes.myselection"], False)
        self.assertEqual(
            self.env["test_orm.message"].search(result[1]["__extra_domain"]),
            self.message_2 | self.message_3 | self.message_4,
        )

        self.message_1.attributes = [
            {
                "name": "myselection",
                "type": "selection",
                "value": "optionA",
                "selection": [],
                "definition_changed": True,
            }
        ]
        result = Model.formatted_read_group(
            domain=[],
            groupby=["attributes.myselection"],
            aggregates=["__count"],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["__count"], 4)
        self._check_domains_count(result)

    @mute_logger("odoo.fields")
    def test_properties_field_read_group_tags(self):
        Model = self.env["test_orm.message"]

        (
            self.message_1 | self.message_2 | self.message_3
        ).discussion = self.discussion_1

        self.message_1.attributes = [
            {
                "name": "mytags",
                "type": "tags",
                "value": ["a", "c", "g"],
                "tags": [[x.lower(), x, i] for i, x in enumerate("ABCDEFG")],
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mytags": ["a", "e", "g"]}
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
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                aggregates=["__count"],
                groupby=["attributes.mytags"],
            )

        self.assertNotIn("invalid", str(result))
        self.assertEqual(len(result), 6)

        all_tags = self.message_1.read(["attributes"])[0]["attributes"][0]["tags"]
        all_tags = {tag[0]: tuple(tag) for tag in all_tags}

        for group, (tag, count) in zip(
            result, (("a", 3), ("c", 1), ("d", 1), ("e", 2), ("g", 2)), strict=False
        ):
            self.assertEqual(group["attributes.mytags"], all_tags[tag])
            self.assertEqual(group["__count"], count)
            self.assertEqual(
                group["__extra_domain"],
                [("attributes.mytags", "in", [tag])],
            )
            property_values = [
                next(pro["value"] for pro in values["attributes"])
                for values in Model.search(group["__extra_domain"]).read(["attributes"])
            ]
            self.assertTrue(
                all(tag in property_value for property_value in property_values)
            )

        self.assertEqual(Model.search(result[-1]["__extra_domain"]), self.message_4)
        self._check_many_falsy_group("mytags", result)
        self._check_domains_count(result)

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
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                aggregates=["__count"],
                groupby=["attributes.mytags"],
            )
        self.assertEqual(
            Model.search(result[-1]["__extra_domain"]),
            self.message_3 | self.message_4,
        )
        self._check_many_falsy_group("mytags", result)
        self._check_domains_count(result)

        for tags in ([], False, None):
            self.message_1.attributes = [
                {
                    "name": "mytags",
                    "type": "tags",
                    "value": tags,
                    "tags": tags,
                    "definition_changed": True,
                }
            ]
            result = Model.formatted_read_group(
                domain=[("discussion", "!=", self.wrong_discussion_id)],
                aggregates=["__count"],
                groupby=["attributes.mytags"],
            )
            self.assertEqual(len(result), 1)
            self.assertFalse(result[0]["attributes.mytags"])
            self.assertEqual(result[0]["__count"], 4)
            self._check_domains_count(result)

    def _check_domains_count(self, result):
        for line in result:
            records = self.env["test_orm.message"].search(line["__extra_domain"])
            self.assertIn("__count", line, "every caller aggregates on __count")
            self.assertEqual(len(records), line["__count"])

    def _check_many_falsy_group(self, property_name, result):
        Model = self.env["test_orm.message"]
        falsy_group = result[-1]
        self.assertFalse(falsy_group[f"attributes.{property_name}"])
        falsy_records = Model.search(falsy_group["__extra_domain"])
        nonfalsy_records = Model.search(
            Domain.OR(line["__extra_domain"] for line in result[:-1])
        )
        self.assertEqual(
            Model.search_count([]), len(falsy_records) + len(nonfalsy_records)
        )
        for falsy_record in falsy_records:
            self.assertNotIn(falsy_record, nonfalsy_records)

        def _get_records_values(records):
            return [
                next(
                    (
                        pro.get("value")
                        for pro in properties["attributes"]
                        if pro["name"] == property_name
                    ),
                )
                for properties in records.read(["attributes"])
            ]

        self.assertTrue(not any(_get_records_values(falsy_records)))
        self.assertTrue(all(_get_records_values(nonfalsy_records)))

    def subtest_properties_field_web_read_group_date_like(self, date_type="date"):
        self._properties_field_read_group_date_prepare(date_type)
        Model = self.env["test_orm.message"]

        hour_min = " 00:00:00" if date_type == "datetime" else ""

        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["attributes.mydate:year"],
                aggregates=[],
            ),
            {
                "groups": [
                    {
                        "__extra_domain": [
                            "&",
                            (
                                "attributes.mydate",
                                ">=",
                                f"2023-01-01{hour_min}",
                            ),
                            ("attributes.mydate", "<", f"2024-01-01{hour_min}"),
                        ],
                        "attributes.mydate:year": (
                            f"2023-01-01{hour_min}",
                            "2023",
                        ),
                        "__count": 4,
                    },
                    {
                        "__extra_domain": [
                            "&",
                            (
                                "attributes.mydate",
                                ">=",
                                f"2077-01-01{hour_min}",
                            ),
                            ("attributes.mydate", "<", f"2078-01-01{hour_min}"),
                        ],
                        "attributes.mydate:year": (
                            f"2077-01-01{hour_min}",
                            "2077",
                        ),
                        "__count": 1,
                    },
                    {
                        "__extra_domain": [("attributes.mydate", "=", False)],
                        "attributes.mydate:year": False,
                        "__count": 2,
                    },
                ],
                "length": 3,
            },
        )
        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["attributes.mydate:year"],
                aggregates=[],
                opening_info=[
                    {
                        "value": f"2077-01-01{hour_min}",
                        "folded": False,
                        "limit": 80,
                        "offset": 0,
                        "progressbar_domain": False,
                        "groups": [],
                    },
                    {"value": f"2023-01-01{hour_min}", "folded": True},
                    {"value": False, "folded": True},
                ],
                unfold_read_specification={"id": {}},
            ),
            {
                "groups": [
                    {
                        "__extra_domain": [
                            "&",
                            (
                                "attributes.mydate",
                                ">=",
                                f"2023-01-01{hour_min}",
                            ),
                            ("attributes.mydate", "<", f"2024-01-01{hour_min}"),
                        ],
                        "attributes.mydate:year": (
                            f"2023-01-01{hour_min}",
                            "2023",
                        ),
                        "__count": 4,
                    },
                    {
                        "__extra_domain": [
                            "&",
                            (
                                "attributes.mydate",
                                ">=",
                                f"2077-01-01{hour_min}",
                            ),
                            ("attributes.mydate", "<", f"2078-01-01{hour_min}"),
                        ],
                        "attributes.mydate:year": (
                            f"2077-01-01{hour_min}",
                            "2077",
                        ),
                        "__records": [{"id": self.message_5.id}],
                        "__count": 1,
                    },
                    {
                        "__extra_domain": [("attributes.mydate", "=", False)],
                        "attributes.mydate:year": False,
                        "__count": 2,
                    },
                ],
                "length": 3,
            },
        )

    def test_properties_field_read_group_date(self):
        self.subtest_properties_field_web_read_group_date_like("date")

    def test_properties_field_read_group_datetime(self):
        self.subtest_properties_field_web_read_group_date_like("datetime")

    def test_unfold_read_specification_on_web_read_group(self):
        self.messages.discussion = self.discussion_1
        self.discussion_1.write({"participants": [Command.link(self.test_user.id)]})
        self.message_2.author = self.test_user

        result = self.env["test_orm.message"].web_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["author"],
            auto_unfold=True,
            unfold_read_specification={"author": {}},
        )
        group1 = result["groups"]

        result = self.env["test_orm.message"].web_read_group(
            domain=[],
            aggregates=["__count"],
            groupby=["author"],
            auto_unfold=True,
            unfold_read_specification=None,
        )
        group2 = result["groups"]

        self.assertEqual(
            group1[0]["__records"],
            [
                {"id": self.message_1.id, "author": self.env.user.id},
                {"id": self.message_3.id, "author": self.env.user.id},
                {"id": self.message_4.id, "author": self.env.user.id},
            ],
        )
        self.assertEqual(
            group2[0]["__records"],
            [
                {"id": self.message_1.id},
                {"id": self.message_3.id},
                {"id": self.message_4.id},
            ],
        )
        self.assertEqual(
            group1[1]["__records"],
            [{"id": self.message_2.id, "author": self.test_user.id}],
        )
        self.assertEqual(group2[1]["__records"], [{"id": self.message_2.id}])


class PropertiesFilteredDomainParityCase(
    TransactionExpressionCase, TestPropertiesMixin
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.messages = cls.message_1 | cls.message_2 | cls.message_3
        cls.env["test_orm.message"].search(
            [("id", "not in", cls.messages.ids)]
        ).unlink()

    def test_filtered_domain_many2one_property_in(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mypartner",
                "type": "many2one",
                "comodel": "test_orm.partner",
                "value": self.partner.id,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mypartner": self.partner_2.id}
        self.message_3.attributes = {"mypartner": False}

        Message = self.env["test_orm.message"]

        domain = [("attributes.mypartner", "in", [self.partner.id])]
        found = self._search(Message, domain)
        self.assertEqual(found, self.message_1)
        self.assertEqual(self.messages.filtered_domain(domain), self.message_1)

        domain = [("attributes.mypartner", "in", [self.partner.id, self.partner_2.id])]
        found = self._search(Message, domain)
        self.assertEqual(found, self.message_1 | self.message_2)
        self.assertEqual(
            self.messages.filtered_domain(domain),
            self.message_1 | self.message_2,
        )

        domain = [("attributes.mypartner", "not in", [self.partner.id])]
        self.assertEqual(
            self._search(Message, domain),
            self.message_2 | self.message_3,
        )

        self.assertEqual(
            Message.browse().filtered_domain(
                [("attributes.mypartner", "in", [self.partner.id])]
            ),
            Message.browse(),
        )

    def test_filtered_domain_tags_property_in(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "mytags",
                "type": "tags",
                "value": ["a", "b"],
                "tags": [["a", "A", 1], ["b", "B", 2], ["c", "C", 3]],
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"mytags": ["b"]}
        self.message_3.attributes = {"mytags": []}

        Message = self.env["test_orm.message"]

        for domain, expected in (
            ([("attributes.mytags", "in", ["a"])], self.message_1),
            ([("attributes.mytags", "in", ["b"])], self.message_1 | self.message_2),
            ([("attributes.mytags", "in", ["c"])], Message.browse()),
            (
                [("attributes.mytags", "in", ["a", "c"])],
                self.message_1,
            ),
            (
                [("attributes.mytags", "in", ["a", "b"])],
                self.message_1 | self.message_2,
            ),
            (
                [("attributes.mytags", "in", ["a", "b", "c"])],
                self.message_1 | self.message_2,
            ),
        ):
            with self.subTest(domain=domain):
                self.assertEqual(self._search(Message, domain), expected)
                self.assertEqual(self.messages.filtered_domain(domain), expected)

    def test_filtered_domain_integer_property_zero(self):
        self.messages.discussion = self.discussion_1
        self.message_1.attributes = [
            {
                "name": "myint",
                "type": "integer",
                "value": 0,
                "definition_changed": True,
            }
        ]
        self.message_2.attributes = {"myint": 111}
        self.message_3.attributes = {"myint": -2}

        Message = self.env["test_orm.message"]

        domain = [("attributes.myint", ">=", 0)]
        found = self._search(Message, domain)
        self.assertEqual(found, self.message_1 | self.message_2)
        self.assertEqual(
            self.messages.filtered_domain(domain),
            self.message_1 | self.message_2,
        )

        domain = [("attributes.myint", "=", 0)]
        found = self._search(Message, domain)
        self.assertEqual(found, self.message_1)
        self.assertEqual(self.messages.filtered_domain(domain), self.message_1)

    def test_zero_scalar_property_reads_back_as_zero(self):
        self.message_1.attributes = [
            {
                "name": "myint",
                "type": "integer",
                "value": 0,
                "definition_changed": True,
            },
            {
                "name": "myfloat",
                "type": "float",
                "value": 0.0,
                "definition_changed": True,
            },
            {
                "name": "mychar",
                "type": "char",
                "value": "",
                "definition_changed": True,
            },
        ]
        self.env.invalidate_all()

        values = self.message_1.attributes
        self.assertEqual(values["myint"], 0)
        self.assertNotIsInstance(values["myint"], bool)
        self.assertEqual(values["myfloat"], 0.0)
        self.assertNotIsInstance(values["myfloat"], bool)
        self.assertIs(values["mychar"], False)

        self.message_2.discussion = self.discussion_1
        self.assertIs(self.message_2.attributes["myint"], False)


class PropertiesRecordsetWriteCase(TestPropertiesMixin):
    def _relational_definition(self):
        return [
            {
                "name": "mym2o",
                "type": "many2one",
                "string": "M2O",
                "comodel": "test_orm.partner",
            },
            {
                "name": "mym2m",
                "type": "many2many",
                "string": "M2M",
                "comodel": "test_orm.partner",
            },
        ]

    def setUp(self):
        super().setUp()
        self.discussion_1.attributes_definition = self._relational_definition()
        self.message_1.attributes = {
            "mym2o": self.partner.id,
            "mym2m": [self.partner.id, self.partner_2.id],
        }
        self.env.flush_all()
        self.env.invalidate_all()

    def test_read_returns_recordsets(self):
        self.assertEqual(self.message_1.attributes["mym2o"], self.partner)
        self.assertEqual(
            self.message_1.attributes["mym2m"], self.partner | self.partner_2
        )

    def test_partial_dict_write_accepts_a_recordset(self):
        for name in ("mym2o", "mym2m"):
            with self.subTest(property=name):
                value = self.message_1.attributes[name]
                self.message_1.attributes = {name: value}
                self.env.flush_all()
                self.env.invalidate_all()
                self.assertEqual(self.message_1.attributes[name], value)

    def test_whole_property_write_still_works(self):
        values = self.message_1.attributes
        self.message_1.attributes = values
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.message_1.attributes["mym2o"], self.partner)
        self.assertEqual(
            self.message_1.attributes["mym2m"], self.partner | self.partner_2
        )

    def test_single_record_many2many_stays_a_list(self):
        self.message_1.attributes = {"mym2m": self.partner}
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.message_1.attributes["mym2m"], self.partner)
        stored = self.message_1.read(["attributes"])[0]["attributes"]
        mym2m = next(p for p in stored if p["name"] == "mym2m")
        self.assertIsInstance(mym2m["value"], list, mym2m)

    def test_list_format_accepts_a_recordset_too(self):
        self.message_1.attributes = [
            {
                "name": "mym2o",
                "type": "many2one",
                "string": "M2O",
                "comodel": "test_orm.partner",
                "value": self.partner_2,
            }
        ]
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.message_1.attributes["mym2o"], self.partner_2)

    def test_unresolvable_recordset_is_refused_by_name(self):
        self.message_1.discussion = False
        with self.assertRaises(ValueError) as capture:
            self.message_1.attributes = {"mym2o": self.partner}
            self.env.flush_all()
        self.assertIn("mym2o", str(capture.exception))


class PropertiesCallerIsolationCase(TestPropertiesMixin):
    def _write_and_mutate(self, payload, mutate):
        self.discussion_1.attributes_definition = [
            {"name": "note", "string": "Note", "type": "char"},
        ]
        self.message_1.attributes = payload
        before = dict(self.message_1.attributes)
        mutate(payload)
        return before, dict(self.message_1.attributes)

    def test_a_plain_dict_is_copied(self):
        payload = {"note": "original"}
        before, after = self._write_and_mutate(
            payload, lambda d: d.__setitem__("note", "mutated")
        )
        self.assertEqual(before, after)
        self.assertEqual(after["note"], "original")

    def test_a_dict_subclass_is_copied_too(self):
        payload = _OrderedDict(note="original")
        before, after = self._write_and_mutate(
            payload, lambda d: d.__setitem__("note", "mutated")
        )
        self.assertEqual(
            after["note"],
            "original",
            "the caller's post-write mutation reached the record: the field "
            "cache is holding the caller's object, not a copy of it",
        )
        self.assertEqual(before, after)

    def test_a_nested_container_is_copied(self):
        inner = {"deep": "original"}
        payload = _OrderedDict(note="x", nested=inner)
        self.discussion_1.attributes_definition = [
            {"name": "note", "string": "Note", "type": "char"},
        ]
        self.message_1.attributes = payload
        inner["deep"] = "mutated"
        stored = dict(self.message_1.attributes)
        self.assertNotIn("mutated", str(stored), "a nested dict was shared, not cloned")


class PropertiesDefinitionRoundTripCase(TestPropertiesMixin):
    def _definition_entry(self, **overrides):
        entry = {"name": "prop_a", "type": "char", "string": "A"}
        entry.update(overrides)
        return [entry]

    def test_a_falsy_type_is_refused_rather_than_silently_dropped(self):
        for bad_type in ("", False, None):
            with self.subTest(type=bad_type), self.assertRaises(ValueError) as capture:
                self.discussion_1.attributes_definition = self._definition_entry(
                    type=bad_type
                )
                self.env.flush_all()
            self.assertIn("type", str(capture.exception))

    def test_a_falsy_name_is_refused(self):
        for bad_name in ("", False, None):
            with self.subTest(name=bad_name), self.assertRaises(ValueError) as capture:
                self.discussion_1.attributes_definition = self._definition_entry(
                    name=bad_name
                )
                self.env.flush_all()
            self.assertIn("name", str(capture.exception))

    def test_a_missing_key_names_itself_instead_of_raising_KeyError(self):
        for missing in ("name", "type"):
            entry = self._definition_entry()
            del entry[0][missing]
            with (
                self.subTest(missing=missing),
                self.assertRaises(ValueError) as capture,
            ):
                self.discussion_1.attributes_definition = entry
                self.env.flush_all()
            self.assertIn(missing, str(capture.exception))

    def test_every_accepted_definition_survives_the_round_trip(self):
        accepted = []
        candidates = [
            self._definition_entry(),
            self._definition_entry(type="integer"),
            self._definition_entry(type="boolean"),
            self._definition_entry(name="prop_b", type="char", default="x"),
            self._definition_entry(type="", string="empty type"),
            self._definition_entry(name="", string="empty name"),
        ]
        for definition in candidates:
            try:
                self.discussion_1.attributes_definition = definition
                self.env.flush_all()
            except ValueError:
                continue
            accepted.append(definition)
            self.env.invalidate_all()
            self.assertEqual(
                len(self.discussion_1.attributes_definition),
                len(definition),
                f"write() accepted {definition!r} but reading it back dropped "
                f"entries; the validator and convert_to_record disagree",
            )
        self.assertTrue(accepted, "test premise: some definitions must be accepted")

    def test_filtered_agrees_with_the_field_on_an_accepted_definition(self):
        self.discussion_1.attributes_definition = self._definition_entry()
        self.env.flush_all()
        self.env.invalidate_all()
        discussions = self.discussion_1 | self.discussion_2
        self.assertEqual(
            discussions.filtered("attributes_definition"),
            discussions.filtered(lambda d: d.attributes_definition),
            "the filtered() cache fast path disagrees with reading the field",
        )


class PropertiesDefinitionColumnNamedDefinitionCase(TransactionCase):
    def test_a_definition_column_named_definition_is_still_readable(self):
        holder = self.env["test_orm.properties.holder.b"].create({"name": "holder"})
        holder.definition = [
            {"name": "kind", "type": "tags", "string": "Kind", "tags": [["x", "X", 1]]},
        ]
        self.env.flush_all()

        self.assertEqual(
            self.env["test_orm.properties.holder.b"]._fields["definition"].type,
            "properties_definition",
            "the fixture must keep a definition field literally named 'definition'",
        )
        definition = self.env["test_orm.properties.target"].get_property_definition(
            "attributes.kind"
        )
        self.assertEqual(
            definition.get("type"),
            "tags",
            "the definition is stored and reachable; an empty dict here means the "
            "SQL alias shadowed the column again",
        )


class TestPropertiesBaseDefinitionReadPaths(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Definition = self.env["properties.base.definition"].sudo()
        self.Model = self.env["test_orm.emailmessage"]
        field = self.env["ir.model.fields"].sudo()._get(self.Model._name, "properties")
        self.Definition.search([("properties_field_id", "=", field.id)]).unlink()

    def _definition_id(self):
        return self.Definition._get_definition_id_for_property_field(
            self.Model._name, "properties"
        )

    def test_unlink_forgets_the_cached_definition(self):
        self.assertIsNone(self._definition_id())

    def test_reading_the_definition_never_creates_it(self):
        before = self.Definition.search_count([])

        self.assertFalse(
            self.Model.search([("properties_base_definition_id", "!=", False)])
        )
        self.Model.fields_get(["properties_base_definition_id"])
        self.Model._read_group([], groupby=["properties_base_definition_id"])

        self.assertEqual(self.Definition.search_count([]), before)
        self.assertIsNone(self._definition_id())

    def test_the_search_method_answers_both_operators(self):
        record = self.Model.create({})
        definition_id = self._definition_id()
        Model = self.Model.with_context(active_test=False)
        self.assertIn(
            record,
            Model.search([("properties_base_definition_id", "=", definition_id)]),
        )
        self.assertNotIn(
            record,
            Model.search([("properties_base_definition_id", "!=", definition_id)]),
        )
        self.assertNotIn(
            record, Model.search([("properties_base_definition_id", "=", False)])
        )
        self.assertIn(
            record, Model.search([("properties_base_definition_id", "!=", False)])
        )

    def test_creating_a_record_attaches_a_definition(self):
        record = self.Model.create({})
        definition_id = self._definition_id()
        self.assertTrue(definition_id)
        self.assertEqual(record.properties_base_definition_id.id, definition_id)
        self.assertIn(
            record,
            self.Model.search([("properties_base_definition_id", "=", definition_id)]),
        )

    def test_grouping_by_the_definition_groups_every_record_under_it(self):
        records = self.Model.create([{}, {}])
        definition = records.properties_base_definition_id
        self.assertEqual(len(definition), 1)
        groups = self.Model.with_context(active_test=False)._read_group(
            [("id", "in", records.ids)],
            groupby=["properties_base_definition_id"],
            aggregates=["__count"],
        )
        self.assertEqual(groups, [(definition, 2)])
