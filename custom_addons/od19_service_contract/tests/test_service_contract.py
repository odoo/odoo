# -*- coding: utf-8 -*-
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestServiceContract(TransactionCase):
    """Acceptance tests for the recurring service contract wrapper (Wave 6.2 / WS-05).

    * A1 - a 12-month monthly contract generates exactly 12 invoices, one per
      period, and never invoices past its end date.
    * A2 - renewing manually pushes the end date out and resumes billing.
    * A3 - the daily cron auto-renews an expired contract when ``auto_renew``.
    * A4 - the daily cron raises a ``mail.activity`` before the end date.
    * A5 - preventive-maintenance cards can be linked to the contract.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create(
            {"name": "Service Contract Customer TEST"}
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Service Contract Income TEST",
                "code": "499201",
                "account_type": "income",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "AMC Service TEST",
                "type": "service",
                "list_price": 1000.0,
                "property_account_income_id": cls.income_account.id,
            }
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_contract(self, date_start, date_end, **kwargs):
        line_vals = {
            "name": "AMC Service TEST",
            "product_id": self.product.id,
            "quantity": 1.0,
            "price_unit": 1000.0,
            "date_start": date_start,
            "date_end": date_end,
            "recurring_next_date": date_start,
        }
        vals = {
            "name": "Service Contract TEST",
            "partner_id": self.partner.id,
            "contract_type": "sale",
            "is_service_contract": True,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "recurring_invoicing_type": "pre-paid",
            "date_start": date_start,
            "contract_line_ids": [Command.create(line_vals)],
        }
        if self.sale_journal:
            vals["journal_id"] = self.sale_journal.id
        vals.update(kwargs)
        return self.env["contract.contract"].create(vals)

    # ------------------------------------------------------------------
    # A1 - automatic monthly invoicing
    # ------------------------------------------------------------------
    def test_monthly_invoice_generation(self):
        date_start = date(2026, 1, 1)
        date_end = date(2026, 12, 31)
        contract = self._create_contract(date_start, date_end)

        self.assertEqual(contract.date_end, date_end)
        self.assertEqual(contract.recurring_next_date, date_start)

        invoices = self.env["account.move"]
        for _index in range(12):
            invoices |= contract._recurring_create_invoice()

        self.assertEqual(len(invoices), 12)
        self.assertTrue(all(move.move_type == "out_invoice" for move in invoices))
        # The last period is billed and then billing stops at the end date.
        self.assertEqual(contract.date_end, date_end)
        self.assertEqual(contract.contract_line_ids.last_date_invoiced, date_end)
        # A further run must not create anything beyond the end date.
        self.assertFalse(contract._recurring_create_invoice())

    # ------------------------------------------------------------------
    # A2 - manual renewal
    # ------------------------------------------------------------------
    def test_manual_renewal_extends_end_date(self):
        date_start = date(2026, 1, 1)
        date_end = date(2026, 12, 31)
        contract = self._create_contract(
            date_start, date_end, renewal_interval_months=12
        )
        for _index in range(12):
            contract._recurring_create_invoice()
        self.assertFalse(contract._recurring_create_invoice())

        contract.action_renew()

        self.assertEqual(contract.date_end, date(2027, 12, 31))
        # Billing resumes for the renewed period.
        renewed_invoice = contract._recurring_create_invoice()
        self.assertEqual(len(renewed_invoice), 1)

    # ------------------------------------------------------------------
    # A3 - automatic renewal through the cron
    # ------------------------------------------------------------------
    def test_cron_auto_renewal(self):
        date_start = date(2025, 1, 1)
        date_end = date(2025, 12, 31)
        contract = self._create_contract(
            date_start, date_end, auto_renew=True, renewal_interval_months=12
        )
        self.assertTrue(contract.date_end < fields.Date.context_today(contract))

        self.env["contract.contract"].cron_service_contract_renewal()

        self.assertEqual(contract.date_end, date(2026, 12, 31))

    # ------------------------------------------------------------------
    # A4 - expiry notice before the end date
    # ------------------------------------------------------------------
    def test_cron_renewal_notice_activity(self):
        today = fields.Date.context_today(self.env["contract.contract"])
        date_start = today - relativedelta(months=11)
        date_end = today + relativedelta(days=10)
        contract = self._create_contract(
            date_start, date_end, auto_renew=False, renewal_notice_days=30
        )

        self.env["contract.contract"].cron_service_contract_renewal()

        self.assertTrue(contract.renewal_notice_sent)
        activities = contract.activity_ids.filtered(
            lambda act: act.summary and "expires soon" in act.summary
        )
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].user_id, contract.user_id)
        # Running the cron again must not duplicate the reminder.
        self.env["contract.contract"].cron_service_contract_renewal()
        self.assertEqual(len(contract.activity_ids), 1)

    # ------------------------------------------------------------------
    # A5 - service card linkage
    # ------------------------------------------------------------------
    def test_service_card_link(self):
        contract = self._create_contract(date(2026, 1, 1), date(2026, 12, 31))
        card = self.env["od19.service.card"].create(
            {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "contract_id": contract.id,
            }
        )

        self.assertEqual(card.contract_id, contract)
        self.assertEqual(contract.service_card_count, 1)
        self.assertIn(card, contract.service_card_ids)
