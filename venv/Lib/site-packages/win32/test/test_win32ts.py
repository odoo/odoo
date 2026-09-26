# Tests for win32ts module

import unittest

import win32ts


class Win32TsTestCase(unittest.TestCase):
    def test_is_remote_session(self):
        ret = win32ts.WTSQuerySessionInformation(
            win32ts.WTS_CURRENT_SERVER_HANDLE,
            win32ts.WTS_CURRENT_SESSION,
            win32ts.WTSIsRemoteSession,
        )
        self.assertIsInstance(ret, bool)


if __name__ == "__main__":
    unittest.main()
