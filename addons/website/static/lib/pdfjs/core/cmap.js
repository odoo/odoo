/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/* globals Util, isString, isInt, warn, error, isCmd, isEOF, isName, Lexer,
           isStream, StringStream, PDFJS, assert */

'use strict';

var BUILT_IN_CMAPS = [
// << Start unicode maps.
'Adobe-GB1-UCS2',
'Adobe-CNS1-UCS2',
'Adobe-Japan1-UCS2',
'Adobe-Korea1-UCS2',
// >> End unicode maps.
'78-EUC-H',
'78-EUC-V',
'78-H',
'78-RKSJ-H',
'78-RKSJ-V',
'78-V',
'78ms-RKSJ-H',
'78ms-RKSJ-V',
'83pv-RKSJ-H',
'90ms-RKSJ-H',
'90ms-RKSJ-V',
'90msp-RKSJ-H',
'90msp-RKSJ-V',
'90pv-RKSJ-H',
'90pv-RKSJ-V',
'Add-H',
'Add-RKSJ-H',
'Add-RKSJ-V',
'Add-V',
'Adobe-CNS1-0',
'Adobe-CNS1-1',
'Adobe-CNS1-2',
'Adobe-CNS1-3',
'Adobe-CNS1-4',
'Adobe-CNS1-5',
'Adobe-CNS1-6',
'Adobe-GB1-0',
'Adobe-GB1-1',
'Adobe-GB1-2',
'Adobe-GB1-3',
'Adobe-GB1-4',
'Adobe-GB1-5',
'Adobe-Japan1-0',
'Adobe-Japan1-1',
'Adobe-Japan1-2',
'Adobe-Japan1-3',
'Adobe-Japan1-4',
'Adobe-Japan1-5',
'Adobe-Japan1-6',
'Adobe-Korea1-0',
'Adobe-Korea1-1',
'Adobe-Korea1-2',
'B5-H',
'B5-V',
'B5pc-H',
'B5pc-V',
'CNS-EUC-H',
'CNS-EUC-V',
'CNS1-H',
'CNS1-V',
'CNS2-H',
'CNS2-V',
'ETHK-B5-H',
'ETHK-B5-V',
'ETen-B5-H',
'ETen-B5-V',
'ETenms-B5-H',
'ETenms-B5-V',
'EUC-H',
'EUC-V',
'Ext-H',
'Ext-RKSJ-H',
'Ext-RKSJ-V',
'Ext-V',
'GB-EUC-H',
'GB-EUC-V',
'GB-H',
'GB-V',
'GBK-EUC-H',
'GBK-EUC-V',
'GBK2K-H',
'GBK2K-V',
'GBKp-EUC-H',
'GBKp-EUC-V',
'GBT-EUC-H',
'GBT-EUC-V',
'GBT-H',
'GBT-V',
'GBTpc-EUC-H',
'GBTpc-EUC-V',
'GBpc-EUC-H',
'GBpc-EUC-V',
'H',
'HKdla-B5-H',
'HKdla-B5-V',
'HKdlb-B5-H',
'HKdlb-B5-V',
'HKgccs-B5-H',
'HKgccs-B5-V',
'HKm314-B5-H',
'HKm314-B5-V',
'HKm471-B5-H',
'HKm471-B5-V',
'HKscs-B5-H',
'HKscs-B5-V',
'Hankaku',
'Hiragana',
'KSC-EUC-H',
'KSC-EUC-V',
'KSC-H',
'KSC-Johab-H',
'KSC-Johab-V',
'KSC-V',
'KSCms-UHC-H',
'KSCms-UHC-HW-H',
'KSCms-UHC-HW-V',
'KSCms-UHC-V',
'KSCpc-EUC-H',
'KSCpc-EUC-V',
'Katakana',
'NWP-H',
'NWP-V',
'RKSJ-H',
'RKSJ-V',
'Roman',
'UniCNS-UCS2-H',
'UniCNS-UCS2-V',
'UniCNS-UTF16-H',
'UniCNS-UTF16-V',
'UniCNS-UTF32-H',
'UniCNS-UTF32-V',
'UniCNS-UTF8-H',
'UniCNS-UTF8-V',
'UniGB-UCS2-H',
'UniGB-UCS2-V',
'UniGB-UTF16-H',
'UniGB-UTF16-V',
'UniGB-UTF32-H',
'UniGB-UTF32-V',
'UniGB-UTF8-H',
'UniGB-UTF8-V',
'UniJIS-UCS2-H',
'UniJIS-UCS2-HW-H',
'UniJIS-UCS2-HW-V',
'UniJIS-UCS2-V',
'UniJIS-UTF16-H',
'UniJIS-UTF16-V',
'UniJIS-UTF32-H',
'UniJIS-UTF32-V',
'UniJIS-UTF8-H',
'UniJIS-UTF8-V',
'UniJIS2004-UTF16-H',
'UniJIS2004-UTF16-V',
'UniJIS2004-UTF32-H',
'UniJIS2004-UTF32-V',
'UniJIS2004-UTF8-H',
'UniJIS2004-UTF8-V',
'UniJISPro-UCS2-HW-V',
'UniJISPro-UCS2-V',
'UniJISPro-UTF8-V',
'UniJISX0213-UTF32-H',
'UniJISX0213-UTF32-V',
'UniJISX02132004-UTF32-H',
'UniJISX02132004-UTF32-V',
'UniKS-UCS2-H',
'UniKS-UCS2-V',
'UniKS-UTF16-H',
'UniKS-UTF16-V',
'UniKS-UTF32-H',
'UniKS-UTF32-V',
'UniKS-UTF8-H',
'UniKS-UTF8-V',
'V',
'WP-Symbol'];

// CMap, not to be confused with TrueType's cmap.
var CMap = (function CMapClosure() {
  function CMap(builtInCMap) {
    // Codespace ranges are stored as follows:
    // [[1BytePairs], [2BytePairs], [3BytePairs], [4BytePairs]]
    // where nBytePairs are ranges e.g. [low1, high1, low2, high2, ...]
    this.codespaceRanges = [[], [], [], []];
    this.numCodespaceRanges = 0;
    // Map entries have one of two forms.
    // - cid chars are 16-bit unsigned integers, stored as integers.
    // - bf chars are variable-length byte sequences, stored as strings, with
    //   one byte per character.
    this._map = [];
    this.vertical = false;
    this.useCMap = null;
    this.builtInCMap = builtInCMap;
  }
  CMap.prototype = {
    addCodespaceRange: function(n, low, high) {
      this.codespaceRanges[n - 1].push(low, high);
      this.numCodespaceRanges++;
    },

    mapCidRange: function(low, high, dstLow) {
      while (low <= high) {
        this._map[low++] = dstLow++;
      }
    },

    mapBfRange: function(low, high, dstLow) {
      var lastByte = dstLow.length - 1;
      while (low <= high) {
        this._map[low++] = dstLow;
        // Only the last byte has to be incremented.
        dstLow = dstLow.substr(0, lastByte) +
                 String.fromCharCode(dstLow.charCodeAt(lastByte) + 1);
      }
    },

    mapBfRangeToArray: function(low, high, array) {
      var i = 0, ii = array.length;
      while (low <= high && i < ii) {
        this._map[low] = array[i++];
        ++low;
      }
    },

    // This is used for both bf and cid chars.
    mapOne: function(src, dst) {
      this._map[src] = dst;
    },

    lookup: function(code) {
      return this._map[code];
    },

    contains: function(code) {
      return this._map[code] !== undefined;
    },

    forEach: function(callback) {
      // Most maps have fewer than 65536 entries, and for those we use normal
      // array iteration. But really sparse tables are possible -- e.g. with
      // indices in the *billions*. For such tables we use for..in, which isn't
      // ideal because it stringifies the indices for all present elements, but
      // it does avoid iterating over every undefined entry.
      var map = this._map;
      var length = map.length;
      var i;
      if (length <= 0x10000) {
        for (i = 0; i < length; i++) {
          if (map[i] !== undefined) {
            callback(i, map[i]);
          }
        }
      } else {
        for (i in this._map) {
          callback(i, map[i]);
        }
      }
    },

    charCodeOf: function(value) {
      return this._map.indexOf(value);
    },

    getMap: function() {
      return this._map;
    },

    readCharCode: function(str, offset, out) {
      var c = 0;
      var codespaceRanges = this.codespaceRanges;
      var codespaceRangesLen = this.codespaceRanges.length;
      // 9.7.6.2 CMap Mapping
      // The code length is at most 4.
      for (var n = 0; n < codespaceRangesLen; n++) {
        c = ((c << 8) | str.charCodeAt(offset + n)) >>> 0;
        // Check each codespace range to see if it falls within.
        var codespaceRange = codespaceRanges[n];
        for (var k = 0, kk = codespaceRange.length; k < kk;) {
          var low = codespaceRange[k++];
          var high = codespaceRange[k++];
          if (c >= low && c <= high) {
            out.charcode = c;
            out.length = n + 1;
            return;
          }
        }
      }
      out.charcode = 0;
      out.length = 1;
    }
  };
  return CMap;
})();

// A special case of CMap, where the _map array implicitly has a length of
// 65535 and each element is equal to its index.
var IdentityCMap = (function IdentityCMapClosure() {
  function IdentityCMap(vertical, n) {
    CMap.call(this);
    this.vertical = vertical;
    this.addCodespaceRange(n, 0, 0xffff);
  }
  Util.inherit(IdentityCMap, CMap, {});

  IdentityCMap.prototype = {
    addCodespaceRange: CMap.prototype.addCodespaceRange,

    mapCidRange: function(low, high, dstLow) {
      error('should not call mapCidRange');
    },

    mapBfRange: function(low, high, dstLow) {
      error('should not call mapBfRange');
    },

    mapBfRangeToArray: function(low, high, array) {
      error('should not call mapBfRangeToArray');
    },

    mapOne: function(src, dst) {
      error('should not call mapCidOne');
    },

    lookup: function(code) {
      return (isInt(code) && code <= 0xffff) ? code : undefined;
    },

    contains: function(code) {
      return isInt(code) && code <= 0xffff;
    },

    forEach: function(callback) {
      for (var i = 0; i <= 0xffff; i++) {
        callback(i, i);
      }
    },

    charCodeOf: function(value) {
      return (isInt(value) && value <= 0xffff) ? value : -1;
    },

    getMap: function() {
      // Sometimes identity maps must be instantiated, but it's rare.
      var map = new Array(0x10000);
      for (var i = 0; i <= 0xffff; i++) {
        map[i] = i;
      }
      return map;
    },

    readCharCode: CMap.prototype.readCharCode
  };

  return IdentityCMap;
})();

var BinaryCMapReader = (function BinaryCMapReaderClosure() {
  function fetchBinaryData(url) {
    var nonBinaryRequest = PDFJS.disableWorker;
    var request = new XMLHttpRequest();
    request.open('GET', url, false);
    if (!nonBinaryRequest) {
      try {
        request.responseType = 'arraybuffer';
        nonBinaryRequest = request.responseType !== 'arraybuffer';
      } catch (e) {
        nonBinaryRequest = true;
      }
    }
    if (nonBinaryRequest && request.overrideMimeType) {
      request.overrideMimeType('text/plain; charset=x-user-defined');
    }
    request.send(null);
    if (nonBinaryRequest ? !request.responseText : !request.response) {
      error('Unable to get binary cMap at: ' + url);
    }
    if (nonBinaryRequest) {
      var data = Array.prototype.map.call(request.responseText, function (ch) {
        return ch.charCodeAt(0) & 255;
      });
      return new Uint8Array(data);
    }
    return new Uint8Array(request.response);
  }

  function hexToInt(a, size) {
    var n = 0;
    for (var i = 0; i <= size; i++) {
      n = (n << 8) | a[i];
    }
    return n >>> 0;
  }

  function hexToStr(a, size) {
    // This code is hot. Special-case some common values to avoid creating an
    // object with subarray().
    if (size === 1) {
      return String.fromCharCode(a[0], a[1]);
    }
    if (size === 3) {
      return String.fromCharCode(a[0], a[1], a[2], a[3]);
    }
    return String.fromCharCode.apply(null, a.subarray(0, size + 1));
  }

  function addHex(a, b, size) {
    var c = 0;
    for (var i = size; i >= 0; i--) {
      c += a[i] + b[i];
      a[i] = c & 255;
      c >>= 8;
    }
  }

  function incHex(a, size) {
    var c = 1;
    for (var i = size; i >= 0 && c > 0; i--) {
      c += a[i];
      a[i] = c & 255;
      c >>= 8;
    }
  }

  var MAX_NUM_SIZE = 16;
  var MAX_ENCODED_NUM_SIZE = 19; // ceil(MAX_NUM_SIZE * 7 / 8)

  function BinaryCMapStream(data) {
    this.buffer = data;
    this.pos = 0;
    this.end = data.length;
    this.tmpBuf = new Uint8Array(MAX_ENCODED_NUM_SIZE);
  }

  BinaryCMapStream.prototype = {
    readByte: function () {
      if (this.pos >= this.end) {
        return -1;
      }
      return this.buffer[this.pos++];
    },
    readNumber: function () {
      var n = 0;
      var last;
      do {
        var b = this.readByte();
        if (b < 0) {
          error('unexpected EOF in bcmap');
        }
        last = !(b & 0x80);
        n = (n << 7) | (b & 0x7F);
      } while (!last);
      return n;
    },
    readSigned: function () {
      var n = this.readNumber();
      return (n & 1) ? ~(n >>> 1) : n >>> 1;
    },
    readHex: function (num, size) {
      num.set(this.buffer.subarray(this.pos,
        this.pos + size + 1));
      this.pos += size + 1;
    },
    readHexNumber: function (num, size) {
      var last;
      var stack = this.tmpBuf, sp = 0;
      do {
        var b = this.readByte();
        if (b < 0) {
          error('unexpected EOF in bcmap');
        }
        last = !(b & 0x80);
        stack[sp++] = b & 0x7F;
      } while (!last);
      var i = size, buffer = 0, bufferSize = 0;
      while (i >= 0) {
        while (bufferSize < 8 && stack.length > 0) {
          buffer = (stack[--sp] << bufferSize) | buffer;
          bufferSize += 7;
        }
        num[i] = buffer & 255;
        i--;
        buffer >>= 8;
        bufferSize -= 8;
      }
    },
    readHexSigned: function (num, size) {
      this.readHexNumber(num, size);
      var sign = num[size] & 1 ? 255 : 0;
      var c = 0;
      for (var i = 0; i <= size; i++) {
        c = ((c & 1) << 8) | num[i];
        num[i] = (c >> 1) ^ sign;
      }
    },
    readString: function () {
      var len = this.readNumber();
      var s = '';
      for (var i = 0; i < len; i++) {
        s += String.fromCharCode(this.readNumber());
      }
      return s;
    }
  };

  function processBinaryCMap(url, cMap, extend) {
    var data = fetchBinaryData(url);
    var stream = new BinaryCMapStream(data);

    var header = stream.readByte();
    cMap.vertical = !!(header & 1);

    var useCMap = null;
    var start = new Uint8Array(MAX_NUM_SIZE);
    var end = new Uint8Array(MAX_NUM_SIZE);
    var char = new Uint8Array(MAX_NUM_SIZE);
    var charCode = new Uint8Array(MAX_NUM_SIZE);
    var tmp = new Uint8Array(MAX_NUM_SIZE);
    var code;

    var b;
    while ((b = stream.readByte()) >= 0) {
      var type = b >> 5;
      if (type === 7) { // metadata, e.g. comment or usecmap
        switch (b & 0x1F) {
          case 0:
            stream.readString(); // skipping comment
            break;
          case 1:
            useCMap = stream.readString();
            break;
        }
        continue;
      }
      var sequence = !!(b & 0x10);
      var dataSize = b & 15;

      assert(dataSize + 1 <= MAX_NUM_SIZE);

      var ucs2DataSize = 1;
      var subitemsCount = stream.readNumber();
      var i;
      switch (type) {
        case 0: // codespacerange
          stream.readHex(start, dataSize);
          stream.readHexNumber(end, dataSize);
          addHex(end, start, dataSize);
          cMap.addCodespaceRange(dataSize + 1, hexToInt(start, dataSize),
                                 hexToInt(end, dataSize));
          for (i = 1; i < subitemsCount; i++) {
            incHex(end, dataSize);
            stream.readHexNumber(start, dataSize);
            addHex(start, end, dataSize);
            stream.readHexNumber(end, dataSize);
            addHex(end, start, dataSize);
            cMap.addCodespaceRange(dataSize + 1, hexToInt(start, dataSize),
                                   hexToInt(end, dataSize));
          }
          break;
        case 1: // notdefrange
          stream.readHex(start, dataSize);
          stream.readHexNumber(end, dataSize);
          addHex(end, start, dataSize);
          code = stream.readNumber();
          // undefined range, skipping
          for (i = 1; i < subitemsCount; i++) {
            incHex(end, dataSize);
            stream.readHexNumber(start, dataSize);
            addHex(start, end, dataSize);
            stream.readHexNumber(end, dataSize);
            addHex(end, start, dataSize);
            code = stream.readNumber();
            // nop
          }
          break;
        case 2: // cidchar
          stream.readHex(char, dataSize);
          code = stream.readNumber();
          cMap.mapOne(hexToInt(char, dataSize), code);
          for (i = 1; i < subitemsCount; i++) {
            incHex(char, dataSize);
            if (!sequence) {
              stream.readHexNumber(tmp, dataSize);
              addHex(char, tmp, dataSize);
            }
            code = stream.readSigned() + (code + 1);
            cMap.mapOne(hexToInt(char, dataSize), code);
          }
          break;
        case 3: // cidrange
          stream.readHex(start, dataSize);
          stream.readHexNumber(end, dataSize);
          addHex(end, start, dataSize);
          code = stream.readNumber();
          cMap.mapCidRange(hexToInt(start, dataSize), hexToInt(end, dataSize),
                           code);
          for (i = 1; i < subitemsCount; i++) {
            incHex(end, dataSize);
            if (!sequence) {
              stream.readHexNumber(start, dataSize);
              addHex(start, end, dataSize);
            } else {
              start.set(end);
            }
            stream.readHexNumber(end, dataSize);
            addHex(end, start, dataSize);
            code = stream.readNumber();
            cMap.mapCidRange(hexToInt(start, dataSize), hexToInt(end, dataSize),
                             code);
          }
          break;
        case 4: // bfchar
          stream.readHex(char, ucs2DataSize);
          stream.readHex(charCode, dataSize);
          cMap.mapOne(hexToInt(char, ucs2DataSize),
                      hexToStr(charCode, dataSize));
          for (i = 1; i < subitemsCount; i++) {
            incHex(char, ucs2DataSize);
            if (!sequence) {
              stream.readHexNumber(tmp, ucs2DataSize);
              addHex(char, tmp, ucs2DataSize);
            }
            incHex(charCode, dataSize);
            stream.readHexSigned(tmp, dataSize);
            addHex(charCode, tmp, dataSize);
            cMap.mapOne(hexToInt(char, ucs2DataSize),
                        hexToStr(charCode, dataSize));
          }
          break;
        case 5: // bfrange
          stream.readHex(start, ucs2DataSize);
          stream.readHexNumber(end, ucs2DataSize);
          addHex(end, start, ucs2DataSize);
          stream.readHex(charCode, dataSize);
          cMap.mapBfRange(hexToInt(start, ucs2DataSize),
                          hexToInt(end, ucs2DataSize),
                          hexToStr(charCode, dataSize));
          for (i = 1; i < subitemsCount; i++) {
            incHex(end, ucs2DataSize);
            if (!sequence) {
              stream.readHexNumber(start, ucs2DataSize);
              addHex(start, end, ucs2DataSize);
            } else {
              start.set(end);
            }
            stream.readHexNumber(end, ucs2DataSize);
            addHex(end, start, ucs2DataSize);
            stream.readHex(charCode, dataSize);
            cMap.mapBfRange(hexToInt(start, ucs2DataSize),
                            hexToInt(end, ucs2DataSize),
                            hexToStr(charCode, dataSize));
          }
          break;
        default:
          error('Unknown type: ' + type);
          break;
      }
    }

    if (useCMap) {
      extend(useCMap);
    }
    return cMap;
  }

  function BinaryCMapReader() {}

  BinaryCMapReader.prototype = {
    read: processBinaryCMap
  };

  return BinaryCMapReader;
})();

var CMapFactory = (function CMapFactoryClosure() {
  function strToInt(str) {
    var a = 0;
    for (var i = 0; i < str.length; i++) {
      a = (a << 8) | str.charCodeAt(i);
    }
    return a >>> 0;
  }

  function expectString(obj) {
    if (!isString(obj)) {
      error('Malformed CMap: expected string.');
    }
  }

  function expectInt(obj) {
    if (!isInt(obj)) {
      error('Malformed CMap: expected int.');
    }
  }

  function parseBfChar(cMap, lexer) {
    while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      }
      if (isCmd(obj, 'endbfchar')) {
        return;
      }
      expectString(obj);
      var src = strToInt(obj);
      obj = lexer.getObj();
      // TODO are /dstName used?
      expectString(obj);
      var dst = obj;
      cMap.mapOne(src, dst);
    }
  }

  function parseBfRange(cMap, lexer) {
    while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      }
      if (isCmd(obj, 'endbfrange')) {
        return;
      }
      expectString(obj);
      var low = strToInt(obj);
      obj = lexer.getObj();
      expectString(obj);
      var high = strToInt(obj);
      obj = lexer.getObj();
      if (isInt(obj) || isString(obj)) {
        var dstLow = isInt(obj) ? String.fromCharCode(obj) : obj;
        cMap.mapBfRange(low, high, dstLow);
      } else if (isCmd(obj, '[')) {
        obj = lexer.getObj();
        var array = [];
        while (!isCmd(obj, ']') && !isEOF(obj)) {
          array.push(obj);
          obj = lexer.getObj();
        }
        cMap.mapBfRangeToArray(low, high, array);
      } else {
        break;
      }
    }
    error('Invalid bf range.');
  }

  function parseCidChar(cMap, lexer) {
    while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      }
      if (isCmd(obj, 'endcidchar')) {
        return;
      }
      expectString(obj);
      var src = strToInt(obj);
      obj = lexer.getObj();
      expectInt(obj);
      var dst = obj;
      cMap.mapOne(src, dst);
    }
  }

  function parseCidRange(cMap, lexer) {
    while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      }
      if (isCmd(obj, 'endcidrange')) {
        return;
      }
      expectString(obj);
      var low = strToInt(obj);
      obj = lexer.getObj();
      expectString(obj);
      var high = strToInt(obj);
      obj = lexer.getObj();
      expectInt(obj);
      var dstLow = obj;
      cMap.mapCidRange(low, high, dstLow);
    }
  }

  function parseCodespaceRange(cMap, lexer) {
    while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      }
      if (isCmd(obj, 'endcodespacerange')) {
        return;
      }
      if (!isString(obj)) {
        break;
      }
      var low = strToInt(obj);
      obj = lexer.getObj();
      if (!isString(obj)) {
        break;
      }
      var high = strToInt(obj);
      cMap.addCodespaceRange(obj.length, low, high);
    }
    error('Invalid codespace range.');
  }

  function parseWMode(cMap, lexer) {
    var obj = lexer.getObj();
    if (isInt(obj)) {
      cMap.vertical = !!obj;
    }
  }

  function parseCMap(cMap, lexer, builtInCMapParams, useCMap) {
    var previous;
    var embededUseCMap;
    objLoop: while (true) {
      var obj = lexer.getObj();
      if (isEOF(obj)) {
        break;
      } else if (isName(obj)) {
        if (obj.name === 'WMode') {
          parseWMode(cMap, lexer);
        }
        previous = obj;
      } else if (isCmd(obj)) {
        switch (obj.cmd) {
          case 'endcmap':
            break objLoop;
          case 'usecmap':
            if (isName(previous)) {
              embededUseCMap = previous.name;
            }
            break;
          case 'begincodespacerange':
            parseCodespaceRange(cMap, lexer);
            break;
          case 'beginbfchar':
            parseBfChar(cMap, lexer);
            break;
          case 'begincidchar':
            parseCidChar(cMap, lexer);
            break;
          case 'beginbfrange':
            parseBfRange(cMap, lexer);
            break;
          case 'begincidrange':
            parseCidRange(cMap, lexer);
            break;
        }
      }
    }

    if (!useCMap && embededUseCMap) {
      // Load the usecmap definition from the file only if there wasn't one
      // specified.
      useCMap = embededUseCMap;
    }
    if (useCMap) {
      extendCMap(cMap, builtInCMapParams, useCMap);
    }
  }

  function extendCMap(cMap, builtInCMapParams, useCMap) {
    cMap.useCMap = createBuiltInCMap(useCMap, builtInCMapParams);
    // If there aren't any code space ranges defined clone all the parent ones
    // into this cMap.
    if (cMap.numCodespaceRanges === 0) {
      var useCodespaceRanges = cMap.useCMap.codespaceRanges;
      for (var i = 0; i < useCodespaceRanges.length; i++) {
        cMap.codespaceRanges[i] = useCodespaceRanges[i].slice();
      }
      cMap.numCodespaceRanges = cMap.useCMap.numCodespaceRanges;
    }
    // Merge the map into the current one, making sure not to override
    // any previously defined entries.
    cMap.useCMap.forEach(function(key, value) {
      if (!cMap.contains(key)) {
        cMap.mapOne(key, cMap.useCMap.lookup(key));
      }
    });
  }

  function parseBinaryCMap(name, builtInCMapParams) {
    var url = builtInCMapParams.url + name + '.bcmap';
    var cMap = new CMap(true);
    new BinaryCMapReader().read(url, cMap, function (useCMap) {
      extendCMap(cMap, builtInCMapParams, useCMap);
    });
    return cMap;
  }

  function createBuiltInCMap(name, builtInCMapParams) {
    if (name === 'Identity-H') {
      return new IdentityCMap(false, 2);
    } else if (name === 'Identity-V') {
      return new IdentityCMap(true, 2);
    }
    if (BUILT_IN_CMAPS.indexOf(name) === -1) {
      error('Unknown cMap name: ' + name);
    }
    assert(builtInCMapParams, 'built-in cMap parameters are not provided');

    if (builtInCMapParams.packed) {
      return parseBinaryCMap(name, builtInCMapParams);
    }

    var request = new XMLHttpRequest();
    var url = builtInCMapParams.url + name;
    request.open('GET', url, false);
    request.send(null);
    if (!request.responseText) {
      error('Unable to get cMap at: ' + url);
    }
    var cMap = new CMap(true);
    var lexer = new Lexer(new StringStream(request.responseText));
    parseCMap(cMap, lexer, builtInCMapParams, null);
    return cMap;
  }

  return {
    create: function (encoding, builtInCMapParams, useCMap) {
      if (isName(encoding)) {
        return createBuiltInCMap(encoding.name, builtInCMapParams);
      } else if (isStream(encoding)) {
        var cMap = new CMap();
        var lexer = new Lexer(encoding);
        try {
          parseCMap(cMap, lexer, builtInCMapParams, useCMap);
        } catch (e) {
          warn('Invalid CMap data. ' + e);
        }
        return cMap;
      }
      error('Encoding required.');
    }
  };
})();
