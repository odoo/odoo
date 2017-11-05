/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */

/* Copyright 2014 Opera Software ASA
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
 *
 *
 * Based on https://code.google.com/p/smhasher/wiki/MurmurHash3.
 * Hashes roughly 100 KB per millisecond on i7 3.4 GHz.
 */
/* globals Uint32ArrayView */

'use strict';

var MurmurHash3_64 = (function MurmurHash3_64Closure (seed) {
  // Workaround for missing math precison in JS.
  var MASK_HIGH = 0xffff0000;
  var MASK_LOW = 0xffff;

  function MurmurHash3_64 (seed) {
    var SEED = 0xc3d2e1f0;
    this.h1 = seed ? seed & 0xffffffff : SEED;
    this.h2 = seed ? seed & 0xffffffff : SEED;
  }

  var alwaysUseUint32ArrayView = false;
//#if !(FIREFOX || MOZCENTRAL || B2G || CHROME)
  // old webkits have issues with non-aligned arrays
  try {
    new Uint32Array(new Uint8Array(5).buffer, 0, 1);
  } catch (e) {
    alwaysUseUint32ArrayView = true;
  }
//#endif

  MurmurHash3_64.prototype = {
    update: function MurmurHash3_64_update(input) {
      var useUint32ArrayView = alwaysUseUint32ArrayView;
      var i;
      if (typeof input === 'string') {
        var data = new Uint8Array(input.length * 2);
        var length = 0;
        for (i = 0; i < input.length; i++) {
          var code = input.charCodeAt(i);
          if (code <= 0xff) {
            data[length++] = code;
          }
          else {
            data[length++] = code >>> 8;
            data[length++] = code & 0xff;
          }
        }
      } else if (input instanceof Uint8Array) {
        data = input;
        length = data.length;
      } else if (typeof input === 'object' && ('length' in input)) {
        // processing regular arrays as well, e.g. for IE9
        data = input;
        length = data.length;
        useUint32ArrayView = true;
      } else {
        throw new Error('Wrong data format in MurmurHash3_64_update. ' +
                        'Input must be a string or array.');
      }

      var blockCounts = length >> 2;
      var tailLength = length - blockCounts * 4;
      // we don't care about endianness here
      var dataUint32 = useUint32ArrayView ?
        new Uint32ArrayView(data, blockCounts) :
        new Uint32Array(data.buffer, 0, blockCounts);
      var k1 = 0;
      var k2 = 0;
      var h1 = this.h1;
      var h2 = this.h2;
      var C1 = 0xcc9e2d51;
      var C2 = 0x1b873593;
      var C1_LOW = C1 & MASK_LOW;
      var C2_LOW = C2 & MASK_LOW;

      for (i = 0; i < blockCounts; i++) {
        if (i & 1) {
          k1 = dataUint32[i];
          k1 = (k1 * C1 & MASK_HIGH) | (k1 * C1_LOW & MASK_LOW);
          k1 = k1 << 15 | k1 >>> 17;
          k1 = (k1 * C2 & MASK_HIGH) | (k1 * C2_LOW & MASK_LOW);
          h1 ^= k1;
          h1 = h1 << 13 | h1 >>> 19;
          h1 = h1 * 5 + 0xe6546b64;
        } else {
          k2 = dataUint32[i];
          k2 = (k2 * C1 & MASK_HIGH) | (k2 * C1_LOW & MASK_LOW);
          k2 = k2 << 15 | k2 >>> 17;
          k2 = (k2 * C2 & MASK_HIGH) | (k2 * C2_LOW & MASK_LOW);
          h2 ^= k2;
          h2 = h2 << 13 | h2 >>> 19;
          h2 = h2 * 5 + 0xe6546b64;
        }
      }

      k1 = 0;

      switch (tailLength) {
        case 3:
          k1 ^= data[blockCounts * 4 + 2] << 16;
          /* falls through */
        case 2:
          k1 ^= data[blockCounts * 4 + 1] << 8;
          /* falls through */
        case 1:
          k1 ^= data[blockCounts * 4];
          /* falls through */
        k1 = (k1 * C1 & MASK_HIGH) | (k1 * C1_LOW & MASK_LOW);
        k1 = k1 << 15 | k1 >>> 17;
        k1 = (k1 * C2 & MASK_HIGH) | (k1 * C2_LOW & MASK_LOW);
        if (blockCounts & 1) {
          h1 ^= k1;
        } else {
          h2 ^= k1;
        }
      }

      this.h1 = h1;
      this.h2 = h2;
      return this;
    },

    hexdigest: function MurmurHash3_64_hexdigest () {
      var h1 = this.h1;
      var h2 = this.h2;

      h1 ^= h2 >>> 1;
      h1 = (h1 * 0xed558ccd & MASK_HIGH) | (h1 * 0x8ccd & MASK_LOW);
      h2 = (h2 * 0xff51afd7 & MASK_HIGH) |
           (((h2 << 16 | h1 >>> 16) * 0xafd7ed55 & MASK_HIGH) >>> 16);
      h1 ^= h2 >>> 1;
      h1 = (h1 * 0x1a85ec53 & MASK_HIGH) | (h1 * 0xec53 & MASK_LOW);
      h2 = (h2 * 0xc4ceb9fe & MASK_HIGH) |
           (((h2 << 16 | h1 >>> 16) * 0xb9fe1a85 & MASK_HIGH) >>> 16);
      h1 ^= h2 >>> 1;

      for (var i = 0, arr = [h1, h2], str = ''; i < arr.length; i++) {
        var hex = (arr[i] >>> 0).toString(16);
        while (hex.length < 8) {
          hex = '0' + hex;
        }
        str += hex;
      }

      return str;
    }
  };

  return MurmurHash3_64;
})();
