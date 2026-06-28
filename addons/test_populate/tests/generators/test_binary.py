import io

from PIL import Image as PilImage

from odoo.tests import TransactionCase
from odoo.tools.binary import BinaryBytes

from odoo.addons.populate.generators import Binary, Image


class TestBinaryGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        self.binary_field = self.env['ir.attachment']._fields['raw']

    def test_binary_default_size(self):
        generator = Binary(field=self.binary_field, env=self.env)
        value = generator.next({})

        self.assertIsInstance(value, BinaryBytes)
        self.assertEqual(value.size, 1024)

    def test_binary_custom_size(self):
        generator = Binary(field=self.binary_field, env=self.env, size=512)
        value = generator.next({})

        self.assertIsInstance(value, BinaryBytes)
        self.assertEqual(value.size, 512)

    def test_binary_values_are_random(self):
        generator = Binary(field=self.binary_field, env=self.env)
        values = [generator.next({}) for _ in range(10)]
        raw_values = [bytes(v) for v in values]

        self.assertGreater(len(set(raw_values)), 1)

    def test_binary_null_ratio(self):
        generator = Binary(field=self.binary_field, env=self.env, null_ratio=1.0)
        values = [generator.next({}) for _ in range(20)]

        self.assertTrue(all(v is False for v in values))

    def test_binary_invalid_size_raises(self):
        with self.assertRaises(ValueError):
            Binary(field=self.binary_field, env=self.env, size=0)

        with self.assertRaises(ValueError):
            Binary(field=self.binary_field, env=self.env, size=-10)

    def test_binary_convert_to_kwargs(self):
        attrs = {
            'generator': 'binary.binary',
            'size': '256',
            'null_ratio': '0.1',
        }
        kwargs = Binary.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['size'], 256)
        self.assertIsInstance(kwargs['size'], int)
        self.assertAlmostEqual(kwargs['null_ratio'], 0.1)


class TestImageGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        self.binary_field = self.env['ir.attachment']._fields['raw']

    def test_image_default_dimensions(self):
        generator = Image(field=self.binary_field, env=self.env)
        value = generator.next({})

        self.assertIsInstance(value, BinaryBytes)
        self.assertGreater(value.size, 0)

    def test_image_is_valid_jpeg(self):
        generator = Image(field=self.binary_field, env=self.env)
        value = generator.next({})

        img = PilImage.open(io.BytesIO(bytes(value)))
        self.assertEqual(img.format, 'JPEG')

    def test_image_custom_dimensions(self):
        generator = Image(field=self.binary_field, env=self.env, width=32, height=16)
        value = generator.next({})

        img = PilImage.open(io.BytesIO(bytes(value)))
        self.assertEqual(img.size, (32, 16))

    def test_image_colors_vary(self):
        generator = Image(field=self.binary_field, env=self.env)
        images = [generator.next({}) for _ in range(10)]

        colors = set()
        for val in images:
            img = PilImage.open(io.BytesIO(bytes(val)))
            center = img.getpixel((img.width // 2, img.height // 2))
            colors.add(center)

        self.assertGreater(len(colors), 1)

    def test_image_null_ratio(self):
        generator = Image(field=self.binary_field, env=self.env, null_ratio=1.0)
        values = [generator.next({}) for _ in range(20)]

        self.assertTrue(all(v is False for v in values))

    def test_image_invalid_dimensions_raises(self):
        with self.assertRaises(ValueError) as cm:
            Image(field=self.binary_field, env=self.env, width=0, height=64)
        self.assertIn("positive integers", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Image(field=self.binary_field, env=self.env, width=64, height=-1)
        self.assertIn("positive integers", str(cm.exception))

    def test_image_convert_to_kwargs(self):
        attrs = {
            'generator': 'binary.image',
            'width': '128',
            'height': '256',
            'null_ratio': '0.2',
        }
        kwargs = Image.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['width'], 128)
        self.assertEqual(kwargs['height'], 256)
        self.assertAlmostEqual(kwargs['null_ratio'], 0.2)
