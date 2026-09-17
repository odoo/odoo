import base64
from datetime import date, datetime
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import common, new_test_user
from odoo.tools import NEGATIVE_SIGN_JOINER

from odoo.addons.base.models.ir_qweb import IrQweb as BaseIrQweb
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class TestQwebFieldTime(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.time"].value_to_html(value, options)

    def test_time_value_to_html(self):
        default_fmt = {"format": "h:mm a"}
        self.assertEqual(self.value_to_html(0, default_fmt), "12:00 AM")

        self.assertEqual(self.value_to_html(11.75, default_fmt), "11:45 AM")

        self.assertEqual(self.value_to_html(12, default_fmt), "12:00 PM")

        self.assertEqual(self.value_to_html(14.25, default_fmt), "2:15 PM")

        self.assertEqual(self.value_to_html(15.1, {"format": "HH:mm:SS"}), "15:06:00")

        with self.assertRaises(ValueError):
            self.value_to_html(-6.5)

        with self.assertRaises(ValueError):
            self.value_to_html(24)


class TestQwebFieldInteger(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.integer"].value_to_html(value, options)

    def test_integer_value_to_html(self):
        self.assertEqual(self.value_to_html(1000), "1,000")
        self.assertEqual(
            self.value_to_html(1000000, {"format_decimalized_number": True}),
            "1M",
        )
        self.assertEqual(
            self.value_to_html(
                125125,
                {"format_decimalized_number": True, "precision_digits": 3},
            ),
            "125.125k",
        )


class TestQwebFieldFloatConverter(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.float"].value_to_html(value, options)

    def test_float_value_to_html_no_precision(self):
        self.assertEqual(self.value_to_html(3), "3.0")
        self.assertEqual(self.value_to_html(3.1), "3.1")
        self.assertEqual(self.value_to_html(3.1231239), "3.123124")

    def test_float_value_to_html_with_precision(self):
        options = {"precision": 3}
        self.assertEqual(self.value_to_html(3, options), "3.000")
        self.assertEqual(self.value_to_html(3.1, options), "3.100")
        self.assertEqual(self.value_to_html(3.123, options), "3.123")
        self.assertEqual(self.value_to_html(3.1239, options), "3.124")

    def test_float_value_to_html_with_min_precision(self):
        options = {"min_precision": 3}
        self.assertEqual(self.value_to_html(0, options), "0.000")
        self.assertEqual(self.value_to_html(3, options), "3.000")
        self.assertEqual(self.value_to_html(3.1, options), "3.100")
        self.assertEqual(self.value_to_html(3.123, options), "3.123")
        self.assertEqual(self.value_to_html(3.1239, options), "3.1239")
        self.assertEqual(self.value_to_html(3.1231239, options), "3.123124")
        self.assertEqual(
            self.value_to_html(1234567890.1234567890, options),
            "1,234,567,890.12346",
        )

    def test_float_value_to_html_with_precision_and_min_precision(self):
        options = {"min_precision": 3, "precision": 4}
        self.assertEqual(self.value_to_html(3, options), "3.000")
        self.assertEqual(self.value_to_html(3.1, options), "3.100")
        self.assertEqual(self.value_to_html(3.123, options), "3.123")
        self.assertEqual(self.value_to_html(3.1239, options), "3.1239")
        self.assertEqual(self.value_to_html(3.12349, options), "3.1235")


class TestQwebFieldFloatTime(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.float_time"].value_to_html(value, options or {})

    def test_float_time_value_to_html(self):
        self.assertEqual(self.value_to_html(1.5), "01:30")
        self.assertEqual(self.value_to_html(0), "00:00")
        self.assertEqual(self.value_to_html(2.25), "02:15")
        self.assertEqual(self.value_to_html(-1.5), "-01:30")


class TestQwebFieldDuration(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.duration"].value_to_html(value, options or {})

    def test_duration_digital_positive(self):
        self.assertEqual(
            self.value_to_html(1.5, {"unit": "hour", "digital": True}), "01:30:00"
        )

    def test_duration_digital_round_clamped_to_hour(self):
        self.assertEqual(
            self.value_to_html(1.5, {"unit": "hour", "round": "day", "digital": True}),
            "02",
        )

    def test_duration_textual_formats(self):
        self.assertEqual(self.value_to_html(1.5, {"unit": "hour"}), "1 hour 30 minutes")
        self.assertEqual(
            self.value_to_html(90, {"unit": "minute", "format": "short"}),
            "1 hr 30 min",
        )

    def test_duration_negative_sign_is_glued_to_the_value(self):
        self.assertEqual(
            self.value_to_html(-1.5, {"unit": "hour"}), "-1 hour 30 minutes"
        )
        self.assertEqual(self.value_to_html(-90, {}), "-1 minute 30 seconds")
        self.assertEqual(self.value_to_html(-3661, {}), "-1 hour 1 minute 1 second")

    def test_duration_negative_digital_unchanged(self):
        self.assertEqual(
            self.value_to_html(-1.5, {"unit": "hour", "digital": True}), "-01:30:00"
        )

    def test_duration_rounding_to_zero_renders_empty_not_a_bare_sign(self):
        self.assertEqual(self.value_to_html(-0.0001, {}), "")
        self.assertEqual(self.value_to_html(0, {}), "")


class TestQwebFieldRelative(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.relative"].value_to_html(value, options or {})

    def test_relative_without_now_defaults_to_current_time(self):
        result = self.value_to_html(fields.Datetime.from_string("2000-01-01 00:00:00"))
        self.assertIn("ago", result)

    def test_relative_with_explicit_now(self):
        result = self.value_to_html(
            fields.Datetime.from_string("2020-01-01 00:00:00"),
            {"now": "2020-01-02 00:00:00"},
        )
        self.assertEqual(result, "1 day ago")

    def test_relative_on_date_value(self):
        result = self.value_to_html(date(2000, 1, 1))
        self.assertIn("ago", result)

    def test_relative_record_to_html_date_field(self):
        rate = self.env["res.currency.rate"].create(
            {
                "currency_id": self.env.ref("base.EUR").id,
                "name": "2020-01-01",
                "rate": 1.5,
            }
        )
        result = self.env["ir.qweb.field.relative"].record_to_html(rate, "name", {})
        self.assertIn("ago", result)


class TestQwebFieldRecordContext(common.TransactionCase):
    QWEB_INTERNALS = (
        "__qweb_compiled_cache",
        "__qweb_loaded_codes",
        "__qweb_loaded_options",
        "_qweb_error_path_xml",
    )

    def test_record_to_html_curates_record_context(self):
        partner = self.env["res.partner"].create({"name": "Ctx Probe"})
        Partner = self.registry["res.partner"]
        seen_contexts = []
        orig_compute = Partner._compute_display_name

        def spy(records):
            seen_contexts.append(records.env.context)
            return orig_compute(records)

        converter = self.env["ir.qweb.field"].with_context(
            tz="Pacific/Auckland",
            __qweb_compiled_cache={},
            __qweb_loaded_codes={},
            __qweb_loaded_options={},
            _qweb_error_path_xml=[None, None, None],
        )
        with patch.object(Partner, "_compute_display_name", spy):
            partner.invalidate_recordset(["display_name"])
            result = converter.record_to_html(partner, "display_name", {})
        self.assertEqual(result, "Ctx Probe")
        self.assertTrue(seen_contexts, "the field compute did not run")
        self.assertEqual(seen_contexts[-1].get("tz"), "Pacific/Auckland")
        for context in seen_contexts:
            for key in self.QWEB_INTERNALS:
                self.assertNotIn(key, context)

    def test_record_to_html_skips_rebind_on_matching_context(self):
        partner = self.env["res.partner"].create({"name": "Same Ctx"})
        converter = self.env["ir.qweb.field"]
        with patch.object(
            type(partner), "with_context", side_effect=AssertionError
        ) as rebind:
            result = converter.record_to_html(partner, "name", {})
        self.assertEqual(result, "Same Ctx")
        rebind.assert_not_called()


class TestQwebFieldSelectionRecord(common.TransactionCase):
    def test_selection_record_to_html_label(self):
        partner = self.env["res.partner"].create({"name": "Sel Probe"})
        result = self.env["ir.qweb.field.selection"].record_to_html(partner, "type", {})
        field = partner._fields["type"]
        expected = dict(field.get_description(self.env)["selection"])["contact"]
        self.assertEqual(result, expected)
        self.assertNotEqual(result, "contact", "label, not raw value, expected")


class TestQwebFieldMonetaryType(common.TransactionCase):
    def test_monetary_rejects_bool(self):
        currency = self.env["res.currency"].search([], limit=1)
        with self.assertRaises(TypeError):
            self.env["ir.qweb.field.monetary"].value_to_html(
                True, {"display_currency": currency}
            )


class TestQwebFieldContact(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Wood Corner",
                "email": "wood.corner26@example.com",
                "phone_ids": [Command.create({"number": "(623)-853-7197"})],
                "website": "http://www.wood-corner.com",
            }
        )

    def test_value_to_html_with_website_and_phone(self):
        Contact = self.env["ir.qweb.field.contact"]
        result = Contact.value_to_html(self.partner, {"fields": ["phone", "website"]})
        self.assertIn('itemprop="website"', result)
        self.assertIn(self.partner.website, result)
        self.assertIn('itemprop="telephone"', result)
        self.assertIn(self.partner.phone_ids.number, result)
        self.assertNotIn('itemprop="email"', result)

    def test_value_to_html_without_phone(self):
        Contact = self.env["ir.qweb.field.contact"]
        result = Contact.value_to_html(self.partner, {"fields": ["name", "website"]})
        self.assertIn('itemprop="website"', result)
        self.assertIn(self.partner.website, result)
        self.assertNotIn(self.partner.phone_ids.number, result)
        self.assertIn(
            'itemprop="telephone"',
            result,
            "Empty telephone itemprop should be added to prevent issue with iOS Safari",
        )

    def test_value_to_html_reads_the_phone_only_when_asked(self):
        Contact = self.env["ir.qweb.field.contact"]
        Contact.value_to_html(self.partner, {"fields": ["name", "phone"]})
        counts = {}
        for shown in (["name"], ["name", "phone"]):
            self.env.invalidate_all()
            count0 = self.cr.sql_statement_count
            Contact.value_to_html(self.partner, {"fields": shown})
            counts[len(shown)] = self.cr.sql_statement_count - count0
        self.assertLess(counts[1], counts[2])


class TestQwebFieldOne2Many(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.one2many"].value_to_html(value, options)

    def test_one2many_empty(self):
        partner = self.env["res.partner"].create({"name": "Test Parent"})
        self.assertFalse(self.value_to_html(partner.child_ids))

    def test_one2many_with_values(self):
        parent = self.env["res.partner"].create({"name": "Parent"})
        self.env["res.partner"].create({"name": "Child", "parent_id": parent.id})
        self.assertEqual(self.value_to_html(parent.child_ids), "Parent, Child")

    def test_one2many_drops_a_private_address_the_user_may_not_read(self):
        Partner = self.env["res.partner"]
        subject = Partner.create({"name": "Subject"})
        Partner.create({"name": "Subject Office", "parent_id": subject.id})
        Partner.create(
            {"name": "Subject Home", "type": "private", "parent_id": subject.id}
        )
        user = new_test_user(self.env, "qweb_o2m_reader")
        self.assertEqual(
            self.value_to_html(subject.with_user(user).child_ids),
            "Subject, Subject Office",
        )


class TestQwebFieldMany2Many(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.many2many"].value_to_html(value, options)

    def test_many2many_empty(self):
        user = self.env["res.users"].create(
            {
                "name": "UserTest",
                "login": "usertest@example.com",
                "group_ids": None,
            }
        )
        self.assertFalse(self.value_to_html(user.group_ids))

    def test_many2many_with_values(self):
        groups = self.env["res.groups"].create(
            [{"name": "Zeta Group"}, {"name": "Alpha Group"}]
        )
        self.assertEqual(
            self.value_to_html(groups),
            "Zeta Group, Alpha Group",
        )
        self.assertEqual(
            self.value_to_html(groups.sorted("name")),
            "Alpha Group, Zeta Group",
        )


class TestQwebFieldMany2One(common.TransactionCase):
    def value_to_html(self, value, options=None):
        options = options or {}
        return self.env["ir.qweb.field.many2one"].value_to_html(value, options)

    def test_many2one_empty(self):
        partner = self.env["res.partner"].create({"name": "Lonely"})
        self.assertFalse(self.value_to_html(partner.parent_id))

    def test_many2one_with_value(self):
        parent = self.env["res.partner"].create({"name": "BigBoss"})
        child = self.env["res.partner"].create(
            {"name": "Minion", "parent_id": parent.id}
        )
        self.assertEqual(self.value_to_html(child.parent_id), "BigBoss")

    def test_many2one_to_a_private_address_renders_nothing(self):
        Partner = self.env["res.partner"]
        subject = Partner.create({"name": "Subject"})
        home = Partner.create(
            {"name": "Subject Home", "type": "private", "parent_id": subject.id}
        )
        record = Partner.create({"name": "Points at home", "parent_id": home.id})
        user = new_test_user(self.env, "qweb_m2o_reader")
        self.assertFalse(self.value_to_html(record.with_user(user).parent_id))
        self.assertEqual(self.value_to_html(record.parent_id), "Subject, Subject Home")


class TestQwebFieldHtml(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.html"].value_to_html(value, options or {})

    def test_html_falsy_values(self):
        self.assertEqual(self.value_to_html(False), "")
        self.assertEqual(self.value_to_html(None), "")
        self.assertEqual(self.value_to_html(""), "")

    def test_html_value_passthrough(self):
        self.assertEqual(self.value_to_html("<p>hi</p>"), "<p>hi</p>")


XSS_NAME = '<script>alert("xss")</script>'
XSS_RAW_FRAGMENTS = ("<script>", '"xss"')


class TestQwebFieldEscaping(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))

    def _assert_escaped(self, rendered):
        rendered = str(rendered)
        for raw in XSS_RAW_FRAGMENTS:
            self.assertNotIn(
                raw, rendered, f"unescaped {raw!r} leaked into {rendered!r}"
            )
        self.assertIn("&lt;script&gt;", rendered)

    def test_text_escapes(self):
        result = self.env["ir.qweb.field.text"].value_to_html(XSS_NAME, {})
        self._assert_escaped(result)

    def test_selection_escapes(self):
        result = self.env["ir.qweb.field.selection"].value_to_html(
            "key", {"selection": {"key": XSS_NAME}}
        )
        self._assert_escaped(result)

    def test_many2one_escapes(self):
        parent = self.env["res.partner"].create({"name": XSS_NAME})
        child = self.env["res.partner"].create(
            {"name": "Child", "parent_id": parent.id}
        )
        result = self.env["ir.qweb.field.many2one"].value_to_html(child.parent_id, {})
        self._assert_escaped(result)

    def test_many2many_escapes(self):
        parent = self.env["res.partner"].create({"name": "Parent"})
        self.env["res.partner"].create({"name": XSS_NAME, "parent_id": parent.id})
        result = self.env["ir.qweb.field.many2many"].value_to_html(parent.child_ids, {})
        self._assert_escaped(result)

    def test_one2many_escapes(self):
        parent = self.env["res.partner"].create({"name": "Parent"})
        self.env["res.partner"].create({"name": XSS_NAME, "parent_id": parent.id})
        result = self.env["ir.qweb.field.one2many"].value_to_html(parent.child_ids, {})
        self._assert_escaped(result)

    def test_contact_escapes(self):
        partner = self.env["res.partner"].create({"name": XSS_NAME})
        result = self.env["ir.qweb.field.contact"].value_to_html(
            partner, {"fields": ["name"]}
        )
        self._assert_escaped(result)

    def test_monetary_escapes_currency_symbol(self):
        currency = self.env["res.currency"].create(
            {
                "name": "XSS",
                "symbol": '"><script>alert(1)</script>',
                "rounding": 0.01,
            }
        )
        result = self.env["ir.qweb.field.monetary"].value_to_html(
            1000.0, {"display_currency": currency}
        )
        rendered = str(result)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_image_url_escapes(self):
        result = self.env["ir.qweb.field.image_url"].value_to_html(
            'http://example.com/"><script>alert(1)</script>', {}
        )
        rendered = str(result)
        self.assertNotIn('"><script>', rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&#34;", rendered)

    def test_image_renders_escaped_data_uri(self):
        png_b64 = (
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4n"
            b"GP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
        )
        result = self.env["ir.qweb.field.image"].value_to_html(png_b64, {})
        rendered = str(result)
        self.assertTrue(rendered.startswith('<img src="data:image/png;base64,'))
        self.assertTrue(rendered.endswith('">'))

    def test_barcode_escapes_value_in_alt(self):
        hostile = 'a"<script>'
        result = self.env["ir.qweb.field.barcode"].value_to_html(
            hostile, {"symbology": "Code128"}
        )
        rendered = str(result)
        self.assertNotIn('"<script>', rendered)
        self.assertNotIn("<script>", rendered)

    def test_barcode_non_ascii_escapes(self):
        result = self.env["ir.qweb.field.barcode"].value_to_html(
            XSS_NAME + "\N{SNOWMAN}", {}
        )
        self._assert_escaped(result)


class TestQwebFieldAttributes(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.partner = cls.env["res.partner"].create({"name": "Branding Co"})

    def test_attributes_returns_empty_without_branding_or_translate(self):
        result = self.env["ir.qweb.field"].attributes(
            self.partner,
            "name",
            {"inherit_branding": False, "translate": False},
        )
        self.assertEqual(result, {})

    def test_attributes_branding_dict(self):
        result = self.env["ir.qweb.field"].attributes(
            self.partner,
            "name",
            {
                "inherit_branding": True,
                "translate": False,
                "type": "char",
                "expression": "record.name",
            },
        )
        self.assertEqual(result["data-oe-model"], "res.partner")
        self.assertEqual(result["data-oe-id"], self.partner.id)
        self.assertEqual(result["data-oe-field"], "name")
        self.assertEqual(result["data-oe-type"], "char")
        self.assertEqual(result["data-oe-expression"], "record.name")

    def test_attributes_readonly_flag(self):
        result = self.env["ir.qweb.field"].attributes(
            self.partner,
            "id",
            {"inherit_branding": True, "translate": False},
        )
        self.assertEqual(result["data-oe-readonly"], 1)


class TestQwebFieldTimeRounding(common.TransactionCase):
    def _time(self, value):
        return self.env["ir.qweb.field.time"].value_to_html(value, {"format": "HH:mm"})

    def _float_time(self, value):
        return self.env["ir.qweb.field.float_time"].value_to_html(value, {})

    def test_time_agrees_with_float_time_on_every_minute_of_the_day(self):
        disagreeing = [
            minutes
            for minutes in range(24 * 60)
            if self._time(minutes / 60.0) != self._float_time(minutes / 60.0)
        ]
        self.assertEqual(disagreeing, [])

    def test_time_rounds_the_known_truncation_cases(self):
        self.assertEqual(self._time(2.05), "02:03")
        self.assertEqual(self._time(4.1), "04:06")
        self.assertEqual(self._time(8.2), "08:12")

    def test_rounding_up_past_midnight_clamps_rather_than_raising(self):
        for value in (23.99, 23.9917, 23.995, 23.999, 23.99999):
            with self.subTest(value):
                self.assertEqual(self._time(value), "23:59")

    def test_the_range_guard_still_fires_on_the_input(self):
        for value in (24.0, 24.0001, 25.0):
            with self.subTest(value), self.assertRaises(ValueError):
                self._time(value)
        with self.assertRaises(ValueError):
            self._time(-0.5)


class TestQwebFieldDurationDirection(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.duration"].value_to_html(value, options or {})

    def test_direction_is_applied_once_to_the_whole_value(self):
        options = {
            "unit": "second",
            "round": "minute",
            "format": "narrow",
            "add_direction": True,
        }
        self.assertEqual(self.value_to_html(5400, options), "in 2h")
        self.assertEqual(self.value_to_html(3661, options), "in 1h")
        self.assertEqual(self.value_to_html(-5400, options), "2h ago")

    def test_direction_matches_what_babel_itself_emits(self):
        import babel.dates

        from odoo.tools.misc import babel_locale_parse

        locale = babel_locale_parse(self.env["ir.qweb.field"].user_lang().code)
        for seconds in (90, 3661, 5400, 7260, 86500):
            self.assertEqual(
                self.value_to_html(seconds, {"add_direction": True}),
                babel.dates.format_timedelta(
                    seconds, add_direction=True, locale=locale, threshold=1
                ),
            )

    def test_sections_are_untouched_without_a_direction(self):
        options = {"unit": "second", "round": "minute", "format": "narrow"}
        self.assertEqual(self.value_to_html(5400, options), "1h 30m")
        self.assertEqual(self.value_to_html(3661, options), "1h 1m")

    def test_a_direction_on_a_zero_value_stays_empty(self):
        self.assertEqual(self.value_to_html(0, {"add_direction": True}), "")

    def test_a_digital_value_that_rounds_to_zero_drops_the_sign_too(self):
        self.assertEqual(
            self.value_to_html(-0.0001, {"unit": "hour", "digital": True}),
            "00:00:00",
        )
        self.assertEqual(
            self.value_to_html(
                -0.0001, {"unit": "hour", "round": "day", "digital": True}
            ),
            "00",
        )
        self.assertEqual(
            self.value_to_html(-1.5, {"unit": "hour", "digital": True}),
            "-01:30:00",
            "a value that does NOT round away still keeps its sign",
        )


class TestQwebFieldDurationLocaleFallback(common.TransactionCase):
    def test_missing_narrow_relative_pattern_widens_before_changing_language(self):
        from odoo.tools.misc import babel_locale_parse

        Duration = self.env["ir.qweb.field.duration"]
        locale = babel_locale_parse("de_IT")
        formatted = Duration._format_timedelta(3600, True, "narrow", locale)
        self.assertNotEqual(formatted, "in 1 hour", "fell back to English")
        self.assertEqual(
            formatted,
            Duration._format_timedelta(3600, True, "long", locale),
        )


class TestQwebFieldImageInput(common.TransactionCase):
    PNG_B64 = (
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4n"
        b"GP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    )

    def value_to_html(self, value):
        return self.env["ir.qweb.field.image"].value_to_html(value, {})

    def test_a_str_payload_renders_like_the_bytes_one(self):
        self.assertEqual(
            str(self.value_to_html(self.PNG_B64.decode())),
            str(self.value_to_html(self.PNG_B64)),
        )

    def test_every_malformed_payload_raises_the_domain_error(self):
        hostile = {
            "an int": 12345,
            "an object": object(),
            "a list": [],
            "non-ascii bytes": self.PNG_B64[:10] + b"\xff" + self.PNG_B64[10:],
            "a non-ascii str": self.PNG_B64[:10].decode()
            + "\N{LATIN SMALL LETTER E WITH ACUTE}"
            + self.PNG_B64[10:].decode(),
        }
        for label, value in hostile.items():
            with self.subTest(label), self.assertRaises(ValueError):
                self.value_to_html(value)

    def test_a_payload_that_only_decodes_by_discarding_bytes_is_refused(self):
        smuggled = self.PNG_B64[:10] + b"\xff" + self.PNG_B64[10:]
        self.assertEqual(
            base64.b64decode(smuggled),
            base64.b64decode(self.PNG_B64),
            "fixture no longer exercises the discard path",
        )
        with self.assertRaises(ValueError):
            self.value_to_html(smuggled)

    def test_a_format_with_no_registered_mime_falls_back_to_the_sniff(self):
        from unittest.mock import patch

        from PIL import Image

        with patch.dict(Image.MIME, clear=True):
            rendered = str(self.value_to_html(self.PNG_B64))
        self.assertIn("data:image/png;base64,", rendered)


class TestQwebFieldBarcodeInput(common.TransactionCase):
    def value_to_html(self, value, options=None):
        return self.env["ir.qweb.field.barcode"].value_to_html(value, options or {})

    def test_an_integer_barcode_renders(self):
        rendered = str(self.value_to_html(123456789012))
        self.assertIn('src="data:image/png;base64,', rendered)
        self.assertIn('alt="Barcode 123456789012"', rendered)

    def test_a_non_str_img_option_renders(self):
        rendered = str(self.value_to_html("ABC", {"img_width": 30}))
        self.assertIn('width="30"', rendered)


class TestQwebFieldSelectionContract(common.TransactionCase):
    def test_a_missing_selection_option_names_itself(self):
        with self.assertRaises(ValueError) as caught:
            self.env["ir.qweb.field.selection"].value_to_html("draft", {})
        self.assertIn("selection", str(caught.exception))


class TestQwebFieldDatetimeOnADate(common.TransactionCase):
    def test_a_date_value_renders_at_midnight(self):
        rendered = self.env["ir.qweb.field.datetime"].value_to_html(
            date(2024, 5, 4), {}
        )
        self.assertIn("2024", rendered)
        self.assertIn("12:00:00 AM", rendered)

    def test_a_readers_timezone_does_not_move_a_date(self):
        converter = self.env["ir.qweb.field.datetime"].with_context(
            tz="Europe/Brussels"
        )

        rendered = converter.value_to_html(date(2024, 5, 4), {})

        self.assertIn("05/04/2024", rendered)
        self.assertIn(
            "12:00:00 AM",
            rendered,
            "a date names no instant, so no timezone may shift it",
        )

    def test_a_named_timezone_does_not_move_a_date_either(self):
        rendered = self.env["ir.qweb.field.datetime"].value_to_html(
            date(2024, 5, 4), {"tz_name": "Pacific/Kiritimati"}
        )

        self.assertIn(
            "05/04/2024",
            rendered,
            "a +14 offset must not carry the date onto the next day",
        )

    def test_a_real_datetime_still_moves_with_the_reader(self):
        converter = self.env["ir.qweb.field.datetime"].with_context(
            tz="Europe/Brussels"
        )

        rendered = converter.value_to_html(datetime(2024, 5, 4, 0, 0, 0), {})

        self.assertIn(
            "02:00:00 AM",
            rendered,
            "an instant is still shown in the reader's timezone",
        )


class TestQwebFieldMonetaryPrecision(common.TransactionCase):
    def value_to_html(self, value, options):
        return str(self.env["ir.qweb.field.monetary"].value_to_html(value, options))

    def test_decimal_places_widens_the_rounding_too(self):
        usd = self.env.ref("base.USD")
        self.assertIn(
            "1,234.5678",
            self.value_to_html(
                1234.5678, {"display_currency": usd, "decimal_places": 4}
            ),
        )

    def test_the_default_still_rounds_with_the_currency(self):
        usd = self.env.ref("base.USD")
        self.assertIn(
            "1,234.57", self.value_to_html(1234.5678, {"display_currency": usd})
        )

    def test_the_number_matches_tools_format_amount(self):
        from odoo.tools import format_amount

        usd = self.env.ref("base.USD")
        for value in (1234.5, -1234.5, 0.004, -0.004, 1e6):
            expected = format_amount(self.env, value, usd)
            rendered = self.value_to_html(value, {"display_currency": usd})
            self.assertIn(expected.strip("$\N{NO-BREAK SPACE}"), rendered)


class TestQwebFieldRecordOptionsHook(common.TransactionCase):
    CONVERTERS = (
        "ir.qweb.field.float",
        "ir.qweb.field.selection",
        "ir.qweb.field.monetary",
        "ir.qweb.field.relative",
    )

    def test_none_of_them_reimplements_record_to_html(self):
        shared = type(self.env["ir.qweb.field"]).record_to_html
        for name in self.CONVERTERS:
            self.assertIs(
                type(self.env[name]).record_to_html,
                shared,
                f"{name} reimplements record_to_html instead of _record_options",
            )

    def test_each_of_them_supplies_the_hook(self):
        inherited = type(self.env["ir.qweb.field"])._record_options
        for name in self.CONVERTERS:
            self.assertIsNot(
                type(self.env[name])._record_options,
                inherited,
                f"{name} enriches nothing -- the override is gone, not moved",
            )

    def test_the_hook_does_not_mutate_the_caller_s_options(self):
        rate = self.env["res.currency.rate"].create(
            {
                "currency_id": self.env.ref("base.EUR").id,
                "name": "2020-01-01",
                "rate": 1.5,
            }
        )
        for name, field_name in (
            ("ir.qweb.field.float", "rate"),
            ("ir.qweb.field.monetary", "rate"),
            ("ir.qweb.field.relative", "name"),
        ):
            options = {}
            self.env[name].record_to_html(rate, field_name, options)
            self.assertEqual(options, {}, f"{name} mutated the options it was given")


class TestQwebFieldAttributesGuard(common.TransactionCase):
    def test_an_unknown_field_is_not_looked_up_when_nothing_is_emitted(self):
        partner = self.env["res.partner"].create({"name": "Guard"})
        result = self.env["ir.qweb.field"].attributes(
            partner, "no_such_field", {"inherit_branding": False, "translate": False}
        )
        self.assertEqual(result, {})


class TestQwebFieldMonetaryCurrencyFallback(common.TransactionCase):
    def test_an_empty_candidate_is_skipped_for_a_populated_one(self):
        company = self.env.company
        Monetary = self.registry["ir.qweb.field.monetary"]
        self.assertFalse(company.parent_id, "fixture needs an empty first candidate")
        self.assertTrue(company.currency_id)

        with patch.object(
            Monetary,
            "_get_currency_field_names",
            lambda self, record, field_name: ["parent_id", "currency_id"],
        ):
            options = self.env["ir.qweb.field.monetary"]._record_options(
                company, "id", {}
            )
        self.assertEqual(options["display_currency"], company.currency_id)

    def test_the_declared_currency_field_is_tried_first(self):
        ranked = self.env["ir.qweb.field.monetary"]._get_currency_field_names(
            self.env["res.company"], "id"
        )
        self.assertEqual(ranked, ["currency_id"])

    def test_the_ranking_does_not_depend_on_field_dict_order(self):
        class Fake:
            def __init__(self, type_, comodel=None, currency_field=None):
                self.type = type_
                self.comodel_name = comodel
                self._currency_field = currency_field

            def get_currency_field(self, record):
                return self._currency_field

        class FakeRecord:
            def __init__(self, fields_):
                self._fields = fields_

        Monetary = self.env["ir.qweb.field.monetary"]
        shuffled = [
            {
                "amount": Fake("monetary", currency_field="pay_currency_id"),
                "z_currency_id": Fake("many2one", "res.currency"),
                "pay_currency_id": Fake("many2one", "res.currency"),
                "currency_id": Fake("many2one", "res.currency"),
            },
            {
                "amount": Fake("monetary", currency_field="pay_currency_id"),
                "currency_id": Fake("many2one", "res.currency"),
                "pay_currency_id": Fake("many2one", "res.currency"),
                "z_currency_id": Fake("many2one", "res.currency"),
            },
        ]
        ranked = [
            Monetary._get_currency_field_names(FakeRecord(fields_), "amount")
            for fields_ in shuffled
        ]
        self.assertEqual(ranked[0], ranked[1], "the order tracked the field dict")
        self.assertEqual(ranked[0], ["pay_currency_id", "currency_id", "z_currency_id"])

    def test_a_non_monetary_field_prefers_currency_id(self):
        class Fake:
            def __init__(self, type_, comodel=None):
                self.type = type_
                self.comodel_name = comodel

        class FakeRecord:
            def __init__(self, fields_):
                self._fields = fields_

        record = FakeRecord(
            {
                "amount": Fake("float"),
                "cost_currency_id": Fake("many2one", "res.currency"),
                "currency_id": Fake("many2one", "res.currency"),
            }
        )
        self.assertEqual(
            self.env["ir.qweb.field.monetary"]._get_currency_field_names(
                record, "amount"
            ),
            ["currency_id", "cost_currency_id"],
        )


class TestFormatAmountNegativeZero(common.TransactionCase):
    def test_format_amount_does_not_render_a_negative_zero(self):
        from odoo.tools import format_amount

        usd = self.env.ref("base.USD")
        for value in (-0.004, -0.0, -0.0000001):
            with self.subTest(value):
                self.assertNotIn("-", format_amount(self.env, value, usd))

    def test_the_converter_does_not_render_a_negative_zero(self):
        usd = self.env.ref("base.USD")
        rendered = str(
            self.env["ir.qweb.field.monetary"].value_to_html(
                -0.004, {"display_currency": usd}
            )
        )
        self.assertNotIn("-", rendered)

    def test_a_value_that_is_nonzero_at_the_asked_precision_keeps_its_sign(self):
        usd = self.env.ref("base.USD")
        rendered = str(
            self.env["ir.qweb.field.monetary"].value_to_html(
                -0.004, {"display_currency": usd, "decimal_places": 4}
            )
        )
        self.assertIn("0.0040", rendered)
        self.assertIn(NEGATIVE_SIGN_JOINER, rendered)


class TestQwebFieldHtmlPostProcessing(common.TransactionCase):
    # base's contract: an override such as website's may decline the name
    # hook (None) and rewrite URLs; these tests read the base implementation
    # whatever the DB has installed.
    def setUp(self):
        super().setUp()
        IrQweb = self.registry["ir.qweb"]
        for name in ("_get_post_processing_att_names", "_post_processing_att"):
            patcher = patch.object(IrQweb, name, getattr(BaseIrQweb, name))
            patcher.start()
            self.addCleanup(patcher.stop)

    def value_to_html(self, value):
        return str(self.env["ir.qweb.field.html"].value_to_html(value, {}))

    def test_every_advertised_name_is_actually_scrubbed(self):
        names = self.env["ir.qweb"]._get_post_processing_att_names()
        self.assertTrue(names, "the base set must not be empty")
        for name in names:
            with self.subTest(name):
                rendered = self.value_to_html(f'<a {name}="javascript:alert(1)">x</a>')
                self.assertNotIn("javascript:", rendered)

    def test_an_attribute_outside_the_set_is_left_alone(self):
        rendered = self.value_to_html('<a title="javascript:alert(1)">x</a>')
        self.assertIn("javascript:alert(1)", rendered)

    def test_the_set_is_conservative_over_every_plausible_attribute(self):
        irQweb = self.env["ir.qweb"]
        names = irQweb._get_post_processing_att_names()
        self.assertIsNotNone(names, "base must narrow; only an override may decline")
        candidates = [
            *names,
            "data-src",
            "data-href",
            "data-action",
            "srcset",
            "poster",
            "background",
            "class",
            "style",
            "id",
            "title",
            "alt",
            "rel",
            "target",
            "cite",
            "longdesc",
            "usemap",
            "ping",
            "content",
        ]
        values = [
            "javascript:alert(1)",
            "JaVaScRiPt:alert(1)",
            "java\tscript:alert(1)",
            "\x01javascript:alert(1)",
            "vbscript:x",
            "data:text/html;base64,PHN2Zz4=",
            "https://example.com/",
        ]
        tags = ["a", "img", "div", "form", "script", "iframe", "object", "span"]
        skipped = 0
        for tag in tags:
            for attr in candidates:
                for value in values:
                    attrib = {attr: value}
                    if not names.isdisjoint(attrib):
                        continue
                    skipped += 1
                    self.assertEqual(
                        irQweb._post_processing_att(tag, dict(attrib)),
                        attrib,
                        f"<{tag} {attr}={value!r}> would be skipped, but "
                        f"_post_processing_att changes it",
                    )
        self.assertGreater(skipped, 100, "the sweep did not exercise the skip")

    def test_no_advertised_name_is_dead_weight(self):
        irQweb = self.env["ir.qweb"]
        for name in irQweb._get_post_processing_att_names():
            with self.subTest(name):
                attrib = {name: "javascript:alert(1)"}
                self.assertNotEqual(
                    irQweb._post_processing_att("a", dict(attrib)),
                    attrib,
                    f"{name!r} is advertised but nothing acts on it",
                )

    def test_a_widened_hook_is_honoured_by_the_converter(self):
        IrQweb = self.registry["ir.qweb"]
        original = IrQweb._post_processing_att

        def widened(self, tagName, atts, *, is_static=False):
            atts = original(self, tagName, atts, is_static=is_static)
            if "title" in atts:
                atts["title"] = "scrubbed"
            return atts

        with patch.object(IrQweb, "_post_processing_att", widened):
            not_widened = self.value_to_html('<a title="keep">x</a>')
            widened_names = self.env["ir.qweb"]._get_post_processing_att_names() | {
                "title"
            }
            with patch.object(
                IrQweb,
                "_get_post_processing_att_names",
                lambda self, names=widened_names: names,
            ):
                widened_out = self.value_to_html('<a title="keep">x</a>')
        self.assertIn('title="keep"', not_widened, "the filter did skip it")
        self.assertIn('title="scrubbed"', widened_out, "widening was honoured")

    def test_the_parse_still_tidies_when_nothing_is_scrubbed(self):
        self.assertEqual(self.value_to_html("<p>unclosed"), "<p>unclosed</p>")
        self.assertEqual(
            self.value_to_html("<html><body><p>a</p></body></html>"), "<p>a</p>"
        )

    def test_untouched_attributes_survive_verbatim(self):
        rendered = self.value_to_html(
            '<p class="a b" id="x" data-k="v">t</p><img src="/ok.png" alt="a">'
        )
        for fragment in ('class="a b"', 'id="x"', 'data-k="v"', 'src="/ok.png"'):
            self.assertIn(fragment, rendered)

    def test_the_body_hook_runs_inside_the_single_parse(self):
        seen = []
        Html = self.registry["ir.qweb.field.html"]

        def spy(self, body, options):
            seen.append(body.tag)
            return body

        with patch.object(Html, "_post_process_html_body", spy):
            self.value_to_html("<p>x</p>")
        self.assertEqual(seen, ["body"], "the hook did not receive the parsed body")


class TestQwebFieldFallbackRobustness(common.TransactionCase):
    def test_undecodable_bytes_do_not_take_the_page_down(self):
        rendered = self.env["ir.qweb.field"].value_to_html(b"\xff\xfe", {})
        self.assertTrue(
            rendered, "expected replacement characters, not an empty string"
        )

    def test_decodable_bytes_are_unchanged(self):
        self.assertEqual(
            self.env["ir.qweb.field"].value_to_html("café".encode(), {}), "café"
        )

    def test_a_non_finite_float_names_itself(self):
        for value in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value), self.assertRaises(ValueError) as caught:
                self.env["ir.qweb.field.float"].value_to_html(value, {})
            self.assertIn("finite", str(caught.exception))

    def test_an_unknown_duration_unit_names_itself_and_the_known_ones(self):
        for option in ("unit", "round"):
            with self.subTest(option), self.assertRaises(ValueError) as caught:
                self.env["ir.qweb.field.duration"].value_to_html(
                    1, {option: "fortnight"}
                )
            message = str(caught.exception)
            self.assertIn("fortnight", message)
            self.assertIn(option, message)
            self.assertIn("second", message, "the known units should be listed")
