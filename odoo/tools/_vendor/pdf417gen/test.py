from datetime import datetime
from xml.etree.ElementTree import ElementTree

import pytest
from mock import patch

from PIL.Image import Image

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


def il_performance_test_encode(cycles=100):
    start = datetime.now()
    for _ in range(cycles):
        encode(ZEN)
    duration = datetime.now() - start
    print("Encode x{}: {}".format(cycles, duration))


def il_performance_test_render_image(cycles=100):
    codes = encode(ZEN)
    start = datetime.now()
    for _ in range(cycles):
        render_image(codes)
    duration = datetime.now() - start
    print("Render image x{}: {}".format(cycles, duration))


def il_performance_test_render_svg(cycles=100):
    codes = encode(ZEN)
    start = datetime.now()
    for _ in range(cycles):
        render_svg(codes)
    duration = datetime.now() - start
    print("Render SVG x{}: {}".format(cycles, duration))


if __name__ == "__main__":
    il_performance_test_encode()
    il_performance_test_render_image()
    il_performance_test_render_svg()


def il_test_compaction_test_byte_compactor():
    def do_compact(str):
        return list(compact_bytes(to_bytes(str)))

    assert do_compact("alcool") == [163, 238, 432, 766, 244]
    assert do_compact("alcoolique") == [163, 238, 432, 766, 244, 105, 113, 117, 101]
    assert do_compact("\00alc\00l") == [0, 573, 880, 505, 712]

def il_test_compaction_test_text_compactor_interim():
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
    assert do_compact("Ff") == [5, ul, 5]
    assert do_compact("F#") == [5, um, 15]
    assert do_compact("F!") == [5, um, mp, 10]

    # Lower transitions
    assert do_compact("fF") == [ul, 5, lm, mu, 5]
    assert do_compact("f#") == [ul, 5, lm, 15]
    assert do_compact("f!") == [ul, 5, lm, mp, 10]

    # Mixed transitions
    assert do_compact("#f") == [um, 15, ml, 5]
    assert do_compact("#F") == [um, 15, mu, 5]
    assert do_compact("#!") == [um, 15, mp, 10]

    # Punct transitions
    assert do_compact("!f") == [um, mp, 10, pu, ul, 5]
    assert do_compact("!F") == [um, mp, 10, pu, 5]
    assert do_compact("!#") == [um, mp, 10, pu, um, 15]


# Bug where the letter g would be encoded as " in the PUNCT submode
# https://github.com/ihabunek/pdf417-py/issues/8
def il_test_compaction_test_text_compactor_interim_error_letter_g():
    def do_compact(str):
        return list(compact_text_interim(to_bytes(str)))

    assert do_compact(">g") == [
        28,  # switch to MIXED
        25,  # switch to PUNCT
        2,   # Encode >"
        29,  # switch to UPPER
        27,  # switch to LOWER
        6,   # encode g
    ]


def il_test_compaction_test_text_compactor():
    def do_compact(str):
        return list(compact_text(to_bytes(str)))

    assert do_compact("Super ") == [567, 615, 137, 809]
    assert do_compact("Super !") == [567, 615, 137, 808, 760]


def il_test_compaction_test_numbers_compactor():
    numbers = [ord(x) for x in "01234"]
    assert list(compact_numbers(numbers)) == [112, 434]


def il_test_compaction_test_compact():
    def do_compact(str):
        return list(compact(to_bytes(str)))

    # When starting with text, the first code word does not need to be the switch
    # Use 13 digites to avoid optimization which keeps it in text mode
    assert do_compact("ABC1234567890123") == [
        1, 89, 902, 17, 110, 836, 811, 223
    ]

    # When starting with numbers, we do need to switch
    assert do_compact("1234567890123ABC") == [
        902, 17, 110, 836, 811, 223,
        900, 1, 89
    ]

    # Also with bytes
    assert do_compact(b"\x0B") == [901, 11]

    # Alternate bytes switch code when number of bytes is divisble by 6
    assert do_compact(b"\x0B\x0B\x0B\x0B\x0B\x0B") == [924, 18, 455, 694, 754, 291]


@pytest.mark.parametrize("data,expected", [
    ('aabb1122foobar💔', [
        ('aabb', compact_text),
        ('1122', compact_numbers),
        ('foobar', compact_text),
        ('💔', compact_bytes),
    ]),
])
def il_test_compaction_test_split_to_chunks(data, expected):
    def chars(string):
        return [i for i in to_bytes(string)]

    data = to_bytes(data)
    expected = [(chars(text), fn) for text, fn in expected]
    assert list(_split_to_chunks(data)) == expected


@pytest.mark.parametrize("data,expected", [
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
])
def il_test_compaction_test_optimizations(data, expected):
    def chars(string):
        return [i for i in to_bytes(string)]

    data = to_bytes(data)
    expected = [Chunk(chars(text), fn) for text, fn in expected]

    actual = _split_to_chunks(data)
    actual = optimizations.replace_short_numeric_chunks(actual)
    actual = optimizations.merge_chunks_with_same_compact_fn(actual)

    assert list(actual) == expected


def il_test_console_test_print_usage(capsys):
    console.print_usage()
    out, err = capsys.readouterr()
    assert "Usage: pdf417gen [command]" in out
    assert not err


def il_test_console_test_print_err(capsys):
    console.print_err("foo")
    out, err = capsys.readouterr()
    assert not out
    assert "foo" in err


@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def il_test_console_test_encode(render_image, encode, capsys):
    text = "foo"

    console.do_encode([text])

    encode.assert_called_once_with(
        text,
        columns=6,
        encoding='utf-8',
        security_level=2
    )

    render_image.assert_called_once_with(
        'RETVAL',
        bg_color='#FFFFFF',
        fg_color='#000000',
        padding=20,
        ratio=3,
        scale=3
    )


@patch('sys.stdin.read', return_value="")
@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def il_test_console_test_encode_no_input(render_image, encode, read, capsys):
    console.do_encode([])

    encode.assert_not_called()
    render_image.assert_not_called()
    read.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert "No input given" in err


@patch('pdf417gen.console.encode', return_value="RETVAL")
@patch('pdf417gen.console.render_image')
def il_test_console_test_encode_exception(render_image, encode, capsys):
    encode.side_effect = ValueError("FAILED")

    console.do_encode(["foo"])

    encode.assert_called_once_with(
        "foo",
        columns=6,
        encoding='utf-8',
        security_level=2
    )
    render_image.assert_not_called()

    out, err = capsys.readouterr()
    assert not out
    assert "FAILED" in err


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


def il_test_encode_test_encode_high():

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

    assert encode_high(to_bytes(TEST_DATA), 6, 2) == expected


def il_test_encode_test_encode_low():

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

    assert list(encode(TEST_DATA, 6, 2)) == expected


def il_test_encode_test_encode_unicode():
    # These two should encode to the same string
    uc = u"love 💔"
    by = b"love \xf0\x9f\x92\x94"

    expected = [
        [130728, 120256, 108592, 115526, 126604, 103616, 66594, 126094, 128318, 260649],
        [130728, 125456, 83916, 107396, 83872, 97968, 77702, 98676, 128352, 260649],
        [130728, 86496, 128114, 90190, 98038, 72124, 72814, 81040, 86256, 260649]]

    assert encode(uc) == expected
    assert encode(by) == expected


def il_test_encode_test_max_barcode_size():
    # Borderline
    encode("x" * 1853, columns=16, security_level=6)

    # Data too long
    with pytest.raises(ValueError) as ex:
        encode("x" * 1854, columns=16, security_level=6)
    assert str(ex.value) == "Data too long. Generated bar code has length descriptor of 944. Maximum is 928."

    # Too few rows
    with pytest.raises(ValueError) as ex:
        encode("x", columns=16, security_level=1)
    assert str(ex.value) == "Generated bar code has 1 rows. Minimum is 3 rows. Try decreasing column count."

    # Too many rows
    with pytest.raises(ValueError) as ex:
        encode("x" * 1853, columns=8, security_level=6)
    assert str(ex.value) == "Generated bar code has 132 rows. Maximum is 90 rows. Try increasing column count."

codes = encode("hello world!")


def il_test_renderers_modules(codes):
    """Iterates over barcode codes and yields barcode moudles.

    Yields: column number (int), row number (int), module visibility (bool).
    """

    for row_id, row in enumerate(codes):
        col_id = 0
        for value in row:
            for digit in format(value, 'b'):
                yield col_id, row_id, digit == "1"
                col_id += 1


def il_test_renderers_test_rgb_to_hex():
    assert rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert rgb_to_hex((0, 255, 0)) == "#00ff00"
    assert rgb_to_hex((0, 0, 255)) == "#0000ff"

    assert rgb_to_hex((100, 0, 0)) == "#640000"
    assert rgb_to_hex((0, 100, 0)) == "#006400"
    assert rgb_to_hex((0, 0, 100)) == "#000064"

    assert rgb_to_hex((111, 222, 32)) == "#6fde20"


def il_test_renderers_test_render_svg():
    scale = 2
    ratio = 4
    description = "hi there"

    tree = render_svg(codes, scale=scale, ratio=ratio, description=description)
    assert isinstance(tree, ElementTree)
    assert tree.findtext("description") == description

    # Test expected size
    width, height = barcode_size(codes)

    root = tree.getroot()

    assert root.get("width") == str(width * scale)
    assert root.get("height") == str(height * scale * ratio)
    assert root.get("version") == "1.1"
    assert root.get("xmlns") == "http://www.w3.org/2000/svg"

    # Check number of rendered modules (only visible ones)
    expected_module_count = len([v for x, y, v in il_test_renderers_modules(codes) if v])
    actual_module_count = len(root.findall('g/rect'))

    assert expected_module_count == actual_module_count


def il_test_renderers_test_render_image():
    width, height = barcode_size(codes)

    image = render_image(codes)
    assert isinstance(image, Image)

    image = render_image(codes, scale=1, ratio=1, padding=0)
    assert image.size == (width, height)

    image = render_image(codes, scale=2, ratio=1, padding=0)
    assert image.size == (2 * width, 2 * height)

    image = render_image(codes, scale=2, ratio=2, padding=0)
    assert image.size == (2 * width, 4 * height)

    image = render_image(codes, scale=2, ratio=2, padding=20)
    assert image.size == (2 * width + 40, 4 * height + 40)

    # Check actual pixels
    fg_color = "LemonChiffon"
    bg_color = "#aabbcc"

    fg_parsed = (255, 250, 205)
    bg_parsed = (170, 187, 204)

    image = render_image(codes, scale=1, ratio=1, padding=0,
                         fg_color=fg_color, bg_color=bg_color)
    px = image.load()

    for column, row, visible in il_test_renderers_modules(codes):
        expected = fg_parsed if visible else bg_parsed
        assert px[column, row] == expected


def il_test_error_correction_test_error_correction():
    data = [16, 902, 1, 278, 827, 900, 295, 902, 2, 326, 823, 544, 900, 149, 900, 900]

    expected_level_0 = [156, 765]
    expected_level_1 = [168, 875, 63, 355]
    expected_level_2 = [628, 715, 393, 299, 863, 601, 169, 708]
    expected_level_3 = [232, 176, 793, 616, 476, 406, 855, 445, 84, 518, 522, 721, 607, 2, 42, 578]
    expected_level_4 = [281, 156, 276, 668, 44, 252, 877, 30, 549, 856, 773, 639, 420, 330, 693, 329, 283, 723, 480, 482, 102, 925, 535, 892, 374, 472, 837, 331, 343, 608, 390, 364]
    expected_level_5 = [31, 850, 18, 870, 53, 477, 837, 130, 533, 186, 266, 450, 39, 492, 542, 653, 499, 887, 618, 103, 364, 313, 906, 396, 270, 735, 593, 81, 557, 712, 810, 48, 167, 533, 205, 577, 503, 126, 449, 189, 859, 471, 493, 849, 554, 76, 878, 893, 168, 497, 251, 704, 311, 650, 283, 268, 462, 223, 659, 763, 176, 34, 544, 304]
    expected_level_6 = [345, 775, 909, 489, 650, 568, 869, 577, 574, 349, 885, 317, 492, 222, 783, 451, 647, 385, 168, 366, 118, 655, 643, 551, 179, 880, 880, 752, 132, 206, 765, 862, 727, 240, 32, 266, 911, 287, 813, 437, 868, 201, 681, 867, 567, 398, 508, 564, 504, 676, 785, 554, 831, 566, 424, 93, 515, 275, 61, 544, 272, 621, 374, 922, 779, 663, 789, 295, 631, 536, 755, 465, 485, 416, 76, 412, 76, 431, 28, 614, 767, 419, 600, 779, 94, 584, 647, 846, 121, 97, 790, 205, 424, 793, 263, 271, 694, 522, 437, 817, 382, 164, 113, 849, 178, 602, 554, 261, 415, 737, 401, 675, 203, 271, 649, 120, 765, 209, 522, 687, 420, 32, 60, 266, 270, 228, 304, 270]
    expected_level_7 = [142, 203, 799, 4, 105, 137, 793, 914, 225, 636, 60, 171, 490, 180, 414, 141, 399, 599, 829, 288, 108, 268, 444, 481, 795, 146, 655, 778, 189, 32, 597, 206, 208, 711, 845, 608, 642, 636, 540, 795, 845, 466, 492, 659, 138, 800, 912, 171, 92, 438, 225, 301, 777, 449, 230, 448, 326, 182, 892, 681, 543, 582, 732, 758, 162, 587, 685, 378, 646, 356, 354, 25, 839, 839, 556, 253, 501, 771, 745, 616, 473, 293, 669, 822, 613, 684, 229, 265, 110, 438, 144, 727, 317, 605, 414, 497, 82, 278, 267, 323, 43, 894, 624, 282, 790, 579, 430, 255, 802, 553, 922, 604, 68, 692, 809, 909, 663, 589, 735, 670, 298, 158, 201, 68, 124, 64, 67, 338, 694, 373, 225, 579, 309, 699, 920, 432, 717, 72, 126, 819, 142, 755, 473, 630, 331, 758, 730, 65, 359, 451, 236, 16, 56, 31, 87, 587, 125, 385, 384, 197, 352, 383, 173, 271, 38, 558, 810, 260, 521, 680, 7, 319, 650, 334, 695, 708, 0, 562, 365, 204, 114, 185, 560, 746, 767, 449, 797, 688, 63, 135, 818, 805, 3, 536, 908, 532, 400, 698, 49, 212, 630, 93, 157, 275, 3, 20, 611, 179, 302, 282, 876, 665, 241, 206, 474, 80, 217, 460, 462, 751, 719, 571, 536, 794, 522, 385, 598, 756, 162, 212, 758, 662, 361, 223, 587, 857, 503, 382, 615, 86, 283, 541, 847, 518, 406, 736, 486, 408, 226, 342, 784, 772, 211, 888, 234, 335]
    expected_level_8 = [538, 446, 840, 510, 163, 708, 177, 666, 423, 600, 707, 913, 770, 571, 156, 683, 676, 697, 898, 776, 128, 851, 163, 854, 135, 661, 880, 279, 92, 324, 397, 207, 379, 223, 574, 9, 70, 858, 878, 579, 61, 551, 261, 388, 315, 856, 266, 865, 923, 38, 313, 62, 381, 198, 265, 256, 385, 878, 347, 532, 821, 53, 855, 225, 697, 826, 263, 334, 207, 565, 460, 496, 705, 599, 383, 289, 178, 168, 401, 268, 555, 190, 922, 284, 180, 810, 891, 832, 636, 813, 894, 495, 701, 484, 204, 793, 129, 164, 444, 228, 636, 98, 809, 57, 736, 697, 727, 534, 889, 480, 898, 773, 234, 851, 880, 843, 714, 443, 412, 489, 578, 468, 367, 663, 11, 686, 319, 352, 345, 670, 106, 106, 219, 466, 439, 350, 538, 66, 852, 175, 465, 731, 332, 110, 926, 491, 18, 422, 736, 797, 624, 376, 728, 526, 735, 200, 502, 923, 789, 529, 923, 706, 384, 869, 172, 548, 520, 463, 813, 384, 793, 231, 190, 653, 864, 351, 400, 525, 487, 828, 654, 307, 141, 638, 770, 775, 282, 54, 758, 197, 492, 320, 86, 790, 275, 237, 923, 25, 591, 605, 61, 824, 79, 631, 532, 337, 867, 423, 340, 597, 682, 923, 287, 408, 503, 361, 881, 196, 468, 759, 746, 389, 124, 784, 198, 865, 538, 451, 178, 772, 653, 121, 497, 598, 711, 716, 241, 159, 429, 88, 799, 761, 639, 105, 54, 807, 351, 435, 793, 873, 360, 8, 881, 479, 693, 576, 849, 875, 771, 621, 134, 863, 8, 171, 799, 924, 103, 63, 491, 538, 597, 855, 697, 499, 7, 886, 286, 85, 107, 220, 319, 124, 197, 150, 729, 899, 585, 540, 676, 414, 256, 856, 596, 259, 882, 436, 26, 273, 753, 127, 679, 390, 654, 42, 276, 420, 247, 629, 116, 803, 131, 25, 403, 645, 462, 897, 151, 622, 108, 167, 227, 831, 887, 662, 739, 263, 829, 56, 624, 317, 908, 378, 39, 393, 861, 338, 202, 179, 907, 109, 360, 736, 554, 342, 594, 125, 433, 394, 195, 698, 844, 912, 530, 842, 337, 294, 528, 231, 735, 93, 8, 579, 42, 148, 609, 233, 782, 887, 888, 915, 620, 78, 137, 161, 282, 217, 775, 564, 33, 195, 36, 584, 679, 775, 476, 309, 230, 303, 708, 143, 679, 502, 814, 193, 508, 532, 542, 580, 603, 641, 338, 361, 542, 537, 810, 394, 764, 136, 167, 611, 881, 775, 267, 433, 142, 202, 828, 363, 101, 728, 660, 583, 483, 786, 717, 190, 809, 422, 567, 741, 695, 310, 120, 177, 47, 494, 345, 508, 16, 639, 402, 625, 286, 298, 358, 54, 705, 916, 291, 424, 375, 883, 655, 675, 498, 498, 884, 862, 365, 310, 805, 763, 855, 354, 777, 543, 53, 773, 120, 408, 234, 728, 438, 914, 3, 670, 546, 465, 449, 923, 51, 546, 709, 648, 96, 320, 682, 326, 848, 234, 855, 791, 20, 97, 901, 351, 317, 764, 767, 312, 206, 139, 610, 578, 646, 264, 389, 238, 675, 595, 430, 88]

    assert compute_error_correction_code_words(data, 0) == expected_level_0
    assert compute_error_correction_code_words(data, 1) == expected_level_1
    assert compute_error_correction_code_words(data, 2) == expected_level_2
    assert compute_error_correction_code_words(data, 3) == expected_level_3
    assert compute_error_correction_code_words(data, 4) == expected_level_4
    assert compute_error_correction_code_words(data, 5) == expected_level_5
    assert compute_error_correction_code_words(data, 6) == expected_level_6
    assert compute_error_correction_code_words(data, 7) == expected_level_7
    assert compute_error_correction_code_words(data, 8) == expected_level_8
