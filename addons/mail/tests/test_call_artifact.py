from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged
from odoo.tools.misc import mute_logger

from odoo.addons.mail.tests.common import MailCommon


@tagged("call_artifacts")
class TestMailCallArtifact(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Test Channel",
            "channel_type": "group",
        })
        cls.call = cls.env["discuss.call.history"].create({
            "channel_id": cls.channel.id,
            "start_dt": fields.Datetime.now(),
        })
        cls.artifact = cls.env["mail.call.artifact"].create({
            "discuss_call_history_id": cls.call.id,
            "start_ms": 0,
            "end_ms": 1000,
        })

    # Test Access Rights & Record Rules ----------------------------

    def test_admin_access(self):
        artifact = self.artifact.with_user(self.user_admin)
        self.assertTrue(artifact.read(["start_ms"]), "Admin should be able to read artifact")
        artifact.write({"end_ms": 2000})
        self.assertEqual(artifact.end_ms, 2000, "Admin should be able to modify artifacts")
        new_artifact = self.env["mail.call.artifact"].with_user(self.user_admin).create({
            "discuss_call_history_id": self.call.id,
            "start_ms": 5000,
            "end_ms": 6000,
        })
        self.assertTrue(new_artifact, "Admins should be able to create artifacts")
        new_artifact.unlink()
        self.assertFalse(new_artifact.exists(), "Admins should be able to unlink artifacts")

    def test_user_access_member(self):
        # Membership grants read access to the channel's calls,
        # which in turn grants read access to the call's artifacts
        self.channel._add_members(partners=self.user_employee.partner_id)
        artifact = self.artifact.with_user(self.user_employee)

        self.assertTrue(artifact.read(["start_ms"]), "Channel member should be able to read artifact")
        search_res = self.env["mail.call.artifact"].with_user(self.user_employee).search([("id", "=", self.artifact.id)])
        self.assertEqual(len(search_res), 1, "Channel member should be able to find artifact")
        with self.assertRaises(AccessError, msg="Artifacts are technical records and cannot be modified by standard users."):
            artifact.write({"end_ms": 2000})
        with self.assertRaises(AccessError, msg="Artifacts are technical records and cannot be created manually."):
            self.env["mail.call.artifact"].with_user(self.user_employee).create({
                "discuss_call_history_id": self.call.id,
                "start_ms": 2000,
                "end_ms": 3000,
            })
        with self.assertRaises(AccessError, msg="Artifacts are technical records and cannot be deleted by standard users."):
            artifact.unlink()

    def test_user_access_non_member(self):
        """Verify that a non-member of the channel cannot read the artifact"""
        artifact = self.artifact.with_user(self.user_employee_c2)
        with self.assertRaises(AccessError, msg="Non-members should not have read access to artifacts"):
            artifact.read(["start_ms"])
        search_res = self.env["mail.call.artifact"].with_user(self.user_employee_c2).search([("id", "=", self.artifact.id)])
        self.assertEqual(len(search_res), 0, "Non-member should not find artifact")

    # Test Constraints ---------------------------------------------

    def test_discuss_artifact_overlap(self):
        # 1. No overlap -> OK (Already one artifact there spanning 0-1000 from setUpClass)
        self.env["mail.call.artifact"].create({"discuss_call_history_id": self.call.id, "start_ms": 2000, "end_ms": 3000})

        # 2. Any overlap -> Error
        with self.assertRaises(ValidationError):
            self.env["mail.call.artifact"].create({"discuss_call_history_id": self.call.id, "start_ms": 2500, "end_ms": 3500})

    @mute_logger("odoo.sql_db", "odoo.models")
    def test_artifact_must_have_possessor(self):
        """Ensure that an artifact is linked to a call record"""
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["mail.call.artifact"].create({
                    "start_ms": 0,
                    "end_ms": 1000,
                })

    def test_discuss_call_unlink_cascades_to_attachments(self):
        """Verify that deleting call.history purges artifacts and their attachments"""
        artifact = self.env["mail.call.artifact"].create({
            "discuss_call_history_id": self.call.id,
            "start_ms": 10000,
            "end_ms": 11000,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "recording.wav",
            "res_model": "mail.call.artifact",
            "res_id": artifact.id,
            "raw": b"audio",
        })
        self.assertTrue(attachment.exists())
        self.call.unlink()
        self.assertFalse(self.call.exists())
        self.assertFalse(artifact.exists(), "The call's artifact should be deleted with the call.")
        self.assertFalse(attachment.exists(), "The artifact's attachment should be purged with the call.")
