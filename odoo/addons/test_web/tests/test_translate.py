from odoo.tools import xml_translate
from odoo.tests.common import tagged, HttpCase


@tagged("-at_install")
class TestTranslation(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["translatable.cases"]
        langs = ["en_US", "fr_FR", "es_ES"]
        cls.langs = langs
        for lang in langs:
            cls.env["res.lang"]._activate_lang(lang)

        base_xml = ("<div>"
            "<span>{code}</span>"
            """<span t-attf-class="some-class" title="{code}">{code}</span>"""
        "</div>")

        cls.templates = {
            "html": base_xml,
            "text": "{code}",
            "xml": base_xml,
        }

        values = {
            fname: {lang: template.format(code=lang) for lang in langs}
            for fname, template in cls.templates.items()
        }

        cls.main_record = cls.Model.create(values)
        cls.backend_url = f"/odoo/{cls.main_record._name}/{cls.main_record.id}"

    def test_sanity(self):
        self.assertEqual(self.Model._fields["text"].translate, True)
        self.assertEqual(self.Model._fields["html"].translate, True)
        self.assertEqual(self.Model._fields["xml"].translate, xml_translate)

        for field_name in ["html", "text", "xml"]:
            field = self.main_record._fields[field_name]
            self.assertEqual(
                field._get_stored_translations(self.main_record),
                {lang: self.templates[field_name].format(code=lang) for lang in self.langs}
            )

    def test_apply_to_all(self):
        with self.with_user("admin"):
            self.env.user.lang = "fr_FR"
        self.start_tour(self.backend_url, "test_web.test_apply_to_all", login="admin")

        self.assertEqual(
            self.main_record._fields["text"]._get_stored_translations(self.main_record),
            {'en_US': 'paul bismuth', 'fr_FR': 'paul bismuth'}
        )

    def test_with_html_editor(self):
        if "html_editor" not in self.env["ir.module.module"]._installed():
            self.skipTest("translating html field with html editor skipped: html_editor not installed")

        self.env.ref("base.user_admin").lang = "fr_FR"
        self.start_tour(self.backend_url, "test_web.test_with_html_editor", login="admin")
        self.assertEqual(self.main_record._fields["html"]._get_stored_translations(self.main_record), {
            'fr_FR': 'nouvelle valeur',
            'en_US': 'some other relevant value in english',
            'es_ES': '<div><span>es_ES</span><span t-attf-class="some-class" title="es_ES">es_ES</span></div>'
        })
