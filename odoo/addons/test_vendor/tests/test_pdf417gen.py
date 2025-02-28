from datetime import datetime, timedelta
from xml.etree.ElementTree import ElementTree

from PIL.Image import Image

from odoo.tests.common import TransactionCase, tagged
from odoo.tools._vendor.pdf417gen.pdf417gen import (
    Bytes,
    Chunk,
    Encoding,
    ErrorCorrection,
    Init,
    Numeric,
    Optimizations,
    Rendering,
    Util,
    Text,
    SWITCH_CODE_LOOKUP,
    TEXT_LATCH,
    NUMERIC_LATCH
)

@tagged('-at_install', 'post_install')
class PerformanceTest(TransactionCase):

    ZEN = """
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
    """.strip()

    def test_encode(self, cycles=100):
        start = datetime.now()
        for _ in range(cycles):
            Encoding.encode(self.ZEN)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(milliseconds=500))

    def test_render_image(self, cycles=100):
        codes = Encoding.encode(self.ZEN)
        start = datetime.now()
        for _ in range(cycles):
            Rendering.render_image(codes)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(milliseconds=500))

    def test_render_svg(self, cycles=100):
        codes = Encoding.encode(self.ZEN)
        start = datetime.now()
        for _ in range(cycles):
            Rendering.render_svg(codes)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(seconds=2))


@tagged('-at_install', 'post_install')
class CompactionTest(TransactionCase):
    def test_byte_compactor(self):
        def do_compact(str):
            return list(Bytes.compact_bytes(Util.to_bytes(str)))

        self.assertEqual(do_compact("alcool"), [163, 238, 432, 766, 244])
        self.assertEqual(do_compact("alcoolique"), [163, 238, 432, 766, 244, 105, 113, 117, 101])
        self.assertEqual(do_compact("\00alc\00l"), [0, 573, 880, 505, 712])

    def test_text_compactor_interim(self):
        def do_compact(str):
            return list(Text.compact_text_interim(Util.to_bytes(str)))

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
            return list(Text.compact_text_interim(Util.to_bytes(str)))

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
            return list(Text.compact_text(Util.to_bytes(str)))

        self.assertEqual(do_compact("Super "), [567, 615, 137, 809])
        self.assertEqual(do_compact("Super !"), [567, 615, 137, 808, 760])


    def test_numbers_compactor(self):
        numbers = [ord(x) for x in "01234"]
        self.assertEqual(list(Numeric.compact_numbers(numbers)), [112, 434])


    def test_compact(self):
        def do_compact(str):
            return list(Init.compact(Util.to_bytes(str)))

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


@tagged('-at_install', 'post_install')
class InitTest(TransactionCase):
    def test_split_to_chunks(self):
        def chars(string):
            return [i for i in Util.to_bytes(string)]

        TESTS = [
            ('aabb1122foobar💔', [
                ('aabb', Text.compact_text),
                ('1122', Numeric.compact_numbers),
                ('foobar', Text.compact_text),
                ('💔', Bytes.compact_bytes),
            ]),
        ]
        for data, expected in TESTS:
            with self.subTest():
                data = Util.to_bytes(data)
                expected = [(chars(text), fn) for text, fn in expected]
                self.assertEqual(list(Init._split_to_chunks(data)), expected)


@tagged('-at_install', 'post_install')
class OptimizationsTest(TransactionCase):
    def test_optimizations(self):
        def chars(string):
            return [i for i in Util.to_bytes(string)]

        TESTS = [
            # Don't switch to text mode for chunks shorter than 13 numeric chars
            # if bordering text chunk
            ('foo1234567890bar', [
                ('foo1234567890bar', Text.compact_text),
            ]),
            ('1234567890bar', [
                ('1234567890bar', Text.compact_text),
            ]),
            ('foo1234567890', [
                ('foo1234567890', Text.compact_text),
            ]),
            ('foo1234567890💔', [
                ('foo1234567890', Text.compact_text),
                ('💔', Bytes.compact_bytes),
            ]),
            ('💔1234567890foo', [
                ('💔', Bytes.compact_bytes),
                ('1234567890foo', Text.compact_text),
            ]),

            # Switch for 13+ chars or when not bordering text chunk
            ('foo1234567890123bar', [
                ('foo', Text.compact_text),
                ('1234567890123', Numeric.compact_numbers),
                ('bar', Text.compact_text),
            ]),
            ('1234567890', [
                ('1234567890', Numeric.compact_numbers),
            ]),
            ('💔1234567890💔', [
                ('💔', Bytes.compact_bytes),
                ('1234567890', Numeric.compact_numbers),
                ('💔', Bytes.compact_bytes),
            ]),
        ]

        for data, expected in TESTS:
            with self.subTest():
                data = Util.to_bytes(data)
                expected = [Chunk(chars(text), fn) for text, fn in expected]

                actual = Init._split_to_chunks(data)
                actual = Optimizations.replace_short_numeric_chunks(actual)
                actual = Optimizations.merge_chunks_with_same_compact_fn(actual)

                self.assertEqual(list(actual), expected)


@tagged('-at_install', 'post_install')
class EncodingTest(TransactionCase):

    TEST_DATA = '\n'.join([
        'HRVHUB30',
        'HRK',
        '000000010000000',
        'Ivan Habunek',
        'Savska cesta 13',
        '10000 Zagreb',
        'Big Fish Software d.o.o.',
        'Savska cesta 13',
        '10000 Zagreb',
        'HR6623400091110651272',
        '00',
        'HR123456',
        'ANTS',
        'Razvoj paketa za bar kodove\n'
    ])

    def test_encode_high(self):

        # High level encoding
        expected = [
            130, 227, 637, 601, 843, 25, 479, 227, 328, 765,

            NUMERIC_LATCH, 1, 624, 142, 113, 522, 200,

            TEXT_LATCH, 865, 479, 267, 630, 416, 868, 237, 1, 613, 130, 865, 479,
            567, 21, 550, 26, 64, 559, 26, 841, 115, 479, 841, 0, 0, 808, 777, 6,
            514, 58, 765, 871, 818, 206, 868, 177, 258, 236, 868, 567, 425, 592, 17,
            146, 118, 537, 448, 537, 448, 535, 479, 567, 21, 550, 26, 64, 559, 26,
            841, 115, 479, 841, 0, 0, 808, 777, 6, 514, 58, 765, 877, 539,

            NUMERIC_LATCH, 31, 251, 786, 557, 565, 1, 372,

            TEXT_LATCH, 865, 479, 840, 25, 479, 227, 841, 63, 125, 205, 479, 13,
            588, 865, 479, 537, 25, 644, 296, 450, 304, 570, 805, 26, 30, 536, 314,
            104, 634, 865, 479, 73, 714, 436, 412, 39, 661, 428, 120

        ]

        self.assertEqual(Encoding.encode_high(Util.to_bytes(self.TEST_DATA), 6, 2), expected)

    def test_encode_low(self):

        # Low level encoding
        expected = [
            [130728, 119920, 82192, 93980, 67848, 99590, 66798, 110200, 128318, 260649],
            [130728, 129678, 101252, 127694, 75652, 113982, 97944, 129720, 129678, 260649],
            [130728, 86496, 66846, 104188, 106814, 96800, 93944, 102290, 119934, 260649],
            [130728, 128190, 73160, 96008, 102812, 67872, 115934, 73156, 119520, 260649],
            [130728, 120588, 104224, 129720, 129938, 119200, 81084, 101252, 120588, 260649],
            [130728, 125892, 113798, 88188, 71822, 129766, 108158, 113840, 120784, 260649],
            [130728, 85880, 120638, 66758, 119006, 96008, 66758, 120256, 85560, 260649],
            [130728, 128176, 128352, 99048, 123146, 128280, 115920, 110492, 128176, 260649],
            [130728, 129634, 99166, 67438, 81644, 127604, 67404, 111676, 85054, 260649],
            [130728, 107422, 91664, 121136, 73156, 78032, 79628, 99680, 107452, 260649],
            [130728, 119692, 125744, 107396, 85894, 70600, 123914, 70600, 119692, 260649],
            [130728, 129588, 77902, 105628, 67960, 113798, 88188, 71822, 107390, 260649],
            [130728, 82208, 120638, 108348, 117798, 120638, 66758, 119006, 106672, 260649],
            [130728, 128070, 101252, 123018, 128352, 128352, 99048, 123146, 128070, 260649],
            [130728, 82206, 108792, 72094, 84028, 99166, 69442, 97048, 82108, 260649],
            [130728, 124350, 81384, 89720, 91712, 67618, 112848, 69712, 104160, 260649],
            [130728, 83928, 129720, 116966, 97968, 81084, 101252, 127450, 83928, 260649],
            [130728, 124392, 128456, 67960, 121150, 98018, 85240, 82206, 124388, 260649],
            [130728, 126222, 112152, 96008, 120560, 77928, 73160, 96008, 111648, 260649],
            [130728, 82918, 70600, 125702, 78322, 121744, 116762, 103328, 82918, 260649],
            [130728, 74992, 80048, 73296, 129766, 128450, 97072, 116210, 93424, 260649],
            [130728, 93744, 106800, 101784, 73160, 96008, 125116, 126828, 112440, 260649],
            [130728, 127628, 120948, 102632, 120582, 78074, 128532, 85966, 127628, 260649],
        ]

        self.assertEqual(list(Encoding.encode(self.TEST_DATA, 6, 2)), expected)

    def test_encode_unicode(self):
        # These two should encode to the same string
        uc = u"love 💔"
        by = b"love \xf0\x9f\x92\x94"

        expected = [
            [130728, 120256, 108592, 115526, 126604, 103616, 66594, 126094, 128318, 260649],
            [130728, 125456, 83916, 107396, 83872, 97968, 77702, 98676, 128352, 260649],
            [130728, 86496, 128114, 90190, 98038, 72124, 72814, 81040, 86256, 260649]]

        self.assertEqual(Encoding.encode(uc), expected)
        self.assertEqual(Encoding.encode(by), expected)

    def test_max_barcode_size(self):
        # Borderline
        Encoding.encode("x" * 1853, columns=16, security_level=6)

        # Data too long
        with self.assertRaises(ValueError) as ex:
            Encoding.encode("x" * 1854, columns=16, security_level=6)
            self.assertEqual(str(ex.value), "Data too long. Generated bar code has length descriptor of 944. Maximum is 928.")

        # Too few rows
        with self.assertRaises(ValueError) as ex:
            Encoding.encode("x", columns=16, security_level=1)
            self.assertEqual(str(ex.value), "Generated bar code has 1 rows. Minimum is 3 rows. Try decreasing column count.")

        # Too many rows
        with self.assertRaises(ValueError) as ex:
            Encoding.encode("x" * 1853, columns=8, security_level=6)
            self.assertEqual(str(ex.value), "Generated bar code has 132 rows. Maximum is 90 rows. Try increasing column count.")


@tagged('-at_install', 'post_install')
class RenderingTest(TransactionCase):
    codes = Encoding.encode("hello world!")
    
    def modules(self, codes):
        """Iterates over barcode codes and yields barcode moudles.

        Yields: column number (int), row number (int), module visibility (bool).
        """

        for row_id, row in enumerate(codes):
            col_id = 0
            for value in row:
                for digit in format(value, 'b'):
                    yield col_id, row_id, digit == "1"
                    col_id += 1


    def test_rgb_to_hex(self):
        self.assertEqual(Rendering.rgb_to_hex((255, 0, 0)), "#ff0000")
        self.assertEqual(Rendering.rgb_to_hex((0, 255, 0)), "#00ff00")
        self.assertEqual(Rendering.rgb_to_hex((0, 0, 255)), "#0000ff")

        self.assertEqual(Rendering.rgb_to_hex((100, 0, 0)), "#640000")
        self.assertEqual(Rendering.rgb_to_hex((0, 100, 0)), "#006400")
        self.assertEqual(Rendering.rgb_to_hex((0, 0, 100)), "#000064")

        self.assertEqual(Rendering.rgb_to_hex((111, 222, 32)), "#6fde20")


    def test_render_svg(self):
        scale = 2
        ratio = 4
        description = "hi there"

        tree = Rendering.render_svg(self.codes, scale=scale, ratio=ratio, description=description)
        self.assertTrue(isinstance(tree, ElementTree))
        self.assertEqual(tree.findtext("description"), description)

        # Test expected size
        width, height = Rendering.barcode_size(self.codes)

        root = tree.getroot()

        self.assertEqual(root.get("width"), str(width * scale))
        self.assertEqual(root.get("height"), str(height * scale * ratio))
        self.assertEqual(root.get("version"), "1.1")
        self.assertEqual(root.get("xmlns"), "http://www.w3.org/2000/svg")

        # Check number of rendered modules (only visible ones)
        expected_module_count = len([v for x, y, v in self.modules(self.codes) if v])
        actual_module_count = len(root.findall('g/rect'))

        self.assertEqual(expected_module_count, actual_module_count)


    def test_render_image(self):
        width, height = Rendering.barcode_size(self.codes)

        image = Rendering.render_image(self.codes)
        self.assertTrue(isinstance(image, Image))

        image = Rendering.render_image(self.codes, scale=1, ratio=1, padding=0)
        self.assertEqual(image.size, (width, height))

        image = Rendering.render_image(self.codes, scale=2, ratio=1, padding=0)
        self.assertEqual(image.size, (2 * width, 2 * height))

        image = Rendering.render_image(self.codes, scale=2, ratio=2, padding=0)
        self.assertEqual(image.size, (2 * width, 4 * height))

        image = Rendering.render_image(self.codes, scale=2, ratio=2, padding=20)
        self.assertEqual(image.size, (2 * width + 40, 4 * height + 40))

        # Check actual pixels
        fg_color = "LemonChiffon"
        bg_color = "#aabbcc"

        fg_parsed = (255, 250, 205)
        bg_parsed = (170, 187, 204)

        image = Rendering.render_image(self.codes, scale=1, ratio=1, padding=0,
                             fg_color=fg_color, bg_color=bg_color)
        px = image.load()

        for column, row, visible in self.modules(self.codes):
            expected = fg_parsed if visible else bg_parsed
            self.assertEqual(px[column, row], expected)


@tagged('-at_install', 'post_install')
class ErrorCorrectionTest(TransactionCase):

    def test_error_correction(self):
        data = [16, 902, 1, 278, 827, 900, 295, 902, 2, 326, 823, 544, 900, 149, 900, 900]

        expected_level_0 = [156, 765]
        expected_level_1 = [168, 875, 63, 355]
        expected_level_2 = [628, 715, 393, 299, 863, 601, 169, 708]
        expected_level_3 = [232, 176, 793, 616, 476, 406, 855, 445, 84, 518, 522, 721, 607, 2, 42,
                            578]
        expected_level_4 = [281, 156, 276, 668, 44, 252, 877, 30, 549, 856, 773, 639, 420, 330, 693,
                            329, 283, 723, 480, 482, 102, 925, 535, 892, 374, 472, 837, 331, 343,
                            608, 390, 364]
        expected_level_5 = [31, 850, 18, 870, 53, 477, 837, 130, 533, 186, 266, 450, 39, 492, 542,
                            653, 499, 887, 618, 103, 364, 313, 906, 396, 270, 735, 593, 81, 557,
                            712, 810, 48, 167, 533, 205, 577, 503, 126, 449, 189, 859, 471, 493,
                            849, 554, 76, 878, 893, 168, 497, 251, 704, 311, 650, 283, 268, 462,
                            223, 659, 763, 176, 34, 544, 304]
        expected_level_6 = [345, 775, 909, 489, 650, 568, 869, 577, 574, 349, 885, 317, 492, 222,
                            783, 451, 647, 385, 168, 366, 118, 655, 643, 551, 179, 880, 880, 752,
                            132, 206, 765, 862, 727, 240, 32, 266, 911, 287, 813, 437, 868, 201,
                            681, 867, 567, 398, 508, 564, 504, 676, 785, 554, 831, 566, 424, 93,
                            515, 275, 61, 544, 272, 621, 374, 922, 779, 663, 789, 295, 631, 536,
                            755, 465, 485, 416, 76, 412, 76, 431, 28, 614, 767, 419, 600, 779, 94,
                            584, 647, 846, 121, 97, 790, 205, 424, 793, 263, 271, 694, 522, 437,
                            817, 382, 164, 113, 849, 178, 602, 554, 261, 415, 737, 401, 675, 203,
                            271, 649, 120, 765, 209, 522, 687, 420, 32, 60, 266, 270, 228, 304, 270]
        expected_level_7 = [142, 203, 799, 4, 105, 137, 793, 914, 225, 636, 60, 171, 490, 180, 414,
                            141, 399, 599, 829, 288, 108, 268, 444, 481, 795, 146, 655, 778, 189,
                            32, 597, 206, 208, 711, 845, 608, 642, 636, 540, 795, 845, 466, 492,
                            659, 138, 800, 912, 171, 92, 438, 225, 301, 777, 449, 230, 448, 326,
                            182, 892, 681, 543, 582, 732, 758, 162, 587, 685, 378, 646, 356, 354,
                            25, 839, 839, 556, 253, 501, 771, 745, 616, 473, 293, 669, 822, 613,
                            684, 229, 265, 110, 438, 144, 727, 317, 605, 414, 497, 82, 278, 267,
                            323, 43, 894, 624, 282, 790, 579, 430, 255, 802, 553, 922, 604, 68, 692,
                            809, 909, 663, 589, 735, 670, 298, 158, 201, 68, 124, 64, 67, 338, 694,
                            373, 225, 579, 309, 699, 920, 432, 717, 72, 126, 819, 142, 755, 473,
                            630, 331, 758, 730, 65, 359, 451, 236, 16, 56, 31, 87, 587, 125, 385,
                            384, 197, 352, 383, 173, 271, 38, 558, 810, 260, 521, 680, 7, 319, 650,
                            334, 695, 708, 0, 562, 365, 204, 114, 185, 560, 746, 767, 449, 797, 688,
                            63, 135, 818, 805, 3, 536, 908, 532, 400, 698, 49, 212, 630, 93, 157,
                            275, 3, 20, 611, 179, 302, 282, 876, 665, 241, 206, 474, 80, 217, 460,
                            462, 751, 719, 571, 536, 794, 522, 385, 598, 756, 162, 212, 758, 662,
                            361, 223, 587, 857, 503, 382, 615, 86, 283, 541, 847, 518, 406, 736,
                            486, 408, 226, 342, 784, 772, 211, 888, 234, 335]
        expected_level_8 = [538, 446, 840, 510, 163, 708, 177, 666, 423, 600, 707, 913, 770, 571,
                            156, 683, 676, 697, 898, 776, 128, 851, 163, 854, 135, 661, 880, 279,
                            92, 324, 397, 207, 379, 223, 574, 9, 70, 858, 878, 579, 61, 551, 261,
                            388, 315, 856, 266, 865, 923, 38, 313, 62, 381, 198, 265, 256, 385, 878,
                            347, 532, 821, 53, 855, 225, 697, 826, 263, 334, 207, 565, 460, 496,
                            705, 599, 383, 289, 178, 168, 401, 268, 555, 190, 922, 284, 180, 810,
                            891, 832, 636, 813, 894, 495, 701, 484, 204, 793, 129, 164, 444, 228,
                            636, 98, 809, 57, 736, 697, 727, 534, 889, 480, 898, 773, 234, 851, 880,
                            843, 714, 443, 412, 489, 578, 468, 367, 663, 11, 686, 319, 352, 345,
                            670, 106, 106, 219, 466, 439, 350, 538, 66, 852, 175, 465, 731, 332,
                            110, 926, 491, 18, 422, 736, 797, 624, 376, 728, 526, 735, 200, 502,
                            923, 789, 529, 923, 706, 384, 869, 172, 548, 520, 463, 813, 384, 793,
                            231, 190, 653, 864, 351, 400, 525, 487, 828, 654, 307, 141, 638, 770,
                            775, 282, 54, 758, 197, 492, 320, 86, 790, 275, 237, 923, 25, 591, 605,
                            61, 824, 79, 631, 532, 337, 867, 423, 340, 597, 682, 923, 287, 408, 503,
                            361, 881, 196, 468, 759, 746, 389, 124, 784, 198, 865, 538, 451, 178,
                            772, 653, 121, 497, 598, 711, 716, 241, 159, 429, 88, 799, 761, 639,
                            105, 54, 807, 351, 435, 793, 873, 360, 8, 881, 479, 693, 576, 849, 875,
                            771, 621, 134, 863, 8, 171, 799, 924, 103, 63, 491, 538, 597, 855, 697,
                            499, 7, 886, 286, 85, 107, 220, 319, 124, 197, 150, 729, 899, 585, 540,
                            676, 414, 256, 856, 596, 259, 882, 436, 26, 273, 753, 127, 679, 390,
                            654, 42, 276, 420, 247, 629, 116, 803, 131, 25, 403, 645, 462, 897, 151,
                            622, 108, 167, 227, 831, 887, 662, 739, 263, 829, 56, 624, 317, 908,
                            378, 39, 393, 861, 338, 202, 179, 907, 109, 360, 736, 554, 342, 594,
                            125, 433, 394, 195, 698, 844, 912, 530, 842, 337, 294, 528, 231, 735,
                            93, 8, 579, 42, 148, 609, 233, 782, 887, 888, 915, 620, 78, 137, 161,
                            282, 217, 775, 564, 33, 195, 36, 584, 679, 775, 476, 309, 230, 303, 708,
                            143, 679, 502, 814, 193, 508, 532, 542, 580, 603, 641, 338, 361, 542,
                            537, 810, 394, 764, 136, 167, 611, 881, 775, 267, 433, 142, 202, 828,
                            363, 101, 728, 660, 583, 483, 786, 717, 190, 809, 422, 567, 741, 695,
                            310, 120, 177, 47, 494, 345, 508, 16, 639, 402, 625, 286, 298, 358, 54,
                            705, 916, 291, 424, 375, 883, 655, 675, 498, 498, 884, 862, 365, 310,
                            805, 763, 855, 354, 777, 543, 53, 773, 120, 408, 234, 728, 438, 914, 3,
                            670, 546, 465, 449, 923, 51, 546, 709, 648, 96, 320, 682, 326, 848, 234,
                            855, 791, 20, 97, 901, 351, 317, 764, 767, 312, 206, 139, 610, 578, 646,
                            264, 389, 238, 675, 595, 430, 88]

        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 0), expected_level_0)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 1), expected_level_1)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 2), expected_level_2)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 3), expected_level_3)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 4), expected_level_4)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 5), expected_level_5)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 6), expected_level_6)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 7), expected_level_7)
        self.assertEqual(ErrorCorrection.compute_error_correction_code_words(data, 8), expected_level_8)
