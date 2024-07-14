# -*- coding: utf-8 -*-

from odoo.tests.common import tagged, TransactionCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


@tagged('post_install', '-at_install')
class TestCaseDocumentsBridgeRecruitment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCaseDocumentsBridgeRecruitment, cls).setUpClass()
        cls.folder = cls.env['documents.folder'].create({'name': 'folder_test'})
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
            'datas': GIF,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': job._name,
            'res_id': job.id
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")

    def test_applicant_attachment(self):
        """
        Document is created from applicant attachment
        """
        partner = self.env['res.partner'].create({
            'name': 'Applicant Partner',
        })
        applicant = self.env['hr.applicant'].create({
            'name': 'Applicant',
            'company_id': self.company.id,
            'partner_id': partner.id,
        })
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': applicant._name,
            'res_id': applicant.id,
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")
        self.assertEqual(doc.partner_id, partner, "The partner_id should be the applicant's partner_id")
