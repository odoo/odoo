# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2016-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from odoo.addons.commission.tests.test_commission import TestCommissionBase


@tagged("post_install", "-at_install")
class TestAccountCommission(TestCommissionBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.commission_net_paid.write({"invoice_state": "paid"})
        cls.commission_net_invoice = cls.commission_model.create(
            {
                "name": "10% fixed commission (Net amount) - Invoice Based",
                "fix_qty": 10.0,
                "amount_base_type": "net_amount",
            }
        )
        cls.commission_section_paid.write({"invoice_state": "paid"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product for commissions",
                "list_price": 5,
            }
        )
        cls.default_line_account = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.company.id),
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        cls.agent_biweekly = cls.res_partner_model.create(
            {
                "name": "Test Agent - Bi-weekly",
                "agent": True,
                "settlement": "biweekly",
                "lang": "en_US",
                "commission_id": cls.commission_net_invoice.id,
            }
        )
        cls.income_account = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )

    def _create_invoice(self, agent, commission, date=None, currency=None):
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "agent_ids": [
                            (
                                0,
                                0,
                                {"agent_id": agent.id, "commission_id": commission.id},
                            )
                        ],
                    },
                )
            ],
        }
        if date:
            vals.update({"invoice_date": date, "date": date})
        if currency:
            vals.update({"currency_id": currency.id})
        return self.env["account.move"].create([vals])

    def _settle_agent_invoice(self, agent=None, period=None, date=None):
        vals = self._get_make_settle_vals(agent, period, date)
        vals["settlement_type"] = "sale_invoice"
        wizard = self.make_settle_model.create(vals)
        wizard.action_settle()

    def _process_invoice_and_settle(self, agent, commission, period, order=None):
        if not order:
            invoice = self._create_invoice(agent, commission)
        else:
            invoice = order.invoice_ids
        invoice.invoice_line_ids.agent_ids._compute_amount()
        invoice.action_post()
        self._settle_agent_invoice(agent, period)
        return invoice

    def _check_settlements(self, agent, commission, settlements=None):
        if not settlements:
            settlements = self._create_settlement(agent, commission)
        settlements.make_invoices(self.journal, self.commission_product)
        for settlement in settlements:
            self.assertEqual(settlement.state, "invoiced")
        with self.assertRaises(UserError):
            settlements.action_cancel()
        with self.assertRaises(UserError):
            settlements.unlink()
        return settlements

    def _check_invoice_thru_settle(
        self, agent, commission, period, initial_count, order=None
    ):
        invoice = self._process_invoice_and_settle(agent, commission, period, order)
        settlements = self.settle_model.search([("state", "=", "settled")])
        self.assertEqual(len(settlements), initial_count)
        journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", invoice.company_id.id)],
            limit=1,
        )
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_ids=invoice.id, active_model="account.move")
            .create({"journal_id": journal.id})
        )
        register_payments.action_create_payments()
        self.assertEqual(invoice.partner_agent_ids.ids, agent.ids)
        self.assertEqual(
            self.env["account.move"]
            .search([("partner_agent_ids", "=", agent.name)])
            .ids,
            invoice.ids,
        )
        self.assertIn(invoice.payment_state, ["in_payment", "paid"])
        self._settle_agent_invoice(agent, period)
        settlements = self.settle_model.search([("state", "=", "settled")])
        self.assertTrue(settlements)
        inv_line = invoice.invoice_line_ids[0]
        self.assertTrue(inv_line.any_settled)
        with self.assertRaises(ValidationError):
            inv_line.agent_ids.amount = 5
        return self._check_settlements(agent, commission, settlements)

    def test_commission_gross_amount(self):
        settlements = self._check_settlements(
            self.env.ref("commission.res_partner_pritesh_sale_agent"),
            self.commission_section_paid,
        )
        # Check report print - It shouldn't fail
        self.env["ir.actions.report"]._render_qweb_html(
            self.env.ref("commission.action_report_settlement").id, settlements[0].ids
        )

    def test_account_commission_gross_amount_payment(self):
        self._check_invoice_thru_settle(
            self.env.ref("commission.res_partner_pritesh_sale_agent"),
            self.commission_section_paid,
            1,
            0,
        )

    def test_account_commission_gross_amount_payment_annual(self):
        self._check_invoice_thru_settle(
            self.agent_annual, self.commission_section_paid, 12, 0
        )

    def test_account_commission_gross_amount_payment_semi(self):
        self.product.list_price = 15100  # for testing specific commission section
        self._check_invoice_thru_settle(
            self.agent_semi, self.commission_section_invoice, 6, 1
        )

    def test_account_commission_gross_amount_invoice(self):
        self._process_invoice_and_settle(
            self.agent_quaterly,
            self.env.ref("commission.demo_commission"),
            1,
        )
        settlements = self.settle_model.search([("state", "=", "invoiced")])
        settlements.make_invoices(self.journal, self.commission_product)
        for settlement in settlements:
            self.assertNotEqual(
                len(settlement.invoice_id),
                0,
                "Settlements need to be in Invoiced State.",
            )

    def test_commission_status(self):
        # Make sure user is in English
        self.env.user.lang = "en_US"
        invoice = self._create_invoice(
            self.env.ref("commission.res_partner_pritesh_sale_agent"),
            self.commission_section_invoice,
        )
        self.assertIn("1", invoice.invoice_line_ids[0].commission_status)
        self.assertNotIn("agents", invoice.invoice_line_ids[0].commission_status)
        invoice.mapped("invoice_line_ids.agent_ids").unlink()
        self.assertIn("No", invoice.invoice_line_ids[0].commission_status)
        invoice.invoice_line_ids[0].agent_ids = [
            (
                0,
                0,
                {
                    "agent_id": self.env.ref(
                        "commission.res_partner_pritesh_sale_agent"
                    ).id,
                    "commission_id": self.env.ref("commission.demo_commission").id,
                },
            ),
            (
                0,
                0,
                {
                    "agent_id": self.env.ref(
                        "commission.res_partner_eiffel_sale_agent"
                    ).id,
                    "commission_id": self.env.ref("commission.demo_commission").id,
                },
            ),
        ]
        self.assertIn("2", invoice.invoice_line_ids[0].commission_status)
        self.assertIn("agents", invoice.invoice_line_ids[0].commission_status)
        invoice.action_post()
        # Free
        invoice.invoice_line_ids.commission_free = True
        self.assertIn("free", invoice.invoice_line_ids.commission_status)
        self.assertAlmostEqual(invoice.invoice_line_ids.agent_ids.amount, 0)
        # test show agents buton
        action = invoice.invoice_line_ids.button_edit_agents()
        self.assertEqual(action["res_id"], invoice.invoice_line_ids.id)

    def test_supplier_invoice(self):
        """No agents should be populated on supplier invoices."""
        self.partner.agent_ids = self.agent_semi
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner.id,
                    "ref": "sale_comission_TEST",
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "quantity": 1,
                                "currency_id": self.company.currency_id.id,
                            },
                        )
                    ],
                }
            ]
        )
        self.assertFalse(invoice.invoice_line_ids.agent_ids)

    def test_commission_propagation(self):
        """Test propagation of agents from partner to invoice."""
        self.partner.agent_ids = [(4, self.agent_monthly.id)]
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "quantity": 1,
                                "currency_id": self.company.currency_id.id,
                            },
                        )
                    ],
                }
            ]
        )
        agent = invoice.invoice_line_ids.agent_ids
        self._check_propagation(agent, self.commission_net_invoice, self.agent_monthly)
        # Check agent change
        agent.agent_id = self.agent_quaterly
        self.assertTrue(agent.commission_id, self.commission_section_invoice)
        # Check recomputation
        agent.unlink()
        invoice.recompute_lines_agents()
        agent = invoice.invoice_line_ids.agent_ids
        self._check_propagation(agent, self.commission_net_invoice, self.agent_monthly)

    def test_negative_settlements(self):
        self.product.write({"list_price": 1000})
        agent = self.agent_monthly
        commission = self.commission_net_invoice
        invoice = self._process_invoice_and_settle(agent, commission, 1)
        settlement = self.settle_model.search([("agent_id", "=", agent.id)])
        self.assertEqual(1, len(settlement))
        self.assertEqual(settlement.state, "settled")
        commission_invoice = settlement.make_invoices(
            product=self.commission_product, journal=self.journal
        )
        self.assertEqual(settlement.state, "invoiced")
        self.assertEqual(commission_invoice.move_type, "in_invoice")
        refund = invoice._reverse_moves(
            default_values_list=[{"invoice_date": invoice.invoice_date}],
        )
        self.assertEqual(
            invoice.invoice_line_ids.agent_ids.agent_id,
            refund.invoice_line_ids.agent_ids.agent_id,
        )
        refund.invoice_line_ids.agent_ids._compute_amount()
        refund.action_post()
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search([("agent_id", "=", agent.id)])
        self.assertEqual(2, len(settlements))
        second_settlement = settlements.filtered(lambda r: r.total < 0)
        self.assertEqual(second_settlement.state, "settled")
        # Use invoice wizard for testing also this part
        wizard = self.env["commission.make.invoice"].create(
            {"product_id": self.commission_product.id}
        )
        action = wizard.button_create()
        commission_refund = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(second_settlement.state, "invoiced")
        self.assertEqual(commission_refund.move_type, "in_refund")
        # Undo invoices + make invoice again to get a unified invoice
        commission_invoices = commission_invoice + commission_refund
        commission_invoices.button_cancel()
        self.assertEqual(settlement.state, "except_invoice")
        self.assertEqual(second_settlement.state, "except_invoice")
        commission_invoices.unlink()
        settlements.unlink()
        self._settle_agent_invoice(False, 1)  # agent=False for testing default
        settlement = self.settle_model.search([("agent_id", "=", agent.id)])
        # Check make invoice wizard
        action = settlement.action_invoice()
        self.assertEqual(action["context"]["settlement_ids"], settlement.ids)
        # Use invoice wizard for testing also this part
        wizard = self.env["commission.make.invoice"].create(
            {
                "product_id": self.commission_product.id,
                "journal_id": self.journal.id,
                "settlement_ids": [(4, settlement.id)],
            }
        )
        action = wizard.button_create()
        invoice = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(invoice.move_type, "in_invoice")
        self.assertAlmostEqual(invoice.amount_total, 0)

    def test_negative_settlements_join_invoice(self):
        self.product.write({"list_price": 1000})
        agent = self.agent_monthly
        commission = self.commission_net_invoice
        invoice = self._process_invoice_and_settle(agent, commission, 1)
        settlement = self.settle_model.search([("agent_id", "=", agent.id)])
        self.assertEqual(1, len(settlement))
        self.assertEqual(settlement.state, "settled")
        refund = invoice._reverse_moves(
            default_values_list=[
                {
                    "invoice_date": invoice.invoice_date + relativedelta(months=-1),
                    "date": invoice.date + relativedelta(months=-1),
                }
            ],
        )
        self.assertEqual(
            invoice.invoice_line_ids.agent_ids.agent_id,
            refund.invoice_line_ids.agent_ids.agent_id,
        )
        refund.action_post()
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search([("agent_id", "=", agent.id)])
        self.assertEqual(2, len(settlements))
        second_settlement = settlements.filtered(lambda r: r.total < 0)
        self.assertEqual(second_settlement.state, "settled")
        # Use invoice wizard for testing also this part
        wizard = self.env["commission.make.invoice"].create(
            {"product_id": self.commission_product.id, "grouped": True}
        )
        action = wizard.button_create()
        commission_invoice = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(1, len(commission_invoice))
        self.assertEqual(commission_invoice.move_type, "in_invoice")
        self.assertAlmostEqual(commission_invoice.amount_total, 0, places=2)

    def _create_multi_settlements(self):
        agent = self.agent_monthly
        commission = self.commission_section_invoice
        today = fields.Date.today()
        last_month = today + relativedelta(months=-1)
        invoice_1 = self._create_invoice(agent, commission, today)
        invoice_1.action_post()
        invoice_2 = self._create_invoice(agent, commission, last_month)
        invoice_2.action_post()
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
                ("state", "=", "settled"),
            ]
        )
        self.assertEqual(2, len(settlements))
        return settlements

    def test_commission_single_invoice(self):
        settlements = self._create_multi_settlements()
        settlements.make_invoices(self.journal, self.commission_product, grouped=True)
        invoices = settlements.mapped("invoice_id")
        self.assertEqual(1, len(invoices))

    def test_commission_multiple_invoice(self):
        settlements = self._create_multi_settlements()
        settlements.make_invoices(self.journal, self.commission_product)
        invoices = settlements.mapped("invoice_id")
        self.assertEqual(2, len(invoices))

    def test_biweekly(self):
        agent = self.agent_biweekly
        commission = self.commission_net_invoice
        invoice = self._create_invoice(agent, commission)
        invoice.invoice_date = "2022-01-01"
        invoice.date = "2022-01-01"
        invoice.action_post()
        invoice2 = self._create_invoice(agent, commission, date="2022-01-16")
        invoice2.invoice_date = "2022-01-16"
        invoice2.date = "2022-01-16"
        invoice2.action_post()
        invoice3 = self._create_invoice(agent, commission, date="2022-01-31")
        invoice3.invoice_date = "2022-01-31"
        invoice3.date = "2022-01-31"
        invoice3.action_post()
        self._settle_agent_invoice(agent=self.agent_biweekly, date="2022-02-01")
        settlements = self.settle_model.search(
            [("agent_id", "=", self.agent_biweekly.id)]
        )
        self.assertEqual(len(settlements), 2)

    def test_account_commission_single_settlement_ids(self):
        settlement = self._check_invoice_thru_settle(
            self.env.ref("commission.res_partner_pritesh_sale_agent"),
            self.commission_section_paid,
            1,
            0,
        )
        invoice_id = settlement.invoice_id
        self.assertEqual(1, invoice_id.settlement_count)

    def test_account_commission_multiple_settlement_ids(self):
        settlements = self._create_multi_settlements()
        settlements.make_invoices(self.journal, self.commission_product, grouped=True)
        invoices = settlements.mapped("invoice_id")
        self.assertEqual(2, invoices.settlement_count)

    def test_unlink_settlement_invoice(self):
        settlements = self._create_multi_settlements()
        invoices = settlements.make_invoices(self.journal, self.commission_product)
        self.assertTrue(
            all(state == "invoiced" for state in settlements.mapped("state"))
        )
        invoices.unlink()
        self.assertTrue(
            all(state == "settled" for state in settlements.mapped("state"))
        )

    def test_multi_currency(self):
        commission = self.commission_net_invoice
        agent = self.agent_monthly
        today = fields.Date.today()
        last_month = today + relativedelta(months=-1)

        # creating invoices with different currencies, same date
        invoice = self._create_invoice(agent, commission, today, currency=None)
        invoice.action_post()
        invoice1 = self._create_invoice(agent, commission, today, self.foreign_currency)
        invoice1.action_post()

        # check settlement creation
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
                ("state", "=", "settled"),
            ]
        )
        self.assertEqual(2, len(settlements))
        self.assertEqual(2, len(settlements.mapped("currency_id")))

        # creating some additional invoices
        invoice2 = self._create_invoice(agent, commission, today, self.foreign_currency)
        invoice2.action_post()
        invoice3 = self._create_invoice(
            agent, commission, last_month, self.foreign_currency
        )
        invoice3.action_post()
        invoice4 = self._create_invoice(
            agent, commission, last_month, self.foreign_currency
        )
        invoice4.action_post()

        # check settlement creation
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
                ("state", "=", "settled"),
            ]
        )
        self.assertEqual(3, len(settlements))

        # check commission invoices
        settlements.make_invoices(self.journal, self.commission_product)
        invoices = settlements.mapped("invoice_id")
        self.assertEqual(3, len(invoices))

        # check settlement creation after a commission invoicing process
        # (previous settlements were already invoiced)
        invoice5 = self._create_invoice(agent, commission, today)
        invoice5.action_post()
        invoice6 = self._create_invoice(agent, commission, today, self.foreign_currency)
        invoice6.action_post()
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
                ("state", "=", "settled"),
            ]
        )
        self.assertEqual(2, len(settlements))

    def test_invoice_partial_refund(self):
        commission = self.commission_net_paid
        agent = self.agent_monthly
        today = fields.Date.today()
        # Create an invoice
        invoice = self._create_invoice(agent, commission, today, currency=None)
        invoice.action_post()
        # Register payment for invoice
        payment_journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", invoice.company_id.id)],
            limit=1,
        )
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_ids=invoice.id, active_model="account.move")
            .create({"journal_id": payment_journal.id})
        )
        register_payments.action_create_payments()
        # Make a parcial refund for the invoice
        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.id)
            .create(
                {
                    "reason": "no reason",
                    "refund_method": "refund",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        refund_form = Form(
            self.env["account.move"].browse(move_reversal.reverse_moves()["res_id"])
        )
        with refund_form.invoice_line_ids.edit(0) as line:
            line.price_unit -= 2
        refund = refund_form.save()
        refund.action_post()
        # Register payment for the refund
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_ids=refund.id, active_model="account.move")
            .create({"journal_id": payment_journal.id})
        )
        register_payments.action_create_payments()
        # check settlement creation. The commission must be (5 - 3) * 0.2 = 0.4
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search([("agent_id", "=", agent.id)])
        self.assertEqual(2, len(settlements.line_ids))
        self.assertEqual(0.4, sum(settlements.mapped("total")))

    def test_invoice_full_refund(self):
        commission = self.commission_net_paid
        agent = self.agent_monthly
        today = fields.Date.today()
        # Create an invoice and refund it
        invoice = self._create_invoice(agent, commission, today, currency=None)
        invoice.action_post()
        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.id)
            .create(
                {
                    "reason": "no reason",
                    "refund_method": "cancel",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        move_reversal.reverse_moves()
        # check settlement creation. The commission must be: (5 - 5) * 0.2 = 0
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
            ]
        )
        self.assertEqual(2, len(settlements.line_ids))
        self.assertEqual(0, sum(settlements.mapped("total")))

    def test_invoice_modify_refund(self):
        commission = self.commission_net_paid
        agent = self.agent_monthly
        today = fields.Date.today()
        # Create an invoice
        invoice = self._create_invoice(agent, commission, today, currency=None)
        invoice.action_post()
        # Create a full refund and a new invoice
        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.id)
            .create(
                {
                    "reason": "no reason",
                    "refund_method": "modify",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        invoice2_form = Form(
            self.env["account.move"].browse(move_reversal.reverse_moves()["res_id"])
        )
        with invoice2_form.invoice_line_ids.edit(0) as line:
            line.price_unit -= 2
        invoice2 = invoice2_form.save()
        invoice2.action_post()
        # Register payment for the new invoice
        payment_journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", invoice.company_id.id)],
            limit=1,
        )
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_ids=invoice2.id, active_model="account.move")
            .create({"journal_id": payment_journal.id})
        )
        register_payments.action_create_payments()

        # check settlement creation. The commission must be (5 - 5 + 3) * 0.2 = 0.6
        self._settle_agent_invoice(agent, 1)
        settlements = self.settle_model.search(
            [
                ("agent_id", "=", agent.id),
            ]
        )
        self.assertEqual(3, len(settlements.line_ids))
        self.assertAlmostEqual(0.6, sum(settlements.mapped("total")), 2)

    def _register_payment(self, invoice):
        payment_journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_ids=invoice.id, active_model="account.move")
            .create({"journal_id": payment_journal.id})
        )
        register_payments.action_create_payments()

    def test_invoice_pending_settlement(self):
        """Make in one settlement all pending invoices to wizard date"""
        fields.Date.today()
        self.commission_net_paid.invoice_state = "paid"
        invoice1 = self._create_invoice(
            self.agent_pending, self.commission_net_paid, "2024-02-15", currency=None
        )
        # Register payment for the new invoice
        invoice2 = self._create_invoice(
            self.agent_pending, self.commission_net_paid, "2024-03-15", currency=None
        )
        invoice3 = self._create_invoice(
            self.agent_pending, self.commission_net_paid, "2024-04-15", currency=None
        )
        # invoice1.invoice_line_ids.agent_ids._compute_amount()
        (invoice1 + invoice2 + invoice3).action_post()
        self._register_payment(invoice1)
        self._register_payment(invoice2)
        self._register_payment(invoice3)
        self._settle_agent_invoice(self.agent_pending, 1)
        settlements = self.settle_model.search([("state", "=", "settled")])
        self.assertEqual(len(settlements.line_ids), 3)
