import hashlib
import os

import unittest2

import openerp
import openerp.tests.common

class test_ir_attachment(openerp.tests.common.TransactionCase):

    def test_00_attachment_flow(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        root_path = openerp.tools.config['root_path']
        ira = registry('ir.attachment')

        # Blob1
        blob1 = 'blob1'
        blob1_b64 = blob1.encode('base64')
        blob1_hash = hashlib.sha1(blob1).hexdigest()
        blob1_fname = blob1_hash[:3] + '/' + blob1_hash

        # Blob2
        blob2 = 'blob2'
        blob2_b64 = blob2.encode('base64')
        blob2_hash = hashlib.sha1(blob2).hexdigest()
        blob2_fname = blob2_hash[:3] + '/' + blob2_hash

        # 'ir_attachment.location' is undefined test database storage
        a1 = ira.create(cr, uid, {'name': 'a1', 'datas': blob1_b64})
        a1_read = ira.read(cr, uid, [a1], ['datas'])
        self.assertEqual(a1_read[0]['datas'], blob1_b64)

        cr.execute("select id,db_datas from ir_attachment where id = %s", (a1,) )
        a1_db_datas = str(cr.fetchall()[0][1])
        self.assertEqual(a1_db_datas, blob1_b64)

        # define a location for filestore
        registry('ir.config_parameter').set_param(cr, uid, 'ir_attachment.location', 'file:///filestore')

        # Test file storage
        a2 = ira.create(cr, uid, {'name': 'a2', 'datas': blob1_b64})
        a2_read = ira.read(cr, uid, [a2], ['datas'])
        self.assertEqual(a2_read[0]['datas'], blob1_b64)

        cr.execute("select id,store_fname from ir_attachment where id = %s", (a2,) )
        a2_store_fname = cr.fetchall()[0][1]
        self.assertEqual(a2_store_fname, blob1_fname)

        a2_fn = os.path.join(root_path, 'filestore', cr.dbname, blob1_hash[:3], blob1_hash)
        fc = file(a2_fn).read()
        self.assertEqual(fc, blob1)

        # create a3 with same blob
        a3 = ira.create(cr, uid, {'name': 'a3', 'datas': blob1_b64})
        a3_read = ira.read(cr, uid, [a3], ['datas'])
        self.assertEqual(a3_read[0]['datas'], blob1_b64)

        cr.execute("select id,store_fname from ir_attachment where id = %s", (a3,) )
        a3_store_fname = cr.fetchall()[0][1]
        self.assertEqual(a3_store_fname, a2_store_fname)

        # create a4 blob2
        a4 = ira.create(cr, uid, {'name': 'a4', 'datas': blob2_b64})
        a4_read = ira.read(cr, uid, [a4], ['datas'])
        self.assertEqual(a4_read[0]['datas'], blob2_b64)

        a4_fn = os.path.join(root_path, 'filestore', cr.dbname, blob2_hash[:3], blob2_hash)
        self.assertTrue(os.path.isfile(a4_fn))

        # delete a3 but file stays
        ira.unlink(cr, uid, [a3])
        self.assertTrue(os.path.isfile(a2_fn))

        # delete a2 it is unlinked
        ira.unlink(cr, uid, [a2])
        self.assertFalse(os.path.isfile(a2_fn))

        # update a4 blob2 by blob1
        ira.write(cr, uid, [a4], {'datas': blob1_b64})
        a4_read = ira.read(cr, uid, [a4], ['datas'])
        self.assertEqual(a4_read[0]['datas'], blob1_b64)

        # file of a4 disapear and a2 reappear
        self.assertFalse(os.path.isfile(a4_fn))
        self.assertTrue(os.path.isfile(a2_fn))

        # everybody applause


