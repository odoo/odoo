# QRCode for Python
#
# Support for Kanji, Hanzi, ECI, FNC1 and Structurded append,
# and optimizations by Anders Hammarquist <iko@openend.se>
#
# Copyright (c) 2014 Open End AB http://www.openend.se/
#
# Ported from the Javascript library by Sam Curren
#
# QRCode for Javascript
# http://d-project.googlecode.com/svn/trunk/misc/qrcode/js/qrcode.js
#
# Copyright (c) 2009 Kazuhiko Arase
#
# URL: http://www.d-project.com/
#
# Licensed under the MIT license:
#   http://www.opensource.org/licenses/mit-license.php
#
# The word "QR Code" is registered trademark of
# DENSO WAVE INCORPORATED
#   http://www.denso-wave.com/qrcode/faqpatent-e.html

import re
import itertools
try:
    from itertools import zip_longest
except:
    from itertools import izip_longest as zip_longest

try:
    unicode
except NameError:
    # No unicode in Python 3
    unicode = str

class QR:
    valid = None
    bits = None
    group = 0

    def __init__(self, data):
        if self.valid and not self.valid(data):
            raise ValueError
        self.data = data

    def __len__(self):
        return len(self.data)

    @property
    def bitlength(self):
        if self.bits is None:
            return 0
        q, r = divmod(len(self), len(self.bits))
        return q * sum(self.bits) + sum(self.bits[:r])

    def getLengthBits(self, ver):
        if 0 < ver < 10:
            return self.lengthbits[0]
        elif ver < 27:
            return self.lengthbits[1]
        elif ver < 41:
            return self.lengthbits[2]
        raise ValueError("Unknown version: " + ver)

    def getLength(self):
        return len(self.data)

    def __repr__(self):
        return repr(self.data)

    def write_header(self, buffer, version):
        buffer.put(self.mode, 4)
        lenbits = self.getLengthBits(version)
        if lenbits:
            buffer.put(len(self.data), lenbits )

    def write(self, buffer, version):
        self.write_header(buffer, version)
        for g in zip_longest(*[iter(self.data)] * self.group):
            bits = 0
            n = 0
            for i in range(self.group):
                if g[i] is not None:
                    n *= len(self.chars)
                    n += self.chars.index(g[i])
                    bits += self.bits[i]
            buffer.put(n, bits)

class QRNumber(QR):
    valid = re.compile(u'[0-9]*$').match
    chars = u'0123456789'
    bits = (4,3,3)
    group = 3
    mode = 0x1
    lengthbits = (10, 12, 14)

class QRAlphaNum(QR):
    valid = re.compile(u'[-0-9A-Z $%*+./:]*$').match
    chars = u'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'
    bits = (6,5)
    group = 2
    mode = 0x2
    lengthbits = (9, 11, 13)

class QR8bitByte(QR):
    bits = (8,)
    group = 1
    mode = 0x4
    lengthbits = (8, 16, 16)

    def __init__(self, data):
        if isinstance(data, unicode):
            self.data = data.encode('utf-8')  # XXX This really needs an ECI too
        else:
            self.data = data  # It'd better be byte data

    def write(self, buffer, version):
        self.write_header(buffer, version)
        for c in self.data:
            if isinstance(c, str):
                c = ord(c)
            buffer.put(c, 8)

class QRKanji(QR):
    bits = (13,)
    group = 1
    mode = 0x8
    lengthbits = (8, 10, 12)

    def __init__(self, data):
        try:
            self.data = self.unicode_to_qrkanji(data)
        except UnicodeEncodeError:
            raise ValueError('Not valid kanji')

    def unicode_to_qrkanji(self, data):
        codes = []
        for i,c in enumerate(data):
            try:
                c = c.encode('shift-jis')
                try:
                    c,d = map(ord, c)
                except TypeError:
                    # Python 3
                    c,d = c
            except UnicodeEncodeError as e:
                raise UnicodeEncodeError('qrkanji', data, i, i+1, e.args[4])
            except ValueError:
                raise UnicodeEncodeError('qrkanji', data, i, i+1,
                                         'illegal multibyte sequence')
            c = c << 8 | d
            if 0x8140 <= c <=0x9ffc:
                c -= 0x8140
                c = (((c & 0xff00) >> 8) * 0xc0) + (c & 0xff)
            elif 0xe040 <= c <= 0xebbf:
                c -= 0xc140
                c = (((c & 0xff00) >> 8) * 0xc0) + (c & 0xff)
            else:
                raise UnicodeEncodeError('qrkanji', data, i, i+1,
                                         'illegal multibyte sequence')
            codes.append(c)
        return codes

    def write(self, buffer, version):
        self.write_header(buffer, version)
        for d in self.data:
            buffer.put(d, 13)

class QRHanzi(QR):
    bits = (13,)
    group = 1
    mode = 0xD
    lengthbits = (8, 10, 12)

    def __init__(self, data):
        try:
            self.data = self.unicode_to_qrhanzi(data)
        except UnicodeEncodeError:
            raise ValueError('Not valid hanzi')

    def unicode_to_qrhanzi(self, data):
        codes = []
        for i,c in enumerate(data):
            try:
                c = c.encode('gb2312')
                try:
                    c,d = map(ord, c)
                except TypeError:
                    # Python 3
                    c,d = c
            except UnicodeEncodeError as e:
                raise UnicodeEncodeError('qrhanzi', data, i, i+1, e.args[4])
            except ValueError:
                raise UnicodeEncodeError('qrhanzi', data, i, i+1,
                                         'illegal multibyte sequence')
            c = c << 8 | d
            if 0xa1a1 <= c <=0xaafe:
                c -= 0xa1a1
                c = (((c & 0xff00) >> 8) * 0x60) + (c & 0xff)
            elif 0xb0a1 <= c <= 0xfafe:
                c -= 0xa6a1
                c = (((c & 0xff00) >> 8) * 0x60) + (c & 0xff)
            else:
                raise UnicodeEncodeError('qrhanzi', data, i, i+1,
                                         'illegal multibyte sequence')
            codes.append(c)
        return codes

    def write_header(self, buffer, version):
        buffer.put(self.mode, 4)
        buffer.put(1, 4)  # Subset 1: GB2312 encoding
        lenbits = self.getLengthBits(version)
        if lenbits:
            buffer.put(len(self.data), lenbits )

    def write(self, buffer, version):
        self.write_header(buffer, version)
        for d in self.data:
            buffer.put(d, 13)


# Special modes
class QRECI(QR):
    mode = 0x7
    lengthbits = (0, 0, 0)

    def __init__(self, data):
        if not 0 < data < 999999:
            # Spec says 999999, format supports up to 0x1fffff = 2097151
            raise ValueError("ECI out of range")
        self.data = data

    def write(self, buffer, version):
        self.write_header(buffer, version)
        if self.data <= 0x7f:
            buffer.put(self.data, 8)
        elif self.data <= 0x3fff:
            buffer.put(self.data | 0x8000, 16)
        elif self.data <= 0x1fffff:
            buffer.put(self.data | 0xC00000, 24)

class QRStructAppend(QR):
    mode = 0x3
    lengthbits = (0, 0, 0)

    def __init__(self, part, total, parity):
        if not 0 < part <= 16:
            raise ValueError("part out of range [1,16]")
        if not 0 < total <= 16:
            raise ValueError("total out of range [1,16]")
        self.part = part
        self.total = total
        self.parity = parity

    def write(self, buffer, version):
        self.write_header(buffer, version)
        buffer.put(self.part, 4)
        buffer.put(self.total, 4)
        buffer.put(self.parity, 8)

class QRFNC1First(QR):
    mode = 0x5
    lengthbits = (0, 0, 0)

    def __init__(self):
        pass

    def write(self, buffer, version):
        self.write_header(buffer, version)


class QRFNC1Second(QR):
    valid = re.compile('^([A-Za-z]|[0-9][0-9])$').match
    mode = 0x9
    lengthbits = (0, 0, 0)

    def write(self, buffer, version):
        self.write_header(buffer, version)
        d = self.data
        if len(d) == 1:
            d = ord(d) + 100
        else:
            d = int(d)
        buffer.put(d, 8)

class QRCode:
    def __init__(self, version, errorCorrectLevel):
        self.version = version
        self.errorCorrectLevel = errorCorrectLevel
        self.modules = None
        self.moduleCount = 0
        self.dataCache = None
        self.dataList = []

    def addData(self, data):
        if isinstance(data, QR):
            newData = data
        else:
            for conv in (QRNumber, QRAlphaNum, QRKanji, QR8bitByte):
                try:
                    newData = conv(data)
                    break
                except ValueError:
                    pass
            else:
                raise ValueError

        self.dataList.append(newData)
        self.dataCache = None

    def isDark(self, row, col):
        return self.modules[row][col]

    def getModuleCount(self):
        return self.moduleCount

    def calculate_version(self):
        # Calculate version for data to fit the QR Code capacity
        for version in range(1, 40):
            rsBlocks = QRRSBlock.getRSBlocks(version, self.errorCorrectLevel)
            totalDataCount = sum(block.dataCount for block in rsBlocks)
            length = 0
            for data in self.dataList:
                length += 4
                length += data.getLengthBits(version)
                length += data.bitlength
            if length <= totalDataCount * 8:
                break
        return version

    def make(self):
        if self.version is None:
            self.version = self.calculate_version()
        self.makeImpl(False, self.getBestMaskPattern())

    def makeImpl(self, test, maskPattern):
        self.moduleCount = self.version * 4 + 17
        self.modules = [ [False] * self.moduleCount
                         for x in range(self.moduleCount) ]
        self.setupPositionProbePattern(0, 0)
        self.setupPositionProbePattern(self.moduleCount - 7, 0)
        self.setupPositionProbePattern(0, self.moduleCount - 7)
        self.setupPositionAdjustPattern()
        self.setupTimingPattern()
        self.setupTypeInfo(test, maskPattern)
        if (self.version >= 7):
            self.setupTypeNumber(test)
        if (self.dataCache == None):
            self.dataCache = QRCode.createData(self.version,
                                               self.errorCorrectLevel,
                                               self.dataList)
        self.mapData(self.dataCache, maskPattern)

    _positionProbePattern = [
        [True,  True,  True,  True,  True,  True,  True],
        [True, False, False, False, False, False,  True],
        [True, False,  True,  True,  True, False,  True],
        [True, False,  True,  True,  True, False,  True],
        [True, False,  True,  True,  True, False,  True],
        [True, False, False, False, False, False,  True],
        [True,  True,  True,  True,  True,  True,  True],
        ]

    def setupPositionProbePattern(self, row, col):
        if row == 0:
            self.modules[row+7][col:col+7] = [False] * 7
            if col == 0:
                self.modules[row+7][col+7] = False
            else:
                self.modules[row+7][col-1] = False
        else:
            # col == 0
            self.modules[row-1][col:col+8] = [False] * 8

        for r, data in enumerate(self._positionProbePattern):
            self.modules[row+r][col:col+7] = data
            if col == 0:
                self.modules[row+r][col+7] = False
            else:
                self.modules[row+r][col-1] = False

    def getBestMaskPattern(self):
        minLostPoint = 0
        pattern = 0
        for i in range(8):
            self.makeImpl(True, i);
            lostPoint = QRUtil.getLostPoint(self);
            if (i == 0 or minLostPoint > lostPoint):
                minLostPoint = lostPoint
                pattern = i
        return pattern

    def setupTimingPattern(self):
        for r in range(8, self.moduleCount - 8):
            self.modules[r][6] = (r % 2 == 0)
        self.modules[6][8:self.moduleCount - 8] = itertools.islice(
            itertools.cycle([True, False]), self.moduleCount - 16)

    _positionAdjustPattern = [
        [True,  True,  True,  True,  True],
        [True, False, False, False,  True],
        [True, False,  True, False,  True],
        [True, False, False, False,  True],
        [True,  True,  True,  True,  True],
        ]

    def setupPositionAdjustPattern(self):
        pos = QRUtil.getPatternPosition(self.version)
        maxpos = self.moduleCount - 8
        for row, col in itertools.product(pos, pos):
            if col <= 8 and (row <= 8 or row >= maxpos):
                continue
            elif col >= maxpos and row <= 8:
                continue
            for r, data in enumerate(self._positionAdjustPattern):
                self.modules[row + r - 2][col-2:col+3] = data

    def setupTypeNumber(self, test):
        bits = QRUtil.getBCHTypeNumber(self.version)
        for i in range(18):
            mod = (not test and ( (bits >> i) & 1) == 1)
            self.modules[i // 3][i % 3 + self.moduleCount - 8 - 3] = mod;
        for i in range(18):
            mod = (not test and ( (bits >> i) & 1) == 1)
            self.modules[i % 3 + self.moduleCount - 8 - 3][i // 3] = mod;

    def setupTypeInfo(self, test, maskPattern):
        data = (self.errorCorrectLevel << 3) | maskPattern
        bits = QRUtil.getBCHTypeInfo(data)
        # vertical
        for i in range(15):
            mod = (not test and ( (bits >> i) & 1) == 1)
            if (i < 6):
                self.modules[i][8] = mod
            elif (i < 8):
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.moduleCount - 15 + i][8] = mod
        # horizontal
        for i in range(15):
            mod = (not test and ( (bits >> i) & 1) == 1);
            if (i < 8):
                self.modules[8][self.moduleCount - i - 1] = mod
            elif (i < 9):
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod
        # fixed module
        self.modules[self.moduleCount - 8][8] = (not test)

    def _dataPosIterator(self):
        cols = itertools.chain(range(self.moduleCount - 1, 6, -2),
                               range(5, 0, -2))
        rows = (list(range(9, self.moduleCount - 8)),
                list(itertools.chain(range(6), range(7, self.moduleCount))),
                list(range(9, self.moduleCount)))
        rrows = tuple( list(reversed(r)) for r in rows)

        ppos = QRUtil.getPatternPosition(self.version)
        ppos = set(itertools.chain.from_iterable(
            (p-2, p-1, p, p+1, p+2) for p in ppos))
        maxpos = self.moduleCount - 11

        for col in cols:
            rows, rrows = rrows, rows
            if col <= 8: rowidx = 0
            elif col >= self.moduleCount - 8: rowidx = 2
            else: rowidx = 1
            for row in rows[rowidx]:
                for c in range(2):
                    c = col - c
                    if self.version >= 7:
                        if row < 6 and c >= self.moduleCount - 11:
                            continue
                        elif col < 6 and row >= self.moduleCount - 11:
                            continue
                    if row in ppos and c in ppos:
                        if not (row < 11 and (c < 11 or c > maxpos) or
                            c < 11 and (row < 11 or row > maxpos)):
                            continue

                    yield (c, row)

    _dataPosList = None

    def dataPosIterator(self):
        if not self._dataPosList:
            self._dataPosList = list(self._dataPosIterator())
        return self._dataPosList

    def _dataBitIterator(self, data):
        for byte in data:
            for bit in [0x80, 0x40, 0x20, 0x10,
                        0x08, 0x04, 0x02, 0x01]:
                yield bool(byte & bit)

    _dataBitList = None
    def dataBitIterator(self, data):
        if not self._dataBitList:
            self._dataBitList = list(self._dataBitIterator(data))
        return iter(self._dataBitList)

    def mapData(self, data, maskPattern):
        bits = self.dataBitIterator(data)
        mask = QRUtil.getMask(maskPattern)

        for (col, row), dark in zip_longest(self.dataPosIterator(), bits,
                                            fillvalue=False):
            self.modules[row][col] = dark ^ mask(row, col)

    PAD0 = 0xEC
    PAD1 = 0x11

    @staticmethod
    def createData(version, errorCorrectLevel, dataList):
        rsBlocks = QRRSBlock.getRSBlocks(version, errorCorrectLevel)
        buffer = QRBitBuffer();
        for data in dataList:
            data.write(buffer, version)
        # calc num max data.
        totalDataCount = 0;
        for block in rsBlocks:
            totalDataCount += block.dataCount
        if (buffer.getLengthInBits() > totalDataCount * 8):
            raise Exception("code length overflow. (%d > %d)" %
                            (buffer.getLengthInBits(), totalDataCount * 8))
        # end code
        if (buffer.getLengthInBits() + 4 <= totalDataCount * 8):
            buffer.put(0, 4)
        # padding
        while (buffer.getLengthInBits() % 8 != 0):
            buffer.putBit(False)
        # padding
        while (True):
            if (buffer.getLengthInBits() >= totalDataCount * 8):
                break
            buffer.put(QRCode.PAD0, 8)
            if (buffer.getLengthInBits() >= totalDataCount * 8):
                break
            buffer.put(QRCode.PAD1, 8)
        return QRCode.createBytes(buffer, rsBlocks)

    @staticmethod
    def createBytes(buffer, rsBlocks):
        offset = 0
        maxDcCount = 0
        maxEcCount = 0
        totalCodeCount = 0
        dcdata = []
        ecdata = []
        for block in rsBlocks:
            totalCodeCount += block.totalCount
            dcCount = block.dataCount
            ecCount = block.totalCount - dcCount
            maxDcCount = max(maxDcCount, dcCount)
            maxEcCount = max(maxEcCount, ecCount)
            dcdata.append(buffer.buffer[offset:offset+dcCount])
            offset += dcCount
            rsPoly = QRUtil.getErrorCorrectPolynomial(ecCount)
            rawPoly = QRPolynomial(dcdata[-1], rsPoly.getLength() - 1)
            modPoly = rawPoly.mod(rsPoly)
            rLen = rsPoly.getLength() - 1
            mLen = modPoly.getLength()
            ecdata.append([ (modPoly.get(i) if i >= 0 else 0)
                          for i in range(mLen - rLen, mLen) ])

        data = [ d for dd in itertools.chain(
                zip_longest(*dcdata), zip_longest(*ecdata))
                 for d in dd if d is not None]
        return data


class QRErrorCorrectLevel:
    L = 1
    M = 0
    Q = 3
    H = 2

class QRMaskPattern:
    PATTERN000 = 0
    PATTERN001 = 1
    PATTERN010 = 2
    PATTERN011 = 3
    PATTERN100 = 4
    PATTERN101 = 5
    PATTERN110 = 6
    PATTERN111 = 7

class QRUtil:
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
        [6, 30, 58, 86, 114, 142, 170]
    ]

    G15 = ((1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) |
           (1 << 0))
    G18 = ((1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) |
           (1 << 5) | (1 << 2) | (1 << 0))
    G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1)

    @staticmethod
    def getBCHTypeInfo(data):
        d = data << 10;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) >= 0):
            d ^= (QRUtil.G15 << (QRUtil.getBCHDigit(d) -
                                 QRUtil.getBCHDigit(QRUtil.G15) ) )
        return ( (data << 10) | d) ^ QRUtil.G15_MASK

    @staticmethod
    def getBCHTypeNumber(data):
        d = data << 12;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) >= 0):
            d ^= (QRUtil.G18 << (QRUtil.getBCHDigit(d) -
                                 QRUtil.getBCHDigit(QRUtil.G18) ) )
        return (data << 12) | d

    @staticmethod
    def getBCHDigit(data):
        digit = 0;
        while (data != 0):
            digit += 1
            data >>= 1
        return digit

    @staticmethod
    def getPatternPosition(version):
        return QRUtil.PATTERN_POSITION_TABLE[version - 1]

    maskPattern = {
        0: lambda i,j: (i + j) % 2 == 0,
        1: lambda i,j: i % 2 == 0,
        2: lambda i,j: j % 3 == 0,
        3: lambda i,j: (i + j) % 3 == 0,
        4: lambda i,j: (i // 2 + j // 3) % 2 == 0,
        5: lambda i,j: (i*j)%2 + (i*j)%3 == 0,
        6: lambda i,j: ( (i * j) % 2 + (i * j) % 3) % 2 == 0,
        7: lambda i,j: ( (i * j) % 3 + (i + j) % 2) % 2 == 0
        }

    @classmethod
    def getMask(cls, maskPattern):
        return cls.maskPattern[maskPattern]

    @staticmethod
    def getErrorCorrectPolynomial(errorCorrectLength):
        a = QRPolynomial([1], 0);
        for i in range(errorCorrectLength):
            a = a.multiply(QRPolynomial([1, QRMath.gexp(i)], 0) )
        return a

    @classmethod
    def maskScoreRule1vert(cls, modules):
        score = 0
        lastCount = [0]
        lastRow = None
        for row in modules:
            # Vertical patterns
            if lastRow:
                changed = [a ^ b for a,b in zip(row, lastRow)]
                scores = [a and (b-4+3) for a,b in
                          zip_longest(changed, lastCount, fillvalue=0)
                          if b >= 4]
                score += sum(scores)
                lastCount = [0 if a else b + 1
                             for a,b in zip_longest(changed, lastCount,
                                                    fillvalue=0)]
            lastRow = row

        score += sum([b-4+3 for b in lastCount if b >= 4])  # final counts
        return score

    @classmethod
    def maskScoreRule2(cls, modules):
        score = 0
        lastRow = modules[0]
        for row in modules[1:]:
            lastCol0, lastCol1 = row[0], lastRow[0]
            for col0, col1 in zip(row[1:], lastRow[1:]):
                if col0 == col1 == lastCol0 == lastCol1:
                    score += 3
                lastCol0, lastCol1 = col0, col1
            lastRow = row

        return score

    @classmethod
    def maskScoreRule3hor(
        cls, modules,
        pattern = [True, False, True, True, True, False, True,
                   False, False, False, False]):
        patternlen = len(pattern)
        score = 0
        for row in modules:
            j = 0
            maxj = len(row) - patternlen
            while j < maxj:
                if row[j:j+patternlen] == pattern:
                    score += 40
                    j += patternlen
                else:
                    j += 1

        return score

    @classmethod
    def maskScoreRule4(cls, modules):
        cellCount = len(modules)**2
        count = sum(sum(row) for row in modules)
        return 10 * (abs(100 * count // cellCount - 50) // 5)

    @classmethod
    def getLostPoint(cls, qrCode):
        lostPoint = 0;
        # LEVEL1
        lostPoint += cls.maskScoreRule1vert(qrCode.modules)
        lostPoint += cls.maskScoreRule1vert(zip(*qrCode.modules))
        # LEVEL2
        lostPoint += cls.maskScoreRule2(qrCode.modules)
        # LEVEL3
        lostPoint += cls.maskScoreRule3hor(qrCode.modules)
        lostPoint += cls.maskScoreRule3hor(zip(*qrCode.modules))
        # LEVEL4
        lostPoint += cls.maskScoreRule4(qrCode.modules)
        return lostPoint

class QRMath:
    @staticmethod
    def glog(n):
        if (n < 1):
            raise Exception("glog(" + n + ")")
        return LOG_TABLE[n];

    @staticmethod
    def gexp(n):
        while n < 0:
            n += 255
        while n >= 256:
            n -= 255
        return EXP_TABLE[n];

EXP_TABLE = [x for x in range(256)]
LOG_TABLE = [x for x in range(256)]
for i in range(8):
    EXP_TABLE[i] = 1 << i;
for i in range(8, 256):
    EXP_TABLE[i] = (EXP_TABLE[i - 4] ^ EXP_TABLE[i - 5] ^
                    EXP_TABLE[i - 6] ^ EXP_TABLE[i - 8])
for i in range(255):
    LOG_TABLE[EXP_TABLE[i] ] = i

class QRPolynomial:
    def __init__(self, num, shift):
        if (len(num) == 0):
            raise Exception(len(num) + "/" + shift)
        offset = 0
        while offset < len(num) and num[offset] == 0:
            offset += 1
        self.num = num[offset:] + [0]*shift

    def get(self, index):
        return self.num[index]

    def getLength(self):
        return len(self.num)

    def multiply(self, e):
        num = [0] * (self.getLength() + e.getLength() - 1);
        for i in range(self.getLength()):
            for j in range(e.getLength()):
                num[i + j] ^= QRMath.gexp(QRMath.glog(self.get(i) ) +
                                          QRMath.glog(e.get(j) ) )
        return QRPolynomial(num, 0);

    def mod(self, e):
        if (self.getLength() < e.getLength()):
            return self;
        ratio = QRMath.glog(self.num[0] ) - QRMath.glog(e.num[0] )
        num = [nn ^ QRMath.gexp(QRMath.glog(en) + ratio)
               for nn,en in zip(self.num, e.num)]
        num += self.num[e.getLength():]
        # recursive call
        return QRPolynomial(num, 0).mod(e);

class QRRSBlock:
    RS_BLOCK_TABLE = [
        # L
        # M
        # Q
        # H

        # 1
        [1, 26, 19],
        [1, 26, 16],
        [1, 26, 13],
        [1, 26, 9],

        # 2
        [1, 44, 34],
        [1, 44, 28],
        [1, 44, 22],
        [1, 44, 16],

        # 3
        [1, 70, 55],
        [1, 70, 44],
        [2, 35, 17],
        [2, 35, 13],

        # 4
        [1, 100, 80],
        [2, 50, 32],
        [2, 50, 24],
        [4, 25, 9],

        # 5
        [1, 134, 108],
        [2, 67, 43],
        [2, 33, 15, 2, 34, 16],
        [2, 33, 11, 2, 34, 12],

        # 6
        [2, 86, 68],
        [4, 43, 27],
        [4, 43, 19],
        [4, 43, 15],

        # 7
        [2, 98, 78],
        [4, 49, 31],
        [2, 32, 14, 4, 33, 15],
        [4, 39, 13, 1, 40, 14],

        # 8
        [2, 121, 97],
        [2, 60, 38, 2, 61, 39],
        [4, 40, 18, 2, 41, 19],
        [4, 40, 14, 2, 41, 15],

        # 9
        [2, 146, 116],
        [3, 58, 36, 2, 59, 37],
        [4, 36, 16, 4, 37, 17],
        [4, 36, 12, 4, 37, 13],

        # 10
        [2, 86, 68, 2, 87, 69],
        [4, 69, 43, 1, 70, 44],
        [6, 43, 19, 2, 44, 20],
        [6, 43, 15, 2, 44, 16],

        # 11
        [4, 101, 81],
        [1, 80, 50, 4, 81, 51],
        [4, 50, 22, 4, 51, 23],
        [3, 36, 12, 8, 37, 13],

        # 12
        [2, 116, 92, 2, 117, 93],
        [6, 58, 36, 2, 59, 37],
        [4, 46, 20, 6, 47, 21],
        [7, 42, 14, 4, 43, 15],

        # 13
        [4, 133, 107],
        [8, 59, 37, 1, 60, 38],
        [8, 44, 20, 4, 45, 21],
        [12, 33, 11, 4, 34, 12],

        # 14
        [3, 145, 115, 1, 146, 116],
        [4, 64, 40, 5, 65, 41],
        [11, 36, 16, 5, 37, 17],
        [11, 36, 12, 5, 37, 13],

        # 15
        [5, 109, 87, 1, 110, 88],
        [5, 65, 41, 5, 66, 42],
        [5, 54, 24, 7, 55, 25],
        [11, 36, 12],

        # 16
        [5, 122, 98, 1, 123, 99],
        [7, 73, 45, 3, 74, 46],
        [15, 43, 19, 2, 44, 20],
        [3, 45, 15, 13, 46, 16],

        # 17
        [1, 135, 107, 5, 136, 108],
        [10, 74, 46, 1, 75, 47],
        [1, 50, 22, 15, 51, 23],
        [2, 42, 14, 17, 43, 15],

        # 18
        [5, 150, 120, 1, 151, 121],
        [9, 69, 43, 4, 70, 44],
        [17, 50, 22, 1, 51, 23],
        [2, 42, 14, 19, 43, 15],

        # 19
        [3, 141, 113, 4, 142, 114],
        [3, 70, 44, 11, 71, 45],
        [17, 47, 21, 4, 48, 22],
        [9, 39, 13, 16, 40, 14],

        # 20
        [3, 135, 107, 5, 136, 108],
        [3, 67, 41, 13, 68, 42],
        [15, 54, 24, 5, 55, 25],
        [15, 43, 15, 10, 44, 16],

        # 21
        [4, 144, 116, 4, 145, 117],
        [17, 68, 42],
        [17, 50, 22, 6, 51, 23],
        [19, 46, 16, 6, 47, 17],

        # 22
        [2, 139, 111, 7, 140, 112],
        [17, 74, 46],
        [7, 54, 24, 16, 55, 25],
        [34, 37, 13],

        # 23
        [4, 151, 121, 5, 152, 122],
        [4, 75, 47, 14, 76, 48],
        [11, 54, 24, 14, 55, 25],
        [16, 45, 15, 14, 46, 16],

        # 24
        [6, 147, 117, 4, 148, 118],
        [6, 73, 45, 14, 74, 46],
        [11, 54, 24, 16, 55, 25],
        [30, 46, 16, 2, 47, 17],

        # 25
        [8, 132, 106, 4, 133, 107],
        [8, 75, 47, 13, 76, 48],
        [7, 54, 24, 22, 55, 25],
        [22, 45, 15, 13, 46, 16],

        # 26
        [10, 142, 114, 2, 143, 115],
        [19, 74, 46, 4, 75, 47],
        [28, 50, 22, 6, 51, 23],
        [33, 46, 16, 4, 47, 17],

        # 27
        [8, 152, 122, 4, 153, 123],
        [22, 73, 45, 3, 74, 46],
        [8, 53, 23, 26, 54, 24],
        [12, 45, 15, 28, 46, 16],

        # 28
        [3, 147, 117, 10, 148, 118],
        [3, 73, 45, 23, 74, 46],
        [4, 54, 24, 31, 55, 25],
        [11, 45, 15, 31, 46, 16],

        # 29
        [7, 146, 116, 7, 147, 117],
        [21, 73, 45, 7, 74, 46],
        [1, 53, 23, 37, 54, 24],
        [19, 45, 15, 26, 46, 16],

        # 30
        [5, 145, 115, 10, 146, 116],
        [19, 75, 47, 10, 76, 48],
        [15, 54, 24, 25, 55, 25],
        [23, 45, 15, 25, 46, 16],

        # 31
        [13, 145, 115, 3, 146, 116],
        [2, 74, 46, 29, 75, 47],
        [42, 54, 24, 1, 55, 25],
        [23, 45, 15, 28, 46, 16],

        # 32
        [17, 145, 115],
        [10, 74, 46, 23, 75, 47],
        [10, 54, 24, 35, 55, 25],
        [19, 45, 15, 35, 46, 16],

        # 33
        [17, 145, 115, 1, 146, 116],
        [14, 74, 46, 21, 75, 47],
        [29, 54, 24, 19, 55, 25],
        [11, 45, 15, 46, 46, 16],

        # 34
        [13, 145, 115, 6, 146, 116],
        [14, 74, 46, 23, 75, 47],
        [44, 54, 24, 7, 55, 25],
        [59, 46, 16, 1, 47, 17],

        # 35
        [12, 151, 121, 7, 152, 122],
        [12, 75, 47, 26, 76, 48],
        [39, 54, 24, 14, 55, 25],
        [22, 45, 15, 41, 46, 16],

        # 36
        [6, 151, 121, 14, 152, 122],
        [6, 75, 47, 34, 76, 48],
        [46, 54, 24, 10, 55, 25],
        [2, 45, 15, 64, 46, 16],

        # 37
        [17, 152, 122, 4, 153, 123],
        [29, 74, 46, 14, 75, 47],
        [49, 54, 24, 10, 55, 25],
        [24, 45, 15, 46, 46, 16],

        # 38
        [4, 152, 122, 18, 153, 123],
        [13, 74, 46, 32, 75, 47],
        [48, 54, 24, 14, 55, 25],
        [42, 45, 15, 32, 46, 16],

        # 39
        [20, 147, 117, 4, 148, 118],
        [40, 75, 47, 7, 76, 48],
        [43, 54, 24, 22, 55, 25],
        [10, 45, 15, 67, 46, 16],

        # 40
        [19, 148, 118, 6, 149, 119],
        [18, 75, 47, 31, 76, 48],
        [34, 54, 24, 34, 55, 25],
        [20, 45, 15, 61, 46, 16]

    ]

    def __init__(self, totalCount, dataCount):
        self.totalCount = totalCount
        self.dataCount = dataCount

    @staticmethod
    def getRSBlocks(version, errorCorrectLevel):
        rsBlock = QRRSBlock.getRsBlockTable(version, errorCorrectLevel);
        if rsBlock == None:
            raise Exception("bad rs block @ version:" + version +
                            "/errorCorrectLevel:" + errorCorrectLevel)
        length = len(rsBlock) // 3
        list = []
        for i in range(length):
            count = rsBlock[i * 3 + 0]
            totalCount = rsBlock[i * 3 + 1]
            dataCount  = rsBlock[i * 3 + 2]
            for j in range(count):
                list.append(QRRSBlock(totalCount, dataCount))
        return list;

    @staticmethod
    def getRsBlockTable(version, errorCorrectLevel):
        if errorCorrectLevel == QRErrorCorrectLevel.L:
            return QRRSBlock.RS_BLOCK_TABLE[(version - 1) * 4 + 0];
        elif errorCorrectLevel == QRErrorCorrectLevel.M:
            return QRRSBlock.RS_BLOCK_TABLE[(version - 1) * 4 + 1];
        elif errorCorrectLevel ==  QRErrorCorrectLevel.Q:
            return QRRSBlock.RS_BLOCK_TABLE[(version - 1) * 4 + 2];
        elif errorCorrectLevel ==  QRErrorCorrectLevel.H:
            return QRRSBlock.RS_BLOCK_TABLE[(version - 1) * 4 + 3];
        else:
            return None;

class QRBitBuffer:
    def __init__(self):
        self.buffer = []
        self.length = 0

    def __repr__(self):
        return ".".join([str(n) for n in self.buffer])

    def get(self, index):
        bufIndex = index // 8
        return ( (self.buffer[bufIndex] >> (7 - index % 8) ) & 1) == 1

    def put(self, num, length):
        for i in range(length):
            self.putBit( ( (num >> (length - i - 1) ) & 1) == 1)

    def getLengthInBits(self):
        return self.length

    def putBit(self, bit):
        bufIndex = self.length // 8
        if len(self.buffer) <= bufIndex:
            self.buffer.append(0)
        if bit:
            self.buffer[bufIndex] |= (0x80 >> (self.length % 8) )
        self.length += 1
