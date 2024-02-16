import datetime

import pytz

from odoo.tests import TransactionCase
from odoo.tools.i18n import format_date, format_datetime, format_list, format_time, formatLang


class I18nTest(TransactionCase):
    def test_format_list(self):
        lang = self.env["res.lang"]

        formatted_text = format_list(self.env, ["Mario", "Luigi"])
        self.assertEqual(formatted_text, "Mario and Luigi", "Should default to English.")

        formatted_text = format_list(self.env, ["To be", "Not to be"], "or")
        self.assertEqual(formatted_text, "To be or Not to be", "Should take the style into account.")

        lang._activate_lang("fr_FR")

        formatted_text = format_list(lang.with_context(lang="fr_FR").env, ["Athos", "Porthos", "Aramis"])
        self.assertEqual(formatted_text, "Athos, Porthos et Aramis", "Should use the language of the user.")

        formatted_text = format_list(
            lang.with_context(lang="en_US").env,
            ["Athos", "Porthos", "Aramis"],
            lang_code="fr_FR",
        )
        self.assertEqual(formatted_text, "Athos, Porthos et Aramis", "Should use the chosen language.")


class TestFormatLangDate(TransactionCase):
    def test_00_accepted_types(self):
        self.env.user.tz = "Europe/Brussels"
        datetime_str = "2017-01-31 12:00:00"
        date_datetime = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        date_date = date_datetime.date()
        date_str = "2017-01-31"
        time_part = datetime.time(16, 30, 22)
        t_medium = "h:mm:ss a"
        medium = f"MMM d, YYYY, {t_medium}"

        self.assertEqual(format_date(self.env, date_datetime), "01/31/2017")
        self.assertEqual(format_date(self.env, date_date), "01/31/2017")
        self.assertEqual(format_date(self.env, date_str), "01/31/2017")
        self.assertEqual(format_date(self.env, ""), "")
        self.assertEqual(format_date(self.env, False), "")
        self.assertEqual(format_date(self.env, None), "")

        self.assertEqual(format_datetime(self.env, date_datetime, dt_format=medium), "Jan 31, 2017, 1:00:00 PM")
        self.assertEqual(format_datetime(self.env, datetime_str, dt_format=medium), "Jan 31, 2017, 1:00:00 PM")
        self.assertEqual(format_datetime(self.env, "", dt_format=medium), "")
        self.assertEqual(format_datetime(self.env, False, dt_format=medium), "")
        self.assertEqual(format_datetime(self.env, None, dt_format=medium), "")

        self.assertEqual(format_time(self.env, time_part, time_format=t_medium), "4:30:22 PM")
        self.assertEqual(format_time(self.env, "", time_format=t_medium), "")
        self.assertEqual(format_time(self.env, False, time_format=t_medium), "")
        self.assertEqual(format_time(self.env, None, time_format=t_medium), "")

    def test_01_code_and_format(self):
        date_str = "2017-01-31"
        lang = self.env["res.lang"]

        # Activate French and Simplified Chinese (test with non-ASCII characters)
        lang._activate_lang("fr_FR")
        lang._activate_lang("zh_CN")

        # -- test `date`
        # Change a single parameter
        self.assertEqual(format_date(lang.with_context(lang="fr_FR").env, date_str), "31/01/2017")
        self.assertEqual(format_date(lang.env, date_str, lang_code="fr_FR"), "31/01/2017")
        self.assertEqual(format_date(lang.env, date_str, date_format="MMM d, y"), "Jan 31, 2017")

        # Change 2 parameters
        self.assertEqual(format_date(lang.with_context(lang="zh_CN").env, date_str, lang_code="fr_FR"), "31/01/2017")
        self.assertEqual(
            format_date(lang.with_context(lang="zh_CN").env, date_str, date_format="MMM d, y"), "1\u6708 31, 2017",
        )
        self.assertEqual(format_date(lang.env, date_str, lang_code="fr_FR", date_format="MMM d, y"), "janv. 31, 2017")

        # Change 3 parameters
        self.assertEqual(
            format_date(lang.with_context(lang="zh_CN").env, date_str, lang_code="en_US", date_format="MMM d, y"),
            "Jan 31, 2017",
        )

        # -- test `datetime`
        datetime_str = "2017-01-31 10:33:00"
        # Change languages and timezones
        datetime_us_str = format_datetime(lang.with_context(lang="en_US").env, datetime_str, tz="Europe/Brussels")
        self.assertNotEqual(
            format_datetime(lang.with_context(lang="fr_FR").env, datetime_str, tz="Europe/Brussels"), datetime_us_str,
        )
        self.assertNotEqual(
            format_datetime(lang.with_context(lang="zh_CN").env, datetime_str, tz="America/New_York"), datetime_us_str
        )

        # Change language, timezone and format
        self.assertEqual(
            format_datetime(
                lang.with_context(lang="fr_FR").env, datetime_str, tz="America/New_York", dt_format="dd/MM/YYYY HH:mm",
            ),
            "31/01/2017 05:33",
        )
        self.assertEqual(
            format_datetime(
                lang.with_context(lang="en_US").env, datetime_str, tz="Europe/Brussels", dt_format="MMM d, y",
            ),
            "Jan 31, 2017",
        )

        # Check given `lang_code` overwites context lang
        fmt_fr = "dd MMMM YYYY à HH:mm:ss Z"
        fmt_us = "MMMM dd, YYYY 'at' hh:mm:ss a Z"
        self.assertEqual(
            format_datetime(lang.env, datetime_str, tz="Europe/Brussels", dt_format=fmt_fr, lang_code="fr_FR"),
            "31 janvier 2017 à 11:33:00 +0100",
        )
        self.assertEqual(
            format_datetime(
                lang.with_context(lang="zh_CN").env,
                datetime_str,
                tz="Europe/Brussels",
                dt_format=fmt_us,
                lang_code="en_US",
            ),
            "January 31, 2017 at 11:33:00 AM +0100",
        )

        # -- test `time`
        time_part = datetime.time(16, 30, 22)
        time_part_tz = datetime.time(16, 30, 22, tzinfo=pytz.timezone("US/Eastern"))  # 4:30 PM timezoned

        self.assertEqual(
            format_time(lang.with_context(lang="fr_FR").env, time_part, time_format="HH:mm:ss"), "16:30:22",
        )
        self.assertEqual(
            format_time(lang.with_context(lang="zh_CN").env, time_part, time_format="ah:m:ss"), "\u4e0b\u53484:30:22",
        )

        # Check format in different languages
        self.assertEqual(format_time(lang.with_context(lang="fr_FR").env, time_part, time_format="HH:mm"), "16:30")
        self.assertEqual(
            format_time(lang.with_context(lang="zh_CN").env, time_part, time_format="ah:mm"), "\u4e0b\u53484:30",
        )

        # Check timezoned time part
        self.assertEqual(
            format_time(lang.with_context(lang="fr_FR").env, time_part_tz, time_format="HH:mm:ss Z"), "16:30:22 -0504",
        )
        self.assertEqual(
            format_time(lang.with_context(lang="zh_CN").env, time_part_tz, time_format="zzzz ah:mm:ss"),
            "\u5317\u7f8e\u4e1c\u90e8\u6807\u51c6\u65f6\u95f4\u0020\u4e0b\u53484:30:22",
        )

        # Check timezone conversion in format_time
        self.assertEqual(
            format_time(lang.with_context(lang="fr_FR").env, datetime_str, "Europe/Brussels", time_format="HH:mm:ss Z"),
            "11:33:00 +0100",
        )
        self.assertEqual(
            format_time(lang.with_context(lang="fr_FR").env, datetime_str, "US/Eastern", time_format="HH:mm:ss Z"),
            "05:33:00 -0500",
        )

        # Check given `lang_code` overwites context lang
        self.assertEqual(
            format_time(lang.with_context(lang="fr_FR").env, time_part, time_format="ah:mm", lang_code="zh_CN"),
            "\u4e0b\u53484:30",
        )
        self.assertEqual(
            format_time(lang.with_context(lang="zh_CN").env, time_part, time_format="ah:mm", lang_code="fr_FR"),
            "PM4:30",
        )

    def test_02_tz(self):
        self.env.user.tz = "Europe/Brussels"
        datetime_str = "2016-12-31 23:55:00"
        date_datetime = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # While London is still in 2016, Brussels is already in 2017
        self.assertEqual(format_date(self.env, date_datetime), "01/01/2017")

        # Force London timezone
        date_datetime = date_datetime.replace(tzinfo=pytz.UTC)
        self.assertEqual(
            format_date(self.env, date_datetime),
            "12/31/2016",
            "User's tz must be ignored when tz is specifed in datetime object",
        )


class TestFormatLang(TransactionCase):
    def test_value_and_digits(self):
        self.assertEqual(formatLang(self.env, 100.23, digits=1), "100.2")
        self.assertEqual(formatLang(self.env, 100.23, digits=3), "100.230")

        self.assertEqual(
            formatLang(self.env, ""), "", "If value is an empty string, it should return an empty string (not 0)",
        )

        self.assertEqual(
            formatLang(self.env, 100), "100.00", "If digits is None (default value), it should default to 2",
        )

        # Default rounding is 'HALF_EVEN'
        self.assertEqual(formatLang(self.env, 100.205), "100.20")
        self.assertEqual(formatLang(self.env, 100.215), "100.22")

    def test_grouping(self):
        self.env["res.lang"].create(
            {
                "name": "formatLang Lang",
                "code": "fLT",
                "grouping": "[3,2,-1]",
                "decimal_point": "!",
                "thousands_sep": "?",
            }
        )

        self.env["res.lang"]._activate_lang("fLT")

        self.assertEqual(
            formatLang(self.env["res.lang"].with_context(lang="fLT").env, 1000000000, grouping=True),
            "10000?00?000!00",
        )
        self.assertEqual(
            formatLang(self.env["res.lang"].with_context(lang="fLT").env, 1000000000, grouping=False),
            "1000000000.00",
        )

    def test_decimal_precision(self):
        decimal_precision = self.env["decimal.precision"].create(
            {
                "name": "formatLang Decimal Precision",
                "digits": 3,  # We want .001 decimals to make sure the decimal precision parameter 'dp' is chosen.
            }
        )

        self.assertEqual(formatLang(self.env, 100, dp=decimal_precision.name), "100.000")

    def test_currency_object(self):
        currency_object = self.env["res.currency"].create(
            {
                "name": "formatLang Currency",
                "symbol": "fL",
                "rounding": 0.1,  # We want .1 decimals to make sure 'currency_obj' is chosen.
                "position": "after",
            }
        )

        self.assertEqual(formatLang(self.env, 100, currency_obj=currency_object), "100.0%sfL" % "\N{NO-BREAK SPACE}")

        currency_object.write({"position": "before"})

        self.assertEqual(formatLang(self.env, 100, currency_obj=currency_object), "fL%s100.0" % "\N{NO-BREAK SPACE}")

    def test_decimal_precision_and_currency_object(self):
        decimal_precision = self.env["decimal.precision"].create(
            {
                "name": "formatLang Decimal Precision",
                "digits": 3,
            }
        )

        currency_object = self.env["res.currency"].create(
            {
                "name": "formatLang Currency",
                "symbol": "fL",
                "rounding": 0.1,
                "position": "after",
            }
        )

        # If we have a 'dp' and 'currency_obj', we use the decimal precision of 'dp' and the format of 'currency_obj'.
        self.assertEqual(
            formatLang(self.env, 100, dp=decimal_precision.name, currency_obj=currency_object),
            "100.000%sfL" % "\N{NO-BREAK SPACE}",
        )

    def test_rounding_method(self):
        self.assertEqual(formatLang(self.env, 100.205), "100.20")  # Default is 'HALF-EVEN'
        self.assertEqual(formatLang(self.env, 100.215), "100.22")  # Default is 'HALF-EVEN'

        self.assertEqual(formatLang(self.env, 100.205, rounding_method="HALF-UP"), "100.21")
        self.assertEqual(formatLang(self.env, 100.215, rounding_method="HALF-UP"), "100.22")

        self.assertEqual(formatLang(self.env, 100.205, rounding_method="HALF-DOWN"), "100.20")
        self.assertEqual(formatLang(self.env, 100.215, rounding_method="HALF-DOWN"), "100.21")

    def test_rounding_unit(self):
        self.assertEqual(formatLang(self.env, 1000000.00), "1,000,000.00")
        self.assertEqual(formatLang(self.env, 1000000.00, rounding_unit="units"), "1,000,000")
        self.assertEqual(formatLang(self.env, 1000000.00, rounding_unit="thousands"), "1,000")
        self.assertEqual(formatLang(self.env, 1000000.00, rounding_unit="lakhs"), "10")
        self.assertEqual(formatLang(self.env, 1000000.00, rounding_unit="millions"), "1")

    def test_rounding_method_and_rounding_unit(self):
        self.assertEqual(formatLang(self.env, 1822060000, rounding_method="HALF-UP", rounding_unit="lakhs"), "18,221")
        self.assertEqual(formatLang(self.env, 1822050000, rounding_method="HALF-UP", rounding_unit="lakhs"), "18,221")
        self.assertEqual(formatLang(self.env, 1822049900, rounding_method="HALF-UP", rounding_unit="lakhs"), "18,220")
