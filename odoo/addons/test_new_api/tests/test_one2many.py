# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import MissingError


class One2manyCase(TransactionCase):
    def setUp(self):
        super(One2manyCase, self).setUp()
        self.Line = self.env["test_new_api.multi.line"]
        self.multi = self.env["test_new_api.multi"].create({
            "name": "What is up?"
        })

        # data for One2many with inverse field Integer
        self.Edition = self.env["test_new_api.creativework.edition"]
        self.Book = self.env["test_new_api.creativework.book"]
        self.Movie = self.env["test_new_api.creativework.movie"]

        book_model_id = self.env['ir.model'].search([('model', '=', self.Book._name)]).id
        movie_model_id = self.env['ir.model'].search([('model', '=', self.Movie._name)]).id

        books_data = (
            ('Imaginary book', ()),
            ('Another imaginary book', ()),
            ('Nineteen Eighty Four', ('First edition', 'Fourth Edition'))
        )

        movies_data = (
            ('The Gold Rush', ('1925 (silent)', '1942')),
            ('Imaginary movie', ()),
            ('Another imaginary movie', ())
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
        self.multi.invalidate_cache()
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
            [self.Line.new({"name": str(name)}).id for name in range(10)]
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
            [self.Line.create({"name": str(name)}).id for name in range(10)]
        )
        self.operations()

    def test_rpcstyle_one_by_one(self):
        """Check lines created with RPC style and appended one by one."""
        for name in range(10):
            self.multi.lines = [(0, 0, {"name": str(name)})]
        self.operations()

    def test_rpcstyle_one_by_one_on_new(self):
        self.multi = self.env["test_new_api.multi"].new({
            "name": "What is up?"
        })
        for name in range(10):
            self.multi.lines = [(0, 0, {"name": str(name)})]
        self.operations()

    def test_rpcstyle_single(self):
        """Check lines created with RPC style and added in one step"""
        self.multi.lines = [(0, 0, {'name': str(name)}) for name in range(10)]
        self.operations()

    def test_rpcstyle_single_on_new(self):
        self.multi = self.env["test_new_api.multi"].new({
            "name": "What is up?"
        })
        self.multi.lines = [(0, 0, {'name': str(name)}) for name in range(10)]
        self.operations()

    def test_many2one_integer(self):
        """Test several models one2many with same inverse Integer field"""
        # utility function to convert records to tuples with id,name
        t = lambda records: records.mapped(lambda r: (r.id, r.name))

        books = self.Book.search([])
        books_with_edition = books.filtered(lambda r: r.editions)
        movies = self.Movie.search([])
        movies_without_edition = movies.filtered(lambda r: not r.editions)
        movies_with_edition = movies.filtered(lambda r: r.editions)
        movie_editions = movies_with_edition.editions
        one_movie_edition = movie_editions[0]

        res_movies_without_edition = self.Movie.search([('editions', '=', False)])
        self.assertItemsEqual(t(res_movies_without_edition), t(movies_without_edition))

        res_movies_with_edition = self.Movie.search([('editions', '!=', False)])
        self.assertItemsEqual(t(res_movies_with_edition), t(movies_with_edition))

        res_books_with_movie_edition = self.Book.search([('editions', 'in', movie_editions.ids)])
        self.assertFalse(t(res_books_with_movie_edition))

        res_books_without_movie_edition = self.Book.search([('editions', 'not in', movie_editions.ids)])
        self.assertItemsEqual(t(res_books_without_movie_edition), t(books))

        res_books_without_one_movie_edition = self.Book.search([('editions', 'not in', movie_editions[:1].ids)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition), t(books))

        res_books_with_one_movie_edition_name = self.Book.search([('editions', '=', movie_editions[:1].name)])
        self.assertFalse(t(res_books_with_one_movie_edition_name))

        res_books_without_one_movie_edition_name = self.Book.search([('editions', '!=', movie_editions[:1].name)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition_name), t(books))

        res_movies_not_of_edition_name = self.Movie.search([('editions', '!=', one_movie_edition.name)])
        self.assertItemsEqual(t(res_movies_not_of_edition_name), t(movies.filtered(lambda r: one_movie_edition not in r.editions)))

    def test_merge_partner(self):
        model = self.env['test_new_api.field_with_caps']
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

    def test_cache_invalidation(self):
        """ Cache invalidation for one2many with integer inverse. """
        record0 = self.env['test_new_api.attachment.host'].create({})
        with self.assertQueryCount(0):
            self.assertFalse(record0.attachment_ids, "inconsistent cache")

        # creating attachment must compute name and invalidate attachment_ids
        attachment = self.env['test_new_api.attachment'].create({
            'res_model': record0._name,
            'res_id': record0.id,
        })
        attachment.flush()
        with self.assertQueryCount(0):
            self.assertEqual(attachment.name, record0.display_name,
                             "field should be computed")
        with self.assertQueryCount(1):
            self.assertEqual(record0.attachment_ids, attachment, "inconsistent cache")

        # creating a host should not attempt to recompute attachment.name
        with self.assertQueryCount(1):
            record1 = self.env['test_new_api.attachment.host'].create({})
        with self.assertQueryCount(0):
            # field res_id should not have been invalidated
            attachment.res_id
        with self.assertQueryCount(0):
            self.assertFalse(record1.attachment_ids, "inconsistent cache")

        # writing on res_id must recompute name and invalidate attachment_ids
        attachment.res_id = record1.id
        attachment.flush()
        with self.assertQueryCount(0):
            self.assertEqual(attachment.name, record1.display_name,
                             "field should be recomputed")
        with self.assertQueryCount(1):
            self.assertEqual(record1.attachment_ids, attachment, "inconsistent cache")
        with self.assertQueryCount(1):
            self.assertFalse(record0.attachment_ids, "inconsistent cache")

    def test_recompute(self):
        """ test recomputation of fields that indirecly depend on one2many """
        discussion = self.env.ref('test_new_api.discussion_0')
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
        parent = self.env['test_new_api.model_parent_m2o'].create({
            'name': 'parent',
            'child_ids': [(0, 0, {'name': 'A'})],
        })
        a = parent.child_ids[0]
        parent.write({'child_ids': [(4, a.id), (0, 0, {'name': 'B'})]})

    def test_recomputation_ends(self):
        """ Regression test for neverending recomputation. """
        parent = self.env['test_new_api.model_parent_m2o'].create({'name': 'parent'})
        child = self.env['test_new_api.model_child_m2o'].create({'name': 'A', 'parent_id': parent.id})
        self.assertEqual(child.size1, 6)

        # delete parent, and check that recomputation ends
        parent.unlink()
        parent.flush()

    def test_compute_stored_many2one_one2many(self):
        container = self.env['test_new_api.compute.container'].create({'name': 'Foo'})
        self.assertFalse(container.member_ids)
        member = self.env['test_new_api.compute.member'].create({'name': 'Foo'})
        # at this point, member.container_id must be computed for member to
        # appear in container.member_ids
        self.assertEqual(container.member_ids, member)

    def test_reward_line_delete(self):
        order = self.env['test_new_api.order'].create({
            'line_ids': [
                (0, 0, {'product': 'a'}),
                (0, 0, {'product': 'b'}),
                (0, 0, {'product': 'b', 'reward': True}),
            ],
        })
        line0, line1, line2 = order.line_ids

        # this is what the client sends to delete the 2nd line; it should not
        # crash when deleting the 2nd line automatically deletes the 3rd line
        order.write({
            'line_ids': [(4, line0.id), (2, line1.id), (4, line2.id)],
        })
        self.assertEqual(order.line_ids, line0)

        # but linking a missing line on purpose is an error
        with self.assertRaises(MissingError):
            order.write({
                'line_ids': [(4, line0.id), (4, line1.id)],
            })
