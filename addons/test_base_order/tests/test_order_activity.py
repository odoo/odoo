from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerOrderActivity(TransactionCase):
    """Cover ``base_order``'s order-activity figures on the test order type.

    ``recent_orders_count`` and ``days_since_last_order`` used to be sale-only
    fields living in a downstream instance module. They are generic here, so
    the behaviour every order type inherits — the company-configured cycle,
    the never-ordered sentinel, the partner and source hooks — is pinned once.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write(
            {
                "order_cycle_count": 3,
                "order_cycle_unit": "month",
            },
        )
        cls.partner = cls.env["res.partner"].create({"name": "Activity"})
        cls.other = cls.env["res.partner"].create({"name": "Quiet"})

    def _make_order(self, partner, days_ago, state="done"):
        order = self.env["base.order.test"].create({"partner_id": partner.id})
        order.write(
            {
                "state": state,
                "date_order": fields.Datetime.now() - timedelta(days=days_ago),
            },
        )
        return order

    def test_only_orders_inside_the_cycle_are_counted(self):
        self._make_order(self.partner, days_ago=10)
        self._make_order(self.partner, days_ago=40)
        self._make_order(self.partner, days_ago=200)

        self.partner.invalidate_recordset(["recent_orders_count"])
        self.assertEqual(
            self.partner.recent_orders_count,
            2,
            "the 200-day-old order falls outside a three-month cycle",
        )

    def test_cycle_length_is_read_from_the_company(self):
        self._make_order(self.partner, days_ago=200)

        self.partner.invalidate_recordset(["recent_orders_count"])
        self.assertEqual(self.partner.recent_orders_count, 0)

        self.company.base_order_config_id.order_cycle_count = 1
        self.company.base_order_config_id.order_cycle_unit = "year"
        self.partner.invalidate_recordset(["recent_orders_count"])
        self.assertEqual(
            self.partner.recent_orders_count,
            1,
            "a longer cycle brings the same order back into range",
        )

    def test_source_domain_excludes_unconfirmed_orders(self):
        self._make_order(self.partner, days_ago=1, state="draft")
        self._make_order(self.partner, days_ago=1, state="cancel")

        self.partner.invalidate_recordset(["recent_orders_count"])
        self.assertEqual(self.partner.recent_orders_count, 0)

    def test_days_since_last_order_uses_the_newest_order(self):
        self._make_order(self.partner, days_ago=400)
        self._make_order(self.partner, days_ago=12)

        self.partner.invalidate_recordset(["days_since_last_order"])
        self.assertEqual(self.partner.days_since_last_order, 12)

    def test_days_since_last_order_ignores_the_cycle(self):
        self._make_order(self.partner, days_ago=400)

        self.partner.invalidate_recordset(["days_since_last_order"])
        self.assertEqual(
            self.partner.days_since_last_order,
            400,
            "the cycle bounds the count, not the age of the last order",
        )

    def test_never_ordered_partner_gets_the_sentinel(self):
        self.other.invalidate_recordset(["days_since_last_order"])
        self.assertEqual(self.other.days_since_last_order, 9999)

    def test_partner_hook_narrows_who_is_measured(self):
        self._make_order(self.partner, days_ago=1)
        self._make_order(self.other, days_ago=1)

        partners = self.partner | self.other
        narrowed = self.partner

        original = type(partners)._get_order_activity_partners
        self.patch(
            type(partners),
            "_get_order_activity_partners",
            lambda records: original(records) & narrowed,
        )

        partners.invalidate_recordset(
            ["recent_orders_count", "days_since_last_order"],
        )
        self.assertEqual(self.partner.recent_orders_count, 1)
        self.assertEqual(
            self.other.recent_orders_count,
            0,
            "a partner the hook excludes is zeroed, not counted",
        )
        self.assertEqual(
            self.other.days_since_last_order,
            0,
            "an excluded partner gets 0, not the never-ordered sentinel",
        )

    def test_cutoff_date_follows_the_configured_unit(self):
        today = fields.Date.today()
        for number, unit, expected in [
            (10, "day", relativedelta(days=10)),
            (2, "week", relativedelta(weeks=2)),
            (6, "month", relativedelta(months=6)),
            (1, "year", relativedelta(years=1)),
        ]:
            with self.subTest(cycle=(number, unit)):
                self.company.base_order_config_id.order_cycle_count = number
                self.company.base_order_config_id.order_cycle_unit = unit
                self.assertEqual(
                    self.company._get_order_cycle_cutoff_date(), today - expected
                )

    def test_a_zero_cycle_is_allowed_and_a_negative_one_is_not(self):
        self.company.base_order_config_id.order_cycle_count = 0
        self.assertEqual(
            self.company._get_order_cycle_cutoff_date(),
            fields.Date.today(),
        )

        with self.assertRaises(ValidationError):
            self.company.base_order_config_id.order_cycle_count = -1
