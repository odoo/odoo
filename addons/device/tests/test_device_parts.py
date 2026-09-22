from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from .common import DeviceFixtureMixin


@tagged("post_install", "-at_install")
class TestDeviceParts(TransactionCase, DeviceFixtureMixin):
    """A device that carries others is one registry entry carrying others,
    not a second registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.profile = cls._create_device_profile()

    def test_a_part_belongs_to_the_device_that_carries_it(self):
        box = self._create_device_device(self.profile, identifier="BOX-1")
        scale = self._create_device_device(
            self.profile, identifier="SCALE-1", parent_id=box.id
        )

        self.assertEqual(scale.parent_id, box)
        self.assertEqual(box.child_ids, scale)
        self.assertEqual(box.child_count, 1)

    def test_a_part_goes_with_the_device_it_is_part_of(self):
        box = self._create_device_device(self.profile, identifier="BOX-2")
        scale = self._create_device_device(
            self.profile, identifier="SCALE-2", parent_id=box.id
        )

        box.unlink()

        self.assertFalse(scale.exists())

    def test_a_device_cannot_be_part_of_itself(self):
        box = self._create_device_device(self.profile, identifier="BOX-3")

        with self.assertRaises(ValidationError):
            box.parent_id = box

    def test_a_cycle_of_parts_is_refused(self):
        first = self._create_device_device(self.profile, identifier="BOX-4")
        second = self._create_device_device(
            self.profile, identifier="BOX-5", parent_id=first.id
        )

        with self.assertRaises(ValidationError):
            first.parent_id = second

    def test_a_device_needs_no_profile(self):
        # An IoT box has no device.profile: the profile is a device model, and
        # not every device in the registry has one.
        device = self.env["device.device"].create(
            {"name": "Profileless", "identifier": "NO-PROFILE"}
        )

        self.assertFalse(device.config_id)
        self.assertTrue(device.credential_id)
