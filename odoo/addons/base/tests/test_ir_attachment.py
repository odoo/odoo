# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
import hashlib
import io
import os

from PIL import Image

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools import image_to_base64

HASH_SPLIT = 2      # FIXME: testing implementations detail is not a good idea


class TestIrAttachment(TransactionCase):
    def setUp(self):
        super(TestIrAttachment, self).setUp()
        self.Attachment = self.env['ir.attachment']
        self.filestore = self.Attachment._filestore()

        # Blob1
        self.blob1 = b'blob1'
        self.blob1_b64 = base64.b64encode(self.blob1)
        self.blob1_hash = hashlib.sha1(self.blob1).hexdigest()
        self.blob1_fname = self.blob1_hash[:HASH_SPLIT] + '/' + self.blob1_hash

        # Blob2
        self.blob2 = b'blob2'
        self.blob2_b64 = base64.b64encode(self.blob2)

    def assertApproximately(self, value, expectedSize, delta=1):
        # we don't used bin_size in context, because on write, the cached value is the data and not
        # the size, so we need on each write to invalidate cache if we really want to get the size.
        try:
            value = base64.b64decode(value.decode())
        except UnicodeDecodeError:
            pass
        size = len(value) / 1024 # kb

        self.assertAlmostEqual(size, expectedSize, delta=delta)

    def test_01_store_in_db(self):
        # force storing in database
        self.env['ir.config_parameter'].set_param('ir_attachment.location', 'db')

        # 'ir_attachment.location' is undefined test database storage
        a1 = self.Attachment.create({'name': 'a1', 'raw': self.blob1})
        self.assertEqual(a1.datas, self.blob1_b64)

        self.assertEqual(a1.db_datas, self.blob1)

    def test_02_store_on_disk(self):
        a2 = self.Attachment.create({'name': 'a2', 'raw': self.blob1})
        self.assertEqual(a2.store_fname, self.blob1_fname)
        self.assertTrue(os.path.isfile(os.path.join(self.filestore, a2.store_fname)))

    def test_03_no_duplication(self):
        a2 = self.Attachment.create({'name': 'a2', 'raw': self.blob1})
        a3 = self.Attachment.create({'name': 'a3', 'raw': self.blob1})
        self.assertEqual(a3.store_fname, a2.store_fname)

    def test_04_keep_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'raw': self.blob1})
        a3 = self.Attachment.create({'name': 'a3', 'raw': self.blob1})

        a2_fn = os.path.join(self.filestore, a2.store_fname)

        a3.unlink()
        self.assertTrue(os.path.isfile(a2_fn))

    def test_05_change_data_change_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'raw': self.blob1})
        a2_store_fname1 = a2.store_fname
        a2_fn = os.path.join(self.filestore, a2_store_fname1)

        self.assertTrue(os.path.isfile(a2_fn))

        a2.write({'raw': self.blob2})

        a2_store_fname2 = a2.store_fname
        self.assertNotEqual(a2_store_fname1, a2_store_fname2)

        a2_fn = os.path.join(self.filestore, a2_store_fname2)
        self.assertTrue(os.path.isfile(a2_fn))

    def test_07_write_mimetype(self):
        """
        Tests the consistency of documents' mimetypes
        """

        Attachment = self.Attachment.with_user(self.env.ref('base.user_demo').id)
        a2 = Attachment.create({'name': 'a2', 'datas': self.blob1_b64, 'mimetype': 'image/png'})
        self.assertEqual(a2.mimetype, 'image/png', "the new mimetype should be the one given on write")
        a3 = Attachment.create({'name': 'a3', 'datas': self.blob1_b64, 'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
        self.assertEqual(a3.mimetype, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', "should preserve office mime type")

    def test_08_neuter_xml_mimetype(self):
        """
        Tests that potentially harmful mimetypes (XML mimetypes that can lead to XSS attacks) are converted to text
        """
        Attachment = self.Attachment.with_user(self.env.ref('base.user_demo').id)
        document = Attachment.create({'name': 'document', 'datas': self.blob1_b64})
        document.write({'datas': self.blob1_b64, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XML mimetype should be forced to text")
        document.write({'datas': self.blob1_b64, 'mimetype': 'image/svg+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "SVG mimetype should be forced to text")
        document.write({'datas': self.blob1_b64, 'mimetype': 'text/html'})
        self.assertEqual(document.mimetype, 'text/plain', "HTML mimetype should be forced to text")
        document.write({'datas': self.blob1_b64, 'mimetype': 'application/xhtml+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XHTML mimetype should be forced to text")

    def test_09_dont_neuter_xml_mimetype_for_admin(self):
        """
        Admin user does not have a mime type filter
        """
        document = self.Attachment.create({'name': 'document', 'datas': self.blob1_b64})
        document.write({'datas': self.blob1_b64, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/xml', "XML mimetype should not be forced to text, for admin user")

    def test_10_image_autoresize(self):
        Attachment = self.env['ir.attachment']
        img_bin = io.BytesIO()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with Image.open(os.path.join(dir_path, 'odoo.jpg'), 'r') as logo:
            img = Image.new('RGB', (4000, 2000), '#4169E1')
            img.paste(logo)
            img.save(img_bin, 'JPEG')

        img_encoded = image_to_base64(img, 'JPEG')
        img_bin = img_bin.getvalue()

        fullsize = 124.99

        ####################################
        ### test create/write on 'datas'
        ####################################
        attach = Attachment.with_context(image_no_postprocess=True).create({
            'name': 'image',
            'datas': img_encoded,
        })
        self.assertApproximately(attach.datas, fullsize)  # no resize, no compression

        attach = attach.with_context(image_no_postprocess=False)
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 12.06)  # default resize + default compression

        # resize + default quality (80)
        self.env['ir.config_parameter'].set_param('base.image_autoresize_max_px', '1024x768')
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 3.71)

        # resize + quality 50
        self.env['ir.config_parameter'].set_param('base.image_autoresize_quality', '50')
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 3.57)

        # no resize + no quality implicit
        self.env['ir.config_parameter'].set_param('base.image_autoresize_max_px', '0')
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, fullsize)

        # Check that we only compress quality when we resize. We avoid to compress again during a new write.
        # no resize + quality -> should have no effect
        self.env['ir.config_parameter'].set_param('base.image_autoresize_max_px', '10000x10000')
        self.env['ir.config_parameter'].set_param('base.image_autoresize_quality', '50')
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, fullsize)

        ####################################
        ### test create/write on 'raw'
        ####################################

        # reset default ~ delete
        self.env['ir.config_parameter'].search([('key', 'ilike', 'base.image_autoresize%')]).unlink()

        attach = Attachment.with_context(image_no_postprocess=True).create({
            'name': 'image',
            'raw': img_bin,
        })
        self.assertApproximately(attach.raw, fullsize)  # no resize, no compression

        attach = attach.with_context(image_no_postprocess=False)
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 12.06)  # default resize + default compression

        # resize + default quality (80)
        self.env['ir.config_parameter'].set_param('base.image_autoresize_max_px', '1024x768')
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 3.71)

        # resize + no quality
        self.env['ir.config_parameter'].set_param('base.image_autoresize_quality', '0')
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 4.09)

        # resize + quality 50
        self.env['ir.config_parameter'].set_param('base.image_autoresize_quality', '50')
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 3.57)

        # no resize + no quality implicit
        self.env['ir.config_parameter'].set_param('base.image_autoresize_max_px', '0')
        attach.raw = img_bin
        self.assertApproximately(attach.raw, fullsize)

    def test_11_copy(self):
        """
        Copying an attachment preserves the data
        """
        document = self.Attachment.create({'name': 'document', 'datas': self.blob2_b64})
        document2 = document.copy({'name': "document (copy)"})
        self.assertEqual(document2.name, "document (copy)")
        self.assertEqual(document2.datas, document.datas)
        self.assertEqual(document2.db_datas, document.db_datas)
        self.assertEqual(document2.store_fname, document.store_fname)
        self.assertEqual(document2.checksum, document.checksum)

        document3 = document.copy({'datas': self.blob1_b64})
        self.assertEqual(document3.datas, self.blob1_b64)
        self.assertEqual(document3.raw, self.blob1)
        self.assertTrue(self.filestore)  # no data in db but has a store_fname
        self.assertEqual(document3.db_datas, False)
        self.assertEqual(document3.store_fname, self.blob1_fname)
        self.assertEqual(document3.checksum, self.blob1_hash)


class TestPermissions(TransactionCase):
    def setUp(self):
        super().setUp()
        # replace self.env(uid=1) with an actual user environment so rules apply
        self.env = self.env(user=self.env.ref('base.user_demo'))
        self.Attachments = self.env['ir.attachment']

        # create a record with an attachment and a rule allowing Read access
        # but preventing Create, Update, or Delete
        record = self.Attachments.create({'name': 'record1'})
        self.vals = {'name': 'attach', 'res_id': record.id, 'res_model': record._name}
        a = self.attachment = self.Attachments.create(self.vals)

        # prevent create, write and unlink accesses on record
        self.rule = self.env['ir.rule'].sudo().create({
            'name': 'remove access to record %d' % record.id,
            'model_id': self.env['ir.model']._get_id(record._name),
            'domain_force': "[('id', '!=', %s)]" % record.id,
            'perm_read': False
        })
        a.flush()
        a.invalidate_cache(ids=a.ids)

    def test_no_read_permission(self):
        """If the record can't be read, the attachment can't be read either
        """
        # check that the information can be read out of the box
        self.attachment.datas
        # prevent read access on record
        self.rule.perm_read = True
        self.attachment.invalidate_cache(ids=self.attachment.ids)
        with self.assertRaises(AccessError):
            self.attachment.datas

    def test_with_write_permissions(self):
        """With write permissions to the linked record, attachment can be
        created, updated, or deleted (or copied).
        """
        # enable write permission on linked record
        self.rule.perm_write = False
        attachment = self.Attachments.create(self.vals)
        attachment.copy()
        attachment.write({'raw': b'test'})
        attachment.unlink()

    def test_basic_modifications(self):
        """Lacking write access to the linked record means create, update, and
        delete on the attachment are forbidden
        """
        with self.assertRaises(AccessError):
            self.Attachments.create(self.vals)
        with self.assertRaises(AccessError):
            self.attachment.write({'raw': b'yay'})
        with self.assertRaises(AccessError):
            self.attachment.unlink()
        with self.assertRaises(AccessError):
            self.attachment.copy()

    def test_cross_record_copies(self):
        """Copying attachments between records (in the same model or not) adds
        wrinkles as the ACLs may diverge a lot more
        """
        # create an other unwritable record in a different model
        unwritable = self.env['res.users.log'].create({})
        with self.assertRaises(AccessError):
            unwritable.write({})  # checks unwritability
        # create a writable record in the same model
        writable = self.Attachments.create({'name': 'yes'})
        writable.name = 'canwrite'  # checks for writeability

        # can copy from a record with read permissions to one with write permissions
        copied = self.attachment.copy({'res_model': writable._name, 'res_id': writable.id})
        # can copy to self given write permission
        copied.copy()
        # can not copy back to record without write permission
        with self.assertRaises(AccessError):
            copied.copy({'res_id': self.vals['res_id']})

        # can not copy to a record without write permission
        with self.assertRaises(AccessError):
            self.attachment.copy({'res_model': unwritable._name, 'res_id': unwritable.id})
        # even from a record with write permissions
        with self.assertRaises(AccessError):
            copied.copy({'res_model': unwritable._name, 'res_id': unwritable.id})
