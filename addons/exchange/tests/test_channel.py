from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import new_test_user, tagged

from .common import ExchangeCase


@tagged("post_install", "-at_install")
class TestExchangeChannel(ExchangeCase):
    def test_a_channel_reads_its_transport_from_the_endpoint(self):
        self.assertEqual(self.channel.name, self.endpoint.name)
        self.assertEqual(self.channel.environment, "test")
        self.assertEqual(
            self.channel.retry_max_attempts, self.endpoint.retry_max_attempts
        )
        self.assertEqual(self.channel.company_id, self.endpoint.company_id)

    def test_a_company_reaches_one_counterparty_once_per_environment(self):
        duplicate_endpoint = self.endpoint.copy({"code": "demo_duplicate"})
        with self.assertRaises(ValidationError):
            self.env["exchange.channel"].create(
                {
                    "endpoint_id": duplicate_endpoint.id,
                    "protocol": "demo",
                    "counterparty": "authority",
                },
            )

    def test_the_same_counterparty_in_another_environment_is_a_second_channel(self):
        production_endpoint = self.endpoint.copy({"code": "demo_production"})
        production = self.env["exchange.channel"].create(
            {
                "endpoint_id": production_endpoint.id,
                "protocol": "demo",
                "counterparty": "authority",
                "environment": "production",
            },
        )
        self.assertTrue(production.id)

    def test_an_uninstalled_protocol_is_refused(self):
        with self.assertRaises(ValidationError):
            self.channel.protocol = "no_such_protocol"

    def test_an_annulment_window_is_not_negative(self):
        with self.assertRaises(ValidationError):
            self.channel.annul_window_days = -1

    def test_a_send_only_channel_holds_no_inbox(self):
        self.assertFalse(self.channel.is_inbox_enabled)
        with self.assertRaises(UserError):
            self.channel.action_read_inbox()

    def test_reading_an_inbox_stamps_when_it_was_read(self):
        self.channel.is_inbox_enabled = True
        self.channel.action_read_inbox()
        self.assertTrue(self.channel.date_last_inbox)

    def test_counts_separate_open_transmissions_from_settled(self):
        first = self._add_transmission()
        second = self._add_transmission(
            subject=self.env["res.partner"].create({"name": "B"})
        )
        self._send(second, self._accepted("SETTLED"))

        self.channel.invalidate_recordset()
        self.assertEqual(self.channel.count_transmission, 2)
        self.assertEqual(self.channel.count_transmission_open, 1)
        self.assertEqual(first.state, "queued")


@tagged("post_install", "-at_install")
class TestExchangeChannelReaders(ExchangeCase):
    def test_an_internal_user_reads_a_channel_and_only_its_service(self):
        # the channel binds its service's read permission (plan section 3.1):
        # an internal user reads a channel's endpoint and no other service
        user = new_test_user(
            self.env, login="exchange_reader", groups="base.group_user"
        )
        other = self.endpoint.copy({"code": "demo_no_channel"})
        channel = self.channel.with_user(user)
        self.assertEqual(channel.name, self.endpoint.name)
        self.assertTrue(self.endpoint.with_user(user).has_access("read"))
        self.assertFalse(other.with_user(user).has_access("read"))
