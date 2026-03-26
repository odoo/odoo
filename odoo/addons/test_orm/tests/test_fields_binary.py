import base64
import io
from collections import OrderedDict
from datetime import date, datetime
from unittest.mock import patch
from contextlib import contextmanager

import psycopg2
from PIL import Image

from odoo import Command, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged, users
from odoo.tools import BinaryBytes, float_repr, mute_logger
from odoo.tools.image import binary_to_image, image_data_uri

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.tests.files import SVG_RAW, ZIP_RAW
from odoo.addons.test_orm.tests.test_domain_expression import TransactionExpressionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFields(TransactionCaseWithUserDemo, TransactionExpressionCase):
    def setUp(self):
        # for tests methods that create custom models/fields
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)
        super().setUp()
        self.env.ref('test_orm.discussion_0').write({'participants': [Command.link(self.user_demo.id)]})
        # YTI FIX ME: The cache shouldn't be inconsistent (rco is gonna fix it)
        # self.env.ref('test_orm.discussion_0').participants -> 1 user
        # self.env.ref('test_orm.discussion_0').invalidate()
        # self.env.ref('test_orm.discussion_0').with_context(active_test=False).participants -> 2 users
        self.env.ref('test_orm.message_0_1').write({'author': self.user_demo.id})

    def test_81_binary_assign(self):
        binary_value1 = BinaryBytes(b'content')
        record = self.env['test_orm.model_binary'].create({'binary': binary_value1})
        self.assertEqual(record.binary.content, binary_value1.content)
        self.assertEqual(record.binary_related_no_store.content, binary_value1.content)
        self.assertEqual(record.binary_related_store.content, binary_value1.content)

        binary_value2 = BinaryBytes(b'test')
        record.binary = binary_value2
        self.assertEqual(record.binary.content, binary_value2.content)
        self.assertEqual(record.binary_related_no_store.content, binary_value2.content)
        self.assertEqual(record.binary_related_store.content, binary_value2.content)

        record.env.invalidate_all()
        self.assertEqual(record.binary.content, binary_value2.content)
        self.assertEqual(record.binary_related_no_store.content, binary_value2.content)
        self.assertEqual(record.binary_related_store.content, binary_value2.content)

    def test_82_binary_bin_size(self):
        binary_value = BinaryBytes(b'content')
        record = self.env['test_orm.model_binary'].create({'binary': binary_value})

        def assertBinaryValue(read_value, fields=('binary', 'binary_related_store', 'binary_related_no_store')):
            for field in fields:
                self.assertEqual(record[field].content, binary_value.content, f'Incorrect result for {field}')
            vals = record.read(fields)[0]
            for field in fields:
                self.assertEqual(vals[field], read_value)

        record = record.with_context(bin_size=True)
        assertBinaryValue(f'{binary_value.size}.00 bytes')

        record = record.with_context(bin_size=False)
        assertBinaryValue(base64.b64encode(binary_value.content).decode())

        # updating and invalidation with bin_size has no effect
        record = record.with_context(bin_size=True)
        record.binary = binary_value = BinaryBytes(b'test')
        record.env.invalidate_all()
        assertBinaryValue(f'{binary_value.size}.00 bytes')

    def test_85_binary_guess_zip(self):
        # Regular ZIP files can be uploaded by non-admin users
        self.env['test_orm.binary_svg'].with_user(self.user_demo).create({
            'name': 'Test without attachment',
            'image_wo_attachment': BinaryBytes(ZIP_RAW),
        })

    def test_86_text_base64_guess_svg(self):
        with self.assertRaises(UserError) as e:
            self.env['test_orm.binary_svg'].with_user(self.user_demo).create({
                'name': 'Test without attachment',
                'image_wo_attachment': BinaryBytes(SVG_RAW),
            })
        self.assertEqual(e.exception.args[0], 'Only admins can upload SVG files.')

    def test_90_binary_svg(self):
        # This should work without problems
        self.env['test_orm.binary_svg'].create({
            'name': 'Test without attachment',
            'image_wo_attachment': BinaryBytes(SVG_RAW),
        })
        # And this gives error
        with self.assertRaises(UserError):
            self.env['test_orm.binary_svg'].with_user(
                self.user_demo,
            ).create({
                'name': 'Test without attachment',
                'image_wo_attachment': BinaryBytes(SVG_RAW),
            })

    def test_91_binary_svg_attachment(self):
        # This doesn't neuter SVG with admin
        record = self.env['test_orm.binary_svg'].create({
            'name': 'Test without attachment',
            'image_attachment': BinaryBytes(SVG_RAW),
        })
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', record._name),
            ('res_field', '=', 'image_attachment'),
            ('res_id', '=', record.id),
        ])
        self.assertEqual(attachment.mimetype, 'image/svg+xml')
        # ...but this should be neutered with demo user
        record = self.env['test_orm.binary_svg'].with_user(
            self.user_demo,
        ).create({
            'name': 'Test without attachment',
            'image_attachment': BinaryBytes(SVG_RAW),
        })
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', record._name),
            ('res_field', '=', 'image_attachment'),
            ('res_id', '=', record.id),
        ])
        self.assertEqual(attachment.mimetype, 'text/plain')

    def test_92_binary_self_avatar_svg(self):
        demo_user = self.user_demo
        # User demo changes his own avatar
        demo_user.with_user(demo_user).image_1920 = BinaryBytes(SVG_RAW)
        # The SVG file should have been neutered
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', demo_user.partner_id._name),
            ('res_field', '=', 'image_1920'),
            ('res_id', '=', demo_user.partner_id.id),
        ])
        self.assertEqual(attachment.mimetype, 'text/plain')

    def test_94_image(self):
        f = io.BytesIO()
        Image.new('RGB', (4000, 2000), '#4169E1').save(f, 'PNG')
        f.seek(0)
        image_w = BinaryBytes(f.read())

        f = io.BytesIO()
        Image.new('RGB', (2000, 4000), '#4169E1').save(f, 'PNG')
        f.seek(0)
        image_h = BinaryBytes(f.read())

        def assertResized(record, **sizes):
            for field_name, size in sizes.items():
                self.assertEqual(binary_to_image(record[field_name]).size, size, f"Image {field_name} incorrectly sized")

        record = self.env['test_orm.model_image'].create({
            'name': 'image',
            'image': image_w,
            'image_128': image_w,
        })

        # test create (no resize)
        self.assertEqual(record.image.content, image_w.content)
        # test create (resize)
        # 64: related stored on column
        # 128: store
        # 256: related no store
        # 512: related store
        assertResized(record, image_64=(64, 32), image_128=(128, 64), image_256=(256, 128), image_512=(512, 256))

        record.write({
            'image': image_h,
            'image_128': image_h,
        })

        # test write (no resize)
        self.assertEqual(record.image.content, image_h.content)
        assertResized(record, image_64=(32, 64), image_128=(64, 128), image_256=(128, 256), image_512=(256, 512))

        record = self.env['test_orm.model_image'].create({
            'name': 'image',
            'image': image_h,
            'image_128': image_h,
        })

        # test create (no resize)
        self.assertEqual(record.image.content, image_h.content)
        assertResized(record, image_64=(32, 64), image_128=(64, 128), image_256=(128, 256), image_512=(256, 512))

        record.write({
            'image': image_w,
            'image_128': image_w,
        })

        # test write (no resize)
        self.assertEqual(record.image.content, image_w.content)
        assertResized(record, image_64=(64, 32), image_128=(128, 64), image_256=(256, 128), image_512=(512, 256))

        # test create inverse store
        record = self.env['test_orm.model_image'].create({
            'name': 'image',
            'image_512': image_w,
        })
        assertResized(record, image_512=(512, 256), image=(4000, 2000), image_256=(256, 128), image_64=(64, 32))
        # test write inverse store
        record.write({
            'image_512': image_h,
        })
        assertResized(record, image_512=(256, 512), image=(2000, 4000), image_256=(128, 256), image_64=(32, 64))

        # test create inverse no store
        record = self.env['test_orm.model_image'].with_context(image_no_postprocess=True).create({
            'name': 'image',
            'image_256': image_w,
        })
        assertResized(record, image_512=(512, 256), image=(4000, 2000), image_256=(256, 128), image_64=(64, 32))
        # test write inverse no store
        record.write({
            'image_256': image_h,
        })
        assertResized(record, image_512=(256, 512), image=(2000, 4000), image_256=(128, 256), image_64=(32, 64))

        # test create inverse stored column
        record = self.env['test_orm.model_image'].with_context(image_no_postprocess=True).create({
            'name': 'image',
            'image_64': image_w,
        })
        assertResized(record, image_512=(512, 256), image=(4000, 2000), image_256=(256, 128), image_64=(64, 32))
        # test write inverse stored column
        record.write({
            'image_64': image_h,
        })
        assertResized(record, image_512=(256, 512), image=(2000, 4000), image_256=(128, 256), image_64=(32, 64))

        # test bin_size
        record.invalidate_recordset()
        values_bin_size = record.with_context(bin_size=True).read([])[0]
        self.assertEqual(values_bin_size.get('image'), '31.54 Kb')
        self.assertEqual(values_bin_size.get('image_512'), '1.02 Kb')
        self.assertEqual(values_bin_size.get('image_256'), '424.00 bytes')
        self.assertEqual(values_bin_size.get('image_64'), '111.00 bytes')

        # ensure image_data_uri works (value must be bytes and not string)
        self.assertEqual(record.image_256.to_base64()[:8], 'iVBORw0K')
        self.assertEqual(image_data_uri(record.image_256)[:30], 'data:image/png;base64,iVBORw0K')

        # ensure invalid image raises
        with self.assertRaises(UserError):
            record.write({
                'image': BinaryBytes(b'invalid image'),
            })

        # assignment of invalid image on new record does nothing, the value is
        # taken from origin instead (use-case: onchange)
        new_record = record.new(origin=record)
        with mute_logger('odoo.fields'):
            new_record.image = '31.54 Kb'
        self.assertEqual(record.image.content, image_h.content)
        self.assertEqual(new_record.image.content, image_h.content)

        # assignment to new record with origin should not do any query
        with self.assertQueryCount(0):
            new_record.image = image_w
