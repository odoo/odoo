import datetime
import logging
import pytz
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools._monkeypatches_pytz import _tz_mapping

_logger = logging.getLogger(__name__)


class TestTZ(TransactionCase):

    def test_tz_legacy(self):
        d = datetime.datetime(1969, 7, 16)
        # See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        def assertTZEqual(tz1, tz2):
            self.assertEqual(tz1.localize(d).strftime('%z'), tz2.localize(d).strftime('%z'))

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
                    target_tz = pytz.timezone(target)
                except pytz.UnknownTimeZoneError:
                    _logger.info("Skipping test for %s -> %s, target does not exist", source, target)
                    continue
                assertTZEqual(pytz.timezone(source), target_tz)

    def test_dont_adapt_available_tz(self):
        with patch.dict(_tz_mapping, {
            'DeprecatedUtc': 'UTC',
            'America/New_York': 'UTC',
        }):
            self.assertNotIn('DeprecatedUtc', pytz.all_timezones_set, 'DeprecatedUtc is not available')
            self.assertEqual(pytz.timezone('DeprecatedUtc'), pytz.timezone('UTC'), 'DeprecatedUtc does not exist and should have been replaced with UTC')
            self.assertIn('America/New_York', pytz.all_timezones_set, 'America/New_York is available')
            self.assertNotEqual(pytz.timezone('America/New_York'), pytz.timezone('UTC'), 'America/New_York exists and should not have been replaced with UTC')

    def test_cannot_set_deprecated_timezone(self):
        # this should be ok
        self.env.user.tz = "America/New_York"
        if "US/Eastern" not in pytz.all_timezones:
            with self.assertRaises(ValueError):
                self.env.user.tz = "US/Eastern"

    def test_partner_with_old_tz(self):
        # this test makes sence after ubuntu noble without tzdata-legacy installed
        partner = self.env['res.partner'].create({'name': 'test', 'tz': 'UTC'})
        self.env.cr.execute("""UPDATE res_partner set tz='US/Eastern' WHERE id=%s""", (partner.id,))
        partner.invalidate_recordset()
        self.assertEqual(partner.tz, 'US/Eastern')  # tz was update despite selection not existing, but data was not migrated
        self.assertEqual(partner.tz_offset, '-0400', "We don't expect pytz.timezone to fail if the timezone diseapeared when chaging os version")
