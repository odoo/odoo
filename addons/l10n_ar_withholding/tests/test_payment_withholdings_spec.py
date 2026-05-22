# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Specification tests for Argentine withholdings applied at payment time.

These tests describe the *expected* behaviour of the AR withholding rules. They are written
from the spec, not from the implementation, and are deliberately self-contained: every
fixture (taxes, scale brackets, partner tax registrations) is built up in the test class
itself instead of relying on the AR chart-template seed data.

Cross-cutting AR rules pinned by these tests:
  - Withholding values exposed to the user (line.base_amount, line.amount) live in the
    payment currency.
  - Legally-binding values are always in ARS (company currency); they appear as `balance`
    on the journal items, and as ARS columns on the payment receipt PDF when the payment
    currency is foreign.
  - Earnings-style withholdings accumulate across the calendar month for a given partner +
    tax code; the accumulator reads `account.move.line.balance` (already in ARS) on prior
    posted payments, so it works regardless of the prior payment's currency.
"""
from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestArInvoicePaymentWithholdingsSpec(TestArCommon):
    # ------------------------------------------------------------------
    # Fixture: simple, hand-rolled withholding taxes (no chart-template dependency)
    # ------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.tax_21 = cls.env.ref(f"account.{company.id}_ri_tax_vat_21_ventas")

        # Sequence shared by all withholdings (the framework requires one for posting).
        cls.wth_seq = cls.env["ir.sequence"].create({
            "name": "AR WTH spec seq",
            "implementation": "standard",
            "padding": 8,
            "number_increment": 1,
        })

        # IIBB 1% on the *untaxed* base.
        cls.iibb_1pc = cls._make_wth(
            company, "IIBB Untaxed 1%", amount=1, ar_type="iibb_untaxed", code="iibb-u",
        )
        # IIBB 0.5% on the *total* (gross) base.
        cls.iibb_total_05pc = cls._make_wth(
            company, "IIBB Total 0.5%", amount=0.5, ar_type="iibb_total", code="iibb-t",
        )
        # Earnings 6% with a non-taxable band and a minimum threshold.
        cls.earnings_6pc = cls._make_wth(
            company, "Earnings 6%", amount=6, ar_type="earnings", code="earn-6",
            l10n_ar_non_taxable_amount=2000, l10n_ar_minimum_threshold=200,
        )
        # Earnings 7% (no band, no threshold) — used for the iteration test.
        cls.earnings_7pc = cls._make_wth(
            company, "Earnings 7%", amount=7, ar_type="earnings", code="earn-7",
        )
        # Progressive earnings scale.
        scale = cls.env["l10n_ar.earnings.scale"].create({"name": "Spec Scale"})
        cls.env["l10n_ar.earnings.scale.line"].create([
            {"scale_id": scale.id, "excess_amount": 0, "to_amount": 10000, "fixed_amount": 0, "percentage": 0},
            {"scale_id": scale.id, "excess_amount": 10000, "to_amount": 20000, "fixed_amount": 0, "percentage": 5},
            {"scale_id": scale.id, "excess_amount": 20000, "to_amount": 50000, "fixed_amount": 500, "percentage": 10},
            {"scale_id": scale.id, "excess_amount": 50000, "to_amount": 100000, "fixed_amount": 3500, "percentage": 15},
        ])
        cls.earnings_scale = cls._make_wth(
            company, "Earnings Scale", amount=0, ar_type="earnings_scale", code="earn-sc",
            l10n_ar_scale_id=scale.id,
        )

        # USD currency with a single rate of 1 USD = 100 ARS, valid on every test date.
        cls.usd = cls.setup_other_currency(
            "USD", rounding=0.01, rates=[("2026-01-01", 0.01)],
        )

        # A vendor we'll pay in every test; partner-tax registrations are added per test.
        cls.vendor = cls.res_partner_adhoc

    @classmethod
    def _make_wth(cls, company, name, amount, ar_type, code, **extra):
        return cls.env["account.tax"].create({
            "name": name,
            "company_id": company.id,
            "country_id": company.account_fiscal_country_id.id,
            "type_tax_use": "purchase",
            "is_withholding_tax_on_payment": True,
            "amount_type": "percent",
            "amount": amount,
            "l10n_ar_tax_type": ar_type,
            "l10n_ar_code": code,
            "withholding_sequence_id": cls.wth_seq.id,
            **extra,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _post_bill(self, *, currency=None, untaxed=1000.0, doc_number="1-1", invoice_date="2026-04-01"):
        # AR posting requires exactly one VAT tax per invoice line; we always attach the
        # 21% VAT. The withholding base is derived from the untaxed-to-total ratio, so the
        # presence of VAT does not change the expected withholding amounts in these tests.
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "currency_id": (currency or self.env.company.currency_id).id,
            "date": invoice_date,
            "invoice_date": invoice_date,
            "l10n_latam_document_number": doc_number,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "price_unit": untaxed,
                "tax_ids": [Command.set(self.tax_21.ids)],
            })],
        })
        bill.action_post()
        return bill

    def _new_register(self, bills, *, currency=None, payment_date="2026-04-15", lines=()):
        """Open the register-payment wizard and (optionally) preload withholding lines."""
        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bills.ids,
        ).new({
            "payment_date": payment_date,
            "currency_id": (currency or self.env.company.currency_id).id,
        })
        if lines:
            wizard.withholding_line_ids = [Command.clear()] + [
                Command.create(vals) for vals in lines
            ]
        return wizard

    def _ensure_own_check_pml(self, journal):
        """Add the Own Checks outbound method to ``journal`` if it isn't there yet."""
        if not journal.outbound_payment_method_line_ids.filtered(lambda m: m.code == "own_checks"):
            journal.outbound_payment_method_line_ids = [Command.create({
                "payment_method_id": self.env.ref("l10n_latam_check.account_payment_method_own_checks").id,
                "name": "Own Checks",
            })]
        return journal.outbound_payment_method_line_ids.filtered(lambda m: m.code == "own_checks")[:1]

    def _make_third_party_check_journal(self, currency=None):
        """Create a `cash` journal that supports inbound new third-party checks (received
        from customers) and outbound existing third-party checks (re-circulated to vendors).
        """
        vals = {
            "name": "Third Party Checks" + (f" ({currency.name})" if currency else ""),
            "type": "cash",
            "outbound_payment_method_line_ids": [Command.create({
                "payment_method_id": self.env.ref("l10n_latam_check.account_payment_method_out_third_party_checks").id,
                "name": "Out Third Party Checks",
            })],
            "inbound_payment_method_line_ids": [
                Command.create({
                    "payment_method_id": self.env.ref("l10n_latam_check.account_payment_method_new_third_party_checks").id,
                    "name": "New Third Party Checks",
                }),
                Command.create({
                    "payment_method_id": self.env.ref("l10n_latam_check.account_payment_method_in_third_party_checks").id,
                    "name": "In Third Party Checks",
                }),
            ],
        }
        if currency:
            vals["currency_id"] = currency.id
        return self.env["account.journal"].create(vals)

    def _create_inbound_third_party_check(self, journal, *, amount, currency=None,
                                          partner=None, name="00001", date="2026-04-01"):
        """Create and post an inbound payment representing a new third-party check entering
        the company. Returns the resulting `l10n_latam.check` recordset (use it as
        `wizard.l10n_latam_move_check_ids` to pay a vendor with that same physical check).
        """
        new_pml = journal.inbound_payment_method_line_ids.filtered(
            lambda m: m.code == "new_third_party_checks",
        )[:1]
        payment = self.env["account.payment"].create({
            "date": date,
            "amount": amount,
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": (partner or self.partner_mipyme).id,
            "journal_id": journal.id,
            "currency_id": (currency or self.env.company.currency_id).id,
            "payment_method_line_id": new_pml.id,
            "l10n_latam_new_check_ids": [Command.create({
                "name": name, "amount": amount, "payment_date": date,
            })],
        })
        payment.action_post()
        return payment.l10n_latam_new_check_ids

    # ------------------------------------------------------------------
    # 1. Single IIBB withholding on an ARS invoice
    # ------------------------------------------------------------------
    def test_iibb_untaxed_single_ars_payment(self):
        """1,000 ARS untaxed + 21% VAT, 1% IIBB withholding on the untaxed base."""
        bill = self._post_bill(untaxed=1000.0, doc_number="1-1")
        wizard = self._new_register(bill, lines=[{"tax_id": self.iibb_1pc.id}])

        line = wizard.withholding_line_ids
        self.assertEqual(line.tax_id, self.iibb_1pc)
        self.assertAlmostEqual(line.base_amount, 1000.00, places=2)   # untaxed
        self.assertAlmostEqual(line.amount, 10.00, places=2)          # 1% of 1000
        self.assertAlmostEqual(wizard.withholding_net_amount, 1200.00, places=2)
        self.assertAlmostEqual(wizard.amount, 1210.00, places=2)      # gross stays gross

        payment = self.env["account.payment"].browse(wizard.action_create_payments()["res_id"])
        self.assertAlmostEqual(payment.amount, 1210.00, places=2)
        wth_aml = payment.move_id.line_ids.filtered(lambda l: l.tax_line_id == self.iibb_1pc)
        self.assertAlmostEqual(wth_aml.balance, -10.00, places=2)     # ARS, signed

    # ------------------------------------------------------------------
    # 2. Two withholdings on the same payment (untaxed-base + total-base)
    # ------------------------------------------------------------------
    def test_two_iibb_withholdings(self):
        """One IIBB on untaxed (1%), one IIBB on total (0.5%); same 1,000 + 21% bill."""
        bill = self._post_bill(untaxed=1000.0, doc_number="1-2")
        wizard = self._new_register(bill, lines=[
            {"tax_id": self.iibb_1pc.id},
            {"tax_id": self.iibb_total_05pc.id},
        ])

        wth_u = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == self.iibb_1pc)
        wth_t = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == self.iibb_total_05pc)
        self.assertAlmostEqual(wth_u.base_amount, 1000.00, places=2)  # untaxed
        self.assertAlmostEqual(wth_u.amount, 10.00, places=2)
        self.assertAlmostEqual(wth_t.base_amount, 1210.00, places=2)  # total
        self.assertAlmostEqual(wth_t.amount, 6.05, places=2)          # 0.5% of 1210
        self.assertAlmostEqual(wizard.withholding_net_amount, 1193.95, places=2)

    # ------------------------------------------------------------------
    # 3. Earnings withholding with non-taxable amount + minimum threshold
    # ------------------------------------------------------------------
    def test_earnings_with_non_taxable_and_threshold(self):
        """6% earnings, non_taxable=2,000, threshold=200.

        Below threshold (small bill) → WTH = 0.
        Above threshold (large bill) → WTH = (untaxed - non_taxable) x 6%.
        """
        # Below threshold: 5,000 untaxed + 21% VAT = 6,050 gross.
        small = self._post_bill(untaxed=5000.0, doc_number="3-1")
        wizard = self._new_register(small, lines=[{"tax_id": self.earnings_6pc.id}])
        # Base = wizard.amount x untaxed/total = 6,050 x 5,000/6,050 = 5,000.
        # Tentative tax = (5,000 - 2,000) x 6% = 180 → below threshold 200 → 0.
        self.assertAlmostEqual(wizard.withholding_line_ids.amount, 0.00, places=2)
        self.assertAlmostEqual(wizard.withholding_net_amount, 6050.00, places=2)

        # Above threshold: 10,000 untaxed + 21% VAT = 12,100 gross.
        big = self._post_bill(untaxed=10000.0, doc_number="3-2")
        wizard = self._new_register(big, lines=[{"tax_id": self.earnings_6pc.id}])
        # Base = 10,000. (10,000 - 2,000) x 6% = 480 → above threshold → 480.
        self.assertAlmostEqual(wizard.withholding_line_ids.amount, 480.00, places=2)
        self.assertAlmostEqual(wizard.withholding_net_amount, 11620.00, places=2)

    # ------------------------------------------------------------------
    # 4. Earnings-scale (progressive brackets)
    # ------------------------------------------------------------------
    def test_earnings_scale_progressive_brackets(self):
        """30,000 ARS bill — falls in bracket [20,000-50,000): WTH = (30k - 20k) x 10% + 500."""
        bill = self._post_bill(untaxed=30000.0, doc_number="4-1")  # 30,000 + 21% VAT = 36,300
        wizard = self._new_register(bill, lines=[{"tax_id": self.earnings_scale.id}])
        # Base = 36,300 x 30,000/36,300 = 30,000. Bracket [20k, 50k): (30k - 20k) x 10% + 500 = 1,500.
        self.assertAlmostEqual(wizard.withholding_line_ids.amount, 1500.00, places=2)
        self.assertAlmostEqual(wizard.withholding_net_amount, 34800.00, places=2)  # 36,300 - 1,500

    # ------------------------------------------------------------------
    # 5. Earnings accumulation across two same-month payments
    # ------------------------------------------------------------------
    def test_earnings_accumulation_same_month(self):
        """Two payments to the same vendor in the same month, single earnings-scale tax.

        Payment 1: base 10,000 → bracket boundary, accumulator-aware tax = 0 → WTH = 0.
        Payment 2: base 25,000 → cumulative base 35,000, cumulative tax = 1,500;
                    minus already-withheld (0) → WTH = 1,500.
        """
        bill1 = self._post_bill(untaxed=10000.0, doc_number="5-1", invoice_date="2026-04-05")
        wizard1 = self._new_register(bill1, payment_date="2026-04-05",
                                     lines=[{"tax_id": self.earnings_scale.id}])
        # Base = 10,000 (12,100 x 10/12.1). Bracket [10k, 20k): (10k - 10k) x 5% + 0 = 0.
        self.assertAlmostEqual(wizard1.withholding_line_ids.amount, 0.00, places=2)
        wizard1.action_create_payments()

        bill2 = self._post_bill(untaxed=25000.0, doc_number="5-2", invoice_date="2026-04-20")
        wizard2 = self._new_register(bill2, payment_date="2026-04-20",
                                     lines=[{"tax_id": self.earnings_scale.id}])
        # Base = 25,000. Cumulative base = 35,000 → bracket [20k, 50k): (35k - 20k) x 10% + 500 = 2,000.
        # Already withheld in this month: 0 → WTH on this payment = 2,000.
        self.assertAlmostEqual(wizard2.withholding_line_ids.amount, 2000.00, places=2)

    # ------------------------------------------------------------------
    # 6. USD invoice + USD payment with IIBB-untaxed: WTH stored in USD, ARS via balance
    # ------------------------------------------------------------------
    def test_usd_invoice_usd_payment_iibb_untaxed(self):
        """100 USD untaxed + 21% VAT, paid in USD at 1 USD = 100 ARS.

        Line shown to the user (payment currency):
            base_amount =  100 USD,  amount = 10 USD,  net = 111 USD.
        Journal entry (balance = ARS):
            WTH tax line: amount_currency = -10 USD, balance = -1,000 ARS (legal value).
        """
        bill = self._post_bill(currency=self.usd, untaxed=100.0, doc_number="6-1",
                               invoice_date="2026-04-01")
        wizard = self._new_register(
            bill, currency=self.usd, payment_date="2026-04-01",
            lines=[{"tax_id": self.iibb_1pc.id, "amount": 0}],   # 1% x 100 USD untaxed = 1 USD
        )
        # Note: iibb_1pc is 1%; the spec doc shows 10% to keep numbers round, but the
        # fixture uses 1% so we adjust here. (1% x 100 USD = 1 USD; balance = 100 ARS.)
        line = wizard.withholding_line_ids
        self.assertEqual(line.comodel_currency_id, self.usd)
        self.assertAlmostEqual(line.base_amount, 100.00, places=2)
        self.assertAlmostEqual(line.amount, 1.00, places=2)
        self.assertAlmostEqual(wizard.withholding_net_amount, 120.00, places=2)  # 121 - 1

        payment = self.env["account.payment"].browse(wizard.action_create_payments()["res_id"])
        wth_aml = payment.move_id.line_ids.filtered(lambda l: l.tax_line_id == self.iibb_1pc)
        self.assertEqual(wth_aml.currency_id, self.usd)
        self.assertAlmostEqual(wth_aml.amount_currency, -1.00, places=2)
        self.assertAlmostEqual(wth_aml.balance, -100.00, places=2)               # 1 USD x 100

    # ------------------------------------------------------------------
    # 7. USD own-check payment: Newton iteration solves for the gross USD amount
    # ------------------------------------------------------------------
    def test_usd_own_check_solves_gross_amount(self):
        """50 USD untaxed + 21% VAT, earnings 7%, fixed check = 50 USD, 1 USD = 100 ARS.

        The wizard solves G such that G - wth_usd(G) = 50, where wth_usd(G) is computed
        in ARS internally and converted back to USD:
            wth_usd(G) = 0.07 x G x 50 / 60.5 ≈ 0.05785 x G
            G ≈ 50 / (1 - 0.05785) ≈ 53.07 USD.
        """
        # Add own-checks method on the company's bank journal.
        bank_journal = self.env["account.journal"].search([
            *self.env["account.journal"]._check_company_domain(self.env.company),
            ("type", "=", "bank"),
        ], limit=1)
        own_check_pml = self._ensure_own_check_pml(bank_journal)

        # Register an earnings-7% partner-tax for the vendor (so the wizard auto-populates).
        self.env["l10n_ar.partner.tax"].create({
            "partner_id": self.vendor.id,
            "company_id": self.env.company.id,
            "tax_id": self.earnings_7pc.id,
        })

        bill = self._post_bill(currency=self.usd, untaxed=50.0, doc_number="7-1",
                               invoice_date="2026-04-15")
        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).new({
            "payment_date": "2026-04-15",
            "currency_id": self.usd.id,
            "journal_id": bank_journal.id,
            "payment_method_line_id": own_check_pml.id,
            "l10n_latam_new_check_ids": [Command.create({
                "name": "00000001", "amount": 50.0, "payment_date": "2026-04-15",
            })],
        })
        # Trigger Newton iteration explicitly (cascading recompute on .new() doesn't always
        # re-run _compute_amount once every dependent field is set).
        wizard._compute_amount()

        line = wizard.withholding_line_ids
        self.assertEqual(line.tax_id, self.earnings_7pc)
        self.assertEqual(line.comodel_currency_id, self.usd)
        self.assertAlmostEqual(wizard.amount, 53.07, places=1)
        self.assertAlmostEqual(line.base_amount, 43.86, places=1)
        self.assertAlmostEqual(line.amount, 3.07, places=1)
        self.assertAlmostEqual(wizard.withholding_net_amount, 50.00, places=2)

    # ------------------------------------------------------------------
    # 8. Multi-partner payment registration disables the WTH editor and shows the alert
    # ------------------------------------------------------------------
    def test_grouping_alert_when_paying_bills_of_two_partners(self):
        """When the wizard is opened on bills from different partners (or grouping is off),
        the user can't edit the withholding lines, and the `l10n_ar_withholding_grouping`
        alert is added to the wizard's `alerts`.
        """
        bill_a = self._post_bill(untaxed=1000.0, doc_number="8-1")
        bill_b = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner_mipyme.id,
            "date": "2026-04-01",
            "invoice_date": "2026-04-01",
            "l10n_latam_document_number": "8-2",
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_21.ids)],
            })],
        })
        bill_b.action_post()

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=(bill_a + bill_b).ids,
        ).create({"payment_date": "2026-04-15"})

        # `can_edit_wizard` is False → grouping alert is emitted AND withholding lines
        # are cleared (the AR override won't auto-populate when the editor is hidden).
        self.assertFalse(wizard.can_edit_wizard, "Cannot edit wizard when paying multiple partners")
        self.assertIn("l10n_ar_withholding_grouping", wizard.alerts or {})
        self.assertFalse(wizard.withholding_line_ids)

    # ------------------------------------------------------------------
    # 9. Partner-tax date validity constraint
    # ------------------------------------------------------------------
    def test_partner_tax_date_range_constraint(self):
        """`l10n_ar.partner.tax` requires `from_date < to_date` when both are set."""
        with self.assertRaises(ValidationError):
            self.env["l10n_ar.partner.tax"].create({
                "partner_id": self.vendor.id,
                "company_id": self.env.company.id,
                "tax_id": self.earnings_6pc.id,
                "from_date": "2026-01-10",
                "to_date": "2026-01-05",  # to before from
            })

    # ------------------------------------------------------------------
    # 11. Earnings-scale `from_amount` exposes the previous bracket's upper bound
    # ------------------------------------------------------------------
    def test_earnings_scale_from_amount_compute(self):
        """The display-only `from_amount` on each scale line equals the previous bracket's
        `to_amount` (or 0 for the first bracket).
        """
        scale_lines = self.earnings_scale.l10n_ar_scale_id.line_ids.sorted("to_amount")
        # Brackets defined in setUpClass: to_amounts = 10000, 20000, 50000, 100000.
        self.assertEqual(scale_lines[0].from_amount, 0)
        self.assertEqual(scale_lines[1].from_amount, 10000)
        self.assertEqual(scale_lines[2].from_amount, 20000)
        self.assertEqual(scale_lines[3].from_amount, 50000)

    # ------------------------------------------------------------------
    # 12. ARS own-check + earnings WTH: Newton iteration in company currency
    # ------------------------------------------------------------------
    def test_ars_own_check_with_earnings_iteration(self):
        """ARS bill of 50 + 21% VAT = 60.50, earnings 7%, fixed own check of 50 ARS.

        Same algebra as the USD own-check case but with no currency conversion involved.
        Solves G - 0.07·(50/60.5)·G = 50 → G ≈ 53.07 ARS.
        """
        self.env["l10n_ar.partner.tax"].create({
            "partner_id": self.vendor.id,
            "company_id": self.env.company.id,
            "tax_id": self.earnings_7pc.id,
        })
        bank_journal = self.env["account.journal"].search([
            *self.env["account.journal"]._check_company_domain(self.env.company),
            ("type", "=", "bank"),
        ], limit=1)
        own_check_pml = self._ensure_own_check_pml(bank_journal)
        bill = self._post_bill(untaxed=50.0, doc_number="12-1")

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).new({
            "payment_date": "2026-04-15",
            "journal_id": bank_journal.id,
            "payment_method_line_id": own_check_pml.id,
            "l10n_latam_new_check_ids": [Command.create({
                "name": "00000001", "amount": 50.0, "payment_date": "2026-04-15",
            })],
        })
        wizard._compute_amount()

        line = wizard.withholding_line_ids
        self.assertEqual(line.tax_id, self.earnings_7pc)
        self.assertEqual(line.comodel_currency_id, self.env.company.currency_id)
        self.assertAlmostEqual(wizard.amount, 53.07, places=1)
        self.assertAlmostEqual(line.base_amount, 43.86, places=1)
        self.assertAlmostEqual(line.amount, 3.07, places=1)
        self.assertAlmostEqual(wizard.withholding_net_amount, 50.00, places=2)

    # ------------------------------------------------------------------
    # 13. ARS third-party check + earnings WTH: same algebra, different instrument
    # ------------------------------------------------------------------
    def test_ars_third_party_check_with_earnings_iteration(self):
        """ARS bill of 50 + 21% VAT = 60.50, earnings 7%, paid by re-circulating an
        existing 50 ARS third-party check (received earlier from a customer).
        """
        self.env["l10n_ar.partner.tax"].create({
            "partner_id": self.vendor.id,
            "company_id": self.env.company.id,
            "tax_id": self.earnings_7pc.id,
        })
        third_party_journal = self._make_third_party_check_journal()
        inbound_checks = self._create_inbound_third_party_check(
            third_party_journal, amount=50.0, name="ARS-001",
        )
        bill = self._post_bill(untaxed=50.0, doc_number="13-1")
        out_pml = third_party_journal.outbound_payment_method_line_ids.filtered(
            lambda m: m.code == "out_third_party_checks",
        )[:1]

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).new({
            "payment_date": "2026-04-15",
            "journal_id": third_party_journal.id,
            "payment_method_line_id": out_pml.id,
            "l10n_latam_move_check_ids": inbound_checks,
        })
        wizard._compute_amount()

        line = wizard.withholding_line_ids
        self.assertEqual(line.tax_id, self.earnings_7pc)
        self.assertAlmostEqual(wizard.amount, 53.07, places=1)
        self.assertAlmostEqual(line.amount, 3.07, places=1)
        self.assertAlmostEqual(wizard.withholding_net_amount, 50.00, places=2)

    # ------------------------------------------------------------------
    # 14. USD third-party check + earnings WTH: foreign-currency re-circulation
    # ------------------------------------------------------------------
    def test_usd_third_party_check_with_earnings_iteration(self):
        """USD bill of 50 + 21% VAT = 60.50 USD, earnings 7%, paid by re-circulating an
        existing 50 USD third-party check at 1 USD = 100 ARS.

        WTH line is in USD; the legal ARS values come from balance via standard rate
        conversion. Iteration converges to the same 53.07 USD as the own-check case.
        """
        self.env["l10n_ar.partner.tax"].create({
            "partner_id": self.vendor.id,
            "company_id": self.env.company.id,
            "tax_id": self.earnings_7pc.id,
        })
        third_party_journal = self._make_third_party_check_journal(currency=self.usd)
        inbound_checks = self._create_inbound_third_party_check(
            third_party_journal, amount=50.0, currency=self.usd, name="USD-001",
        )
        bill = self._post_bill(currency=self.usd, untaxed=50.0, doc_number="14-1",
                               invoice_date="2026-04-15")
        out_pml = third_party_journal.outbound_payment_method_line_ids.filtered(
            lambda m: m.code == "out_third_party_checks",
        )[:1]

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).new({
            "payment_date": "2026-04-15",
            "currency_id": self.usd.id,
            "journal_id": third_party_journal.id,
            "payment_method_line_id": out_pml.id,
            "l10n_latam_move_check_ids": inbound_checks,
        })
        wizard._compute_amount()

        line = wizard.withholding_line_ids
        self.assertEqual(line.tax_id, self.earnings_7pc)
        self.assertEqual(line.comodel_currency_id, self.usd)
        self.assertAlmostEqual(wizard.amount, 53.07, places=1)
        self.assertAlmostEqual(line.base_amount, 43.86, places=1)
        self.assertAlmostEqual(line.amount, 3.07, places=1)
        self.assertAlmostEqual(wizard.withholding_net_amount, 50.00, places=2)
