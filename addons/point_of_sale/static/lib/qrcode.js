/**
 * @fileoverview
 * - Using the 'QRCode for Javascript library'
 * - Fixed dataset of 'QRCode for Javascript library' for support full-spec.
 * - this library has no dependencies.
 *
 * @author davidshimjs
 * @see <a href="http://www.d-project.com/" target="_blank">http://www.d-project.com/</a>
 * @see <a href="http://jeromeetienne.github.com/jquery-qrcode/" target="_blank">http://jeromeetienne.github.com/jquery-qrcode/</a>
 */
let QRCode;

(() => {
    //---------------------------------------------------------------------
    // QRCode for JavaScript
    //
    // Copyright (c) 2009 Kazuhiko Arase
    //
    // URL: http://www.d-project.com/
    // Github: https://github.com/davidshimjs/qrcodejs
    //
    // Licensed under the MIT license:
    //   http://www.opensource.org/licenses/mit-license.php
    //
    // The MIT License (MIT)
    // ---------------------
    // Copyright (c) 2012 davidshimjs
    //
    // Permission is hereby granted, free of charge,
    // to any person obtaining a copy of this software and associated documentation files (the "Software"),
    // to deal in the Software without restriction,
    // including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
    // and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
    // subject to the following conditions:
    //
    // The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
    //
    // THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    //
    //
    // The word "QR Code" is registered trademark of
    // DENSO WAVE INCORPORATED
    //   http://www.denso-wave.com/qrcode/faqpatent-e.html
    //
    //---------------------------------------------------------------------
    class QR8bitByte {
        constructor(data) {
            this.mode = QRMode.MODE_8BIT_BYTE;
            this.data = data;
            this.parsedData = [];

            // Added to support UTF-8 Characters
            for (let i = 0, l = this.data.length; i < l; i++) {
                const byteArray = [];
                const code = this.data.charCodeAt(i);

                if (code > 0x10000) {
                    byteArray[0] = 0xf0 | ((code & 0x1c0000) >>> 18);
                    byteArray[1] = 0x80 | ((code & 0x3f000) >>> 12);
                    byteArray[2] = 0x80 | ((code & 0xfc0) >>> 6);
                    byteArray[3] = 0x80 | (code & 0x3f);
                } else if (code > 0x800) {
                    byteArray[0] = 0xe0 | ((code & 0xf000) >>> 12);
                    byteArray[1] = 0x80 | ((code & 0xfc0) >>> 6);
                    byteArray[2] = 0x80 | (code & 0x3f);
                } else if (code > 0x80) {
                    byteArray[0] = 0xc0 | ((code & 0x7c0) >>> 6);
                    byteArray[1] = 0x80 | (code & 0x3f);
                } else {
                    byteArray[0] = code;
                }

                this.parsedData.push(byteArray);
            }

            this.parsedData = Array.prototype.concat.apply([], this.parsedData);

            if (this.parsedData.length != this.data.length) {
                this.parsedData.unshift(191);
                this.parsedData.unshift(187);
                this.parsedData.unshift(239);
            }
        }

        getLength(buffer) {
            return this.parsedData.length;
        }

        write(buffer) {
            for (let i = 0, l = this.parsedData.length; i < l; i++) {
                buffer.put(this.parsedData[i], 8);
            }
        }
    }

    class QRCodeModel {
        constructor(typeNumber, errorCorrectLevel) {
            this.typeNumber = typeNumber;
            this.errorCorrectLevel = errorCorrectLevel;
            this.modules = null;
            this.moduleCount = 0;
            this.dataCache = null;
            this.dataList = [];
        }

        addData(data) {
            const newData = new QR8bitByte(data);
            this.dataList.push(newData);
            this.dataCache = null;
        }

        isDark(row, col) {
            if (row < 0 || this.moduleCount <= row || col < 0 || this.moduleCount <= col) {
                throw new Error(`${row},${col}`);
            }
            return this.modules[row][col];
        }

        getModuleCount() {
            return this.moduleCount;
        }
        make() {
            this.makeImpl(false, this.getBestMaskPattern());
        }

        makeImpl(test, maskPattern) {
            this.moduleCount = this.typeNumber * 4 + 17;
            this.modules = new Array(this.moduleCount);
            for (let row = 0; row < this.moduleCount; row++) {
                this.modules[row] = new Array(this.moduleCount);
                for (let col = 0; col < this.moduleCount; col++) {
                    this.modules[row][col] = null;
                }
            }
            this.setupPositionProbePattern(0, 0);
            this.setupPositionProbePattern(this.moduleCount - 7, 0);
            this.setupPositionProbePattern(0, this.moduleCount - 7);
            this.setupPositionAdjustPattern();
            this.setupTimingPattern();
            this.setupTypeInfo(test, maskPattern);
            if (this.typeNumber >= 7) {
                this.setupTypeNumber(test);
            }
            if (this.dataCache == null) {
                this.dataCache = QRCodeModel.createData(
                    this.typeNumber,
                    this.errorCorrectLevel,
                    this.dataList
                );
            }
            this.mapData(this.dataCache, maskPattern);
        }

        setupPositionProbePattern(row, col) {
            for (let r = -1; r <= 7; r++) {
                if (row + r <= -1 || this.moduleCount <= row + r) {
                    continue;
                }
                for (let c = -1; c <= 7; c++) {
                    if (col + c <= -1 || this.moduleCount <= col + c) {
                        continue;
                    }
                    if (
                        (0 <= r && r <= 6 && (c == 0 || c == 6)) ||
                        (0 <= c && c <= 6 && (r == 0 || r == 6)) ||
                        (2 <= r && r <= 4 && 2 <= c && c <= 4)
                    ) {
                        this.modules[row + r][col + c] = true;
                    } else {
                        this.modules[row + r][col + c] = false;
                    }
                }
            }
        }

        getBestMaskPattern() {
            let minLostPoint = 0;
            let pattern = 0;
            for (let i = 0; i < 8; i++) {
                this.makeImpl(true, i);
                const lostPoint = QRUtil.getLostPoint(this);
                if (i == 0 || minLostPoint > lostPoint) {
                    minLostPoint = lostPoint;
                    pattern = i;
                }
            }
            return pattern;
        }

        createMovieClip(target_mc, instance_name, depth) {
            const qr_mc = target_mc.createEmptyMovieClip(instance_name, depth);
            const cs = 1;
            this.make();
            for (let row = 0; row < this.modules.length; row++) {
                const y = row * cs;
                for (let col = 0; col < this.modules[row].length; col++) {
                    const x = col * cs;
                    const dark = this.modules[row][col];
                    if (dark) {
                        qr_mc.beginFill(0, 100);
                        qr_mc.moveTo(x, y);
                        qr_mc.lineTo(x + cs, y);
                        qr_mc.lineTo(x + cs, y + cs);
                        qr_mc.lineTo(x, y + cs);
                        qr_mc.endFill();
                    }
                }
            }
            return qr_mc;
        }

        setupTimingPattern() {
            for (let r = 8; r < this.moduleCount - 8; r++) {
                if (this.modules[r][6] != null) {
                    continue;
                }
                this.modules[r][6] = r % 2 == 0;
            }
            for (let c = 8; c < this.moduleCount - 8; c++) {
                if (this.modules[6][c] != null) {
                    continue;
                }
                this.modules[6][c] = c % 2 == 0;
            }
        }

        setupPositionAdjustPattern() {
            const pos = QRUtil.getPatternPosition(this.typeNumber);
            for (let i = 0; i < pos.length; i++) {
                for (let j = 0; j < pos.length; j++) {
                    const row = pos[i];
                    const col = pos[j];
                    if (this.modules[row][col] != null) {
                        continue;
                    }
                    for (let r = -2; r <= 2; r++) {
                        for (let c = -2; c <= 2; c++) {
                            if (r == -2 || r == 2 || c == -2 || c == 2 || (r == 0 && c == 0)) {
                                this.modules[row + r][col + c] = true;
                            } else {
                                this.modules[row + r][col + c] = false;
                            }
                        }
                    }
                }
            }
        }

        setupTypeNumber(test) {
            const bits = QRUtil.getBCHTypeNumber(this.typeNumber);
            for (let i = 0; i < 18; i++) {
                const mod = !test && ((bits >> i) & 1) == 1;
                this.modules[Math.floor(i / 3)][(i % 3) + this.moduleCount - 8 - 3] = mod;
            }
            for (let i = 0; i < 18; i++) {
                const mod = !test && ((bits >> i) & 1) == 1;
                this.modules[(i % 3) + this.moduleCount - 8 - 3][Math.floor(i / 3)] = mod;
            }
        }

        setupTypeInfo(test, maskPattern) {
            const data = (this.errorCorrectLevel << 3) | maskPattern;
            const bits = QRUtil.getBCHTypeInfo(data);
            for (let i = 0; i < 15; i++) {
                const mod = !test && ((bits >> i) & 1) == 1;
                if (i < 6) {
                    this.modules[i][8] = mod;
                } else if (i < 8) {
                    this.modules[i + 1][8] = mod;
                } else {
                    this.modules[this.moduleCount - 15 + i][8] = mod;
                }
            }
            for (let i = 0; i < 15; i++) {
                const mod = !test && ((bits >> i) & 1) == 1;
                if (i < 8) {
                    this.modules[8][this.moduleCount - i - 1] = mod;
                } else if (i < 9) {
                    this.modules[8][15 - i - 1 + 1] = mod;
                } else {
                    this.modules[8][15 - i - 1] = mod;
                }
            }
            this.modules[this.moduleCount - 8][8] = !test;
        }

        mapData(data, maskPattern) {
            let inc = -1;
            let row = this.moduleCount - 1;
            let bitIndex = 7;
            let byteIndex = 0;
            for (let col = this.moduleCount - 1; col > 0; col -= 2) {
                if (col == 6) col--;
                while (true) {
                    for (let c = 0; c < 2; c++) {
                        if (this.modules[row][col - c] == null) {
                            let dark = false;
                            if (byteIndex < data.length) {
                                dark = ((data[byteIndex] >>> bitIndex) & 1) == 1;
                            }
                            const mask = QRUtil.getMask(maskPattern, row, col - c);
                            if (mask) {
                                dark = !dark;
                            }
                            this.modules[row][col - c] = dark;
                            bitIndex--;
                            if (bitIndex == -1) {
                                byteIndex++;
                                bitIndex = 7;
                            }
                        }
                    }
                    row += inc;
                    if (row < 0 || this.moduleCount <= row) {
                        row -= inc;
                        inc = -inc;
                        break;
                    }
                }
            }
        }

        static createData(typeNumber, errorCorrectLevel, dataList) {
            const rsBlocks = QRRSBlock.getRSBlocks(typeNumber, errorCorrectLevel);
            const buffer = new QRBitBuffer();
            for (let i = 0; i < dataList.length; i++) {
                const data = dataList[i];
                buffer.put(data.mode, 4);
                buffer.put(data.getLength(), QRUtil.getLengthInBits(data.mode, typeNumber));
                data.write(buffer);
            }
            let totalDataCount = 0;
            for (let i = 0; i < rsBlocks.length; i++) {
                totalDataCount += rsBlocks[i].dataCount;
            }
            if (buffer.getLengthInBits() > totalDataCount * 8) {
                throw new Error(
                    `code length overflow. (${buffer.getLengthInBits()}>${totalDataCount * 8})`
                );
            }
            if (buffer.getLengthInBits() + 4 <= totalDataCount * 8) {
                buffer.put(0, 4);
            }
            while (buffer.getLengthInBits() % 8 != 0) {
                buffer.putBit(false);
            }
            while (true) {
                if (buffer.getLengthInBits() >= totalDataCount * 8) {
                    break;
                }
                buffer.put(QRCodeModel.PAD0, 8);
                if (buffer.getLengthInBits() >= totalDataCount * 8) {
                    break;
                }
                buffer.put(QRCodeModel.PAD1, 8);
            }
            return QRCodeModel.createBytes(buffer, rsBlocks);
        }

        static createBytes(buffer, rsBlocks) {
            let offset = 0;
            let maxDcCount = 0;
            let maxEcCount = 0;
            const dcdata = new Array(rsBlocks.length);
            const ecdata = new Array(rsBlocks.length);
            for (let r = 0; r < rsBlocks.length; r++) {
                const dcCount = rsBlocks[r].dataCount;
                const ecCount = rsBlocks[r].totalCount - dcCount;
                maxDcCount = Math.max(maxDcCount, dcCount);
                maxEcCount = Math.max(maxEcCount, ecCount);
                dcdata[r] = new Array(dcCount);
                for (let i = 0; i < dcdata[r].length; i++) {
                    dcdata[r][i] = 0xff & buffer.buffer[i + offset];
                }
                offset += dcCount;
                const rsPoly = QRUtil.getErrorCorrectPolynomial(ecCount);
                const rawPoly = new QRPolynomial(dcdata[r], rsPoly.getLength() - 1);
                const modPoly = rawPoly.mod(rsPoly);
                ecdata[r] = new Array(rsPoly.getLength() - 1);
                for (let i = 0; i < ecdata[r].length; i++) {
                    const modIndex = i + modPoly.getLength() - ecdata[r].length;
                    ecdata[r][i] = modIndex >= 0 ? modPoly.get(modIndex) : 0;
                }
            }
            let totalCodeCount = 0;
            for (let i = 0; i < rsBlocks.length; i++) {
                totalCodeCount += rsBlocks[i].totalCount;
            }
            const data = new Array(totalCodeCount);
            let index = 0;
            for (let i = 0; i < maxDcCount; i++) {
                for (let r = 0; r < rsBlocks.length; r++) {
                    if (i < dcdata[r].length) {
                        data[index++] = dcdata[r][i];
                    }
                }
            }
            for (let i = 0; i < maxEcCount; i++) {
                for (let r = 0; r < rsBlocks.length; r++) {
                    if (i < ecdata[r].length) {
                        data[index++] = ecdata[r][i];
                    }
                }
            }
            return data;
        }
    }

    QRCodeModel.PAD0 = 0xec;
    QRCodeModel.PAD1 = 0x11;
    const QRMode = {
        MODE_NUMBER: 1 << 0,
        MODE_ALPHA_NUM: 1 << 1,
        MODE_8BIT_BYTE: 1 << 2,
        MODE_KANJI: 1 << 3,
    };
    const QRErrorCorrectLevel = { L: 1, M: 0, Q: 3, H: 2 };
    const QRMaskPattern = {
        PATTERN000: 0,
        PATTERN001: 1,
        PATTERN010: 2,
        PATTERN011: 3,
        PATTERN100: 4,
        PATTERN101: 5,
        PATTERN110: 6,
        PATTERN111: 7,
    };
    const QRUtil = {
        PATTERN_POSITION_TABLE: [
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
        ],
        G15: (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0),
        G18:
            (1 << 12) |
            (1 << 11) |
            (1 << 10) |
            (1 << 9) |
            (1 << 8) |
            (1 << 5) |
            (1 << 2) |
            (1 << 0),
        G15_MASK: (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1),
        getBCHTypeInfo(data) {
            let d = data << 10;
            while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) >= 0) {
                d ^= QRUtil.G15 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15));
            }
            return ((data << 10) | d) ^ QRUtil.G15_MASK;
        },
        getBCHTypeNumber(data) {
            let d = data << 12;
            while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) >= 0) {
                d ^= QRUtil.G18 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18));
            }
            return (data << 12) | d;
        },
        getBCHDigit(data) {
            let digit = 0;
            while (data != 0) {
                digit++;
                data >>>= 1;
            }
            return digit;
        },
        getPatternPosition(typeNumber) {
            return QRUtil.PATTERN_POSITION_TABLE[typeNumber - 1];
        },
        getMask(maskPattern, i, j) {
            switch (maskPattern) {
                case QRMaskPattern.PATTERN000:
                    return (i + j) % 2 == 0;
                case QRMaskPattern.PATTERN001:
                    return i % 2 == 0;
                case QRMaskPattern.PATTERN010:
                    return j % 3 == 0;
                case QRMaskPattern.PATTERN011:
                    return (i + j) % 3 == 0;
                case QRMaskPattern.PATTERN100:
                    return (Math.floor(i / 2) + Math.floor(j / 3)) % 2 == 0;
                case QRMaskPattern.PATTERN101:
                    return ((i * j) % 2) + ((i * j) % 3) == 0;
                case QRMaskPattern.PATTERN110:
                    return (((i * j) % 2) + ((i * j) % 3)) % 2 == 0;
                case QRMaskPattern.PATTERN111:
                    return (((i * j) % 3) + ((i + j) % 2)) % 2 == 0;
                default:
                    throw new Error(`bad maskPattern:${maskPattern}`);
            }
        },
        getErrorCorrectPolynomial(errorCorrectLength) {
            let a = new QRPolynomial([1], 0);
            for (let i = 0; i < errorCorrectLength; i++) {
                a = a.multiply(new QRPolynomial([1, QRMath.gexp(i)], 0));
            }
            return a;
        },
        getLengthInBits(mode, type) {
            if (1 <= type && type < 10) {
                switch (mode) {
                    case QRMode.MODE_NUMBER:
                        return 10;
                    case QRMode.MODE_ALPHA_NUM:
                        return 9;
                    case QRMode.MODE_8BIT_BYTE:
                        return 8;
                    case QRMode.MODE_KANJI:
                        return 8;
                    default:
                        throw new Error(`mode:${mode}`);
                }
            } else if (type < 27) {
                switch (mode) {
                    case QRMode.MODE_NUMBER:
                        return 12;
                    case QRMode.MODE_ALPHA_NUM:
                        return 11;
                    case QRMode.MODE_8BIT_BYTE:
                        return 16;
                    case QRMode.MODE_KANJI:
                        return 10;
                    default:
                        throw new Error(`mode:${mode}`);
                }
            } else if (type < 41) {
                switch (mode) {
                    case QRMode.MODE_NUMBER:
                        return 14;
                    case QRMode.MODE_ALPHA_NUM:
                        return 13;
                    case QRMode.MODE_8BIT_BYTE:
                        return 16;
                    case QRMode.MODE_KANJI:
                        return 12;
                    default:
                        throw new Error(`mode:${mode}`);
                }
            } else {
                throw new Error(`type:${type}`);
            }
        },
        getLostPoint(qrCode) {
            const moduleCount = qrCode.getModuleCount();
            let lostPoint = 0;
            for (let row = 0; row < moduleCount; row++) {
                for (let col = 0; col < moduleCount; col++) {
                    let sameCount = 0;
                    const dark = qrCode.isDark(row, col);
                    for (let r = -1; r <= 1; r++) {
                        if (row + r < 0 || moduleCount <= row + r) {
                            continue;
                        }
                        for (let c = -1; c <= 1; c++) {
                            if (col + c < 0 || moduleCount <= col + c) {
                                continue;
                            }
                            if (r == 0 && c == 0) {
                                continue;
                            }
                            if (dark == qrCode.isDark(row + r, col + c)) {
                                sameCount++;
                            }
                        }
                    }
                    if (sameCount > 5) {
                        lostPoint += 3 + sameCount - 5;
                    }
                }
            }
            for (let row = 0; row < moduleCount - 1; row++) {
                for (let col = 0; col < moduleCount - 1; col++) {
                    let count = 0;
                    if (qrCode.isDark(row, col)) count++;
                    if (qrCode.isDark(row + 1, col)) count++;
                    if (qrCode.isDark(row, col + 1)) count++;
                    if (qrCode.isDark(row + 1, col + 1)) count++;
                    if (count == 0 || count == 4) {
                        lostPoint += 3;
                    }
                }
            }
            for (let row = 0; row < moduleCount; row++) {
                for (let col = 0; col < moduleCount - 6; col++) {
                    if (
                        qrCode.isDark(row, col) &&
                        !qrCode.isDark(row, col + 1) &&
                        qrCode.isDark(row, col + 2) &&
                        qrCode.isDark(row, col + 3) &&
                        qrCode.isDark(row, col + 4) &&
                        !qrCode.isDark(row, col + 5) &&
                        qrCode.isDark(row, col + 6)
                    ) {
                        lostPoint += 40;
                    }
                }
            }
            for (let col = 0; col < moduleCount; col++) {
                for (let row = 0; row < moduleCount - 6; row++) {
                    if (
                        qrCode.isDark(row, col) &&
                        !qrCode.isDark(row + 1, col) &&
                        qrCode.isDark(row + 2, col) &&
                        qrCode.isDark(row + 3, col) &&
                        qrCode.isDark(row + 4, col) &&
                        !qrCode.isDark(row + 5, col) &&
                        qrCode.isDark(row + 6, col)
                    ) {
                        lostPoint += 40;
                    }
                }
            }
            let darkCount = 0;
            for (let col = 0; col < moduleCount; col++) {
                for (let row = 0; row < moduleCount; row++) {
                    if (qrCode.isDark(row, col)) {
                        darkCount++;
                    }
                }
            }
            const ratio = Math.abs((100 * darkCount) / moduleCount / moduleCount - 50) / 5;
            lostPoint += ratio * 10;
            return lostPoint;
        },
    };
    const QRMath = {
        glog(n) {
            if (n < 1) {
                throw new Error(`glog(${n})`);
            }
            return QRMath.LOG_TABLE[n];
        },
        gexp(n) {
            while (n < 0) {
                n += 255;
            }
            while (n >= 256) {
                n -= 255;
            }
            return QRMath.EXP_TABLE[n];
        },
        EXP_TABLE: new Array(256),
        LOG_TABLE: new Array(256),
    };
    for (let i = 0; i < 8; i++) {
        QRMath.EXP_TABLE[i] = 1 << i;
    }
    for (let i = 8; i < 256; i++) {
        QRMath.EXP_TABLE[i] =
            QRMath.EXP_TABLE[i - 4] ^
            QRMath.EXP_TABLE[i - 5] ^
            QRMath.EXP_TABLE[i - 6] ^
            QRMath.EXP_TABLE[i - 8];
    }
    for (let i = 0; i < 255; i++) {
        QRMath.LOG_TABLE[QRMath.EXP_TABLE[i]] = i;
    }

    class QRPolynomial {
        constructor(num, shift) {
            if (num.length == undefined) {
                throw new Error(`${num.length}/${shift}`);
            }
            let offset = 0;
            while (offset < num.length && num[offset] == 0) {
                offset++;
            }
            this.num = new Array(num.length - offset + shift);
            for (let i = 0; i < num.length - offset; i++) {
                this.num[i] = num[i + offset];
            }
        }

        get(index) {
            return this.num[index];
        }
        getLength() {
            return this.num.length;
        }

        multiply(e) {
            const num = new Array(this.getLength() + e.getLength() - 1);
            for (let i = 0; i < this.getLength(); i++) {
                for (let j = 0; j < e.getLength(); j++) {
                    num[i + j] ^= QRMath.gexp(QRMath.glog(this.get(i)) + QRMath.glog(e.get(j)));
                }
            }
            return new QRPolynomial(num, 0);
        }

        mod(e) {
            if (this.getLength() - e.getLength() < 0) {
                return this;
            }
            const ratio = QRMath.glog(this.get(0)) - QRMath.glog(e.get(0));
            const num = new Array(this.getLength());
            for (let i = 0; i < this.getLength(); i++) {
                num[i] = this.get(i);
            }
            for (let i = 0; i < e.getLength(); i++) {
                num[i] ^= QRMath.gexp(QRMath.glog(e.get(i)) + ratio);
            }
            return new QRPolynomial(num, 0).mod(e);
        }
    }

    class QRRSBlock {
        constructor(totalCount, dataCount) {
            this.totalCount = totalCount;
            this.dataCount = dataCount;
        }

        static getRSBlocks(typeNumber, errorCorrectLevel) {
            const rsBlock = QRRSBlock.getRsBlockTable(typeNumber, errorCorrectLevel);
            if (rsBlock == undefined) {
                throw new Error(
                    `bad rs block @ typeNumber:${typeNumber}/errorCorrectLevel:${errorCorrectLevel}`
                );
            }
            const length = rsBlock.length / 3;
            const list = [];
            for (let i = 0; i < length; i++) {
                const count = rsBlock[i * 3 + 0];
                const totalCount = rsBlock[i * 3 + 1];
                const dataCount = rsBlock[i * 3 + 2];
                for (let j = 0; j < count; j++) {
                    list.push(new QRRSBlock(totalCount, dataCount));
                }
            }
            return list;
        }

        static getRsBlockTable(typeNumber, errorCorrectLevel) {
            switch (errorCorrectLevel) {
                case QRErrorCorrectLevel.L:
                    return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 0];
                case QRErrorCorrectLevel.M:
                    return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 1];
                case QRErrorCorrectLevel.Q:
                    return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 2];
                case QRErrorCorrectLevel.H:
                    return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 3];
                default:
                    return undefined;
            }
        }
    }

    QRRSBlock.RS_BLOCK_TABLE = [
        [1, 26, 19],
        [1, 26, 16],
        [1, 26, 13],
        [1, 26, 9],
        [1, 44, 34],
        [1, 44, 28],
        [1, 44, 22],
        [1, 44, 16],
        [1, 70, 55],
        [1, 70, 44],
        [2, 35, 17],
        [2, 35, 13],
        [1, 100, 80],
        [2, 50, 32],
        [2, 50, 24],
        [4, 25, 9],
        [1, 134, 108],
        [2, 67, 43],
        [2, 33, 15, 2, 34, 16],
        [2, 33, 11, 2, 34, 12],
        [2, 86, 68],
        [4, 43, 27],
        [4, 43, 19],
        [4, 43, 15],
        [2, 98, 78],
        [4, 49, 31],
        [2, 32, 14, 4, 33, 15],
        [4, 39, 13, 1, 40, 14],
        [2, 121, 97],
        [2, 60, 38, 2, 61, 39],
        [4, 40, 18, 2, 41, 19],
        [4, 40, 14, 2, 41, 15],
        [2, 146, 116],
        [3, 58, 36, 2, 59, 37],
        [4, 36, 16, 4, 37, 17],
        [4, 36, 12, 4, 37, 13],
        [2, 86, 68, 2, 87, 69],
        [4, 69, 43, 1, 70, 44],
        [6, 43, 19, 2, 44, 20],
        [6, 43, 15, 2, 44, 16],
        [4, 101, 81],
        [1, 80, 50, 4, 81, 51],
        [4, 50, 22, 4, 51, 23],
        [3, 36, 12, 8, 37, 13],
        [2, 116, 92, 2, 117, 93],
        [6, 58, 36, 2, 59, 37],
        [4, 46, 20, 6, 47, 21],
        [7, 42, 14, 4, 43, 15],
        [4, 133, 107],
        [8, 59, 37, 1, 60, 38],
        [8, 44, 20, 4, 45, 21],
        [12, 33, 11, 4, 34, 12],
        [3, 145, 115, 1, 146, 116],
        [4, 64, 40, 5, 65, 41],
        [11, 36, 16, 5, 37, 17],
        [11, 36, 12, 5, 37, 13],
        [5, 109, 87, 1, 110, 88],
        [5, 65, 41, 5, 66, 42],
        [5, 54, 24, 7, 55, 25],
        [11, 36, 12],
        [5, 122, 98, 1, 123, 99],
        [7, 73, 45, 3, 74, 46],
        [15, 43, 19, 2, 44, 20],
        [3, 45, 15, 13, 46, 16],
        [1, 135, 107, 5, 136, 108],
        [10, 74, 46, 1, 75, 47],
        [1, 50, 22, 15, 51, 23],
        [2, 42, 14, 17, 43, 15],
        [5, 150, 120, 1, 151, 121],
        [9, 69, 43, 4, 70, 44],
        [17, 50, 22, 1, 51, 23],
        [2, 42, 14, 19, 43, 15],
        [3, 141, 113, 4, 142, 114],
        [3, 70, 44, 11, 71, 45],
        [17, 47, 21, 4, 48, 22],
        [9, 39, 13, 16, 40, 14],
        [3, 135, 107, 5, 136, 108],
        [3, 67, 41, 13, 68, 42],
        [15, 54, 24, 5, 55, 25],
        [15, 43, 15, 10, 44, 16],
        [4, 144, 116, 4, 145, 117],
        [17, 68, 42],
        [17, 50, 22, 6, 51, 23],
        [19, 46, 16, 6, 47, 17],
        [2, 139, 111, 7, 140, 112],
        [17, 74, 46],
        [7, 54, 24, 16, 55, 25],
        [34, 37, 13],
        [4, 151, 121, 5, 152, 122],
        [4, 75, 47, 14, 76, 48],
        [11, 54, 24, 14, 55, 25],
        [16, 45, 15, 14, 46, 16],
        [6, 147, 117, 4, 148, 118],
        [6, 73, 45, 14, 74, 46],
        [11, 54, 24, 16, 55, 25],
        [30, 46, 16, 2, 47, 17],
        [8, 132, 106, 4, 133, 107],
        [8, 75, 47, 13, 76, 48],
        [7, 54, 24, 22, 55, 25],
        [22, 45, 15, 13, 46, 16],
        [10, 142, 114, 2, 143, 115],
        [19, 74, 46, 4, 75, 47],
        [28, 50, 22, 6, 51, 23],
        [33, 46, 16, 4, 47, 17],
        [8, 152, 122, 4, 153, 123],
        [22, 73, 45, 3, 74, 46],
        [8, 53, 23, 26, 54, 24],
        [12, 45, 15, 28, 46, 16],
        [3, 147, 117, 10, 148, 118],
        [3, 73, 45, 23, 74, 46],
        [4, 54, 24, 31, 55, 25],
        [11, 45, 15, 31, 46, 16],
        [7, 146, 116, 7, 147, 117],
        [21, 73, 45, 7, 74, 46],
        [1, 53, 23, 37, 54, 24],
        [19, 45, 15, 26, 46, 16],
        [5, 145, 115, 10, 146, 116],
        [19, 75, 47, 10, 76, 48],
        [15, 54, 24, 25, 55, 25],
        [23, 45, 15, 25, 46, 16],
        [13, 145, 115, 3, 146, 116],
        [2, 74, 46, 29, 75, 47],
        [42, 54, 24, 1, 55, 25],
        [23, 45, 15, 28, 46, 16],
        [17, 145, 115],
        [10, 74, 46, 23, 75, 47],
        [10, 54, 24, 35, 55, 25],
        [19, 45, 15, 35, 46, 16],
        [17, 145, 115, 1, 146, 116],
        [14, 74, 46, 21, 75, 47],
        [29, 54, 24, 19, 55, 25],
        [11, 45, 15, 46, 46, 16],
        [13, 145, 115, 6, 146, 116],
        [14, 74, 46, 23, 75, 47],
        [44, 54, 24, 7, 55, 25],
        [59, 46, 16, 1, 47, 17],
        [12, 151, 121, 7, 152, 122],
        [12, 75, 47, 26, 76, 48],
        [39, 54, 24, 14, 55, 25],
        [22, 45, 15, 41, 46, 16],
        [6, 151, 121, 14, 152, 122],
        [6, 75, 47, 34, 76, 48],
        [46, 54, 24, 10, 55, 25],
        [2, 45, 15, 64, 46, 16],
        [17, 152, 122, 4, 153, 123],
        [29, 74, 46, 14, 75, 47],
        [49, 54, 24, 10, 55, 25],
        [24, 45, 15, 46, 46, 16],
        [4, 152, 122, 18, 153, 123],
        [13, 74, 46, 32, 75, 47],
        [48, 54, 24, 14, 55, 25],
        [42, 45, 15, 32, 46, 16],
        [20, 147, 117, 4, 148, 118],
        [40, 75, 47, 7, 76, 48],
        [43, 54, 24, 22, 55, 25],
        [10, 45, 15, 67, 46, 16],
        [19, 148, 118, 6, 149, 119],
        [18, 75, 47, 31, 76, 48],
        [34, 54, 24, 34, 55, 25],
        [20, 45, 15, 61, 46, 16],
    ];

    class QRBitBuffer {
        constructor() {
            this.buffer = [];
            this.length = 0;
        }
        get(index) {
            const bufIndex = Math.floor(index / 8);
            return ((this.buffer[bufIndex] >>> (7 - (index % 8))) & 1) == 1;
        }
        put(num, length) {
            for (let i = 0; i < length; i++) {
                this.putBit(((num >>> (length - i - 1)) & 1) == 1);
            }
        }
        getLengthInBits() {
            return this.length;
        }

        putBit(bit) {
            const bufIndex = Math.floor(this.length / 8);
            if (this.buffer.length <= bufIndex) {
                this.buffer.push(0);
            }
            if (bit) {
                this.buffer[bufIndex] |= 0x80 >>> this.length % 8;
            }
            this.length++;
        }
    }

    const QRCodeLimitLength = [
        [17, 14, 11, 7],
        [32, 26, 20, 14],
        [53, 42, 32, 24],
        [78, 62, 46, 34],
        [106, 84, 60, 44],
        [134, 106, 74, 58],
        [154, 122, 86, 64],
        [192, 152, 108, 84],
        [230, 180, 130, 98],
        [271, 213, 151, 119],
        [321, 251, 177, 137],
        [367, 287, 203, 155],
        [425, 331, 241, 177],
        [458, 362, 258, 194],
        [520, 412, 292, 220],
        [586, 450, 322, 250],
        [644, 504, 364, 280],
        [718, 560, 394, 310],
        [792, 624, 442, 338],
        [858, 666, 482, 382],
        [929, 711, 509, 403],
        [1003, 779, 565, 439],
        [1091, 857, 611, 461],
        [1171, 911, 661, 511],
        [1273, 997, 715, 535],
        [1367, 1059, 751, 593],
        [1465, 1125, 805, 625],
        [1528, 1190, 868, 658],
        [1628, 1264, 908, 698],
        [1732, 1370, 982, 742],
        [1840, 1452, 1030, 790],
        [1952, 1538, 1112, 842],
        [2068, 1628, 1168, 898],
        [2188, 1722, 1228, 958],
        [2303, 1809, 1283, 983],
        [2431, 1911, 1351, 1051],
        [2563, 1989, 1423, 1093],
        [2699, 2099, 1499, 1139],
        [2809, 2213, 1579, 1219],
        [2953, 2331, 1663, 1273],
    ];

    // android 2.x doesn't support Data-URI spec
    function _getAndroid() {
        let android = false;
        const sAgent = navigator.userAgent;

        if (/android/i.test(sAgent)) {
            // android
            android = true;
            const aMat = sAgent.toString().match(/android ([0-9]\.[0-9])/i);

            if (aMat && aMat[1]) {
                android = parseFloat(aMat[1]);
            }
        }

        return android;
    }

    const svgDrawer = (() => {
        const Drawing = function (el, htOption) {
            this._el = el;
            this._htOption = htOption;
        };

        Drawing.prototype.draw = function (oQRCode) {
            const _htOption = this._htOption;
            const _el = this._el;
            const nCount = oQRCode.getModuleCount();
            const nWidth = Math.floor(_htOption.width / nCount);
            const nHeight = Math.floor(_htOption.height / nCount);

            this.clear();

            function makeSVG(tag, attrs) {
                const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
                for (const k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
                return el;
            }

            const svg = makeSVG("svg", {
                viewBox: `0 0 ${String(nCount)} ${String(nCount)}`,
                width: "100%",
                height: "100%",
                fill: _htOption.colorLight,
            });
            svg.setAttributeNS(
                "http://www.w3.org/2000/xmlns/",
                "xmlns:xlink",
                "http://www.w3.org/1999/xlink"
            );
            _el.appendChild(svg);

            svg.appendChild(
                makeSVG("rect", { fill: _htOption.colorLight, width: "100%", height: "100%" })
            );
            svg.appendChild(
                makeSVG("rect", {
                    fill: _htOption.colorDark,
                    width: "1",
                    height: "1",
                    id: "template",
                })
            );

            for (let row = 0; row < nCount; row++) {
                for (let col = 0; col < nCount; col++) {
                    if (oQRCode.isDark(row, col)) {
                        const child = makeSVG("use", { x: String(col), y: String(row) });
                        child.setAttributeNS("http://www.w3.org/1999/xlink", "href", "#template");
                        svg.appendChild(child);
                    }
                }
            }
        };
        Drawing.prototype.clear = function () {
            while (this._el.hasChildNodes()) this._el.removeChild(this._el.lastChild);
        };
        return Drawing;
    })();

    const useSVG = document.documentElement.tagName.toLowerCase() === "svg";

    // Drawing in DOM by using Table tag
    let Drawing = useSVG
        ? svgDrawer
        : (function () {
              // Drawing in Canvas
              function _onMakeImage() {
                  this._elImage.src = this._elCanvas.toDataURL("image/png");
                  this._elImage.style.display = "block";
                  this._elCanvas.style.display = "none";
              }

              // Android 2.1 bug workaround
              // http://code.google.com/p/android/issues/detail?id=5141
              if (this._android && this._android <= 2.1) {
                  const factor = 1 / window.devicePixelRatio;
                  const drawImage = CanvasRenderingContext2D.prototype.drawImage;
                  CanvasRenderingContext2D.prototype.drawImage = function (
                      image,
                      sx,
                      sy,
                      sw,
                      sh,
                      dx,
                      dy,
                      dw,
                      dh
                  ) {
                      if ("nodeName" in image && /img/i.test(image.nodeName)) {
                          for (let i = arguments.length - 1; i >= 1; i--) {
                              arguments[i] = arguments[i] * factor;
                          }
                      } else if (typeof dw == "undefined") {
                          arguments[1] *= factor;
                          arguments[2] *= factor;
                          arguments[3] *= factor;
                          arguments[4] *= factor;
                      }

                      drawImage.apply(this, arguments);
                  };
              }

              /**
               * Check whether the user's browser supports Data URI or not
               *
               * @private
               * @param {Function} fSuccess Occurs if it supports Data URI
               * @param {Function} fFail Occurs if it doesn't support Data URI
               */
              function _safeSetDataURI(fSuccess, fFail) {
                  const self = this;
                  self._fFail = fFail;
                  self._fSuccess = fSuccess;

                  // Check it just once
                  if (self._bSupportDataURI === null) {
                      const el = document.createElement("img");
                      const fOnError = () => {
                          self._bSupportDataURI = false;

                          if (self._fFail) {
                              self._fFail.call(self);
                          }
                      };
                      const fOnSuccess = () => {
                          self._bSupportDataURI = true;

                          if (self._fSuccess) {
                              self._fSuccess.call(self);
                          }
                      };

                      el.onabort = fOnError;
                      el.onerror = fOnError;
                      el.onload = fOnSuccess;
                      el.src =
                          "data:image/gif;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="; // the Image contains 1px data.
                      return;
                  } else if (self._bSupportDataURI === true && self._fSuccess) {
                      self._fSuccess.call(self);
                  } else if (self._bSupportDataURI === false && self._fFail) {
                      self._fFail.call(self);
                  }
              }

              /**
               * Drawing QRCode by using canvas
               *
               * @constructor
               * @param {HTMLElement} el
               * @param {Object} htOption QRCode Options
               */
              class Drawing {
                  constructor(el, htOption) {
                      this._bIsPainted = false;
                      this._android = _getAndroid();

                      this._htOption = htOption;
                      this._elCanvas = document.createElement("canvas");
                      this._elCanvas.width = htOption.width;
                      this._elCanvas.height = htOption.height;
                      el.appendChild(this._elCanvas);
                      this._el = el;
                      this._oContext = this._elCanvas.getContext("2d");
                      this._bIsPainted = false;
                      this._elImage = document.createElement("img");
                      this._elImage.alt = "Scan me!";
                      this._elImage.style.display = "none";
                      this._el.appendChild(this._elImage);
                      this._bSupportDataURI = null;
                  }

                  /**
                   * Draw the QRCode
                   *
                   * @param {QRCode} oQRCode
                   */
                  draw(oQRCode) {
                      const _elImage = this._elImage;
                      const _oContext = this._oContext;
                      const _htOption = this._htOption;

                      const nCount = oQRCode.getModuleCount();
                      const nWidth = _htOption.width / nCount;
                      const nHeight = _htOption.height / nCount;
                      const nRoundedWidth = Math.round(nWidth);
                      const nRoundedHeight = Math.round(nHeight);

                      _elImage.style.display = "none";
                      this.clear();

                      for (let row = 0; row < nCount; row++) {
                          for (let col = 0; col < nCount; col++) {
                              const bIsDark = oQRCode.isDark(row, col);
                              const nLeft = col * nWidth;
                              const nTop = row * nHeight;
                              _oContext.strokeStyle = bIsDark
                                  ? _htOption.colorDark
                                  : _htOption.colorLight;
                              _oContext.lineWidth = 1;
                              _oContext.fillStyle = bIsDark
                                  ? _htOption.colorDark
                                  : _htOption.colorLight;
                              _oContext.fillRect(nLeft, nTop, nWidth, nHeight);

                              // 안티 앨리어싱 방지 처리
                              _oContext.strokeRect(
                                  Math.floor(nLeft) + 0.5,
                                  Math.floor(nTop) + 0.5,
                                  nRoundedWidth,
                                  nRoundedHeight
                              );

                              _oContext.strokeRect(
                                  Math.ceil(nLeft) - 0.5,
                                  Math.ceil(nTop) - 0.5,
                                  nRoundedWidth,
                                  nRoundedHeight
                              );
                          }
                      }

                      this._bIsPainted = true;
                  }

                  /**
                   * Make the image from Canvas if the browser supports Data URI.
                   */
                  makeImage() {
                      if (this._bIsPainted) {
                          _safeSetDataURI.call(this, _onMakeImage);
                      }
                  }

                  /**
                   * Return whether the QRCode is painted or not
                   *
                   * @return {Boolean}
                   */
                  isPainted() {
                      return this._bIsPainted;
                  }

                  /**
                   * Clear the QRCode
                   */
                  clear() {
                      this._oContext.clearRect(0, 0, this._elCanvas.width, this._elCanvas.height);
                      this._bIsPainted = false;
                  }

                  /**
                   * @private
                   * @param {Number} nNumber
                   */
                  round(nNumber) {
                      if (!nNumber) {
                          return nNumber;
                      }

                      return Math.floor(nNumber * 1000) / 1000;
                  }
              }

              return Drawing;
          })();

    /**
     * Get the type by string length
     *
     * @private
     * @param {String} sText
     * @param {Number} nCorrectLevel
     * @return {Number} type
     */
    function _getTypeNumber(sText, nCorrectLevel) {
        let nType = 1;
        const length = _getUTF8Length(sText);

        for (let i = 0, len = QRCodeLimitLength.length; i <= len; i++) {
            let nLimit = 0;

            switch (nCorrectLevel) {
                case QRErrorCorrectLevel.L:
                    nLimit = QRCodeLimitLength[i][0];
                    break;
                case QRErrorCorrectLevel.M:
                    nLimit = QRCodeLimitLength[i][1];
                    break;
                case QRErrorCorrectLevel.Q:
                    nLimit = QRCodeLimitLength[i][2];
                    break;
                case QRErrorCorrectLevel.H:
                    nLimit = QRCodeLimitLength[i][3];
                    break;
            }

            if (length <= nLimit) {
                break;
            } else {
                nType++;
            }
        }

        if (nType > QRCodeLimitLength.length) {
            throw new Error("Too long data");
        }

        return nType;
    }

    function _getUTF8Length(sText) {
        const replacedText = encodeURI(sText)
            .toString()
            .replace(/\%[0-9a-fA-F]{2}/g, "a");
        return replacedText.length + (replacedText.length != sText ? 3 : 0);
    }

    /**
     * @class QRCode
     * @constructor
     * @example
     * new QRCode(document.getElementById("test"), "http://jindo.dev.naver.com/collie");
     *
     * @example
     * const oQRCode = new QRCode("test", {
     *    text : "http://naver.com",
     *    width : 128,
     *    height : 128
     * });
     *
     * oQRCode.clear(); // Clear the QRCode.
     * oQRCode.makeCode("http://map.naver.com"); // Re-create the QRCode.
     *
     * @param {HTMLElement|String} el target element or 'id' attribute of element.
     * @param {Object|String} vOption
     * @param {String} vOption.text QRCode link data
     * @param {Number} [vOption.width=256]
     * @param {Number} [vOption.height=256]
     * @param {String} [vOption.colorDark="#000000"]
     * @param {String} [vOption.colorLight="#ffffff"]
     * @param {QRCode.CorrectLevel} [vOption.correctLevel=QRCode.CorrectLevel.H] [L|M|Q|H]
     */
    QRCode = function (el, vOption) {
        this._htOption = {
            width: 256,
            height: 256,
            typeNumber: 4,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRErrorCorrectLevel.H,
        };

        if (typeof vOption === "string") {
            vOption = {
                text: vOption,
            };
        }

        // Overwrites options
        if (vOption) {
            for (const i in vOption) {
                this._htOption[i] = vOption[i];
            }
        }

        if (typeof el == "string") {
            el = document.getElementById(el);
        }

        if (this._htOption.useSVG) {
            Drawing = svgDrawer;
        }

        this._android = _getAndroid();
        this._el = el;
        this._oQRCode = null;
        this._oDrawing = new Drawing(this._el, this._htOption);

        if (this._htOption.text) {
            this.makeCode(this._htOption.text);
        }
    };

    /**
     * Make the QRCode
     *
     * @param {String} sText link data
     */
    QRCode.prototype.makeCode = function (sText) {
        this._oQRCode = new QRCodeModel(
            _getTypeNumber(sText, this._htOption.correctLevel),
            this._htOption.correctLevel
        );
        this._oQRCode.addData(sText);
        this._oQRCode.make();
        this._el.title = sText;
        this._oDrawing.draw(this._oQRCode);
        this.makeImage();
    };

    /**
     * Make the Image from Canvas element
     * - It occurs automatically
     * - Android below 3 doesn't support Data-URI spec.
     *
     * @private
     */
    QRCode.prototype.makeImage = function () {
        if (
            typeof this._oDrawing.makeImage == "function" &&
            (!this._android || this._android >= 3)
        ) {
            this._oDrawing.makeImage();
        }
    };

    /**
     * Clear the QRCode
     */
    QRCode.prototype.clear = function () {
        this._oDrawing.clear();
    };

    /**
     * @name QRCode.CorrectLevel
     */
    QRCode.CorrectLevel = QRErrorCorrectLevel;
})();
