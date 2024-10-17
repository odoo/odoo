# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.translate import _, xml_translate, LazyTranslate

_lt = LazyTranslate(__name__)


class DummyClass:
    def dummy_function(self, term):
        return term


class TestTranslationImportModel1(models.Model):
    _name = 'test.translation.import.model1'
    _description = 'Translation Test 1'

    name = fields.Char('Name', translate=True, help='Help, English')
    selection = fields.Selection([
        ('foo', 'Selection Foo'),
        ('bar', 'Selection Bar'),
    ], export_string_translation=False)
    xml = fields.Text('XML', translate=xml_translate)

    def get_code_translation(self):
        _('slot')  # a code translation for both python and js(static/src/xml/js_template.xml)
        return _('Code, English')

    def get_code_lazy_translation(self):
        return _lt('Code Lazy, English')

    def get_code_placeholder_translation(self, *args, **kwargs):
        return _('Code, %s, English', *args, **kwargs)

    def get_code_named_placeholder_translation(self, *args, **kwargs):
        return _('Code, %(num)s, %(symbol)s, English', *args, **kwargs)

    def test_deeply_nested_translations(self):
        def dummy_function(term):
            return term

        dummy = DummyClass()
        dummy_dict = {
            "dummy_function": dummy_function,
        }

        terms = ["a", "b", "c"]
        term = "term"

        _("PY Export 01 %s", "NO - PY Export 01")
        _("PY Export 02 %(named)s", named="NO - PY Export 02")

        _("PY Export 03 %s", _("PY Export 04 (Nested)"))
        _("PY Export 05 %(named)s", named=_("PY Export 06 (Nested Named)"))

        _("PY Export 07 %s", dummy_function(_("PY Export 08 (Double Nested)")))
        _("PY Export 09 %(named)s", named=dummy_function(_("PY Export 10 (Double Nested Named)")))

        _("PY Export 11 %s", dummy.dummy_function(_("PY Export 12 (Double Nested)")))
        _("PY Export 13 %(named)s", named=dummy.dummy_function(_("PY Export 14 (Double Nested Named)")))

        _("PY Export 15 %s", dummy_dict["a_function"](_("PY Export 16 (Double Nested)")))
        _("PY Export 17 %(named)s", named=dummy_dict["a_function"](_("PY Export 18 (Double Nested Named)")))

        dummy_function(_("PY Export 19 (Base Nested)"))
        dummy.dummy_function(_("PY Export 20 (Base Nested)"))
        dummy_dict["a_function"](_("PY Export 21 (Base Nested)"))

        _("PY Export 22 %s", "NO - PY Export 03" + _("PY Export 23"))
        _("PY Export 24 %s", _("PY Export 25") + "NO - PY Export 04")

        _("PY Export 26 %s", "NO - PY Export 05" + "".join(terms))
        _("PY Export 27 %s", "".join(terms) + "NO - PY Export 06")

        # pylint: disable=E8502
        _(f"PY Export 28")  # noqa: F541, INT001
        # pylint: disable=E8502
        _(f"NO - PY Export 07 {term}")  # noqa: INT001

        # pylint: disable=E8502
        _(dummy_function("NO - PY Export 08"))


class TestTranslationImportModel2(models.Model):
    _name = 'test.translation.import.model2'
    _inherits = {'test.translation.import.model1': 'model1_id'}
    _description = 'Translation Test 2'

    model1_id = fields.Many2one('test.translation.import.model1', required=True, ondelete='cascade')
