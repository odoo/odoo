"""Unit tests for odoo.libs.res_country — no Odoo ORM dependency."""

import unittest

from odoo.libs.res_country import (
    EU_EXTRA_VAT_CODES,
    FLAG_MAPPING,
    NO_FLAG_COUNTRIES,
    extract_address_format_fields,
    extract_address_line_fields,
    get_flag_code,
    get_flag_image_url,
)


class TestGetFlagCode(unittest.TestCase):
    """Test get_flag_code pure function."""

    def test_normal_country(self):
        self.assertEqual(get_flag_code("US"), "us")

    def test_normal_country_lowercase_output(self):
        self.assertEqual(get_flag_code("FR"), "fr")

    def test_territory_override(self):
        """French Guiana uses France's flag."""
        self.assertEqual(get_flag_code("GF"), "fr")

    def test_all_overrides_present(self):
        for code, expected in FLAG_MAPPING.items():
            self.assertEqual(get_flag_code(code), expected)

    def test_no_flag_country(self):
        """Antarctica has no flag."""
        self.assertIsNone(get_flag_code("AQ"))

    def test_svalbard_no_flag(self):
        self.assertIsNone(get_flag_code("SJ"))

    def test_empty_string(self):
        self.assertIsNone(get_flag_code(""))

    def test_none(self):
        self.assertIsNone(get_flag_code(None))


class TestGetFlagImageUrl(unittest.TestCase):
    """Test get_flag_image_url pure function."""

    def test_normal_country(self):
        self.assertEqual(
            get_flag_image_url("US"), "/base/static/img/country_flags/us.png"
        )

    def test_override_country(self):
        self.assertEqual(
            get_flag_image_url("GF"), "/base/static/img/country_flags/fr.png"
        )

    def test_no_flag_returns_none(self):
        self.assertIsNone(get_flag_image_url("AQ"))

    def test_none_returns_none(self):
        self.assertIsNone(get_flag_image_url(None))


class TestExtractAddressFormatFields(unittest.TestCase):
    """Test extract_address_format_fields pure function."""

    def test_us_default_format(self):
        fmt = (
            "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        )
        result = extract_address_format_fields(fmt)
        self.assertEqual(
            result,
            ["street", "street2", "city", "state_code", "zip", "country_name"],
        )

    def test_simple_format(self):
        self.assertEqual(
            extract_address_format_fields("%(city)s %(zip)s"), ["city", "zip"]
        )

    def test_empty_string(self):
        self.assertEqual(extract_address_format_fields(""), [])

    def test_no_placeholders(self):
        self.assertEqual(extract_address_format_fields("just plain text"), [])


class TestExtractAddressLineFields(unittest.TestCase):
    """Test extract_address_line_fields pure function."""

    def test_city_zip_state_line(self):
        line = "%(city)s %(state_code)s %(zip)s"
        fields = ("zip", "city", "state_code", "state_name")
        result = extract_address_line_fields(line, fields)
        self.assertEqual(result, ["city", "state_code", "zip"])

    def test_reversed_order(self):
        line = "%(zip)s %(city)s"
        fields = ("zip", "city", "state_code")
        result = extract_address_line_fields(line, fields)
        self.assertEqual(result, ["zip", "city"])

    def test_no_matches(self):
        line = "no fields here"
        fields = ("zip", "city")
        result = extract_address_line_fields(line, fields)
        self.assertEqual(result, [])

    def test_single_field(self):
        line = "%(city)s"
        fields = ("zip", "city", "state_code")
        result = extract_address_line_fields(line, fields)
        self.assertEqual(result, ["city"])


class TestEuExtraVatCodes(unittest.TestCase):
    """Test EU_EXTRA_VAT_CODES constant."""

    def test_greece(self):
        self.assertEqual(EU_EXTRA_VAT_CODES["GR"], "EL")

    def test_uk(self):
        self.assertEqual(EU_EXTRA_VAT_CODES["GB"], "XI")

    def test_length(self):
        self.assertEqual(len(EU_EXTRA_VAT_CODES), 2)

    def test_normal_country_not_present(self):
        self.assertNotIn("FR", EU_EXTRA_VAT_CODES)


if __name__ == "__main__":
    unittest.main()
