import io
import json

from odoo import http

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests.common import HttpCase


class TestDocumentsProjectRoutes(HttpCase, TestProjectCommon):

    def test_upload_attachment_to_task_through_activity_with_folder(self):
        """Test the flow of uploading an attachment on a task through an activity with a folder.
        Ensure that only one document is created and linked to the task through the process.
        """
        self.folder_a = self.env["documents.folder"].create(
            {
                "name": "folder A",
            }
        )
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Upload Document with Folder",
                "category": "upload_file",
                "folder_id": self.folder_a.id,
            }
        )
        activity = self.task_1.activity_schedule(
            activity_type_id=activity_type.id,
            user_id=self.env.user.id,
        )

        # Check that the activity is linked to the task
        self.assertEqual(
            activity.id,
            self.task_1.activity_ids.id,
            "Activity should be linked to the task",
        )

        # Check that a temporary document is created and linked to the activity
        document = self.env["documents.document"].search(
            [
                ("request_activity_id", "=", self.task_1.activity_ids.id),
                ("attachment_id", "=", False),
            ]
        )
        self.assertEqual(
            len(document), 1, "Temporary document should be linked on the activity"
        )

        # Upload an attachment through the activity
        self.authenticate("admin", "admin")
        with io.StringIO("Hello world!") as file:
            response = self.opener.post(
                url="%s/mail/attachment/upload" % self.base_url(),
                files={"ufile": file},
                data={
                    "activity_id": activity.id,
                    "thread_id": self.task_1.id,
                    "thread_model": self.task_1._name,
                    "csrf_token": http.Request.csrf_token(self),
                },
            )
            self.assertEqual(response.status_code, 200)
        response_content = json.loads(response.content)

        # Check that only one document is linked to the task
        self.assertEqual(
            self.task_1.document_ids,
            document,
            "Only document linked to the activity should be linked to the task",
        )
        activity._action_done(attachment_ids=[response_content["id"]])
        # Ensure the document is not linked to the activity anymore after the action is done
        self.assertFalse(
            document.request_activity_id,
            "Document should not be linked to the activity anymore",
        )
