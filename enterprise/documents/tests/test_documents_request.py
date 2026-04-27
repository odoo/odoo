import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
import io
import json

from odoo import Command, fields, http
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form, RecordCapturer, HttpCase
from odoo.tools import mute_logger


class TestDocumentRequest(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_partner_1 = cls.env['res.partner'].create({
             'name': 'Test Partner 1',
             'email': 'test1@example.com',
        })
        cls.doc_partner_2 = cls.env['res.partner'].create({
             'name': 'Test Partner 2',
             'email': 'test2@example.com',
        })
        cls.doc_user = cls.env['res.users'].create({
             'name': 'Test Partner',
             'login': 'test_partner',
             'partner_id': cls.doc_partner_1.id,
        })
        cls.folder_a = cls.env['documents.document'].create({
            'name': 'folder A',
            'type': 'folder',
        })
        cls.activity_type = cls.env['mail.activity.type'].create({
            'name': 'request_document',
            'category': 'upload_file',
            'folder_id': cls.folder_a.id,
        })
        cls.user_employee.write({
            'groups_id': [Command.link(cls.env.ref('documents.group_documents_user').id)]
        })
        cls.folder_a.action_update_access_rights('none', partners={
            cls.user_employee.partner_id.id: ('edit', False),
        })

    @freeze_time('2022-07-24 08:00:00')
    def test_request_document_from_partner_with_user(self):
        with self.mock_mail_gateway(), self.with_user(self.user_employee.login):
            wizard = self.env['documents.request_wizard'].create({
                'name': 'Wizard Request',
                'requestee_id': self.doc_partner_1.id,
                'activity_type_id': self.activity_type.id,
                'folder_id': self.folder_a.id,
                'activity_date_deadline_range_type': 'days',
                'activity_date_deadline_range': 3,
            })
            document = wizard.request_document()

        self.assertEqual(document.requestee_partner_id, self.doc_partner_1)
        self.assertEqual(document.request_activity_id.user_id, self.doc_user, "Activity assigned to the requestee")
        self.assertEqual(document.owner_id, self.user_employee, "Owner of the document is the requester")
        self.assertSentEmail('"Ernest Employee" <e.e@example.com>', self.doc_partner_1, subject='Document Request : Wizard Request')
        self.assertEqual(document.access_via_link, 'none')
        self.assertEqual(len(document.access_ids), 2)
        access_by_partner = {a.partner_id: a for a in document.access_ids}
        access_doc_partner_1 = access_by_partner[self.doc_partner_1]
        self.assertEqual(access_doc_partner_1.role, 'edit')
        self.assertEqual(access_doc_partner_1.expiration_date,
                         datetime.combine(fields.Date.today() + relativedelta(days=3), datetime.max.time()))
        access_doc_employee = access_by_partner[self.partner_employee]
        self.assertEqual(access_doc_employee.role, 'edit')
        self.assertFalse(access_doc_employee.expiration_date)

        # Updating the activity deadline, update the access expiration
        with self.with_user(self.user_employee.login):
            document.request_activity_id.date_deadline = fields.Date.today() + relativedelta(days=5)
        new_expiration_date = datetime.combine(fields.Date.today() + relativedelta(days=5), datetime.max.time())
        self.assertEqual(access_doc_partner_1.expiration_date, new_expiration_date)
        self.assertFalse(access_doc_employee.expiration_date)

        # Simulating upload document
        self.assertTrue(document.request_activity_id)
        with self.with_user(self.user_employee.login):
            document.write({
                'name': 'requested_file.txt',
                'datas': base64.b64encode(b'Test'),
                'mimetype': 'text/plain',
            })
        self.assertFalse(document.request_activity_id)
        self.assertFalse(document.requestee_partner_id)
        self.assertEqual(document.access_via_link, 'none')
        self.assertEqual(access_doc_employee.role, 'edit')
        self.assertEqual(access_doc_partner_1.role, 'edit')
        self.assertEqual(access_doc_partner_1.expiration_date, new_expiration_date)

    def test_request_document_from_partner_without_user(self):
        with self.mock_mail_gateway(), self.with_user(self.user_employee.login):
            wizard = self.env['documents.request_wizard'].create({
                'name': 'Wizard Request 2',
                'requestee_id': self.doc_partner_2.id,
                'activity_type_id': self.activity_type.id,
                'folder_id': self.folder_a.id,
                'activity_date_deadline_range_type': 'days',
                'activity_date_deadline_range': 3,
            })
            document = wizard.request_document()

        self.assertEqual(document.requestee_partner_id, self.doc_partner_2)
        self.assertEqual(document.request_activity_id.user_id, self.user_employee, "Activity assigned to the requester because the requestee has no user")
        self.assertEqual(document.owner_id, self.user_employee, "Owner of the document is the requester")
        self.assertSentEmail('"Ernest Employee" <e.e@example.com>', self.doc_partner_2, subject='Document Request : Wizard Request 2')

        self.assertEqual(len(document.access_ids), 1)
        self.assertEqual(document.access_via_link, 'edit')
        access_by_partner = {a.partner_id: a for a in document.access_ids}
        access_doc_employee = access_by_partner[self.partner_employee]
        self.assertEqual(access_doc_employee.role, 'edit')
        self.assertFalse(access_doc_employee.expiration_date)

        # As the requestee has no user, updating the activity deadline should not change any access expiration
        with self.with_user(self.user_employee.login):
            document.request_activity_id.date_deadline = fields.Date.today() + relativedelta(days=1)
        self.assertEqual(len(document.access_ids), 1)
        self.assertFalse(access_doc_employee.expiration_date)

        # Simulating upload document
        self.assertTrue(document.request_activity_id)
        with self.with_user(self.user_employee.login):
            document.write({
                'name': 'requested_file.txt',
                'datas': base64.b64encode(b'Test'),
                'mimetype': 'text/plain',
            })
        self.assertFalse(document.request_activity_id)
        self.assertFalse(document.requestee_partner_id)
        self.assertEqual(document.access_via_link, 'view')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_send_message_with_attachment_on_doc_request(self):
        wizard = self.env['documents.request_wizard'].create({
            'name': 'Wizard Request 3',
            'requestee_id': self.doc_partner_2.id,
            'activity_type_id': self.activity_type.id,
            'folder_id': self.folder_a.id,
        })
        with self.mock_mail_gateway():
            document = wizard.request_document()
        self.assertFalse(document.attachment_id)

        form = Form(self.env['mail.compose.message'].with_context({
            'default_partner_ids': self.doc_partner_1.ids,
            'default_model': document._name,
            'default_res_ids': document.ids,
        }))
        form.body = '<p>Hello</p>'
        form.subject = 'Example of document required'
        # Simulate file upload on the composed message
        form.attachment_ids = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'res_model': 'mail.compose.message',
            'res_id': form._record.id,
        })
        saved_form = form.save()
        with self.mock_mail_gateway(), RecordCapturer(self.env['mail.message'], []) as capture:
            saved_form._action_send_mail()
            message = capture.records

        self.assertEqual(len(message), 1)
        self.assertFalse(document.attachment_id, 'The document remains a request')
        self.assertEqual(message.body, '<p>Hello</p>')
        self.assertEqual(message.partner_ids, self.doc_partner_1)
        self.assertEqual(message.subject, 'Example of document required')

    def test_request_document_upload_through_activity_popover(self):
        wizard = self.env['documents.request_wizard'].create({
            'name': 'Wizard Request',
            'requestee_id': self.doc_partner_1.id,
            'activity_type_id': self.activity_type.id,
            'folder_id': self.folder_a.id,
        })
        with self.mock_mail_gateway():
            document = wizard.request_document()

        self.assertEqual(document.request_activity_id.user_id, self.doc_user, "Activity assigned to the requestee")
        self.assertEqual(document.owner_id, self.env.user, "Owner of the document is the requester")
        document.action_update_access_rights(partners={self.user_admin.partner_id: ('edit', False)})

        self.authenticate("admin", "admin")
        with io.StringIO("Hello world!") as file:
            response = self.opener.post(
                url=f"{self.base_url()}/mail/attachment/upload",
                files={"ufile": file},
                data={
                    "activity_id": document.activity_ids.id,
                    "thread_id": document.id,
                    "thread_model": "documents.document",
                    "csrf_token": http.Request.csrf_token(self),
                },
            )
        self.assertEqual(response.status_code, 200)
        response_content = response.json()
        data_attachment = response_content.get('data', {}).get('ir.attachment', {})
        self.assertTrue(data_attachment)
        self.assertEqual(len(data_attachment), 1)
        data_attachment_id = data_attachment[0].get('id')
        self.assertTrue(data_attachment_id, "We should have the id of the attachment upload inside the response.")
        document.activity_ids.action_feedback(attachment_ids=[data_attachment_id])
        self.assertEqual(document.attachment_id.id, data_attachment_id,
                         "Attachment should be linked to document only once.")
