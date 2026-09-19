import odoo
from odoo import Command

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestPoSWithFiscalPosition(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.config = cls.basic_config
        cls.company.account_config_id.tax_calculation_rounding_method = "round_per_line"

        cls.new_tax_17 = cls.env["account.tax"].create(
            {"name": "New Tax 17%", "amount": 17}
        )
        cls.new_tax_17.invoice_repartition_line_ids.write(
            {"account_id": cls.tax_received_account.id}
        )

        cls.fpos = cls._create_fiscal_position()
        cls.fpos_no_tax_dest = cls._create_fiscal_position_no_tax_dest()

        cls.product1 = cls.create_product(
            "Product 1",
            cls.categ_basic,
            lst_price=10.99,
            standard_price=5.0,
            tax_ids=cls.taxes["tax7"].ids,
        )
        cls.product2 = cls.create_product(
            "Product 2",
            cls.categ_basic,
            lst_price=19.99,
            standard_price=10.0,
            tax_ids=cls.taxes["tax10"].ids,
        )
        cls.product3 = cls.create_product(
            "Product 3",
            cls.categ_basic,
            lst_price=30.99,
            standard_price=15.0,
            tax_ids=cls.taxes["tax7"].ids,
        )
        cls.adjust_inventory([cls.product1, cls.product2, cls.product3], [100, 50, 50])

    @classmethod
    def _create_fiscal_position(cls):
        fpos = cls.env["account.fiscal.position"].create(
            {"name": "Test Fiscal Position"}
        )

        account_fpos = cls.env["account.fiscal.position.account"].create(
            {
                "position_id": fpos.id,
                "account_src_id": cls.sale_account.id,
                "account_dest_id": cls.other_sale_account.id,
            }
        )
        fpos.write(
            {
                "account_ids": [(6, 0, account_fpos.ids)],
            }
        )
        cls.new_tax_17.write(
            {
                "fiscal_position_ids": [Command.link(fpos.id)],
                "original_tax_ids": [Command.link(cls.taxes["tax7"].id)],
            }
        )
        return fpos

    @classmethod
    def _create_fiscal_position_no_tax_dest(cls):
        fpos_no_tax_dest = cls.env["account.fiscal.position"].create(
            {"name": "Test Fiscal Position"}
        )
        account_fpos = cls.env["account.fiscal.position.account"].create(
            {
                "position_id": fpos_no_tax_dest.id,
                "account_src_id": cls.sale_account.id,
                "account_dest_id": cls.other_sale_account.id,
            }
        )
        fpos_no_tax_dest.write(
            {
                "account_ids": [(6, 0, account_fpos.ids)],
            }
        )
        cls.env["account.tax"].create(
            {
                "name": "Exempt",
                "amount": 0,
                "fiscal_position_ids": [Command.link(fpos_no_tax_dest.id)],
                "original_tax_ids": [Command.link(cls.taxes["tax7"].id)],
            }
        )
        return fpos_no_tax_dest

    def test_01_no_invoice_fpos(self):

        self.customer.write({"property_account_position_id": self.fpos.id})

        def _before_closing_cb():
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(
                order.amount_total for order in self.pos_session.order_ids
            )
            self.assertAlmostEqual(
                orders_total,
                self.pos_session.total_payments_amount,
                msg="Total order amount should be equal to the total payment amount.",
            )

        self._run_test(
            {
                "payment_methods": self.cash_pm1 | self.bank_pm1,
                "orders": [
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 10),
                            (self.product2, 10),
                            (self.product3, 10),
                        ],
                        "customer": self.customer,
                        "uuid": "00100-010-0001",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 5),
                            (self.product2, 5),
                        ],
                        "customer": self.customer,
                        "uuid": "00100-010-0002",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product2, 5),
                            (self.product3, 5),
                        ],
                        "payments": [(self.bank_pm1, 265.75)],
                        "uuid": "00100-010-0003",
                    },
                ],
                "before_closing_cb": _before_closing_cb,
                "journal_entries_before_closing": {},
                "journal_entries_after_closing": {
                    "session_journal_entry": {
                        "line_ids": [
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 80.70,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 36.35,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 10.85,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 474.75,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 272.59,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.sales_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 90.86,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.sales_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 154.95,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.bank_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 265.75,
                                "credit": 0,
                                "reconciled": True,
                            },
                            {
                                "account_id": self.cash_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 855.30,
                                "credit": 0,
                                "reconciled": True,
                            },
                        ],
                    },
                    "cash_statement": [
                        (
                            (855.30,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.cash_pm1.journal_id.default_account_id.id,
                                        "partner_id": False,
                                        "debit": 855.30,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.cash_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 855.30,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                    "bank_payments": [
                        (
                            (265.75,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.bank_pm1.outstanding_account_id.id,
                                        "partner_id": False,
                                        "debit": 265.75,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.bank_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 265.75,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                },
            }
        )

    def test_02_no_invoice_fpos_no_tax_dest(self):

        self.customer.write({"property_account_position_id": self.fpos_no_tax_dest.id})

        def _before_closing_cb():
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(
                order.amount_total for order in self.pos_session.order_ids
            )
            self.assertAlmostEqual(
                orders_total,
                self.pos_session.total_payments_amount,
                msg="Total order amount should be equal to the total payment amount.",
            )

        self._run_test(
            {
                "payment_methods": self.cash_pm1 | self.bank_pm1,
                "orders": [
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 10),
                            (self.product2, 10),
                            (self.product3, 10),
                        ],
                        "payments": [(self.bank_pm1, 619.7)],
                        "customer": self.customer,
                        "uuid": "00100-010-0001",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 5),
                            (self.product2, 5),
                        ],
                        "customer": self.customer,
                        "uuid": "00100-010-0002",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product2, 5),
                            (self.product3, 5),
                        ],
                        "payments": [(self.bank_pm1, 265.75)],
                        "uuid": "00100-010-0003",
                    },
                ],
                "before_closing_cb": _before_closing_cb,
                "journal_entries_before_closing": {},
                "journal_entries_after_closing": {
                    "session_journal_entry": {
                        "line_ids": [
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 36.35,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 10.85,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 474.75,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 272.59,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.sales_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 90.86,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.sales_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 154.95,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.bank_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 885.45,
                                "credit": 0,
                                "reconciled": True,
                            },
                            {
                                "account_id": self.cash_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 154.9,
                                "credit": 0,
                                "reconciled": True,
                            },
                        ],
                    },
                    "cash_statement": [
                        (
                            (154.9,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.cash_pm1.journal_id.default_account_id.id,
                                        "partner_id": False,
                                        "debit": 154.9,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.cash_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 154.9,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                    "bank_payments": [
                        (
                            (885.45,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.bank_pm1.outstanding_account_id.id,
                                        "partner_id": False,
                                        "debit": 885.45,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.bank_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 885.45,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                },
            }
        )

    def test_03_invoiced_fpos(self):

        self.customer.write({"property_account_position_id": self.fpos.id})

        def _before_closing_cb():
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(
                order.amount_total for order in self.pos_session.order_ids
            )
            self.assertAlmostEqual(
                orders_total,
                self.pos_session.total_payments_amount,
                msg="Total order amount should be equal to the total payment amount.",
            )

            invoiced_order_1 = self.pos_session.order_ids.filtered(
                lambda order: "00100-010-0001" in order.uuid
            )
            invoiced_order_2 = self.pos_session.order_ids.filtered(
                lambda order: "00100-010-0003" in order.uuid
            )

            self.assertTrue(invoiced_order_1, msg="Invoiced order 1 should exist.")
            self.assertTrue(invoiced_order_2, msg="Invoiced order 2 should exist.")
            self.assertTrue(
                invoiced_order_1.account_move,
                msg="Invoiced order 1 should have invoice (account_move).",
            )
            self.assertTrue(
                invoiced_order_2.account_move,
                msg="Invoiced order 2 should have invoice (account_move).",
            )

        self._run_test(
            {
                "payment_methods": self.cash_pm1 | self.bank_pm1,
                "orders": [
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 10),
                            (self.product2, 10),
                            (self.product3, 10),
                        ],
                        "payments": [(self.bank_pm1, 691.06)],
                        "customer": self.customer,
                        "is_invoiced": True,
                        "uuid": "00100-010-0001",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product1, 5),
                            (self.product2, 5),
                        ],
                        "customer": self.customer,
                        "uuid": "00100-010-0002",
                    },
                    {
                        "pos_order_lines_ui_args": [
                            (self.product2, 5),
                            (self.product3, 5),
                        ],
                        "customer": self.other_customer,
                        "is_invoiced": True,
                        "uuid": "00100-010-0003",
                    },
                ],
                "before_closing_cb": _before_closing_cb,
                "journal_entries_before_closing": {
                    "00100-010-0001": {
                        "payments": [
                            (
                                (self.bank_pm1, 691.06),
                                {
                                    "line_ids": [
                                        {
                                            "account_id": self.c1_receivable.id,
                                            "partner_id": self.customer.id,
                                            "debit": 0,
                                            "credit": 691.06,
                                            "reconciled": True,
                                        },
                                        {
                                            "account_id": self.pos_receivable_account.id,
                                            "partner_id": False,
                                            "debit": 691.06,
                                            "credit": 0,
                                            "reconciled": False,
                                        },
                                    ]
                                },
                            ),
                        ],
                    },
                    "00100-010-0003": {
                        "payments": [
                            (
                                (self.cash_pm1, 265.75),
                                {
                                    "line_ids": [
                                        {
                                            "account_id": self.other_receivable_account.id,
                                            "partner_id": self.other_customer.id,
                                            "debit": 0,
                                            "credit": 265.75,
                                            "reconciled": True,
                                        },
                                        {
                                            "account_id": self.pos_receivable_account.id,
                                            "partner_id": False,
                                            "debit": 265.75,
                                            "credit": 0,
                                            "reconciled": False,
                                        },
                                    ]
                                },
                            ),
                        ],
                    },
                },
                "journal_entries_after_closing": {
                    "session_journal_entry": {
                        "line_ids": [
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 9.34,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.tax_received_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 9.09,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 54.95,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.other_sale_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 90.86,
                                "reconciled": False,
                            },
                            {
                                "account_id": self.bank_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 691.06,
                                "credit": 0,
                                "reconciled": True,
                            },
                            {
                                "account_id": self.cash_pm1.receivable_account_id.id,
                                "partner_id": False,
                                "debit": 429.99,
                                "credit": 0,
                                "reconciled": True,
                            },
                            {
                                "account_id": self.pos_receivable_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 691.06,
                                "reconciled": True,
                            },
                            {
                                "account_id": self.pos_receivable_account.id,
                                "partner_id": False,
                                "debit": 0,
                                "credit": 265.75,
                                "reconciled": True,
                            },
                        ],
                    },
                    "cash_statement": [
                        (
                            (429.99,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.cash_pm1.journal_id.default_account_id.id,
                                        "partner_id": False,
                                        "debit": 429.99,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.cash_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 429.99,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                    "bank_payments": [
                        (
                            (691.06,),
                            {
                                "line_ids": [
                                    {
                                        "account_id": self.bank_pm1.outstanding_account_id.id,
                                        "partner_id": False,
                                        "debit": 691.06,
                                        "credit": 0,
                                        "reconciled": False,
                                    },
                                    {
                                        "account_id": self.bank_pm1.receivable_account_id.id,
                                        "partner_id": False,
                                        "debit": 0,
                                        "credit": 691.06,
                                        "reconciled": True,
                                    },
                                ]
                            },
                        ),
                    ],
                },
            }
        )
