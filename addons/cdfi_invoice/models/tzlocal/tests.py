import mock
import os
import pytz
import sys
import tzlocal.unix
import unittest

from datetime import datetime


class TzLocalTests(unittest.TestCase):
    def setUp(self):
        if 'TZ' in os.environ:
            del os.environ['TZ']

        self.path = os.path.split(__file__)[0]

    def test_env(self):
        tz_harare = tzlocal.unix._tz_from_env(':Africa/Harare')
        self.assertEqual(tz_harare.zone, 'Africa/Harare')

        # Some Unices allow this as well, so we must allow it:
        tz_harare = tzlocal.unix._tz_from_env('Africa/Harare')
        self.assertEqual(tz_harare.zone, 'Africa/Harare')

        tz_local = tzlocal.unix._tz_from_env(':' + os.path.join(self.path, 'test_data', 'Harare'))
        self.assertEqual(tz_local.zone, 'local')
        # Make sure the local timezone is the same as the Harare one above.
        # We test this with a past date, so that we don't run into future changes
        # of the Harare timezone.
        dt = datetime(2012, 1, 1, 5)
        self.assertEqual(tz_harare.localize(dt), tz_local.localize(dt))

        # Non-zoneinfo timezones are not supported in the TZ environment.
        self.assertRaises(pytz.UnknownTimeZoneError, tzlocal.unix._tz_from_env, 'GMT+03:00')

        # Test the _try function
        os.environ['TZ'] = 'Africa/Harare'
        tz_harare = tzlocal.unix._try_tz_from_env()
        self.assertEqual(tz_harare.zone, 'Africa/Harare')
        # With a zone that doesn't exist
        os.environ['TZ'] = 'Just Nonsense'
        tz_harare = tzlocal.unix._try_tz_from_env()
        self.assertIsNone(tz_harare)


    def test_timezone(self):
        # Most versions of Ubuntu

        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'timezone'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_zone_setting(self):
        # A ZONE setting in /etc/sysconfig/clock, f ex CentOS

        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'zone_setting'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_timezone_setting(self):
        # A ZONE setting in /etc/conf.d/clock, f ex Gentoo

        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'timezone_setting'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_symlink_localtime(self):
        # A ZONE setting in the target path of a symbolic linked localtime, f ex systemd distributions

        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'symlink_localtime'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_vardbzoneinfo_setting(self):
        # A ZONE setting in /etc/conf.d/clock, f ex Gentoo

        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'vardbzoneinfo'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_only_localtime(self):
        tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data', 'localtime'))
        self.assertEqual(tz.zone, 'local')
        dt = datetime(2012, 1, 1, 5)
        self.assertEqual(pytz.timezone('Africa/Harare').localize(dt), tz.localize(dt))

    def test_get_reload(self):
        os.environ['TZ'] = 'Africa/Harare'
        tz_harare = tzlocal.unix.get_localzone()
        self.assertEqual(tz_harare.zone, 'Africa/Harare')
        # Changing the TZ makes no difference, because it's cached
        os.environ['TZ'] = 'Africa/Johannesburg'
        tz_harare = tzlocal.unix.get_localzone()
        self.assertEqual(tz_harare.zone, 'Africa/Harare')
        # So we reload it
        tz_harare = tzlocal.unix.reload_localzone()
        self.assertEqual(tz_harare.zone, 'Africa/Johannesburg')

    def test_fail(self):
        with self.assertRaises(pytz.exceptions.UnknownTimeZoneError):
            tz = tzlocal.unix._get_localzone(_root=os.path.join(self.path, 'test_data'))

if sys.platform == 'win32':

    import tzlocal.win32
    class TzWin32Tests(unittest.TestCase):

        def test_win32(self):
            tzlocal.win32.get_localzone()

else:

    class TzWin32Tests(unittest.TestCase):

        def test_win32_on_unix(self):
            # Yes, winreg is all mocked out, but this test means we at least
            # catch syntax errors, etc.
            winreg = mock.MagicMock()
            winreg.OpenKey = mock.MagicMock()
            winreg.OpenKey.close = mock.MagicMock()
            winreg.QueryInfoKey = mock.MagicMock(return_value=(1, 1))
            winreg.EnumValue = mock.MagicMock(
                return_value=('TimeZoneKeyName','Belarus Standard Time'))
            winreg.EnumKey = mock.Mock(return_value='Bahia Standard Time')
            sys.modules['winreg'] = winreg
            import tzlocal.win32
            tz = tzlocal.win32.get_localzone()
            self.assertEqual(tz.zone, 'Europe/Minsk')

            tzlocal.win32.valuestodict = mock.Mock(return_value={
                'StandardName': 'Mocked Standard Time',
                'Std': 'Mocked Standard Time',
            })
            tz = tzlocal.win32.reload_localzone()
            self.assertEqual(tz.zone, 'America/Bahia')

if __name__ == '__main__':
    unittest.main()
