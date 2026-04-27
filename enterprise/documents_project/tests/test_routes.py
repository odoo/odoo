import io
import json
import zipfile

from odoo import http

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests.common import HttpCase, RecordCapturer


class TestDocumentsProjectRoutes(HttpCase, TestProjectCommon):

    def test_upload_attachment_to_task_through_activity_with_folder(self):
        """Test the flow of uploading an attachment on a task through an activity with a folder.
        Ensure that only one document is created and linked to the task through the process.
        """
        folder_a = self.env["documents.document"].create({"name": "folder A", "type": "folder"})
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Upload Document with Folder",
                "category": "upload_file",
                "folder_id": folder_a.id,
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
            self.task_1.document_ids.filtered(lambda d: d.type == "binary"),
            document,
            "Only document linked to the activity should be linked to the task",
        )
        activity._action_done(attachment_ids=[response_content["data"]["ir.attachment"][0]["id"]])
        # Ensure the document is not linked to the activity anymore after the action is done
        self.assertFalse(
            document.request_activity_id,
            "Document should not be linked to the activity anymore",
        )

    def test_open_project_documents(self):
        self.authenticate(self.user_portal.login, self.user_portal.login)
        self.document_hello = self.env['documents.document'].create({
            'type': 'binary',
            'name': 'hello.txt',
            'raw': b'Hello\n',
            'folder_id': self.project_pigs.documents_folder_id.id,
            'owner_id': self.user_projectuser.id,
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
            'access_via_link': 'none',
        })

        def project_url_open(path, *args, **kwargs):
            kwargs.setdefault('allow_redirects', False)
            url = (
                f'/my/projects/{self.project_pigs.id}'
                f'{path}'
                f'?access_token={self.project_pigs.access_token}'
            )
            return self.url_open(url, *args, **kwargs)

        # No access
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 303, "must not access an unshared project")

        # Access project, but not documents
        self.project_pigs.privacy_visibility = "portal"
        self.project_pigs._portal_ensure_token()
        self.project_pigs._add_collaborators(self.user_portal.partner_id)
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the template must render nicely")
        self.assertRegex(res.text, r"0\s+folders,\s+0\s+files", "no document should be visible")

        portal_access = self.document_hello.access_ids.filtered(lambda a: a.partner_id == self.user_portal.partner_id)
        self.assertFalse(portal_access)

        # Log access to the document so that is_access_via_link_hidden is irrelevant for this user.
        self.document_hello.action_update_access_rights(access_via_link='view')
        self.url_open(self.document_hello.access_url).raise_for_status()

        # Access project and documents
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the template must render nicely")
        self.assertRegex(res.text, r"0\s+folders,\s+1\s+files", "some documents should be visible")

        portal_access = self.document_hello.access_ids.filtered(lambda a: a.partner_id == self.user_portal.partner_id)
        self.assertEqual(len(portal_access), 1)
        self.assertFalse(portal_access.role)

        # Access project and documents from visited hidden access_via_link
        self.document_hello.action_update_access_rights(is_access_via_link_hidden=True)
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the template must render nicely")
        self.assertRegex(res.text, r"0\s+folders,\s+1\s+files", "some documents should be visible")

        # Lost access is honored
        self.document_hello.action_update_access_rights(access_via_link='none')
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the template must render nicely")
        self.assertRegex(res.text, r"0\s+folders,\s+0\s+files", "no document should be visible")

        # Access from membership
        self.project_pigs.documents_folder_id.action_update_access_rights(
            partners={self.user_portal.partner_id: ('view', False)})
        res = project_url_open('/documents')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the template must render nicely")
        self.assertRegex(res.text, r"0\s+folders,\s+1\s+files", "some documents should be visible")

        # Download zip
        res = project_url_open('/documents/download')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200, "the zip must download nicely")

        with io.BytesIO(res.content) as resfile, zipfile.ZipFile(resfile) as reszip:
            self.assertEqual(sorted(reszip.namelist()), ['hello.txt'])
            self.assertEqual(reszip.read('hello.txt'), b'Hello\n')

        # Upload new document
        with RecordCapturer(self.env['documents.document'], []) as capture:
            res = project_url_open(
                '/documents/upload',
                data={'csrf_token': http.Request.csrf_token(self)},
                files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain'),
            })
            res.raise_for_status()

        new_doc = capture.records.ensure_one()
        folder = self.project_pigs.documents_folder_id
        self.assertEqual(new_doc.name, 'salut.txt')
        self.assertEqual(new_doc.raw, b"Salut !\n")
        self.assertEqual(new_doc.folder_id, folder)
        self.assertEqual(new_doc.access_via_link, folder.access_via_link)
        self.assertEqual(new_doc.access_internal, folder.access_internal)
        self.assertEqual(new_doc.res_model, 'project.project')
        self.assertEqual(new_doc.res_id, self.project_pigs.id)

    def test_upload_to_project_folder_without_sharing_project(self):
        """Test sharing the project's folder without sharing the project itself.
        Ensure that the user can upload documents to the folder without having access to the project.

        Test Case:
        ==========
        1. Create a project
        2. Get shareable link for the project's folder with permission to upload
        3. as portal user, upload a document to the folder using the shareable link
        4. Verify that the document is created and linked to the folder
        """
        self.authenticate(self.user_portal.login, self.user_portal.login)

        folder = self.project_pigs.documents_folder_id
        folder.action_update_access_rights(
            partners={self.user_portal.partner_id: ('edit', False)},
            access_via_link='none'
        )

        with RecordCapturer(self.env['documents.document'], []) as capture:
            res = self.url_open(f'/documents/upload/{folder.access_token}',
                data={'csrf_token': http.Request.csrf_token(self)},
                files={'ufile': ('hello.txt', io.BytesIO(b"Hello"), 'text/plain')},
                allow_redirects=False)
            res.raise_for_status()
        document = capture.records.ensure_one()
        self.assertEqual(document.name, 'hello.txt')
        self.assertEqual(document.mimetype, 'text/plain')
        self.assertEqual(document.folder_id, folder)
