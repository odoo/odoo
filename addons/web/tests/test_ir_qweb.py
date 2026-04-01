import base64
from lxml import etree

from odoo.tests.common import TransactionCase
from odoo.tools.mimetypes import guess_mimetype

class TestIrQweb(TransactionCase):
    def test_image_field(self):
        view = self.env["ir.ui.view"].create({
            "key": "web.test_qweb",
            "type": "qweb",
            "arch": """<t t-name="test_qweb">
                <span t-field="record.avatar_128" t-options-widget="'image'" t-options-qweb_img_raw_data="is_raw_image" />
            </t>"""
        })
        partner = self.env["res.partner"].create({
            "name": "test image partner",
            "image_1920": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII=",
        })

        html = view._render_template(view.id, {"is_raw_image": True, "record": partner})
        tree = etree.fromstring(html)
        img = tree.find("img")
        self.assertTrue(img.get("src").startswith("data:image/png;base64"))
        self.assertEqual(img.get("class"), "img img-fluid")
        self.assertEqual(img.get("alt"), "test image partner")

        html = view._render_template(view.id, {"is_raw_image": False, "record": partner})
        tree = etree.fromstring(html)
        img = tree.find("img")
        self.assertTrue(img.get("src").startswith("/web/image"))
        self.assertEqual(img.get("class"), "img img-fluid")
        self.assertEqual(img.get("alt"), "test image partner")

    def test_image_field_webp(self):
        webp = "UklGRsCpAQBXRUJQVlA4WAoAAAAQAAAAGAQA/wMAQUxQSMywAAAdNANp22T779/0RUREkvqLOTPesG1T21jatpLTSbpXQzTMEw3zWMM81jCPnWG2fTM7vpndvpkd38y2758Y+6a/Ld/Mt3zzT/XwzCKlV0Ooo61UpZIsKLjKc98R"
        webp_decoded = base64.b64decode(webp)
        self.assertEqual(guess_mimetype(webp_decoded), "image/webp")

        view = self.env["ir.ui.view"].create({
            "key": "web.test_qweb",
            "type": "qweb",
            "arch": """<t t-name="test_qweb">
                <span t-field="record.flag_image" t-options-widget="'image'" t-options-qweb_img_raw_data="is_raw_image" />
            </t>"""
        })
        lang_record = self.env["res.lang"].create({
            "name": "test lang",
            "flag_image": webp,
            "code": "TEST"
        })
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "res.lang"),
            ("res_id", '=', lang_record.id),
            ("res_field", "=", "flag_image")
        ])

        jpeg_attach = self.env["ir.attachment"].create({
            "name": "webpcopy.jpg",
            "res_model": "ir.attachment",
            "res_id": attachment.id,
            "datas": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII="
        })
        jpeg_datas = jpeg_attach.datas

        html = view.with_context(webp_as_jpg=False)._render_template(view.id, {"is_raw_image": True, "record": lang_record})
        tree = etree.fromstring(html)
        img = tree.find("img")
        self.assertEqual(img.get("src"), "data:image/webp;base64,%s" % webp)

        html = view.with_context(webp_as_jpg=True)._render_template(view.id, {"is_raw_image": True, "record": lang_record})
        tree = etree.fromstring(html)
        img = tree.find("img")
        self.assertEqual(img.get("src"), "data:image/png;base64,%s" % jpeg_datas.decode())

    def test_image_svg(self):
        image = """<?xml version='1.0' encoding='UTF-8' ?>
        <svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>
            <rect fill='#ff0000' height='180' width='180'/>
            <text fill='#ffffff' font-size='96' text-anchor='middle' x='90' y='125' font-family='sans-serif'>H</text>
        </svg>"""

        b64_image = base64.b64encode(image.encode()).decode()
        view = self.env["ir.ui.view"].create({
            "key": "web.test_qweb",
            "type": "qweb",
            "arch": """<t t-name="test_qweb">
                <span t-field="record.flag_image" t-options-widget="'image'" t-options-qweb_img_raw_data="True" />
            </t>"""
        })
        partner = self.env["res.lang"].create({
            "name": "test image partner",
            "flag_image": b64_image,
            "code": "TEST"
        })

        html = view._render_template(view.id, {"record": partner})
        tree = etree.fromstring(html)
        img = tree.find("img")
        self.assertEqual(img.get("src"), f"data:image/svg+xml;base64,{b64_image}")
        self.assertEqual(img.get("class"), "img img-fluid")
        self.assertEqual(img.get("alt"), "test image partner")
