import datetime
import logging
from unittest.mock import patch
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from odoo.tests.common import tagged, TransactionCase
from odoo._monkeypatches.zoneinfo import _tz_mapping
from odoo.tools.date_utils import all_timezones

_logger = logging.getLogger(__name__)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestTZ(TransactionCase):

    def test_tz_legacy(self):
        d = datetime.datetime(1969, 7, 16)
        # See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        def assertTZEqual(tz1, tz2):
            self.assertEqual(d.replace(tzinfo=tz1).strftime('%z'), d.replace(tzinfo=tz2).strftime('%z'))

            # in some version of tzdata the timezones are not symlink, as an example in 2023c-0ubuntu0.20.04.1
            # this as a side effect to have sligh difference in timezones seconds, breaking the following assertions
            # in some cases:
            #
            # self.assertEqual(tz1._utcoffset, tz2._utcoffset)
            # if hasattr(tz2, '_transition_info'):
            #     self.assertEqual(tz1._transition_info, tz2._transition_info)
            #
            # the first one is more robust

        for source, target in _tz_mapping.items():
            with self.subTest(source=source, target=target):
                if source == 'Pacific/Enderbury':  # this one was wrong in some version of tzdata
                    continue
                try:
                    target_tz = ZoneInfo(target)
                except ZoneInfoNotFoundError:
                    _logger.info("Skipping test for %s -> %s, target does not exist", source, target)
                    continue
                assertTZEqual(ZoneInfo(source), target_tz)

    def test_dont_adapt_available_tz(self):
        with patch.dict(_tz_mapping, {
            'DeprecatedUtc': 'UTC',
            'America/New_York': 'UTC',
        }):
            self.assertNotIn('DeprecatedUtc', all_timezones, 'DeprecatedUtc is not available')
            self.assertEqual(ZoneInfo('DeprecatedUtc'), ZoneInfo("UTC"), 'DeprecatedUtc does not exist and should have been replaced with UTC')
            self.assertIn('America/New_York', all_timezones, 'America/New_York is available')
            self.assertNotEqual(ZoneInfo('America/New_York'), ZoneInfo("UTC"), 'America/New_York exists and should not have been replaced with UTC')

    def test_cannot_set_deprecated_timezone(self):
        # this should be ok
        self.env.user.tz = "America/New_York"
        if "US/Eastern" not in all_timezones:
            with self.assertRaises(ValueError):
                self.env.user.tz = "US/Eastern"

    def test_partner_with_old_tz(self):
        # this test makes sence after ubuntu noble without tzdata-legacy installed
        partner = self.env['res.partner'].create({'name': 'test', 'tz': 'UTC'})
        self.env.cr.execute("""UPDATE res_partner set tz='US/Eastern' WHERE id=%s""", (partner.id,))
        partner.invalidate_recordset()
        self.assertEqual(partner.tz, 'US/Eastern')  # tz was update despite selection not existing, but data was not migrated
        expected_offset = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%z')
        # offest will be -0400 in summer, -0500 in winter
        self.assertEqual(partner.tz_offset, expected_offset)
