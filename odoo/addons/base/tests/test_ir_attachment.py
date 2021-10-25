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
        blob1_hash = hashlib.sha1(self.blob1).hexdigest()
        self.blob1_fname = blob1_hash[:HASH_SPLIT] + '/' + blob1_hash

        # Blob2
        self.blob2 = b'blob2'

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

    def test_06_linked_record_permission(self):
        Attachment = self.Attachment.with_user(self.env.ref('base.user_demo').id)
        a1 = self.Attachment.create({'name': 'a1'})
        vals = {'name': 'attach', 'res_id': a1.id, 'res_model': 'ir.attachment'}
        a2 = Attachment.create(vals)

        # remove access to linked record a1
        rule = self.env['ir.rule'].create({
            'name': 'test_rule', 'domain_force': "[('id', '!=', %s)]" % a1.id,
            'model_id': self.env.ref('base.model_ir_attachment').id,
        })
        a2.invalidate_cache(ids=a2.ids)

        # no read permission on linked record
        with self.assertRaises(AccessError):
            a2.datas

        # read permission on linked record
        rule.perm_read = False
        a2.datas

        # no write permission on linked record
        with self.assertRaises(AccessError):
            a3 = Attachment.create(vals)
        with self.assertRaises(AccessError):
            a2.write({'raw': self.blob2})
        with self.assertRaises(AccessError):
            a2.unlink()

        # write permission on linked record
        rule.perm_write = False
        a4 = Attachment.create(vals)
        a4.write({'raw': self.blob2})
        a4.unlink()

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
