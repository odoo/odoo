import codecs
import io
import unittest
import wave

from PIL import Image

from odoo.libs.filesystem.mimetypes import _guess_mimetype_by_signature as signature


class TestWeakSignaturesNeedTheirDiscriminant(unittest.TestCase):
    def test_text_that_opens_like_a_bitmap_or_markup_is_text(self):
        self.assertEqual(signature(b"BMW quarterly report\n"), "text/plain")
        self.assertEqual(signature(b"<3 thanks for everything\n"), "text/plain")

    def test_a_riff_file_that_is_not_webp_is_not_webp(self):
        stream = io.BytesIO()
        with wave.open(stream, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 100)
        self.assertNotEqual(signature(stream.getvalue()), "image/webp")

    def test_real_markup_and_images_keep_their_type(self):
        stream = io.BytesIO()
        Image.new("RGB", (4, 4)).save(stream, "BMP")
        self.assertEqual(signature(stream.getvalue()), "image/bmp")
        self.assertEqual(signature(b"<?xml version='1.0'?><a/>"), "text/xml")
        self.assertEqual(signature(b"<Document xmlns='x'/>"), "text/xml")
        self.assertEqual(signature(b"<!DOCTYPE html><html></html>"), "text/html")

    def test_a_byte_order_mark_does_not_hide_the_type(self):
        svg = codecs.BOM_UTF8 + b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        self.assertEqual(signature(svg), "image/svg+xml")
        self.assertEqual(signature("hello world\n".encode("utf-16")), "text/plain")

    def test_a_truncated_zip_is_unknown_quietly(self):
        with self.assertNoLogs("odoo.libs.filesystem.mimetypes", level="WARNING"):
            self.assertEqual(signature(b"PK\x03\x04truncated"), "application/zip")
