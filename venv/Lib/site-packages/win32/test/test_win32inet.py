import unittest

import winerror
from pywin32_testutil import TestSkipped, testmain
from win32inet import (
    FtpCommand,
    InternetCanonicalizeUrl,
    InternetConnect,
    InternetGetCookie,
    InternetGetLastResponseInfo,
    InternetOpen,
    InternetOpenUrl,
    InternetReadFile,
    InternetSetCookie,
    error,
)
from win32inetcon import (
    FTP_TRANSFER_TYPE_ASCII,
    INTERNET_FLAG_EXISTING_CONNECT,
    INTERNET_INVALID_PORT_NUMBER,
    INTERNET_OPEN_TYPE_DIRECT,
    INTERNET_SERVICE_FTP,
)


class CookieTests(unittest.TestCase):
    def testCookies(self):
        data = "TestData=Test"
        InternetSetCookie("https://www.python.org", None, data)
        got = InternetGetCookie("https://www.python.org", None)
        # handle that there might already be cookies for the domain.
        bits = (x.strip() for x in got.split(";"))
        self.assertTrue(data in bits)

    def testCookiesEmpty(self):
        try:
            InternetGetCookie("https://site-with-no-cookie.python.org", None)
            self.fail("expected win32 exception")
        except error as exc:
            self.assertEqual(exc.winerror, winerror.ERROR_NO_MORE_ITEMS)


class UrlTests(unittest.TestCase):
    def testSimpleCanonicalize(self):
        ret = InternetCanonicalizeUrl("foo bar")
        self.assertEqual(ret, "foo%20bar")

    def testLongCanonicalize(self):
        # a 4k URL causes the underlying API to request a bigger buffer"
        big = "x" * 2048
        ret = InternetCanonicalizeUrl(big + " " + big)
        self.assertEqual(ret, big + "%20" + big)


class TestNetwork(unittest.TestCase):
    def setUp(self):
        self.hi = InternetOpen("test", INTERNET_OPEN_TYPE_DIRECT, None, None, 0)

    def tearDown(self):
        self.hi.Close()

    def testPythonDotOrg(self):
        hdl = InternetOpenUrl(
            self.hi, "https://www.python.org", None, INTERNET_FLAG_EXISTING_CONNECT
        )
        chunks = []
        while 1:
            chunk = InternetReadFile(hdl, 1024)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        # This must appear somewhere on the main page!
        self.assertGreater(data.find(b"Python"), 0, repr(data))

    def testFtpCommand(self):
        # ftp.python.org doesn't exist.  ftp.gnu.org is what Python's urllib
        # test code uses.
        # (As of 2020 it doesn't! Unsurprisingly, it's difficult to find a good
        # test server. This test sometimes works, but often doesn't - so handle
        # failure here as a "skip")
        try:
            hcon = InternetConnect(
                self.hi,
                "ftp.gnu.org",
                INTERNET_INVALID_PORT_NUMBER,
                None,
                None,  # username/password
                INTERNET_SERVICE_FTP,
                0,
                0,
            )
            try:
                hftp = FtpCommand(hcon, True, FTP_TRANSFER_TYPE_ASCII, "NLST", 0)
                try:
                    print("Connected - response info is", InternetGetLastResponseInfo())
                    got = InternetReadFile(hftp, 2048)
                    print("Read", len(got), "bytes")
                finally:
                    hftp.Close()
            finally:
                hcon.Close()
        except error as e:
            raise TestSkipped(e)


if __name__ == "__main__":
    testmain()
