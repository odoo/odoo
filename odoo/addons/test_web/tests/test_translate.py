from odoo.tools import xml_translate, SQL
from odoo.tests.common import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestTranslation(HttpCase):

    @property
    def backend_url(self):
        return f"/odoo/{self.main_record._name}/{self.main_record.id}"

    def _fetch_raw_values(self, record, fields):
        fields = SQL(", ").join(SQL.identifier(f) for f in fields if f in record._fields)
        table = SQL.identifier(record._table)
        q = SQL("select %(fields)s from %(table)s where id = %(res_id)s", res_id=record.id, fields=fields, table=table)
        self.env.cr.execute(q)
        return self.env.cr.fetchone()

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

        values = {}
        for fname in cls.templates:
            lang_vals = {}
            for lang in langs:
                lang_vals[lang] = cls.templates[fname].format(code=lang)
            values[fname] = lang_vals
        cls.main_record = cls.Model.create(values)

    def test_sanity(self):
        self.assertEqual(self.Model._fields["text"].translate, True)
        self.assertEqual(self.Model._fields["html"].translate, True)
        self.assertEqual(self.Model._fields["xml"].translate, xml_translate)

        record = self.main_record
        fields = ["html", "text", "xml"]
        db_vals = self._fetch_raw_values(record, fields)

        for index, fname in enumerate(fields):
            vals = {lang: self.templates[fname].format(code=lang) for lang in self.langs}
            self.assertEqual(db_vals[index], vals)

    def test_apply_to_all(self):
        with self.with_user("admin"):
            self.env.user.lang = "fr_FR"
        self.start_tour(self.backend_url, "test_web.test_apply_to_all", login="admin")

        db_value = self._fetch_raw_values(self.main_record, ["text"])
        self.assertEqual(db_value[0], {'en_US': 'paul bismuth', 'fr_FR': 'paul bismuth'})

    def test_with_html_editor(self):
        if "html_editor" in self.env["ir.module.module"]._installed():
            self.env.ref("base.user_admin").lang = "fr_FR"
            self.start_tour(self.backend_url, "test_web.test_with_html_editor", login="admin")
            db_value = self._fetch_raw_values(self.main_record, ["html"])
            self.assertEqual(db_value[0], {
                'fr_FR': 'nouvelle valeur',
                'en_US': 'some other relevant value in english',
                'es_ES': '<div><span>es_ES</span><span t-attf-class="some-class" title="es_ES">es_ES</span></div>'
            })
