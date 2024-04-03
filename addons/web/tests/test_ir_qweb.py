from lxml import etree
from odoo.tests.common import TransactionCase

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
            "image_128": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII=",
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
