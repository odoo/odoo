import base64

from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TransactionCaseDocumentsHr(TransactionCaseDocuments):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.TEXT = base64.b64encode(bytes("documents_hr", 'utf-8'))
        cls.doc_user_2, cls.hr_manager = cls.env['res.users'].create([{
            'name': "documents test basic user",
            'login': "dtbu",
            'email': "dtbu@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('documents.group_documents_user').id])]
        }, {
            'name': "Hr manager test",
            'login': "hr_manager_test",
            'email': "hr_manager_test@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('hr.group_hr_manager').id])]
        }])
        cls.hr_folder = cls.env['documents.document'].create({
            'name': 'hr_folder',
            'type': 'folder',
            'access_internal': 'view',
        })
        cls.hr_folder.action_update_access_rights(partners={cls.hr_manager.partner_id: ('edit', False)})
        company = cls.env.user.company_id
        company.documents_hr_settings = True
        company.documents_hr_folder = cls.hr_folder.id
        cls.user_root = cls.env.ref('base.user_root')

    def create_hr_related_document(self, related_record, folder, n=2):
        return self.env['documents.document'].create([{
                'res_id': related_record.id,
                'res_model': related_record._name,
                'name': f'Create document of {related_record.display_name}',
                'folder_id': folder.id,
            }
            for _ in range(n)])

    def create_hr_related_document_by_attachment(self, related_record, n=2):
        attachment_vals = {
            'res_id': related_record.id,
            'res_model': related_record._name,
            'name': f'Auto creation of document from attachment related to {related_record.display_name}',
        }
        attachments = self.env['ir.attachment'].create([attachment_vals for _ in range(n)])
        return self.env['documents.document'].search([('attachment_id', 'in', attachments.ids)])

    def create_hr_related_document_with_attachment(self, related_record, folder, n=2):
        name = f'Creation of document with an already created attachment of {related_record.display_name}'
        att_vals = {
            'name': name,
            'res_id': related_record.id,
            'res_model': related_record._name,
        }
        return self.env['documents.document'].create([{
            'name': name,
            'folder_id': folder.id,
            'attachment_id': self.env['ir.attachment'].with_context(no_document=True).create(att_vals).id,
        } for _ in range(n)])

    def check_document_no_access(self, document, doc_user):
        document.ensure_one()
        with mute_logger('odoo.addons.base.models.ir_rule'), self.assertRaises(
                AccessError, msg=f"{doc_user.name} cannot see document {document.name}"):
            document.with_user(doc_user).mapped('name')

    def check_document_creation_permission(self, related_record, folder=None, folder_manager=None):
        """ Test that documents created with the given related record is only viewable by the employee of this record
        and the manager set on the folder.

        :param related_record: Related record of doc_user employee
        :param folder: folder where documents are to be created (when created explicitly not through an attachment).
        :param folder_manager: manager (user) with edit access on the folder to test access propagation

        We add this method in common to check various model of HR (employee, contract, payslips, ...).
        """
        folder = folder or self.hr_folder
        folder_manager = folder_manager or self.hr_manager

        self.assertTrue(folder.access_ids)
        for documents in (self.create_hr_related_document(related_record, folder),
                          self.create_hr_related_document_by_attachment(related_record),
                          self.create_hr_related_document_with_attachment(related_record, folder)):
            with self.subTest(name=documents[0].name):
                self.assertEqual(documents.with_user(self.doc_user).mapped('user_permission'), ['view', 'view'],
                                 "At employee document creation, the employee contact gets view access")
                # We test access propagation because there is no propagation if access_ids are set at document creation
                self.assertEqual(documents.with_user(folder_manager).mapped('user_permission'), ['edit', 'edit'],
                                 "At employee document creation, the folder access are propagated")
                for doc_idx in (0, 1):
                    self.check_document_no_access(documents[doc_idx], self.doc_user_2)
                    self.check_document_no_access(documents[doc_idx], self.document_manager)
                    self.assertEqual(len(documents[doc_idx].access_ids), 2,
                                     "Only the employee and the manager have access")

        folder.action_update_access_rights(partners={self.doc_user.partner_id: ('edit', False)})
        documents = self.create_hr_related_document(related_record, folder)
        self.assertEqual(documents.with_user(self.doc_user).mapped('user_permission'), ['edit', 'edit'],
                         "Permission inherited from folder permission are not overridden")
