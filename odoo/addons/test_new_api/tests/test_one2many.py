# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


class One2manyCase(TransactionCase):
    def setUp(self):
        super(One2manyCase, self).setUp()
        self.Line = self.env["test_new_api.multi.line"]
        self.multi = self.env["test_new_api.multi"].create({
            "name": "What is up?"
        })

    def operations(self):
        """Run operations on o2m fields to check all works fine."""
        # Check the lines first
        self.assertItemsEqual(
            self.multi.lines.mapped('name'),
            map(str, range(10)))
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
