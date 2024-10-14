import math
import re
from typing import List

from qrcode import LUT, base, exceptions
from qrcode.base import RSBlock

# QR encoding modes.
MODE_NUMBER = 1 << 0
MODE_ALPHA_NUM = 1 << 1
MODE_8BIT_BYTE = 1 << 2
MODE_KANJI = 1 << 3

# Encoding mode sizes.
MODE_SIZE_SMALL = {
    MODE_NUMBER: 10,
    MODE_ALPHA_NUM: 9,
    MODE_8BIT_BYTE: 8,
    MODE_KANJI: 8,
}
MODE_SIZE_MEDIUM = {
    MODE_NUMBER: 12,
    MODE_ALPHA_NUM: 11,
    MODE_8BIT_BYTE: 16,
    MODE_KANJI: 10,
}
MODE_SIZE_LARGE = {
    MODE_NUMBER: 14,
    MODE_ALPHA_NUM: 13,
    MODE_8BIT_BYTE: 16,
    MODE_KANJI: 12,
}

ALPHA_NUM = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
RE_ALPHA_NUM = re.compile(b"^[" + re.escape(ALPHA_NUM) + rb"]*\Z")

# The number of bits for numeric delimited data lengths.
NUMBER_LENGTH = {3: 10, 2: 7, 1: 4}

PATTERN_POSITION_TABLE = [
    [],
    [6, 18],
    [6, 22],
    [6, 26],
    [6, 30],
    [6, 34],
    [6, 22, 38],
    [6, 24, 42],
    [6, 26, 46],
    [6, 28, 50],
    [6, 30, 54],
    [6, 32, 58],
    [6, 34, 62],
    [6, 26, 46, 66],
    [6, 26, 48, 70],
    [6, 26, 50, 74],
    [6, 30, 54, 78],
    [6, 30, 56, 82],
    [6, 30, 58, 86],
    [6, 34, 62, 90],
    [6, 28, 50, 72, 94],
    [6, 26, 50, 74, 98],
    [6, 30, 54, 78, 102],
    [6, 28, 54, 80, 106],
    [6, 32, 58, 84, 110],
    [6, 30, 58, 86, 114],
    [6, 34, 62, 90, 118],
    [6, 26, 50, 74, 98, 122],
    [6, 30, 54, 78, 102, 126],
    [6, 26, 52, 78, 104, 130],
    [6, 30, 56, 82, 108, 134],
    [6, 34, 60, 86, 112, 138],
    [6, 30, 58, 86, 114, 142],
    [6, 34, 62, 90, 118, 146],
    [6, 30, 54, 78, 102, 126, 150],
    [6, 24, 50, 76, 102, 128, 154],
    [6, 28, 54, 80, 106, 132, 158],
    [6, 32, 58, 84, 110, 136, 162],
    [6, 26, 54, 82, 110, 138, 166],
    [6, 30, 58, 86, 114, 142, 170],
]

G15 = (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0)
G18 = (
    (1 << 12)
    | (1 << 11)
    | (1 << 10)
    | (1 << 9)
    | (1 << 8)
    | (1 << 5)
    | (1 << 2)
    | (1 << 0)
)
G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1)

PAD0 = 0xEC
PAD1 = 0x11


# Precompute bit count limits, indexed by error correction level and code size
def _data_count(block):
    return block.data_count


BIT_LIMIT_TABLE = [
    [0]
    + [
        8 * sum(map(_data_count, base.rs_blocks(version, error_correction)))
        for version in range(1, 41)
    ]
    for error_correction in range(4)
]


def BCH_type_info(data):
    d = data << 10
    while BCH_digit(d) - BCH_digit(G15) >= 0:
        d ^= G15 << (BCH_digit(d) - BCH_digit(G15))

    return ((data << 10) | d) ^ G15_MASK


def BCH_type_number(data):
    d = data << 12
    while BCH_digit(d) - BCH_digit(G18) >= 0:
        d ^= G18 << (BCH_digit(d) - BCH_digit(G18))
    return (data << 12) | d


def BCH_digit(data):
    digit = 0
    while data != 0:
        digit += 1
        data >>= 1
    return digit


def pattern_position(version):
    return PATTERN_POSITION_TABLE[version - 1]


def mask_func(pattern):
    """
    Return the mask function for the given mask pattern.
    """
    if pattern == 0:  # 000
        return lambda i, j: (i + j) % 2 == 0
    if pattern == 1:  # 001
        return lambda i, j: i % 2 == 0
    if pattern == 2:  # 010
        return lambda i, j: j % 3 == 0
    if pattern == 3:  # 011
        return lambda i, j: (i + j) % 3 == 0
    if pattern == 4:  # 100
        return lambda i, j: (math.floor(i / 2) + math.floor(j / 3)) % 2 == 0
    if pattern == 5:  # 101
        return lambda i, j: (i * j) % 2 + (i * j) % 3 == 0
    if pattern == 6:  # 110
        return lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0
    if pattern == 7:  # 111
        return lambda i, j: ((i * j) % 3 + (i + j) % 2) % 2 == 0
    raise TypeError("Bad mask pattern: " + pattern)  # pragma: no cover


def mode_sizes_for_version(version):
    if version < 10:
        return MODE_SIZE_SMALL
    elif version < 27:
        return MODE_SIZE_MEDIUM
    else:
        return MODE_SIZE_LARGE


def length_in_bits(mode, version):
    if mode not in (MODE_NUMBER, MODE_ALPHA_NUM, MODE_8BIT_BYTE, MODE_KANJI):
        raise TypeError(f"Invalid mode ({mode})")  # pragma: no cover

    check_version(version)

    return mode_sizes_for_version(version)[mode]


def check_version(version):
    if version < 1 or version > 40:
        raise ValueError(f"Invalid version (was {version}, expected 1 to 40)")


def lost_point(modules):
    modules_count = len(modules)

    lost_point = 0

    lost_point = _lost_point_level1(modules, modules_count)
    lost_point += _lost_point_level2(modules, modules_count)
    lost_point += _lost_point_level3(modules, modules_count)
    lost_point += _lost_point_level4(modules, modules_count)

    return lost_point


def _lost_point_level1(modules, modules_count):
    lost_point = 0

    modules_range = range(modules_count)
    container = [0] * (modules_count + 1)

    for row in modules_range:
        this_row = modules[row]
        previous_color = this_row[0]
        length = 0
        for col in modules_range:
            if this_row[col] == previous_color:
                length += 1
            else:
                if length >= 5:
                    container[length] += 1
                length = 1
                previous_color = this_row[col]
        if length >= 5:
            container[length] += 1

    for col in modules_range:
        previous_color = modules[0][col]
        length = 0
        for row in modules_range:
            if modules[row][col] == previous_color:
                length += 1
            else:
                if length >= 5:
                    container[length] += 1
                length = 1
                previous_color = modules[row][col]
        if length >= 5:
            container[length] += 1

    lost_point += sum(
        container[each_length] * (each_length - 2)
        for each_length in range(5, modules_count + 1)
    )

    return lost_point


def _lost_point_level2(modules, modules_count):
    lost_point = 0

    modules_range = range(modules_count - 1)
    for row in modules_range:
        this_row = modules[row]
        next_row = modules[row + 1]
        # use iter() and next() to skip next four-block. e.g.
        # d a f   if top-right a != b bottom-right,
        # c b e   then both abcd and abef won't lost any point.
        modules_range_iter = iter(modules_range)
        for col in modules_range_iter:
            top_right = this_row[col + 1]
            if top_right != next_row[col + 1]:
                # reduce 33.3% of runtime via next().
                # None: raise nothing if there is no next item.
                next(modules_range_iter, None)
            elif top_right != this_row[col]:
                continue
            elif top_right != next_row[col]:
                continue
            else:
                lost_point += 3

    return lost_point


def _lost_point_level3(modules, modules_count):
    # 1 : 1 : 3 : 1 : 1 ratio (dark:light:dark:light:dark) pattern in
    # row/column, preceded or followed by light area 4 modules wide. From ISOIEC.
    # pattern1:     10111010000
    # pattern2: 00001011101
    modules_range = range(modules_count)
    modules_range_short = range(modules_count - 10)
    lost_point = 0

    for row in modules_range:
        this_row = modules[row]
        modules_range_short_iter = iter(modules_range_short)
        col = 0
        for col in modules_range_short_iter:
            if (
                not this_row[col + 1]
                and this_row[col + 4]
                and not this_row[col + 5]
                and this_row[col + 6]
                and not this_row[col + 9]
                and (
                    this_row[col + 0]
                    and this_row[col + 2]
                    and this_row[col + 3]
                    and not this_row[col + 7]
                    and not this_row[col + 8]
                    and not this_row[col + 10]
                    or not this_row[col + 0]
                    and not this_row[col + 2]
                    and not this_row[col + 3]
                    and this_row[col + 7]
                    and this_row[col + 8]
                    and this_row[col + 10]
                )
            ):
                lost_point += 40
            # horspool algorithm.
            # if this_row[col + 10]:
            #   pattern1 shift 4, pattern2 shift 2. So min=2.
            # else:
            #   pattern1 shift 1, pattern2 shift 1. So min=1.
            if this_row[col + 10]:
                next(modules_range_short_iter, None)

    for col in modules_range:
        modules_range_short_iter = iter(modules_range_short)
        row = 0
        for row in modules_range_short_iter:
            if (
                not modules[row + 1][col]
                and modules[row + 4][col]
                and not modules[row + 5][col]
                and modules[row + 6][col]
                and not modules[row + 9][col]
                and (
                    modules[row + 0][col]
                    and modules[row + 2][col]
                    and modules[row + 3][col]
                    and not modules[row + 7][col]
                    and not modules[row + 8][col]
                    and not modules[row + 10][col]
                    or not modules[row + 0][col]
                    and not modules[row + 2][col]
                    and not modules[row + 3][col]
                    and modules[row + 7][col]
                    and modules[row + 8][col]
                    and modules[row + 10][col]
                )
            ):
                lost_point += 40
            if modules[row + 10][col]:
                next(modules_range_short_iter, None)

    return lost_point


def _lost_point_level4(modules, modules_count):
    dark_count = sum(map(sum, modules))
    percent = float(dark_count) / (modules_count**2)
    # Every 5% departure from 50%, rating++
    rating = int(abs(percent * 100 - 50) / 5)
    return rating * 10


def optimal_data_chunks(data, minimum=4):
    """
    An iterator returning QRData chunks optimized to the data content.

    :param minimum: The minimum number of bytes in a row to split as a chunk.
    """
    data = to_bytestring(data)
    num_pattern = rb"\d"
    alpha_pattern = b"[" + re.escape(ALPHA_NUM) + b"]"
    if len(data) <= minimum:
        num_pattern = re.compile(b"^" + num_pattern + b"+$")
        alpha_pattern = re.compile(b"^" + alpha_pattern + b"+$")
    else:
        re_repeat = b"{" + str(minimum).encode("ascii") + b",}"
        num_pattern = re.compile(num_pattern + re_repeat)
        alpha_pattern = re.compile(alpha_pattern + re_repeat)
    num_bits = _optimal_split(data, num_pattern)
    for is_num, chunk in num_bits:
        if is_num:
            yield QRData(chunk, mode=MODE_NUMBER, check_data=False)
        else:
            for is_alpha, sub_chunk in _optimal_split(chunk, alpha_pattern):
                mode = MODE_ALPHA_NUM if is_alpha else MODE_8BIT_BYTE
                yield QRData(sub_chunk, mode=mode, check_data=False)


def _optimal_split(data, pattern):
    while data:
        match = re.search(pattern, data)
        if not match:
            break
        start, end = match.start(), match.end()
        if start:
            yield False, data[:start]
        yield True, data[start:end]
        data = data[end:]
    if data:
        yield False, data


def to_bytestring(data):
    """
    Convert data to a (utf-8 encoded) byte-string if it isn't a byte-string
    already.
    """
    if not isinstance(data, bytes):
        data = str(data).encode("utf-8")
    return data


def optimal_mode(data):
    """
    Calculate the optimal mode for this chunk of data.
    """
    if data.isdigit():
        return MODE_NUMBER
    if RE_ALPHA_NUM.match(data):
        return MODE_ALPHA_NUM
    return MODE_8BIT_BYTE


class QRData:
    """
    Data held in a QR compatible format.

    Doesn't currently handle KANJI.
    """

    def __init__(self, data, mode=None, check_data=True):
        """
        If ``mode`` isn't provided, the most compact QR data type possible is
        chosen.
        """
        if check_data:
            data = to_bytestring(data)

        if mode is None:
            self.mode = optimal_mode(data)
        else:
            self.mode = mode
            if mode not in (MODE_NUMBER, MODE_ALPHA_NUM, MODE_8BIT_BYTE):
                raise TypeError(f"Invalid mode ({mode})")  # pragma: no cover
            if check_data and mode < optimal_mode(data):  # pragma: no cover
                raise ValueError(f"Provided data can not be represented in mode {mode}")

        self.data = data

    def __len__(self):
        return len(self.data)

    def write(self, buffer):
        if self.mode == MODE_NUMBER:
            for i in range(0, len(self.data), 3):
                chars = self.data[i : i + 3]
                bit_length = NUMBER_LENGTH[len(chars)]
                buffer.put(int(chars), bit_length)
        elif self.mode == MODE_ALPHA_NUM:
            for i in range(0, len(self.data), 2):
                chars = self.data[i : i + 2]
                if len(chars) > 1:
                    buffer.put(
                        ALPHA_NUM.find(chars[0]) * 45 + ALPHA_NUM.find(chars[1]), 11
                    )
                else:
                    buffer.put(ALPHA_NUM.find(chars), 6)
        else:
            # Iterating a bytestring in Python 3 returns an integer,
            # no need to ord().
            data = self.data
            for c in data:
                buffer.put(c, 8)

    def __repr__(self):
        return repr(self.data)


class BitBuffer:
    def __init__(self):
        self.buffer: List[int] = []
        self.length = 0

    def __repr__(self):
        return ".".join([str(n) for n in self.buffer])

    def get(self, index):
        buf_index = math.floor(index / 8)
        return ((self.buffer[buf_index] >> (7 - index % 8)) & 1) == 1

    def put(self, num, length):
        for i in range(length):
            self.put_bit(((num >> (length - i - 1)) & 1) == 1)

    def __len__(self):
        return self.length

    def put_bit(self, bit):
        buf_index = self.length // 8
        if len(self.buffer) <= buf_index:
            self.buffer.append(0)
        if bit:
            self.buffer[buf_index] |= 0x80 >> (self.length % 8)
        self.length += 1


def create_bytes(buffer: BitBuffer, rs_blocks: List[RSBlock]):
    offset = 0

    maxDcCount = 0
    maxEcCount = 0

    dcdata: List[List[int]] = []
    ecdata: List[List[int]] = []

    for rs_block in rs_blocks:
        dcCount = rs_block.data_count
        ecCount = rs_block.total_count - dcCount

        maxDcCount = max(maxDcCount, dcCount)
        maxEcCount = max(maxEcCount, ecCount)

        current_dc = [0xFF & buffer.buffer[i + offset] for i in range(dcCount)]
        offset += dcCount

        # Get error correction polynomial.
        if ecCount in LUT.rsPoly_LUT:
            rsPoly = base.Polynomial(LUT.rsPoly_LUT[ecCount], 0)
        else:
            rsPoly = base.Polynomial([1], 0)
            for i in range(ecCount):
                rsPoly = rsPoly * base.Polynomial([1, base.gexp(i)], 0)

        rawPoly = base.Polynomial(current_dc, len(rsPoly) - 1)

        modPoly = rawPoly % rsPoly
        current_ec = []
        mod_offset = len(modPoly) - ecCount
        for i in range(ecCount):
            modIndex = i + mod_offset
            current_ec.append(modPoly[modIndex] if (modIndex >= 0) else 0)

        dcdata.append(current_dc)
        ecdata.append(current_ec)

    data = []
    for i in range(maxDcCount):
        for dc in dcdata:
            if i < len(dc):
                data.append(dc[i])
    for i in range(maxEcCount):
        for ec in ecdata:
            if i < len(ec):
                data.append(ec[i])

    return data


def create_data(version, error_correction, data_list):
    buffer = BitBuffer()
    for data in data_list:
        buffer.put(data.mode, 4)
        buffer.put(len(data), length_in_bits(data.mode, version))
        data.write(buffer)

    # Calculate the maximum number of bits for the given version.
    rs_blocks = base.rs_blocks(version, error_correction)
    bit_limit = sum(block.data_count * 8 for block in rs_blocks)
    if len(buffer) > bit_limit:
        raise exceptions.DataOverflowError(
            "Code length overflow. Data size (%s) > size available (%s)"
            % (len(buffer), bit_limit)
        )

    # Terminate the bits (add up to four 0s).
    for _ in range(min(bit_limit - len(buffer), 4)):
        buffer.put_bit(False)

    # Delimit the string into 8-bit words, padding with 0s if necessary.
    delimit = len(buffer) % 8
    if delimit:
        for _ in range(8 - delimit):
            buffer.put_bit(False)

    # Add special alternating padding bitstrings until buffer is full.
    bytes_to_fill = (bit_limit - len(buffer)) // 8
    for i in range(bytes_to_fill):
        if i % 2 == 0:
            buffer.put(PAD0, 8)
        else:
            buffer.put(PAD1, 8)

    return create_bytes(buffer, rs_blocks)
