# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestDeliveryCarrier(WebsiteSaleCommon):
    def _enable_delivery_estimate(self, carrier):
        carrier.write({
            "enable_delivery_estimate": True,
            "delivery_estimate_lead_days": 1,
            "delivery_estimate_range_days": 5,
            "delivery_calendar_id": self.env["resource.calendar"].search([], limit=1).id,
        })

    def test_estimated_delivery_settings_kept_when_switching_to_supported_type(self):
        """Estimated delivery settings survive a switch between types that support them."""
        self._enable_delivery_estimate(self.carrier)

        self.carrier.delivery_type = "base_on_rule"

        self.assertRecordValues(
            self.carrier,
            [
                {
                    "enable_delivery_estimate": True,
                    "delivery_estimate_lead_days": 1,
                    "delivery_estimate_range_days": 5,
                    "delivery_calendar_id": self.env["resource.calendar"].search([], limit=1).id,
                }
            ],
        )

    def test_estimated_delivery_settings_reset_when_switching_to_unsupported_type(self):
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
                    "enable_delivery_estimate": False,
                    "delivery_estimate_lead_days": 0,
                    "delivery_estimate_range_days": 0,
                    "delivery_calendar_id": False,
                }
            ],
        )
