# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


class CacheCase(object):
    def setUp(self):
        super(CacheCase, self).setUp()
        self.Line = self.env["test_new_api.multi.line"]
        self.multi = self.env["test_new_api.multi"].create({
            "name": "What is up?"
        })

    def test_reassign_recordset(self):
        """Gets updated in cache and after invalidating it."""
        self.multi.lines = self.multi.lines[:-1]
        self.assertEqual(len(self.multi.lines), 9)
        self.multi.invalidate_cache()
        self.assertEqual(len(self.multi.lines), 9)

    def test_names_ok(self):
        """Line names were saved fine."""
        expected = set(map(str, range(10)))
        self.assertEqual(expected, set(self.multi.lines.mapped("name")))

    def test_modify(self):
        """Editing a NewId removes it in cache and after invalidating it."""
        self.multi.lines[-1].name = "hello!"
        self.assertIn("hello!", self.multi.lines.mapped("name"))
        self.multi.invalidate_cache()
        self.assertIn("hello!", self.multi.lines.mapped("name"))


class ORMNewStyleCacheCase(CacheCase, TransactionCase):
    def setUp(self):
        super(ORMNewStyleCacheCase, self).setUp()
        for name in range(10):
            self.multi.lines |= self.Line.new({"name": str(name)})


class ORMCreateStyleCacheCase(CacheCase, TransactionCase):
    def setUp(self):
        super(ORMCreateStyleCacheCase, self).setUp()
        for name in range(10):
            self.multi.lines |= self.Line.create({"name": str(name)})


class RPCStyleCacheCase(CacheCase, TransactionCase):
    def setUp(self):
        super(RPCStyleCacheCase, self).setUp()
        new = [(5, False, False)]
        for name in range(10):
            new += [(0, False, {"name": str(name)})]
        self.multi.lines = new
