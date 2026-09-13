from odoo.libs.netguard import DestinationRefused
from odoo.tests.common import TransactionCase


class TestWebhookSsrfGuard(TransactionCase):
    def assertRefused(self, url):
        with self.assertRaises(DestinationRefused):
            self.env["ir.egress"].check_url(url)

    def test_non_global_literals_are_blocked(self):
        for host in (
            "127.0.0.1",
            "169.254.169.254",
            "10.0.0.1",
            "192.168.1.1",
            "100.64.0.1",
            "0.0.0.0",
            "255.255.255.255",
            "224.0.0.1",
            "239.255.255.250",
            "[::1]",
            "[::ffff:127.0.0.1]",
            "[::ffff:169.254.169.254]",
            "[64:ff9b::a9fe:a9fe]",
            "[2002:a9fe:a9fe::]",
            "[fd00::1]",
            "[fe80::1]",
            "[ff02::1]",
            "[ff00::1]",
            "[5f00::1]",
            "[2001:db8::1]",
        ):
            with self.subTest(host=host):
                self.assertRefused(f"http://{host}/hook")

    def test_public_literals_are_allowed(self):
        for host in (
            "8.8.8.8",
            "1.1.1.1",
            "93.184.216.34",
            "[2606:4700::1111]",
            "[64:ff9b::808:808]",
        ):
            with self.subTest(host=host):
                self.env["ir.egress"].check_url(f"https://{host}/hook")

    def test_non_http_schemes_and_malformed_urls_are_blocked(self):
        for url in (
            "file:///etc/passwd",
            "gopher://x/",
            "ftp://example.com/",
            "http://",
        ):
            with self.subTest(url=url):
                self.assertRefused(url)

    def test_an_operator_network_is_allowed_and_nothing_else(self):
        self.env["ir.config_parameter"].set_param(
            "base.egress_allowed_networks", "10.20.0.0/16, fd12::/16"
        )
        self.env["ir.egress"].check_url("http://10.20.1.2/hook")
        self.env["ir.egress"].check_url("http://[fd12::5]/hook")
        self.assertRefused("http://10.21.1.2/hook")
        self.assertRefused("http://127.0.0.1/hook")

    def test_a_malformed_operator_network_allows_nothing_extra(self):
        self.env["ir.config_parameter"].set_param(
            "base.egress_allowed_networks", "10.20.0.0/16 not-a-network"
        )
        with self.assertLogs("odoo.addons.base.models.ir_egress", "ERROR"):
            self.assertRefused("http://10.20.1.2/hook")
