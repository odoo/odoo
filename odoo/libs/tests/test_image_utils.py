import base64
import io
import struct
import unittest
import zlib
from unittest import mock

from PIL import Image

from odoo.libs.image.utils import (
    IMAGE_MAX_RESOLUTION,
    ImageDecodeError,
    ImageProcess,
    ImageTooLargeError,
    average_dominant_color,
    base64_to_image,
    binary_to_image,
    image_process,
    is_image_size_above,
)

SVG = b"<svg xmlns='http://www.w3.org/2000/svg'><rect width='1' height='1'/></svg>"

TRUNCATED_WEBP = b"RIFF" + b"\x00" * 4 + b"WEBPVP8 " + b"\x00" * 20


def _encode(fmt: str, size: tuple[int, int] = (8, 6), **kw) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(stream, fmt, **kw)
    return stream.getvalue()


def _encode_animated(
    fmt: str, size: tuple[int, int] = (8, 6), frames: int = 3
) -> bytes:
    stream = io.BytesIO()
    images = [Image.new("RGB", size, (i * 40, 0, 0)) for i in range(frames)]
    images[0].save(stream, fmt, save_all=True, append_images=images[1:], duration=100)
    return stream.getvalue()


class TestOriginalFormatAlwaysDefined(unittest.TestCase):
    def test_empty_source(self):
        self.assertEqual(ImageProcess(b"").original_format, "")

    def test_falsy_source(self):
        self.assertEqual(ImageProcess(None).original_format, "")

    def test_svg_source(self):
        self.assertEqual(ImageProcess(SVG).original_format, "")

    def test_webp_source(self):
        self.assertEqual(ImageProcess(_encode("WEBP")).original_format, "WEBP")

    def test_a_truncated_webp_is_a_decode_error_not_a_passthrough(self):
        with self.assertRaises(ImageDecodeError):
            ImageProcess(TRUNCATED_WEBP)


class TestImageTooLarge(unittest.TestCase):
    def _oversized_image(self):
        side = int(IMAGE_MAX_RESOLUTION**0.5) + 1000
        return mock.Mock(spec=["size"], size=(side, side))

    def test_verify_resolution_true_raises_on_oversized_image(self):
        with mock.patch(
            "odoo.libs.image.utils.binary_to_image",
            return_value=self._oversized_image(),
        ):
            with self.assertRaises(ImageTooLargeError):
                ImageProcess(b"\x89PNG", verify_resolution=True)


class TestWebpIsProcessedLikeAnyOtherRaster(unittest.TestCase):
    def test_resize_actually_resizes(self):
        source = _encode("WEBP", (200, 100))
        out = ImageProcess(source).resize(50, 50).image_quality()
        self.assertNotEqual(out, source)
        assert out is not False, "the resize produced no image"
        self.assertEqual(Image.open(io.BytesIO(out)).size, (50, 25))

    def test_the_format_is_preserved_rather_than_transcoded_to_jpeg(self):
        out = ImageProcess(_encode("WEBP", (40, 40))).resize(20, 20).image_quality()
        assert out is not False, "the resize produced no image"
        self.assertEqual(Image.open(io.BytesIO(out)).format, "WEBP")

    def test_an_untouched_webp_is_still_returned_byte_identical(self):
        source = _encode("WEBP", (40, 40))
        self.assertEqual(ImageProcess(source).image_quality(), source)

    def test_an_animated_webp_keeps_its_frames_through_a_resize(self):
        source = _encode_animated("WEBP", (40, 40), frames=3)
        processed = ImageProcess(source)
        self.assertTrue(processed.animated)
        out = processed.resize(20, 20).image_quality()
        assert out is not False, "the resize produced no image"
        reloaded = Image.open(io.BytesIO(out))
        self.assertEqual(reloaded.n_frames, 3)
        self.assertEqual(reloaded.size, (20, 20))

    def test_an_animated_gif_still_keeps_its_frames(self):
        source = _encode_animated("GIF", (40, 40), frames=3)
        out = ImageProcess(source).resize(20, 20).image_quality()
        assert out is not False, "the resize produced no image"
        self.assertEqual(Image.open(io.BytesIO(out)).n_frames, 3)

    def test_a_format_outside_preinit_is_decodable_again(self):
        self.assertEqual(ImageProcess(_encode("TIFF")).original_format, "TIFF")

    def test_svg_passthrough_still_works(self):
        self.assertEqual(ImageProcess(SVG).image_quality(), SVG)

    def test_chaining_on_svg_is_a_noop(self):
        processed = ImageProcess(SVG).resize(64, 64).image_quality()
        self.assertEqual(processed, SVG)


class TestAverageDominantColorDegenerateInput(unittest.TestCase):
    def test_empty_list(self):
        with self.assertRaises(ValueError) as ctx:
            average_dominant_color([])
        self.assertIn("non-empty", str(ctx.exception))

    def test_all_zero_counts(self):
        with self.assertRaises(ValueError) as ctx:
            average_dominant_color([(0, (1, 2, 3, 255))])
        self.assertIn("non-zero count", str(ctx.exception))

    def test_feedback_loop_shape(self):
        colors = [(10, (255, 0, 0, 255)), (5, (0, 0, 255, 255))]
        primary, remaining = average_dominant_color(colors)
        self.assertEqual(len(primary), 3)
        while remaining:
            _next_color, remaining = average_dominant_color(remaining)


class TestAverageDominantColorStillCorrect(unittest.TestCase):
    def test_single_color(self):
        self.assertEqual(
            average_dominant_color([(5, (10, 20, 30, 255))]), ((10, 20, 30), [])
        )

    def test_similar_colors_grouped(self):
        primary, remaining = average_dominant_color(
            [(100, (10, 10, 10, 255)), (1, (250, 250, 250, 255))]
        )
        self.assertEqual(remaining, [(1, (250, 250, 250, 255))])
        self.assertEqual(primary, (10, 10, 10))

    def test_mitigate_caps_brightness(self):
        primary, _ = average_dominant_color([(1, (255, 255, 255, 255))], mitigate=175)
        self.assertTrue(all(band <= 175 for band in primary))


def _png(mode: str, size: tuple[int, int] = (4, 4), color=(1, 2, 3)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color if mode in ("RGB", "RGBA") else 128).save(
        buf, format="PNG"
    )
    return buf.getvalue()


class TestColorizeAcceptsEveryMode(unittest.TestCase):
    def test_every_mode_survives(self):
        for mode in ("RGB", "RGBA", "L", "P", "1"):
            with self.subTest(mode=mode):
                processed = ImageProcess(_png(mode)).colorize((10, 20, 30))
                image = processed.image
                assert image is not False, "a PNG must decode"
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(processed.operations_count, 1)

    def test_a_transparent_pixel_still_shows_the_fill(self):
        buf = io.BytesIO()
        Image.new("RGBA", (2, 2), (255, 0, 0, 0)).save(buf, format="PNG")
        image = ImageProcess(buf.getvalue()).colorize((7, 8, 9)).image
        assert image is not False, "a PNG must decode"
        self.assertEqual(image.getpixel((0, 0)), (7, 8, 9))

    def test_an_opaque_pixel_still_covers_the_fill(self):
        buf = io.BytesIO()
        Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(buf, format="PNG")
        image = ImageProcess(buf.getvalue()).colorize((7, 8, 9)).image
        assert image is not False, "a PNG must decode"
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))


def _png_header(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b""))
        + chunk(b"IEND", b"")
    )


def _with_orientation(orientation: int, size: tuple[int, int] = (8, 6)) -> bytes:
    exif = Image.Exif()
    exif[0x112] = orientation
    return _encode("JPEG", size, exif=exif.tobytes())


class TestResizeToOneSide(unittest.TestCase):
    def test_a_thin_image_asked_for_a_height_keeps_one_column(self):
        thin = _encode("PNG", (4, 1000))
        resized = binary_to_image(image_process(thin, size=(0, 128)))
        self.assertEqual(resized.size, (1, 128))

    def test_a_flat_image_asked_for_a_width_keeps_one_row(self):
        flat = _encode("PNG", (1000, 4))
        for crop in (None, "center"):
            with self.subTest(crop=crop):
                resized = binary_to_image(image_process(flat, size=(128, 0), crop=crop))
                self.assertEqual(resized.size, (128, 1))


class TestPillowFailuresAreImageErrors(unittest.TestCase):
    def test_a_decompression_bomb_is_too_large_not_a_pillow_error(self):
        bomb = _png_header(20000, 10000)
        with self.assertRaises(ImageTooLargeError):
            binary_to_image(bomb)
        with self.assertRaises(ImageTooLargeError):
            ImageProcess(bomb, verify_resolution=False)

    def test_a_truncated_image_is_a_decode_error_not_an_oserror(self):
        for fmt in ("JPEG", "PNG"):
            with self.subTest(fmt=fmt):
                truncated = _encode(fmt, (64, 64))[:-40]
                with self.assertRaises(ImageDecodeError):
                    ImageProcess(truncated)


class TestOrientation(unittest.TestCase):
    def test_an_upright_image_is_not_copied_to_be_transposed(self):
        with mock.patch(
            "odoo.libs.image.utils.image_fix_orientation"
        ) as fix_orientation:
            ImageProcess(_with_orientation(1))
            ImageProcess(_encode("JPEG"))
        fix_orientation.assert_not_called()

    def test_a_rotated_image_is_still_turned_upright(self):
        self.assertEqual(ImageProcess(_with_orientation(6)).image.size, (6, 8))
        self.assertEqual(ImageProcess(_with_orientation(3)).image.size, (8, 6))


class TestDecodeFailuresShareOneError(unittest.TestCase):
    def test_binary_to_image(self):
        with self.assertRaises(ImageDecodeError):
            binary_to_image(b"not an image")

    def test_base64_to_image_with_undecodable_image(self):
        with self.assertRaises(ImageDecodeError):
            base64_to_image(base64.b64encode(b"nope"))

    def test_base64_to_image_with_malformed_base64(self):
        with self.assertRaises(ImageDecodeError):
            base64_to_image("!!!not base64!!!")

    def test_image_process_constructor(self):
        with self.assertRaises(ImageDecodeError):
            ImageProcess(b"not an image")


class TestIsImageSizeAbove(unittest.TestCase):
    def test_compares_dimensions(self):
        big, small = (
            base64.b64encode(_png("RGB", (8, 8))),
            base64.b64encode(_png("RGB", (4, 4))),
        )
        self.assertTrue(is_image_size_above(big, small))
        self.assertFalse(is_image_size_above(small, big))
        self.assertFalse(is_image_size_above(big, big))

    def test_svg_and_falsy_sources_are_never_above(self):
        png = base64.b64encode(_png("RGB"))
        self.assertFalse(is_image_size_above(b"P...", png))
        self.assertFalse(is_image_size_above(png, b"P..."))
        self.assertFalse(is_image_size_above(None, png))
        self.assertFalse(is_image_size_above(png, b""))


if __name__ == "__main__":
    unittest.main()


class TestHighBitDepthImages(unittest.TestCase):
    def test_a_16_bit_grayscale_png_resizes_to_any_target(self):
        for mode in ("I;16", "I"):
            for size in ((300, 200), (3, 900), (900, 3)):
                source = io.BytesIO()
                Image.new(mode, size).save(source, "PNG")
                for target in ((128, 128), (0, 64), (64, 0)):
                    with self.subTest(mode=mode, size=size, target=target):
                        self.assertTrue(image_process(source.getvalue(), size=target))
