from odoo.tests import common, tagged
from odoo.tools._vendor.pdf417gen.compaction import compact, compact_bytes, compact_numbers, compact_text
from odoo.tools._vendor.pdf417gen.compaction import optimizations, _split_to_chunks, Chunk
from odoo.tools._vendor.pdf417gen.compaction.text import compact_text_interim
from odoo.tools._vendor.pdf417gen.encoding import to_bytes
from odoo.tools._vendor.pdf417gen.data import SWITCH_CODE_LOOKUP


@tagged('-at_install', 'post_install')
class TestCompaction(common.TransactionCase):

    def test_byte_compactor(self):
        def do_compact(str):
            return list(compact_bytes(to_bytes(str)))

        self.assertEqual(do_compact("alcool"), [163, 238, 432, 766, 244])
        self.assertEqual(do_compact("alcoolique"), [163, 238, 432, 766, 244, 105, 113, 117, 101])
        self.assertEqual(do_compact("\00alc\00l"), [0, 573, 880, 505, 712])

    def test_text_compactor_interim(self):
        def do_compact(str):
            return list(compact_text_interim(to_bytes(str)))

        # Latch codes for single-code transitions
        lm = SWITCH_CODE_LOOKUP['LOWER']['MIXED']
        ul = SWITCH_CODE_LOOKUP['UPPER']['LOWER']
        um = SWITCH_CODE_LOOKUP['UPPER']['MIXED']
        ml = SWITCH_CODE_LOOKUP['MIXED']['LOWER']
        mu = SWITCH_CODE_LOOKUP['MIXED']['UPPER']
        mp = SWITCH_CODE_LOOKUP['MIXED']['PUNCT']
        pu = SWITCH_CODE_LOOKUP['PUNCT']['UPPER']

        # Upper transitions
        self.assertEqual(do_compact("Ff"), [5, ul, 5])
        self.assertEqual(do_compact("F#"), [5, um, 15])
        self.assertEqual(do_compact("F!"), [5, um, mp, 10])

        # Lower transitions
        self.assertEqual(do_compact("fF"), [ul, 5, lm, mu, 5])
        self.assertEqual(do_compact("f#"), [ul, 5, lm, 15])
        self.assertEqual(do_compact("f!"), [ul, 5, lm, mp, 10])

        # Mixed transitions
        self.assertEqual(do_compact("#f"), [um, 15, ml, 5])
        self.assertEqual(do_compact("#F"), [um, 15, mu, 5])
        self.assertEqual(do_compact("#!"), [um, 15, mp, 10])

        # Punct transitions
        self.assertEqual(do_compact("!f"), [um, mp, 10, pu, ul, 5])
        self.assertEqual(do_compact("!F"), [um, mp, 10, pu, 5])
        self.assertEqual(do_compact("!#"), [um, mp, 10, pu, um, 15])


    # Bug where the letter g would be encoded as " in the PUNCT submode
    # https://github.com/ihabunek/pdf417-py/issues/8
    def test_text_compactor_interim_error_letter_g(self):
        def do_compact(str):
            return list(compact_text_interim(to_bytes(str)))

        self.assertEqual(do_compact(">g"), [
            28,  # switch to MIXED
            25,  # switch to PUNCT
            2,   # Encode >"
            29,  # switch to UPPER
            27,  # switch to LOWER
            6,   # encode g
        ])


    def test_text_compactor(self):
        def do_compact(str):
            return list(compact_text(to_bytes(str)))

        self.assertEqual(do_compact("Super "), [567, 615, 137, 809])
        self.assertEqual(do_compact("Super !"), [567, 615, 137, 808, 760])


    def test_numbers_compactor(self):
        numbers = [ord(x) for x in "01234"]
        self.assertEqual(list(compact_numbers(numbers)), [112, 434])


    def test_compact(self):
        def do_compact(str):
            return list(compact(to_bytes(str)))

        # When starting with text, the first code word does not need to be the switch
        # Use 13 digites to avoid optimization which keeps it in text mode
        self.assertEqual(do_compact("ABC1234567890123"), [
            1, 89, 902, 17, 110, 836, 811, 223
        ])

        # When starting with numbers, we do need to switch
        self.assertEqual(do_compact("1234567890123ABC"), [
            902, 17, 110, 836, 811, 223,
            900, 1, 89
        ])

        # Also with bytes
        self.assertEqual(do_compact(b"\x0B"), [901, 11])

        # Alternate bytes switch code when number of bytes is divisble by 6
        self.assertEqual(do_compact(b"\x0B\x0B\x0B\x0B\x0B\x0B"), [924, 18, 455, 694, 754, 291])


    def test_split_to_chunks(self):
        def chars(string):
            return [i for i in to_bytes(string)]

        test_cases = [
            ('aabb1122foobar💔', [
                ('aabb', compact_text),
                ('1122', compact_numbers),
                ('foobar', compact_text),
                ('💔', compact_bytes),
            ]),
        ]
        for data, expected in test_cases:
            with self.subTest(data=data):
                data = to_bytes(data)
                expected = [(chars(text), fn) for text, fn in expected]
                self.assertEqual(list(_split_to_chunks(data)), expected)


    def test_optimizations(self):
        def chars(string):
            return [i for i in to_bytes(string)]

        test_cases = [
            # Don't switch to text mode for chunks shorter than 13 numeric chars
            # if bordering text chunk
            ('foo1234567890bar', [
                ('foo1234567890bar', compact_text),
            ]),
            ('1234567890bar', [
                ('1234567890bar', compact_text),
            ]),
            ('foo1234567890', [
                ('foo1234567890', compact_text),
            ]),
            ('foo1234567890💔', [
                ('foo1234567890', compact_text),
                ('💔', compact_bytes),
            ]),
            ('💔1234567890foo', [
                ('💔', compact_bytes),
                ('1234567890foo', compact_text),
            ]),

            # Switch for 13+ chars or when not bordering text chunk
            ('foo1234567890123bar', [
                ('foo', compact_text),
                ('1234567890123', compact_numbers),
                ('bar', compact_text),
            ]),
            ('1234567890', [
                ('1234567890', compact_numbers),
            ]),
            ('💔1234567890💔', [
                ('💔', compact_bytes),
                ('1234567890', compact_numbers),
                ('💔', compact_bytes),
            ]),
        ]

        for data, expected in test_cases:
            with self.subTest(data=data):
                data = to_bytes(data)
                expected = [Chunk(chars(text), fn) for text, fn in expected]

                actual = _split_to_chunks(data)
                actual = optimizations.replace_short_numeric_chunks(actual)
                actual = optimizations.merge_chunks_with_same_compact_fn(actual)

                self.assertEqual(list(actual), expected)
