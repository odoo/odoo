import sys
from bisect import bisect_left
from typing import (
    Dict,
    Generic,
    List,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
    cast,
    overload,
    Literal,
)

from qrcode import constants, exceptions, util
from qrcode.image.base import BaseImage
from qrcode.image.pure import PyPNGImage

ModulesType = List[List[Optional[bool]]]
# Cache modules generated just based on the QR Code version
precomputed_qr_blanks: Dict[int, ModulesType] = {}


def make(data=None, **kwargs):
    qr = QRCode(**kwargs)
    qr.add_data(data)
    return qr.make_image()


def _check_box_size(size):
    if int(size) <= 0:
        raise ValueError(f"Invalid box size (was {size}, expected larger than 0)")


def _check_border(size):
    if int(size) < 0:
        raise ValueError(
            "Invalid border value (was %s, expected 0 or larger than that)" % size
        )


def _check_mask_pattern(mask_pattern):
    if mask_pattern is None:
        return
    if not isinstance(mask_pattern, int):
        raise TypeError(
            f"Invalid mask pattern (was {type(mask_pattern)}, expected int)"
        )
    if mask_pattern < 0 or mask_pattern > 7:
        raise ValueError(f"Mask pattern should be in range(8) (got {mask_pattern})")


def copy_2d_array(x):
    return [row[:] for row in x]


class ActiveWithNeighbors(NamedTuple):
    NW: bool
    N: bool
    NE: bool
    W: bool
    me: bool
    E: bool
    SW: bool
    S: bool
    SE: bool

    def __bool__(self) -> bool:
        return self.me


GenericImage = TypeVar("GenericImage", bound=BaseImage)
GenericImageLocal = TypeVar("GenericImageLocal", bound=BaseImage)


class QRCode(Generic[GenericImage]):
    modules: ModulesType
    _version: Optional[int] = None

    def __init__(
        self,
        version=None,
        error_correction=constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
        image_factory: Optional[Type[GenericImage]] = None,
        mask_pattern=None,
    ):
        _check_box_size(box_size)
        _check_border(border)
        self.version = version
        self.error_correction = int(error_correction)
        self.box_size = int(box_size)
        # Spec says border should be at least four boxes wide, but allow for
        # any (e.g. for producing printable QR codes).
        self.border = int(border)
        self.mask_pattern = mask_pattern
        self.image_factory = image_factory
        if image_factory is not None:
            assert issubclass(image_factory, BaseImage)
        self.clear()

    @property
    def version(self) -> int:
        if self._version is None:
            self.best_fit()
        return cast(int, self._version)

    @version.setter
    def version(self, value) -> None:
        if value is not None:
            value = int(value)
            util.check_version(value)
        self._version = value

    @property
    def mask_pattern(self):
        return self._mask_pattern

    @mask_pattern.setter
    def mask_pattern(self, pattern):
        _check_mask_pattern(pattern)
        self._mask_pattern = pattern

    def clear(self):
        """
        Reset the internal data.
        """
        self.modules = [[]]
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def add_data(self, data, optimize=20):
        """
        Add data to this QR Code.

        :param optimize: Data will be split into multiple chunks to optimize
            the QR size by finding to more compressed modes of at least this
            length. Set to ``0`` to avoid optimizing at all.
        """
        if isinstance(data, util.QRData):
            self.data_list.append(data)
        elif optimize:
            self.data_list.extend(util.optimal_data_chunks(data, minimum=optimize))
        else:
            self.data_list.append(util.QRData(data))
        self.data_cache = None

    def make(self, fit=True):
        """
        Compile the data into a QR Code array.

        :param fit: If ``True`` (or if a size has not been provided), find the
            best fit for the data to avoid data overflow errors.
        """
        if fit or (self.version is None):
            self.best_fit(start=self.version)
        if self.mask_pattern is None:
            self.makeImpl(False, self.best_mask_pattern())
        else:
            self.makeImpl(False, self.mask_pattern)

    def makeImpl(self, test, mask_pattern):
        self.modules_count = self.version * 4 + 17

        if self.version in precomputed_qr_blanks:
            self.modules = copy_2d_array(precomputed_qr_blanks[self.version])
        else:
            self.modules = [
                [None] * self.modules_count for i in range(self.modules_count)
            ]
            self.setup_position_probe_pattern(0, 0)
            self.setup_position_probe_pattern(self.modules_count - 7, 0)
            self.setup_position_probe_pattern(0, self.modules_count - 7)
            self.setup_position_adjust_pattern()
            self.setup_timing_pattern()

            precomputed_qr_blanks[self.version] = copy_2d_array(self.modules)

        self.setup_type_info(test, mask_pattern)

        if self.version >= 7:
            self.setup_type_number(test)

        if self.data_cache is None:
            self.data_cache = util.create_data(
                self.version, self.error_correction, self.data_list
            )
        self.map_data(self.data_cache, mask_pattern)

    def setup_position_probe_pattern(self, row, col):
        for r in range(-1, 8):
            if row + r <= -1 or self.modules_count <= row + r:
                continue

            for c in range(-1, 8):
                if col + c <= -1 or self.modules_count <= col + c:
                    continue

                if (
                    (0 <= r <= 6 and c in {0, 6})
                    or (0 <= c <= 6 and r in {0, 6})
                    or (2 <= r <= 4 and 2 <= c <= 4)
                ):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False

    def best_fit(self, start=None):
        """
        Find the minimum size required to fit in the data.
        """
        if start is None:
            start = 1
        util.check_version(start)

        # Corresponds to the code in util.create_data, except we don't yet know
        # version, so optimistically assume start and check later
        mode_sizes = util.mode_sizes_for_version(start)
        buffer = util.BitBuffer()
        for data in self.data_list:
            buffer.put(data.mode, 4)
            buffer.put(len(data), mode_sizes[data.mode])
            data.write(buffer)

        needed_bits = len(buffer)
        self.version = bisect_left(
            util.BIT_LIMIT_TABLE[self.error_correction], needed_bits, start
        )
        if self.version == 41:
            raise exceptions.DataOverflowError()

        # Now check whether we need more bits for the mode sizes, recursing if
        # our guess was too low
        if mode_sizes is not util.mode_sizes_for_version(self.version):
            self.best_fit(start=self.version)
        return self.version

    def best_mask_pattern(self):
        """
        Find the most efficient mask pattern.
        """
        min_lost_point = 0
        pattern = 0

        for i in range(8):
            self.makeImpl(True, i)

            lost_point = util.lost_point(self.modules)

            if i == 0 or min_lost_point > lost_point:
                min_lost_point = lost_point
                pattern = i

        return pattern

    def print_tty(self, out=None):
        """
        Output the QR Code only using TTY colors.

        If the data has not been compiled yet, make it first.
        """
        if out is None:
            import sys

            out = sys.stdout

        if not out.isatty():
            raise OSError("Not a tty")

        if self.data_cache is None:
            self.make()

        modcount = self.modules_count
        out.write("\x1b[1;47m" + (" " * (modcount * 2 + 4)) + "\x1b[0m\n")
        for r in range(modcount):
            out.write("\x1b[1;47m  \x1b[40m")
            for c in range(modcount):
                if self.modules[r][c]:
                    out.write("  ")
                else:
                    out.write("\x1b[1;47m  \x1b[40m")
            out.write("\x1b[1;47m  \x1b[0m\n")
        out.write("\x1b[1;47m" + (" " * (modcount * 2 + 4)) + "\x1b[0m\n")
        out.flush()

    def print_ascii(self, out=None, tty=False, invert=False):
        """
        Output the QR Code using ASCII characters.

        :param tty: use fixed TTY color codes (forces invert=True)
        :param invert: invert the ASCII characters (solid <-> transparent)
        """
        if out is None:
            out = sys.stdout

        if tty and not out.isatty():
            raise OSError("Not a tty")

        if self.data_cache is None:
            self.make()

        modcount = self.modules_count
        codes = [bytes((code,)).decode("cp437") for code in (255, 223, 220, 219)]
        if tty:
            invert = True
        if invert:
            codes.reverse()

        def get_module(x, y) -> int:
            if invert and self.border and max(x, y) >= modcount + self.border:
                return 1
            if min(x, y) < 0 or max(x, y) >= modcount:
                return 0
            return cast(int, self.modules[x][y])

        for r in range(-self.border, modcount + self.border, 2):
            if tty:
                if not invert or r < modcount + self.border - 1:
                    out.write("\x1b[48;5;232m")  # Background black
                out.write("\x1b[38;5;255m")  # Foreground white
            for c in range(-self.border, modcount + self.border):
                pos = get_module(r, c) + (get_module(r + 1, c) << 1)
                out.write(codes[pos])
            if tty:
                out.write("\x1b[0m")
            out.write("\n")
        out.flush()

    @overload
    def make_image(
        self, image_factory: Literal[None] = None, **kwargs
    ) -> GenericImage: ...

    @overload
    def make_image(
        self, image_factory: Type[GenericImageLocal] = None, **kwargs
    ) -> GenericImageLocal: ...

    def make_image(self, image_factory=None, **kwargs):
        """
        Make an image from the QR Code data.

        If the data has not been compiled yet, make it first.
        """
        if (
            kwargs.get("embeded_image_path") or kwargs.get("embeded_image")
        ) and self.error_correction != constants.ERROR_CORRECT_H:
            raise ValueError(
                "Error correction level must be ERROR_CORRECT_H if an embedded image is provided"
            )
        _check_box_size(self.box_size)
        if self.data_cache is None:
            self.make()

        if image_factory is not None:
            assert issubclass(image_factory, BaseImage)
        else:
            image_factory = self.image_factory
            if image_factory is None:
                from qrcode.image.pil import Image, PilImage

                # Use PIL by default if available, otherwise use PyPNG.
                image_factory = PilImage if Image else PyPNGImage

        im = image_factory(
            self.border,
            self.modules_count,
            self.box_size,
            qrcode_modules=self.modules,
            **kwargs,
        )

        if im.needs_drawrect:
            for r in range(self.modules_count):
                for c in range(self.modules_count):
                    if im.needs_context:
                        im.drawrect_context(r, c, qr=self)
                    elif self.modules[r][c]:
                        im.drawrect(r, c)
        if im.needs_processing:
            im.process()

        return im

    # return true if and only if (row, col) is in the module
    def is_constrained(self, row: int, col: int) -> bool:
        return (
            row >= 0
            and row < len(self.modules)
            and col >= 0
            and col < len(self.modules[row])
        )

    def setup_timing_pattern(self):
        for r in range(8, self.modules_count - 8):
            if self.modules[r][6] is not None:
                continue
            self.modules[r][6] = r % 2 == 0

        for c in range(8, self.modules_count - 8):
            if self.modules[6][c] is not None:
                continue
            self.modules[6][c] = c % 2 == 0

    def setup_position_adjust_pattern(self):
        pos = util.pattern_position(self.version)

        for i in range(len(pos)):
            row = pos[i]

            for j in range(len(pos)):
                col = pos[j]

                if self.modules[row][col] is not None:
                    continue

                for r in range(-2, 3):
                    for c in range(-2, 3):
                        if (
                            r == -2
                            or r == 2
                            or c == -2
                            or c == 2
                            or (r == 0 and c == 0)
                        ):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def setup_type_number(self, test):
        bits = util.BCH_type_number(self.version)

        for i in range(18):
            mod = not test and ((bits >> i) & 1) == 1
            self.modules[i // 3][i % 3 + self.modules_count - 8 - 3] = mod

        for i in range(18):
            mod = not test and ((bits >> i) & 1) == 1
            self.modules[i % 3 + self.modules_count - 8 - 3][i // 3] = mod

    def setup_type_info(self, test, mask_pattern):
        data = (self.error_correction << 3) | mask_pattern
        bits = util.BCH_type_info(data)

        # vertical
        for i in range(15):
            mod = not test and ((bits >> i) & 1) == 1

            if i < 6:
                self.modules[i][8] = mod
            elif i < 8:
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.modules_count - 15 + i][8] = mod

        # horizontal
        for i in range(15):
            mod = not test and ((bits >> i) & 1) == 1

            if i < 8:
                self.modules[8][self.modules_count - i - 1] = mod
            elif i < 9:
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod

        # fixed module
        self.modules[self.modules_count - 8][8] = not test

    def map_data(self, data, mask_pattern):
        inc = -1
        row = self.modules_count - 1
        bitIndex = 7
        byteIndex = 0

        mask_func = util.mask_func(mask_pattern)

        data_len = len(data)

        for col in range(self.modules_count - 1, 0, -2):
            if col <= 6:
                col -= 1

            col_range = (col, col - 1)

            while True:
                for c in col_range:
                    if self.modules[row][c] is None:
                        dark = False

                        if byteIndex < data_len:
                            dark = ((data[byteIndex] >> bitIndex) & 1) == 1

                        if mask_func(row, c):
                            dark = not dark

                        self.modules[row][c] = dark
                        bitIndex -= 1

                        if bitIndex == -1:
                            byteIndex += 1
                            bitIndex = 7

                row += inc

                if row < 0 or self.modules_count <= row:
                    row -= inc
                    inc = -inc
                    break

    def get_matrix(self):
        """
        Return the QR Code as a multidimensional array, including the border.

        To return the array without a border, set ``self.border`` to 0 first.
        """
        if self.data_cache is None:
            self.make()

        if not self.border:
            return self.modules

        width = len(self.modules) + self.border * 2
        code = [[False] * width] * self.border
        x_border = [False] * self.border
        for module in self.modules:
            code.append(x_border + cast(List[bool], module) + x_border)
        code += [[False] * width] * self.border

        return code

    def active_with_neighbors(self, row: int, col: int) -> ActiveWithNeighbors:
        context: List[bool] = []
        for r in range(row - 1, row + 2):
            for c in range(col - 1, col + 2):
                context.append(self.is_constrained(r, c) and bool(self.modules[r][c]))
        return ActiveWithNeighbors(*context)
