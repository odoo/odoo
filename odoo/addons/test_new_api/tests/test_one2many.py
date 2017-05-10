# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


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

    def test_rpcstyle_single(self):
        """Check lines created with RPC style and added in one step"""
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
        movie_editions = movies_with_edition.mapped('editions')
        one_movie_edition = movie_editions[0]

        res_movies_without_edition = self.Movie.search([('editions', '=', False)])
        self.assertItemsEqual(t(res_movies_without_edition), t(movies_without_edition))

        res_movies_with_edition = self.Movie.search([('editions', '!=', False)])
        self.assertItemsEqual(t(res_movies_with_edition), t(movies_with_edition))

        res_books_with_movie_edition = self.Book.search([('editions', 'in', movie_editions.ids)])
        self.assertFalse(t(res_books_with_movie_edition))

        res_books_without_movie_edition = self.Book.search([('editions', 'not in', movie_editions.ids)])
        self.assertItemsEqual(t(res_books_without_movie_edition), t(books_with_edition))

        res_books_without_one_movie_edition = self.Book.search([('editions', 'not in', movie_editions[:1].ids)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition), t(books_with_edition))

        res_books_with_one_movie_edition_name = self.Book.search([('editions', '=', movie_editions[:1].name)])
        self.assertFalse(t(res_books_with_one_movie_edition_name))

        res_books_without_one_movie_edition_name = self.Book.search([('editions', '!=', movie_editions[:1].name)])
        self.assertItemsEqual(t(res_books_without_one_movie_edition_name), t(books_with_edition))

        res_movies_not_of_edition_name = self.Movie.search([('editions', '!=', one_movie_edition.name)])
        self.assertItemsEqual(t(res_movies_not_of_edition_name), t(movies.filtered(lambda r: one_movie_edition not in r.editions)))
