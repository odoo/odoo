from functools import partial
from pathlib import Path

from PIL import Image

from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import frozendict
from odoo.tools.image import hex_to_rgb, image_to_base64

dir_path = Path(__file__).parent
_file_cache = {}


@tagged("web_unit", "web_layout")
class TestBaseDocumentLayoutHelpers(TransactionCase):
    def setUp(self):
        super().setUp()
        self.color_fields = ["primary_color", "secondary_color"]
        self.company = self.env.company
        self.css_color_error = 0
        self._set_templates_and_layouts()
        self._set_images()

    def _write_layout(self, vals):
        config_fields = self.company.report_config_id._fields
        config_vals = {
            k: v for k, v in vals.items() if k in config_fields and k != "company_id"
        }
        company_vals = {k: v for k, v in vals.items() if k not in config_vals}
        if company_vals:
            self.company.write(company_vals)
        if config_vals:
            self.company.report_config_id.write(config_vals)

    def assertColors(self, checked_obj, expected):
        if getattr(expected, "_name", None) == "res.company":
            expected = expected.report_config_id
        _expected_getter = (
            expected.get if isinstance(expected, dict) else partial(getattr, expected)
        )
        for fname in self.color_fields:
            color1 = getattr(checked_obj, fname)
            color2 = _expected_getter(fname)
            if self.css_color_error:
                self._compare_colors_rgb(color1, color2)
            else:
                self.assertEqual(color1, color2)

    def _compare_colors_rgb(self, color1, color2):
        self.assertEqual(bool(color1), bool(color2))
        if not color1:
            return
        color1 = hex_to_rgb(color1)
        color2 = hex_to_rgb(color2)
        self.assertEqual(len(color1), len(color2))
        for c1, c2 in zip(color1, color2, strict=True):
            self.assertAlmostEqual(c1, c2, delta=self.css_color_error)

    def _get_images_for_test(self):
        return ["sweden.png", "odoo.png"]

    def _set_images(self):
        for fname in self._get_images_for_test():
            fname_split = fname.split(".")
            if fname_split[0] not in _file_cache:
                with Image.open(dir_path / fname, "r") as img:
                    base64_img = image_to_base64(img, "PNG")
                    primary, secondary = self.env[
                        "base.document.layout"
                    ].extract_image_primary_secondary_colors(base64_img)
                    _img = frozendict(
                        {
                            "img": base64_img,
                            "colors": {
                                "primary_color": primary,
                                "secondary_color": secondary,
                            },
                        }
                    )
                    _file_cache[fname_split[0]] = _img
        self.company_imgs = frozendict(_file_cache)

    def _set_templates_and_layouts(self):
        self.layout_template1 = self.env["ir.ui.view"].create(
            {
                "name": "layout_template1",
                "key": "web.layout_template1",
                "type": "qweb",
                "arch": """<div></div>""",
            }
        )
        self.env["ir.model.data"].create(
            {
                "name": self.layout_template1.name,
                "model": "ir.ui.view",
                "module": "web",
                "res_id": self.layout_template1.id,
            }
        )
        self.default_colors = {
            "primary_color": "#000000",
            "secondary_color": "#000000",
        }
        self.report_layout1 = self.env["report.layout"].create(
            {
                "view_id": self.layout_template1.id,
                "name": "report_%s" % self.layout_template1.name,
            }
        )
        self.layout_template2 = self.env["ir.ui.view"].create(
            {
                "name": "layout_template2",
                "key": "web.layout_template2",
                "type": "qweb",
                "arch": """<div></div>""",
            }
        )
        self.env["ir.model.data"].create(
            {
                "name": self.layout_template2.name,
                "model": "ir.ui.view",
                "module": "web",
                "res_id": self.layout_template2.id,
            }
        )
        self.report_layout2 = self.env["report.layout"].create(
            {
                "view_id": self.layout_template2.id,
                "name": "report_%s" % self.layout_template2.name,
            }
        )


@tagged("document_layout", "post_install", "-at_install", "web_unit", "web_layout")
class TestBaseDocumentLayout(TestBaseDocumentLayoutHelpers):
    def test_company_no_color_change_logo(self):
        self._write_layout(
            {
                "primary_color": False,
                "secondary_color": False,
                "image_1920": False,
                "external_report_layout_id": self.env.ref("web.layout_template1").id,
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )
        default_colors = self.default_colors
        with Form(self.env["base.document.layout"]) as doc_layout:
            self.assertColors(doc_layout, default_colors)
            self.assertEqual(doc_layout.company_id, self.company)
            doc_layout.image_1920 = self.company_imgs["sweden"]["img"]

            self.assertColors(doc_layout, self.company_imgs["sweden"]["colors"])

            doc_layout.image_1920 = ""
            self.assertColors(doc_layout, self.company_imgs["sweden"]["colors"])
            self.assertEqual(doc_layout.image_1920, "")

    def test_company_no_color_but_logo_change_logo(self):
        self._write_layout(
            {
                "primary_color": "#ff0080",
                "secondary_color": "#00ff00",
                "image_1920": self.company_imgs["sweden"]["img"],
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )

        with Form(self.env["base.document.layout"]) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.image_1920 = self.company_imgs["odoo"]["img"]
            self.assertColors(doc_layout, self.company_imgs["odoo"]["colors"])

    def test_company_colors_change_logo(self):
        self._write_layout(
            {
                "primary_color": "#ff0080",
                "secondary_color": "#00ff00",
                "image_1920": False,
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )

        with Form(self.env["base.document.layout"]) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.image_1920 = self.company_imgs["odoo"]["img"]
            self.assertColors(doc_layout, self.company_imgs["odoo"]["colors"])

    def test_company_colors_and_logo_change_logo(self):
        self._write_layout(
            {
                "primary_color": "#ff0080",
                "secondary_color": "#00ff00",
                "image_1920": self.company_imgs["sweden"]["img"],
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )

        with Form(self.env["base.document.layout"]) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.image_1920 = self.company_imgs["odoo"]["img"]
            self.assertColors(doc_layout, self.company_imgs["odoo"]["colors"])

    def test_company_colors_reset_colors(self):
        self._write_layout(
            {
                "primary_color": "#ff0080",
                "secondary_color": "#00ff00",
                "image_1920": self.company_imgs["sweden"]["img"],
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )

        with Form(self.env["base.document.layout"]) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.primary_color = doc_layout.logo_primary_color
            doc_layout.secondary_color = doc_layout.logo_secondary_color
            self.assertColors(doc_layout, self.company_imgs["sweden"]["colors"])

    def test_parse_company_colors_grayscale(self):
        self._write_layout(
            {
                "primary_color": "#ff0080",
                "secondary_color": "#00ff00",
                "paperformat_id": self.env.ref("base.paperformat_us").id,
            }
        )
        with Form(self.env["base.document.layout"]) as doc_layout:
            with Image.open(dir_path / "logo_ci.png", "r") as img:
                base64_img = image_to_base64(img, "PNG")
                doc_layout.image_1920 = base64_img
            self.assertNotEqual(None, doc_layout.primary_color)

    def test_company_details_blank_lines(self):
        doc_layout_1 = self.env["base.document.layout"].create(
            {"company_id": self.company.id}
        )
        self.assertNotIn("\n<br>\n", doc_layout_1.company_details)

        self._write_layout({"street2": "street_2_detail"})
        doc_layout_2 = self.env["base.document.layout"].create(
            {"company_id": self.company.id}
        )
        self.assertIn("street_2_detail", doc_layout_2.company_details)

    def test_clean_address_format_removes_trailing_placeholder(self):
        doc_layout = self.env["base.document.layout"]
        company_data = {"street": "123 Main St", "city": "Springfield", "zip": False}

        result = doc_layout._clean_address_format(
            "%(street)s\n%(city)s %(zip)s", company_data
        )
        self.assertNotIn("%(zip)s", result, "Trailing placeholder must be stripped")
        rendered = result % {k: (v or "") for k, v in company_data.items()}
        self.assertNotIn(
            "False",
            rendered,
            "Rendered address must not contain literal 'False'",
        )

    def test_clean_address_format_removes_mid_format_placeholder(self):
        doc_layout = self.env["base.document.layout"]
        company_data = {"city": "Springfield", "state_id": False, "zip": "12345"}

        result = doc_layout._clean_address_format(
            "%(city)s %(state_id)s\n%(zip)s", company_data
        )
        self.assertNotIn(
            "%(state_id)s", result, "Mid-format placeholder must be stripped"
        )
        self.assertIn("12345", result % {k: (v or "") for k, v in company_data.items()})

    def test_extract_colors_tolerates_non_text_logo(self):
        layout = self.env["base.document.layout"]
        self.assertEqual(
            layout.extract_image_primary_secondary_colors(memoryview(b"abc")),
            (False, False),
        )
        self.assertEqual(
            layout.extract_image_primary_secondary_colors(b"@@@not-an-image@@@"),
            (False, False),
        )
        self.assertEqual(
            layout.extract_image_primary_secondary_colors(False), (False, False)
        )
