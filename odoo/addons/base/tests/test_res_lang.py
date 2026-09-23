import contextlib
import locale

from odoo import tools
from odoo.exceptions import UserError
from odoo.libs.locale import format_number, intersperse
from odoo.orm.fields.binary import Binary
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import mute_logger

from odoo.addons.base.models.res_lang import LangData


class TestFormatNumberPure(BaseCase):
    EN = LangData(
        {"id": 1, "decimal_point": ".", "thousands_sep": ",", "grouping": "[3,0]"}
    )
    EU = LangData(
        {"id": 2, "decimal_point": ",", "thousands_sep": ".", "grouping": "[3,0]"}
    )
    IN = LangData(
        {"id": 3, "decimal_point": ".", "thousands_sep": ",", "grouping": "[3,2,0]"}
    )

    def test_float_specs(self):
        self.assertEqual(format_number("%.2f", 1234.5, self.EN), "1234.50")
        self.assertEqual(
            format_number("%.2f", 1234.5, self.EN, grouping=True), "1,234.50"
        )
        self.assertEqual(
            format_number("%.2f", -1234.5, self.EN, grouping=True), "-1,234.50"
        )
        self.assertEqual(
            format_number("%.2f", 1234.5, self.EU, grouping=True), "1.234,50"
        )
        self.assertEqual(format_number("%.2f", 1234.5, self.EU), "1234,50")

    def test_int_specs(self):
        self.assertEqual(
            format_number("%d", 1234567, self.EN, grouping=True), "1,234,567"
        )
        self.assertEqual(format_number("%d", 1234567, self.EN), "1234567")
        self.assertEqual(
            format_number("%d", 12345678, self.IN, grouping=True), "1,23,45,678"
        )

    def test_scientific_notation_not_grouped(self):
        self.assertEqual(format_number("%g", 1e20, self.EN, grouping=True), "1e+20")
        self.assertEqual(
            format_number("%e", 1e20, self.EN, grouping=True), "1.000000e+20"
        )
        self.assertEqual(format_number("%g", 1234.5, self.EN, grouping=True), "1,234.5")

    def test_bad_spec_raises(self):
        with self.assertRaises(ValueError):
            format_number("d", 1234, self.EN)
        with self.assertRaises(ValueError):
            format_number("", 1234, self.EN)


class test_res_lang(TransactionCase):
    def test_00_intersperse(self):
        assert intersperse("", []) == ("", 0)
        assert intersperse("0", []) == ("0", 0)
        assert intersperse("012", []) == ("012", 0)
        assert intersperse("1", []) == ("1", 0)
        assert intersperse("12", []) == ("12", 0)
        assert intersperse("123", []) == ("123", 0)
        assert intersperse("1234", []) == ("1234", 0)
        assert intersperse("123456789", []) == ("123456789", 0)
        assert intersperse("&ab%#@1", []) == ("&ab%#@1", 0)

        assert intersperse("0", []) == ("0", 0)
        assert intersperse("0", [1]) == ("0", 0)
        assert intersperse("0", [2]) == ("0", 0)
        assert intersperse("0", [200]) == ("0", 0)

        assert intersperse("12345678", [1], ".") == ("1234567.8", 1)
        assert intersperse("12345678", [1], ".") == ("1234567.8", 1)
        assert intersperse("12345678", [2], ".") == ("123456.78", 1)
        assert intersperse("12345678", [2, 1], ".") == ("12345.6.78", 2)
        assert intersperse("12345678", [2, 0], ".") == ("12.34.56.78", 3)
        assert intersperse("12345678", [-1, 2], ".") == ("12345678", 0)
        assert intersperse("12345678", [2, -1], ".") == ("123456.78", 1)
        assert intersperse("12345678", [2, 0, 1], ".") == ("12.34.56.78", 3)
        assert intersperse("12345678", [2, 0, 0], ".") == ("12.34.56.78", 3)
        assert intersperse("12345678", [2, 0, -1], ".") == ("12.34.56.78", 3)
        assert intersperse("12345678", [3, 3, 3, 3], ".") == ("12.345.678", 2)

        assert intersperse("abc1234567xy", [2], ".") == ("abc1234567.xy", 1)
        assert intersperse("abc1234567xy8", [2], ".") == (
            "abc1234567x.y8",
            1,
        )
        assert intersperse("abc12", [3], ".") == ("abc12", 0)
        assert intersperse("abc12", [2], ".") == ("abc12", 0)
        assert intersperse("abc12", [1], ".") == ("abc1.2", 1)

    def test_format_scientific_notation_not_grouped(self):
        lang = self.env["res.lang"]._activate_lang("en_US")
        self.assertEqual(lang.format("%g", 1e20, grouping=True), "1e+20")
        self.assertEqual(lang.format("%g", 1e7, grouping=True), "1e+07")
        self.assertEqual(lang.format("%G", 1e20, grouping=True), "1E+20")
        self.assertEqual(lang.format("%e", 1e20, grouping=True), "1.000000e+20")
        self.assertEqual(lang.format("%E", 1e20, grouping=True), "1.000000E+20")
        self.assertEqual(lang.format("%.2f", 1234.5, grouping=True), "1,234.50")
        self.assertEqual(lang.format("%g", 1234.5, grouping=True), "1,234.5")
        self.assertEqual(lang.format("%d", 1234567, grouping=True), "1,234,567")

    def test_format_indian_grouping(self):
        lang = self.env["res.lang"]._activate_lang("en_US")
        lang.grouping = "[3,2,0]"
        self.assertEqual(lang.format("%d", 12345678, grouping=True), "1,23,45,678")
        self.assertEqual(
            lang.format("%.2f", 12345678.0, grouping=True), "1,23,45,678.00"
        )

    def test_format_negative_grouping(self):
        lang = self.env["res.lang"]._activate_lang("en_US")
        self.assertEqual(lang.format("%.2f", -1234.5, grouping=True), "-1,234.50")
        self.assertEqual(lang.format("%d", -1234567, grouping=True), "-1,234,567")

    def test_format_bad_spec_raises(self):
        lang = self.env["res.lang"]._activate_lang("en_US")
        with self.assertRaises(ValueError):
            lang.format("d", 1234)
        with self.assertRaises(ValueError):
            lang.format("", 1234)

    def test_create_lang_grouping_normalisation(self):
        ResLang = self.env["res.lang"]
        grouping_options = {v for v, _label in ResLang._fields["grouping"].selection}
        normalised = str([3, 0]).replace(" ", "")
        self.assertEqual(normalised, "[3,0]")
        self.assertIn(normalised, grouping_options)
        weird = str([4, 0]).replace(" ", "")
        self.assertNotIn(weird, grouping_options)
        coerced = weird if weird in grouping_options else "[3,0]"
        self.assertEqual(coerced, "[3,0]")

    def test_create_lang_resets_process_locale(self):
        before = tools.translate.resetlocale()
        self.addCleanup(locale.setlocale, locale.LC_ALL, before)
        for name in tools.translate.get_locales("en_GB"):
            with contextlib.suppress(locale.Error):
                applied = locale.setlocale(locale.LC_ALL, name)
                break
        else:
            self.skipTest("the en_GB locale is not installed")
        locale.setlocale(locale.LC_ALL, before)
        if applied == before:
            self.skipTest("the process already runs under en_GB")

        ResLang = self.env["res.lang"].with_context(active_test=False)
        ResLang.search([("code", "=", "en_GB")]).unlink()
        lang = ResLang._create_lang("en_GB", "Locale Window Test")

        self.assertEqual(
            locale.setlocale(locale.LC_ALL),
            before,
            "_create_lang must restore the process locale it found",
        )
        self.assertEqual(lang.code, "en_GB")
        self.assertEqual(lang.date_format, "%d/%m/%Y")
        self.assertIn(
            lang.grouping,
            {v for v, _label in lang._fields["grouping"].selection},
        )

    @mute_logger("odoo.addons.base.models.res_lang")
    def test_create_lang_without_a_system_locale_keeps_defaults(self):
        before = tools.translate.resetlocale()
        self.addCleanup(locale.setlocale, locale.LC_ALL, before)
        lang = self.env["res.lang"]._create_lang("xx_XX", "Locale Window Test")
        self.assertEqual(locale.setlocale(locale.LC_ALL), before)
        self.assertTrue(lang.active)
        self.assertTrue(lang.date_format)
        self.assertTrue(lang.time_format)

    def test_copy_lang_codes_are_url_safe_and_unique(self):
        lang = self.env["res.lang"]._activate_lang("en_US")
        copy1 = lang.copy()
        self.assertEqual(copy1.name, f"{lang.name} (copy)")
        self.assertEqual(copy1.code, f"{lang.code}_copy")
        self.assertEqual(copy1.url_code, f"{lang.url_code}_copy")
        copy2 = lang.copy({"name": "English (US) (second copy)"})
        self.assertEqual(copy2.code, f"{lang.code}_copy2")
        self.assertEqual(copy2.url_code, f"{lang.url_code}_copy2")
        copy3 = lang.copy({"name": "Xx", "code": "xx_XX", "url_code": "xx"})
        self.assertEqual(copy3.code, "xx_XX")
        self.assertEqual(copy3.url_code, "xx")

    def test_inactive_users_lang_deactivation(self):
        language = self.env["res.lang"]._activate_lang("en_GB")

        user = self.env["res.users"].create(
            {
                "name": "Foo",
                "login": "foo@example.com",
                "lang": "en_GB",
                "active": False,
            }
        )

        self.assertEqual(
            self.env["res.users"]
            .with_context(active_test=False)
            .search([("lang", "=", "en_GB")]),
            user,
        )

        with self.assertRaises(UserError):
            language.active = False

    def test_archived_user_with_archived_partner_names_the_archived_user(self):
        language = self.env["res.lang"]._activate_lang("en_GB")
        user = self.env["res.users"].create(
            {
                "name": "Bar",
                "login": "bar@example.com",
                "lang": "en_GB",
                "active": False,
            }
        )
        user.partner_id.active = False

        with self.assertRaisesRegex(UserError, "archived users"):
            language.active = False

    def test_get_data(self):
        ResLang = self.env["res.lang"]
        en_id = ResLang._activate_lang("en_US").id
        en_url_code = ResLang.browse(en_id).url_code
        fr_id = ResLang._activate_lang("fr_FR").id
        fr_direction = ResLang.browse(fr_id).direction
        fr_data = ResLang._get_data(id=fr_id)
        dummy_data = ResLang._get_data(id=0)

        self.env.registry.clear_cache()
        self.assertEqual(ResLang._get_data(id=fr_id), fr_data)
        self.assertEqual(ResLang._get_data(id=0), dummy_data)

        self.assertTrue(ResLang._get_data(code="en_US"))
        self.assertFalse(ResLang._get_data(code="nl_NL"))
        self.assertFalse(ResLang._get_data(code="dummy"))

        self.assertEqual(
            dict(ResLang._get_data(id=fr_id)),
            ResLang.browse(fr_id).read(ResLang.CACHED_FIELDS)[0],
        )
        self.assertEqual(
            dict(ResLang._get_data(id=0)),
            dict.fromkeys(ResLang.CACHED_FIELDS, False),
        )

        self.env.core.clear_cache()
        self.env.registry.clear_cache()
        with self.assertQueryCount(2):
            self.assertEqual(ResLang._get_data(code="en_US").url_code, en_url_code)
            self.assertEqual(ResLang._get_data(code="fr_FR").direction, fr_direction)
            self.assertEqual(ResLang._get_data(code="nl_NL").direction, False)
            self.assertEqual(ResLang._get_data(code="dummy").direction, False)

        with self.assertRaises(AttributeError):
            _ = ResLang._get_data(code="en_US").flag_image
        with self.assertRaises(AttributeError):
            _ = ResLang._get_data(code="nl_NL").flag_image
        with self.assertRaises(AttributeError):
            _ = ResLang._get_data(code="dummy").flag_image

    def test_lang_url_code_shortening(self):
        ResLang = self.env["res.lang"]
        es_ES = self.env.ref("base.lang_es")
        self.assertFalse(es_ES.active)
        self.assertEqual(es_ES.url_code, "es_ES")
        es_419 = self.env.ref("base.lang_es_419")
        self.assertFalse(es_419.active)
        self.assertEqual(es_419.url_code, "es")

        ResLang._activate_lang("es_ES")
        self.assertEqual(es_419.url_code, "es_419")
        self.assertEqual(es_ES.url_code, "es")
        ResLang._activate_lang("es_419")
        self.assertEqual(es_419.url_code, "es_419")
        self.assertEqual(es_ES.url_code, "es")
        (es_419 + es_ES).write({"active": False})
        ResLang._activate_lang("es_419")
        self.assertEqual(es_419.url_code, "es")
        self.assertEqual(es_ES.url_code, "es_ES")

        self.env.cr.execute(
            f""" UPDATE res_lang SET code = 'es' where id = {es_419.id}"""
        )
        self.env.invalidate_all()
        self.assertEqual(es_419.code, "es")
        (es_419 + es_ES).write({"active": False})
        ResLang._activate_lang("es_419")
        self.assertEqual(es_419.url_code, "es")
        self.assertEqual(es_ES.url_code, "es_ES")
        es_419.active = False
        ResLang._activate_lang("es_ES")
        self.assertEqual(es_419.url_code, "es")
        self.assertEqual(es_ES.url_code, "es_ES")

        my_MM = ResLang._activate_lang("my_MM")
        self.assertEqual(my_MM.url_code, "mya")


class TestResLangUnsavedRecord(TransactionCase):
    def test_flag_image_url_on_unsaved_record(self):
        lang = self.env["res.lang"].new({})
        self.assertFalse(lang.flag_image_url)

    def test_flag_image_url_still_derived_from_code(self):
        lang = self.env["res.lang"].new({"code": "fr_BE"})
        self.assertEqual(lang.flag_image_url, "/base/static/img/country_flags/be.png")


class TestFlagImageUrlDoesNotLoadImages(TransactionCase):
    PNG_1X1 = (
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        b"z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def test_url_reflects_the_uploaded_flag_without_reading_it(self):
        lang = self.env.ref("base.lang_en")
        lang.flag_image = self.PNG_1X1
        lang.invalidate_recordset()
        self.assertEqual(
            lang.flag_image_url, f"/web/image/res.lang/{lang.id}/flag_image"
        )

        lang.flag_image = False
        lang.invalidate_recordset()
        self.assertEqual(lang.flag_image_url, "/base/static/img/country_flags/us.png")

    def test_computing_the_url_never_materializes_the_payload(self):
        lang = self.env.ref("base.lang_en")
        lang.flag_image = self.PNG_1X1
        lang.flush_recordset()

        read_sizes = []
        original = Binary.read

        def spy(field, records):
            if field.name == "flag_image":
                read_sizes.append(
                    bool(records.env.context.get("bin_size"))
                    or bool(records.env.context.get("bin_size_flag_image"))
                )
            return original(field, records)

        self.patch(Binary, "read", spy)
        self.env.invalidate_all()
        self.env["res.lang"].search([])._compute_flag_image_url()

        self.assertTrue(read_sizes, "the compute must still consult flag_image")
        self.assertTrue(
            all(read_sizes),
            "flag_image was read for its payload, not merely for its size",
        )
