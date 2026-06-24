# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command, fields


@tagged('post_install', '-at_install')
class TestAccountInvoiceReport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.company_data_2 = cls.setup_other_company()
        pack_of_six = cls.env['uom.uom'].search([('name', '=', 'Pack of 6')])
        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 3,
                        'price_unit': 4500,
                        'product_uom_id': pack_of_six.id,
                    }),
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 3000,
                    }),
                ]
            },
            {
                'move_type': 'out_receipt',
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 6000,
                    }),
                ]
            },
            {
                'move_type': 'out_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 1200,
                    }),
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 3,
                        'price_unit': 4500,
                        'product_uom_id': pack_of_six.id,
                    }),
                ]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 60,
                    }),
                ]
            },
            {
                'move_type': 'in_receipt',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 60,
                    }),
                ]
            },
            {
                'move_type': 'in_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 12,
                    }),
                ]
            },
            {
                'move_type': 'out_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.other_currency.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 2400,
                    }),
                ]
            },
        ])

    def assertInvoiceReportValues(self, expected_values_list):
        reports = self.env['account.invoice.report'].search([('company_id', '=', self.company_data['company'].id)], order='price_subtotal DESC, quantity ASC')
        expected_values_dict = [{
            'price_average': vals[0],
            'price_subtotal': vals[1],
            'quantity': vals[2],
            'price_margin': vals[3],
            'inventory_value': vals[4],
        } for vals in expected_values_list]

        self.assertRecordValues(reports, expected_values_dict)

    def test_invoice_report_multiple_types(self):
        """
        Each line represent an invoice line
        First and last lines use Packagings. Quantity and price from the invoice are adapted
        to the standard UoM of the product.

        quantity is quantity in product_uom
        price_subtotal = Price_unit * Number_of_packages / currency_rate
        price_average = price_subtotal / quantity
        inventory_value = quantity * standard_price * (-1 OR 1 depending of move_type)
        price_margin = (price_average - standard_price) * quantity

        E.g. first line:
        quantity : 6 * 3 = 18
        price_subtotal = 4500 * 3 / 3 = 4500
        price_average = 4500 / 18 = 250
        inventory_value = 800*18*-1 = -14400
        price_margin = (250 - 800) * 18 = -9900
        """
        self.assertInvoiceReportValues([
            # pylint: disable=bad-whitespace
            # price_average, price_subtotal, quantity, price_margin, inventory_value
            [           250,           4500,       18,        -9900,          -14400],  # price_unit = 4500,  currency.rate = 3.0
            [          2000,           2000,        1,         1200,            -800], # price_unit = 6000, currency.rate = 3.0
            [          1000,           1000,        1,          200,            -800], # price_unit = 3000, currency.rate = 3.0
            [             6,              6,        1,            0,            -800], # price_unit = 12,   currency.rate = 2.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [           600,           -600,       -1,          200,             800],  # price_unit = 1200, currency.rate = 2.0
            [          1200,          -1200,       -1,         -400,             800],  # price_unit = 2400, currency.rate = 2.0
            [           375,          -6750,      -18,         7650,           14400],  # price_unit = 4500, currency.rate = 2.0
        ])

    def test_invoice_report_multicompany_product_cost(self):
        """
        In a multicompany environment, if you define one product with different standard price per company
        the invoice analysis report should only display the product from the company
        Standard Price in Company A: 800 (default setup)
        Standard Price in Company B: 700
        -> invoice report for Company A should remain the same
        """
        self.product_a.with_company(self.company_data_2.get('company')).write({'standard_price': 700.0})
        self.assertInvoiceReportValues([
            # pylint: disable=bad-whitespace
            # price_average, price_subtotal, quantity, price_margin, inventory_value
            [           250,           4500,       18,        -9900,          -14400],  # price_unit = 4500,  currency.rate = 3.0
            [          2000,           2000,        1,         1200,            -800], # price_unit = 6000, currency.rate = 3.0
            [          1000,           1000,        1,          200,            -800], # price_unit = 3000, currency.rate = 3.0
            [             6,              6,        1,            0,            -800], # price_unit = 12,   currency.rate = 2.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [           600,           -600,       -1,          200,             800],  # price_unit = 1200, currency.rate = 2.0
            [          1200,          -1200,       -1,         -400,             800],  # price_unit = 2400, currency.rate = 2.0
            [           375,          -6750,      -18,         7650,           14400],  # price_unit = 4500, currency.rate = 2.0
        ])

    def test_avg_price_calculation(self):
        """
        Check that the average is correctly calculated based on the total price and quantity:
            3 lines:
                - 10 units * 10$
                -  5 units *  5$
                - 20 units *  2$
            Total quantity: 35
            Total price: 165$
            Average: 165 / 35 = 4.71
        """
        product = self.product_a.copy()
        invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': self.env.company.currency_id.id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 10,
                        'price_unit': 10,
                    }),
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 5,
                        'price_unit': 5,
                    }),
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 20,
                        'price_unit': 2,
                    }),
                ]
        })
        invoice.action_post()

        report = self.env['account.invoice.report'].formatted_read_group(
            [('product_id', '=', product.id)],
            [],
            ['price_subtotal:sum', 'quantity:sum', 'price_average:avg'],
        )
        self.assertEqual(report[0]['quantity:sum'], 35)
        self.assertEqual(report[0]['price_subtotal:sum'], 165)
        self.assertEqual(round(report[0]['price_average:avg'], 2), 4.71)

        # ensure that it works with only 'price_average:avg' in aggregates
        report = self.env['account.invoice.report'].formatted_read_group(
            [('product_id', '=', product.id)],
            [],
            ['price_average:avg'],
        )
        self.assertEqual(round(report[0]['price_average:avg'], 2), 4.71)

    def test_avg_price_group_by_month(self):
        """
        Check that the average is correctly calculated based on the total price and quantity
        with multiple invoices and group by month:
            Invoice 1:
                2 lines:
                    - 10 units * 10$
                    -  5 units *  5$
                Total quantity: 15
                Total price: 125$
                Average: 125 / 15 = 8.33
            Invoice 2:
                1 line:
                    - 0 units * 5$
                Total quantity: 0
                Total price: 0$
                Average: 0.00
        """
        self.env['account.move'].search([]).unlink()
        invoices = self.env["account.move"].create([
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2025-01-01'),
                'currency_id': self.env.company.currency_id.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 10,
                        'price_unit': 10,
                    }),
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 5,
                        'price_unit': 5,
                    }),
                ]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2025-02-01'),
                'currency_id': self.env.company.currency_id.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 0,
                        'price_unit': 5,
                    }),
                ]
            },
        ])
        invoices.action_post()

        report = self.env['account.invoice.report'].formatted_read_group(
            [('product_id', '=', self.product_a.id)],
            ['invoice_date:month'],
            ['__count', 'price_subtotal:sum', 'quantity:sum', 'price_average:avg'],
        )

        self.assertEqual(report[0]['__count'], 2)
        self.assertEqual(report[0]['quantity:sum'], 15.0)
        self.assertEqual(report[0]['price_subtotal:sum'], 125.0)
        self.assertEqual(round(report[0]['price_average:avg'], 2), 8.33)

        self.assertEqual(report[1]['__count'], 1)
        self.assertEqual(report[1]['quantity:sum'], 0.0)
        self.assertEqual(report[1]['price_subtotal:sum'], 0.0)
        self.assertEqual(report[1]['price_average:avg'], 0.00)

    def test_inventory_margin_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 750,
                }),
            ],
        })
        egy_company = self.env['res.company'].create({
            'name': 'Egyptian Company',
            'currency_id': self.env.ref('base.EGP').id,
            'user_ids': [Command.set(self.env.user.ids)],
        })
        orig_company = self.env.company
        report = self.env['account.invoice.report'].search(
            [('move_id', '=', invoice.id)],
        )
        self.assertEqual(report.inventory_value, -800)
        self.assertEqual(report.price_margin, -50)
        self.env.user.company_id = egy_company
        self.env['res.currency.rate'].create({
            'name': '2017-11-03',
            'rate': 0.5,
            'currency_id': orig_company.currency_id.id,
        })
        self.env.flush_all()
        self.env['account.invoice.report'].invalidate_model()
        report = self.env['account.invoice.report'].search(
            [('move_id', '=', invoice.id)],
        )
        self.assertEqual(report.inventory_value, -1600)
        self.assertEqual(report.price_margin, -100)

    def test_minimal_queries(self):
        """Check that inner the queries for `account.invoice.report` are minimal.

        Depending on the parameters of the graph/pivot views, we don't need to do some joins.
        For instance, the partner, product or UoM are not always used and would force worse query plans.
        """
        with self.assertQueries([
            """
            SELECT date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date,
                   SUM("account_invoice_report"."price_total"),
                   COUNT(*)
              FROM (
                       SELECT "account_move_line"."id" AS "id",
                              "account_move_line__move_id"."move_type" AS "move_type",
                              "account_move_line__move_id"."state" AS "state",
                              "account_move_line"."company_id" AS "company_id",
                              "account_move_line__move_id"."invoice_date" AS "invoice_date",
                              "account_move_line"."price_subtotal" * CASE WHEN "account_move_line__move_id"."move_type" IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END / "account_move_line__move_id"."invoice_currency_rate" AS "price_total"
                         FROM "account_move_line"
                         JOIN "account_move" AS "account_move_line__move_id"
                           ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")
                        WHERE (
                                  "account_move_line"."account_id" IS NOT NULL
                                  AND "account_move_line"."display_type" IN %s
                                  AND "account_move_line__move_id"."move_type" IN %s
                              )
                   ) AS "account_invoice_report"
             WHERE ("account_invoice_report"."move_type" IN %s AND ("account_invoice_report"."state" IN %s OR "account_invoice_report"."state" IS NULL))
               AND "account_invoice_report"."company_id" IN %s
          GROUP BY date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date
          ORDER BY date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date ASC
            """
        ]):
            # Default graph view
            self.env['account.invoice.report'].formatted_read_group(
                domain=[('state', 'not in', ('draft', 'cancel')), ('move_type', '=', 'out_invoice')],
                groupby=['invoice_date:month'],
                aggregates=['price_total:sum', '__count'],
                order=None,
            )

        with self.assertQueries([
            """
                SELECT GROUPING(
                           "account_invoice_report"."product_categ_id",
                           date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date
                       ),
                       "account_invoice_report"."product_categ_id",
                       date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date,
                       SUM("account_invoice_report"."price_subtotal"),
                       COUNT(*)
                  FROM (
                         SELECT "account_move_line"."id" AS "id",
                                "account_move_line__move_id"."move_type" AS "move_type",
                                "account_move_line__move_id"."state" AS "state",
                                "account_move_line"."company_id" AS "company_id",
                                "account_move_line__product_id__product_tmpl_id"."categ_id" AS "product_categ_id",
                                "account_move_line__move_id"."invoice_date" AS "invoice_date",
                                -(1 * "account_move_line"."balance") AS "price_subtotal"
                           FROM "account_move_line"
                           JOIN "account_move" AS "account_move_line__move_id"
                             ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")
                      LEFT JOIN "product_product" AS "account_move_line__product_id"
                             ON ("account_move_line"."product_id" = "account_move_line__product_id"."id")
                      LEFT JOIN "product_template" AS "account_move_line__product_id__product_tmpl_id"
                             ON ("account_move_line__product_id"."product_tmpl_id" = "account_move_line__product_id__product_tmpl_id"."id")
                          WHERE (
                                    "account_move_line"."account_id" IS NOT NULL
                                    AND "account_move_line"."display_type" IN %s
                                    AND "account_move_line__move_id"."move_type" IN %s
                                )
                       ) AS "account_invoice_report"
             LEFT JOIN "product_category" AS "account_invoice_report__product_categ_id"
                    ON ("account_invoice_report"."product_categ_id" = "account_invoice_report__product_categ_id"."id")
             LEFT JOIN "product_category" AS "account_invoice_report__product_categ_id__parent_id"
                    ON ("account_invoice_report__product_categ_id"."parent_id" = "account_invoice_report__product_categ_id__parent_id"."id")
                 WHERE ("account_invoice_report"."move_type" IN %s AND ("account_invoice_report"."state" IN %s OR "account_invoice_report"."state" IS NULL))
                   AND "account_invoice_report"."company_id" IN %s
              GROUP BY GROUPING SETS (
                           ("account_invoice_report"."product_categ_id", "account_invoice_report__product_categ_id__parent_id"."name"->>%s, "account_invoice_report__product_categ_id"."name"->>%s),
                           (date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date),
                           (date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date, "account_invoice_report"."product_categ_id", "account_invoice_report__product_categ_id__parent_id"."name"->>%s, "account_invoice_report__product_categ_id"."name"->>%s)
                       )
              ORDER BY "account_invoice_report__product_categ_id__parent_id"."name"->>%s DESC,
                       "account_invoice_report__product_categ_id"."name"->>%s ASC ,
                       date_trunc(%s, "account_invoice_report"."invoice_date"::timestamp)::date ASC
            """,
        ]):
            # Default pivot view
            self.env['account.invoice.report'].formatted_read_grouping_sets(
                domain=[('state', 'not in', ('draft', 'cancel')), ('move_type', '=', 'out_invoice')],
                grouping_sets=[['product_categ_id'], ['invoice_date:month'], ['invoice_date:month', 'product_categ_id']],
                aggregates=['price_subtotal:sum', '__count'],
                order=None,
            )
