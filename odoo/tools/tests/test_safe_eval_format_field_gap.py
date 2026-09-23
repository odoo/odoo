import unittest

from odoo.tools.safe_eval import safe_eval

SECRET = "db-password-xyz"


def _victim():
    pass


class TestFormatReflectionEscapeClosed(unittest.TestCase):
    def test_a_literal_dunder_template_is_refused(self):
        with self.assertRaises(Exception):
            safe_eval('"{0.__globals__[SECRET]}".format(f)', {"f": _victim})

    def test_a_context_supplied_template_is_refused(self):
        with self.assertRaises(Exception):
            safe_eval(
                "template.format(f)",
                {"f": _victim, "template": "{0.__globals__[SECRET]}"},
            )

    def test_a_runtime_assembled_template_is_refused(self):
        with self.assertRaises(Exception):
            safe_eval(
                '("{0.%sglobals%s[SECRET]}" % ("__", "__")).format(f)',
                {"f": _victim},
            )

    def test_the_str_class_pivot_is_refused(self):
        with self.assertRaises(Exception):
            safe_eval('str.format("{0.__globals__[SECRET]}", f)', {"f": _victim})

    def test_format_map_is_refused(self):
        with self.assertRaises(Exception):
            safe_eval('"{0.__globals__[SECRET]}".format_map(m)', {"m": [_victim]})

    def test_a_compatibility_spelled_method_name_is_refused(self):
        # the parser NFKC-normalises identifiers: U+FF46 + "ormat" is `format`
        # although the source text never contains the ASCII word
        dunder = "__globals__"
        for expr in (
            '("{0." + d + "}").\uff46ormat(f)',
            'str.\uff46ormat("{0." + d + "}", f)',
            '("{0." + d + "}").\uff46ormat_map([f])',
            '("{0." + d + "}").ｆｏｒｍａｔ(f)',
        ):
            with self.subTest(expr=expr), self.assertRaises(ValueError) as caught:
                safe_eval(expr, {"f": _victim, "d": dunder})
            self.assertIn("attribute access is not allowed", str(caught.exception))

    def test_the_recordset_public_attribute_pivot_is_refused(self):

        class Rec:
            env = type("E", (), {"cr": type("C", (), {"dbname": "secretdb"})()})()

        with self.assertRaises(Exception):
            safe_eval('"{0.env.cr.dbname}".format(r)', {"r": Rec()})

    def test_a_leaked_secret_never_comes_back(self):
        _victim.__globals__["SECRET"] = SECRET
        try:
            for expr, ns in (
                ('"{0.__globals__[SECRET]}".format(f)', {"f": _victim}),
                ("t.format(f)", {"f": _victim, "t": "{0.__globals__[SECRET]}"}),
            ):
                try:
                    result = safe_eval(expr, ns)
                except Exception:  # noqa: S112 - the block below is the assertion
                    continue
                self.assertNotIn(SECRET, str(result))
        finally:
            _victim.__globals__.pop("SECRET", None)


class TestFormatLegitimateUsesUnaffected(unittest.TestCase):
    def test_numeric_and_positional_and_kwargs(self):
        self.assertEqual(safe_eval('"{:,.2f}".format(x)', {"x": 1234.5}), "1,234.50")
        self.assertEqual(safe_eval('"{}-{}".format(a, b)', {"a": 1, "b": 2}), "1-2")
        self.assertEqual(
            safe_eval('"{n}:{v:>6.2f}".format(n="x", v=3.14159)', {}), "x:  3.14"
        )

    def test_index_access_is_still_allowed(self):
        self.assertEqual(safe_eval('"{0[0]}-{0[1]}".format(p)', {"p": [7, 8]}), "7-8")

    def test_a_models_own_format_method_is_untouched(self):
        class FakeCurrency:
            def format(self, amount):
                return f"${amount}"

        self.assertEqual(safe_eval("c.format(v)", {"c": FakeCurrency(), "v": 9}), "$9")


if __name__ == "__main__":
    unittest.main()
