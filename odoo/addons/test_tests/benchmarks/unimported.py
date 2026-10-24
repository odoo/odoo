"""Unimported scenario: discovery must follow the package's explicit imports."""

from odoo.tests import BenchmarkCase, benchmark


class Unimported(BenchmarkCase):
    @benchmark
    def ping(self):
        self.cr.execute('SELECT 1')
