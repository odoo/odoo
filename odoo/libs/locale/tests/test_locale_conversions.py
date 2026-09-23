import babel
import pytest

from odoo.libs.locale.conversions import posix_to_ldml, py_to_js_locale
from odoo.libs.locale.number_format import format_number


@pytest.fixture(scope="module")
def en_us():
    return babel.Locale.parse("en_US")


class TestPyToJsLocale:
    @pytest.mark.parametrize(
        ("py", "js"),
        [
            ("en_US", "en-US"),
            ("fr_FR", "fr-FR"),
            ("sr@latin", "sr-Latn"),
            ("en", "en"),
        ],
    )
    def test_mapping(self, py, js):
        assert py_to_js_locale(py) == js


class TestPosixToLdml:
    def test_basic_directives(self, en_us):
        assert posix_to_ldml("%m/%d/%Y", en_us) == "MM/dd/yyyy"

    def test_no_pad_flag_does_not_leak_into_next_directive(self, en_us):
        assert posix_to_ldml("%-d %B", en_us) == "d MMMM"
        assert posix_to_ldml("%-x%d", en_us) == "M/d/yydd"

    def test_unsupported_directive_raises_valueerror(self, en_us):
        with pytest.raises(ValueError, match="Unsupported strftime directive"):
            posix_to_ldml("%Q", en_us)


class _EU:
    decimal_point = ","
    thousands_sep = "."
    grouping = "[3,0]"


class _EN:
    decimal_point = "."
    thousands_sep = ","
    grouping = "[3,0]"


class TestFormatNumberFindsItsConversion:
    def test_a_trailing_literal_percent(self):
        assert format_number("%.2f%%", 1234.5, _EU(), grouping=True) == "1.234,50%"

    def test_trailing_literal_text(self):
        assert format_number("%d units", 1234, _EU(), grouping=True) == "1.234 units"

    def test_flags_and_width_do_not_confuse_it(self):
        assert format_number("%+.2f", 1234.5, _EU(), grouping=True) == "+1.234,50"
        assert format_number("%08.2f", 1234.5, _EU(), grouping=True) == "01.234,50"

    @pytest.mark.parametrize(
        ("spec", "value", "eu", "en"),
        [
            ("%.2f", 1234.5, "1.234,50", "1,234.50"),
            ("%d", 1234, "1.234", "1,234"),
            ("%g", 1234.5, "1.234,5", "1,234.5"),
            ("%e", 1234.5, "1,234500e+03", "1.234500e+03"),
            ("%E", 1234.5, "1,234500E+03", "1.234500E+03"),
        ],
    )
    def test_specs_ending_at_their_conversion_are_unchanged(self, spec, value, eu, en):
        assert format_number(spec, value, _EU(), grouping=True) == eu
        assert format_number(spec, value, _EN(), grouping=True) == en


class TestFormatNumberDetectsScientificFromTheSpec:
    def test_a_literal_e_in_the_suffix_no_longer_suppresses_grouping(self):
        assert format_number("%.2f EUR", 1234.5, _EU(), grouping=True) == "1.234,50 EUR"

    def test_a_real_exponent_is_still_not_grouped(self):
        assert format_number("%e", 1234500.0, _EU(), grouping=True) == "1,234500e+06"
        assert format_number("%.3g", 1234500.0, _EU(), grouping=True) == "1,23e+06"

    def test_g_without_an_exponent_is_grouped(self):
        assert format_number("%g", 1234.5, _EU(), grouping=True) == "1.234,5"


def test_a_grouping_stored_as_a_bare_count_formats():
    from types import SimpleNamespace

    bare = SimpleNamespace(decimal_point=".", grouping="3", thousands_sep=",")
    listed = SimpleNamespace(decimal_point=".", grouping="[3]", thousands_sep=",")
    assert format_number("%.2f", 1234567.5, bare, grouping=True) == format_number(
        "%.2f", 1234567.5, listed, grouping=True
    )


def test_a_grouping_that_is_not_digit_counts_is_a_clear_error():
    from types import SimpleNamespace

    import pytest

    lang = SimpleNamespace(decimal_point=".", grouping="'x'", thousands_sep=",")
    with pytest.raises(ValueError, match="list of digit counts"):
        format_number("%.2f", 1234.5, lang, grouping=True)
