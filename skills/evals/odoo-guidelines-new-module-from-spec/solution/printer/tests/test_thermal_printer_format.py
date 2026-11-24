import base64
from io import BytesIO
from PIL import Image
from xml.etree import ElementTree as ET

from odoo.tests import TransactionCase
from odoo.addons.printer.models.ir_actions_report import thermal_printer_format


def make_image_bytes(width: int, height: int, mode: str = "RGB") -> bytes:
    """Return raw PNG bytes for a solid gray image of the given size."""
    img = Image.new(mode, (width, height), color=128)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestThermalPrinterFormat(TransactionCase):
    def test_returns_bytes(self):
        result = thermal_printer_format(make_image_bytes(100, 200))
        self.assertIsInstance(result, bytes, "Expected bytes output")

    def test_output_is_valid_xml(self):
        result = thermal_printer_format(make_image_bytes(100, 200))
        try:
            ET.fromstring(result.decode())
        except ET.ParseError as e:
            self.fail(f"Output is not valid XML: {e}")

    def test_output_width_is_576(self):
        result = thermal_printer_format(make_image_bytes(100, 200)).decode()
        self.assertIn('width="576"', result, "Image width should always be 576 to fit printer paper")

    def test_aspect_ratio_preserved(self):
        original_w, original_h = 100, 200  # 1:2 ratio
        result = thermal_printer_format(make_image_bytes(original_w, original_h)).decode()
        expected_height = int(original_h * (576 / original_w))
        self.assertIn(f'height="{expected_height}"', result,
                      f"Expected height {expected_height} to preserve aspect ratio")

    def test_landscape_image_is_rotated(self):
        # 400 wide x 100 tall → after 90° rotation: 100 wide x 400 tall
        result = thermal_printer_format(make_image_bytes(400, 100)).decode()
        expected_height = int(400 * (576 / 100))
        self.assertIn(f'height="{expected_height}"', result,
                      "Landscape image should be rotated to portrait before scaling")

    def test_portrait_image_not_rotated(self):
        result = thermal_printer_format(make_image_bytes(100, 400)).decode()
        expected_height = int(400 * (576 / 100))
        self.assertIn(f'height="{expected_height}"', result, "Portrait image should not be rotated")

    def test_square_image_not_rotated(self):
        result = thermal_printer_format(make_image_bytes(200, 200)).decode()
        self.assertIn('height="576"', result, "Square image should not be rotated")

    def test_base64_payload_is_valid(self):
        result = thermal_printer_format(make_image_bytes(100, 200)).decode()
        start = result.index('align="center">') + len('align="center">')
        end = result.index("</image>")
        try:
            base64.b64decode(result[start:end])
        except Exception as e:  # noqa: BLE001
            self.fail(f"Image payload is not valid base64: {e}")

    def test_contains_cut_element(self):
        result = thermal_printer_format(make_image_bytes(100, 200)).decode()
        self.assertIn('<cut type="feed"', result, "Missing paper cut command")

    def test_accepts_grayscale_input(self):
        try:
            result = thermal_printer_format(make_image_bytes(100, 200, mode="L"))
            self.assertIsInstance(result, bytes, "Expected bytes output for grayscale input")
        except Exception as e:  # noqa: BLE001
            self.fail(f"Failed to process grayscale image: {e}")

    def test_accepts_rgba_input(self):
        try:
            result = thermal_printer_format(make_image_bytes(100, 200, mode="RGBA"))
            self.assertIsInstance(result, bytes, "Expected bytes output for RGBA input")
        except Exception as e:  # noqa: BLE001
            self.fail(f"Failed to process RGBA image: {e}")
