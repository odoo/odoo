from unittest import SkipTest

from odoo import fields
from odoo.tests import BenchmarkCase, benchmark


class BenchmarkInvoice(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        blueprint = cls.env.ref('account.benchmark_invoices', raise_if_not_found=False)
        if not blueprint:
            msg = "Required blueprint account.benchmark_invoices is missing"
            raise SkipTest(msg)

        cls.invoices = blueprint._get_populated('inv_invoices').filtered(
            lambda invoice: invoice.state == 'draft' and invoice.company_id == cls.env.company,
        )
        if not cls.invoices:
            msg = "The account population has no draft invoices in the current company"
            raise SkipTest(msg)

    @benchmark
    def change_date(self):
        invoice_date = fields.Date.add(self.invoices[0].invoice_date, days=1)
        self.invoices.write({'invoice_date': invoice_date})

    @benchmark
    def duplicate(self):
        values = self.invoices.copy_data()
        with self.measure():
            self.env['account.move'].create(values)
