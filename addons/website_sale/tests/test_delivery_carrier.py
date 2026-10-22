# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestDeliveryCarrier(WebsiteSaleCommon):
    _test_user_groups = ("base.group_user", "sales_team.group_sale_manager")

    _test_user_name = "Test Sales Manager"

    def _enable_delivery_estimate(self, carrier):
        carrier.write({
            "delivery_estimate_mode": "user_choice",
            "delivery_estimate_min_days": 1,
            "delivery_estimate_max_days": 5,
            "delivery_calendar_id": self.env["resource.calendar"].search([], limit=1).id,
        })

    def test_delivery_estimate_settings_kept_when_switching_to_supported_type(self):
        """Estimated delivery settings survive a switch between types that support them."""
        self._enable_delivery_estimate(self.carrier)

        self.carrier.delivery_type = "base_on_rule"

        self.assertRecordValues(
            self.carrier,
            [
                {
                    "delivery_estimate_mode": "user_choice",
                    "delivery_estimate_min_days": 1,
                    "delivery_estimate_max_days": 5,
                    "delivery_calendar_id": self.env["resource.calendar"].search([], limit=1).id,
                }
            ],
        )

    def test_delivery_estimate_fixed_sets_unset_max_days_to_fixed_day(self):
        """The fixed mode raises an unset maximum to the fixed day."""
        self.carrier.write({"delivery_estimate_mode": "fixed", "delivery_estimate_min_days": 6})

        self.assertEqual(self.carrier.delivery_estimate_max_days, 6)

    def test_delivery_estimate_fixed_raises_max_days_below_fixed_day(self):
        """The fixed mode raises a maximum that is below the fixed day."""
        self.carrier.write({
            "delivery_estimate_mode": "user_choice",
            "delivery_estimate_min_days": 6,
            "delivery_estimate_max_days": 10,
        })

        self.carrier.write({"delivery_estimate_mode": "fixed", "delivery_estimate_min_days": 12})

        self.assertEqual(self.carrier.delivery_estimate_max_days, 12)

    def test_delivery_estimate_fixed_lowers_max_days_above_fixed_day(self):
        """The fixed mode lowers a maximum that is above the fixed day."""
        self.carrier.write({
            "delivery_estimate_mode": "user_choice",
            "delivery_estimate_min_days": 6,
            "delivery_estimate_max_days": 10,
        })

        self.carrier.delivery_estimate_mode = "fixed"

        self.assertEqual(self.carrier.delivery_estimate_max_days, 6)

    def test_delivery_estimate_settings_reset_when_switching_to_unsupported_type(self):
        """Estimated delivery settings are reset when the new type does not support them."""
        self._enable_delivery_estimate(self.carrier)

        with patch.object(
            self.registry["delivery.carrier"],
            "_get_delivery_estimate_supported_types",
            return_value=["fixed"],
        ):
            self.carrier.delivery_type = "base_on_rule"

        self.assertRecordValues(
            self.carrier,
            [
                {
                    "delivery_estimate_mode": "none",
                    "delivery_estimate_min_days": 0,
                    "delivery_estimate_max_days": 0,
                    "delivery_calendar_id": False,
                }
            ],
        )
