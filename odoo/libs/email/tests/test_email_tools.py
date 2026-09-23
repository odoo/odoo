import unittest
from typing import Any, ClassVar, Literal

from odoo.libs.email.parsing import (
    email_anonymize,
    email_domain_normalize,
    email_normalize,
    email_re,
    email_split,
    email_split_and_format,
    email_split_and_format_normalize,
    email_split_tuples,
    extract_rfc2822_addresses,
    formataddr,
    single_email_re,
)


class TestEmailTools(unittest.TestCase):
    sources: ClassVar[list[str]]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sources = [
            "alfred.astaire@test.example.com",
            " alfred.astaire@test.example.com ",
            "Fredo The Great <alfred.astaire@test.example.com>",
            '"Fredo The Great" <alfred.astaire@test.example.com>',
            'Fredo "The Great" <alfred.astaire@test.example.com>',
            "alfred.astaire@test.example.com, evelyne.gargouillis@test.example.com",
            "Fredo The Great <alfred.astaire@test.example.com>, Evelyne The Goat <evelyne.gargouillis@test.example.com>",
            '"Fredo The Great" <alfred.astaire@test.example.com>, evelyne.gargouillis@test.example.com',
            '"Fredo The Great" <alfred.astaire@test.example.com>, <evelyne.gargouillis@test.example.com>',
            "Hello alfred.astaire@test.example.com how are you ?",
            "<p>Hello alfred.astaire@test.example.com</p>",
            'Hello "Fredo" <alfred.astaire@test.example.com>, evelyne.gargouillis@test.example.com',
            'Hello "Fredo" <alfred.astaire@test.example.com> and evelyne.gargouillis@test.example.com',
            "<p>Hello Fredo</p>",
            'j\'adore écrire des @gmail.com ou "@gmail.com" a bit randomly',
            "",
        ]

    def test_email_domain_normalize(self):
        cases: list[tuple[Any, str | Literal[False], str]] = [
            ("Test.Com", "test.com", "Should have normalized domain"),
            (
                "email@test.com",
                False,
                "Domain is not valid, should return False",
            ),
            (False, False, "Domain is not valid, should retunr False"),
        ]
        for source, expected, msg in cases:
            self.assertEqual(email_domain_normalize(source), expected, msg)

    def test_email_normalize(self):
        format_name = "My Super Prénom"
        format_name_ascii = "=?utf-8?b?TXkgU3VwZXIgUHLDqW5vbQ==?="
        sources = [
            '"Super Déboulonneur" <deboulonneur@example.com>',
            "Déboulonneur deboulonneur@example.com",
            "deboulonneur@example.com Déboulonneur",
            '"Super Déboulonneur" <DEBOULONNEUR@example.com>, "Super Déboulonneur 2" <deboulonneur2@EXAMPLE.com>',
            " Déboulonneur deboulonneur@example.com déboulonneur deboulonneur2@example.com",
            '"Déboulonneur 😊" <deboulonneur.😊@example.com>',
            '"Déboulonneur" <déboulonneur@examplé.com>',
            '"Déboulonneur" <DéBoulonneur@Examplé.com>',
        ]
        expected_list: list[str | Literal[False]] = [
            "deboulonneur@example.com",
            "deboulonneur@example.com",
            "deboulonneur@example.comdéboulonneur",
            False,
            False,
            "deboulonneur.😊@example.com",
            "déboulonneur@examplé.com",
            "DéBoulonneur@examplé.com",
        ]
        expected_fmt_utf8_list = [
            f'"{format_name}" <deboulonneur@example.com>',
            f'"{format_name}" <deboulonneur@example.com>',
            f'"{format_name}" <deboulonneur@example.comdéboulonneur>',
            f'"{format_name}" <@>',
            f'"{format_name}" <@>',
            f'"{format_name}" <deboulonneur.😊@example.com>',
            f'"{format_name}" <déboulonneur@examplé.com>',
            f'"{format_name}" <DéBoulonneur@examplé.com>',
        ]
        expected_fmt_ascii_list = [
            f"{format_name_ascii} <deboulonneur@example.com>",
            f"{format_name_ascii} <deboulonneur@example.com>",
            f"{format_name_ascii} <deboulonneur@example.xn--comdboulonneur-ekb>",
            f"{format_name_ascii} <@>",
            f"{format_name_ascii} <@>",
            f"{format_name_ascii} <deboulonneur.😊@example.com>",
            f"{format_name_ascii} <déboulonneur@xn--exampl-gva.com>",
            f"{format_name_ascii} <DéBoulonneur@xn--exampl-gva.com>",
        ]
        for source, expected, expected_utf8_fmt, expected_ascii_fmt in zip(
            sources,
            expected_list,
            expected_fmt_utf8_list,
            expected_fmt_ascii_list,
            strict=False,
        ):
            with self.subTest(source=source):
                self.assertEqual(email_normalize(source, strict=True), expected)
                if not expected:
                    for charset in ("utf-8", "ascii"):
                        with self.assertRaises(ValueError):
                            formataddr((format_name, ""), charset=charset)
                    continue
                self.assertEqual(
                    formataddr((format_name, expected), charset="utf-8"),
                    expected_utf8_fmt,
                )
                self.assertEqual(
                    formataddr((format_name, expected), charset="ascii"),
                    expected_ascii_fmt,
                )

    def test_email_re(self):
        expected = [
            ["alfred.astaire@test.example.com"],
            ["alfred.astaire@test.example.com"],
            ["alfred.astaire@test.example.com"],
            ["alfred.astaire@test.example.com"],
            ["alfred.astaire@test.example.com"],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            ["alfred.astaire@test.example.com"],
            ["alfred.astaire@test.example.com"],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            [
                "alfred.astaire@test.example.com",
                "evelyne.gargouillis@test.example.com",
            ],
            [],
            [],
            [],
        ]

        for src, exp in zip(self.sources, expected, strict=False):
            res = email_re.findall(src)
            self.assertEqual(
                res,
                exp,
                "Seems email_re is broken with %s (expected %r, received %r)"
                % (src, exp, res),
            )

    def test_email_split(self):
        cases = [
            ("John <12345@gmail.com>", ["12345@gmail.com"]),
            ("d@x; 1@2", ["d@x", "1@2"]),
            (
                "'(ss)' <123@gmail.com>, 'foo' <foo@bar>",
                ["123@gmail.com", "foo@bar"],
            ),
            (
                '"john@gmail.com"<johnny@gmail.com>',
                ["johnny@gmail.com"],
            ),
            (
                '"<jg>" <johnny@gmail.com>',
                ["johnny@gmail.com"],
            ),
            ("@gmail.com", ["@gmail.com"]),
            ("fr@ncois.th@notgmail.com", ["fr@ncois.th"]),
            (
                "f@r@nc.gz,ois@notgmail.com",
                ["r@nc.gz", "ois@notgmail.com"],
            ),
            (
                "@notgmail.com esteban_gnole@coldmail.com@notgmail.com",
                ["esteban_gnole@coldmail.com"],
            ),
            (
                "Ivan@dezotos.com Cc iv.an@notgmail.com",
                ["Ivan@dezotos.com", "iv.an@notgmail.com"],
            ),
            (
                "ivan-dredi@coldmail.com ivan.dredi@notgmail.com",
                ["ivan-dredi@coldmail.com", "ivan.dredi@notgmail.com"],
            ),
            (
                "@notgmail.com ivan@coincoin.com.ar jeanine@coincoin.com.ar",
                ["ivan@coincoin.com.ar", "jeanine@coincoin.com.ar"],
            ),
            (
                "@notgmail.com whoareyou@youhou.com.   ivan.dezotos@notgmail.com",
                ["whoareyou@youhou.com", "ivan.dezotos@notgmail.com"],
            ),
            (
                "francois@nc.gz CC: ois@notgmail.com ivan@dezotos.com",
                ["francois@nc.gz", "ois@notgmail.com", "ivan@dezotos.com"],
            ),
            (
                "francois@nc.gz CC: ois@notgmail.com,ivan@dezotos.com",
                ["francois@nc.gzCC", "ois@notgmail.com", "ivan@dezotos.com"],
            ),
            (
                "ivan.plein@dezotos.com / ivan.plu@notgmail.com",
                ["ivan.plein@dezotos.com", "ivan.plu@notgmail.com"],
            ),
            (
                "@notgmail.com ivan.parfois@notgmail.com/ ivan.souvent@notgmail.com",
                ["ivan.parfois@notgmail.com", "ivan.souvent@notgmail.com"],
            ),
            (
                "ivan@dezotos.com - ivan.dezotos@notgmail.com",
                ["ivan@dezotos.com", "ivan.dezotos@notgmail.com"],
            ),
            (
                "car.pool@notgmail.com - co (TAMBO) Registration car.warsh@notgmail.com",
                ["car.pool@notgmail.com", "car.warsh@notgmail.com"],
            ),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(email_split(source), expected)

    def test_email_split_and_format(self):
        sources = [
            "deboulonneur@example.com",
            '"Super Déboulonneur" <deboulonneur@example.com>',
            "Déboulonneur <deboulonneur@example.com",
            "Déboulonneur deboulonneur@example.com",
            "deboulonneur@example.com Déboulonneur",
            "Déboulonneur, deboulonneur@example.com",
            "deboulonneur@example.com, deboulonneur2@example.com",
            " Déboulonneur deboulonneur@example.com déboulonneur deboulonneur2@example.com",
            '"Déboulonneur" <"Déboulonneur Encapsulated" <deboulonneur@example.com>>',
            '"Super Déboulonneur" <deboulonneur@example.com>, "Super Déboulonneur 2" <deboulonneur2@example.com>',
            '"Super Déboulonneur" <deboulonneur@example.com>, wrong, ',
            '"Déboulonneur 😊" <deboulonneur@example.com>',
            '"Déboulonneur 😊" <deboulonneur.😊@example.com>',
            '"Déboulonneur" <déboulonneur@examplé.com>',
            '"Déboulonneur" <DEboulonneur@😊.example.com>',
            '"Déboulonneur" <DÉBoulonneur.😊@Éxamplé.com>',
        ]
        expected_list = [
            ["deboulonneur@example.com"],
            ['"Super Déboulonneur" <deboulonneur@example.com>'],
            ['"Déboulonneur" <deboulonneur@example.com>'],
            ['"Déboulonneur" <deboulonneur@example.com>'],
            ["deboulonneur@example.comDéboulonneur"],
            ["deboulonneur@example.com"],
            ["deboulonneur@example.com", "deboulonneur2@example.com"],
            [
                "deboulonneur@example.com",
                "deboulonneur2@example.com",
            ],
            ["deboulonneur@example.com"],
            [
                '"Super Déboulonneur" <deboulonneur@example.com>',
                '"Super Déboulonneur 2" <deboulonneur2@example.com>',
            ],
            ['"Super Déboulonneur" <deboulonneur@example.com>'],
            ['"Déboulonneur 😊" <deboulonneur@example.com>'],
            ['"Déboulonneur 😊" <deboulonneur.😊@example.com>'],
            ['"Déboulonneur" <déboulonneur@examplé.com>'],
            ['"Déboulonneur" <DEboulonneur@😊.example.com>'],
            ['"Déboulonneur" <DÉBoulonneur.😊@Éxamplé.com>'],
        ]
        normalized = {
            "deboulonneur@example.com Déboulonneur": [
                "deboulonneur@example.comdéboulonneur"
            ],
            '"Déboulonneur" <DEboulonneur@😊.example.com>': [
                '"Déboulonneur" <deboulonneur@😊.example.com>'
            ],
            '"Déboulonneur" <DÉBoulonneur.😊@Éxamplé.com>': [
                '"Déboulonneur" <DÉBoulonneur.😊@éxamplé.com>'
            ],
        }
        for source, expected in zip(sources, expected_list, strict=False):
            with self.subTest(source=source):
                self.assertEqual(email_split_and_format(source), expected)
                self.assertEqual(
                    email_split_and_format_normalize(source),
                    normalized.get(source, expected),
                )

    def test_email_split_tuples(self):
        expected = [
            [("", "alfred.astaire@test.example.com")],
            [("", "alfred.astaire@test.example.com")],
            [("Fredo The Great", "alfred.astaire@test.example.com")],
            [("Fredo The Great", "alfred.astaire@test.example.com")],
            [("Fredo The Great", "alfred.astaire@test.example.com")],
            [
                ("", "alfred.astaire@test.example.com"),
                ("", "evelyne.gargouillis@test.example.com"),
            ],
            [
                ("Fredo The Great", "alfred.astaire@test.example.com"),
                ("Evelyne The Goat", "evelyne.gargouillis@test.example.com"),
            ],
            [
                ("Fredo The Great", "alfred.astaire@test.example.com"),
                ("", "evelyne.gargouillis@test.example.com"),
            ],
            [
                ("Fredo The Great", "alfred.astaire@test.example.com"),
                ("", "evelyne.gargouillis@test.example.com"),
            ],
            [("Hello", "alfred.astaire@test.example.comhowareyou?")],
            [("Hello", "alfred.astaire@test.example.com")],
            [
                ("Hello Fredo", "alfred.astaire@test.example.com"),
                ("", "evelyne.gargouillis@test.example.com"),
            ],
            [
                ("Hello Fredo", "alfred.astaire@test.example.com"),
                ("and", "evelyne.gargouillis@test.example.com"),
            ],
            [],
            [("j'adore écrire", "des@gmail.comou"), ("", "@gmail.com")],
            [],
        ]

        for src, exp in zip(self.sources, expected, strict=False):
            res = email_split_tuples(src)
            self.assertEqual(
                res,
                exp,
                "Seems email_split_tuples is broken with %s (expected %r, received %r)"
                % (src, exp, res),
            )

    def test_email_formataddr(self):
        email_base = "joe@example.com"
        email_idna = "joe@examplé.com"
        cases = [
            (("", email_base), ["ascii", "utf-8"], "joe@example.com"),
            (
                ("joe", email_base),
                ["ascii", "utf-8"],
                '"joe" <joe@example.com>',
            ),
            (
                ("joe doe", email_base),
                ["ascii", "utf-8"],
                '"joe doe" <joe@example.com>',
            ),
            (
                ('joe"doe', email_base),
                ["ascii", "utf-8"],
                '"joe\\"doe" <joe@example.com>',
            ),
            (
                ("joé", email_base),
                ["ascii"],
                "=?utf-8?b?am/DqQ==?= <joe@example.com>",
            ),
            (("joé", email_base), ["utf-8"], '"joé" <joe@example.com>'),
            (("", email_idna), ["ascii"], "joe@xn--exampl-gva.com"),
            (("", email_idna), ["utf-8"], "joe@examplé.com"),
            (
                ("joé", email_idna),
                ["ascii"],
                "=?utf-8?b?am/DqQ==?= <joe@xn--exampl-gva.com>",
            ),
            (("joé", email_idna), ["utf-8"], '"joé" <joe@examplé.com>'),
            (("", "joé@example.com"), ["ascii", "utf-8"], "joé@example.com"),
        ]

        for pair, charsets, expected in cases:
            for charset in charsets:
                with self.subTest(pair=pair, charset=charset):
                    self.assertEqual(formataddr(pair, charset), expected)

    def test_extract_rfc2822_addresses(self):
        cases = [
            ('"Admin" <admin@example.com>', ["admin@example.com"]),
            (
                '"Admin" <admin@example.com>, Demo <demo@test.com>',
                ["admin@example.com", "demo@test.com"],
            ),
            ("admin@example.com", ["admin@example.com"]),
            (
                '"Admin" <admin@example.com>, Demo <malformed email>',
                ["admin@example.com"],
            ),
            ("admin@éxample.com", ["admin@xn--xample-9ua.com"]),
            (
                '"admin@éxample.com" <admin@éxample.com>',
                ["admin@xn--xample-9ua.com", "admin@xn--xample-9ua.com"],
            ),
            (
                '"Robert Le Grand" <robert@notgmail.com>',
                ["robert@notgmail.com"],
            ),
            (
                '"robert@notgmail.com" <robert@notgmail.com>',
                ["robert@notgmail.com", "robert@notgmail.com"],
            ),
            ('"Bike @ Home" <bike@example.com>', ["bike@example.com"]),
            (
                '"Bike@Home" <bike@example.com>',
                ["Bike@Home", "bike@example.com"],
            ),
            (
                '"Not an Email" <robert@notgmail.com>, "robert@notgmail.com" <robert@notgmail.com>',
                [
                    "robert@notgmail.com",
                    "robert@notgmail.com",
                    "robert@notgmail.com",
                ],
            ),
            ("DéBoulonneur@examplé.com", ["DéBoulonneur@xn--exampl-gva.com"]),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(extract_rfc2822_addresses(source), expected)

    def test_single_email_re(self):
        expected = [
            ["alfred.astaire@test.example.com"],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        ]

        for src, exp in zip(self.sources, expected, strict=False):
            res = single_email_re.findall(src)
            self.assertEqual(
                res,
                exp,
                "Seems single_email_re is broken with %s (expected %r, received %r)"
                % (src, exp, res),
            )

    def test_email_anonymize(self):
        cases = [
            (
                "admin@example.com",
                "a****@example.com",
                "a****@e******.com",
            ),
            (
                "portal@example.com",
                "p***al@example.com",
                "p***al@e******.com",
            ),
            (
                "a@example.com",
                "a@example.com",
                "a@e******.com",
            ),
            (
                "joé@example.com",
                "j**@example.com",
                "j**@e******.com",
            ),
            (
                "élise@example.com",
                "é****@example.com",
                "é****@e******.com",
            ),
            (
                "admin@[127.0.0.1]",
                "a****@[127.0.0.1]",
                "a****@[127.0.0.1]",
            ),
            (
                "admin@[IPv6:::1]",
                "a****@[IPv6:::1]",
                "a****@[IPv6:::1]",
            ),
            ("", "", ""),
            (
                "@example.com",
                "@example.com",
                "@e******.com",
            ),
            ("john", "j***", "j***"),
            (
                "Jo <j@example.com>",
                "J****@example.com>",
                "J****@e******.com>",
            ),
            (
                "admin@com",
                "a****@com",
                "a****@com",
            ),
        ]
        for source, expected, expected_redacted_domain in cases:
            with self.subTest(source=source):
                self.assertEqual(email_anonymize(source), expected)
                self.assertEqual(
                    email_anonymize(source, redact_domain=True),
                    expected_redacted_domain,
                )
