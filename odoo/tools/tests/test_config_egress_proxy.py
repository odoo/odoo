import contextlib
import io
import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from odoo.libs import guarded_http
from odoo.tools.config import configmanager


class TestEgressProxyOption(unittest.TestCase):
    def setUp(self):
        self.addCleanup(
            guarded_http.configure_egress_proxy, guarded_http.egress_proxy()
        )
        self.rcfile = Path(tempfile.mkdtemp(), "test.conf")
        self.rcfile.write_text("[options]\n", encoding="utf-8")

    def parse(self, *argv):
        cfg = configmanager()
        with contextlib.redirect_stderr(io.StringIO()):
            cfg._parse_config(["-c", str(self.rcfile), *argv])
        return cfg

    def test_the_option_is_the_process_egress_route(self):
        self.parse("--egress-proxy=http://user:pw@127.0.0.1:3128")
        self.assertEqual(guarded_http.egress_proxy(), "http://user:pw@127.0.0.1:3128")
        self.parse()
        self.assertIsNone(guarded_http.egress_proxy())

    def test_a_proxy_that_is_not_an_http_url_is_refused_at_startup(self):
        with self.assertRaises(SystemExit):
            self.parse("--egress-proxy=socks5://127.0.0.1:1080")

    def test_an_environment_proxy_is_named_once_as_ignored(self):
        cfg = self.parse()
        with (
            mock.patch.dict("os.environ", {"HTTPS_PROXY": "http://corp:3128"}),
            self.assertLogs("odoo.tools.config", logging.WARNING) as logs,
        ):
            cfg._warn_ignored_proxy_environment()
            cfg._flush_log_and_warn_entries()
        warnings = [line for line in logs.output if "egress_proxy" in line]
        self.assertEqual(len(warnings), 1)
        self.assertIn("HTTPS_PROXY", warnings[0])
