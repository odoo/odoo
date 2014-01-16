import hashlib
import os

import openerp
import openerp.tests.common

HASH_SPLIT = 2      # FIXME: testing implementations detail is not a good idea

class test_ir_attachment(openerp.tests.common.TransactionCase):
    def setUp(self):
        super(test_ir_attachment, self).setUp()
        registry, cr, uid = self.registry, self.cr, self.uid
        self.ira = registry('ir.attachment')
        self.filestore = self.ira._filestore(cr, uid)

        # Blob1
        self.blob1 = 'blob1'
        self.blob1_b64 = self.blob1.encode('base64')
        blob1_hash = hashlib.sha1(self.blob1).hexdigest()
        self.blob1_fname = blob1_hash[:HASH_SPLIT] + '/' + blob1_hash

        # Blob2
        blob2 = 'blob2'
        self.blob2_b64 = blob2.encode('base64')

    def test_01_store_in_db(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        # force storing in database
        registry('ir.config_parameter').set_param(cr, uid, 'ir_attachment.location', 'db')

        # 'ir_attachment.location' is undefined test database storage
        a1 = self.ira.create(cr, uid, {'name': 'a1', 'datas': self.blob1_b64})
        a1_read = self.ira.read(cr, uid, [a1], ['datas'])
        self.assertEqual(a1_read[0]['datas'], self.blob1_b64)

        a1_db_datas = self.ira.browse(cr, uid, a1).db_datas
        self.assertEqual(a1_db_datas, self.blob1_b64)

    def test_02_store_on_disk(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        a2 = self.ira.create(cr, uid, {'name': 'a2', 'datas': self.blob1_b64})
        a2_store_fname = self.ira.browse(cr, uid, a2).store_fname

        self.assertEqual(a2_store_fname, self.blob1_fname)
        self.assertTrue(os.path.isfile(os.path.join(self.filestore, a2_store_fname)))

    def test_03_no_duplication(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        a2 = self.ira.create(cr, uid, {'name': 'a2', 'datas': self.blob1_b64})
        a2_store_fname = self.ira.browse(cr, uid, a2).store_fname

        a3 = self.ira.create(cr, uid, {'name': 'a3', 'datas': self.blob1_b64})
        a3_store_fname = self.ira.browse(cr, uid, a3).store_fname

        self.assertEqual(a3_store_fname, a2_store_fname)

    def test_04_keep_file(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        a2 = self.ira.create(cr, uid, {'name': 'a2', 'datas': self.blob1_b64})
        a3 = self.ira.create(cr, uid, {'name': 'a3', 'datas': self.blob1_b64})

        a2_store_fname = self.ira.browse(cr, uid, a2).store_fname
        a2_fn = os.path.join(self.filestore, a2_store_fname)

        self.ira.unlink(cr, uid, [a3])
        self.assertTrue(os.path.isfile(a2_fn))

        # delete a2 it is unlinked
        self.ira.unlink(cr, uid, [a2])
        self.assertFalse(os.path.isfile(a2_fn))

    def test_05_change_data_change_file(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        a2 = self.ira.create(cr, uid, {'name': 'a2', 'datas': self.blob1_b64})
        a2_store_fname = self.ira.browse(cr, uid, a2).store_fname
        a2_fn = os.path.join(self.filestore, a2_store_fname)

        self.assertTrue(os.path.isfile(a2_fn))

        self.ira.write(cr, uid, [a2], {'datas': self.blob2_b64})
        self.assertFalse(os.path.isfile(a2_fn))

        new_a2_store_fname = self.ira.browse(cr, uid, a2).store_fname
        self.assertNotEqual(a2_store_fname, new_a2_store_fname)

        new_a2_fn = os.path.join(self.filestore, new_a2_store_fname)
        self.assertTrue(os.path.isfile(new_a2_fn))
