from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments, GIF, TEXT


class TestDocumentsMailActivity(TransactionCaseDocuments):

    def test_request_activity(self):
        """
        Makes sure the document request activities are working properly
        """
        partner = self.env['res.partner'].create({'name': 'Pepper Street'})
        activity_type = self.env['mail.activity.type'].create({
            'name': 'test_activity_type',
            'category': 'upload_file',
            'folder_id': self.folder_a.id,
        })
        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'user_id': self.doc_user.id,
            'res_id': partner.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'summary': 'test_summary',
        })

        activity_2 = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'user_id': self.doc_user.id,
            'res_id': partner.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'summary': 'test_summary_2',
        })

        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'Test activity 1',
        })

        document_1 = self.env['documents.document'].search([('request_activity_id', '=', activity.id)], limit=1)
        document_2 = self.env['documents.document'].search([('request_activity_id', '=', activity_2.id)], limit=1)

        self.assertEqual(document_1.name, 'test_summary', 'the activity document should have the right name')
        self.assertEqual(document_1.folder_id.id, self.folder_a.id, 'the document 1 should have the right folder')
        self.assertEqual(document_2.folder_id.id, self.folder_a.id, 'the document 2 should have the right folder')
        activity._action_done(attachment_ids=[attachment.id])
        document_2.write({'datas': TEXT, 'name': 'new filename'})
        self.assertEqual(document_1.attachment_id.id, attachment.id,
                         'the document should have the newly added attachment')
        self.assertFalse(activity.exists(), 'the activity should be done')
        self.assertFalse(activity_2.exists(), 'the activity_2 should be done')

    def test_recurring_document_request(self):
        """
        Ensure that separate document requests are created for recurring upload activities
        Ensure that the next activity is linked to the new document
        """
        self.doc_partner = self.env['res.partner'].create({
            'name': 'Luke Skywalker',
        })
        activity_type = self.env['mail.activity.type'].create({
            'name': 'recurring_upload_activity_type',
            'category': 'upload_file',
            'folder_id': self.folder_a.id,
        })
        activity_type.write({
            'chaining_type': 'trigger',
            'triggered_next_type_id': activity_type.id
        })
        document = self.env['documents.request_wizard'].create({
            'name': 'Wizard Request',
            'requestee_id': self.doc_partner.id,
            'activity_type_id': activity_type.id,
            'folder_id': self.folder_a.id,
        }).request_document()
        activity = document.request_activity_id

        self.assertEqual(activity.summary, 'Wizard Request')

        # Simulate the document upload controller which create the attachment
        document.write({'attachment_id': self.env['ir.attachment'].create({'datas': GIF, 'name': 'testGif.gif'}).id})

        self.assertFalse(activity.exists(), 'the activity should be removed after file upload')
        self.assertEqual(document.type, 'binary', 'document 1 type should be binary')
        self.assertFalse(document.request_activity_id, 'document 1 should have no activity remaining')

        # a new document (request) and file_upload activity should be created
        activity_2 = self.env['mail.activity'].search([
            ('res_model', '=', 'documents.document'), ('activity_type_id', '=', activity_type.id)])
        document_2 = self.env['documents.document'].search([('request_activity_id', '=', activity_2.id), ('type', '=', 'binary'), ('attachment_id', '=', False)])

        self.assertNotEqual(document_2.id, document.id, 'a new document and activity should exist')
        self.assertEqual(document_2.request_activity_id.summary, 'Wizard Request')
