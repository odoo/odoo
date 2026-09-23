from decimal import Decimal
from math import log10

from odoo.tests.common import TransactionCase
from odoo.tools import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
    float_split_str,
)


class TestFloatPrecision(TransactionCase):
    def test_rounding_02(self):
        currency = self.env.ref("base.EUR")

        def try_round(amount, expected, digits=2, method="HALF-UP"):
            value = float_round(amount, precision_digits=digits, rounding_method=method)
            result = float_repr(value, precision_digits=digits)
            self.assertEqual(
                result,
                expected,
                "Rounding error: got %s, expected %s" % (result, expected),
            )

        try_round(2.674, "2.67")
        try_round(2.675, "2.68")
        try_round(-2.675, "-2.68")
        try_round(0.001, "0.00")
        try_round(-0.001, "0.00")
        try_round(0.0049, "0.00")
        try_round(0.005, "0.01")
        try_round(-0.005, "-0.01")
        try_round(6.6 * 0.175, "1.16")
        try_round(-6.6 * 0.175, "-1.16")
        try_round(5.015, "5.02", method="HALF-EVEN")
        try_round(5.025, "5.02", method="HALF-EVEN")
        try_round(-5.015, "-5.02", method="HALF-EVEN")
        try_round(-5.025, "-5.02", method="HALF-EVEN")

        def try_zero(amount, expected):
            self.assertEqual(
                currency.is_zero(amount),
                expected,
                "Rounding error: %s should be zero!" % amount,
            )

        try_zero(0.01, False)
        try_zero(-0.01, False)
        try_zero(0.001, True)
        try_zero(-0.001, True)
        try_zero(0.0046, True)
        try_zero(-0.0046, True)
        try_zero(2.68 - 2.675, False)
        try_zero(2.68 - 2.676, True)
        try_zero(2.676 - 2.68, True)
        try_zero(2.675 - 2.68, False)

        def try_compare(amount1, amount2, expected):
            self.assertEqual(
                currency.compare_amounts(amount1, amount2),
                expected,
                "Rounding error, compare_amounts(%s,%s) should be %s"
                % (amount1, amount2, expected),
            )

        try_compare(0.001, 0.001, 0)
        try_compare(-0.001, -0.001, 0)
        try_compare(0.001, 0.002, 0)
        try_compare(-0.001, -0.002, 0)
        try_compare(2.675, 2.68, 0)
        try_compare(2.676, 2.68, 0)
        try_compare(-2.676, -2.68, 0)
        try_compare(2.674, 2.68, -1)
        try_compare(-2.674, -2.68, 1)
        try_compare(3, 2.68, 1)
        try_compare(-3, -2.68, -1)
        try_compare(0.01, 0, 1)
        try_compare(-0.01, 0, -1)

    def test_rounding_03(self):

        def try_round(amount, expected, digits=3, method="HALF-UP"):
            value = float_round(amount, precision_digits=digits, rounding_method=method)
            result = float_repr(value, precision_digits=digits)
            self.assertEqual(
                result,
                expected,
                "Rounding error: got %s, expected %s" % (result, expected),
            )

        try_round(2.6735, "2.674")
        try_round(-2.6735, "-2.674")
        try_round(2.6745, "2.675")
        try_round(-2.6745, "-2.675")
        try_round(2.6744, "2.674")
        try_round(-2.6744, "-2.674")
        try_round(0.0004, "0.000")
        try_round(-0.0004, "0.000")
        try_round(357.4555, "357.456")
        try_round(-357.4555, "-357.456")
        try_round(457.4554, "457.455")
        try_round(-457.4554, "-457.455")

        try_round(2.6735, "2.673", method="HALF-DOWN")
        try_round(-2.6735, "-2.673", method="HALF-DOWN")
        try_round(2.6745, "2.674", method="HALF-DOWN")
        try_round(-2.6745, "-2.674", method="HALF-DOWN")
        try_round(2.6744, "2.674", method="HALF-DOWN")
        try_round(-2.6744, "-2.674", method="HALF-DOWN")
        try_round(0.0004, "0.000", method="HALF-DOWN")
        try_round(-0.0004, "0.000", method="HALF-DOWN")
        try_round(357.4555, "357.455", method="HALF-DOWN")
        try_round(-357.4555, "-357.455", method="HALF-DOWN")
        try_round(457.4554, "457.455", method="HALF-DOWN")
        try_round(-457.4554, "-457.455", method="HALF-DOWN")

        try_round(2.6735, "2.674", method="HALF-EVEN")
        try_round(-2.6735, "-2.674", method="HALF-EVEN")
        try_round(2.6745, "2.674", method="HALF-EVEN")
        try_round(-2.6745, "-2.674", method="HALF-EVEN")
        try_round(2.6744, "2.674", method="HALF-EVEN")
        try_round(-2.6744, "-2.674", method="HALF-EVEN")
        try_round(0.0004, "0.000", method="HALF-EVEN")
        try_round(-0.0004, "0.000", method="HALF-EVEN")
        try_round(357.4555, "357.456", method="HALF-EVEN")
        try_round(-357.4555, "-357.456", method="HALF-EVEN")
        try_round(457.4554, "457.455", method="HALF-EVEN")
        try_round(-457.4554, "-457.455", method="HALF-EVEN")

        try_round(8.175, "8.175", method="UP")
        try_round(8.1751, "8.176", method="UP")
        try_round(-8.175, "-8.175", method="UP")
        try_round(-8.1751, "-8.176", method="UP")
        try_round(-6.000, "-6.000", method="UP")
        try_round(1.8, "2", 0, method="UP")
        try_round(-1.8, "-2", 0, method="UP")

        try_round(2.425, "2.425", method="DOWN")
        try_round(2.4249, "2.424", method="DOWN")
        try_round(-2.425, "-2.425", method="DOWN")
        try_round(-2.4249, "-2.424", method="DOWN")
        try_round(-2.500, "-2.500", method="DOWN")
        try_round(1.8, "1", 0, method="DOWN")
        try_round(-1.8, "-1", 0, method="DOWN")

        fractions = [
            0.0,
            0.015,
            0.01499,
            0.675,
            0.67499,
            0.4555,
            0.4555,
            0.45555,
        ]
        expecteds = [".00", ".02", ".01", ".68", ".67", ".46", ".456", ".4556"]
        precisions = [2, 2, 2, 2, 2, 2, 3, 4]
        for magnitude in range(7):
            for frac, exp, prec in zip(fractions, expecteds, precisions, strict=False):
                for sign in [-1, 1]:
                    for x in range(0, 10000, 97):
                        n = x * 10**magnitude
                        f = sign * (n + frac)
                        f_exp = ("-" if f != 0 and sign == -1 else "") + str(n) + exp
                        try_round(f, f_exp, digits=prec)

        def try_zero(amount, expected):
            self.assertEqual(
                float_is_zero(amount, precision_digits=3),
                expected,
                "Rounding error: %s should be zero!" % amount,
            )

        try_zero(0.0002, True)
        try_zero(-0.0002, True)
        try_zero(0.00034, True)
        try_zero(0.0005, False)
        try_zero(-0.0005, False)
        try_zero(0.0008, False)
        try_zero(-0.0008, False)

        def try_compare(amount1, amount2, expected):
            self.assertEqual(
                float_compare(amount1, amount2, precision_digits=3),
                expected,
                "Rounding error, compare_amounts(%s,%s) should be %s"
                % (amount1, amount2, expected),
            )

        try_compare(0.0003, 0.0004, 0)
        try_compare(-0.0003, -0.0004, 0)
        try_compare(0.0002, 0.0005, -1)
        try_compare(-0.0002, -0.0005, 1)
        try_compare(0.0009, 0.0004, 1)
        try_compare(-0.0009, -0.0004, -1)
        try_compare(557.4555, 557.4556, 0)
        try_compare(-557.4555, -557.4556, 0)
        try_compare(657.4444, 657.445, -1)
        try_compare(-657.4444, -657.445, 1)

        def try_round(amount, expected, precision_rounding=None, method="HALF-UP"):
            value = float_round(
                amount,
                precision_rounding=precision_rounding,
                rounding_method=method,
            )
            result = float_repr(value, precision_digits=2)
            self.assertEqual(
                result,
                expected,
                "Rounding error: got %s, expected %s" % (result, expected),
            )

        try_round(-457.4554, "-457.45", precision_rounding=0.05)
        try_round(457.444, "457.50", precision_rounding=0.5)
        try_round(457.3, "455.00", precision_rounding=5)
        try_round(457.5, "460.00", precision_rounding=5)
        try_round(457.1, "456.00", precision_rounding=3)
        try_round(2.5, "2.50", precision_rounding=0.05, method="DOWN")
        try_round(-2.5, "-2.50", precision_rounding=0.05, method="DOWN")

    def test_rounding_04(self):
        currency = self.env.ref("base.EUR")
        currency_rate = self.env["res.currency.rate"]

        def try_roundtrip(value, expected, date):
            rate = currency_rate.create(
                {"name": date, "rate": value, "currency_id": currency.id}
            )
            self.assertEqual(
                rate.rate,
                expected,
                "Roundtrip error: got %s back from db, expected %s" % (rate, expected),
            )

        try_roundtrip(10000.999999, 10000.999999, "2000-01-03")

    def test_rounding_large_magnitude(self):
        rescued_145 = {"HALF-UP": "0.15", "HALF-DOWN": "0.14", "HALF-EVEN": "0.14"}
        for method in ("HALF-UP", "HALF-DOWN", "HALF-EVEN"):
            for value in (5.6e12, 1e13, 1.23456789e14, 1e15):
                self.assertEqual(
                    float_round(value, precision_rounding=0.01, rounding_method=method),
                    value,
                    "spurious digit at 2-digit precision for %s (%s)" % (value, method),
                )
                self.assertEqual(
                    float_round(value, precision_digits=0, rounding_method=method),
                    value,
                    "spurious unit at 0-digit precision for %s (%s)" % (value, method),
                )
            self.assertEqual(
                float_round(-1e13, precision_rounding=0.01, rounding_method=method),
                -1e13,
                "spurious digit for negative large value (%s)" % method,
            )
            self.assertEqual(
                float_repr(
                    float_round(0.145, precision_digits=2, rounding_method=method),
                    precision_digits=2,
                ),
                rescued_145[method],
                "representation-error tie no longer rescued (%s)" % method,
            )
        self.assertEqual(float_round(1.005, precision_digits=2), 1.01)
        self.assertEqual(float_round(2.675, precision_digits=2), 2.68)
        self.assertEqual(
            float_round(1e13 + 0.5, precision_rounding=1.0, rounding_method="HALF-UP"),
            1e13 + 1,
        )

    def test_float_split_05(self):
        currency = self.env.ref("base.EUR")

        def try_split(value, expected, split_fun, rounding=None):
            digits = (
                max(0, -int(log10(currency.rounding))) if rounding is None else rounding
            )
            result = split_fun(value, precision_digits=digits)
            self.assertEqual(
                result,
                expected,
                "Split error: got %s, expected %s" % (result, expected),
            )

        try_split(2.674, ("2", "67"), float_split_str)
        try_split(2.675, ("2", "68"), float_split_str)
        try_split(-2.675, ("-2", "68"), float_split_str)
        try_split(0.001, ("0", "00"), float_split_str)
        try_split(-0.001, ("0", "00"), float_split_str)
        try_split(42, ("42", "00"), float_split_str)
        try_split(0.1, ("0", "10"), float_split_str)
        try_split(13.0, ("13", ""), float_split_str, rounding=0)

    def test_rounding_invalid(self):
        with self.assertRaises(ValueError):
            float_is_zero(0.01, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(ValueError):
            float_is_zero(0.0, precision_rounding=0.0)

        with self.assertRaises(ValueError):
            float_is_zero(0.0, precision_rounding=-0.1)

        with self.assertRaises(ValueError):
            float_compare(0.01, 0.02, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(ValueError):
            float_compare(1.0, 1.0, precision_rounding=0.0)

        with self.assertRaises(ValueError):
            float_compare(1.0, 1.0, precision_rounding=-0.1)

        with self.assertRaises(ValueError):
            float_round(0.01, precision_digits=3, precision_rounding=0.01)

        with self.assertRaises(ValueError):
            float_round(-1.0, precision_digits=0, precision_rounding=0.1)

        with self.assertRaises(ValueError):
            float_round(1.25, precision_rounding=0.0)

        with self.assertRaises(ValueError):
            float_round(1.25, precision_rounding=-0.1)

        with self.assertRaises(ValueError):
            float_round(1.25, precision_digits=-1)

        with self.assertRaises(ValueError):
            float_round(1.25, precision_digits=0.5)

    def test_amount_to_text_10(self):
        currency = self.env.ref("base.EUR")

        amount_target = currency.amount_to_text(0.29)
        amount_test = currency.amount_to_text(0.28)
        self.assertNotEqual(
            amount_test,
            amount_target,
            "Amount in text should not depend on float representation",
        )


class TestNumericColumnPrecision(TransactionCase):
    LOSSY = (
        12345678901234.56,
        99999999999999.98,
        1234567890123456.8,
        1 / 3,
        0.1 + 0.2,
    )

    def _numeric_field(self):
        model = self.env["res.partner"]
        field = model._fields["partner_latitude"]
        self.assertEqual(
            field.column_type[0],
            "numeric",
            "this test needs a Float mapped to a numeric column",
        )
        return model, field

    def test_a_numeric_column_is_given_a_Decimal(self):
        from decimal import Decimal

        model, field = self._numeric_field()
        value = field.convert_to_column(12345678901234.56, model, {})
        self.assertIsInstance(
            value,
            Decimal,
            "a float goes out as float8 and PostgreSQL's cast to numeric keeps "
            "15 significant digits, silently dropping the cents of a large "
            "amount",
        )

    def test_a_float8_column_is_still_given_a_float(self):
        float8_fields = self.assertSweep(
            (
                (name, fname, field)
                for name, model in self.env.registry.items()
                if not model._abstract
                for fname, field in self.env[name]._fields.items()
                if field.type == "float"
                and field.store
                and field.column_type
                and field.column_type[0] == "float8"
            ),
            "no stored float8 field is installed, so this test cannot check "
            "what float8 conversion does",
        )
        for name, fname, field in float8_fields:
            with self.subTest(field=f"{name}.{fname}"):
                self.assertIsInstance(
                    field.convert_to_column(1 / 3, self.env[name], {}),
                    float,
                    f"{name}.{fname} is float8; converting it to Decimal would "
                    f"make PostgreSQL cast on every comparison",
                )

    def test_what_the_field_decided_is_what_is_stored(self):
        model, field = self._numeric_field()
        self.env.cr.execute("DROP TABLE IF EXISTS _test_numeric_precision")
        self.env.cr.execute(
            "CREATE TABLE _test_numeric_precision (id serial primary key, v numeric)"
        )
        for value in self.LOSSY:
            with self.subTest(value=value):
                decided = field.convert_to_column(value, model, {})
                self.env.cr.execute("DELETE FROM _test_numeric_precision")
                self.env.cr.execute(
                    "INSERT INTO _test_numeric_precision (v) VALUES (%s)", (decided,)
                )
                self.env.cr.execute("SELECT v FROM _test_numeric_precision")
                stored = float(self.env.cr.fetchone()[0])
                self.assertEqual(
                    stored,
                    float(decided),
                    "a float8 round trip through PostgreSQL's numeric cast "
                    "would drop digits the field had kept",
                )

    def test_a_large_amount_keeps_its_cents(self):
        model = self.env["res.currency"]
        field = model._fields["rounding"]
        self.assertEqual(field.column_type[0], "numeric")
        self.env.cr.execute("DROP TABLE IF EXISTS _test_cents")
        self.env.cr.execute(
            "CREATE TABLE _test_cents (id serial primary key, v numeric)"
        )
        for value in (12345678901234.56, 99999999999999.98):
            with self.subTest(value=value):
                self.env.cr.execute("DELETE FROM _test_cents")
                self.env.cr.execute(
                    "INSERT INTO _test_cents (v) VALUES (%s)",
                    (Decimal(repr(value)),),
                )
                self.env.cr.execute("SELECT v::text FROM _test_cents")
                self.assertEqual(
                    self.env.cr.fetchone()[0],
                    repr(value),
                    "sent as float8 this loses the cents: 12345678901234.56 "
                    "arrives as 12345678901234.6 and 99999999999999.98 as "
                    "100000000000000",
                )

    def test_both_write_paths_send_the_same_thing(self):
        from decimal import Decimal

        model, field = self._numeric_field()
        value = 12345678901234.56
        insert_side = field.convert_to_column(value, model, {})
        copy_side = Decimal(str(value))
        self.assertEqual(
            insert_side,
            copy_side,
            "INSERT and COPY must agree, or the number of records created in "
            "one call changes what is stored",
        )
