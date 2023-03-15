# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import os

from odoo.tests.common import TransactionCase

HASH_SPLIT = 2      # FIXME: testing implementations detail is not a good idea


class TestIrAttachment(TransactionCase):
    def setUp(self):
        super(TestIrAttachment, self).setUp()
        self.Attachment = self.env['ir.attachment']
        self.filestore = self.Attachment._filestore()

        # Blob1
        self.blob1 = b'blob1'
        self.blob1_b64 = base64.b64encode(self.blob1)
        blob1_hash = hashlib.sha1(self.blob1).hexdigest()
        self.blob1_fname = blob1_hash[:HASH_SPLIT] + '/' + blob1_hash

        # Blob2
        self.blob2 = b'blob2'
        self.blob2_b64 = base64.b64encode(self.blob2)

    def test_01_store_in_db(self):
        # force storing in database
        self.env['ir.config_parameter'].set_param('ir_attachment.location', 'db')

        # 'ir_attachment.location' is undefined test database storage
        a1 = self.Attachment.create({'name': 'a1', 'datas': self.blob1_b64})
        self.assertEqual(a1.datas, self.blob1_b64)

        a1_db_datas = a1.db_datas
        self.assertEqual(a1_db_datas, self.blob1_b64)

    def test_02_store_on_disk(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        self.assertEqual(a2.store_fname, self.blob1_fname)
        self.assertTrue(os.path.isfile(os.path.join(self.filestore, a2.store_fname)))

    def test_03_no_duplication(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a3 = self.Attachment.create({'name': 'a3', 'datas': self.blob1_b64})
        self.assertEqual(a3.store_fname, a2.store_fname)

    def test_04_keep_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a3 = self.Attachment.create({'name': 'a3', 'datas': self.blob1_b64})

        a2_fn = os.path.join(self.filestore, a2.store_fname)

        a3.unlink()
        self.assertTrue(os.path.isfile(a2_fn))

    def test_05_change_data_change_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a2_store_fname1 = a2.store_fname
        a2_fn = os.path.join(self.filestore, a2_store_fname1)

        self.assertTrue(os.path.isfile(a2_fn))

        a2.write({'datas': self.blob2_b64})

        a2_store_fname2 = a2.store_fname
        self.assertNotEqual(a2_store_fname1, a2_store_fname2)

        a2_fn = os.path.join(self.filestore, a2_store_fname2)
        self.assertTrue(os.path.isfile(a2_fn))

    def test_06_write_mimetype(self):
        """
        Tests the consistency of documents mimetypes and SVG with others users
        """
        Attachment = self.Attachment.with_user(self.env.ref('base.user_demo').id)
        a2 = Attachment.create({'name': 'a2', 'datas': self.blob1_b64, 'mimetype': 'image/png'})
        self.assertEqual(a2.mimetype, 'image/png', "the new mimetype should be the one given on write")
        a3 = Attachment.create({'name': 'a3', 'datas': self.blob1_b64, 'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
        self.assertEqual(a3.mimetype, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', "should preserve office mime type")
        a4 = Attachment.create({'name': 'a4', 'datas': self.blob1_b64, 'mimetype': 'image/svg+xml'})
        self.assertEqual(a4.mimetype, 'image/svg+xml', "should preserve svg mime type")

    def test_07_dont_neuter_xml_mimetype_for_admin(self):
        """
        Admin user does not have a mime type filter
        """
        document = self.Attachment.create({'name': 'document', 'datas': self.blob1_b64})
        document.write({'datas': self.blob1_b64, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/xml', "XML mimetype should not be forced to text, for admin user")
