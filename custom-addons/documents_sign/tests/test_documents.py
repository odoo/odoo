# -*- coding: utf-8 -*-

import base64
from odoo.tools import file_open
from odoo.tests.common import TransactionCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


class TestCaseDocumentsBridgeSign(TransactionCase):
    """

    """
    def setUp(self):
        super(TestCaseDocumentsBridgeSign, self).setUp()

        with file_open('sign/static/demo/sample_contract.pdf', "rb") as f:
            pdf_content = f.read()

        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.folder_a_a = self.env['documents.folder'].create({
            'name': 'folder A - A',
            'parent_folder_id': self.folder_a.id,
        })
        self.document_pdf = self.env['documents.document'].create({
            'datas': base64.encodebytes(pdf_content),
            'name': 'file.pdf',
            'folder_id': self.folder_a_a.id,
        })
        self.workflow_rule_template = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule create template on f_a',
            'create_model': 'sign.template.new',
        })

        self.workflow_rule_direct_sign = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule direct sign',
            'create_model': 'sign.template.direct',
        })

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (sign).
    
        """
        self.assertEqual(self.document_pdf.res_model, 'documents.document', "failed at default res model")
        self.workflow_rule_template.apply_actions([self.document_pdf.id])
        self.assertTrue(self.workflow_rule_direct_sign.limited_to_single_record,
                        "this rule should only be available on single records")
    
        self.assertEqual(self.document_pdf.res_model, 'sign.template',
                         "failed at workflow_bridge_dms_sign new res_model")
        template = self.env['sign.template'].search([('id', '=', self.document_pdf.res_id)])
        self.assertTrue(template.exists(), 'failed at workflow_bridge_dms_account template')
        self.assertEqual(self.document_pdf.res_id, template.id, "failed at workflow_bridge_dms_account res_id")
