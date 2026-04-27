# -*- coding: utf-8 -*-

import base64
import io

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.tools.pdf import OdooPdfFileWriter
from odoo.addons.sign.tests.sign_request_common import SignRequestCommon

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


@tagged('post_install', '-at_install')
class TestCaseDocumentsBridgeSign(SignRequestCommon):
    """

    """
    def setUp(self):
        super(TestCaseDocumentsBridgeSign, self).setUp()

        with file_open('sign/static/demo/sample_contract.pdf', "rb") as f:
            pdf_content = f.read()

        self.folder_a = self.env['documents.document'].create({
            'name': 'folder A',
            'type': 'folder',
        })
        self.folder_a_a = self.env['documents.document'].create({
            'name': 'folder A - A',
            'type': 'folder',
            'folder_id': self.folder_a.id,
        })
        self.documents = self.env['documents.document'].create([{
            'datas': base64.encodebytes(pdf_content),
            'name': f'file_{idx}.pdf',
            'folder_id': self.folder_a_a.id,
        } for idx in range(2)])
        self.document_pdf_0 = self.documents[0]

    def _run_wkhtmltopdf(self, *args, **kwargs):
        return file_open('base/tests/minimal.pdf', 'rb').read()

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (sign).
    
        """
        self.assertEqual(self.document_pdf_0.res_model, 'documents.document', "failed at default res model")
        self.documents.document_sign_create_sign_template_x('sign.template.new', self.folder_a.id)

        with self.assertRaises(UserError, msg="Can only be executed on one record."):
            self.documents.document_sign_create_sign_template_x('sign.template.direct', self.folder_a.id)
    
        self.assertEqual(self.document_pdf_0.res_model, 'sign.template',
                         "failed at workflow_bridge_dms_sign new res_model")
        template = self.env['sign.template'].search([('id', '=', self.document_pdf_0.res_id)])
        self.assertTrue(template.exists(), 'failed at workflow_bridge_dms_account template')
        self.assertEqual(self.document_pdf_0.res_id, template.id, "failed at workflow_bridge_dms_account res_id")

    def test_sign_action(self):
        """ Test sign a document from Document app using the workflow rule. """
        self.document_pdf_0.document_sign_create_sign_template_x('sign.template.direct', self.folder_a.id)
        self.assertEqual(self.document_pdf_0.res_model, 'sign.template')
        template = self.env['sign.template'].search([('id', '=', self.document_pdf_0.res_id)])
        # Get the sign item for the customer from template_3_roles and assign it to the template
        self.template_3_roles.sign_item_ids[0].copy().template_id = template
        sign_request = self.env['sign.request'].create({
            'template_id': template.id,
            'reference': template.display_name,
            'request_item_ids': [Command.create({
                'partner_id': self.partner_1.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
            })],
        })
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(template.sign_item_ids, self.role_customer.id)

        self.patch(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', self._run_wkhtmltopdf)
        sign_request_item.with_context(force_report_rendering=True)._edit_and_sign(sign_values)
        self.assertEqual(sign_request_item.state, 'completed', 'The sign.request.item should be completed')

    def test_signed_documents_access_rights(self):
        """ Test access rights and owner of signed/certificate documents. """
        Document = self.env["documents.document"]
        Partner = self.env["res.partner"]
        User = self.env["res.users"]
        user_root = self.env.ref("base.user_root")

        users = User.create([
            {
                "name": f"test_sign_owner_{group}",
                "login": f"test_sign_owner_{group}@ex.com",
                "email": f"test_sign_owner_{group}@ex.com",
                "groups_id": [Command.set([self.env.ref(group).id])]
            } for group in ("base.group_portal", "base.group_user", "sign.group_sign_user", "sign.group_sign_manager")
        ])
        user_sign_manager = users[-1]
        self.template_1_role.folder_id = self.folder_a
        self.folder_a.action_update_access_rights(partners={user_sign_manager.partner_id: ('edit', False)})

        all_documents_signed = self.env['documents.document']
        self.patch(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', self._run_wkhtmltopdf)
        for user in users:
            with self.subTest(user_name=user.name):
                sign_request = self.create_sign_request_1_role(user.partner_id, Partner)
                # See /sign/sign/<int:sign_request_id>/<token> controller
                sign_request.request_item_ids[0].with_user(user).sudo().with_context(force_report_rendering=True)._edit_and_sign(
                    {str(self.template_1_role.sign_item_ids[0].id): "Test Sign"})
                self.env['documents.access'].invalidate_model()
                documents_signed = Document.search(
                    [('res_model', '=', 'sign.request'), ('res_id', '=', sign_request.id)])
                all_documents_signed |= documents_signed
                self.assertEqual(len(documents_signed), 2)
                self.assertEqual(documents_signed.owner_id, self.env.ref('base.user_root'),
                                 "Owner of the signed/certificate documents must be odooBot.")
                for doc in documents_signed:
                    self.assertEqual(doc.access_via_link, "none")
                    self.assertEqual(doc.access_internal, "none")
                    self.assertTrue(doc.is_access_via_link_hidden)
                    self.assertEqual(doc.owner_id, user_root)
                    self.assertEqual(doc.partner_id, user.partner_id)
                    access_by_partner = {access.partner_id: access for access in doc.access_ids}
                    self.assertEqual(len(doc.access_ids), 1 if user == user_sign_manager else 2)
                    access_manager = access_by_partner.get(user_sign_manager.partner_id)
                    self.assertTrue(access_manager)
                    self.assertEqual(access_manager.role, "edit")
                    self.assertFalse(access_manager.expiration_date)
                    if user != user_sign_manager:
                        access_signer = access_by_partner.get(user.partner_id)
                        self.assertTrue(access_signer)
                        self.assertEqual(access_signer.role, "view")
                        self.assertFalse(access_signer.expiration_date)
                    if user == user_sign_manager:
                        break
                    doc.with_user(user).mapped("name")
                    with self.assertRaises(
                            AccessError,
                            msg="Users without edit permission on the folder cannot edit the signature",
                    ):
                        doc.with_user(user).write({"name": "New name"})

        # user_sign_manager have edit access on all the signed documents
        self.assertEqual(len(all_documents_signed), 8)
        for doc in all_documents_signed:
            doc.with_user(user_sign_manager).name = "Name overridden by the manager"

    def test_correct_reference_doc_set(self):
        """Verifies that the correct reference document is linked to a sign request.
        Ensures that when documents have identical checksums, the sign request is 
        only linked to the document it originated from."""
        writer = OdooPdfFileWriter()
        writer.addBlankPage(width=200, height=200)
        stream = io.BytesIO()
        writer.write(stream)
        # create a document
        self.env['documents.document'].create({
            'name': 'another.pdf',
            'datas': base64.b64encode(stream.getvalue()),
            'access_internal': 'view',
            'folder_id': self.folder_a_a.id,
        })
        # create a document to sign with the same content
        document_to_sign = self.env['documents.document'].create({
            'name': 'test.pdf',
            'datas': base64.b64encode(stream.getvalue()),
            'access_internal': 'view',
            'folder_id': self.folder_a_a.id,
        })
            
        with self.subTest("Ensure sign request does not link to unrelated documents and cause access errors"):
            # create a sign template with the same content then request a signature
            with self.with_user(self.user_1.login):
                attachment = self.env['ir.attachment'].create({
                    'name': 'test.pdf',
                    'datas': base64.b64encode(stream.getvalue()),
                    'mimetype': 'application/pdf',
                })
                template = self.env['sign.template'].create({
                    'attachment_id': attachment.id,
                    'folder_id': self.folder_a_a.id,
                })
                wizard = self.env['sign.send.request'].create({
                    'template_id': template.id,
                    'subject': 'test test',
                    'filename': 'test.pdf',
                    'signer_id': self.user_1.partner_id.id,
                })
                unrelated_request = wizard.create_request()
                wizard._create_request_log_note(unrelated_request)
            self.assertIsNone(unrelated_request.reference_doc, "Sign request should not be linked to unrelated documents")

        with self.subTest("Ensure sign request links to the correct document"):
            # create a sign request from the document_to_sign
            action = document_to_sign.document_sign_create_sign_template_x('sign.template.direct')
            document_sign_template = self.env['sign.template'].browse(action['params']['id'])
            wizard = self.env['sign.send.request'].create({
                'template_id': document_sign_template.id,
                'subject': 'test test',
                'filename': 'test.pdf',
                'signer_id': self.env.user.partner_id.id,
            })
            related_request = wizard.create_request()
            wizard._create_request_log_note(related_request)
            # Verify that the request got linked to the document_to_sign
            self.assertEqual(related_request.reference_doc, document_to_sign)

    def test_signed_document_requester_access(self):
        """ Verifies that the requester of a sign request has at least view access to the signed document. """
        Document = self.env["documents.document"]
        User = self.env["res.users"]

        signer, requester = User.create([{
            "name": f"test_sign_{role}",
            "login": f"test_sign_{role}@ex.com",
            "email": f"test_sign_{role}@ex.com",
        } for role in ("signer", "requester")])

        self.template_1_role.folder_id = self.folder_a

        sign_request = self.env['sign.request'].with_user(requester).create({
            'template_id': self.template_1_role.id,
            'reference': self.template_1_role.display_name,
            'request_item_ids': [Command.create({
                'partner_id': signer.partner_id.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
            })],
        })
        self.patch(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', self._run_wkhtmltopdf)
        sign_request.request_item_ids[0].with_user(signer).sudo().with_context(force_report_rendering=True)._edit_and_sign(
            {str(self.template_1_role.sign_item_ids[0].id): "Test Sign"})
        documents_signed = Document.search(
            [('res_model', '=', 'sign.request'), ('res_id', '=', sign_request.id)])
        self.assertEqual(len(documents_signed), 2)
        for doc in documents_signed:
            # The requester has view access to the signed document
            access_by_partner = doc.access_ids.grouped('partner_id')
            requester_access = access_by_partner[requester.partner_id]
            self.assertIsNotNone(requester_access, "The requester should have access to the signed document")
            doc.with_user(requester).check_access('read')
