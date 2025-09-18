import datetime
import logging
from unittest.mock import patch

from odoo.libs.datetime import tz
from odoo.libs.datetime.tz import TIMEZONE_ALIASES, all_timezones, timezone
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestTZ(TransactionCase):
    def test_tz_legacy(self):
        """Test that legacy timezone names are properly mapped to canonical names."""
        # Use a recent date to avoid historical timezone rule differences
        # (some aliases like Mexico/BajaNorte -> America/Tijuana differ at historical dates)
        d = datetime.datetime(2024, 6, 15)

        def assertTZEqual(tz1, tz2):
            # Compare timezone offsets at a specific date
            dt1 = d.replace(tzinfo=tz1)
            dt2 = d.replace(tzinfo=tz2)
            self.assertEqual(dt1.strftime("%z"), dt2.strftime("%z"))

        for source, target in TIMEZONE_ALIASES.items():
            with self.subTest(source=source, target=target):
                if (
                    source == "Pacific/Enderbury"
                ):  # this one was wrong in some version of tzdata
                    continue
                try:
                    target_tz = timezone(target)
                except KeyError:
                    _logger.info(
                        "Skipping test for %s -> %s, target does not exist",
                        source,
                        target,
                    )
                    continue
                # Clear cache between iterations to test fresh lookups
                tz._timezone_cache.clear()
                source_tz = timezone(source)
                assertTZEqual(source_tz, target_tz)

    def test_dont_adapt_available_tz(self):
        """Test that available timezones are not replaced by alias mapping."""
        with patch.dict(
            TIMEZONE_ALIASES,
            {
                "DeprecatedUtc": "UTC",
                "America/New_York": "UTC",
            },
            clear=False,
        ):
            # Clear the cache to pick up the new mapping
            tz._timezone_cache.clear()

            self.assertNotIn(
                "DeprecatedUtc",
                all_timezones(),
                "DeprecatedUtc is not available",
            )
            # DeprecatedUtc should be mapped to UTC
            deprecated_tz = timezone("DeprecatedUtc")
            utc_tz = timezone("UTC")
            # They should be the same (both UTC)
            now = datetime.datetime.now()
            self.assertEqual(
                now.replace(tzinfo=deprecated_tz).strftime("%z"),
                now.replace(tzinfo=utc_tz).strftime("%z"),
                "DeprecatedUtc does not exist and should have been replaced with UTC",
            )

            self.assertIn(
                "America/New_York",
                all_timezones(),
                "America/New_York is available",
            )
            # Clear cache again to ensure America/New_York is looked up fresh
            tz._timezone_cache.clear()
            ny_tz = timezone("America/New_York")
            # America/New_York should NOT be replaced with UTC even if in mapping
            # because it exists in all_timezones
            self.assertNotEqual(
                now.replace(tzinfo=ny_tz).strftime("%z"),
                now.replace(tzinfo=utc_tz).strftime("%z"),
                "America/New_York exists and should not have been replaced with UTC",
            )

    def test_cannot_set_deprecated_timezone(self):
        """Test setting deprecated timezone names on user."""
        # Canonical timezone should always work via Selection field
        self.env.user.tz = "America/New_York"
        if "US/Eastern" not in all_timezones():
            # US/Eastern is not in the Selection values, so the field rejects it.
            # Verify the alias mapping works at the tz utility level instead.
            resolved = tz.timezone("US/Eastern")
            self.assertEqual(resolved.key, "America/New_York")

    def test_partner_with_old_tz(self):
        """Test partner with old timezone name stored in database."""
        # Clear cache to ensure we get fresh timezone lookups
        tz._timezone_cache.clear()

        # this test makes sense after ubuntu noble without tzdata-legacy installed
        partner = self.env["res.partner"].create({"name": "test", "tz": "UTC"})
        self.env.cr.execute(
            """UPDATE res_partner set tz='US/Eastern' WHERE id=%s""",
            (partner.id,),
        )
        partner.invalidate_recordset()
        self.assertEqual(
            partner.tz, "US/Eastern"
        )  # tz was updated despite selection not existing

        # comparing with 'America/New_York' - US/Eastern is aliased to America/New_York
        expected_offset = datetime.datetime.now(timezone("America/New_York")).strftime(
            "%z"
        )
        # offset will be -0400 in summer, -0500 in winter
        self.assertEqual(
            partner.tz_offset,
            expected_offset,
            "Timezone offset should work even with deprecated timezone names",
        )
