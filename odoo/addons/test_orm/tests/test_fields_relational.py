import base64
import io
from collections import OrderedDict
from datetime import date, datetime
from unittest.mock import patch
from contextlib import contextmanager

import psycopg2
from PIL import Image

from odoo import Command, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged, users
from odoo.tools import BinaryBytes, float_repr, mute_logger
from odoo.tools.image import binary_to_image, image_data_uri

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.tests.files import SVG_RAW, ZIP_RAW
from odoo.addons.test_orm.tests.test_domain_expression import TransactionExpressionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFields(TransactionCaseWithUserDemo, TransactionExpressionCase):
    def setUp(self):
        # for tests methods that create custom models/fields
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)
        super().setUp()
        self.env.ref('test_orm.discussion_0').write({'participants': [Command.link(self.user_demo.id)]})
        # YTI FIX ME: The cache shouldn't be inconsistent (rco is gonna fix it)
        # self.env.ref('test_orm.discussion_0').participants -> 1 user
        # self.env.ref('test_orm.discussion_0').invalidate()
        # self.env.ref('test_orm.discussion_0').with_context(active_test=False).participants -> 2 users
        self.env.ref('test_orm.message_0_1').write({'author': self.user_demo.id})

    def test_12_one2many_reference_domain(self):
        model = self.env['test_orm.inverse_m2o_ref']
        o2m_field = model._fields['model_ids']
        self.assertEqual(o2m_field.get_comodel_domain(model), Domain('const', '=', True) & Domain('res_model', '=', model._name))
        o2m_field = model._fields['model_computed_ids']
        self.assertEqual(o2m_field.get_comodel_domain(model), Domain.TRUE)

    def test_25_related_many2one(self):
        bar = self.env['test_orm.related_bar'].create({'name': 'A'})
        foo = self.env['test_orm.related_foo'].create({'name': 'A', 'bar_id': bar.id})
        self.assertEqual(foo.bar_id, bar)
        self.assertEqual(foo.bar_alias, foo.bar_id)

        # After deactivating the foo record, the search should be executed with
        # context depending on searching a many2one field: active_test=False.
        for active in (True, False):
            with self.subTest(active=active):
                bar.active = active
                self.assertEqual(foo.search([('id', 'in', foo.ids), ('bar_id', 'ilike', 'A')]), foo)
                self.assertEqual(foo.search([('id', 'in', foo.ids), ('bar_alias', 'ilike', 'A')]), foo)

    def test_25_one2many_inverse_related(self):
        left = self.env['test_orm.trigger.left'].create({})
        right = self.env['test_orm.trigger.right'].create({})
        self.assertFalse(left.right_id)
        self.assertFalse(right.left_ids)
        self.assertFalse(right.left_size)

        # create middle: this should trigger left.right_id by traversing
        # middle.left_id, and right.left_size by traversing left.right_id
        # after its computation!
        middle = self.env['test_orm.trigger.middle'].create({
            'left_id': left.id,
            'right_id': right.id,
        })
        self.assertEqual(left.right_id, right)
        self.assertEqual(right.left_ids, left)
        self.assertEqual(right.left_size, 1)

        # delete middle: this should trigger left.right_id by traversing
        # middle.left_id, and right.left_size by traversing left.right_id
        # before its computation!
        middle.unlink()
        self.assertFalse(left.right_id)
        self.assertFalse(right.left_ids)
        self.assertFalse(right.left_size)

    def test_41_new_one2many(self):
        """ Check command on one2many field on new record. """
        move = self.env['test_orm.move'].create({})
        line = self.env['test_orm.move_line'].create({'move_id': move.id, 'quantity': 1})
        self.env.flush_all()

        new_move = move.new(origin=move)
        new_line = line.new(origin=line)
        self.assertEqual(new_move.line_ids, new_line)

        # drop line, and create a new one
        new_move.line_ids = [Command.delete(new_line.id), Command.create({'quantity': 2})]
        self.assertEqual(len(new_move.line_ids), 1)
        self.assertFalse(new_move.line_ids.id)
        self.assertEqual(new_move.line_ids.quantity, 2)

        # assign line to new move without origin
        new_move = move.new()
        new_move.line_ids = line
        self.assertFalse(new_move.line_ids.id)
        self.assertEqual(new_move.line_ids._origin, line)
        self.assertEqual(new_move.line_ids.move_id, new_move)

    def test_41_new_many2many(self):
        group = self.env['test_orm.group'].create({})
        user0 = self.env['test_orm.user'].create({'group_ids': [Command.link(group.id)]})
        new_user0 = user0.new(origin=user0)
        new_group = group.new(origin=group)

        self.env.invalidate_all()

        # creating new_user1 shoud not fetch new_group.all_user_ids, which is the
        # inverse of field new_user1.group_ids
        with self.assertQueryCount(0):
            new_user1 = self.env['test_orm.user'].new({'group_ids': [Command.link(group.id)]})
            self.assertEqual(new_user1.group_ids, new_group)

        # accessing new_group.all_user_ids should fetch group.all_user_ids and patch
        # new_group.all_user_ids
        with self.assertQueryCount(1):
            self.assertEqual(new_group.user_ids, new_user0 + new_user1)

        # creating new_user2 should patch new_group.all_user_ids immediately, since
        # it is in cache
        with self.assertQueryCount(0):
            new_user2 = self.env['test_orm.user'].new({'group_ids': [Command.link(group.id)]})
            self.assertEqual(new_user2.group_ids, new_group)
            self.assertEqual(new_group.user_ids, new_user0 + new_user1 + new_user2)

        # the patches on new_group.all_user_ids should not have changed group.all_user_ids
        self.assertEqual(group.user_ids, user0)

    def test_50_search_many2one(self):
        """ test search through a path of computed fields"""
        messages = self.env['test_orm.message'].search(
            [('author_partner.name', '=', 'Marc Demo')])
        self.assertEqual(messages, self.env.ref('test_orm.message_0_1'))

    def test_51_search_many2one_ordered(self):
        """ test search on many2one ordered by id """
        with self.assertQueries(['''
            SELECT "test_orm_message"."id" FROM "test_orm_message"
            WHERE "test_orm_message"."active" IS TRUE
            ORDER BY  "test_orm_message"."discussion"
        ''']):
            self.env['test_orm.message'].search([], order='discussion')

    def test_52_search_many2one_active_test(self):
        Model = self.env['test_orm.model_active_field']

        active_parent = Model.create({'name': 'Parent'})
        child_of_active = Model.create({'parent_id': active_parent.id})

        inactive_parent = Model.create({'name': 'Parent', 'active': False})
        child_of_inactive = Model.create({'parent_id': inactive_parent.id})

        self.assertEqual(
            self._search(Model, [('parent_id.name', '=', 'Parent')]),
            child_of_active + child_of_inactive,
        )
        self.assertEqual(
            self._search(Model, [('parent_id', '=', 'Parent')]),
            child_of_active + child_of_inactive,
        )
        self.assertEqual(
            Model.search([('id', 'child_of', active_parent.id)]),
            active_parent + child_of_active,
        )
        # weird semantics: active_parent is in both results but doesn't have a parent_id
        self.assertEqual(
            self._search(Model, [('parent_id', 'child_of', active_parent.id)]),
            active_parent + child_of_active,
        )
        self.assertEqual(
            self._search(Model, [('parent_id', 'child_of', 'Parent')]),
            active_parent + child_of_active + child_of_inactive,
        )

    def test_60_one2many_domain(self):
        """ test the cache consistency of a one2many field with a domain """
        discussion = self.env.ref('test_orm.discussion_0')
        message = discussion.messages[0]
        self.assertNotIn(message, discussion.important_messages)

        message.important = True
        self.assertIn(message, discussion.important_messages)

        # writing on very_important_messages should call its domain method
        self.assertIn(message, discussion.very_important_messages)
        discussion.write({'very_important_messages': [Command.clear()]})
        self.assertFalse(discussion.very_important_messages)
        self.assertFalse(message.exists())

    def test_60_many2many_domain(self):
        """ test the cache consistency of a many2many field with a domain """
        tag = self.env['test_orm.multi.tag'].create({'name': 'bar'})
        record = self.env['test_orm.multi'].create({'tags': tag.ids})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(type(record).tags.domain, [('name', 'ilike', 'a')])

        # the tag is in the many2many
        self.assertIn(tag, record.tags)

        # modify the tag; it should not longer be in the many2many
        tag.name = 'foo'
        self.assertNotIn(tag, record.tags)

        # modify again the tag; it should be back in the many2many
        tag.name = 'baz'
        self.assertIn(tag, record.tags)

    def test_61_one2many_domain(self):
        model = self.env['test_orm.inverse_m2o_ref']
        field = model._fields['model_ids']
        self.assertEqual(
            field.get_comodel_domain(model),
            Domain('const', '=', True) & Domain('res_model', '=', model._name),
        )
        self.assertEqual(
            field.get_description(self.env, ['domain'])['domain'],
            "([('const', '=', True)]) + ([('res_model', '=', 'test_orm.inverse_m2o_ref')])",
            "res_model should appear in the descripton of the domain",
        )

    def test_70_x2many_write(self):
        discussion = self.env.ref('test_orm.discussion_0')
        # See YTI FIXME
        self.env.invalidate_all()

        Message = self.env['test_orm.message']
        # There must be 3 messages, 0 important
        self.assertEqual(len(discussion.messages), 3)
        self.assertEqual(len(discussion.important_messages), 0)
        self.assertEqual(len(discussion.very_important_messages), 0)
        discussion.important_messages = [Command.create({
            'body': 'What is the answer?',
            'important': True,
        })]
        # There must be 4 messages, 1 important
        self.assertEqual(len(discussion.messages), 4)
        self.assertEqual(len(discussion.important_messages), 1)
        self.assertEqual(len(discussion.very_important_messages), 1)
        discussion.very_important_messages |= Message.new({
            'body': '42',
            'important': True,
        })
        # There must be 5 messages, 2 important
        self.assertEqual(len(discussion.messages), 5)
        self.assertEqual(len(discussion.important_messages), 2)
        self.assertEqual(len(discussion.very_important_messages), 2)

    def test_70_relational_inverse(self):
        """ Check the consistency of relational fields with inverse(s). """
        discussion = self.env.ref('test_orm.discussion_0')
        demo_discussion = discussion.with_user(self.user_demo)

        # check that the demo user sees the same messages
        self.assertEqual(demo_discussion.messages, discussion.messages)

        # See YTI FIXME
        self.env.flush_all()
        self.env.invalidate_all()

        # add a message as user demo
        messages = demo_discussion.messages
        message = messages.create({'discussion': discussion.id})
        self.assertEqual(demo_discussion.messages, messages + message)
        self.assertEqual(demo_discussion.messages, discussion.messages)

        # add a message as superuser
        messages = discussion.messages
        message = messages.create({'discussion': discussion.id})
        self.assertEqual(discussion.messages, messages + message)
        self.assertEqual(demo_discussion.messages, discussion.messages)

    def test_71_relational_inverse(self):
        """ Check the consistency of relational fields with inverse(s). """
        move1 = self.env['test_orm.move'].create({})
        move2 = self.env['test_orm.move'].create({})
        line = self.env['test_orm.move_line'].create({'move_id': move1.id})
        self.env.flush_all()
        self.env.invalidate_all()

        line.with_context(prefetch_fields=False).move_id

        # Setting 'move_id' updates the one2many field that is based on it,
        # which has a domain.  Here we check that evaluating the domain does not
        # accidentally override 'move_id' (by prefetch).
        line.move_id = move2
        self.assertEqual(line.move_id, move2)

    def test_72_relational_inverse(self):
        """ Check the consistency of relational fields with inverse(s). """
        move1 = self.env['test_orm.move'].create({})
        move2 = self.env['test_orm.move'].create({})

        # makes sure that line.move_id is flushed before search
        line = self.env['test_orm.move_line'].create({'move_id': move1.id})
        moves = self.env['test_orm.move'].search([('line_ids', 'in', line.id)])
        self.assertEqual(moves, move1)

        # makes sure that line.move_id is flushed before search
        line.move_id = move2
        moves = self.env['test_orm.move'].search([('line_ids', 'in', line.id)])
        self.assertEqual(moves, move2)

    def test_73_relational_inverse(self):
        """ Check the consistency of relational fields with inverse(s). """
        discussion1, discussion2 = self.env['test_orm.discussion'].create([
            {'name': "discussion1"}, {'name': "discussion2"},
        ])
        category1, category2 = self.env['test_orm.category'].create([
            {'name': "category1"}, {'name': "category2"},
        ])

        # assumption: category12 and category21 are in different order, but are
        # in the same order when put in a set()
        category12 = category1 + category2
        category21 = category2 + category1
        self.assertNotEqual(category12.ids, category21.ids)
        self.assertEqual(list(set(category12.ids)), list(set(category21.ids)))

        # make sure discussion1.categories is in cache; the write() below should
        # update the cache of discussion1.categories by appending category12.ids
        discussion1.categories
        category12.write({'discussions': [Command.link(discussion1.id)]})
        self.assertEqual(discussion1.categories.ids, category12.ids)

        # make sure discussion2.categories is in cache; the write() below should
        # update the cache of discussion2.categories by appending category21.ids
        discussion2.categories
        category21.write({'discussions': [Command.link(discussion2.id)]})
        self.assertEqual(discussion2.categories.ids, category21.ids)

    def test_96_order_m2o(self):
        belgium, congo = self.env['test_orm.country'].create([
            {'name': "Duchy of Brabant"},
            {'name': "Congo"},
        ])
        cities = self.env['test_orm.city'].create([
            {'name': "Brussels", 'country_id': belgium.id},
            {'name': "Kinshasa", 'country_id': congo.id},
        ])
        # cities are sorted by country_id, name
        self.assertEqual(cities.sorted().mapped('name'), ["Kinshasa", "Brussels"])

        # change order of countries, and check sorted()
        belgium.name = "Belgium"
        self.assertEqual(cities.sorted().mapped('name'), ["Brussels", "Kinshasa"])

    def test_97_ir_rule_m2m_field(self):
        """Ensures m2m fields can't be read if the left records can't be read.
        Also makes sure reading m2m doesn't take more queries than necessary."""
        tag = self.env['test_orm.multi.tag'].create({})
        record = self.env['test_orm.multi.line'].create({
            'name': 'image',
            'tags': [Command.link(tag.id)],
        })

        # only one query as admin: reading pivot table
        with self.assertQueryCount(1):
            # trick: if value is in cache, read() does not make any query
            record.invalidate_recordset(['tags'])
            record.read(['tags'])

        user = self.env['res.users'].create({'name': "user", 'login': "user"})
        record_user = record.with_user(user)

        # prep the following query count by caching access check related data
        record_user.invalidate_recordset(['tags'])
        record_user.read(['tags'])

        # only one query as user: reading pivot table
        with self.assertQueryCount(1):
            # trick: if value is in cache, read() does not make any query
            record_user.invalidate_recordset(['tags'])
            record_user.read(['tags'])

        # create a passing ir.rule
        self.env['ir.rule'].create({
            'model_id': self.env['ir.model']._get(record._name).id,
            'domain_force': "[('id', '=', %d)]" % record.id,
        })

        # prep the following query count by caching access check related data
        record_user.invalidate_recordset(['tags'])
        record_user.read(['tags'])

        # still only 1 query: reading pivot table
        # access rules are checked in python in this case
        with self.assertQueryCount(1):
            # trick: if value is in cache, read() does not make any query
            record_user.invalidate_recordset(['tags'])
            record_user.read(['tags'])

        # create a blocking ir.rule
        self.env['ir.rule'].create({
            'model_id': self.env['ir.model']._get(record._name).id,
            'domain_force': "[('id', '!=', %d)]" % record.id,
        })

        # ensure ir.rule is applied even when reading m2m
        with self.assertRaises(AccessError):
            record_user.read(['tags'])


class TestX2many(TransactionExpressionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls.env['res.users'].sudo().search([('login', '=', 'portal')])
        cls.partner_portal = cls.user_portal.partner_id

        if not cls.user_portal:
            cls.env['ir.config_parameter'].sudo().set_int('auth_password_policy.minlength', 4)
            cls.partner_portal = cls.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            cls.user_portal = cls.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': cls.partner_portal.id,
                'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
            })

    def test_definition_many2many(self):
        """ Test the definition of inherited many2many fields. """
        field = self.env['test_orm.multi.line']._fields['tags']
        self.assertEqual(field.relation, 'test_orm_multi_line_test_orm_multi_tag_rel')
        self.assertEqual(field.column1, 'test_orm_multi_line_id')
        self.assertEqual(field.column2, 'test_orm_multi_tag_id')

        field = self.env['test_orm.multi.line2']._fields['tags']
        self.assertEqual(field.relation, 'test_orm_multi_line2_test_orm_multi_tag_rel')
        self.assertEqual(field.column1, 'test_orm_multi_line2_id')
        self.assertEqual(field.column2, 'test_orm_multi_tag_id')

    def test_10_ondelete_many2many(self):
        """Test A can't be deleted when used on the relation."""
        record_a = self.env['test_orm.model_a'].create({'name': 'a'})
        record_b = self.env['test_orm.model_b'].create({'name': 'b'})
        record_a.write({
            'a_restricted_b_ids': [Command.set(record_b.ids)],
        })
        with self.assertRaises(psycopg2.IntegrityError):
            with mute_logger('odoo.sql_db'):
                record_a.unlink()
        # Test B is still cascade.
        record_b.unlink()
        self.assertFalse(record_b.exists())

    def test_11_ondelete_many2many(self):
        """Test B can't be deleted when used on the relation."""
        record_a = self.env['test_orm.model_a'].create({'name': 'a'})
        record_b = self.env['test_orm.model_b'].create({'name': 'b'})
        record_a.write({
            'b_restricted_b_ids': [Command.set(record_b.ids)],
        })
        with self.assertRaises(psycopg2.IntegrityError):
            with mute_logger('odoo.sql_db'):
                record_b.unlink()
        # Test A is still cascade.
        record_a.unlink()
        self.assertFalse(record_a.exists())

    def test_12_active_test_one2many(self):
        Model = self.env['test_orm.model_active_field']

        parent = Model.create({})
        self.assertFalse(parent.children_ids)

        # create with implicit active_test=True in context
        child1, child2 = Model.create([
            {'parent_id': parent.id, 'active': True},
            {'parent_id': parent.id, 'active': False},
        ])
        act_children = child1
        all_children = child1 + child2
        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)

        # create with active_test=False in context
        child3, child4 = Model.with_context(active_test=False).create([
            {'parent_id': parent.id, 'active': True},
            {'parent_id': parent.id, 'active': False},
        ])
        act_children = child1 + child3
        all_children = child1 + child2 + child3 + child4
        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)

        # replace active children
        parent.write({'children_ids': [Command.set([child1.id])]})
        act_children = child1
        all_children = child1 + child2 + child4
        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)

        # replace all children
        parent.with_context(active_test=False).write({'children_ids': [Command.set([child1.id])]})
        act_children = child1
        all_children = child1
        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)

        # check recomputation of inactive records
        parent.write({'children_ids': [Command.set(child4.ids)]})
        self.assertTrue(child4.parent_active)
        parent.active = False
        self.assertFalse(child4.parent_active)

    def test_12_active_test_one2many_with_context(self):
        Model = self.env['test_orm.model_active_field']
        parent = Model.create({})
        all_children = Model.create([
            {'parent_id': parent.id, 'active': True},
            {'parent_id': parent.id, 'active': False},
        ])
        act_children = all_children[0]

        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)

        self.assertEqual(parent.all_children_ids, all_children)
        self.assertEqual(parent.with_context(active_test=True).all_children_ids, all_children)
        self.assertEqual(parent.with_context(active_test=False).all_children_ids, all_children)

        self.assertEqual(parent.active_children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=True).active_children_ids, act_children)
        self.assertEqual(parent.with_context(active_test=False).active_children_ids, act_children)

        # check read()
        self.env.invalidate_all()
        self.assertEqual(parent.children_ids, act_children)
        self.assertEqual(parent.all_children_ids, all_children)
        self.assertEqual(parent.active_children_ids, act_children)

        self.env.invalidate_all()
        self.assertEqual(parent.with_context(active_test=False).children_ids, all_children)
        self.assertEqual(parent.with_context(active_test=False).all_children_ids, all_children)
        self.assertEqual(parent.with_context(active_test=False).active_children_ids, act_children)

    def test_12_active_test_one2many_search(self):
        Model = self.env['test_orm.model_active_field']
        parent = Model.create({
            'children_ids': [
                Command.create({'name': 'A', 'active': True}),
                Command.create({'name': 'B', 'active': False}),
            ],
        })

        # a one2many field without context does not match its inactive children
        self.assertIn(parent, self._search(Model, [('children_ids.name', '=', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('children_ids.name', '=', 'B')]))
        # Same result when it used _search_display_name
        self.assertIn(parent, self._search(Model, [('children_ids', '=', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('children_ids', '=', 'B')]))
        # Same result with the child_of operator
        self.assertIn(parent, self._search(Model, [('children_ids', 'child_of', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('children_ids', 'child_of', 'B')]))

        # a one2many field with active_test=False matches its inactive children
        self.assertIn(parent, self._search(Model, [('all_children_ids.name', '=', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_children_ids.name', '=', 'B')]))
        # Same result when it used _search_display_name
        self.assertIn(parent, self._search(Model, [('all_children_ids', '=', 'A')]))
        # Same result with the child_of operator
        self.assertIn(parent, self._search(Model, [('all_children_ids', 'child_of', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_children_ids', '=', 'B')]))
        # Same result with the child_of operator
        self.assertIn(parent, self._search(Model, [('all_children_ids', 'child_of', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_children_ids', 'child_of', 'B')]))

    def test_12_active_test_many2many_search(self):
        Model = self.env['test_orm.model_active_field']
        parent = Model.create({
            'relatives_ids': [
                Command.create({'name': 'A', 'active': True}),
                Command.create({'name': 'B', 'active': False}),
            ],
        })
        child_a, child_b = parent.with_context(active_test=False).relatives_ids
        # TODO all_relatives_ids is empty, because it is another fields using
        # the same backend table as relative_ids
        Model.invalidate_model(['all_relatives_ids'])

        # a many2many field without context does not match its inactive children
        self.assertIn(parent, self._search(Model, [('relatives_ids.name', '=', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('relatives_ids.name', '=', 'B')]))
        # Same result when it used _search_display_name
        self.assertIn(parent, self._search(Model, [('relatives_ids', '=', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('relatives_ids', '=', 'B')]))
        # Same result with the child_of operator
        self.assertIn(parent, self._search(Model, [('relatives_ids', 'child_of', child_a.id)]))
        self.assertIn(parent, self._search(Model, [('relatives_ids', 'child_of', 'A')]))
        self.assertNotIn(parent, self._search(Model, [('relatives_ids', 'child_of', child_b.id)]))
        self.assertNotIn(parent, self._search(Model, [('relatives_ids', 'child_of', 'B')]))

        # a many2many field with active_test=False matches its inactive children
        self.assertIn(parent, self._search(Model, [('all_relatives_ids.name', '=', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_relatives_ids.name', '=', 'B')]))
        # Same result when it used _search_display_name
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', '=', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', '=', 'B')]))
        # Same result with the child_of operator
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', 'child_of', child_a.id)]))
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', 'child_of', 'A')]))
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', 'child_of', child_b.id)]))
        self.assertIn(parent, self._search(Model, [('all_relatives_ids', 'child_of', 'B')]))

    def test_search_many2many(self):
        """ Tests search on many2many fields. """
        tags = self.env['test_orm.multi.tag']
        tagA = tags.create({})
        tagB = tags.create({})
        tagC = tags.create({})
        recs = self.env['test_orm.multi.line']
        recW = recs.create({})
        recX = recs.create({'tags': [Command.link(tagA.id)]})
        recY = recs.create({'tags': [Command.link(tagB.id)]})
        recZ = recs.create({'tags': [Command.link(tagA.id), Command.link(tagB.id)]})
        recs = recW + recX + recY + recZ

        # test 'in'
        result = self._search(recs, [('tags', 'in', (tagA + tagB).ids)])
        self.assertEqual(result, recX + recY + recZ)

        result = self._search(recs, [('tags', 'in', tagA.ids)])
        self.assertEqual(result, recX + recZ)

        result = self._search(recs, [('tags', 'in', tagB.ids)])
        self.assertEqual(result, recY + recZ)

        result = self._search(recs, [('tags', 'in', tagC.ids)])
        self.assertEqual(result, recs.browse())

        result = self._search(recs, [('tags', 'in', [])])
        self.assertEqual(result, recs.browse())

        # test 'not in'
        result = self._search(recs, [('id', 'in', recs.ids), ('tags', 'not in', (tagA + tagB).ids)])
        self.assertEqual(result, recs - recX - recY - recZ)

        result = self._search(recs, [('id', 'in', recs.ids), ('tags', 'not in', tagA.ids)])
        self.assertEqual(result, recs - recX - recZ)

        result = self._search(recs, [('id', 'in', recs.ids), ('tags', 'not in', tagB.ids)])
        self.assertEqual(result, recs - recY - recZ)

        result = self._search(recs, [('id', 'in', recs.ids), ('tags', 'not in', tagC.ids)])
        self.assertEqual(result, recs)

        result = self._search(recs, [('id', 'in', recs.ids), ('tags', 'not in', [])])
        self.assertEqual(result, recs)

        # special case: compare with False
        result = self._search(recs, [('id', 'in', recs.ids), ('tags', '=', False)])
        self.assertEqual(result, recW)

        result = self._search(recs, [('id', 'in', recs.ids), ('tags', '!=', False)])
        self.assertEqual(result, recs - recW)

    def test_search_one2many(self):
        """ Tests search on one2many fields. """
        recs = self.env['test_orm.multi']
        recX = recs.create({'lines': [Command.create({}), Command.create({})]})
        recY = recs.create({'lines': [Command.create({})]})
        recZ = recs.create({})
        recs = recX + recY + recZ
        line1, line2, line3 = recs.lines
        line4 = recs.create({'lines': [Command.create({})]}).lines
        line0 = line4.create({})

        # test 'in'
        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'in', (line1 + line2 + line3 + line4).ids)])
        self.assertEqual(result, recX + recY)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'in', (line1 + line3 + line4).ids)])
        self.assertEqual(result, recX + recY)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'in', (line1 + line4).ids)])
        self.assertEqual(result, recX)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'in', line4.ids)])
        self.assertEqual(result, recs.browse())

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'in', [])])
        self.assertEqual(result, recs.browse())

        # test 'not in'
        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', (line1 + line2 + line3).ids)])
        self.assertEqual(result, recs - recX - recY)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', (line1 + line3).ids)])
        self.assertEqual(result, recs - recX - recY)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', line1.ids)])
        self.assertEqual(result, recs - recX)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', (line1 + line4).ids)])
        self.assertEqual(result, recs - recX)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', line4.ids)])
        self.assertEqual(result, recs)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', [])])
        self.assertEqual(result, recs)

        # test 'not in' where the lines contain NULL values
        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', (line1 + line0).ids)])
        self.assertEqual(result, recs - recX)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', 'not in', line0.ids)])
        self.assertEqual(result, recs)

        # special case: compare with False
        result = self._search(recs, [('id', 'in', recs.ids), ('lines', '=', False)])
        self.assertEqual(result, recZ)

        result = self._search(recs, [('id', 'in', recs.ids), ('lines', '!=', False)])
        self.assertEqual(result, recs - recZ)

    def test_create_batch_m2m(self):
        lines = self.env['test_orm.multi.line'].create([{
            'tags': [Command.create({'name': str(j)}) for j in range(3)],
        } for i in range(3)])
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertEqual(len(line.tags), 3)

    def test_custom_m2m(self):
        model_id = self.env['ir.model']._get_id('res.partner')
        field = self.env['ir.model.fields'].create({
            'name': 'x_foo',
            'field_description': 'Foo',
            'model_id': model_id,
            'ttype': 'many2many',
            'relation': 'res.country',
            'store': False,
        })
        self.assertTrue(field.unlink())

    def test_custom_m2m_related(self):
        # this checks the ondelete of a related many2many field
        model_id = self.env['ir.model']._get_id('res.partner')
        field = self.env['ir.model.fields'].create({
            'name': 'x_foo',
            'field_description': 'Foo',
            'model_id': model_id,
            'ttype': 'many2many',
            'relation': 'res.partner.category',
            'related': 'category_id',
            'readonly': True,
            'store': True,
        })
        self.assertTrue(field.unlink())


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequiredMany2one(TransactionCase):

    def test_explicit_ondelete(self):
        field = self.env['test_orm.req_m2o']._fields['foo']
        self.assertEqual(field.ondelete, 'cascade')

    def test_implicit_ondelete(self):
        field = self.env['test_orm.req_m2o']._fields['bar']
        self.assertEqual(field.ondelete, 'restrict')

    def test_explicit_set_null(self):
        Model = self.env['test_orm.req_m2o']
        field = Model._fields['foo']

        # clean up registry after this test
        self.addCleanup(self.registry.reset_changes)
        self.patch(field, 'ondelete', 'set null')

        with self.assertRaises(ValueError):
            field.setup_nonrelated(Model)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequiredMany2oneTransient(TransactionCase):

    def test_explicit_ondelete(self):
        field = self.env['test_orm.req_m2o_transient']._fields['foo']
        self.assertEqual(field.ondelete, 'restrict')

    def test_implicit_ondelete(self):
        field = self.env['test_orm.req_m2o_transient']._fields['bar']
        self.assertEqual(field.ondelete, 'cascade')

    def test_explicit_set_null(self):
        Model = self.env['test_orm.req_m2o_transient']
        field = Model._fields['foo']

        # clean up registry after this test
        self.addCleanup(self.registry.reset_changes)
        self.patch(field, 'ondelete', 'set null')

        with self.assertRaises(ValueError):
            field.setup_nonrelated(Model)


@tagged('m2oref')
class TestMany2oneReference(TransactionExpressionCase):

    def test_delete_m2o_reference_records(self):
        m = self.env['test_orm.model_many2one_reference']
        self.env.cr.execute("SELECT max(id) FROM test_orm_model_many2one_reference")
        ids = self.env.cr.fetchone()
        # fake record to emulate the unlink of a non-existant record
        foo = m.browse(1 if not ids[0] else (ids[0] + 1))
        self.assertTrue(foo.unlink())

    def test_search_inverse_one2many_bypass_search_access(self):
        record = self.env['test_orm.inverse_m2o_ref'].create({})

        # the one2many field 'model_ids' should be bypass_search_access=True
        self.patch(type(record).model_ids, 'bypass_search_access', True)

        # create a reference to record
        reference = self.env['test_orm.model_many2one_reference'].create({'res_id': record.id})
        reference.res_model = record._name

        # the model field 'res_model' is not in database yet
        self.assertIn(reference.id, self.env._field_dirty[reference._fields['res_model']])

        # searching on the one2many should flush the field 'res_model'
        records = record.search([('model_ids.create_date', '!=', False)])
        self.assertIn(record, records)

        # filtered should be aligned
        # TODO right now, need to invalidate because the inverse of
        # many2one_reference is not updated
        record.invalidate_model()
        self._search(record, [('model_ids.create_date', '!=', False)])
