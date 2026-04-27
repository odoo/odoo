# -*- coding: utf-8 -*-

from odoo.addons.hr_recruitment.tests.test_recruitment_interviewer import TestRecruitmentInterviewer
from odoo.addons.documents_hr.tests.test_documents_hr_common import TransactionCaseDocumentsHr
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestCaseDocumentsBridgeRecruitment(TransactionCaseDocumentsHr, TestRecruitmentInterviewer):

    @classmethod
    def setUpClass(cls):
        super(TestCaseDocumentsBridgeRecruitment, cls).setUpClass()
        cls.folder = cls.env['documents.document'].create({'name': 'folder_test', 'type': 'folder'})
        cls.company = cls.env['res.company'].create({
            'name': 'test bridge recruitment',
            'recruitment_folder_id': cls.folder.id,
            'documents_recruitment_settings': True,
        })

    def test_job_attachment(self):
        """
        Document is created from job attachment
        """
        job = self.env['hr.job'].create({
            'name': 'Cobble Dev :/',
            'company_id': self.company.id
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': job._name,
            'res_id': job.id
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")
        self.assertEqual(doc.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(doc.access_via_link, "none")
        self.assertEqual(doc.access_internal, "none")
        self.assertTrue(doc.is_access_via_link_hidden)
        self.check_document_no_access(doc, self.doc_user_2)
        self.check_document_no_access(doc, self.document_manager)

    def test_applicant_attachment(self):
        """
        Document is created from applicant attachment
        """
        partner = self.env['res.partner'].create({
            'name': 'Applicant Partner',
        })
        applicant = self.env['hr.applicant'].create({
            'candidate_id': self.env['hr.candidate'].create({'partner_id': partner.id, 'company_id': self.company.id}).id,
            'company_id': self.company.id,
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': applicant._name,
            'res_id': applicant.id,
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")
        self.assertEqual(doc.partner_id, partner, "The partner_id should be the applicant's partner_id")
        self.assertEqual(doc.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(doc.access_via_link, "none")
        self.assertEqual(doc.access_internal, "none")
        self.assertTrue(doc.is_access_via_link_hidden)
        self.check_document_no_access(doc, self.doc_user_2)
        self.check_document_no_access(doc, self.document_manager)

    def test_create_applicant_action(self):
        document = self.env['documents.document'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
        })
        action = document.document_hr_recruitment_create_hr_candidate()
        self.assertEqual(document.res_model, 'hr.candidate', "The document is linked to the created candidate.")
        applicant = self.env['hr.candidate'].search([('id', '=', document.res_id)])
        self.assertTrue(applicant.exists(), 'Candidate has been created.')
        self.assertTrue(action)

    def test_applicant_attachments_access_rights(self):
        """
        Changing the interviewer or the user of an applicant should update the access rights of the documents
        """
        partner = self.env['res.partner'].create({
            'name': 'Applicant Partner',
        })
        applicant = self.env['hr.applicant'].create({
            'candidate_id': self.env['hr.candidate'].create({'partner_id': partner.id, 'company_id': self.company.id}).id,
            'company_id': self.company.id,
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': applicant._name,
            'res_id': applicant.id,
        })

        applicant_document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        doc_access_internal = applicant_document.access_internal
        doc_access_via_link = applicant_document.access_via_link
        doc_access_internal_link = applicant_document.is_access_via_link_hidden

        applicant.interviewer_ids = self.interviewer_user
        applicant.user_id = self.manager_user
        self.assertEqual(len(applicant_document.access_ids), 2, "The 2 partners should have access of the document")
        self.assertEqual(applicant_document.access_ids.mapped('role'), ['view', 'view'], "The 2 partners should have view access of the document")
        self.assertEqual(doc_access_internal, applicant_document.access_internal, "The access_internal should not have changed")
        self.assertEqual(doc_access_via_link, applicant_document.access_via_link, "The access_via_link should not have changed")
        self.assertEqual(doc_access_internal_link, applicant_document.is_access_via_link_hidden, "The access_internal_link should not have changed")

        applicant.interviewer_ids = self.env['res.users']
        unassigned_partner_access_id = applicant_document.access_ids.filtered(lambda p: p.partner_id == applicant.interviewer_ids.partner_id)
        self.assertEqual(unassigned_partner_access_id.role, False, "The partner should not have access of the document")

    def test_document_vals_access_rights(self):
        """
        documents created in a recruitment folder inherit the correct access rights from their parent folder
        """
        company = self.env['res.company'].create({'name': 'Test Company', 'documents_recruitment_settings': True})
        recruitment_folder = self.env['documents.document'].create({
            'name': 'Recruitment Folder',
            'type': 'folder',
            'access_internal': 'view',
            'access_via_link': 'edit',
        })
        company.recruitment_folder_id = recruitment_folder.id
        partner = self.env['res.partner'].create({'name': 'Applicant Partner'})
        candidate = self.env['hr.candidate'].create({'partner_id': partner.id, 'company_id': company.id})
        applicant = self.env['hr.applicant'].create({
            'candidate_id': candidate.id,
            'company_id': company.id,
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': 'hr.applicant',
            'res_id': applicant.id
        })
        applicant_document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertEqual(recruitment_folder.access_internal, applicant_document.access_internal)
        self.assertEqual(recruitment_folder.access_via_link, applicant_document.access_via_link)
