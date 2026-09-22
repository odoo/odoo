from unittest.mock import patch

from odoo.tests.common import HttpCase, TransactionCase


class DeviceFixtureMixin:
    @classmethod
    def _create_device_profile(cls, **overrides):
        vals = {"name": "Test Config"}
        vals.update(overrides)
        return cls.env["device.profile"].create(vals)

    @classmethod
    def _create_device_device(cls, config=None, **overrides):
        vals = {
            "name": "Test Device",
            "identifier": "TEST-DEVICE",
            "config_id": (config or cls._create_device_profile()).id,
            "comm_protocol": "http",
            "endpoint": "10.0.0.1",
        }
        vals.update(overrides)
        return cls.env["device.device"].create(vals)

    @classmethod
    def _device_token(cls, device):
        return device.credential_id.sudo().credential_value


class InlineStateRetryMixin:
    def setUp(self):
        super().setUp()

        def _inline_retry(model, func, what, max_attempts=3):
            return func(model.env)

        patcher = patch.object(
            type(self.env["device.device"]),
            "_run_with_state_retry",
            _inline_retry,
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class DeviceTransactionCase(DeviceFixtureMixin, TransactionCase):
    pass


class DeviceHttpCase(DeviceFixtureMixin, HttpCase):
    pass
