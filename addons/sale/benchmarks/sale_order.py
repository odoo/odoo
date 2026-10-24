from unittest import SkipTest

from odoo import Command
from odoo.tests import BenchmarkCase, Form, benchmark, new_test_user, users


class BenchmarkSaleOrder(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        blueprint = cls.env.ref('sale.benchmark_invoice_ready_orders', raise_if_not_found=False)
        if not blueprint:
            msg = "Required blueprint sale.benchmark_invoice_ready_orders is missing"
            raise SkipTest(msg)

        cls.orders = blueprint._get_populated('bench_wide_orders').filtered(
            lambda order: (
                order.state in ('draft', 'sent')
                and order.company_id == cls.env.company
                and order.order_line
            )
        )
        partners = blueprint._get_populated('bench_wide_partners')
        if not cls.orders or not partners:
            msg = "The sale population has no eligible quotations or partners"
            raise SkipTest(msg)

        cls.partner = partners[0]
        cls.salesman = new_test_user(
            cls.env, login='benchmark_sale_salesman', groups='sales_team.group_sale_salesman_all_leads',
            company_id=cls.env.company.id, company_ids=[Command.set(cls.env.company.ids)],
        )
        cls.orders.write({'user_id': cls.salesman.id})

    @benchmark
    def confirm(self):
        self.orders.action_confirm()

    @users('admin', 'benchmark_sale_salesman')
    @benchmark
    def confirm_as_user(self):
        self.orders.with_env(self.env).action_confirm()

    @benchmark
    def create_from_form(self):
        form = Form(self.env['sale.order'])
        form.partner_id = self.partner
        with self.measure():
            form.save()

    @benchmark
    def confirm_then_invoice(self):
        with self.measure('confirm'):
            self.orders.action_confirm()
        with self.measure('invoice'):
            self.orders._create_invoices()
