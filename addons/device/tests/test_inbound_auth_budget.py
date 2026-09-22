from odoo.exceptions import ValidationError

from .common import DeviceTransactionCase

_PAST_THE_DECRYPT_CAP = 130


class TestInboundAuthBudget(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Auth Budget Config")
        cls.device = cls._create_device_device(
            config=cls.config, identifier="AUTH-BUDGET-1"
        )
        cls.token = cls.device.credential_id.sudo().credential_value

    def test_is_valid_token_survives_past_the_decrypt_cap(self):
        public = self.env.ref("base.public_user")
        device = self.device.with_user(public).sudo()
        for attempt in range(_PAST_THE_DECRYPT_CAP):
            try:
                self.assertTrue(
                    device.is_valid_token(self.token),
                    f"token stopped verifying at attempt {attempt + 1}",
                )
            except ValidationError as error:
                self.fail(
                    f"authentication spent the decryption budget at attempt "
                    f"{attempt + 1}: {error}"
                )

    def test_find_by_token_survives_past_the_decrypt_cap(self):
        public = self.env.ref("base.public_user")
        model = self.env["device.device"].with_user(public).sudo()
        for attempt in range(_PAST_THE_DECRYPT_CAP):
            try:
                found = model._find_by_inbound_token(self.token)
            except ValidationError as error:
                self.fail(
                    f"reverse lookup spent the decryption budget at attempt "
                    f"{attempt + 1}: {error}"
                )
            self.assertIn(self.device, found)

    def test_authenticate_request_survives_past_the_decrypt_cap(self):
        public = self.env.ref("base.public_user")
        device = self.device.with_user(public).sudo()
        headers = {"Authorization": f"Bearer {self.token}"}
        for attempt in range(_PAST_THE_DECRYPT_CAP):
            try:
                self.assertTrue(
                    device.authenticate_request(headers=headers, body=b""),
                    f"authenticate_request failed at attempt {attempt + 1}",
                )
            except ValidationError as error:
                self.fail(
                    f"authenticate_request spent the decryption budget at "
                    f"attempt {attempt + 1}: {error}"
                )

    def test_wrong_token_is_rejected(self):
        self.assertFalse(self.device.is_valid_token("not-the-token"))
        self.assertFalse(self.device.is_valid_token(""))
        self.assertFalse(self.device.is_valid_token(None))
        self.assertFalse(
            self.env["device.device"]._find_by_inbound_token("not-the-token")
        )
        self.assertFalse(
            self.device.authenticate_request(
                headers={"Authorization": "Bearer not-the-token"}, body=b""
            )
        )

    def test_x_device_token_header_is_accepted(self):
        self.assertTrue(
            self.device.authenticate_request(
                headers={"X-Device-Token": self.token}, body=b""
            )
        )

    def test_a_device_without_a_secret_authenticates_nothing(self):
        device = self._create_device_device(
            config=self.config, identifier="AUTH-BUDGET-NO-SECRET"
        )
        device.sudo().credential_id = False
        device.invalidate_recordset()
        self.assertFalse(device.sudo().credential_fingerprint)
        self.assertFalse(device.is_valid_token(""))
        self.assertFalse(device.is_valid_token("anything"))
