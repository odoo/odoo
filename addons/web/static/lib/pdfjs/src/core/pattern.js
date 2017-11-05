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
/* globals ColorSpace, PDFFunction, Util, error, warn, info, isArray, isStream,
           assert, isPDFFunction, UnsupportedManager, UNSUPPORTED_FEATURES,
           MissingDataException */

'use strict';

var PatternType = {
  FUNCTION_BASED: 1,
  AXIAL: 2,
  RADIAL: 3,
  FREE_FORM_MESH: 4,
  LATTICE_FORM_MESH: 5,
  COONS_PATCH_MESH: 6,
  TENSOR_PATCH_MESH: 7
};

var Pattern = (function PatternClosure() {
  // Constructor should define this.getPattern
  function Pattern() {
    error('should not call Pattern constructor');
  }

  Pattern.prototype = {
    // Input: current Canvas context
    // Output: the appropriate fillStyle or strokeStyle
    getPattern: function Pattern_getPattern(ctx) {
      error('Should not call Pattern.getStyle: ' + ctx);
    }
  };

  Pattern.parseShading = function Pattern_parseShading(shading, matrix, xref,
                                                       res) {

    var dict = isStream(shading) ? shading.dict : shading;
    var type = dict.get('ShadingType');

    try {
      switch (type) {
        case PatternType.AXIAL:
        case PatternType.RADIAL:
          // Both radial and axial shadings are handled by RadialAxial shading.
          return new Shadings.RadialAxial(dict, matrix, xref, res);
        case PatternType.FREE_FORM_MESH:
        case PatternType.LATTICE_FORM_MESH:
        case PatternType.COONS_PATCH_MESH:
        case PatternType.TENSOR_PATCH_MESH:
          return new Shadings.Mesh(shading, matrix, xref, res);
        default:
          throw new Error('Unknown PatternType: ' + type);
      }
    } catch (ex) {
      if (ex instanceof MissingDataException) {
        throw ex;
      }
      UnsupportedManager.notify(UNSUPPORTED_FEATURES.shadingPattern);
      warn(ex);
      return new Shadings.Dummy();
    }
  };
  return Pattern;
})();

var Shadings = {};

// A small number to offset the first/last color stops so we can insert ones to
// support extend.  Number.MIN_VALUE appears to be too small and breaks the
// extend. 1e-7 works in FF but chrome seems to use an even smaller sized number
// internally so we have to go bigger.
Shadings.SMALL_NUMBER = 1e-2;

// Radial and axial shading have very similar implementations
// If needed, the implementations can be broken into two classes
Shadings.RadialAxial = (function RadialAxialClosure() {
  function RadialAxial(dict, matrix, xref, res) {
    this.matrix = matrix;
    this.coordsArr = dict.get('Coords');
    this.shadingType = dict.get('ShadingType');
    this.type = 'Pattern';
    var cs = dict.get('ColorSpace', 'CS');
    cs = ColorSpace.parse(cs, xref, res);
    this.cs = cs;

    var t0 = 0.0, t1 = 1.0;
    if (dict.has('Domain')) {
      var domainArr = dict.get('Domain');
      t0 = domainArr[0];
      t1 = domainArr[1];
    }

    var extendStart = false, extendEnd = false;
    if (dict.has('Extend')) {
      var extendArr = dict.get('Extend');
      extendStart = extendArr[0];
      extendEnd = extendArr[1];
    }

    if (this.shadingType === PatternType.RADIAL &&
       (!extendStart || !extendEnd)) {
      // Radial gradient only currently works if either circle is fully within
      // the other circle.
      var x1 = this.coordsArr[0];
      var y1 = this.coordsArr[1];
      var r1 = this.coordsArr[2];
      var x2 = this.coordsArr[3];
      var y2 = this.coordsArr[4];
      var r2 = this.coordsArr[5];
      var distance = Math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
      if (r1 <= r2 + distance &&
          r2 <= r1 + distance) {
        warn('Unsupported radial gradient.');
      }
    }

    this.extendStart = extendStart;
    this.extendEnd = extendEnd;

    var fnObj = dict.get('Function');
    var fn = PDFFunction.parseArray(xref, fnObj);

    // 10 samples seems good enough for now, but probably won't work
    // if there are sharp color changes. Ideally, we would implement
    // the spec faithfully and add lossless optimizations.
    var diff = t1 - t0;
    var step = diff / 10;

    var colorStops = this.colorStops = [];

    // Protect against bad domains so we don't end up in an infinte loop below.
    if (t0 >= t1 || step <= 0) {
      // Acrobat doesn't seem to handle these cases so we'll ignore for
      // now.
      info('Bad shading domain.');
      return;
    }

    var color = new Float32Array(cs.numComps), ratio = new Float32Array(1);
    var rgbColor;
    for (var i = t0; i <= t1; i += step) {
      ratio[0] = i;
      fn(ratio, 0, color, 0);
      rgbColor = cs.getRgb(color, 0);
      var cssColor = Util.makeCssRgb(rgbColor[0], rgbColor[1], rgbColor[2]);
      colorStops.push([(i - t0) / diff, cssColor]);
    }

    var background = 'transparent';
    if (dict.has('Background')) {
      rgbColor = cs.getRgb(dict.get('Background'), 0);
      background = Util.makeCssRgb(rgbColor[0], rgbColor[1], rgbColor[2]);
    }

    if (!extendStart) {
      // Insert a color stop at the front and offset the first real color stop
      // so it doesn't conflict with the one we insert.
      colorStops.unshift([0, background]);
      colorStops[1][0] += Shadings.SMALL_NUMBER;
    }
    if (!extendEnd) {
      // Same idea as above in extendStart but for the end.
      colorStops[colorStops.length - 1][0] -= Shadings.SMALL_NUMBER;
      colorStops.push([1, background]);
    }

    this.colorStops = colorStops;
  }

  RadialAxial.prototype = {
    getIR: function RadialAxial_getIR() {
      var coordsArr = this.coordsArr;
      var shadingType = this.shadingType;
      var type, p0, p1, r0, r1;
      if (shadingType === PatternType.AXIAL) {
        p0 = [coordsArr[0], coordsArr[1]];
        p1 = [coordsArr[2], coordsArr[3]];
        r0 = null;
        r1 = null;
        type = 'axial';
      } else if (shadingType === PatternType.RADIAL) {
        p0 = [coordsArr[0], coordsArr[1]];
        p1 = [coordsArr[3], coordsArr[4]];
        r0 = coordsArr[2];
        r1 = coordsArr[5];
        type = 'radial';
      } else {
        error('getPattern type unknown: ' + shadingType);
      }

      var matrix = this.matrix;
      if (matrix) {
        p0 = Util.applyTransform(p0, matrix);
        p1 = Util.applyTransform(p1, matrix);
      }

      return ['RadialAxial', type, this.colorStops, p0, p1, r0, r1];
    }
  };

  return RadialAxial;
})();

// All mesh shading. For now, they will be presented as set of the triangles
// to be drawn on the canvas and rgb color for each vertex.
Shadings.Mesh = (function MeshClosure() {
  function MeshStreamReader(stream, context) {
    this.stream = stream;
    this.context = context;
    this.buffer = 0;
    this.bufferLength = 0;

    var numComps = context.numComps;
    this.tmpCompsBuf = new Float32Array(numComps);
    var csNumComps = context.colorSpace;
    this.tmpCsCompsBuf = context.colorFn ? new Float32Array(csNumComps) :
                                           this.tmpCompsBuf;
  }
  MeshStreamReader.prototype = {
    get hasData() {
      if (this.stream.end) {
        return this.stream.pos < this.stream.end;
      }
      if (this.bufferLength > 0) {
        return true;
      }
      var nextByte = this.stream.getByte();
      if (nextByte < 0) {
        return false;
      }
      this.buffer = nextByte;
      this.bufferLength = 8;
      return true;
    },
    readBits: function MeshStreamReader_readBits(n) {
      var buffer = this.buffer;
      var bufferLength = this.bufferLength;
      if (n === 32) {
        if (bufferLength === 0) {
          return ((this.stream.getByte() << 24) |
            (this.stream.getByte() << 16) | (this.stream.getByte() << 8) |
            this.stream.getByte()) >>> 0;
        }
        buffer = (buffer << 24) | (this.stream.getByte() << 16) |
          (this.stream.getByte() << 8) | this.stream.getByte();
        var nextByte = this.stream.getByte();
        this.buffer = nextByte & ((1 << bufferLength) - 1);
        return ((buffer << (8 - bufferLength)) |
          ((nextByte & 0xFF) >> bufferLength)) >>> 0;
      }
      if (n === 8 && bufferLength === 0) {
        return this.stream.getByte();
      }
      while (bufferLength < n) {
        buffer = (buffer << 8) | this.stream.getByte();
        bufferLength += 8;
      }
      bufferLength -= n;
      this.bufferLength = bufferLength;
      this.buffer = buffer & ((1 << bufferLength) - 1);
      return buffer >> bufferLength;
    },
    align: function MeshStreamReader_align() {
      this.buffer = 0;
      this.bufferLength = 0;
    },
    readFlag: function MeshStreamReader_readFlag() {
      return this.readBits(this.context.bitsPerFlag);
    },
    readCoordinate: function MeshStreamReader_readCoordinate() {
      var bitsPerCoordinate = this.context.bitsPerCoordinate;
      var xi = this.readBits(bitsPerCoordinate);
      var yi = this.readBits(bitsPerCoordinate);
      var decode = this.context.decode;
      var scale = bitsPerCoordinate < 32 ? 1 / ((1 << bitsPerCoordinate) - 1) :
        2.3283064365386963e-10; // 2 ^ -32
      return [
        xi * scale * (decode[1] - decode[0]) + decode[0],
        yi * scale * (decode[3] - decode[2]) + decode[2]
      ];
    },
    readComponents: function MeshStreamReader_readComponents() {
      var numComps = this.context.numComps;
      var bitsPerComponent = this.context.bitsPerComponent;
      var scale = bitsPerComponent < 32 ? 1 / ((1 << bitsPerComponent) - 1) :
        2.3283064365386963e-10; // 2 ^ -32
      var decode = this.context.decode;
      var components = this.tmpCompsBuf;
      for (var i = 0, j = 4; i < numComps; i++, j += 2) {
        var ci = this.readBits(bitsPerComponent);
        components[i] = ci * scale * (decode[j + 1] - decode[j]) + decode[j];
      }
      var color = this.tmpCsCompsBuf;
      if (this.context.colorFn) {
        this.context.colorFn(components, 0, color, 0);
      }
      return this.context.colorSpace.getRgb(color, 0);
    }
  };

  function decodeType4Shading(mesh, reader) {
    var coords = mesh.coords;
    var colors = mesh.colors;
    var operators = [];
    var ps = []; // not maintaining cs since that will match ps
    var verticesLeft = 0; // assuming we have all data to start a new triangle
    while (reader.hasData) {
      var f = reader.readFlag();
      var coord = reader.readCoordinate();
      var color = reader.readComponents();
      if (verticesLeft === 0) { // ignoring flags if we started a triangle
        assert(0 <= f && f <= 2, 'Unknown type4 flag');
        switch (f) {
          case 0:
            verticesLeft = 3;
            break;
          case 1:
            ps.push(ps[ps.length - 2], ps[ps.length - 1]);
            verticesLeft = 1;
            break;
          case 2:
            ps.push(ps[ps.length - 3], ps[ps.length - 1]);
            verticesLeft = 1;
            break;
        }
        operators.push(f);
      }
      ps.push(coords.length);
      coords.push(coord);
      colors.push(color);
      verticesLeft--;

      reader.align();
    }

    var psPacked = new Int32Array(ps);

    mesh.figures.push({
      type: 'triangles',
      coords: psPacked,
      colors: psPacked
    });
  }

  function decodeType5Shading(mesh, reader, verticesPerRow) {
    var coords = mesh.coords;
    var colors = mesh.colors;
    var ps = []; // not maintaining cs since that will match ps
    while (reader.hasData) {
      var coord = reader.readCoordinate();
      var color = reader.readComponents();
      ps.push(coords.length);
      coords.push(coord);
      colors.push(color);
    }

    var psPacked = new Int32Array(ps);

    mesh.figures.push({
      type: 'lattice',
      coords: psPacked,
      colors: psPacked,
      verticesPerRow: verticesPerRow
    });
  }

  var MIN_SPLIT_PATCH_CHUNKS_AMOUNT = 3;
  var MAX_SPLIT_PATCH_CHUNKS_AMOUNT = 20;

  var TRIANGLE_DENSITY = 20; // count of triangles per entire mesh bounds

  var getB = (function getBClosure() {
    function buildB(count) {
      var lut = [];
      for (var i = 0; i <= count; i++) {
        var t = i / count, t_ = 1 - t;
        lut.push(new Float32Array([t_ * t_ * t_, 3 * t * t_ * t_,
          3 * t * t * t_, t * t * t]));
      }
      return lut;
    }
    var cache = [];
    return function getB(count) {
      if (!cache[count]) {
        cache[count] = buildB(count);
      }
      return cache[count];
    };
  })();

  function buildFigureFromPatch(mesh, index) {
    var figure = mesh.figures[index];
    assert(figure.type === 'patch', 'Unexpected patch mesh figure');

    var coords = mesh.coords, colors = mesh.colors;
    var pi = figure.coords;
    var ci = figure.colors;

    var figureMinX = Math.min(coords[pi[0]][0], coords[pi[3]][0],
                              coords[pi[12]][0], coords[pi[15]][0]);
    var figureMinY = Math.min(coords[pi[0]][1], coords[pi[3]][1],
                              coords[pi[12]][1], coords[pi[15]][1]);
    var figureMaxX = Math.max(coords[pi[0]][0], coords[pi[3]][0],
                              coords[pi[12]][0], coords[pi[15]][0]);
    var figureMaxY = Math.max(coords[pi[0]][1], coords[pi[3]][1],
                              coords[pi[12]][1], coords[pi[15]][1]);
    var splitXBy = Math.ceil((figureMaxX - figureMinX) * TRIANGLE_DENSITY /
                             (mesh.bounds[2] - mesh.bounds[0]));
    splitXBy = Math.max(MIN_SPLIT_PATCH_CHUNKS_AMOUNT,
               Math.min(MAX_SPLIT_PATCH_CHUNKS_AMOUNT, splitXBy));
    var splitYBy = Math.ceil((figureMaxY - figureMinY) * TRIANGLE_DENSITY /
                             (mesh.bounds[3] - mesh.bounds[1]));
    splitYBy = Math.max(MIN_SPLIT_PATCH_CHUNKS_AMOUNT,
               Math.min(MAX_SPLIT_PATCH_CHUNKS_AMOUNT, splitYBy));

    var verticesPerRow = splitXBy + 1;
    var figureCoords = new Int32Array((splitYBy + 1) * verticesPerRow);
    var figureColors = new Int32Array((splitYBy + 1) * verticesPerRow);
    var k = 0;
    var cl = new Uint8Array(3), cr = new Uint8Array(3);
    var c0 = colors[ci[0]], c1 = colors[ci[1]],
      c2 = colors[ci[2]], c3 = colors[ci[3]];
    var bRow = getB(splitYBy), bCol = getB(splitXBy);
    for (var row = 0; row <= splitYBy; row++) {
      cl[0] = ((c0[0] * (splitYBy - row) + c2[0] * row) / splitYBy) | 0;
      cl[1] = ((c0[1] * (splitYBy - row) + c2[1] * row) / splitYBy) | 0;
      cl[2] = ((c0[2] * (splitYBy - row) + c2[2] * row) / splitYBy) | 0;

      cr[0] = ((c1[0] * (splitYBy - row) + c3[0] * row) / splitYBy) | 0;
      cr[1] = ((c1[1] * (splitYBy - row) + c3[1] * row) / splitYBy) | 0;
      cr[2] = ((c1[2] * (splitYBy - row) + c3[2] * row) / splitYBy) | 0;

      for (var col = 0; col <= splitXBy; col++, k++) {
        if ((row === 0 || row === splitYBy) &&
            (col === 0 || col === splitXBy)) {
          continue;
        }
        var x = 0, y = 0;
        var q = 0;
        for (var i = 0; i <= 3; i++) {
          for (var j = 0; j <= 3; j++, q++) {
            var m = bRow[row][i] * bCol[col][j];
            x += coords[pi[q]][0] * m;
            y += coords[pi[q]][1] * m;
          }
        }
        figureCoords[k] = coords.length;
        coords.push([x, y]);
        figureColors[k] = colors.length;
        var newColor = new Uint8Array(3);
        newColor[0] = ((cl[0] * (splitXBy - col) + cr[0] * col) / splitXBy) | 0;
        newColor[1] = ((cl[1] * (splitXBy - col) + cr[1] * col) / splitXBy) | 0;
        newColor[2] = ((cl[2] * (splitXBy - col) + cr[2] * col) / splitXBy) | 0;
        colors.push(newColor);
      }
    }
    figureCoords[0] = pi[0];
    figureColors[0] = ci[0];
    figureCoords[splitXBy] = pi[3];
    figureColors[splitXBy] = ci[1];
    figureCoords[verticesPerRow * splitYBy] = pi[12];
    figureColors[verticesPerRow * splitYBy] = ci[2];
    figureCoords[verticesPerRow * splitYBy + splitXBy] = pi[15];
    figureColors[verticesPerRow * splitYBy + splitXBy] = ci[3];

    mesh.figures[index] = {
      type: 'lattice',
      coords: figureCoords,
      colors: figureColors,
      verticesPerRow: verticesPerRow
    };
  }

  function decodeType6Shading(mesh, reader) {
    // A special case of Type 7. The p11, p12, p21, p22 automatically filled
    var coords = mesh.coords;
    var colors = mesh.colors;
    var ps = new Int32Array(16); // p00, p10, ..., p30, p01, ..., p33
    var cs = new Int32Array(4); // c00, c30, c03, c33
    while (reader.hasData) {
      var f = reader.readFlag();
      assert(0 <= f && f <= 3, 'Unknown type6 flag');
      var i, ii;
      var pi = coords.length;
      for (i = 0, ii = (f !== 0 ? 8 : 12); i < ii; i++) {
        coords.push(reader.readCoordinate());
      }
      var ci = colors.length;
      for (i = 0, ii = (f !== 0 ? 2 : 4); i < ii; i++) {
        colors.push(reader.readComponents());
      }
      var tmp1, tmp2, tmp3, tmp4;
      switch (f) {
        case 0:
          ps[12] = pi + 3; ps[13] = pi + 4;  ps[14] = pi + 5;  ps[15] = pi + 6;
          ps[ 8] = pi + 2; /* values for 5, 6, 9, 10 are    */ ps[11] = pi + 7;
          ps[ 4] = pi + 1; /* calculated below              */ ps[ 7] = pi + 8;
          ps[ 0] = pi;     ps[ 1] = pi + 11; ps[ 2] = pi + 10; ps[ 3] = pi + 9;
          cs[2] = ci + 1; cs[3] = ci + 2;
          cs[0] = ci;     cs[1] = ci + 3;
          break;
        case 1:
          tmp1 = ps[12]; tmp2 = ps[13]; tmp3 = ps[14]; tmp4 = ps[15];
          ps[12] = pi + 5; ps[13] = pi + 4;  ps[14] = pi + 3;  ps[15] = pi + 2;
          ps[ 8] = pi + 6; /* values for 5, 6, 9, 10 are    */ ps[11] = pi + 1;
          ps[ 4] = pi + 7; /* calculated below              */ ps[ 7] = pi;
          ps[ 0] = tmp1;   ps[ 1] = tmp2;    ps[ 2] = tmp3;    ps[ 3] = tmp4;
          tmp1 = cs[2]; tmp2 = cs[3];
          cs[2] = ci + 1; cs[3] = ci;
          cs[0] = tmp1;   cs[1] = tmp2;
          break;
        case 2:
          ps[12] = ps[15]; ps[13] = pi + 7; ps[14] = pi + 6;   ps[15] = pi + 5;
          ps[ 8] = ps[11]; /* values for 5, 6, 9, 10 are    */ ps[11] = pi + 4;
          ps[ 4] = ps[7];  /* calculated below              */ ps[ 7] = pi + 3;
          ps[ 0] = ps[3];  ps[ 1] = pi;     ps[ 2] = pi + 1;   ps[ 3] = pi + 2;
          cs[2] = cs[3]; cs[3] = ci + 1;
          cs[0] = cs[1]; cs[1] = ci;
          break;
        case 3:
          ps[12] = ps[0];  ps[13] = ps[1];   ps[14] = ps[2];   ps[15] = ps[3];
          ps[ 8] = pi;     /* values for 5, 6, 9, 10 are    */ ps[11] = pi + 7;
          ps[ 4] = pi + 1; /* calculated below              */ ps[ 7] = pi + 6;
          ps[ 0] = pi + 2; ps[ 1] = pi + 3;  ps[ 2] = pi + 4;  ps[ 3] = pi + 5;
          cs[2] = cs[0]; cs[3] = cs[1];
          cs[0] = ci;    cs[1] = ci + 1;
          break;
      }
      // set p11, p12, p21, p22
      ps[5] = coords.length;
      coords.push([
        (-4 * coords[ps[0]][0] - coords[ps[15]][0] +
          6 * (coords[ps[4]][0] + coords[ps[1]][0]) -
          2 * (coords[ps[12]][0] + coords[ps[3]][0]) +
          3 * (coords[ps[13]][0] + coords[ps[7]][0])) / 9,
        (-4 * coords[ps[0]][1] - coords[ps[15]][1] +
          6 * (coords[ps[4]][1] + coords[ps[1]][1]) -
          2 * (coords[ps[12]][1] + coords[ps[3]][1]) +
          3 * (coords[ps[13]][1] + coords[ps[7]][1])) / 9
      ]);
      ps[6] = coords.length;
      coords.push([
        (-4 * coords[ps[3]][0] - coords[ps[12]][0] +
          6 * (coords[ps[2]][0] + coords[ps[7]][0]) -
          2 * (coords[ps[0]][0] + coords[ps[15]][0]) +
          3 * (coords[ps[4]][0] + coords[ps[14]][0])) / 9,
        (-4 * coords[ps[3]][1] - coords[ps[12]][1] +
          6 * (coords[ps[2]][1] + coords[ps[7]][1]) -
          2 * (coords[ps[0]][1] + coords[ps[15]][1]) +
          3 * (coords[ps[4]][1] + coords[ps[14]][1])) / 9
      ]);
      ps[9] = coords.length;
      coords.push([
        (-4 * coords[ps[12]][0] - coords[ps[3]][0] +
          6 * (coords[ps[8]][0] + coords[ps[13]][0]) -
          2 * (coords[ps[0]][0] + coords[ps[15]][0]) +
          3 * (coords[ps[11]][0] + coords[ps[1]][0])) / 9,
        (-4 * coords[ps[12]][1] - coords[ps[3]][1] +
          6 * (coords[ps[8]][1] + coords[ps[13]][1]) -
          2 * (coords[ps[0]][1] + coords[ps[15]][1]) +
          3 * (coords[ps[11]][1] + coords[ps[1]][1])) / 9
      ]);
      ps[10] = coords.length;
      coords.push([
        (-4 * coords[ps[15]][0] - coords[ps[0]][0] +
          6 * (coords[ps[11]][0] + coords[ps[14]][0]) -
          2 * (coords[ps[12]][0] + coords[ps[3]][0]) +
          3 * (coords[ps[2]][0] + coords[ps[8]][0])) / 9,
        (-4 * coords[ps[15]][1] - coords[ps[0]][1] +
          6 * (coords[ps[11]][1] + coords[ps[14]][1]) -
          2 * (coords[ps[12]][1] + coords[ps[3]][1]) +
          3 * (coords[ps[2]][1] + coords[ps[8]][1])) / 9
      ]);
      mesh.figures.push({
        type: 'patch',
        coords: new Int32Array(ps), // making copies of ps and cs
        colors: new Int32Array(cs)
      });
    }
  }

  function decodeType7Shading(mesh, reader) {
    var coords = mesh.coords;
    var colors = mesh.colors;
    var ps = new Int32Array(16); // p00, p10, ..., p30, p01, ..., p33
    var cs = new Int32Array(4); // c00, c30, c03, c33
    while (reader.hasData) {
      var f = reader.readFlag();
      assert(0 <= f && f <= 3, 'Unknown type7 flag');
      var i, ii;
      var pi = coords.length;
      for (i = 0, ii = (f !== 0 ? 12 : 16); i < ii; i++) {
        coords.push(reader.readCoordinate());
      }
      var ci = colors.length;
      for (i = 0, ii = (f !== 0 ? 2 : 4); i < ii; i++) {
        colors.push(reader.readComponents());
      }
      var tmp1, tmp2, tmp3, tmp4;
      switch (f) {
        case 0:
          ps[12] = pi + 3; ps[13] = pi + 4;  ps[14] = pi + 5;  ps[15] = pi + 6;
          ps[ 8] = pi + 2; ps[ 9] = pi + 13; ps[10] = pi + 14; ps[11] = pi + 7;
          ps[ 4] = pi + 1; ps[ 5] = pi + 12; ps[ 6] = pi + 15; ps[ 7] = pi + 8;
          ps[ 0] = pi;     ps[ 1] = pi + 11; ps[ 2] = pi + 10; ps[ 3] = pi + 9;
          cs[2] = ci + 1; cs[3] = ci + 2;
          cs[0] = ci;     cs[1] = ci + 3;
          break;
        case 1:
          tmp1 = ps[12]; tmp2 = ps[13]; tmp3 = ps[14]; tmp4 = ps[15];
          ps[12] = pi + 5; ps[13] = pi + 4;  ps[14] = pi + 3;  ps[15] = pi + 2;
          ps[ 8] = pi + 6; ps[ 9] = pi + 11; ps[10] = pi + 10; ps[11] = pi + 1;
          ps[ 4] = pi + 7; ps[ 5] = pi + 8;  ps[ 6] = pi + 9;  ps[ 7] = pi;
          ps[ 0] = tmp1;   ps[ 1] = tmp2;    ps[ 2] = tmp3;    ps[ 3] = tmp4;
          tmp1 = cs[2]; tmp2 = cs[3];
          cs[2] = ci + 1; cs[3] = ci;
          cs[0] = tmp1;   cs[1] = tmp2;
          break;
        case 2:
          ps[12] = ps[15]; ps[13] = pi + 7; ps[14] = pi + 6;  ps[15] = pi + 5;
          ps[ 8] = ps[11]; ps[ 9] = pi + 8; ps[10] = pi + 11; ps[11] = pi + 4;
          ps[ 4] = ps[7];  ps[ 5] = pi + 9; ps[ 6] = pi + 10; ps[ 7] = pi + 3;
          ps[ 0] = ps[3];  ps[ 1] = pi;     ps[ 2] = pi + 1;  ps[ 3] = pi + 2;
          cs[2] = cs[3]; cs[3] = ci + 1;
          cs[0] = cs[1]; cs[1] = ci;
          break;
        case 3:
          ps[12] = ps[0];  ps[13] = ps[1];   ps[14] = ps[2];   ps[15] = ps[3];
          ps[ 8] = pi;     ps[ 9] = pi + 9;  ps[10] = pi + 8;  ps[11] = pi + 7;
          ps[ 4] = pi + 1; ps[ 5] = pi + 10; ps[ 6] = pi + 11; ps[ 7] = pi + 6;
          ps[ 0] = pi + 2; ps[ 1] = pi + 3;  ps[ 2] = pi + 4;  ps[ 3] = pi + 5;
          cs[2] = cs[0]; cs[3] = cs[1];
          cs[0] = ci;    cs[1] = ci + 1;
          break;
      }
      mesh.figures.push({
        type: 'patch',
        coords: new Int32Array(ps), // making copies of ps and cs
        colors: new Int32Array(cs)
      });
    }
  }

  function updateBounds(mesh) {
    var minX = mesh.coords[0][0], minY = mesh.coords[0][1],
      maxX = minX, maxY = minY;
    for (var i = 1, ii = mesh.coords.length; i < ii; i++) {
      var x = mesh.coords[i][0], y = mesh.coords[i][1];
      minX = minX > x ? x : minX;
      minY = minY > y ? y : minY;
      maxX = maxX < x ? x : maxX;
      maxY = maxY < y ? y : maxY;
    }
    mesh.bounds = [minX, minY, maxX, maxY];
  }

  function packData(mesh) {
    var i, ii, j, jj;

    var coords = mesh.coords;
    var coordsPacked = new Float32Array(coords.length * 2);
    for (i = 0, j = 0, ii = coords.length; i < ii; i++) {
      var xy = coords[i];
      coordsPacked[j++] = xy[0];
      coordsPacked[j++] = xy[1];
    }
    mesh.coords = coordsPacked;

    var colors = mesh.colors;
    var colorsPacked = new Uint8Array(colors.length * 3);
    for (i = 0, j = 0, ii = colors.length; i < ii; i++) {
      var c = colors[i];
      colorsPacked[j++] = c[0];
      colorsPacked[j++] = c[1];
      colorsPacked[j++] = c[2];
    }
    mesh.colors = colorsPacked;

    var figures = mesh.figures;
    for (i = 0, ii = figures.length; i < ii; i++) {
      var figure = figures[i], ps = figure.coords, cs = figure.colors;
      for (j = 0, jj = ps.length; j < jj; j++) {
        ps[j] *= 2;
        cs[j] *= 3;
      }
    }
  }

  function Mesh(stream, matrix, xref, res) {
    assert(isStream(stream), 'Mesh data is not a stream');
    var dict = stream.dict;
    this.matrix = matrix;
    this.shadingType = dict.get('ShadingType');
    this.type = 'Pattern';
    this.bbox = dict.get('BBox');
    var cs = dict.get('ColorSpace', 'CS');
    cs = ColorSpace.parse(cs, xref, res);
    this.cs = cs;
    this.background = dict.has('Background') ?
      cs.getRgb(dict.get('Background'), 0) : null;

    var fnObj = dict.get('Function');
    var fn = fnObj ? PDFFunction.parseArray(xref, fnObj) : null;

    this.coords = [];
    this.colors = [];
    this.figures = [];

    var decodeContext = {
      bitsPerCoordinate: dict.get('BitsPerCoordinate'),
      bitsPerComponent: dict.get('BitsPerComponent'),
      bitsPerFlag: dict.get('BitsPerFlag'),
      decode: dict.get('Decode'),
      colorFn: fn,
      colorSpace: cs,
      numComps: fn ? 1 : cs.numComps
    };
    var reader = new MeshStreamReader(stream, decodeContext);

    var patchMesh = false;
    switch (this.shadingType) {
      case PatternType.FREE_FORM_MESH:
        decodeType4Shading(this, reader);
        break;
      case PatternType.LATTICE_FORM_MESH:
        var verticesPerRow = dict.get('VerticesPerRow') | 0;
        assert(verticesPerRow >= 2, 'Invalid VerticesPerRow');
        decodeType5Shading(this, reader, verticesPerRow);
        break;
      case PatternType.COONS_PATCH_MESH:
        decodeType6Shading(this, reader);
        patchMesh = true;
        break;
      case PatternType.TENSOR_PATCH_MESH:
        decodeType7Shading(this, reader);
        patchMesh = true;
        break;
      default:
        error('Unsupported mesh type.');
        break;
    }

    if (patchMesh) {
      // dirty bounds calculation for determining, how dense shall be triangles
      updateBounds(this);
      for (var i = 0, ii = this.figures.length; i < ii; i++) {
        buildFigureFromPatch(this, i);
      }
    }
    // calculate bounds
    updateBounds(this);

    packData(this);
  }

  Mesh.prototype = {
    getIR: function Mesh_getIR() {
      return ['Mesh', this.shadingType, this.coords, this.colors, this.figures,
        this.bounds, this.matrix, this.bbox, this.background];
    }
  };

  return Mesh;
})();

Shadings.Dummy = (function DummyClosure() {
  function Dummy() {
    this.type = 'Pattern';
  }

  Dummy.prototype = {
    getIR: function Dummy_getIR() {
      return ['Dummy'];
    }
  };
  return Dummy;
})();

function getTilingPatternIR(operatorList, dict, args) {
  var matrix = dict.get('Matrix');
  var bbox = dict.get('BBox');
  var xstep = dict.get('XStep');
  var ystep = dict.get('YStep');
  var paintType = dict.get('PaintType');
  var tilingType = dict.get('TilingType');

  return [
    'TilingPattern', args, operatorList, matrix, bbox, xstep, ystep,
    paintType, tilingType
  ];
}
