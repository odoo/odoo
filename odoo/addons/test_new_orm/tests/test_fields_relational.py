import psycopg2

from unittest.mock import patch

from odoo import Command
from odoo.fields import Command, Domain
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.tools import mute_logger
from odoo.tests.common import TransactionCase, new_test_user, tagged, users

from odoo.addons.base.tests.test_expression import TransactionExpressionCase
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class Many2manyCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ship = self.env['test_orm.ship'].create({'name': 'Colombus'})
        # the ship contains one prisoner
        self.env['test_orm.prisoner'].create({
            'name': 'Brian',
            'ship_ids': self.ship.ids,
        })
        # the ship contains one pirate
        self.blackbeard = self.env['test_orm.pirate'].create({
            'name': 'Black Beard',
            'ship_ids': self.ship.ids,
        })
        self.redbeard = self.env['test_orm.pirate'].create({'name': 'Red Beard'})

    def test_not_in_relation(self):
        pirates = self.env['test_orm.pirate'].search([('ship_ids', 'not in', self.ship.ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)

    def test_not_in_relation_as_query(self):
        # ship_ids is a Query object
        ship_ids = self.env['test_orm.ship']._search([('name', '=', 'Colombus')])
        pirates = self.env['test_orm.pirate'].search([('ship_ids', 'not in', ship_ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)

    def test_attachment_m2m_link(self):
        user = new_test_user(self.env, 'foo', groups='base.group_system')

        attachments = self.env['ir.attachment'].create({
            'res_model': self.ship._name,
            'res_id': self.ship.id,
            'name': 'test',
        }).with_user(user)
        record = self.env['test_orm.attachment.host'].create({
            'real_binary': b'aGV5',
        }).with_user(user)
        attachments += attachments.sudo().search([
            ('res_model', '=', record._name),
            ('res_field', '=', 'real_binary'),
        ])
        self.assertEqual(len(attachments), 2)
        record.real_m2m_attachment_ids = [Command.link(a.id) for a in attachments]

        self.assertFalse(record.env.su)

        record.invalidate_model()
        self.assertEqual(len(record.real_m2m_attachment_ids), len(attachments))

    def test_bypass_search_access(self):
        user = new_test_user(self.env, 'foo', groups='base.group_system')

        attachment = self.env['test_orm.attachment'].create({
            'res_model': self.ship._name,
            'res_id': self.ship.id,
        }).with_user(user)
        record = self.env['test_orm.attachment.host'].create({
            'm2m_attachment_ids': [Command.link(attachment.id)],
        }).with_user(user)

        self.assertFalse(record.env.su)

        field = record._fields['m2m_attachment_ids']
        self.assertTrue(field.bypass_search_access)

        # check that attachments are searched with bypass_access, and filtered with _check_access()
        Attachment = type(attachment)
        with (
            patch.object(Attachment, '_search', autospec=True, side_effect=Attachment._search) as _search,
            patch.object(Attachment, '_check_access', autospec=True, return_value=None) as _check_access,
        ):
            record.invalidate_model()
            record.m2m_attachment_ids
            _search.assert_called_once_with(attachment.browse(), Domain.TRUE, order='id', bypass_access=True)
            _check_access.assert_called_once_with(attachment, 'read')

        # check that otherwise, attachments are searched without bypass_access
        self.patch(field, 'bypass_search_access', False)
        with (
            patch.object(Attachment, '_search', autospec=True, side_effect=Attachment._search) as _search,
            patch.object(Attachment, '_check_access', autospec=True, return_value=None) as _check_access,
        ):
            record.invalidate_model()
            record.m2m_attachment_ids
            _search.assert_called_once_with(attachment.browse(), Domain.TRUE, order='id', bypass_access=False)
            _check_access.assert_called_once_with(attachment.browse(), 'read')


class One2manyCase(TransactionExpressionCase):
    def setUp(self):
        super().setUp()
        self.Line = self.env["test_orm.multi.line"]
        self.multi = self.env["test_orm.multi"].create({
            "name": "What is up?",
        })

        # data for One2many with inverse field Integer
        self.Edition = self.env["test_orm.creativework.edition"]
        self.Book = self.env["test_orm.creativework.book"]
        self.Movie = self.env["test_orm.creativework.movie"]

        book_model_id = self.env['ir.model'].search([('model', '=', self.Book._name)]).id
        movie_model_id = self.env['ir.model'].search([('model', '=', self.Movie._name)]).id

        books_data = (
            ('Imaginary book', ()),
            ('Another imaginary book', ()),
            ('Nineteen Eighty Four', ('First edition', 'Fourth Edition')),
        )

        movies_data = (
            ('The Gold Rush', ('1925 (silent)', '1942')),
            ('Imaginary movie', ()),
            ('Another imaginary movie', ()),
        )

        for name, editions in books_data:
            book_id = self.Book.create({'name': name}).id
            for edition in editions:
                self.Edition.create({'res_model_id': book_model_id, 'name': edition, 'res_id': book_id})

        for name, editions in movies_data:
            movie_id = self.Movie.create({'name': name}).id
            for edition in editions:
                self.Edition.create({'res_model_id': movie_model_id, 'name': edition, 'res_id': movie_id})

    def operations(self):
        """Run operations on o2m fields to check all works fine."""
        # Check the lines first
        self.assertItemsEqual(
            self.multi.lines.mapped('name'),
            [str(i) for i in range(10)])
        # Modify the first line and drop the last one
        self.multi.lines[0].name = "hello"
        self.multi.lines = self.multi.lines[:-1]
        self.assertEqual(len(self.multi.lines), 9)
        self.assertIn("hello", self.multi.lines.mapped('name'))
        if not self.multi.id:
            return
        # Invalidate the cache and check again; this crashes if the value
        # of self.multi.lines in cache contains new records
        self.env.invalidate_all()
        self.assertEqual(len(self.multi.lines), 9)
        self.assertIn("hello", self.multi.lines.mapped('name'))

    def test_new_one_by_one(self):
        """Check lines created with ``new()`` and appended one by one."""
        for name in range(10):
            self.multi.lines |= self.Line.new({"name": str(name)})
        self.operations()

    def test_new_single(self):
        """Check lines created with ``new()`` and added in one step."""
        self.multi.lines = self.Line.browse(
            [self.Line.new({"name": str(name)}).id for name in range(10)],
        )
        self.operations()

    def test_create_one_by_one(self):
        """Check lines created with ``create()`` and appended one by one."""
        for name in range(10):
            self.multi.lines |= self.Line.create({"name": str(name)})
        self.operations()

    def test_create_single(self):
        """Check lines created with ``create()`` and added in one step."""
        self.multi.lines = self.Line.browse(
            [self.Line.create({"name": str(name)}).id for name in range(10)],
        )
        self.operations()

    def test_rpcstyle_one_by_one(self):
        """Check lines created with RPC style and appended one by one."""
        for name in range(10):
            self.multi.lines = [Command.create({"name": str(name)})]
        self.operations()

    def test_rpcstyle_one_by_one_on_new(self):
        self.multi = self.env["test_orm.multi"].new({
            "name": "What is up?",
        })
        for name in range(10):
            self.multi.lines = [Command.create({"name": str(name)})]
        self.operations()

    def test_rpcstyle_single(self):
        """Check lines created with RPC style and added in one step"""
        self.multi.lines = [Command.create({'name': str(name)}) for name in range(10)]
        self.operations()

    def test_rpcstyle_single_on_new(self):
        self.multi = self.env["test_orm.multi"].new({
            "name": "What is up?",
        })
        self.multi.lines = [Command.create({'name': str(name)}) for name in range(10)]
        self.operations()

    def test_many2one_integer(self):
        """Test several models one2many with same inverse Integer field"""
        # utility function to convert records to tuples with id,name
        def t(records):
            return records.mapped(lambda r: (r.id, r.name))

        books = self.Book.search([])
        movies = self.Movie.search([])
        movies_without_edition = movies.filtered(lambda r: not r.editions)
        movies_with_edition = movies.filtered(lambda r: r.editions)
        movie_editions = movies_with_edition.editions
        one_movie_edition = movie_editions[0]

        res_movies_without_edition = self._search(self.Movie, [('editions', '=', False)])
        self.assertItemsEqual(t(res_movies_without_edition), t(movies_without_edition))

        res_movies_with_edition = self._search(self.Movie, [('editions', '!=', False)])
        self.assertItemsEqual(t(res_movies_with_edition), t(movies_with_edition))

        res_books_with_movie_edition = self._search(self.Book, [('editions', 'in', movie_editions.ids)])
        self.assertFalse(t(res_books_with_movie_edition))

        res_books_without_movie_edition = self._search(self.Book, [('editions', 'not in', movie_editions.ids)])
        self.assertItemsEqual(t(res_books_without_movie_edition), t(books))

        res_books_without_one_movie_edition = self._search(self.Book, [('editions', 'not in', movie_editions[:1].ids)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition), t(books))

        res_books_with_one_movie_edition_name = self._search(self.Book, [('editions', '=', movie_editions[:1].name)])
        self.assertFalse(t(res_books_with_one_movie_edition_name))

        res_books_without_one_movie_edition_name = self._search(self.Book, [('editions', '!=', movie_editions[:1].name)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition_name), t(books))

        res_movies_not_of_edition_name = self._search(self.Movie, [('editions', '!=', one_movie_edition.name)])
        self.assertItemsEqual(t(res_movies_not_of_edition_name), t(movies.filtered(lambda r: one_movie_edition not in r.editions)))

    def test_merge_partner(self):
        model = self.env['test_orm.field_with_caps']
        partner = self.env['res.partner']

        p1 = partner.create({'name': 'test1'})
        p2 = partner.create({'name': 'test2'})

        model1 = model.create({'pArTneR_321_id': p1.id})
        model2 = model.create({'pArTneR_321_id': p2.id})

        self.env['base.partner.merge.automatic.wizard']._merge((p1 + p2).ids, p1)

        self.assertFalse(p2.exists())
        self.assertTrue(p1.exists())

        self.assertEqual(model1.pArTneR_321_id, p1)
        self.assertTrue(model2.exists())
        self.assertEqual(model2.pArTneR_321_id, p1)

    def test_merge_partner_archived(self):
        partner = self.env['res.partner']

        p1 = partner.create({'name': 'test1'})
        p2 = partner.create({'name': 'test2'})
        p3 = partner.create({'name': 'test3', 'active': False})
        partners_ids = (p1 + p2 + p3)

        wizard = self.env['base.partner.merge.automatic.wizard'].with_context(active_ids=partners_ids.ids, active_model='res.partner').create({})

        self.assertEqual(wizard.partner_ids, partners_ids)
        self.assertEqual(wizard.dst_partner_id, p2)

        wizard.action_merge()

        self.assertFalse(p1.exists())
        self.assertTrue(p2.exists())
        self.assertFalse(p3.exists())

    def test_partner_merge_wizard_more_than_one_user_error(self):
        """ Test that partners cannot be merged if linked to more than one user even if only one is active. """
        p1, p2, dst_partner = self.env['res.partner'].create([{'name': f'test{idx + 1}'} for idx in range(3)])
        u1, u2 = self.env['res.users'].create([{'name': 'test1', 'login': 'test1', 'partner_id': p1.id},
                                               {'name': 'test2', 'login': 'test2', 'partner_id': p2.id}])
        MergeWizard_with_context = self.env['base.partner.merge.automatic.wizard'].with_context(
            active_ids=(u1.partner_id + u2.partner_id + dst_partner).ids, active_model='res.partner')

        with self.assertRaises(UserError):
            MergeWizard_with_context.create({}).action_merge()

        u2.action_archive()
        with self.assertRaises(UserError):
            MergeWizard_with_context.create({}).action_merge()

        u2.unlink()
        MergeWizard_with_context.create({}).action_merge()
        self.assertTrue(dst_partner.exists())
        self.assertEqual(u1.partner_id.id, dst_partner.id)

    def test_cache_invalidation(self):
        """ Cache invalidation for one2many with integer inverse. """
        record0 = self.env['test_orm.attachment.host'].create({})
        with self.assertQueryCount(0):
            self.assertFalse(record0.attachment_ids, "inconsistent cache")

        # creating attachment must compute name and invalidate attachment_ids
        attachment = self.env['test_orm.attachment'].create({
            'res_model': record0._name,
            'res_id': record0.id,
        })
        self.env.flush_all()
        with self.assertQueryCount(0):
            self.assertEqual(attachment.name, record0.display_name,
                             "field should be computed")
        with self.assertQueryCount(1):
            self.assertEqual(record0.attachment_ids, attachment, "inconsistent cache")

        # creating a host should not attempt to recompute attachment.name
        with self.assertQueryCount(1):
            record1 = self.env['test_orm.attachment.host'].create({})
        with self.assertQueryCount(0):
            # field res_id should not have been invalidated
            attachment.res_id
        with self.assertQueryCount(0):
            self.assertFalse(record1.attachment_ids, "inconsistent cache")

        # writing on res_id must recompute name and invalidate attachment_ids
        attachment.res_id = record1.id
        self.env.flush_all()
        with self.assertQueryCount(0):
            self.assertEqual(attachment.name, record1.display_name,
                             "field should be recomputed")
        with self.assertQueryCount(1):
            self.assertEqual(record1.attachment_ids, attachment, "inconsistent cache")
        with self.assertQueryCount(1):
            self.assertFalse(record0.attachment_ids, "inconsistent cache")

    def test_recompute(self):
        """ test recomputation of fields that indirecly depend on one2many """
        discussion = self.env.ref('test_orm.discussion_0')
        self.assertTrue(discussion.messages)

        # detach message from discussion
        message = discussion.messages[0]
        message.discussion = False

        # DLE P54: a computed stored field should not depend on the context
        # writing on the one2many and actually modifying the relation must
        # trigger recomputation of fields that depend on its inverse many2one
        # self.assertNotIn(message, discussion.messages)
        # discussion.with_context(compute_name='X').write({'messages': [(4, message.id)]})
        # self.assertEqual(message.name, 'X')

        # writing on the one2many without modifying the relation should not
        # trigger recomputation of fields that depend on its inverse many2one
        # self.assertIn(message, discussion.messages)
        # discussion.with_context(compute_name='Y').write({'messages': [(4, message.id)]})
        # self.assertEqual(message.name, 'X')

    def test_dont_write_the_existing_childs(self):
        """ test that the existing child should not be changed when adding a new child to the parent.
        This is the behaviour of the form view."""
        parent = self.env['test_orm.model_parent_m2o'].create({
            'name': 'parent',
            'child_ids': [Command.create({'name': 'A'})],
        })
        a = parent.child_ids[0]
        parent.write({'child_ids': [Command.link(a.id), Command.create({'name': 'B'})]})

    def test_create_with_commands(self):
        # create lines and warm up caches
        order = self.env['test_orm.order'].create({
            'line_ids': [Command.create({'product': name}) for name in ('set', 'sept')],
        })
        line1, line2 = order.line_ids

        # INSERT, UPDATE of line1
        with self.assertQueryCount(2):
            self.env['test_orm.order'].create({
                'line_ids': [Command.set(line1.ids)],
            })

        # INSERT order, INSERT thief, UPDATE of line1+line2
        with self.assertQueryCount(3):
            order = self.env['test_orm.order'].create({
                'line_ids': [Command.set(line1.ids)],
            })
            thief = self.env['test_orm.order'].create({
                'line_ids': [Command.set((line1 + line2).ids)],
            })

        # the lines have been stolen by thief
        self.assertFalse(order.line_ids)
        self.assertEqual(thief.line_ids, line1 + line2)

    def test_recomputation_ends(self):
        """ Regression test for neverending recomputation. """
        parent = self.env['test_orm.model_parent_m2o'].create({'name': 'parent'})
        child = self.env['test_orm.model_child_m2o'].create({'name': 'A', 'parent_id': parent.id})
        self.assertEqual(child.size1, 6)

        # delete parent, and check that recomputation ends
        parent.unlink()
        self.env.flush_all()

    def test_compute_stored_many2one_one2many(self):
        container = self.env['test_orm.compute.container'].create({'name': 'Foo'})
        self.assertFalse(container.member_ids)
        member = self.env['test_orm.compute.member'].create({'name': 'Foo'})
        # at this point, member.container_id must be computed for member to
        # appear in container.member_ids
        self.assertEqual(container.member_ids, member)
        self.assertEqual(container.member_count, 1)

        # Changing member.name will trigger recomputing member.container_id,
        # container.member_ids and container.member_count. Since we are setting
        # the name to bar, it will be detached from container, resulting in a
        # member_count of zero on the container.
        member.name = 'Bar'
        self.assertEqual(container.member_count, 0)

        # Reattach member to container again
        member.name = 'Foo'
        self.assertEqual(container.member_count, 1)

    def test_reward_line_delete(self):
        order = self.env['test_orm.order'].create({
            'line_ids': [
                Command.create({'product': 'a'}),
                Command.create({'product': 'b'}),
                Command.create({'product': 'b', 'reward': True}),
            ],
        })
        line0, line1, line2 = order.line_ids

        # this is what the client sends to delete the 2nd line; it should not
        # crash when deleting the 2nd line automatically deletes the 3rd line
        order.write({
            'line_ids': [
                Command.link(line0.id),
                Command.delete(line1.id),
                Command.link(line2.id),
            ],
        })
        self.assertEqual(order.line_ids, line0)

        # but linking a missing line on purpose is an error
        with self.assertRaises(MissingError):
            order.write({
                'line_ids': [Command.link(line0.id), Command.link(line1.id)],
            })

    def test_new_real_interactions(self):
        """ Test and specify the interactions between new and real records.
        Through m2o and o2m, with real/unreal records on both sides, the behavior
        varies greatly.  At least, the behavior will be clearly consistent and any
        change will have to adapt the current test.
        """
        ##############
        # REAL - NEW #
        ##############
        parent = self.env['test_orm.model_parent_m2o'].create({'name': 'parentB'})
        new_child = self.env['test_orm.model_child_m2o'].new({'name': 'B', 'parent_id': parent.id})

        # wanted behavior: when creating a new with a real parent id, the child
        # isn't present in the parent childs until true creation
        self.assertFalse(parent.child_ids)
        self.assertEqual(new_child.parent_id, parent)

        # current (wanted?) behavior: when adding a new record to a real record
        # o2m, the record is created, but not linked to the new in cache
        # REAL.O2M += NEW RECORD
        parent.child_ids += new_child
        self.assertTrue(parent.child_ids)
        self.assertNotEqual(parent.child_ids, new_child)

        #############
        # NEW - NEW #
        #############
        # wanted behavior: linking new records to new records is totally fine
        new_parent = self.env['test_orm.model_parent_m2o'].new({
            "name": 'parentC3PO',
            "child_ids": [(0, 0, {"name": "C3"})],
        })
        self.assertEqual(new_parent, new_parent.child_ids.parent_id)
        self.assertFalse(new_parent.id)
        self.assertTrue(new_parent.child_ids)
        self.assertFalse(new_parent.child_ids.ids)

        new_child = self.env['test_orm.model_child_m2o'].new({
            'name': 'PO',
        })
        new_parent.child_ids += new_child
        self.assertIn(new_child, new_parent.child_ids)
        self.assertEqual(len(new_parent.child_ids), 2)
        self.assertListEqual(new_parent.child_ids.mapped('name'), ['C3', 'PO'])

        new_child2 = self.env['test_orm.model_child_m2o'].new({
            'name': 'R2D2',
            'parent_id': new_parent.id,
        })
        self.assertIn(new_child2, new_parent.child_ids)
        self.assertEqual(len(new_parent.child_ids), 3)
        self.assertListEqual(new_parent.child_ids.mapped('name'), ['C3', 'PO', 'R2D2'])

        ###############################
        # NEW TO REAL CONVERSION TEST #
        ###############################

        # A bit out of scope, but was interesting to check everything was
        # working fine on the way.
        name = type(new_parent).name
        child_ids = type(new_parent).child_ids
        parent = self.env['test_orm.model_parent_m2o'].create({
            'name': name.convert_to_write(new_parent.name, new_parent),
            'child_ids': child_ids.convert_to_write(new_parent.child_ids, new_parent),
        })
        self.assertEqual(len(parent.child_ids), 3)
        self.assertEqual(parent, parent.child_ids.parent_id)
        self.assertEqual(parent.child_ids.mapped('name'), ['C3', 'PO', 'R2D2'])

    def test_parent_id(self):
        Team = self.env['test_orm.team']
        Member = self.env['test_orm.team.member']

        team1 = Team.create({'name': 'ORM'})
        team2 = Team.create({'name': 'Bugfix', 'parent_id': team1.id})
        team3 = Team.create({'name': 'Support', 'parent_id': team2.id})

        Member.create({'name': 'Raphael', 'team_id': team1.id})
        member2 = Member.create({'name': 'Noura', 'team_id': team3.id})
        Member.create({'name': 'Ivan', 'team_id': team2.id})

        # In this specific case...
        self.assertEqual(member2.id, member2.team_id.parent_id.id)

        # ...we had an infinite recursion on making the following search, but not anymore
        Team.search([('member_ids', 'child_of', member2.id)])

        # Also, test a simple infinite loop if record is marked as a parent of itself
        team1.parent_id = team1.id
        # Check that the search is not stuck in the loop
        self._search(Team, [('id', 'parent_of', team1.id)])
        self._search(Team, [('id', 'child_of', team1.id)])

    def test_create_one2many_with_unsearchable_field(self):
        unsearchableO2M = self.env['test_orm.unsearchable.o2m']

        # Create a parent record
        parent_record1 = unsearchableO2M.create({
            'name': 'Parent 1',
        })

        # Create another parent record
        parent_record2 = unsearchableO2M.create({
            'name': 'Parent 2',
        })

        children = {parent_record1.id: [], parent_record2.id: []}
        # Create child records linked to parent_record1
        for i in range(5):
            child = unsearchableO2M.create({
                'name': f'Child {i}',
                'stored_parent_id': parent_record1.id,
                'parent_id': parent_record1.id,
            })
            self.assertEqual(child.parent_id, parent_record1)
            children[parent_record1.id].append(child.id)

        # Create child records linked to parent_record2
        for i in range(5, 10):
            child = unsearchableO2M.create({
                'name': f'Child {i}',
                'stored_parent_id': parent_record2.id,
                'parent_id': parent_record2.id,
            })
            self.assertEqual(child.parent_id, parent_record2)
            children[parent_record2.id].append(child.id)

        # invalidating the cache to force reading one2many again
        self.env.invalidate_all()
        with self.assertRaisesRegex(ValueError, r'it is not stored'):
            # Make sure the parent_record1 only has its own child records
            self.assertEqual(parent_record1.child_ids.ids, children[parent_record1.id])

    def test_computed_inverse_one2many(self):
        record = self.env['test_orm.computed_inverse_one2many'].create({
            'name': 'SuperRecord',
            'low_priority_line_ids': [Command.create({
                'name': 'SuperChild 01',
                'priority': 1,
            })],
        })
        self.assertTrue(record.low_priority_line_ids.ids)

        record.low_priority_line_ids = [Command.create({
            'name': 'SuperChild 02',
            'priority': 2,
        })]
        self.assertEqual(len(record.low_priority_line_ids.ids), 2)


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


class SudoCommands(TransactionCaseWithUserDemo):

    @mute_logger('odoo.addons.base.models.ir_model')
    @users('demo')
    def test_sudo_commands(self):
        """Test manipulating a x2many field using Commands with `sudo` or with another user (`with_user`)
        is not allowed when the destination model is flagged `_allow_sudo_commands = False` and the transaction user
        does not have the required access rights.

        This test asserts an AccessError is raised
        when a user attempts to pass Commands to a One2many and Many2many field
        targeting a model flagged with `_allow_sudo_commands = False`
        while using an environment with `sudo()` or `with_user(admin_user)`.

        The `with_user` are edge cases in some business codes, where a more-priviledged user is used temporary
        to perform an action, such as:
        - `Documents.with_user(share.create_uid)`
        - `request.env['sign.request'].with_user(contract.hr_responsible_id).sudo()`
        """

        admin_user = self.env.ref('base.user_admin')
        my_user = self.env.user.sudo(False)

        # 1. one2many field `res.partner.user_ids`
        # Sanity checks
        # `res.partner` must be flagged as `_allow_sudo_commands = False` otherwise the test is pointless
        self.assertEqual(self.env['res.users']._allow_sudo_commands, False)
        # in case the type of `res.partner.user_ids` changes in a future release.
        # if `res.partner.user_ids` is no longer a one2many, this test must be adapted.
        self.assertEqual(self.env['res.partner']._fields['user_ids'].type, 'one2many')
        p = my_user.partner_id

        for Partner, my_partner in [
            (self.env['res.partner'].with_user(admin_user), p.with_user(admin_user)),
            (self.env['res.partner'].sudo(), p.sudo()),
        ]:
            # 1.0 Command.CREATE
            # Case: a public/portal user creating a new users with arbitrary values
            with self.assertRaisesRegex(AccessError, "not allowed to create 'User'"):
                Partner.create({
                    'name': 'foo',
                    'user_ids': [Command.create({
                        'login': 'foo',
                        'password': 'foo',
                    })],
                })
            # 1.1 Command.UPDATE
            # Case: a public/portal updating his user to add himself a group
            with self.assertRaisesRegex(AccessError, "do not have enough rights to access the field"):
                my_partner.write({
                    'user_ids': [Command.update(my_partner.user_ids[0].id, {
                        'group_ids': [self.env.ref('base.group_system').id],
                    })],
                })
            # 1.2 Command.DELETE
            # Case: a public user deleting the public user to mess with the database
            with self.assertRaisesRegex(AccessError, "not allowed to delete 'User'"):
                my_partner.write({
                    'user_ids': [Command.delete(my_partner.user_ids[0].id)],
                })
            # 1.3 Command.UNLINK
            # Case: a public user unlinking the public partner and the public user to mess with the database
            with self.assertRaisesRegex(AccessError, "do not have enough rights to access the field"):
                my_partner.write({
                    'user_ids': [Command.unlink(my_partner.user_ids[0].id)],
                })
            # 1.4 Command.LINK
            # Case: a normal user changing the `partner_id` of an admin,
            # to change the email address of the user and ask for a reset password.
            # We get a read error since Command.link need to read the corecord first, see One2many.write_real
            with self.assertRaisesRegex(AccessError, "doesn't have 'write' access to"):
                my_partner.write({
                    'user_ids': [Command.link(admin_user.id)],
                })
            # 1.5 Command.CLEAR
            # Case: a public user unlinking the public partner and the public user just to mess with the database
            with self.assertRaisesRegex(AccessError, "do not have enough rights to access the field"):
                my_partner.write({
                    'user_ids': [Command.clear()],
                })
            # 1.6 Command.SET
            # Case: a normal user changing the `partner_id` of an admin,
            # to change the email address of the user and ask for a reset password.
            with self.assertRaisesRegex(AccessError, "do not have enough rights to access the field"):
                my_partner.write({
                    'user_ids': [Command.set([admin_user.id])],
                })

        # 2. many2many field `test_orm.discussion.participants`
        # Sanity checks
        # `test_orm.user` must be flagged as `_allow_sudo_commands = False` otherwise the test is pointless
        self.assertEqual(self.env['test_orm.group']._allow_sudo_commands, False)
        # in case the type of `test_orm.discussion.participants` changes in a future release.
        # if `test_orm.discussion.participants` is no longer a many2many, this test must be adapted.
        self.assertEqual(self.env['test_orm.user']._fields['group_ids'].type, 'many2many')
        public_group = self.env['test_orm.group'].with_user(admin_user).create({
            'name': 'public',
        }).with_user(self.env.user)
        with self.assertRaises(AccessError):
            # the default user on the transaction has no access
            self.env['test_orm.user'].with_user(admin_user).create({
                'name': 'foo',
                'group_ids': [public_group.id],
            })
        u = self.env['test_orm.user'].with_user(admin_user).sudo().create({
            'name': 'foo',
            'group_ids': [public_group.id],
        }).with_user(self.env.user)

        for User, my_user in [
            (self.env['test_orm.user'].with_user(admin_user), u.with_user(admin_user)),
            (self.env['test_orm.user'].sudo(), u.sudo()),
        ]:
            # 2.0 Command.CREATE
            # Case: a normal user creating a new users with arbitrary values
            with self.assertRaisesRegex(AccessError, "not allowed to create 'test_orm.group'"):
                User.create({
                    'name': 'foo',
                    'group_ids': [Command.create({})],
                })
            # 2.1 Command.UPDATE
            # Case: a normal updating his user to add himself a group
            with self.assertRaisesRegex(AccessError, "not allowed to modify 'test_orm.group'"):
                my_user.write({
                    'group_ids': [Command.update(my_user.group_ids[0].id, {})],
                })
            # 2.2 Command.DELETE
            # Case: a public user deleting the public user to mess with the database
            with self.assertRaisesRegex(AccessError, "not allowed to delete 'test_orm.group'"):
                my_user.write({
                    'group_ids': [Command.delete(my_user.group_ids[0].id)],
                })


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
        self.assertIn(record.id, self.env._field_dirty[reference._fields['res_model']])

        # searching on the one2many should flush the field 'res_model'
        records = record.search([('model_ids.create_date', '!=', False)])
        self.assertIn(record, records)

        # filtered should be aligned
        # TODO right now, need to invalidate because the inverse of
        # many2one_reference is not updated
        record.invalidate_model()
        self._search(record, [('model_ids.create_date', '!=', False)])
