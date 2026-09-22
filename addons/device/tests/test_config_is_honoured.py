from datetime import timedelta

from lxml import etree

from odoo import fields

from odoo.addons.device.tests.common import (
    DeviceTransactionCase,
    InlineStateRetryMixin,
)


class TestDisconnectAlert(InlineStateRetryMixin, DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Alerting Config")
        cls.silent = cls._create_device_profile(
            name="Silent Config", alert_on_disconnect=False
        )

    def _stale_device(self, config, identifier):
        device = self._create_device_device(
            config=config, identifier=identifier, comm_protocol="http"
        )
        device.sudo().write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now() - timedelta(days=30),
            }
        )
        return device

    def _messages(self, device):
        return self.env["mail.message"].search(
            [("model", "=", "device.device"), ("res_id", "=", device.id)]
        )

    def test_a_device_going_quiet_raises_the_alert_it_promises(self):
        device = self._stale_device(self.config, "ALERT-ON")
        before = len(self._messages(device))

        self.env["device.device"]._cron_check_health()

        device.invalidate_recordset()
        self.assertEqual(device.connection_state, "disconnected")
        self.assertGreater(
            len(self._messages(device)),
            before,
            "the profile asks for a disconnect alert and nothing was posted",
        )

    def test_no_alert_when_the_profile_does_not_ask_for_one(self):
        device = self._stale_device(self.silent, "ALERT-OFF")
        before = len(self._messages(device))
        self.env["device.device"]._cron_check_health()
        device.invalidate_recordset()
        self.assertEqual(device.connection_state, "disconnected")
        self.assertEqual(len(self._messages(device)), before)

    def test_a_healthy_device_raises_nothing(self):
        device = self._create_device_device(
            config=self.config, identifier="ALERT-HEALTHY"
        )
        device.sudo().write(
            {
                "connection_state": "connected",
                "date_last_data_received": fields.Datetime.now(),
            }
        )
        before = len(self._messages(device))
        self.env["device.device"]._cron_check_health()
        self.assertEqual(len(self._messages(device)), before)


class TestPerProfileRetention(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "device.data_retention_days", "90"
        )
        cls.short = cls._create_device_profile(
            name="Short Retention", data_retention_days=7
        )
        cls.default = cls._create_device_profile(name="Default Retention")

    def _log_at(self, device, days_ago):
        return self.env["device.data.log"].create(
            {
                "device_id": device.id,
                "timestamp": fields.Datetime.now() - timedelta(days=days_ago),
                "data_type": "json",
                "value_json": {"t": 1},
            }
        )

    def test_a_profile_keeps_its_own_retention_period(self):
        device = self._create_device_device(
            config=self.short, identifier="RETAIN-SHORT"
        )
        old = self._log_at(device, 30)
        recent = self._log_at(device, 1)

        self.env["device.data.log"]._gc_old_data_logs()

        self.assertFalse(
            old.exists(),
            "a profile set to 7 days kept a 30-day-old point: the per-profile "
            "retention setting is being ignored again",
        )
        self.assertTrue(recent.exists())

    def test_other_profiles_still_use_the_global_period(self):
        device = self._create_device_device(
            config=self.default, identifier="RETAIN-GLOBAL"
        )
        within = self._log_at(device, 30)
        beyond = self._log_at(device, 120)

        self.env["device.data.log"]._gc_old_data_logs()

        self.assertTrue(
            within.exists(),
            "the global 90-day period was not applied to a default profile",
        )
        self.assertFalse(beyond.exists())


class TestGlobalRetentionFallback(DeviceTransactionCase):
    # With no device.data_retention_days configured the module falls back to its
    # own default. That default used to be read from a second parameter,
    # device.data_retention_days_default, which 19.0.1.10.0 deleted -- so the
    # read was dead and the literal beside it was the only reachable value.

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().search(
            [
                (
                    "key",
                    "in",
                    (
                        "device.data_retention_days",
                        "device.data_retention_days_default",
                    ),
                )
            ],
        ).unlink()
        # data_retention_days defaults to 90 on the profile, and a profile with
        # its own period is swept by the per-profile branch and excluded from
        # the global one. 0 is what puts this device on the global path.
        cls.profile = cls._create_device_profile(
            name="Fallback Retention", data_retention_days=0
        )

    def _log_at(self, device, days_ago):
        return self.env["device.data.log"].create(
            {
                "device_id": device.id,
                "timestamp": fields.Datetime.now() - timedelta(days=days_ago),
                "data_type": "json",
                "value_json": {"t": 1},
            }
        )

    def test_the_module_default_is_used_when_nothing_is_configured(self):
        device = self._create_device_device(
            config=self.profile, identifier="RETAIN-FALLBACK"
        )
        within = self._log_at(device, 30)
        beyond = self._log_at(device, 120)

        self.env["device.data.log"]._gc_old_data_logs()

        self.assertTrue(
            within.exists(),
            "the module default retention was not applied with no parameter set",
        )
        self.assertFalse(beyond.exists())

    def test_the_default_is_named_rather_than_inlined(self):
        self.assertEqual(
            self.env["device.data.log"]._DEFAULT_RETENTION_DAYS,
            90,
            "the collapse of the dead parameter read must keep the same value",
        )


class TestDisconnectTimeoutTiers(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "device.disconnect_timeout_default", "300"
        )

    def _device(self, identifier, *, profile_timeout=0, category_timeout=None):
        config = self._create_device_profile(
            name=f"Timeout {identifier}", disconnect_timeout=profile_timeout
        )
        values = {}
        if category_timeout is not None:
            values["device_category_id"] = (
                self.env["device.kind"]
                .create(
                    {
                        "name": f"Cat {identifier}",
                        "code": f"cat_{identifier.lower()}",
                        "disconnect_timeout_seconds": category_timeout,
                    }
                )
                .id
            )
        return self._create_device_device(
            config=config, identifier=identifier, **values
        )

    def test_a_profile_with_no_timeout_inherits_the_parameter(self):
        device = self._device("TIER-INHERIT")
        self.assertEqual(device._disconnect_timeout()[device.id], 300)

    def test_a_profile_timeout_overrides_the_parameter(self):
        device = self._device("TIER-PROFILE", profile_timeout=1800)
        self.assertEqual(
            device._disconnect_timeout()[device.id],
            1800,
            "device.profile.disconnect_timeout is set and still not read",
        )

    def test_a_category_timeout_overrides_the_profile(self):
        device = self._device(
            "TIER-CATEGORY", profile_timeout=1800, category_timeout=60
        )
        self.assertEqual(device._disconnect_timeout()[device.id], 60)


class TestProfileFormShowsLiveSettings(DeviceTransactionCase):
    _ALWAYS_VISIBLE = ("endpoint_url", "disconnect_timeout")

    def _form_arch(self):
        return etree.fromstring(
            self.env["device.profile"].get_view(
                view_id=self.env.ref("device.view_device_profile_form").id
            )["arch"]
        )

    def test_the_shared_settings_are_not_hidden_behind_a_protocol(self):
        arch = self._form_arch()
        for name in self._ALWAYS_VISIBLE:
            with self.subTest(field=name):
                nodes = arch.xpath(f"//field[@name='{name}']")
                self.assertTrue(nodes, f"{name} is on no group of the profile form")
                for node in nodes:
                    ancestors = [node, *node.iterancestors()]
                    hidden = [
                        element.get("invisible")
                        for element in ancestors
                        if element.get("invisible")
                    ]
                    self.assertFalse(
                        hidden,
                        f"{name} is read by the transports but hidden by {hidden}",
                    )
