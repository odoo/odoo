/**
 * @licstart The following is the entire license notice for the
 * JavaScript code in this page
 *
 * Copyright 2022 Mozilla Foundation
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
 * @licend The above is the entire license notice for the
 * JavaScript code in this page
 */

(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory();
	else if(typeof define === 'function' && define.amd)
		define("pdfjs-dist/build/pdf", [], factory);
	else if(typeof exports === 'object')
		exports["pdfjs-dist/build/pdf"] = factory();
	else
		root["pdfjs-dist/build/pdf"] = root.pdfjsLib = factory();
})(globalThis, () => {
return /******/ (() => { // webpackBootstrap
/******/ 	var __webpack_modules__ = ([
/* 0 */,
/* 1 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.VerbosityLevel = exports.Util = exports.UnknownErrorException = exports.UnexpectedResponseException = exports.UNSUPPORTED_FEATURES = exports.TextRenderingMode = exports.StreamType = exports.RenderingIntentFlag = exports.PermissionFlag = exports.PasswordResponses = exports.PasswordException = exports.PageActionEventType = exports.OPS = exports.MissingPDFException = exports.LINE_FACTOR = exports.LINE_DESCENT_FACTOR = exports.InvalidPDFException = exports.ImageKind = exports.IDENTITY_MATRIX = exports.FormatError = exports.FontType = exports.FeatureTest = exports.FONT_IDENTITY_MATRIX = exports.DocumentActionEventType = exports.CMapCompressionType = exports.BaseException = exports.AnnotationType = exports.AnnotationStateModelType = exports.AnnotationReviewState = exports.AnnotationReplyType = exports.AnnotationMode = exports.AnnotationMarkedState = exports.AnnotationFlag = exports.AnnotationFieldFlag = exports.AnnotationEditorType = exports.AnnotationEditorPrefix = exports.AnnotationEditorParamsType = exports.AnnotationBorderStyleType = exports.AnnotationActionEventType = exports.AbortException = void 0;
exports.arrayByteLength = arrayByteLength;
exports.arraysToBytes = arraysToBytes;
exports.assert = assert;
exports.bytesToString = bytesToString;
exports.createPromiseCapability = createPromiseCapability;
exports.createValidAbsoluteUrl = createValidAbsoluteUrl;
exports.escapeString = escapeString;
exports.getModificationDate = getModificationDate;
exports.getVerbosityLevel = getVerbosityLevel;
exports.info = info;
exports.isArrayBuffer = isArrayBuffer;
exports.isArrayEqual = isArrayEqual;
exports.isAscii = isAscii;
exports.objectFromMap = objectFromMap;
exports.objectSize = objectSize;
exports.setVerbosityLevel = setVerbosityLevel;
exports.shadow = shadow;
exports.string32 = string32;
exports.stringToBytes = stringToBytes;
exports.stringToPDFString = stringToPDFString;
exports.stringToUTF16BEString = stringToUTF16BEString;
exports.stringToUTF8String = stringToUTF8String;
exports.unreachable = unreachable;
exports.utf8StringToString = utf8StringToString;
exports.warn = warn;

__w_pdfjs_require__(2);

const IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0];
exports.IDENTITY_MATRIX = IDENTITY_MATRIX;
const FONT_IDENTITY_MATRIX = [0.001, 0, 0, 0.001, 0, 0];
exports.FONT_IDENTITY_MATRIX = FONT_IDENTITY_MATRIX;
const LINE_FACTOR = 1.35;
exports.LINE_FACTOR = LINE_FACTOR;
const LINE_DESCENT_FACTOR = 0.35;
exports.LINE_DESCENT_FACTOR = LINE_DESCENT_FACTOR;
const RenderingIntentFlag = {
  ANY: 0x01,
  DISPLAY: 0x02,
  PRINT: 0x04,
  ANNOTATIONS_FORMS: 0x10,
  ANNOTATIONS_STORAGE: 0x20,
  ANNOTATIONS_DISABLE: 0x40,
  OPLIST: 0x100
};
exports.RenderingIntentFlag = RenderingIntentFlag;
const AnnotationMode = {
  DISABLE: 0,
  ENABLE: 1,
  ENABLE_FORMS: 2,
  ENABLE_STORAGE: 3
};
exports.AnnotationMode = AnnotationMode;
const AnnotationEditorPrefix = "pdfjs_internal_editor_";
exports.AnnotationEditorPrefix = AnnotationEditorPrefix;
const AnnotationEditorType = {
  DISABLE: -1,
  NONE: 0,
  FREETEXT: 3,
  INK: 15
};
exports.AnnotationEditorType = AnnotationEditorType;
const AnnotationEditorParamsType = {
  FREETEXT_SIZE: 1,
  FREETEXT_COLOR: 2,
  FREETEXT_OPACITY: 3,
  INK_COLOR: 11,
  INK_THICKNESS: 12,
  INK_OPACITY: 13
};
exports.AnnotationEditorParamsType = AnnotationEditorParamsType;
const PermissionFlag = {
  PRINT: 0x04,
  MODIFY_CONTENTS: 0x08,
  COPY: 0x10,
  MODIFY_ANNOTATIONS: 0x20,
  FILL_INTERACTIVE_FORMS: 0x100,
  COPY_FOR_ACCESSIBILITY: 0x200,
  ASSEMBLE: 0x400,
  PRINT_HIGH_QUALITY: 0x800
};
exports.PermissionFlag = PermissionFlag;
const TextRenderingMode = {
  FILL: 0,
  STROKE: 1,
  FILL_STROKE: 2,
  INVISIBLE: 3,
  FILL_ADD_TO_PATH: 4,
  STROKE_ADD_TO_PATH: 5,
  FILL_STROKE_ADD_TO_PATH: 6,
  ADD_TO_PATH: 7,
  FILL_STROKE_MASK: 3,
  ADD_TO_PATH_FLAG: 4
};
exports.TextRenderingMode = TextRenderingMode;
const ImageKind = {
  GRAYSCALE_1BPP: 1,
  RGB_24BPP: 2,
  RGBA_32BPP: 3
};
exports.ImageKind = ImageKind;
const AnnotationType = {
  TEXT: 1,
  LINK: 2,
  FREETEXT: 3,
  LINE: 4,
  SQUARE: 5,
  CIRCLE: 6,
  POLYGON: 7,
  POLYLINE: 8,
  HIGHLIGHT: 9,
  UNDERLINE: 10,
  SQUIGGLY: 11,
  STRIKEOUT: 12,
  STAMP: 13,
  CARET: 14,
  INK: 15,
  POPUP: 16,
  FILEATTACHMENT: 17,
  SOUND: 18,
  MOVIE: 19,
  WIDGET: 20,
  SCREEN: 21,
  PRINTERMARK: 22,
  TRAPNET: 23,
  WATERMARK: 24,
  THREED: 25,
  REDACT: 26
};
exports.AnnotationType = AnnotationType;
const AnnotationStateModelType = {
  MARKED: "Marked",
  REVIEW: "Review"
};
exports.AnnotationStateModelType = AnnotationStateModelType;
const AnnotationMarkedState = {
  MARKED: "Marked",
  UNMARKED: "Unmarked"
};
exports.AnnotationMarkedState = AnnotationMarkedState;
const AnnotationReviewState = {
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
  COMPLETED: "Completed",
  NONE: "None"
};
exports.AnnotationReviewState = AnnotationReviewState;
const AnnotationReplyType = {
  GROUP: "Group",
  REPLY: "R"
};
exports.AnnotationReplyType = AnnotationReplyType;
const AnnotationFlag = {
  INVISIBLE: 0x01,
  HIDDEN: 0x02,
  PRINT: 0x04,
  NOZOOM: 0x08,
  NOROTATE: 0x10,
  NOVIEW: 0x20,
  READONLY: 0x40,
  LOCKED: 0x80,
  TOGGLENOVIEW: 0x100,
  LOCKEDCONTENTS: 0x200
};
exports.AnnotationFlag = AnnotationFlag;
const AnnotationFieldFlag = {
  READONLY: 0x0000001,
  REQUIRED: 0x0000002,
  NOEXPORT: 0x0000004,
  MULTILINE: 0x0001000,
  PASSWORD: 0x0002000,
  NOTOGGLETOOFF: 0x0004000,
  RADIO: 0x0008000,
  PUSHBUTTON: 0x0010000,
  COMBO: 0x0020000,
  EDIT: 0x0040000,
  SORT: 0x0080000,
  FILESELECT: 0x0100000,
  MULTISELECT: 0x0200000,
  DONOTSPELLCHECK: 0x0400000,
  DONOTSCROLL: 0x0800000,
  COMB: 0x1000000,
  RICHTEXT: 0x2000000,
  RADIOSINUNISON: 0x2000000,
  COMMITONSELCHANGE: 0x4000000
};
exports.AnnotationFieldFlag = AnnotationFieldFlag;
const AnnotationBorderStyleType = {
  SOLID: 1,
  DASHED: 2,
  BEVELED: 3,
  INSET: 4,
  UNDERLINE: 5
};
exports.AnnotationBorderStyleType = AnnotationBorderStyleType;
const AnnotationActionEventType = {
  E: "Mouse Enter",
  X: "Mouse Exit",
  D: "Mouse Down",
  U: "Mouse Up",
  Fo: "Focus",
  Bl: "Blur",
  PO: "PageOpen",
  PC: "PageClose",
  PV: "PageVisible",
  PI: "PageInvisible",
  K: "Keystroke",
  F: "Format",
  V: "Validate",
  C: "Calculate"
};
exports.AnnotationActionEventType = AnnotationActionEventType;
const DocumentActionEventType = {
  WC: "WillClose",
  WS: "WillSave",
  DS: "DidSave",
  WP: "WillPrint",
  DP: "DidPrint"
};
exports.DocumentActionEventType = DocumentActionEventType;
const PageActionEventType = {
  O: "PageOpen",
  C: "PageClose"
};
exports.PageActionEventType = PageActionEventType;
const StreamType = {
  UNKNOWN: "UNKNOWN",
  FLATE: "FLATE",
  LZW: "LZW",
  DCT: "DCT",
  JPX: "JPX",
  JBIG: "JBIG",
  A85: "A85",
  AHX: "AHX",
  CCF: "CCF",
  RLX: "RLX"
};
exports.StreamType = StreamType;
const FontType = {
  UNKNOWN: "UNKNOWN",
  TYPE1: "TYPE1",
  TYPE1STANDARD: "TYPE1STANDARD",
  TYPE1C: "TYPE1C",
  CIDFONTTYPE0: "CIDFONTTYPE0",
  CIDFONTTYPE0C: "CIDFONTTYPE0C",
  TRUETYPE: "TRUETYPE",
  CIDFONTTYPE2: "CIDFONTTYPE2",
  TYPE3: "TYPE3",
  OPENTYPE: "OPENTYPE",
  TYPE0: "TYPE0",
  MMTYPE1: "MMTYPE1"
};
exports.FontType = FontType;
const VerbosityLevel = {
  ERRORS: 0,
  WARNINGS: 1,
  INFOS: 5
};
exports.VerbosityLevel = VerbosityLevel;
const CMapCompressionType = {
  NONE: 0,
  BINARY: 1,
  STREAM: 2
};
exports.CMapCompressionType = CMapCompressionType;
const OPS = {
  dependency: 1,
  setLineWidth: 2,
  setLineCap: 3,
  setLineJoin: 4,
  setMiterLimit: 5,
  setDash: 6,
  setRenderingIntent: 7,
  setFlatness: 8,
  setGState: 9,
  save: 10,
  restore: 11,
  transform: 12,
  moveTo: 13,
  lineTo: 14,
  curveTo: 15,
  curveTo2: 16,
  curveTo3: 17,
  closePath: 18,
  rectangle: 19,
  stroke: 20,
  closeStroke: 21,
  fill: 22,
  eoFill: 23,
  fillStroke: 24,
  eoFillStroke: 25,
  closeFillStroke: 26,
  closeEOFillStroke: 27,
  endPath: 28,
  clip: 29,
  eoClip: 30,
  beginText: 31,
  endText: 32,
  setCharSpacing: 33,
  setWordSpacing: 34,
  setHScale: 35,
  setLeading: 36,
  setFont: 37,
  setTextRenderingMode: 38,
  setTextRise: 39,
  moveText: 40,
  setLeadingMoveText: 41,
  setTextMatrix: 42,
  nextLine: 43,
  showText: 44,
  showSpacedText: 45,
  nextLineShowText: 46,
  nextLineSetSpacingShowText: 47,
  setCharWidth: 48,
  setCharWidthAndBounds: 49,
  setStrokeColorSpace: 50,
  setFillColorSpace: 51,
  setStrokeColor: 52,
  setStrokeColorN: 53,
  setFillColor: 54,
  setFillColorN: 55,
  setStrokeGray: 56,
  setFillGray: 57,
  setStrokeRGBColor: 58,
  setFillRGBColor: 59,
  setStrokeCMYKColor: 60,
  setFillCMYKColor: 61,
  shadingFill: 62,
  beginInlineImage: 63,
  beginImageData: 64,
  endInlineImage: 65,
  paintXObject: 66,
  markPoint: 67,
  markPointProps: 68,
  beginMarkedContent: 69,
  beginMarkedContentProps: 70,
  endMarkedContent: 71,
  beginCompat: 72,
  endCompat: 73,
  paintFormXObjectBegin: 74,
  paintFormXObjectEnd: 75,
  beginGroup: 76,
  endGroup: 77,
  beginAnnotations: 78,
  endAnnotations: 79,
  beginAnnotation: 80,
  endAnnotation: 81,
  paintJpegXObject: 82,
  paintImageMaskXObject: 83,
  paintImageMaskXObjectGroup: 84,
  paintImageXObject: 85,
  paintInlineImageXObject: 86,
  paintInlineImageXObjectGroup: 87,
  paintImageXObjectRepeat: 88,
  paintImageMaskXObjectRepeat: 89,
  paintSolidColorImageMask: 90,
  constructPath: 91
};
exports.OPS = OPS;
const UNSUPPORTED_FEATURES = {
  unknown: "unknown",
  forms: "forms",
  javaScript: "javaScript",
  signatures: "signatures",
  smask: "smask",
  shadingPattern: "shadingPattern",
  font: "font",
  errorTilingPattern: "errorTilingPattern",
  errorExtGState: "errorExtGState",
  errorXObject: "errorXObject",
  errorFontLoadType3: "errorFontLoadType3",
  errorFontState: "errorFontState",
  errorFontMissing: "errorFontMissing",
  errorFontTranslate: "errorFontTranslate",
  errorColorSpace: "errorColorSpace",
  errorOperatorList: "errorOperatorList",
  errorFontToUnicode: "errorFontToUnicode",
  errorFontLoadNative: "errorFontLoadNative",
  errorFontBuildPath: "errorFontBuildPath",
  errorFontGetPath: "errorFontGetPath",
  errorMarkedContent: "errorMarkedContent",
  errorContentSubStream: "errorContentSubStream"
};
exports.UNSUPPORTED_FEATURES = UNSUPPORTED_FEATURES;
const PasswordResponses = {
  NEED_PASSWORD: 1,
  INCORRECT_PASSWORD: 2
};
exports.PasswordResponses = PasswordResponses;
let verbosity = VerbosityLevel.WARNINGS;

function setVerbosityLevel(level) {
  if (Number.isInteger(level)) {
    verbosity = level;
  }
}

function getVerbosityLevel() {
  return verbosity;
}

function info(msg) {
  if (verbosity >= VerbosityLevel.INFOS) {
    console.log(`Info: ${msg}`);
  }
}

function warn(msg) {
  if (verbosity >= VerbosityLevel.WARNINGS) {
    console.log(`Warning: ${msg}`);
  }
}

function unreachable(msg) {
  throw new Error(msg);
}

function assert(cond, msg) {
  if (!cond) {
    unreachable(msg);
  }
}

function _isValidProtocol(url) {
  if (!url) {
    return false;
  }

  switch (url.protocol) {
    case "http:":
    case "https:":
    case "ftp:":
    case "mailto:":
    case "tel:":
      return true;

    default:
      return false;
  }
}

function createValidAbsoluteUrl(url) {
  let baseUrl = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  let options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;

  if (!url) {
    return null;
  }

  try {
    if (options && typeof url === "string") {
      if (options.addDefaultProtocol && url.startsWith("www.")) {
        const dots = url.match(/\./g);

        if (dots && dots.length >= 2) {
          url = `http://${url}`;
        }
      }

      if (options.tryConvertEncoding) {
        try {
          url = stringToUTF8String(url);
        } catch (ex) {}
      }
    }

    const absoluteUrl = baseUrl ? new URL(url, baseUrl) : new URL(url);

    if (_isValidProtocol(absoluteUrl)) {
      return absoluteUrl;
    }
  } catch (ex) {}

  return null;
}

function shadow(obj, prop, value) {
  Object.defineProperty(obj, prop, {
    value,
    enumerable: true,
    configurable: true,
    writable: false
  });
  return value;
}

const BaseException = function BaseExceptionClosure() {
  function BaseException(message, name) {
    if (this.constructor === BaseException) {
      unreachable("Cannot initialize BaseException.");
    }

    this.message = message;
    this.name = name;
  }

  BaseException.prototype = new Error();
  BaseException.constructor = BaseException;
  return BaseException;
}();

exports.BaseException = BaseException;

class PasswordException extends BaseException {
  constructor(msg, code) {
    super(msg, "PasswordException");
    this.code = code;
  }

}

exports.PasswordException = PasswordException;

class UnknownErrorException extends BaseException {
  constructor(msg, details) {
    super(msg, "UnknownErrorException");
    this.details = details;
  }

}

exports.UnknownErrorException = UnknownErrorException;

class InvalidPDFException extends BaseException {
  constructor(msg) {
    super(msg, "InvalidPDFException");
  }

}

exports.InvalidPDFException = InvalidPDFException;

class MissingPDFException extends BaseException {
  constructor(msg) {
    super(msg, "MissingPDFException");
  }

}

exports.MissingPDFException = MissingPDFException;

class UnexpectedResponseException extends BaseException {
  constructor(msg, status) {
    super(msg, "UnexpectedResponseException");
    this.status = status;
  }

}

exports.UnexpectedResponseException = UnexpectedResponseException;

class FormatError extends BaseException {
  constructor(msg) {
    super(msg, "FormatError");
  }

}

exports.FormatError = FormatError;

class AbortException extends BaseException {
  constructor(msg) {
    super(msg, "AbortException");
  }

}

exports.AbortException = AbortException;

function bytesToString(bytes) {
  if (typeof bytes !== "object" || bytes === null || bytes.length === undefined) {
    unreachable("Invalid argument for bytesToString");
  }

  const length = bytes.length;
  const MAX_ARGUMENT_COUNT = 8192;

  if (length < MAX_ARGUMENT_COUNT) {
    return String.fromCharCode.apply(null, bytes);
  }

  const strBuf = [];

  for (let i = 0; i < length; i += MAX_ARGUMENT_COUNT) {
    const chunkEnd = Math.min(i + MAX_ARGUMENT_COUNT, length);
    const chunk = bytes.subarray(i, chunkEnd);
    strBuf.push(String.fromCharCode.apply(null, chunk));
  }

  return strBuf.join("");
}

function stringToBytes(str) {
  if (typeof str !== "string") {
    unreachable("Invalid argument for stringToBytes");
  }

  const length = str.length;
  const bytes = new Uint8Array(length);

  for (let i = 0; i < length; ++i) {
    bytes[i] = str.charCodeAt(i) & 0xff;
  }

  return bytes;
}

function arrayByteLength(arr) {
  if (arr.length !== undefined) {
    return arr.length;
  }

  if (arr.byteLength !== undefined) {
    return arr.byteLength;
  }

  unreachable("Invalid argument for arrayByteLength");
}

function arraysToBytes(arr) {
  const length = arr.length;

  if (length === 1 && arr[0] instanceof Uint8Array) {
    return arr[0];
  }

  let resultLength = 0;

  for (let i = 0; i < length; i++) {
    resultLength += arrayByteLength(arr[i]);
  }

  let pos = 0;
  const data = new Uint8Array(resultLength);

  for (let i = 0; i < length; i++) {
    let item = arr[i];

    if (!(item instanceof Uint8Array)) {
      if (typeof item === "string") {
        item = stringToBytes(item);
      } else {
        item = new Uint8Array(item);
      }
    }

    const itemLength = item.byteLength;
    data.set(item, pos);
    pos += itemLength;
  }

  return data;
}

function string32(value) {
  return String.fromCharCode(value >> 24 & 0xff, value >> 16 & 0xff, value >> 8 & 0xff, value & 0xff);
}

function objectSize(obj) {
  return Object.keys(obj).length;
}

function objectFromMap(map) {
  const obj = Object.create(null);

  for (const [key, value] of map) {
    obj[key] = value;
  }

  return obj;
}

function isLittleEndian() {
  const buffer8 = new Uint8Array(4);
  buffer8[0] = 1;
  const view32 = new Uint32Array(buffer8.buffer, 0, 1);
  return view32[0] === 1;
}

function isEvalSupported() {
  try {
    new Function("");
    return true;
  } catch (e) {
    return false;
  }
}

class FeatureTest {
  static get isLittleEndian() {
    return shadow(this, "isLittleEndian", isLittleEndian());
  }

  static get isEvalSupported() {
    return shadow(this, "isEvalSupported", isEvalSupported());
  }

  static get isOffscreenCanvasSupported() {
    return shadow(this, "isOffscreenCanvasSupported", typeof OffscreenCanvas !== "undefined");
  }

}

exports.FeatureTest = FeatureTest;
const hexNumbers = [...Array(256).keys()].map(n => n.toString(16).padStart(2, "0"));

class Util {
  static makeHexColor(r, g, b) {
    return `#${hexNumbers[r]}${hexNumbers[g]}${hexNumbers[b]}`;
  }

  static scaleMinMax(transform, minMax) {
    let temp;

    if (transform[0]) {
      if (transform[0] < 0) {
        temp = minMax[0];
        minMax[0] = minMax[1];
        minMax[1] = temp;
      }

      minMax[0] *= transform[0];
      minMax[1] *= transform[0];

      if (transform[3] < 0) {
        temp = minMax[2];
        minMax[2] = minMax[3];
        minMax[3] = temp;
      }

      minMax[2] *= transform[3];
      minMax[3] *= transform[3];
    } else {
      temp = minMax[0];
      minMax[0] = minMax[2];
      minMax[2] = temp;
      temp = minMax[1];
      minMax[1] = minMax[3];
      minMax[3] = temp;

      if (transform[1] < 0) {
        temp = minMax[2];
        minMax[2] = minMax[3];
        minMax[3] = temp;
      }

      minMax[2] *= transform[1];
      minMax[3] *= transform[1];

      if (transform[2] < 0) {
        temp = minMax[0];
        minMax[0] = minMax[1];
        minMax[1] = temp;
      }

      minMax[0] *= transform[2];
      minMax[1] *= transform[2];
    }

    minMax[0] += transform[4];
    minMax[1] += transform[4];
    minMax[2] += transform[5];
    minMax[3] += transform[5];
  }

  static transform(m1, m2) {
    return [m1[0] * m2[0] + m1[2] * m2[1], m1[1] * m2[0] + m1[3] * m2[1], m1[0] * m2[2] + m1[2] * m2[3], m1[1] * m2[2] + m1[3] * m2[3], m1[0] * m2[4] + m1[2] * m2[5] + m1[4], m1[1] * m2[4] + m1[3] * m2[5] + m1[5]];
  }

  static applyTransform(p, m) {
    const xt = p[0] * m[0] + p[1] * m[2] + m[4];
    const yt = p[0] * m[1] + p[1] * m[3] + m[5];
    return [xt, yt];
  }

  static applyInverseTransform(p, m) {
    const d = m[0] * m[3] - m[1] * m[2];
    const xt = (p[0] * m[3] - p[1] * m[2] + m[2] * m[5] - m[4] * m[3]) / d;
    const yt = (-p[0] * m[1] + p[1] * m[0] + m[4] * m[1] - m[5] * m[0]) / d;
    return [xt, yt];
  }

  static getAxialAlignedBoundingBox(r, m) {
    const p1 = Util.applyTransform(r, m);
    const p2 = Util.applyTransform(r.slice(2, 4), m);
    const p3 = Util.applyTransform([r[0], r[3]], m);
    const p4 = Util.applyTransform([r[2], r[1]], m);
    return [Math.min(p1[0], p2[0], p3[0], p4[0]), Math.min(p1[1], p2[1], p3[1], p4[1]), Math.max(p1[0], p2[0], p3[0], p4[0]), Math.max(p1[1], p2[1], p3[1], p4[1])];
  }

  static inverseTransform(m) {
    const d = m[0] * m[3] - m[1] * m[2];
    return [m[3] / d, -m[1] / d, -m[2] / d, m[0] / d, (m[2] * m[5] - m[4] * m[3]) / d, (m[4] * m[1] - m[5] * m[0]) / d];
  }

  static apply3dTransform(m, v) {
    return [m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2]];
  }

  static singularValueDecompose2dScale(m) {
    const transpose = [m[0], m[2], m[1], m[3]];
    const a = m[0] * transpose[0] + m[1] * transpose[2];
    const b = m[0] * transpose[1] + m[1] * transpose[3];
    const c = m[2] * transpose[0] + m[3] * transpose[2];
    const d = m[2] * transpose[1] + m[3] * transpose[3];
    const first = (a + d) / 2;
    const second = Math.sqrt((a + d) ** 2 - 4 * (a * d - c * b)) / 2;
    const sx = first + second || 1;
    const sy = first - second || 1;
    return [Math.sqrt(sx), Math.sqrt(sy)];
  }

  static normalizeRect(rect) {
    const r = rect.slice(0);

    if (rect[0] > rect[2]) {
      r[0] = rect[2];
      r[2] = rect[0];
    }

    if (rect[1] > rect[3]) {
      r[1] = rect[3];
      r[3] = rect[1];
    }

    return r;
  }

  static intersect(rect1, rect2) {
    const xLow = Math.max(Math.min(rect1[0], rect1[2]), Math.min(rect2[0], rect2[2]));
    const xHigh = Math.min(Math.max(rect1[0], rect1[2]), Math.max(rect2[0], rect2[2]));

    if (xLow > xHigh) {
      return null;
    }

    const yLow = Math.max(Math.min(rect1[1], rect1[3]), Math.min(rect2[1], rect2[3]));
    const yHigh = Math.min(Math.max(rect1[1], rect1[3]), Math.max(rect2[1], rect2[3]));

    if (yLow > yHigh) {
      return null;
    }

    return [xLow, yLow, xHigh, yHigh];
  }

  static bezierBoundingBox(x0, y0, x1, y1, x2, y2, x3, y3) {
    const tvalues = [],
          bounds = [[], []];
    let a, b, c, t, t1, t2, b2ac, sqrtb2ac;

    for (let i = 0; i < 2; ++i) {
      if (i === 0) {
        b = 6 * x0 - 12 * x1 + 6 * x2;
        a = -3 * x0 + 9 * x1 - 9 * x2 + 3 * x3;
        c = 3 * x1 - 3 * x0;
      } else {
        b = 6 * y0 - 12 * y1 + 6 * y2;
        a = -3 * y0 + 9 * y1 - 9 * y2 + 3 * y3;
        c = 3 * y1 - 3 * y0;
      }

      if (Math.abs(a) < 1e-12) {
        if (Math.abs(b) < 1e-12) {
          continue;
        }

        t = -c / b;

        if (0 < t && t < 1) {
          tvalues.push(t);
        }

        continue;
      }

      b2ac = b * b - 4 * c * a;
      sqrtb2ac = Math.sqrt(b2ac);

      if (b2ac < 0) {
        continue;
      }

      t1 = (-b + sqrtb2ac) / (2 * a);

      if (0 < t1 && t1 < 1) {
        tvalues.push(t1);
      }

      t2 = (-b - sqrtb2ac) / (2 * a);

      if (0 < t2 && t2 < 1) {
        tvalues.push(t2);
      }
    }

    let j = tvalues.length,
        mt;
    const jlen = j;

    while (j--) {
      t = tvalues[j];
      mt = 1 - t;
      bounds[0][j] = mt * mt * mt * x0 + 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t * t * t * x3;
      bounds[1][j] = mt * mt * mt * y0 + 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t * t * t * y3;
    }

    bounds[0][jlen] = x0;
    bounds[1][jlen] = y0;
    bounds[0][jlen + 1] = x3;
    bounds[1][jlen + 1] = y3;
    bounds[0].length = bounds[1].length = jlen + 2;
    return [Math.min(...bounds[0]), Math.min(...bounds[1]), Math.max(...bounds[0]), Math.max(...bounds[1])];
  }

}

exports.Util = Util;
const PDFStringTranslateTable = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x2d8, 0x2c7, 0x2c6, 0x2d9, 0x2dd, 0x2db, 0x2da, 0x2dc, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x2022, 0x2020, 0x2021, 0x2026, 0x2014, 0x2013, 0x192, 0x2044, 0x2039, 0x203a, 0x2212, 0x2030, 0x201e, 0x201c, 0x201d, 0x2018, 0x2019, 0x201a, 0x2122, 0xfb01, 0xfb02, 0x141, 0x152, 0x160, 0x178, 0x17d, 0x131, 0x142, 0x153, 0x161, 0x17e, 0, 0x20ac];

function stringToPDFString(str) {
  if (str[0] >= "\xEF") {
    let encoding;

    if (str[0] === "\xFE" && str[1] === "\xFF") {
      encoding = "utf-16be";
    } else if (str[0] === "\xFF" && str[1] === "\xFE") {
      encoding = "utf-16le";
    } else if (str[0] === "\xEF" && str[1] === "\xBB" && str[2] === "\xBF") {
      encoding = "utf-8";
    }

    if (encoding) {
      try {
        const decoder = new TextDecoder(encoding, {
          fatal: true
        });
        const buffer = stringToBytes(str);
        return decoder.decode(buffer);
      } catch (ex) {
        warn(`stringToPDFString: "${ex}".`);
      }
    }
  }

  const strBuf = [];

  for (let i = 0, ii = str.length; i < ii; i++) {
    const code = PDFStringTranslateTable[str.charCodeAt(i)];
    strBuf.push(code ? String.fromCharCode(code) : str.charAt(i));
  }

  return strBuf.join("");
}

function escapeString(str) {
  return str.replace(/([()\\\n\r])/g, match => {
    if (match === "\n") {
      return "\\n";
    } else if (match === "\r") {
      return "\\r";
    }

    return `\\${match}`;
  });
}

function isAscii(str) {
  return /^[\x00-\x7F]*$/.test(str);
}

function stringToUTF16BEString(str) {
  const buf = ["\xFE\xFF"];

  for (let i = 0, ii = str.length; i < ii; i++) {
    const char = str.charCodeAt(i);
    buf.push(String.fromCharCode(char >> 8 & 0xff), String.fromCharCode(char & 0xff));
  }

  return buf.join("");
}

function stringToUTF8String(str) {
  return decodeURIComponent(escape(str));
}

function utf8StringToString(str) {
  return unescape(encodeURIComponent(str));
}

function isArrayBuffer(v) {
  return typeof v === "object" && v !== null && v.byteLength !== undefined;
}

function isArrayEqual(arr1, arr2) {
  if (arr1.length !== arr2.length) {
    return false;
  }

  for (let i = 0, ii = arr1.length; i < ii; i++) {
    if (arr1[i] !== arr2[i]) {
      return false;
    }
  }

  return true;
}

function getModificationDate() {
  let date = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : new Date();
  const buffer = [date.getUTCFullYear().toString(), (date.getUTCMonth() + 1).toString().padStart(2, "0"), date.getUTCDate().toString().padStart(2, "0"), date.getUTCHours().toString().padStart(2, "0"), date.getUTCMinutes().toString().padStart(2, "0"), date.getUTCSeconds().toString().padStart(2, "0")];
  return buffer.join("");
}

function createPromiseCapability() {
  const capability = Object.create(null);
  let isSettled = false;
  Object.defineProperty(capability, "settled", {
    get() {
      return isSettled;
    }

  });
  capability.promise = new Promise(function (resolve, reject) {
    capability.resolve = function (data) {
      isSettled = true;
      resolve(data);
    };

    capability.reject = function (reason) {
      isSettled = true;
      reject(reason);
    };
  });
  return capability;
}

/***/ }),
/* 2 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";


var _is_node = __w_pdfjs_require__(3);

if (!globalThis._pdfjsCompatibilityChecked) {
  globalThis._pdfjsCompatibilityChecked = true;

  (function checkNodeBtoa() {
    if (globalThis.btoa || !_is_node.isNodeJS) {
      return;
    }

    globalThis.btoa = function (chars) {
      return Buffer.from(chars, "binary").toString("base64");
    };
  })();

  (function checkNodeAtob() {
    if (globalThis.atob || !_is_node.isNodeJS) {
      return;
    }

    globalThis.atob = function (input) {
      return Buffer.from(input, "base64").toString("binary");
    };
  })();

  (function checkDOMMatrix() {
    if (globalThis.DOMMatrix || !_is_node.isNodeJS) {
      return;
    }

    globalThis.DOMMatrix = require("dommatrix/dist/dommatrix.js");
  })();

  (function checkReadableStream() {
    if (globalThis.ReadableStream || !_is_node.isNodeJS) {
      return;
    }

    globalThis.ReadableStream = require("web-streams-polyfill/dist/ponyfill.js").ReadableStream;
  })();

  (function checkArrayAt() {
    if (Array.prototype.at) {
      return;
    }

    __w_pdfjs_require__(4);
  })();

  (function checkTypedArrayAt() {
    if (Uint8Array.prototype.at) {
      return;
    }

    __w_pdfjs_require__(76);
  })();

  (function checkStructuredClone() {
    if (globalThis.structuredClone) {
      return;
    }

    __w_pdfjs_require__(86);
  })();
}

/***/ }),
/* 3 */
/***/ ((__unused_webpack_module, exports) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.isNodeJS = void 0;
const isNodeJS = typeof process === "object" && process + "" === "[object process]" && !process.versions.nw && !(process.versions.electron && process.type && process.type !== "browser");
exports.isNodeJS = isNodeJS;

/***/ }),
/* 4 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

__w_pdfjs_require__(5);
var entryUnbind = __w_pdfjs_require__(75);
module.exports = entryUnbind('Array', 'at');

/***/ }),
/* 5 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var $ = __w_pdfjs_require__(6);
var toObject = __w_pdfjs_require__(41);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var toIntegerOrInfinity = __w_pdfjs_require__(63);
var addToUnscopables = __w_pdfjs_require__(70);
$({
 target: 'Array',
 proto: true
}, {
 at: function at(index) {
  var O = toObject(this);
  var len = lengthOfArrayLike(O);
  var relativeIndex = toIntegerOrInfinity(index);
  var k = relativeIndex >= 0 ? relativeIndex : len + relativeIndex;
  return k < 0 || k >= len ? undefined : O[k];
 }
});
addToUnscopables('at');

/***/ }),
/* 6 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var getOwnPropertyDescriptor = (__w_pdfjs_require__(8).f);
var createNonEnumerableProperty = __w_pdfjs_require__(45);
var defineBuiltIn = __w_pdfjs_require__(49);
var defineGlobalProperty = __w_pdfjs_require__(39);
var copyConstructorProperties = __w_pdfjs_require__(57);
var isForced = __w_pdfjs_require__(69);
module.exports = function (options, source) {
 var TARGET = options.target;
 var GLOBAL = options.global;
 var STATIC = options.stat;
 var FORCED, target, key, targetProperty, sourceProperty, descriptor;
 if (GLOBAL) {
  target = global;
 } else if (STATIC) {
  target = global[TARGET] || defineGlobalProperty(TARGET, {});
 } else {
  target = (global[TARGET] || {}).prototype;
 }
 if (target)
  for (key in source) {
   sourceProperty = source[key];
   if (options.dontCallGetSet) {
    descriptor = getOwnPropertyDescriptor(target, key);
    targetProperty = descriptor && descriptor.value;
   } else
    targetProperty = target[key];
   FORCED = isForced(GLOBAL ? key : TARGET + (STATIC ? '.' : '#') + key, options.forced);
   if (!FORCED && targetProperty !== undefined) {
    if (typeof sourceProperty == typeof targetProperty)
     continue;
    copyConstructorProperties(sourceProperty, targetProperty);
   }
   if (options.sham || targetProperty && targetProperty.sham) {
    createNonEnumerableProperty(sourceProperty, 'sham', true);
   }
   defineBuiltIn(target, key, sourceProperty, options);
  }
};

/***/ }),
/* 7 */
/***/ ((module) => {

var check = function (it) {
 return it && it.Math == Math && it;
};
module.exports = check(typeof globalThis == 'object' && globalThis) || check(typeof window == 'object' && window) || check(typeof self == 'object' && self) || check(typeof global == 'object' && global) || (function () {
 return this;
}()) || Function('return this')();

/***/ }),
/* 8 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var call = __w_pdfjs_require__(11);
var propertyIsEnumerableModule = __w_pdfjs_require__(13);
var createPropertyDescriptor = __w_pdfjs_require__(14);
var toIndexedObject = __w_pdfjs_require__(15);
var toPropertyKey = __w_pdfjs_require__(20);
var hasOwn = __w_pdfjs_require__(40);
var IE8_DOM_DEFINE = __w_pdfjs_require__(43);
var $getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
exports.f = DESCRIPTORS ? $getOwnPropertyDescriptor : function getOwnPropertyDescriptor(O, P) {
 O = toIndexedObject(O);
 P = toPropertyKey(P);
 if (IE8_DOM_DEFINE)
  try {
   return $getOwnPropertyDescriptor(O, P);
  } catch (error) {
  }
 if (hasOwn(O, P))
  return createPropertyDescriptor(!call(propertyIsEnumerableModule.f, O, P), O[P]);
};

/***/ }),
/* 9 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
module.exports = !fails(function () {
 return Object.defineProperty({}, 1, {
  get: function () {
   return 7;
  }
 })[1] != 7;
});

/***/ }),
/* 10 */
/***/ ((module) => {

module.exports = function (exec) {
 try {
  return !!exec();
 } catch (error) {
  return true;
 }
};

/***/ }),
/* 11 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var NATIVE_BIND = __w_pdfjs_require__(12);
var call = Function.prototype.call;
module.exports = NATIVE_BIND ? call.bind(call) : function () {
 return call.apply(call, arguments);
};

/***/ }),
/* 12 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
module.exports = !fails(function () {
 var test = function () {
 }.bind();
 return typeof test != 'function' || test.hasOwnProperty('prototype');
});

/***/ }),
/* 13 */
/***/ ((__unused_webpack_module, exports) => {

"use strict";

var $propertyIsEnumerable = {}.propertyIsEnumerable;
var getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
var NASHORN_BUG = getOwnPropertyDescriptor && !$propertyIsEnumerable.call({ 1: 2 }, 1);
exports.f = NASHORN_BUG ? function propertyIsEnumerable(V) {
 var descriptor = getOwnPropertyDescriptor(this, V);
 return !!descriptor && descriptor.enumerable;
} : $propertyIsEnumerable;

/***/ }),
/* 14 */
/***/ ((module) => {

module.exports = function (bitmap, value) {
 return {
  enumerable: !(bitmap & 1),
  configurable: !(bitmap & 2),
  writable: !(bitmap & 4),
  value: value
 };
};

/***/ }),
/* 15 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var IndexedObject = __w_pdfjs_require__(16);
var requireObjectCoercible = __w_pdfjs_require__(19);
module.exports = function (it) {
 return IndexedObject(requireObjectCoercible(it));
};

/***/ }),
/* 16 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var fails = __w_pdfjs_require__(10);
var classof = __w_pdfjs_require__(18);
var $Object = Object;
var split = uncurryThis(''.split);
module.exports = fails(function () {
 return !$Object('z').propertyIsEnumerable(0);
}) ? function (it) {
 return classof(it) == 'String' ? split(it, '') : $Object(it);
} : $Object;

/***/ }),
/* 17 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var NATIVE_BIND = __w_pdfjs_require__(12);
var FunctionPrototype = Function.prototype;
var bind = FunctionPrototype.bind;
var call = FunctionPrototype.call;
var uncurryThis = NATIVE_BIND && bind.bind(call, call);
module.exports = NATIVE_BIND ? function (fn) {
 return fn && uncurryThis(fn);
} : function (fn) {
 return fn && function () {
  return call.apply(fn, arguments);
 };
};

/***/ }),
/* 18 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var toString = uncurryThis({}.toString);
var stringSlice = uncurryThis(''.slice);
module.exports = function (it) {
 return stringSlice(toString(it), 8, -1);
};

/***/ }),
/* 19 */
/***/ ((module) => {

var $TypeError = TypeError;
module.exports = function (it) {
 if (it == undefined)
  throw $TypeError("Can't call method on " + it);
 return it;
};

/***/ }),
/* 20 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toPrimitive = __w_pdfjs_require__(21);
var isSymbol = __w_pdfjs_require__(24);
module.exports = function (argument) {
 var key = toPrimitive(argument, 'string');
 return isSymbol(key) ? key : key + '';
};

/***/ }),
/* 21 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var call = __w_pdfjs_require__(11);
var isObject = __w_pdfjs_require__(22);
var isSymbol = __w_pdfjs_require__(24);
var getMethod = __w_pdfjs_require__(31);
var ordinaryToPrimitive = __w_pdfjs_require__(34);
var wellKnownSymbol = __w_pdfjs_require__(35);
var $TypeError = TypeError;
var TO_PRIMITIVE = wellKnownSymbol('toPrimitive');
module.exports = function (input, pref) {
 if (!isObject(input) || isSymbol(input))
  return input;
 var exoticToPrim = getMethod(input, TO_PRIMITIVE);
 var result;
 if (exoticToPrim) {
  if (pref === undefined)
   pref = 'default';
  result = call(exoticToPrim, input, pref);
  if (!isObject(result) || isSymbol(result))
   return result;
  throw $TypeError("Can't convert object to primitive value");
 }
 if (pref === undefined)
  pref = 'number';
 return ordinaryToPrimitive(input, pref);
};

/***/ }),
/* 22 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isCallable = __w_pdfjs_require__(23);
module.exports = function (it) {
 return typeof it == 'object' ? it !== null : isCallable(it);
};

/***/ }),
/* 23 */
/***/ ((module) => {

module.exports = function (argument) {
 return typeof argument == 'function';
};

/***/ }),
/* 24 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var getBuiltIn = __w_pdfjs_require__(25);
var isCallable = __w_pdfjs_require__(23);
var isPrototypeOf = __w_pdfjs_require__(26);
var USE_SYMBOL_AS_UID = __w_pdfjs_require__(27);
var $Object = Object;
module.exports = USE_SYMBOL_AS_UID ? function (it) {
 return typeof it == 'symbol';
} : function (it) {
 var $Symbol = getBuiltIn('Symbol');
 return isCallable($Symbol) && isPrototypeOf($Symbol.prototype, $Object(it));
};

/***/ }),
/* 25 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var isCallable = __w_pdfjs_require__(23);
var aFunction = function (argument) {
 return isCallable(argument) ? argument : undefined;
};
module.exports = function (namespace, method) {
 return arguments.length < 2 ? aFunction(global[namespace]) : global[namespace] && global[namespace][method];
};

/***/ }),
/* 26 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
module.exports = uncurryThis({}.isPrototypeOf);

/***/ }),
/* 27 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var NATIVE_SYMBOL = __w_pdfjs_require__(28);
module.exports = NATIVE_SYMBOL && !Symbol.sham && typeof Symbol.iterator == 'symbol';

/***/ }),
/* 28 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var V8_VERSION = __w_pdfjs_require__(29);
var fails = __w_pdfjs_require__(10);
module.exports = !!Object.getOwnPropertySymbols && !fails(function () {
 var symbol = Symbol();
 return !String(symbol) || !(Object(symbol) instanceof Symbol) || !Symbol.sham && V8_VERSION && V8_VERSION < 41;
});

/***/ }),
/* 29 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var userAgent = __w_pdfjs_require__(30);
var process = global.process;
var Deno = global.Deno;
var versions = process && process.versions || Deno && Deno.version;
var v8 = versions && versions.v8;
var match, version;
if (v8) {
 match = v8.split('.');
 version = match[0] > 0 && match[0] < 4 ? 1 : +(match[0] + match[1]);
}
if (!version && userAgent) {
 match = userAgent.match(/Edge\/(\d+)/);
 if (!match || match[1] >= 74) {
  match = userAgent.match(/Chrome\/(\d+)/);
  if (match)
   version = +match[1];
 }
}
module.exports = version;

/***/ }),
/* 30 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var getBuiltIn = __w_pdfjs_require__(25);
module.exports = getBuiltIn('navigator', 'userAgent') || '';

/***/ }),
/* 31 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var aCallable = __w_pdfjs_require__(32);
module.exports = function (V, P) {
 var func = V[P];
 return func == null ? undefined : aCallable(func);
};

/***/ }),
/* 32 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isCallable = __w_pdfjs_require__(23);
var tryToString = __w_pdfjs_require__(33);
var $TypeError = TypeError;
module.exports = function (argument) {
 if (isCallable(argument))
  return argument;
 throw $TypeError(tryToString(argument) + ' is not a function');
};

/***/ }),
/* 33 */
/***/ ((module) => {

var $String = String;
module.exports = function (argument) {
 try {
  return $String(argument);
 } catch (error) {
  return 'Object';
 }
};

/***/ }),
/* 34 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var call = __w_pdfjs_require__(11);
var isCallable = __w_pdfjs_require__(23);
var isObject = __w_pdfjs_require__(22);
var $TypeError = TypeError;
module.exports = function (input, pref) {
 var fn, val;
 if (pref === 'string' && isCallable(fn = input.toString) && !isObject(val = call(fn, input)))
  return val;
 if (isCallable(fn = input.valueOf) && !isObject(val = call(fn, input)))
  return val;
 if (pref !== 'string' && isCallable(fn = input.toString) && !isObject(val = call(fn, input)))
  return val;
 throw $TypeError("Can't convert object to primitive value");
};

/***/ }),
/* 35 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var shared = __w_pdfjs_require__(36);
var hasOwn = __w_pdfjs_require__(40);
var uid = __w_pdfjs_require__(42);
var NATIVE_SYMBOL = __w_pdfjs_require__(28);
var USE_SYMBOL_AS_UID = __w_pdfjs_require__(27);
var WellKnownSymbolsStore = shared('wks');
var Symbol = global.Symbol;
var symbolFor = Symbol && Symbol['for'];
var createWellKnownSymbol = USE_SYMBOL_AS_UID ? Symbol : Symbol && Symbol.withoutSetter || uid;
module.exports = function (name) {
 if (!hasOwn(WellKnownSymbolsStore, name) || !(NATIVE_SYMBOL || typeof WellKnownSymbolsStore[name] == 'string')) {
  var description = 'Symbol.' + name;
  if (NATIVE_SYMBOL && hasOwn(Symbol, name)) {
   WellKnownSymbolsStore[name] = Symbol[name];
  } else if (USE_SYMBOL_AS_UID && symbolFor) {
   WellKnownSymbolsStore[name] = symbolFor(description);
  } else {
   WellKnownSymbolsStore[name] = createWellKnownSymbol(description);
  }
 }
 return WellKnownSymbolsStore[name];
};

/***/ }),
/* 36 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var IS_PURE = __w_pdfjs_require__(37);
var store = __w_pdfjs_require__(38);
(module.exports = function (key, value) {
 return store[key] || (store[key] = value !== undefined ? value : {});
})('versions', []).push({
 version: '3.24.1',
 mode: IS_PURE ? 'pure' : 'global',
 copyright: '© 2014-2022 Denis Pushkarev (zloirock.ru)',
 license: 'https://github.com/zloirock/core-js/blob/v3.24.1/LICENSE',
 source: 'https://github.com/zloirock/core-js'
});

/***/ }),
/* 37 */
/***/ ((module) => {

module.exports = false;

/***/ }),
/* 38 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var defineGlobalProperty = __w_pdfjs_require__(39);
var SHARED = '__core-js_shared__';
var store = global[SHARED] || defineGlobalProperty(SHARED, {});
module.exports = store;

/***/ }),
/* 39 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var defineProperty = Object.defineProperty;
module.exports = function (key, value) {
 try {
  defineProperty(global, key, {
   value: value,
   configurable: true,
   writable: true
  });
 } catch (error) {
  global[key] = value;
 }
 return value;
};

/***/ }),
/* 40 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var toObject = __w_pdfjs_require__(41);
var hasOwnProperty = uncurryThis({}.hasOwnProperty);
module.exports = Object.hasOwn || function hasOwn(it, key) {
 return hasOwnProperty(toObject(it), key);
};

/***/ }),
/* 41 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var requireObjectCoercible = __w_pdfjs_require__(19);
var $Object = Object;
module.exports = function (argument) {
 return $Object(requireObjectCoercible(argument));
};

/***/ }),
/* 42 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var id = 0;
var postfix = Math.random();
var toString = uncurryThis(1.0.toString);
module.exports = function (key) {
 return 'Symbol(' + (key === undefined ? '' : key) + ')_' + toString(++id + postfix, 36);
};

/***/ }),
/* 43 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var fails = __w_pdfjs_require__(10);
var createElement = __w_pdfjs_require__(44);
module.exports = !DESCRIPTORS && !fails(function () {
 return Object.defineProperty(createElement('div'), 'a', {
  get: function () {
   return 7;
  }
 }).a != 7;
});

/***/ }),
/* 44 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var isObject = __w_pdfjs_require__(22);
var document = global.document;
var EXISTS = isObject(document) && isObject(document.createElement);
module.exports = function (it) {
 return EXISTS ? document.createElement(it) : {};
};

/***/ }),
/* 45 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var definePropertyModule = __w_pdfjs_require__(46);
var createPropertyDescriptor = __w_pdfjs_require__(14);
module.exports = DESCRIPTORS ? function (object, key, value) {
 return definePropertyModule.f(object, key, createPropertyDescriptor(1, value));
} : function (object, key, value) {
 object[key] = value;
 return object;
};

/***/ }),
/* 46 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var IE8_DOM_DEFINE = __w_pdfjs_require__(43);
var V8_PROTOTYPE_DEFINE_BUG = __w_pdfjs_require__(47);
var anObject = __w_pdfjs_require__(48);
var toPropertyKey = __w_pdfjs_require__(20);
var $TypeError = TypeError;
var $defineProperty = Object.defineProperty;
var $getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
var ENUMERABLE = 'enumerable';
var CONFIGURABLE = 'configurable';
var WRITABLE = 'writable';
exports.f = DESCRIPTORS ? V8_PROTOTYPE_DEFINE_BUG ? function defineProperty(O, P, Attributes) {
 anObject(O);
 P = toPropertyKey(P);
 anObject(Attributes);
 if (typeof O === 'function' && P === 'prototype' && 'value' in Attributes && WRITABLE in Attributes && !Attributes[WRITABLE]) {
  var current = $getOwnPropertyDescriptor(O, P);
  if (current && current[WRITABLE]) {
   O[P] = Attributes.value;
   Attributes = {
    configurable: CONFIGURABLE in Attributes ? Attributes[CONFIGURABLE] : current[CONFIGURABLE],
    enumerable: ENUMERABLE in Attributes ? Attributes[ENUMERABLE] : current[ENUMERABLE],
    writable: false
   };
  }
 }
 return $defineProperty(O, P, Attributes);
} : $defineProperty : function defineProperty(O, P, Attributes) {
 anObject(O);
 P = toPropertyKey(P);
 anObject(Attributes);
 if (IE8_DOM_DEFINE)
  try {
   return $defineProperty(O, P, Attributes);
  } catch (error) {
  }
 if ('get' in Attributes || 'set' in Attributes)
  throw $TypeError('Accessors not supported');
 if ('value' in Attributes)
  O[P] = Attributes.value;
 return O;
};

/***/ }),
/* 47 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var fails = __w_pdfjs_require__(10);
module.exports = DESCRIPTORS && fails(function () {
 return Object.defineProperty(function () {
 }, 'prototype', {
  value: 42,
  writable: false
 }).prototype != 42;
});

/***/ }),
/* 48 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isObject = __w_pdfjs_require__(22);
var $String = String;
var $TypeError = TypeError;
module.exports = function (argument) {
 if (isObject(argument))
  return argument;
 throw $TypeError($String(argument) + ' is not an object');
};

/***/ }),
/* 49 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isCallable = __w_pdfjs_require__(23);
var definePropertyModule = __w_pdfjs_require__(46);
var makeBuiltIn = __w_pdfjs_require__(50);
var defineGlobalProperty = __w_pdfjs_require__(39);
module.exports = function (O, key, value, options) {
 if (!options)
  options = {};
 var simple = options.enumerable;
 var name = options.name !== undefined ? options.name : key;
 if (isCallable(value))
  makeBuiltIn(value, name, options);
 if (options.global) {
  if (simple)
   O[key] = value;
  else
   defineGlobalProperty(key, value);
 } else {
  try {
   if (!options.unsafe)
    delete O[key];
   else if (O[key])
    simple = true;
  } catch (error) {
  }
  if (simple)
   O[key] = value;
  else
   definePropertyModule.f(O, key, {
    value: value,
    enumerable: false,
    configurable: !options.nonConfigurable,
    writable: !options.nonWritable
   });
 }
 return O;
};

/***/ }),
/* 50 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
var isCallable = __w_pdfjs_require__(23);
var hasOwn = __w_pdfjs_require__(40);
var DESCRIPTORS = __w_pdfjs_require__(9);
var CONFIGURABLE_FUNCTION_NAME = (__w_pdfjs_require__(51).CONFIGURABLE);
var inspectSource = __w_pdfjs_require__(52);
var InternalStateModule = __w_pdfjs_require__(53);
var enforceInternalState = InternalStateModule.enforce;
var getInternalState = InternalStateModule.get;
var defineProperty = Object.defineProperty;
var CONFIGURABLE_LENGTH = DESCRIPTORS && !fails(function () {
 return defineProperty(function () {
 }, 'length', { value: 8 }).length !== 8;
});
var TEMPLATE = String(String).split('String');
var makeBuiltIn = module.exports = function (value, name, options) {
 if (String(name).slice(0, 7) === 'Symbol(') {
  name = '[' + String(name).replace(/^Symbol\(([^)]*)\)/, '$1') + ']';
 }
 if (options && options.getter)
  name = 'get ' + name;
 if (options && options.setter)
  name = 'set ' + name;
 if (!hasOwn(value, 'name') || CONFIGURABLE_FUNCTION_NAME && value.name !== name) {
  if (DESCRIPTORS)
   defineProperty(value, 'name', {
    value: name,
    configurable: true
   });
  else
   value.name = name;
 }
 if (CONFIGURABLE_LENGTH && options && hasOwn(options, 'arity') && value.length !== options.arity) {
  defineProperty(value, 'length', { value: options.arity });
 }
 try {
  if (options && hasOwn(options, 'constructor') && options.constructor) {
   if (DESCRIPTORS)
    defineProperty(value, 'prototype', { writable: false });
  } else if (value.prototype)
   value.prototype = undefined;
 } catch (error) {
 }
 var state = enforceInternalState(value);
 if (!hasOwn(state, 'source')) {
  state.source = TEMPLATE.join(typeof name == 'string' ? name : '');
 }
 return value;
};
Function.prototype.toString = makeBuiltIn(function toString() {
 return isCallable(this) && getInternalState(this).source || inspectSource(this);
}, 'toString');

/***/ }),
/* 51 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var hasOwn = __w_pdfjs_require__(40);
var FunctionPrototype = Function.prototype;
var getDescriptor = DESCRIPTORS && Object.getOwnPropertyDescriptor;
var EXISTS = hasOwn(FunctionPrototype, 'name');
var PROPER = EXISTS && function something() {
}.name === 'something';
var CONFIGURABLE = EXISTS && (!DESCRIPTORS || DESCRIPTORS && getDescriptor(FunctionPrototype, 'name').configurable);
module.exports = {
 EXISTS: EXISTS,
 PROPER: PROPER,
 CONFIGURABLE: CONFIGURABLE
};

/***/ }),
/* 52 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var isCallable = __w_pdfjs_require__(23);
var store = __w_pdfjs_require__(38);
var functionToString = uncurryThis(Function.toString);
if (!isCallable(store.inspectSource)) {
 store.inspectSource = function (it) {
  return functionToString(it);
 };
}
module.exports = store.inspectSource;

/***/ }),
/* 53 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var NATIVE_WEAK_MAP = __w_pdfjs_require__(54);
var global = __w_pdfjs_require__(7);
var uncurryThis = __w_pdfjs_require__(17);
var isObject = __w_pdfjs_require__(22);
var createNonEnumerableProperty = __w_pdfjs_require__(45);
var hasOwn = __w_pdfjs_require__(40);
var shared = __w_pdfjs_require__(38);
var sharedKey = __w_pdfjs_require__(55);
var hiddenKeys = __w_pdfjs_require__(56);
var OBJECT_ALREADY_INITIALIZED = 'Object already initialized';
var TypeError = global.TypeError;
var WeakMap = global.WeakMap;
var set, get, has;
var enforce = function (it) {
 return has(it) ? get(it) : set(it, {});
};
var getterFor = function (TYPE) {
 return function (it) {
  var state;
  if (!isObject(it) || (state = get(it)).type !== TYPE) {
   throw TypeError('Incompatible receiver, ' + TYPE + ' required');
  }
  return state;
 };
};
if (NATIVE_WEAK_MAP || shared.state) {
 var store = shared.state || (shared.state = new WeakMap());
 var wmget = uncurryThis(store.get);
 var wmhas = uncurryThis(store.has);
 var wmset = uncurryThis(store.set);
 set = function (it, metadata) {
  if (wmhas(store, it))
   throw new TypeError(OBJECT_ALREADY_INITIALIZED);
  metadata.facade = it;
  wmset(store, it, metadata);
  return metadata;
 };
 get = function (it) {
  return wmget(store, it) || {};
 };
 has = function (it) {
  return wmhas(store, it);
 };
} else {
 var STATE = sharedKey('state');
 hiddenKeys[STATE] = true;
 set = function (it, metadata) {
  if (hasOwn(it, STATE))
   throw new TypeError(OBJECT_ALREADY_INITIALIZED);
  metadata.facade = it;
  createNonEnumerableProperty(it, STATE, metadata);
  return metadata;
 };
 get = function (it) {
  return hasOwn(it, STATE) ? it[STATE] : {};
 };
 has = function (it) {
  return hasOwn(it, STATE);
 };
}
module.exports = {
 set: set,
 get: get,
 has: has,
 enforce: enforce,
 getterFor: getterFor
};

/***/ }),
/* 54 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var isCallable = __w_pdfjs_require__(23);
var inspectSource = __w_pdfjs_require__(52);
var WeakMap = global.WeakMap;
module.exports = isCallable(WeakMap) && /native code/.test(inspectSource(WeakMap));

/***/ }),
/* 55 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var shared = __w_pdfjs_require__(36);
var uid = __w_pdfjs_require__(42);
var keys = shared('keys');
module.exports = function (key) {
 return keys[key] || (keys[key] = uid(key));
};

/***/ }),
/* 56 */
/***/ ((module) => {

module.exports = {};

/***/ }),
/* 57 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var hasOwn = __w_pdfjs_require__(40);
var ownKeys = __w_pdfjs_require__(58);
var getOwnPropertyDescriptorModule = __w_pdfjs_require__(8);
var definePropertyModule = __w_pdfjs_require__(46);
module.exports = function (target, source, exceptions) {
 var keys = ownKeys(source);
 var defineProperty = definePropertyModule.f;
 var getOwnPropertyDescriptor = getOwnPropertyDescriptorModule.f;
 for (var i = 0; i < keys.length; i++) {
  var key = keys[i];
  if (!hasOwn(target, key) && !(exceptions && hasOwn(exceptions, key))) {
   defineProperty(target, key, getOwnPropertyDescriptor(source, key));
  }
 }
};

/***/ }),
/* 58 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var getBuiltIn = __w_pdfjs_require__(25);
var uncurryThis = __w_pdfjs_require__(17);
var getOwnPropertyNamesModule = __w_pdfjs_require__(59);
var getOwnPropertySymbolsModule = __w_pdfjs_require__(68);
var anObject = __w_pdfjs_require__(48);
var concat = uncurryThis([].concat);
module.exports = getBuiltIn('Reflect', 'ownKeys') || function ownKeys(it) {
 var keys = getOwnPropertyNamesModule.f(anObject(it));
 var getOwnPropertySymbols = getOwnPropertySymbolsModule.f;
 return getOwnPropertySymbols ? concat(keys, getOwnPropertySymbols(it)) : keys;
};

/***/ }),
/* 59 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

var internalObjectKeys = __w_pdfjs_require__(60);
var enumBugKeys = __w_pdfjs_require__(67);
var hiddenKeys = enumBugKeys.concat('length', 'prototype');
exports.f = Object.getOwnPropertyNames || function getOwnPropertyNames(O) {
 return internalObjectKeys(O, hiddenKeys);
};

/***/ }),
/* 60 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var hasOwn = __w_pdfjs_require__(40);
var toIndexedObject = __w_pdfjs_require__(15);
var indexOf = (__w_pdfjs_require__(61).indexOf);
var hiddenKeys = __w_pdfjs_require__(56);
var push = uncurryThis([].push);
module.exports = function (object, names) {
 var O = toIndexedObject(object);
 var i = 0;
 var result = [];
 var key;
 for (key in O)
  !hasOwn(hiddenKeys, key) && hasOwn(O, key) && push(result, key);
 while (names.length > i)
  if (hasOwn(O, key = names[i++])) {
   ~indexOf(result, key) || push(result, key);
  }
 return result;
};

/***/ }),
/* 61 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toIndexedObject = __w_pdfjs_require__(15);
var toAbsoluteIndex = __w_pdfjs_require__(62);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var createMethod = function (IS_INCLUDES) {
 return function ($this, el, fromIndex) {
  var O = toIndexedObject($this);
  var length = lengthOfArrayLike(O);
  var index = toAbsoluteIndex(fromIndex, length);
  var value;
  if (IS_INCLUDES && el != el)
   while (length > index) {
    value = O[index++];
    if (value != value)
     return true;
   }
  else
   for (; length > index; index++) {
    if ((IS_INCLUDES || index in O) && O[index] === el)
     return IS_INCLUDES || index || 0;
   }
  return !IS_INCLUDES && -1;
 };
};
module.exports = {
 includes: createMethod(true),
 indexOf: createMethod(false)
};

/***/ }),
/* 62 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toIntegerOrInfinity = __w_pdfjs_require__(63);
var max = Math.max;
var min = Math.min;
module.exports = function (index, length) {
 var integer = toIntegerOrInfinity(index);
 return integer < 0 ? max(integer + length, 0) : min(integer, length);
};

/***/ }),
/* 63 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var trunc = __w_pdfjs_require__(64);
module.exports = function (argument) {
 var number = +argument;
 return number !== number || number === 0 ? 0 : trunc(number);
};

/***/ }),
/* 64 */
/***/ ((module) => {

var ceil = Math.ceil;
var floor = Math.floor;
module.exports = Math.trunc || function trunc(x) {
 var n = +x;
 return (n > 0 ? floor : ceil)(n);
};

/***/ }),
/* 65 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toLength = __w_pdfjs_require__(66);
module.exports = function (obj) {
 return toLength(obj.length);
};

/***/ }),
/* 66 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toIntegerOrInfinity = __w_pdfjs_require__(63);
var min = Math.min;
module.exports = function (argument) {
 return argument > 0 ? min(toIntegerOrInfinity(argument), 0x1FFFFFFFFFFFFF) : 0;
};

/***/ }),
/* 67 */
/***/ ((module) => {

module.exports = [
 'constructor',
 'hasOwnProperty',
 'isPrototypeOf',
 'propertyIsEnumerable',
 'toLocaleString',
 'toString',
 'valueOf'
];

/***/ }),
/* 68 */
/***/ ((__unused_webpack_module, exports) => {

exports.f = Object.getOwnPropertySymbols;

/***/ }),
/* 69 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
var isCallable = __w_pdfjs_require__(23);
var replacement = /#|\.prototype\./;
var isForced = function (feature, detection) {
 var value = data[normalize(feature)];
 return value == POLYFILL ? true : value == NATIVE ? false : isCallable(detection) ? fails(detection) : !!detection;
};
var normalize = isForced.normalize = function (string) {
 return String(string).replace(replacement, '.').toLowerCase();
};
var data = isForced.data = {};
var NATIVE = isForced.NATIVE = 'N';
var POLYFILL = isForced.POLYFILL = 'P';
module.exports = isForced;

/***/ }),
/* 70 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var wellKnownSymbol = __w_pdfjs_require__(35);
var create = __w_pdfjs_require__(71);
var defineProperty = (__w_pdfjs_require__(46).f);
var UNSCOPABLES = wellKnownSymbol('unscopables');
var ArrayPrototype = Array.prototype;
if (ArrayPrototype[UNSCOPABLES] == undefined) {
 defineProperty(ArrayPrototype, UNSCOPABLES, {
  configurable: true,
  value: create(null)
 });
}
module.exports = function (key) {
 ArrayPrototype[UNSCOPABLES][key] = true;
};

/***/ }),
/* 71 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var anObject = __w_pdfjs_require__(48);
var definePropertiesModule = __w_pdfjs_require__(72);
var enumBugKeys = __w_pdfjs_require__(67);
var hiddenKeys = __w_pdfjs_require__(56);
var html = __w_pdfjs_require__(74);
var documentCreateElement = __w_pdfjs_require__(44);
var sharedKey = __w_pdfjs_require__(55);
var GT = '>';
var LT = '<';
var PROTOTYPE = 'prototype';
var SCRIPT = 'script';
var IE_PROTO = sharedKey('IE_PROTO');
var EmptyConstructor = function () {
};
var scriptTag = function (content) {
 return LT + SCRIPT + GT + content + LT + '/' + SCRIPT + GT;
};
var NullProtoObjectViaActiveX = function (activeXDocument) {
 activeXDocument.write(scriptTag(''));
 activeXDocument.close();
 var temp = activeXDocument.parentWindow.Object;
 activeXDocument = null;
 return temp;
};
var NullProtoObjectViaIFrame = function () {
 var iframe = documentCreateElement('iframe');
 var JS = 'java' + SCRIPT + ':';
 var iframeDocument;
 iframe.style.display = 'none';
 html.appendChild(iframe);
 iframe.src = String(JS);
 iframeDocument = iframe.contentWindow.document;
 iframeDocument.open();
 iframeDocument.write(scriptTag('document.F=Object'));
 iframeDocument.close();
 return iframeDocument.F;
};
var activeXDocument;
var NullProtoObject = function () {
 try {
  activeXDocument = new ActiveXObject('htmlfile');
 } catch (error) {
 }
 NullProtoObject = typeof document != 'undefined' ? document.domain && activeXDocument ? NullProtoObjectViaActiveX(activeXDocument) : NullProtoObjectViaIFrame() : NullProtoObjectViaActiveX(activeXDocument);
 var length = enumBugKeys.length;
 while (length--)
  delete NullProtoObject[PROTOTYPE][enumBugKeys[length]];
 return NullProtoObject();
};
hiddenKeys[IE_PROTO] = true;
module.exports = Object.create || function create(O, Properties) {
 var result;
 if (O !== null) {
  EmptyConstructor[PROTOTYPE] = anObject(O);
  result = new EmptyConstructor();
  EmptyConstructor[PROTOTYPE] = null;
  result[IE_PROTO] = O;
 } else
  result = NullProtoObject();
 return Properties === undefined ? result : definePropertiesModule.f(result, Properties);
};

/***/ }),
/* 72 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

var DESCRIPTORS = __w_pdfjs_require__(9);
var V8_PROTOTYPE_DEFINE_BUG = __w_pdfjs_require__(47);
var definePropertyModule = __w_pdfjs_require__(46);
var anObject = __w_pdfjs_require__(48);
var toIndexedObject = __w_pdfjs_require__(15);
var objectKeys = __w_pdfjs_require__(73);
exports.f = DESCRIPTORS && !V8_PROTOTYPE_DEFINE_BUG ? Object.defineProperties : function defineProperties(O, Properties) {
 anObject(O);
 var props = toIndexedObject(Properties);
 var keys = objectKeys(Properties);
 var length = keys.length;
 var index = 0;
 var key;
 while (length > index)
  definePropertyModule.f(O, key = keys[index++], props[key]);
 return O;
};

/***/ }),
/* 73 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var internalObjectKeys = __w_pdfjs_require__(60);
var enumBugKeys = __w_pdfjs_require__(67);
module.exports = Object.keys || function keys(O) {
 return internalObjectKeys(O, enumBugKeys);
};

/***/ }),
/* 74 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var getBuiltIn = __w_pdfjs_require__(25);
module.exports = getBuiltIn('document', 'documentElement');

/***/ }),
/* 75 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
var uncurryThis = __w_pdfjs_require__(17);
module.exports = function (CONSTRUCTOR, METHOD) {
 return uncurryThis(global[CONSTRUCTOR].prototype[METHOD]);
};

/***/ }),
/* 76 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

__w_pdfjs_require__(77);

/***/ }),
/* 77 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var ArrayBufferViewCore = __w_pdfjs_require__(78);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var toIntegerOrInfinity = __w_pdfjs_require__(63);
var aTypedArray = ArrayBufferViewCore.aTypedArray;
var exportTypedArrayMethod = ArrayBufferViewCore.exportTypedArrayMethod;
exportTypedArrayMethod('at', function at(index) {
 var O = aTypedArray(this);
 var len = lengthOfArrayLike(O);
 var relativeIndex = toIntegerOrInfinity(index);
 var k = relativeIndex >= 0 ? relativeIndex : len + relativeIndex;
 return k < 0 || k >= len ? undefined : O[k];
});

/***/ }),
/* 78 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var NATIVE_ARRAY_BUFFER = __w_pdfjs_require__(79);
var DESCRIPTORS = __w_pdfjs_require__(9);
var global = __w_pdfjs_require__(7);
var isCallable = __w_pdfjs_require__(23);
var isObject = __w_pdfjs_require__(22);
var hasOwn = __w_pdfjs_require__(40);
var classof = __w_pdfjs_require__(80);
var tryToString = __w_pdfjs_require__(33);
var createNonEnumerableProperty = __w_pdfjs_require__(45);
var defineBuiltIn = __w_pdfjs_require__(49);
var defineProperty = (__w_pdfjs_require__(46).f);
var isPrototypeOf = __w_pdfjs_require__(26);
var getPrototypeOf = __w_pdfjs_require__(82);
var setPrototypeOf = __w_pdfjs_require__(84);
var wellKnownSymbol = __w_pdfjs_require__(35);
var uid = __w_pdfjs_require__(42);
var InternalStateModule = __w_pdfjs_require__(53);
var enforceInternalState = InternalStateModule.enforce;
var getInternalState = InternalStateModule.get;
var Int8Array = global.Int8Array;
var Int8ArrayPrototype = Int8Array && Int8Array.prototype;
var Uint8ClampedArray = global.Uint8ClampedArray;
var Uint8ClampedArrayPrototype = Uint8ClampedArray && Uint8ClampedArray.prototype;
var TypedArray = Int8Array && getPrototypeOf(Int8Array);
var TypedArrayPrototype = Int8ArrayPrototype && getPrototypeOf(Int8ArrayPrototype);
var ObjectPrototype = Object.prototype;
var TypeError = global.TypeError;
var TO_STRING_TAG = wellKnownSymbol('toStringTag');
var TYPED_ARRAY_TAG = uid('TYPED_ARRAY_TAG');
var TYPED_ARRAY_CONSTRUCTOR = 'TypedArrayConstructor';
var NATIVE_ARRAY_BUFFER_VIEWS = NATIVE_ARRAY_BUFFER && !!setPrototypeOf && classof(global.opera) !== 'Opera';
var TYPED_ARRAY_TAG_REQUIRED = false;
var NAME, Constructor, Prototype;
var TypedArrayConstructorsList = {
 Int8Array: 1,
 Uint8Array: 1,
 Uint8ClampedArray: 1,
 Int16Array: 2,
 Uint16Array: 2,
 Int32Array: 4,
 Uint32Array: 4,
 Float32Array: 4,
 Float64Array: 8
};
var BigIntArrayConstructorsList = {
 BigInt64Array: 8,
 BigUint64Array: 8
};
var isView = function isView(it) {
 if (!isObject(it))
  return false;
 var klass = classof(it);
 return klass === 'DataView' || hasOwn(TypedArrayConstructorsList, klass) || hasOwn(BigIntArrayConstructorsList, klass);
};
var getTypedArrayConstructor = function (it) {
 var proto = getPrototypeOf(it);
 if (!isObject(proto))
  return;
 var state = getInternalState(proto);
 return state && hasOwn(state, TYPED_ARRAY_CONSTRUCTOR) ? state[TYPED_ARRAY_CONSTRUCTOR] : getTypedArrayConstructor(proto);
};
var isTypedArray = function (it) {
 if (!isObject(it))
  return false;
 var klass = classof(it);
 return hasOwn(TypedArrayConstructorsList, klass) || hasOwn(BigIntArrayConstructorsList, klass);
};
var aTypedArray = function (it) {
 if (isTypedArray(it))
  return it;
 throw TypeError('Target is not a typed array');
};
var aTypedArrayConstructor = function (C) {
 if (isCallable(C) && (!setPrototypeOf || isPrototypeOf(TypedArray, C)))
  return C;
 throw TypeError(tryToString(C) + ' is not a typed array constructor');
};
var exportTypedArrayMethod = function (KEY, property, forced, options) {
 if (!DESCRIPTORS)
  return;
 if (forced)
  for (var ARRAY in TypedArrayConstructorsList) {
   var TypedArrayConstructor = global[ARRAY];
   if (TypedArrayConstructor && hasOwn(TypedArrayConstructor.prototype, KEY))
    try {
     delete TypedArrayConstructor.prototype[KEY];
    } catch (error) {
     try {
      TypedArrayConstructor.prototype[KEY] = property;
     } catch (error2) {
     }
    }
  }
 if (!TypedArrayPrototype[KEY] || forced) {
  defineBuiltIn(TypedArrayPrototype, KEY, forced ? property : NATIVE_ARRAY_BUFFER_VIEWS && Int8ArrayPrototype[KEY] || property, options);
 }
};
var exportTypedArrayStaticMethod = function (KEY, property, forced) {
 var ARRAY, TypedArrayConstructor;
 if (!DESCRIPTORS)
  return;
 if (setPrototypeOf) {
  if (forced)
   for (ARRAY in TypedArrayConstructorsList) {
    TypedArrayConstructor = global[ARRAY];
    if (TypedArrayConstructor && hasOwn(TypedArrayConstructor, KEY))
     try {
      delete TypedArrayConstructor[KEY];
     } catch (error) {
     }
   }
  if (!TypedArray[KEY] || forced) {
   try {
    return defineBuiltIn(TypedArray, KEY, forced ? property : NATIVE_ARRAY_BUFFER_VIEWS && TypedArray[KEY] || property);
   } catch (error) {
   }
  } else
   return;
 }
 for (ARRAY in TypedArrayConstructorsList) {
  TypedArrayConstructor = global[ARRAY];
  if (TypedArrayConstructor && (!TypedArrayConstructor[KEY] || forced)) {
   defineBuiltIn(TypedArrayConstructor, KEY, property);
  }
 }
};
for (NAME in TypedArrayConstructorsList) {
 Constructor = global[NAME];
 Prototype = Constructor && Constructor.prototype;
 if (Prototype)
  enforceInternalState(Prototype)[TYPED_ARRAY_CONSTRUCTOR] = Constructor;
 else
  NATIVE_ARRAY_BUFFER_VIEWS = false;
}
for (NAME in BigIntArrayConstructorsList) {
 Constructor = global[NAME];
 Prototype = Constructor && Constructor.prototype;
 if (Prototype)
  enforceInternalState(Prototype)[TYPED_ARRAY_CONSTRUCTOR] = Constructor;
}
if (!NATIVE_ARRAY_BUFFER_VIEWS || !isCallable(TypedArray) || TypedArray === Function.prototype) {
 TypedArray = function TypedArray() {
  throw TypeError('Incorrect invocation');
 };
 if (NATIVE_ARRAY_BUFFER_VIEWS)
  for (NAME in TypedArrayConstructorsList) {
   if (global[NAME])
    setPrototypeOf(global[NAME], TypedArray);
  }
}
if (!NATIVE_ARRAY_BUFFER_VIEWS || !TypedArrayPrototype || TypedArrayPrototype === ObjectPrototype) {
 TypedArrayPrototype = TypedArray.prototype;
 if (NATIVE_ARRAY_BUFFER_VIEWS)
  for (NAME in TypedArrayConstructorsList) {
   if (global[NAME])
    setPrototypeOf(global[NAME].prototype, TypedArrayPrototype);
  }
}
if (NATIVE_ARRAY_BUFFER_VIEWS && getPrototypeOf(Uint8ClampedArrayPrototype) !== TypedArrayPrototype) {
 setPrototypeOf(Uint8ClampedArrayPrototype, TypedArrayPrototype);
}
if (DESCRIPTORS && !hasOwn(TypedArrayPrototype, TO_STRING_TAG)) {
 TYPED_ARRAY_TAG_REQUIRED = true;
 defineProperty(TypedArrayPrototype, TO_STRING_TAG, {
  get: function () {
   return isObject(this) ? this[TYPED_ARRAY_TAG] : undefined;
  }
 });
 for (NAME in TypedArrayConstructorsList)
  if (global[NAME]) {
   createNonEnumerableProperty(global[NAME], TYPED_ARRAY_TAG, NAME);
  }
}
module.exports = {
 NATIVE_ARRAY_BUFFER_VIEWS: NATIVE_ARRAY_BUFFER_VIEWS,
 TYPED_ARRAY_TAG: TYPED_ARRAY_TAG_REQUIRED && TYPED_ARRAY_TAG,
 aTypedArray: aTypedArray,
 aTypedArrayConstructor: aTypedArrayConstructor,
 exportTypedArrayMethod: exportTypedArrayMethod,
 exportTypedArrayStaticMethod: exportTypedArrayStaticMethod,
 getTypedArrayConstructor: getTypedArrayConstructor,
 isView: isView,
 isTypedArray: isTypedArray,
 TypedArray: TypedArray,
 TypedArrayPrototype: TypedArrayPrototype
};

/***/ }),
/* 79 */
/***/ ((module) => {

module.exports = typeof ArrayBuffer != 'undefined' && typeof DataView != 'undefined';

/***/ }),
/* 80 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var TO_STRING_TAG_SUPPORT = __w_pdfjs_require__(81);
var isCallable = __w_pdfjs_require__(23);
var classofRaw = __w_pdfjs_require__(18);
var wellKnownSymbol = __w_pdfjs_require__(35);
var TO_STRING_TAG = wellKnownSymbol('toStringTag');
var $Object = Object;
var CORRECT_ARGUMENTS = classofRaw((function () {
 return arguments;
}())) == 'Arguments';
var tryGet = function (it, key) {
 try {
  return it[key];
 } catch (error) {
 }
};
module.exports = TO_STRING_TAG_SUPPORT ? classofRaw : function (it) {
 var O, tag, result;
 return it === undefined ? 'Undefined' : it === null ? 'Null' : typeof (tag = tryGet(O = $Object(it), TO_STRING_TAG)) == 'string' ? tag : CORRECT_ARGUMENTS ? classofRaw(O) : (result = classofRaw(O)) == 'Object' && isCallable(O.callee) ? 'Arguments' : result;
};

/***/ }),
/* 81 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var wellKnownSymbol = __w_pdfjs_require__(35);
var TO_STRING_TAG = wellKnownSymbol('toStringTag');
var test = {};
test[TO_STRING_TAG] = 'z';
module.exports = String(test) === '[object z]';

/***/ }),
/* 82 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var hasOwn = __w_pdfjs_require__(40);
var isCallable = __w_pdfjs_require__(23);
var toObject = __w_pdfjs_require__(41);
var sharedKey = __w_pdfjs_require__(55);
var CORRECT_PROTOTYPE_GETTER = __w_pdfjs_require__(83);
var IE_PROTO = sharedKey('IE_PROTO');
var $Object = Object;
var ObjectPrototype = $Object.prototype;
module.exports = CORRECT_PROTOTYPE_GETTER ? $Object.getPrototypeOf : function (O) {
 var object = toObject(O);
 if (hasOwn(object, IE_PROTO))
  return object[IE_PROTO];
 var constructor = object.constructor;
 if (isCallable(constructor) && object instanceof constructor) {
  return constructor.prototype;
 }
 return object instanceof $Object ? ObjectPrototype : null;
};

/***/ }),
/* 83 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
module.exports = !fails(function () {
 function F() {
 }
 F.prototype.constructor = null;
 return Object.getPrototypeOf(new F()) !== F.prototype;
});

/***/ }),
/* 84 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var anObject = __w_pdfjs_require__(48);
var aPossiblePrototype = __w_pdfjs_require__(85);
module.exports = Object.setPrototypeOf || ('__proto__' in {} ? (function () {
 var CORRECT_SETTER = false;
 var test = {};
 var setter;
 try {
  setter = uncurryThis(Object.getOwnPropertyDescriptor(Object.prototype, '__proto__').set);
  setter(test, []);
  CORRECT_SETTER = test instanceof Array;
 } catch (error) {
 }
 return function setPrototypeOf(O, proto) {
  anObject(O);
  aPossiblePrototype(proto);
  if (CORRECT_SETTER)
   setter(O, proto);
  else
   O.__proto__ = proto;
  return O;
 };
}()) : undefined);

/***/ }),
/* 85 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isCallable = __w_pdfjs_require__(23);
var $String = String;
var $TypeError = TypeError;
module.exports = function (argument) {
 if (typeof argument == 'object' || isCallable(argument))
  return argument;
 throw $TypeError("Can't set " + $String(argument) + ' as a prototype');
};

/***/ }),
/* 86 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

__w_pdfjs_require__(87);
__w_pdfjs_require__(93);
__w_pdfjs_require__(95);
__w_pdfjs_require__(117);
__w_pdfjs_require__(119);
var path = __w_pdfjs_require__(128);
module.exports = path.structuredClone;

/***/ }),
/* 87 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var toIndexedObject = __w_pdfjs_require__(15);
var addToUnscopables = __w_pdfjs_require__(70);
var Iterators = __w_pdfjs_require__(88);
var InternalStateModule = __w_pdfjs_require__(53);
var defineProperty = (__w_pdfjs_require__(46).f);
var defineIterator = __w_pdfjs_require__(89);
var IS_PURE = __w_pdfjs_require__(37);
var DESCRIPTORS = __w_pdfjs_require__(9);
var ARRAY_ITERATOR = 'Array Iterator';
var setInternalState = InternalStateModule.set;
var getInternalState = InternalStateModule.getterFor(ARRAY_ITERATOR);
module.exports = defineIterator(Array, 'Array', function (iterated, kind) {
 setInternalState(this, {
  type: ARRAY_ITERATOR,
  target: toIndexedObject(iterated),
  index: 0,
  kind: kind
 });
}, function () {
 var state = getInternalState(this);
 var target = state.target;
 var kind = state.kind;
 var index = state.index++;
 if (!target || index >= target.length) {
  state.target = undefined;
  return {
   value: undefined,
   done: true
  };
 }
 if (kind == 'keys')
  return {
   value: index,
   done: false
  };
 if (kind == 'values')
  return {
   value: target[index],
   done: false
  };
 return {
  value: [
   index,
   target[index]
  ],
  done: false
 };
}, 'values');
var values = Iterators.Arguments = Iterators.Array;
addToUnscopables('keys');
addToUnscopables('values');
addToUnscopables('entries');
if (!IS_PURE && DESCRIPTORS && values.name !== 'values')
 try {
  defineProperty(values, 'name', { value: 'values' });
 } catch (error) {
 }

/***/ }),
/* 88 */
/***/ ((module) => {

module.exports = {};

/***/ }),
/* 89 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var $ = __w_pdfjs_require__(6);
var call = __w_pdfjs_require__(11);
var IS_PURE = __w_pdfjs_require__(37);
var FunctionName = __w_pdfjs_require__(51);
var isCallable = __w_pdfjs_require__(23);
var createIteratorConstructor = __w_pdfjs_require__(90);
var getPrototypeOf = __w_pdfjs_require__(82);
var setPrototypeOf = __w_pdfjs_require__(84);
var setToStringTag = __w_pdfjs_require__(92);
var createNonEnumerableProperty = __w_pdfjs_require__(45);
var defineBuiltIn = __w_pdfjs_require__(49);
var wellKnownSymbol = __w_pdfjs_require__(35);
var Iterators = __w_pdfjs_require__(88);
var IteratorsCore = __w_pdfjs_require__(91);
var PROPER_FUNCTION_NAME = FunctionName.PROPER;
var CONFIGURABLE_FUNCTION_NAME = FunctionName.CONFIGURABLE;
var IteratorPrototype = IteratorsCore.IteratorPrototype;
var BUGGY_SAFARI_ITERATORS = IteratorsCore.BUGGY_SAFARI_ITERATORS;
var ITERATOR = wellKnownSymbol('iterator');
var KEYS = 'keys';
var VALUES = 'values';
var ENTRIES = 'entries';
var returnThis = function () {
 return this;
};
module.exports = function (Iterable, NAME, IteratorConstructor, next, DEFAULT, IS_SET, FORCED) {
 createIteratorConstructor(IteratorConstructor, NAME, next);
 var getIterationMethod = function (KIND) {
  if (KIND === DEFAULT && defaultIterator)
   return defaultIterator;
  if (!BUGGY_SAFARI_ITERATORS && KIND in IterablePrototype)
   return IterablePrototype[KIND];
  switch (KIND) {
  case KEYS:
   return function keys() {
    return new IteratorConstructor(this, KIND);
   };
  case VALUES:
   return function values() {
    return new IteratorConstructor(this, KIND);
   };
  case ENTRIES:
   return function entries() {
    return new IteratorConstructor(this, KIND);
   };
  }
  return function () {
   return new IteratorConstructor(this);
  };
 };
 var TO_STRING_TAG = NAME + ' Iterator';
 var INCORRECT_VALUES_NAME = false;
 var IterablePrototype = Iterable.prototype;
 var nativeIterator = IterablePrototype[ITERATOR] || IterablePrototype['@@iterator'] || DEFAULT && IterablePrototype[DEFAULT];
 var defaultIterator = !BUGGY_SAFARI_ITERATORS && nativeIterator || getIterationMethod(DEFAULT);
 var anyNativeIterator = NAME == 'Array' ? IterablePrototype.entries || nativeIterator : nativeIterator;
 var CurrentIteratorPrototype, methods, KEY;
 if (anyNativeIterator) {
  CurrentIteratorPrototype = getPrototypeOf(anyNativeIterator.call(new Iterable()));
  if (CurrentIteratorPrototype !== Object.prototype && CurrentIteratorPrototype.next) {
   if (!IS_PURE && getPrototypeOf(CurrentIteratorPrototype) !== IteratorPrototype) {
    if (setPrototypeOf) {
     setPrototypeOf(CurrentIteratorPrototype, IteratorPrototype);
    } else if (!isCallable(CurrentIteratorPrototype[ITERATOR])) {
     defineBuiltIn(CurrentIteratorPrototype, ITERATOR, returnThis);
    }
   }
   setToStringTag(CurrentIteratorPrototype, TO_STRING_TAG, true, true);
   if (IS_PURE)
    Iterators[TO_STRING_TAG] = returnThis;
  }
 }
 if (PROPER_FUNCTION_NAME && DEFAULT == VALUES && nativeIterator && nativeIterator.name !== VALUES) {
  if (!IS_PURE && CONFIGURABLE_FUNCTION_NAME) {
   createNonEnumerableProperty(IterablePrototype, 'name', VALUES);
  } else {
   INCORRECT_VALUES_NAME = true;
   defaultIterator = function values() {
    return call(nativeIterator, this);
   };
  }
 }
 if (DEFAULT) {
  methods = {
   values: getIterationMethod(VALUES),
   keys: IS_SET ? defaultIterator : getIterationMethod(KEYS),
   entries: getIterationMethod(ENTRIES)
  };
  if (FORCED)
   for (KEY in methods) {
    if (BUGGY_SAFARI_ITERATORS || INCORRECT_VALUES_NAME || !(KEY in IterablePrototype)) {
     defineBuiltIn(IterablePrototype, KEY, methods[KEY]);
    }
   }
  else
   $({
    target: NAME,
    proto: true,
    forced: BUGGY_SAFARI_ITERATORS || INCORRECT_VALUES_NAME
   }, methods);
 }
 if ((!IS_PURE || FORCED) && IterablePrototype[ITERATOR] !== defaultIterator) {
  defineBuiltIn(IterablePrototype, ITERATOR, defaultIterator, { name: DEFAULT });
 }
 Iterators[NAME] = defaultIterator;
 return methods;
};

/***/ }),
/* 90 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var IteratorPrototype = (__w_pdfjs_require__(91).IteratorPrototype);
var create = __w_pdfjs_require__(71);
var createPropertyDescriptor = __w_pdfjs_require__(14);
var setToStringTag = __w_pdfjs_require__(92);
var Iterators = __w_pdfjs_require__(88);
var returnThis = function () {
 return this;
};
module.exports = function (IteratorConstructor, NAME, next, ENUMERABLE_NEXT) {
 var TO_STRING_TAG = NAME + ' Iterator';
 IteratorConstructor.prototype = create(IteratorPrototype, { next: createPropertyDescriptor(+!ENUMERABLE_NEXT, next) });
 setToStringTag(IteratorConstructor, TO_STRING_TAG, false, true);
 Iterators[TO_STRING_TAG] = returnThis;
 return IteratorConstructor;
};

/***/ }),
/* 91 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var fails = __w_pdfjs_require__(10);
var isCallable = __w_pdfjs_require__(23);
var create = __w_pdfjs_require__(71);
var getPrototypeOf = __w_pdfjs_require__(82);
var defineBuiltIn = __w_pdfjs_require__(49);
var wellKnownSymbol = __w_pdfjs_require__(35);
var IS_PURE = __w_pdfjs_require__(37);
var ITERATOR = wellKnownSymbol('iterator');
var BUGGY_SAFARI_ITERATORS = false;
var IteratorPrototype, PrototypeOfArrayIteratorPrototype, arrayIterator;
if ([].keys) {
 arrayIterator = [].keys();
 if (!('next' in arrayIterator))
  BUGGY_SAFARI_ITERATORS = true;
 else {
  PrototypeOfArrayIteratorPrototype = getPrototypeOf(getPrototypeOf(arrayIterator));
  if (PrototypeOfArrayIteratorPrototype !== Object.prototype)
   IteratorPrototype = PrototypeOfArrayIteratorPrototype;
 }
}
var NEW_ITERATOR_PROTOTYPE = IteratorPrototype == undefined || fails(function () {
 var test = {};
 return IteratorPrototype[ITERATOR].call(test) !== test;
});
if (NEW_ITERATOR_PROTOTYPE)
 IteratorPrototype = {};
else if (IS_PURE)
 IteratorPrototype = create(IteratorPrototype);
if (!isCallable(IteratorPrototype[ITERATOR])) {
 defineBuiltIn(IteratorPrototype, ITERATOR, function () {
  return this;
 });
}
module.exports = {
 IteratorPrototype: IteratorPrototype,
 BUGGY_SAFARI_ITERATORS: BUGGY_SAFARI_ITERATORS
};

/***/ }),
/* 92 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var defineProperty = (__w_pdfjs_require__(46).f);
var hasOwn = __w_pdfjs_require__(40);
var wellKnownSymbol = __w_pdfjs_require__(35);
var TO_STRING_TAG = wellKnownSymbol('toStringTag');
module.exports = function (target, TAG, STATIC) {
 if (target && !STATIC)
  target = target.prototype;
 if (target && !hasOwn(target, TO_STRING_TAG)) {
  defineProperty(target, TO_STRING_TAG, {
   configurable: true,
   value: TAG
  });
 }
};

/***/ }),
/* 93 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

var TO_STRING_TAG_SUPPORT = __w_pdfjs_require__(81);
var defineBuiltIn = __w_pdfjs_require__(49);
var toString = __w_pdfjs_require__(94);
if (!TO_STRING_TAG_SUPPORT) {
 defineBuiltIn(Object.prototype, 'toString', toString, { unsafe: true });
}

/***/ }),
/* 94 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var TO_STRING_TAG_SUPPORT = __w_pdfjs_require__(81);
var classof = __w_pdfjs_require__(80);
module.exports = TO_STRING_TAG_SUPPORT ? {}.toString : function toString() {
 return '[object ' + classof(this) + ']';
};

/***/ }),
/* 95 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

__w_pdfjs_require__(96);

/***/ }),
/* 96 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var collection = __w_pdfjs_require__(97);
var collectionStrong = __w_pdfjs_require__(114);
collection('Map', function (init) {
 return function Map() {
  return init(this, arguments.length ? arguments[0] : undefined);
 };
}, collectionStrong);

/***/ }),
/* 97 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var $ = __w_pdfjs_require__(6);
var global = __w_pdfjs_require__(7);
var uncurryThis = __w_pdfjs_require__(17);
var isForced = __w_pdfjs_require__(69);
var defineBuiltIn = __w_pdfjs_require__(49);
var InternalMetadataModule = __w_pdfjs_require__(98);
var iterate = __w_pdfjs_require__(105);
var anInstance = __w_pdfjs_require__(111);
var isCallable = __w_pdfjs_require__(23);
var isObject = __w_pdfjs_require__(22);
var fails = __w_pdfjs_require__(10);
var checkCorrectnessOfIteration = __w_pdfjs_require__(112);
var setToStringTag = __w_pdfjs_require__(92);
var inheritIfRequired = __w_pdfjs_require__(113);
module.exports = function (CONSTRUCTOR_NAME, wrapper, common) {
 var IS_MAP = CONSTRUCTOR_NAME.indexOf('Map') !== -1;
 var IS_WEAK = CONSTRUCTOR_NAME.indexOf('Weak') !== -1;
 var ADDER = IS_MAP ? 'set' : 'add';
 var NativeConstructor = global[CONSTRUCTOR_NAME];
 var NativePrototype = NativeConstructor && NativeConstructor.prototype;
 var Constructor = NativeConstructor;
 var exported = {};
 var fixMethod = function (KEY) {
  var uncurriedNativeMethod = uncurryThis(NativePrototype[KEY]);
  defineBuiltIn(NativePrototype, KEY, KEY == 'add' ? function add(value) {
   uncurriedNativeMethod(this, value === 0 ? 0 : value);
   return this;
  } : KEY == 'delete' ? function (key) {
   return IS_WEAK && !isObject(key) ? false : uncurriedNativeMethod(this, key === 0 ? 0 : key);
  } : KEY == 'get' ? function get(key) {
   return IS_WEAK && !isObject(key) ? undefined : uncurriedNativeMethod(this, key === 0 ? 0 : key);
  } : KEY == 'has' ? function has(key) {
   return IS_WEAK && !isObject(key) ? false : uncurriedNativeMethod(this, key === 0 ? 0 : key);
  } : function set(key, value) {
   uncurriedNativeMethod(this, key === 0 ? 0 : key, value);
   return this;
  });
 };
 var REPLACE = isForced(CONSTRUCTOR_NAME, !isCallable(NativeConstructor) || !(IS_WEAK || NativePrototype.forEach && !fails(function () {
  new NativeConstructor().entries().next();
 })));
 if (REPLACE) {
  Constructor = common.getConstructor(wrapper, CONSTRUCTOR_NAME, IS_MAP, ADDER);
  InternalMetadataModule.enable();
 } else if (isForced(CONSTRUCTOR_NAME, true)) {
  var instance = new Constructor();
  var HASNT_CHAINING = instance[ADDER](IS_WEAK ? {} : -0, 1) != instance;
  var THROWS_ON_PRIMITIVES = fails(function () {
   instance.has(1);
  });
  var ACCEPT_ITERABLES = checkCorrectnessOfIteration(function (iterable) {
   new NativeConstructor(iterable);
  });
  var BUGGY_ZERO = !IS_WEAK && fails(function () {
   var $instance = new NativeConstructor();
   var index = 5;
   while (index--)
    $instance[ADDER](index, index);
   return !$instance.has(-0);
  });
  if (!ACCEPT_ITERABLES) {
   Constructor = wrapper(function (dummy, iterable) {
    anInstance(dummy, NativePrototype);
    var that = inheritIfRequired(new NativeConstructor(), dummy, Constructor);
    if (iterable != undefined)
     iterate(iterable, that[ADDER], {
      that: that,
      AS_ENTRIES: IS_MAP
     });
    return that;
   });
   Constructor.prototype = NativePrototype;
   NativePrototype.constructor = Constructor;
  }
  if (THROWS_ON_PRIMITIVES || BUGGY_ZERO) {
   fixMethod('delete');
   fixMethod('has');
   IS_MAP && fixMethod('get');
  }
  if (BUGGY_ZERO || HASNT_CHAINING)
   fixMethod(ADDER);
  if (IS_WEAK && NativePrototype.clear)
   delete NativePrototype.clear;
 }
 exported[CONSTRUCTOR_NAME] = Constructor;
 $({
  global: true,
  constructor: true,
  forced: Constructor != NativeConstructor
 }, exported);
 setToStringTag(Constructor, CONSTRUCTOR_NAME);
 if (!IS_WEAK)
  common.setStrong(Constructor, CONSTRUCTOR_NAME, IS_MAP);
 return Constructor;
};

/***/ }),
/* 98 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var $ = __w_pdfjs_require__(6);
var uncurryThis = __w_pdfjs_require__(17);
var hiddenKeys = __w_pdfjs_require__(56);
var isObject = __w_pdfjs_require__(22);
var hasOwn = __w_pdfjs_require__(40);
var defineProperty = (__w_pdfjs_require__(46).f);
var getOwnPropertyNamesModule = __w_pdfjs_require__(59);
var getOwnPropertyNamesExternalModule = __w_pdfjs_require__(99);
var isExtensible = __w_pdfjs_require__(102);
var uid = __w_pdfjs_require__(42);
var FREEZING = __w_pdfjs_require__(104);
var REQUIRED = false;
var METADATA = uid('meta');
var id = 0;
var setMetadata = function (it) {
 defineProperty(it, METADATA, {
  value: {
   objectID: 'O' + id++,
   weakData: {}
  }
 });
};
var fastKey = function (it, create) {
 if (!isObject(it))
  return typeof it == 'symbol' ? it : (typeof it == 'string' ? 'S' : 'P') + it;
 if (!hasOwn(it, METADATA)) {
  if (!isExtensible(it))
   return 'F';
  if (!create)
   return 'E';
  setMetadata(it);
 }
 return it[METADATA].objectID;
};
var getWeakData = function (it, create) {
 if (!hasOwn(it, METADATA)) {
  if (!isExtensible(it))
   return true;
  if (!create)
   return false;
  setMetadata(it);
 }
 return it[METADATA].weakData;
};
var onFreeze = function (it) {
 if (FREEZING && REQUIRED && isExtensible(it) && !hasOwn(it, METADATA))
  setMetadata(it);
 return it;
};
var enable = function () {
 meta.enable = function () {
 };
 REQUIRED = true;
 var getOwnPropertyNames = getOwnPropertyNamesModule.f;
 var splice = uncurryThis([].splice);
 var test = {};
 test[METADATA] = 1;
 if (getOwnPropertyNames(test).length) {
  getOwnPropertyNamesModule.f = function (it) {
   var result = getOwnPropertyNames(it);
   for (var i = 0, length = result.length; i < length; i++) {
    if (result[i] === METADATA) {
     splice(result, i, 1);
     break;
    }
   }
   return result;
  };
  $({
   target: 'Object',
   stat: true,
   forced: true
  }, { getOwnPropertyNames: getOwnPropertyNamesExternalModule.f });
 }
};
var meta = module.exports = {
 enable: enable,
 fastKey: fastKey,
 getWeakData: getWeakData,
 onFreeze: onFreeze
};
hiddenKeys[METADATA] = true;

/***/ }),
/* 99 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var classof = __w_pdfjs_require__(18);
var toIndexedObject = __w_pdfjs_require__(15);
var $getOwnPropertyNames = (__w_pdfjs_require__(59).f);
var arraySlice = __w_pdfjs_require__(100);
var windowNames = typeof window == 'object' && window && Object.getOwnPropertyNames ? Object.getOwnPropertyNames(window) : [];
var getWindowNames = function (it) {
 try {
  return $getOwnPropertyNames(it);
 } catch (error) {
  return arraySlice(windowNames);
 }
};
module.exports.f = function getOwnPropertyNames(it) {
 return windowNames && classof(it) == 'Window' ? getWindowNames(it) : $getOwnPropertyNames(toIndexedObject(it));
};

/***/ }),
/* 100 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var toAbsoluteIndex = __w_pdfjs_require__(62);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var createProperty = __w_pdfjs_require__(101);
var $Array = Array;
var max = Math.max;
module.exports = function (O, start, end) {
 var length = lengthOfArrayLike(O);
 var k = toAbsoluteIndex(start, length);
 var fin = toAbsoluteIndex(end === undefined ? length : end, length);
 var result = $Array(max(fin - k, 0));
 for (var n = 0; k < fin; k++, n++)
  createProperty(result, n, O[k]);
 result.length = n;
 return result;
};

/***/ }),
/* 101 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var toPropertyKey = __w_pdfjs_require__(20);
var definePropertyModule = __w_pdfjs_require__(46);
var createPropertyDescriptor = __w_pdfjs_require__(14);
module.exports = function (object, key, value) {
 var propertyKey = toPropertyKey(key);
 if (propertyKey in object)
  definePropertyModule.f(object, propertyKey, createPropertyDescriptor(0, value));
 else
  object[propertyKey] = value;
};

/***/ }),
/* 102 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
var isObject = __w_pdfjs_require__(22);
var classof = __w_pdfjs_require__(18);
var ARRAY_BUFFER_NON_EXTENSIBLE = __w_pdfjs_require__(103);
var $isExtensible = Object.isExtensible;
var FAILS_ON_PRIMITIVES = fails(function () {
 $isExtensible(1);
});
module.exports = FAILS_ON_PRIMITIVES || ARRAY_BUFFER_NON_EXTENSIBLE ? function isExtensible(it) {
 if (!isObject(it))
  return false;
 if (ARRAY_BUFFER_NON_EXTENSIBLE && classof(it) == 'ArrayBuffer')
  return false;
 return $isExtensible ? $isExtensible(it) : true;
} : $isExtensible;

/***/ }),
/* 103 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
module.exports = fails(function () {
 if (typeof ArrayBuffer == 'function') {
  var buffer = new ArrayBuffer(8);
  if (Object.isExtensible(buffer))
   Object.defineProperty(buffer, 'a', { value: 8 });
 }
});

/***/ }),
/* 104 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
module.exports = !fails(function () {
 return Object.isExtensible(Object.preventExtensions({}));
});

/***/ }),
/* 105 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var bind = __w_pdfjs_require__(106);
var call = __w_pdfjs_require__(11);
var anObject = __w_pdfjs_require__(48);
var tryToString = __w_pdfjs_require__(33);
var isArrayIteratorMethod = __w_pdfjs_require__(107);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var isPrototypeOf = __w_pdfjs_require__(26);
var getIterator = __w_pdfjs_require__(108);
var getIteratorMethod = __w_pdfjs_require__(109);
var iteratorClose = __w_pdfjs_require__(110);
var $TypeError = TypeError;
var Result = function (stopped, result) {
 this.stopped = stopped;
 this.result = result;
};
var ResultPrototype = Result.prototype;
module.exports = function (iterable, unboundFunction, options) {
 var that = options && options.that;
 var AS_ENTRIES = !!(options && options.AS_ENTRIES);
 var IS_RECORD = !!(options && options.IS_RECORD);
 var IS_ITERATOR = !!(options && options.IS_ITERATOR);
 var INTERRUPTED = !!(options && options.INTERRUPTED);
 var fn = bind(unboundFunction, that);
 var iterator, iterFn, index, length, result, next, step;
 var stop = function (condition) {
  if (iterator)
   iteratorClose(iterator, 'normal', condition);
  return new Result(true, condition);
 };
 var callFn = function (value) {
  if (AS_ENTRIES) {
   anObject(value);
   return INTERRUPTED ? fn(value[0], value[1], stop) : fn(value[0], value[1]);
  }
  return INTERRUPTED ? fn(value, stop) : fn(value);
 };
 if (IS_RECORD) {
  iterator = iterable.iterator;
 } else if (IS_ITERATOR) {
  iterator = iterable;
 } else {
  iterFn = getIteratorMethod(iterable);
  if (!iterFn)
   throw $TypeError(tryToString(iterable) + ' is not iterable');
  if (isArrayIteratorMethod(iterFn)) {
   for (index = 0, length = lengthOfArrayLike(iterable); length > index; index++) {
    result = callFn(iterable[index]);
    if (result && isPrototypeOf(ResultPrototype, result))
     return result;
   }
   return new Result(false);
  }
  iterator = getIterator(iterable, iterFn);
 }
 next = IS_RECORD ? iterable.next : iterator.next;
 while (!(step = call(next, iterator)).done) {
  try {
   result = callFn(step.value);
  } catch (error) {
   iteratorClose(iterator, 'throw', error);
  }
  if (typeof result == 'object' && result && isPrototypeOf(ResultPrototype, result))
   return result;
 }
 return new Result(false);
};

/***/ }),
/* 106 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var aCallable = __w_pdfjs_require__(32);
var NATIVE_BIND = __w_pdfjs_require__(12);
var bind = uncurryThis(uncurryThis.bind);
module.exports = function (fn, that) {
 aCallable(fn);
 return that === undefined ? fn : NATIVE_BIND ? bind(fn, that) : function () {
  return fn.apply(that, arguments);
 };
};

/***/ }),
/* 107 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var wellKnownSymbol = __w_pdfjs_require__(35);
var Iterators = __w_pdfjs_require__(88);
var ITERATOR = wellKnownSymbol('iterator');
var ArrayPrototype = Array.prototype;
module.exports = function (it) {
 return it !== undefined && (Iterators.Array === it || ArrayPrototype[ITERATOR] === it);
};

/***/ }),
/* 108 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var call = __w_pdfjs_require__(11);
var aCallable = __w_pdfjs_require__(32);
var anObject = __w_pdfjs_require__(48);
var tryToString = __w_pdfjs_require__(33);
var getIteratorMethod = __w_pdfjs_require__(109);
var $TypeError = TypeError;
module.exports = function (argument, usingIterator) {
 var iteratorMethod = arguments.length < 2 ? getIteratorMethod(argument) : usingIterator;
 if (aCallable(iteratorMethod))
  return anObject(call(iteratorMethod, argument));
 throw $TypeError(tryToString(argument) + ' is not iterable');
};

/***/ }),
/* 109 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var classof = __w_pdfjs_require__(80);
var getMethod = __w_pdfjs_require__(31);
var Iterators = __w_pdfjs_require__(88);
var wellKnownSymbol = __w_pdfjs_require__(35);
var ITERATOR = wellKnownSymbol('iterator');
module.exports = function (it) {
 if (it != undefined)
  return getMethod(it, ITERATOR) || getMethod(it, '@@iterator') || Iterators[classof(it)];
};

/***/ }),
/* 110 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var call = __w_pdfjs_require__(11);
var anObject = __w_pdfjs_require__(48);
var getMethod = __w_pdfjs_require__(31);
module.exports = function (iterator, kind, value) {
 var innerResult, innerError;
 anObject(iterator);
 try {
  innerResult = getMethod(iterator, 'return');
  if (!innerResult) {
   if (kind === 'throw')
    throw value;
   return value;
  }
  innerResult = call(innerResult, iterator);
 } catch (error) {
  innerError = true;
  innerResult = error;
 }
 if (kind === 'throw')
  throw value;
 if (innerError)
  throw innerResult;
 anObject(innerResult);
 return value;
};

/***/ }),
/* 111 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isPrototypeOf = __w_pdfjs_require__(26);
var $TypeError = TypeError;
module.exports = function (it, Prototype) {
 if (isPrototypeOf(Prototype, it))
  return it;
 throw $TypeError('Incorrect invocation');
};

/***/ }),
/* 112 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var wellKnownSymbol = __w_pdfjs_require__(35);
var ITERATOR = wellKnownSymbol('iterator');
var SAFE_CLOSING = false;
try {
 var called = 0;
 var iteratorWithReturn = {
  next: function () {
   return { done: !!called++ };
  },
  'return': function () {
   SAFE_CLOSING = true;
  }
 };
 iteratorWithReturn[ITERATOR] = function () {
  return this;
 };
 Array.from(iteratorWithReturn, function () {
  throw 2;
 });
} catch (error) {
}
module.exports = function (exec, SKIP_CLOSING) {
 if (!SKIP_CLOSING && !SAFE_CLOSING)
  return false;
 var ITERATION_SUPPORT = false;
 try {
  var object = {};
  object[ITERATOR] = function () {
   return {
    next: function () {
     return { done: ITERATION_SUPPORT = true };
    }
   };
  };
  exec(object);
 } catch (error) {
 }
 return ITERATION_SUPPORT;
};

/***/ }),
/* 113 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var isCallable = __w_pdfjs_require__(23);
var isObject = __w_pdfjs_require__(22);
var setPrototypeOf = __w_pdfjs_require__(84);
module.exports = function ($this, dummy, Wrapper) {
 var NewTarget, NewTargetPrototype;
 if (setPrototypeOf && isCallable(NewTarget = dummy.constructor) && NewTarget !== Wrapper && isObject(NewTargetPrototype = NewTarget.prototype) && NewTargetPrototype !== Wrapper.prototype)
  setPrototypeOf($this, NewTargetPrototype);
 return $this;
};

/***/ }),
/* 114 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var defineProperty = (__w_pdfjs_require__(46).f);
var create = __w_pdfjs_require__(71);
var defineBuiltIns = __w_pdfjs_require__(115);
var bind = __w_pdfjs_require__(106);
var anInstance = __w_pdfjs_require__(111);
var iterate = __w_pdfjs_require__(105);
var defineIterator = __w_pdfjs_require__(89);
var setSpecies = __w_pdfjs_require__(116);
var DESCRIPTORS = __w_pdfjs_require__(9);
var fastKey = (__w_pdfjs_require__(98).fastKey);
var InternalStateModule = __w_pdfjs_require__(53);
var setInternalState = InternalStateModule.set;
var internalStateGetterFor = InternalStateModule.getterFor;
module.exports = {
 getConstructor: function (wrapper, CONSTRUCTOR_NAME, IS_MAP, ADDER) {
  var Constructor = wrapper(function (that, iterable) {
   anInstance(that, Prototype);
   setInternalState(that, {
    type: CONSTRUCTOR_NAME,
    index: create(null),
    first: undefined,
    last: undefined,
    size: 0
   });
   if (!DESCRIPTORS)
    that.size = 0;
   if (iterable != undefined)
    iterate(iterable, that[ADDER], {
     that: that,
     AS_ENTRIES: IS_MAP
    });
  });
  var Prototype = Constructor.prototype;
  var getInternalState = internalStateGetterFor(CONSTRUCTOR_NAME);
  var define = function (that, key, value) {
   var state = getInternalState(that);
   var entry = getEntry(that, key);
   var previous, index;
   if (entry) {
    entry.value = value;
   } else {
    state.last = entry = {
     index: index = fastKey(key, true),
     key: key,
     value: value,
     previous: previous = state.last,
     next: undefined,
     removed: false
    };
    if (!state.first)
     state.first = entry;
    if (previous)
     previous.next = entry;
    if (DESCRIPTORS)
     state.size++;
    else
     that.size++;
    if (index !== 'F')
     state.index[index] = entry;
   }
   return that;
  };
  var getEntry = function (that, key) {
   var state = getInternalState(that);
   var index = fastKey(key);
   var entry;
   if (index !== 'F')
    return state.index[index];
   for (entry = state.first; entry; entry = entry.next) {
    if (entry.key == key)
     return entry;
   }
  };
  defineBuiltIns(Prototype, {
   clear: function clear() {
    var that = this;
    var state = getInternalState(that);
    var data = state.index;
    var entry = state.first;
    while (entry) {
     entry.removed = true;
     if (entry.previous)
      entry.previous = entry.previous.next = undefined;
     delete data[entry.index];
     entry = entry.next;
    }
    state.first = state.last = undefined;
    if (DESCRIPTORS)
     state.size = 0;
    else
     that.size = 0;
   },
   'delete': function (key) {
    var that = this;
    var state = getInternalState(that);
    var entry = getEntry(that, key);
    if (entry) {
     var next = entry.next;
     var prev = entry.previous;
     delete state.index[entry.index];
     entry.removed = true;
     if (prev)
      prev.next = next;
     if (next)
      next.previous = prev;
     if (state.first == entry)
      state.first = next;
     if (state.last == entry)
      state.last = prev;
     if (DESCRIPTORS)
      state.size--;
     else
      that.size--;
    }
    return !!entry;
   },
   forEach: function forEach(callbackfn) {
    var state = getInternalState(this);
    var boundFunction = bind(callbackfn, arguments.length > 1 ? arguments[1] : undefined);
    var entry;
    while (entry = entry ? entry.next : state.first) {
     boundFunction(entry.value, entry.key, this);
     while (entry && entry.removed)
      entry = entry.previous;
    }
   },
   has: function has(key) {
    return !!getEntry(this, key);
   }
  });
  defineBuiltIns(Prototype, IS_MAP ? {
   get: function get(key) {
    var entry = getEntry(this, key);
    return entry && entry.value;
   },
   set: function set(key, value) {
    return define(this, key === 0 ? 0 : key, value);
   }
  } : {
   add: function add(value) {
    return define(this, value = value === 0 ? 0 : value, value);
   }
  });
  if (DESCRIPTORS)
   defineProperty(Prototype, 'size', {
    get: function () {
     return getInternalState(this).size;
    }
   });
  return Constructor;
 },
 setStrong: function (Constructor, CONSTRUCTOR_NAME, IS_MAP) {
  var ITERATOR_NAME = CONSTRUCTOR_NAME + ' Iterator';
  var getInternalCollectionState = internalStateGetterFor(CONSTRUCTOR_NAME);
  var getInternalIteratorState = internalStateGetterFor(ITERATOR_NAME);
  defineIterator(Constructor, CONSTRUCTOR_NAME, function (iterated, kind) {
   setInternalState(this, {
    type: ITERATOR_NAME,
    target: iterated,
    state: getInternalCollectionState(iterated),
    kind: kind,
    last: undefined
   });
  }, function () {
   var state = getInternalIteratorState(this);
   var kind = state.kind;
   var entry = state.last;
   while (entry && entry.removed)
    entry = entry.previous;
   if (!state.target || !(state.last = entry = entry ? entry.next : state.state.first)) {
    state.target = undefined;
    return {
     value: undefined,
     done: true
    };
   }
   if (kind == 'keys')
    return {
     value: entry.key,
     done: false
    };
   if (kind == 'values')
    return {
     value: entry.value,
     done: false
    };
   return {
    value: [
     entry.key,
     entry.value
    ],
    done: false
   };
  }, IS_MAP ? 'entries' : 'values', !IS_MAP, true);
  setSpecies(CONSTRUCTOR_NAME);
 }
};

/***/ }),
/* 115 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var defineBuiltIn = __w_pdfjs_require__(49);
module.exports = function (target, src, options) {
 for (var key in src)
  defineBuiltIn(target, key, src[key], options);
 return target;
};

/***/ }),
/* 116 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var getBuiltIn = __w_pdfjs_require__(25);
var definePropertyModule = __w_pdfjs_require__(46);
var wellKnownSymbol = __w_pdfjs_require__(35);
var DESCRIPTORS = __w_pdfjs_require__(9);
var SPECIES = wellKnownSymbol('species');
module.exports = function (CONSTRUCTOR_NAME) {
 var Constructor = getBuiltIn(CONSTRUCTOR_NAME);
 var defineProperty = definePropertyModule.f;
 if (DESCRIPTORS && Constructor && !Constructor[SPECIES]) {
  defineProperty(Constructor, SPECIES, {
   configurable: true,
   get: function () {
    return this;
   }
  });
 }
};

/***/ }),
/* 117 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

__w_pdfjs_require__(118);

/***/ }),
/* 118 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var collection = __w_pdfjs_require__(97);
var collectionStrong = __w_pdfjs_require__(114);
collection('Set', function (init) {
 return function Set() {
  return init(this, arguments.length ? arguments[0] : undefined);
 };
}, collectionStrong);

/***/ }),
/* 119 */
/***/ ((__unused_webpack_module, __unused_webpack_exports, __w_pdfjs_require__) => {

var IS_PURE = __w_pdfjs_require__(37);
var $ = __w_pdfjs_require__(6);
var global = __w_pdfjs_require__(7);
var getBuiltin = __w_pdfjs_require__(25);
var uncurryThis = __w_pdfjs_require__(17);
var fails = __w_pdfjs_require__(10);
var uid = __w_pdfjs_require__(42);
var isCallable = __w_pdfjs_require__(23);
var isConstructor = __w_pdfjs_require__(120);
var isObject = __w_pdfjs_require__(22);
var isSymbol = __w_pdfjs_require__(24);
var iterate = __w_pdfjs_require__(105);
var anObject = __w_pdfjs_require__(48);
var classof = __w_pdfjs_require__(80);
var hasOwn = __w_pdfjs_require__(40);
var createProperty = __w_pdfjs_require__(101);
var createNonEnumerableProperty = __w_pdfjs_require__(45);
var lengthOfArrayLike = __w_pdfjs_require__(65);
var validateArgumentsLength = __w_pdfjs_require__(121);
var getRegExpFlags = __w_pdfjs_require__(122);
var ERROR_STACK_INSTALLABLE = __w_pdfjs_require__(124);
var V8 = __w_pdfjs_require__(29);
var IS_BROWSER = __w_pdfjs_require__(125);
var IS_DENO = __w_pdfjs_require__(126);
var IS_NODE = __w_pdfjs_require__(127);
var Object = global.Object;
var Date = global.Date;
var Error = global.Error;
var EvalError = global.EvalError;
var RangeError = global.RangeError;
var ReferenceError = global.ReferenceError;
var SyntaxError = global.SyntaxError;
var TypeError = global.TypeError;
var URIError = global.URIError;
var PerformanceMark = global.PerformanceMark;
var WebAssembly = global.WebAssembly;
var CompileError = WebAssembly && WebAssembly.CompileError || Error;
var LinkError = WebAssembly && WebAssembly.LinkError || Error;
var RuntimeError = WebAssembly && WebAssembly.RuntimeError || Error;
var DOMException = getBuiltin('DOMException');
var Set = getBuiltin('Set');
var Map = getBuiltin('Map');
var MapPrototype = Map.prototype;
var mapHas = uncurryThis(MapPrototype.has);
var mapGet = uncurryThis(MapPrototype.get);
var mapSet = uncurryThis(MapPrototype.set);
var setAdd = uncurryThis(Set.prototype.add);
var objectKeys = getBuiltin('Object', 'keys');
var push = uncurryThis([].push);
var booleanValueOf = uncurryThis(true.valueOf);
var numberValueOf = uncurryThis(1.0.valueOf);
var stringValueOf = uncurryThis(''.valueOf);
var getTime = uncurryThis(Date.prototype.getTime);
var PERFORMANCE_MARK = uid('structuredClone');
var DATA_CLONE_ERROR = 'DataCloneError';
var TRANSFERRING = 'Transferring';
var checkBasicSemantic = function (structuredCloneImplementation) {
 return !fails(function () {
  var set1 = new global.Set([7]);
  var set2 = structuredCloneImplementation(set1);
  var number = structuredCloneImplementation(Object(7));
  return set2 == set1 || !set2.has(7) || typeof number != 'object' || number != 7;
 }) && structuredCloneImplementation;
};
var checkErrorsCloning = function (structuredCloneImplementation, $Error) {
 return !fails(function () {
  var error = new $Error();
  var test = structuredCloneImplementation({
   a: error,
   b: error
  });
  return !(test && test.a === test.b && test.a instanceof $Error && test.a.stack === error.stack);
 });
};
var checkNewErrorsCloningSemantic = function (structuredCloneImplementation) {
 return !fails(function () {
  var test = structuredCloneImplementation(new global.AggregateError([1], PERFORMANCE_MARK, { cause: 3 }));
  return test.name != 'AggregateError' || test.errors[0] != 1 || test.message != PERFORMANCE_MARK || test.cause != 3;
 });
};
var nativeStructuredClone = global.structuredClone;
var FORCED_REPLACEMENT = IS_PURE || !checkErrorsCloning(nativeStructuredClone, Error) || !checkErrorsCloning(nativeStructuredClone, DOMException) || !checkNewErrorsCloningSemantic(nativeStructuredClone);
var structuredCloneFromMark = !nativeStructuredClone && checkBasicSemantic(function (value) {
 return new PerformanceMark(PERFORMANCE_MARK, { detail: value }).detail;
});
var nativeRestrictedStructuredClone = checkBasicSemantic(nativeStructuredClone) || structuredCloneFromMark;
var throwUncloneable = function (type) {
 throw new DOMException('Uncloneable type: ' + type, DATA_CLONE_ERROR);
};
var throwUnpolyfillable = function (type, kind) {
 throw new DOMException((kind || 'Cloning') + ' of ' + type + ' cannot be properly polyfilled in this engine', DATA_CLONE_ERROR);
};
var structuredCloneInternal = function (value, map) {
 if (isSymbol(value))
  throwUncloneable('Symbol');
 if (!isObject(value))
  return value;
 if (map) {
  if (mapHas(map, value))
   return mapGet(map, value);
 } else
  map = new Map();
 var type = classof(value);
 var deep = false;
 var C, name, cloned, dataTransfer, i, length, keys, key, source, target;
 switch (type) {
 case 'Array':
  cloned = [];
  deep = true;
  break;
 case 'Object':
  cloned = {};
  deep = true;
  break;
 case 'Map':
  cloned = new Map();
  deep = true;
  break;
 case 'Set':
  cloned = new Set();
  deep = true;
  break;
 case 'RegExp':
  cloned = new RegExp(value.source, getRegExpFlags(value));
  break;
 case 'Error':
  name = value.name;
  switch (name) {
  case 'AggregateError':
   cloned = getBuiltin('AggregateError')([]);
   break;
  case 'EvalError':
   cloned = EvalError();
   break;
  case 'RangeError':
   cloned = RangeError();
   break;
  case 'ReferenceError':
   cloned = ReferenceError();
   break;
  case 'SyntaxError':
   cloned = SyntaxError();
   break;
  case 'TypeError':
   cloned = TypeError();
   break;
  case 'URIError':
   cloned = URIError();
   break;
  case 'CompileError':
   cloned = CompileError();
   break;
  case 'LinkError':
   cloned = LinkError();
   break;
  case 'RuntimeError':
   cloned = RuntimeError();
   break;
  default:
   cloned = Error();
  }
  deep = true;
  break;
 case 'DOMException':
  cloned = new DOMException(value.message, value.name);
  deep = true;
  break;
 case 'DataView':
 case 'Int8Array':
 case 'Uint8Array':
 case 'Uint8ClampedArray':
 case 'Int16Array':
 case 'Uint16Array':
 case 'Int32Array':
 case 'Uint32Array':
 case 'Float32Array':
 case 'Float64Array':
 case 'BigInt64Array':
 case 'BigUint64Array':
  C = global[type];
  if (!isObject(C))
   throwUnpolyfillable(type);
  cloned = new C(structuredCloneInternal(value.buffer, map), value.byteOffset, type === 'DataView' ? value.byteLength : value.length);
  break;
 case 'DOMQuad':
  try {
   cloned = new DOMQuad(structuredCloneInternal(value.p1, map), structuredCloneInternal(value.p2, map), structuredCloneInternal(value.p3, map), structuredCloneInternal(value.p4, map));
  } catch (error) {
   if (nativeRestrictedStructuredClone) {
    cloned = nativeRestrictedStructuredClone(value);
   } else
    throwUnpolyfillable(type);
  }
  break;
 case 'FileList':
  C = global.DataTransfer;
  if (isConstructor(C)) {
   dataTransfer = new C();
   for (i = 0, length = lengthOfArrayLike(value); i < length; i++) {
    dataTransfer.items.add(structuredCloneInternal(value[i], map));
   }
   cloned = dataTransfer.files;
  } else if (nativeRestrictedStructuredClone) {
   cloned = nativeRestrictedStructuredClone(value);
  } else
   throwUnpolyfillable(type);
  break;
 case 'ImageData':
  try {
   cloned = new ImageData(structuredCloneInternal(value.data, map), value.width, value.height, { colorSpace: value.colorSpace });
  } catch (error) {
   if (nativeRestrictedStructuredClone) {
    cloned = nativeRestrictedStructuredClone(value);
   } else
    throwUnpolyfillable(type);
  }
  break;
 default:
  if (nativeRestrictedStructuredClone) {
   cloned = nativeRestrictedStructuredClone(value);
  } else
   switch (type) {
   case 'BigInt':
    cloned = Object(value.valueOf());
    break;
   case 'Boolean':
    cloned = Object(booleanValueOf(value));
    break;
   case 'Number':
    cloned = Object(numberValueOf(value));
    break;
   case 'String':
    cloned = Object(stringValueOf(value));
    break;
   case 'Date':
    cloned = new Date(getTime(value));
    break;
   case 'ArrayBuffer':
    C = global.DataView;
    if (!C && typeof value.slice != 'function')
     throwUnpolyfillable(type);
    try {
     if (typeof value.slice == 'function') {
      cloned = value.slice(0);
     } else {
      length = value.byteLength;
      cloned = new ArrayBuffer(length);
      source = new C(value);
      target = new C(cloned);
      for (i = 0; i < length; i++) {
       target.setUint8(i, source.getUint8(i));
      }
     }
    } catch (error) {
     throw new DOMException('ArrayBuffer is detached', DATA_CLONE_ERROR);
    }
    break;
   case 'SharedArrayBuffer':
    cloned = value;
    break;
   case 'Blob':
    try {
     cloned = value.slice(0, value.size, value.type);
    } catch (error) {
     throwUnpolyfillable(type);
    }
    break;
   case 'DOMPoint':
   case 'DOMPointReadOnly':
    C = global[type];
    try {
     cloned = C.fromPoint ? C.fromPoint(value) : new C(value.x, value.y, value.z, value.w);
    } catch (error) {
     throwUnpolyfillable(type);
    }
    break;
   case 'DOMRect':
   case 'DOMRectReadOnly':
    C = global[type];
    try {
     cloned = C.fromRect ? C.fromRect(value) : new C(value.x, value.y, value.width, value.height);
    } catch (error) {
     throwUnpolyfillable(type);
    }
    break;
   case 'DOMMatrix':
   case 'DOMMatrixReadOnly':
    C = global[type];
    try {
     cloned = C.fromMatrix ? C.fromMatrix(value) : new C(value);
    } catch (error) {
     throwUnpolyfillable(type);
    }
    break;
   case 'AudioData':
   case 'VideoFrame':
    if (!isCallable(value.clone))
     throwUnpolyfillable(type);
    try {
     cloned = value.clone();
    } catch (error) {
     throwUncloneable(type);
    }
    break;
   case 'File':
    try {
     cloned = new File([value], value.name, value);
    } catch (error) {
     throwUnpolyfillable(type);
    }
    break;
   case 'CryptoKey':
   case 'GPUCompilationMessage':
   case 'GPUCompilationInfo':
   case 'ImageBitmap':
   case 'RTCCertificate':
   case 'WebAssembly.Module':
    throwUnpolyfillable(type);
   default:
    throwUncloneable(type);
   }
 }
 mapSet(map, value, cloned);
 if (deep)
  switch (type) {
  case 'Array':
  case 'Object':
   keys = objectKeys(value);
   for (i = 0, length = lengthOfArrayLike(keys); i < length; i++) {
    key = keys[i];
    createProperty(cloned, key, structuredCloneInternal(value[key], map));
   }
   break;
  case 'Map':
   value.forEach(function (v, k) {
    mapSet(cloned, structuredCloneInternal(k, map), structuredCloneInternal(v, map));
   });
   break;
  case 'Set':
   value.forEach(function (v) {
    setAdd(cloned, structuredCloneInternal(v, map));
   });
   break;
  case 'Error':
   createNonEnumerableProperty(cloned, 'message', structuredCloneInternal(value.message, map));
   if (hasOwn(value, 'cause')) {
    createNonEnumerableProperty(cloned, 'cause', structuredCloneInternal(value.cause, map));
   }
   if (name == 'AggregateError') {
    cloned.errors = structuredCloneInternal(value.errors, map);
   }
  case 'DOMException':
   if (ERROR_STACK_INSTALLABLE) {
    createNonEnumerableProperty(cloned, 'stack', structuredCloneInternal(value.stack, map));
   }
  }
 return cloned;
};
var PROPER_TRANSFER = nativeStructuredClone && !fails(function () {
 if (IS_DENO && V8 > 92 || IS_NODE && V8 > 94 || IS_BROWSER && V8 > 97)
  return false;
 var buffer = new ArrayBuffer(8);
 var clone = nativeStructuredClone(buffer, { transfer: [buffer] });
 return buffer.byteLength != 0 || clone.byteLength != 8;
});
var tryToTransfer = function (rawTransfer, map) {
 if (!isObject(rawTransfer))
  throw TypeError('Transfer option cannot be converted to a sequence');
 var transfer = [];
 iterate(rawTransfer, function (value) {
  push(transfer, anObject(value));
 });
 var i = 0;
 var length = lengthOfArrayLike(transfer);
 var value, type, C, transferredArray, transferred, canvas, context;
 if (PROPER_TRANSFER) {
  transferredArray = nativeStructuredClone(transfer, { transfer: transfer });
  while (i < length)
   mapSet(map, transfer[i], transferredArray[i++]);
 } else
  while (i < length) {
   value = transfer[i++];
   if (mapHas(map, value))
    throw new DOMException('Duplicate transferable', DATA_CLONE_ERROR);
   type = classof(value);
   switch (type) {
   case 'ImageBitmap':
    C = global.OffscreenCanvas;
    if (!isConstructor(C))
     throwUnpolyfillable(type, TRANSFERRING);
    try {
     canvas = new C(value.width, value.height);
     context = canvas.getContext('bitmaprenderer');
     context.transferFromImageBitmap(value);
     transferred = canvas.transferToImageBitmap();
    } catch (error) {
    }
    break;
   case 'AudioData':
   case 'VideoFrame':
    if (!isCallable(value.clone) || !isCallable(value.close))
     throwUnpolyfillable(type, TRANSFERRING);
    try {
     transferred = value.clone();
     value.close();
    } catch (error) {
    }
    break;
   case 'ArrayBuffer':
   case 'MessagePort':
   case 'OffscreenCanvas':
   case 'ReadableStream':
   case 'TransformStream':
   case 'WritableStream':
    throwUnpolyfillable(type, TRANSFERRING);
   }
   if (transferred === undefined)
    throw new DOMException('This object cannot be transferred: ' + type, DATA_CLONE_ERROR);
   mapSet(map, value, transferred);
  }
};
$({
 global: true,
 enumerable: true,
 sham: !PROPER_TRANSFER,
 forced: FORCED_REPLACEMENT
}, {
 structuredClone: function structuredClone(value) {
  var options = validateArgumentsLength(arguments.length, 1) > 1 && arguments[1] != null ? anObject(arguments[1]) : undefined;
  var transfer = options ? options.transfer : undefined;
  var map;
  if (transfer !== undefined) {
   map = new Map();
   tryToTransfer(transfer, map);
  }
  return structuredCloneInternal(value, map);
 }
});

/***/ }),
/* 120 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var uncurryThis = __w_pdfjs_require__(17);
var fails = __w_pdfjs_require__(10);
var isCallable = __w_pdfjs_require__(23);
var classof = __w_pdfjs_require__(80);
var getBuiltIn = __w_pdfjs_require__(25);
var inspectSource = __w_pdfjs_require__(52);
var noop = function () {
};
var empty = [];
var construct = getBuiltIn('Reflect', 'construct');
var constructorRegExp = /^\s*(?:class|function)\b/;
var exec = uncurryThis(constructorRegExp.exec);
var INCORRECT_TO_STRING = !constructorRegExp.exec(noop);
var isConstructorModern = function isConstructor(argument) {
 if (!isCallable(argument))
  return false;
 try {
  construct(noop, empty, argument);
  return true;
 } catch (error) {
  return false;
 }
};
var isConstructorLegacy = function isConstructor(argument) {
 if (!isCallable(argument))
  return false;
 switch (classof(argument)) {
 case 'AsyncFunction':
 case 'GeneratorFunction':
 case 'AsyncGeneratorFunction':
  return false;
 }
 try {
  return INCORRECT_TO_STRING || !!exec(constructorRegExp, inspectSource(argument));
 } catch (error) {
  return true;
 }
};
isConstructorLegacy.sham = true;
module.exports = !construct || fails(function () {
 var called;
 return isConstructorModern(isConstructorModern.call) || !isConstructorModern(Object) || !isConstructorModern(function () {
  called = true;
 }) || called;
}) ? isConstructorLegacy : isConstructorModern;

/***/ }),
/* 121 */
/***/ ((module) => {

var $TypeError = TypeError;
module.exports = function (passed, required) {
 if (passed < required)
  throw $TypeError('Not enough arguments');
 return passed;
};

/***/ }),
/* 122 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var call = __w_pdfjs_require__(11);
var hasOwn = __w_pdfjs_require__(40);
var isPrototypeOf = __w_pdfjs_require__(26);
var regExpFlags = __w_pdfjs_require__(123);
var RegExpPrototype = RegExp.prototype;
module.exports = function (R) {
 var flags = R.flags;
 return flags === undefined && !('flags' in RegExpPrototype) && !hasOwn(R, 'flags') && isPrototypeOf(RegExpPrototype, R) ? call(regExpFlags, R) : flags;
};

/***/ }),
/* 123 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

"use strict";

var anObject = __w_pdfjs_require__(48);
module.exports = function () {
 var that = anObject(this);
 var result = '';
 if (that.hasIndices)
  result += 'd';
 if (that.global)
  result += 'g';
 if (that.ignoreCase)
  result += 'i';
 if (that.multiline)
  result += 'm';
 if (that.dotAll)
  result += 's';
 if (that.unicode)
  result += 'u';
 if (that.unicodeSets)
  result += 'v';
 if (that.sticky)
  result += 'y';
 return result;
};

/***/ }),
/* 124 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var fails = __w_pdfjs_require__(10);
var createPropertyDescriptor = __w_pdfjs_require__(14);
module.exports = !fails(function () {
 var error = Error('a');
 if (!('stack' in error))
  return true;
 Object.defineProperty(error, 'stack', createPropertyDescriptor(1, 7));
 return error.stack !== 7;
});

/***/ }),
/* 125 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var IS_DENO = __w_pdfjs_require__(126);
var IS_NODE = __w_pdfjs_require__(127);
module.exports = !IS_DENO && !IS_NODE && typeof window == 'object' && typeof document == 'object';

/***/ }),
/* 126 */
/***/ ((module) => {

module.exports = typeof Deno == 'object' && Deno && typeof Deno.version == 'object';

/***/ }),
/* 127 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var classof = __w_pdfjs_require__(18);
var global = __w_pdfjs_require__(7);
module.exports = classof(global.process) == 'process';

/***/ }),
/* 128 */
/***/ ((module, __unused_webpack_exports, __w_pdfjs_require__) => {

var global = __w_pdfjs_require__(7);
module.exports = global;

/***/ }),
/* 129 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.build = exports.RenderTask = exports.PDFWorkerUtil = exports.PDFWorker = exports.PDFPageProxy = exports.PDFDocumentProxy = exports.PDFDocumentLoadingTask = exports.PDFDataRangeTransport = exports.LoopbackPort = exports.DefaultStandardFontDataFactory = exports.DefaultCanvasFactory = exports.DefaultCMapReaderFactory = void 0;
exports.getDocument = getDocument;
exports.setPDFNetworkStreamFactory = setPDFNetworkStreamFactory;
exports.version = void 0;

var _util = __w_pdfjs_require__(1);

var _annotation_storage = __w_pdfjs_require__(130);

var _display_utils = __w_pdfjs_require__(133);

var _font_loader = __w_pdfjs_require__(136);

var _canvas = __w_pdfjs_require__(137);

var _worker_options = __w_pdfjs_require__(140);

var _is_node = __w_pdfjs_require__(3);

var _message_handler = __w_pdfjs_require__(141);

var _metadata = __w_pdfjs_require__(142);

var _optional_content_config = __w_pdfjs_require__(143);

var _transport_stream = __w_pdfjs_require__(144);

var _xfa_text = __w_pdfjs_require__(145);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classStaticPrivateFieldSpecSet(receiver, classConstructor, descriptor, value) { _classCheckPrivateStaticAccess(receiver, classConstructor); _classCheckPrivateStaticFieldDescriptor(descriptor, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classStaticPrivateFieldSpecGet(receiver, classConstructor, descriptor) { _classCheckPrivateStaticAccess(receiver, classConstructor); _classCheckPrivateStaticFieldDescriptor(descriptor, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classCheckPrivateStaticFieldDescriptor(descriptor, action) { if (descriptor === undefined) { throw new TypeError("attempted to " + action + " private static field before its declaration"); } }

function _classCheckPrivateStaticAccess(receiver, classConstructor) { if (receiver !== classConstructor) { throw new TypeError("Private static access of wrong provenance"); } }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

const DEFAULT_RANGE_CHUNK_SIZE = 65536;
const RENDERING_CANCELLED_TIMEOUT = 100;
let DefaultCanvasFactory = _display_utils.DOMCanvasFactory;
exports.DefaultCanvasFactory = DefaultCanvasFactory;
let DefaultCMapReaderFactory = _display_utils.DOMCMapReaderFactory;
exports.DefaultCMapReaderFactory = DefaultCMapReaderFactory;
let DefaultStandardFontDataFactory = _display_utils.DOMStandardFontDataFactory;
exports.DefaultStandardFontDataFactory = DefaultStandardFontDataFactory;

if (_is_node.isNodeJS) {
  const {
    NodeCanvasFactory,
    NodeCMapReaderFactory,
    NodeStandardFontDataFactory
  } = __w_pdfjs_require__(146);

  exports.DefaultCanvasFactory = DefaultCanvasFactory = NodeCanvasFactory;
  exports.DefaultCMapReaderFactory = DefaultCMapReaderFactory = NodeCMapReaderFactory;
  exports.DefaultStandardFontDataFactory = DefaultStandardFontDataFactory = NodeStandardFontDataFactory;
}

let createPDFNetworkStream;

function setPDFNetworkStreamFactory(pdfNetworkStreamFactory) {
  createPDFNetworkStream = pdfNetworkStreamFactory;
}

function getDocument(src) {
  const task = new PDFDocumentLoadingTask();
  let source;

  if (typeof src === "string" || src instanceof URL) {
    source = {
      url: src
    };
  } else if ((0, _util.isArrayBuffer)(src)) {
    source = {
      data: src
    };
  } else if (src instanceof PDFDataRangeTransport) {
    source = {
      range: src
    };
  } else {
    if (typeof src !== "object") {
      throw new Error("Invalid parameter in getDocument, " + "need either string, URL, TypedArray, or parameter object.");
    }

    if (!src.url && !src.data && !src.range) {
      throw new Error("Invalid parameter object: need either .data, .range or .url");
    }

    source = src;
  }

  const params = Object.create(null);
  let rangeTransport = null,
      worker = null;

  for (const key in source) {
    const value = source[key];

    switch (key) {
      case "url":
        if (typeof window !== "undefined") {
          try {
            params[key] = new URL(value, window.location).href;
            continue;
          } catch (ex) {
            (0, _util.warn)(`Cannot create valid URL: "${ex}".`);
          }
        } else if (typeof value === "string" || value instanceof URL) {
          params[key] = value.toString();
          continue;
        }

        throw new Error("Invalid PDF url data: " + "either string or URL-object is expected in the url property.");

      case "range":
        rangeTransport = value;
        continue;

      case "worker":
        worker = value;
        continue;

      case "data":
        if (_is_node.isNodeJS && typeof Buffer !== "undefined" && value instanceof Buffer) {
          params[key] = new Uint8Array(value);
        } else if (value instanceof Uint8Array) {
          break;
        } else if (typeof value === "string") {
          params[key] = (0, _util.stringToBytes)(value);
        } else if (typeof value === "object" && value !== null && !isNaN(value.length)) {
          params[key] = new Uint8Array(value);
        } else if ((0, _util.isArrayBuffer)(value)) {
          params[key] = new Uint8Array(value);
        } else {
          throw new Error("Invalid PDF binary data: either TypedArray, " + "string, or array-like object is expected in the data property.");
        }

        continue;
    }

    params[key] = value;
  }

  params.CMapReaderFactory = params.CMapReaderFactory || DefaultCMapReaderFactory;
  params.StandardFontDataFactory = params.StandardFontDataFactory || DefaultStandardFontDataFactory;
  params.ignoreErrors = params.stopAtErrors !== true;
  params.fontExtraProperties = params.fontExtraProperties === true;
  params.pdfBug = params.pdfBug === true;
  params.enableXfa = params.enableXfa === true;

  if (!Number.isInteger(params.rangeChunkSize) || params.rangeChunkSize < 1) {
    params.rangeChunkSize = DEFAULT_RANGE_CHUNK_SIZE;
  }

  if (typeof params.docBaseUrl !== "string" || (0, _display_utils.isDataScheme)(params.docBaseUrl)) {
    params.docBaseUrl = null;
  }

  if (!Number.isInteger(params.maxImageSize) || params.maxImageSize < -1) {
    params.maxImageSize = -1;
  }

  if (typeof params.cMapUrl !== "string") {
    params.cMapUrl = null;
  }

  if (typeof params.standardFontDataUrl !== "string") {
    params.standardFontDataUrl = null;
  }

  if (typeof params.useWorkerFetch !== "boolean") {
    params.useWorkerFetch = params.CMapReaderFactory === _display_utils.DOMCMapReaderFactory && params.StandardFontDataFactory === _display_utils.DOMStandardFontDataFactory;
  }

  if (typeof params.isEvalSupported !== "boolean") {
    params.isEvalSupported = true;
  }

  if (typeof params.disableFontFace !== "boolean") {
    params.disableFontFace = _is_node.isNodeJS;
  }

  if (typeof params.useSystemFonts !== "boolean") {
    params.useSystemFonts = !_is_node.isNodeJS && !params.disableFontFace;
  }

  if (typeof params.ownerDocument !== "object" || params.ownerDocument === null) {
    params.ownerDocument = globalThis.document;
  }

  if (typeof params.disableRange !== "boolean") {
    params.disableRange = false;
  }

  if (typeof params.disableStream !== "boolean") {
    params.disableStream = false;
  }

  if (typeof params.disableAutoFetch !== "boolean") {
    params.disableAutoFetch = false;
  }

  (0, _util.setVerbosityLevel)(params.verbosity);

  if (!worker) {
    const workerParams = {
      verbosity: params.verbosity,
      port: _worker_options.GlobalWorkerOptions.workerPort
    };
    worker = workerParams.port ? PDFWorker.fromPort(workerParams) : new PDFWorker(workerParams);
    task._worker = worker;
  }

  const docId = task.docId;
  worker.promise.then(function () {
    if (task.destroyed) {
      throw new Error("Loading aborted");
    }

    const workerIdPromise = _fetchDocument(worker, params, rangeTransport, docId);

    const networkStreamPromise = new Promise(function (resolve) {
      let networkStream;

      if (rangeTransport) {
        networkStream = new _transport_stream.PDFDataTransportStream({
          length: params.length,
          initialData: params.initialData,
          progressiveDone: params.progressiveDone,
          contentDispositionFilename: params.contentDispositionFilename,
          disableRange: params.disableRange,
          disableStream: params.disableStream
        }, rangeTransport);
      } else if (!params.data) {
        networkStream = createPDFNetworkStream({
          url: params.url,
          length: params.length,
          httpHeaders: params.httpHeaders,
          withCredentials: params.withCredentials,
          rangeChunkSize: params.rangeChunkSize,
          disableRange: params.disableRange,
          disableStream: params.disableStream
        });
      }

      resolve(networkStream);
    });
    return Promise.all([workerIdPromise, networkStreamPromise]).then(function (_ref) {
      let [workerId, networkStream] = _ref;

      if (task.destroyed) {
        throw new Error("Loading aborted");
      }

      const messageHandler = new _message_handler.MessageHandler(docId, workerId, worker.port);
      const transport = new WorkerTransport(messageHandler, task, networkStream, params);
      task._transport = transport;
      messageHandler.send("Ready", null);
    });
  }).catch(task._capability.reject);
  return task;
}

async function _fetchDocument(worker, source, pdfDataRangeTransport, docId) {
  if (worker.destroyed) {
    throw new Error("Worker was destroyed");
  }

  if (pdfDataRangeTransport) {
    source.length = pdfDataRangeTransport.length;
    source.initialData = pdfDataRangeTransport.initialData;
    source.progressiveDone = pdfDataRangeTransport.progressiveDone;
    source.contentDispositionFilename = pdfDataRangeTransport.contentDispositionFilename;
  }

  const workerId = await worker.messageHandler.sendWithPromise("GetDocRequest", {
    docId,
    apiVersion: '2.16.105',
    source: {
      data: source.data,
      url: source.url,
      password: source.password,
      disableAutoFetch: source.disableAutoFetch,
      rangeChunkSize: source.rangeChunkSize,
      length: source.length
    },
    maxImageSize: source.maxImageSize,
    disableFontFace: source.disableFontFace,
    docBaseUrl: source.docBaseUrl,
    ignoreErrors: source.ignoreErrors,
    isEvalSupported: source.isEvalSupported,
    fontExtraProperties: source.fontExtraProperties,
    enableXfa: source.enableXfa,
    useSystemFonts: source.useSystemFonts,
    cMapUrl: source.useWorkerFetch ? source.cMapUrl : null,
    standardFontDataUrl: source.useWorkerFetch ? source.standardFontDataUrl : null
  });

  if (source.data) {
    source.data = null;
  }

  if (worker.destroyed) {
    throw new Error("Worker was destroyed");
  }

  return workerId;
}

class PDFDocumentLoadingTask {
  constructor() {
    var _PDFDocumentLoadingTa, _PDFDocumentLoadingTa2;

    this._capability = (0, _util.createPromiseCapability)();
    this._transport = null;
    this._worker = null;
    this.docId = `d${(_classStaticPrivateFieldSpecSet(PDFDocumentLoadingTask, PDFDocumentLoadingTask, _docId, (_PDFDocumentLoadingTa = _classStaticPrivateFieldSpecGet(PDFDocumentLoadingTask, PDFDocumentLoadingTask, _docId), _PDFDocumentLoadingTa2 = _PDFDocumentLoadingTa++, _PDFDocumentLoadingTa)), _PDFDocumentLoadingTa2)}`;
    this.destroyed = false;
    this.onPassword = null;
    this.onProgress = null;
    this.onUnsupportedFeature = null;
  }

  get promise() {
    return this._capability.promise;
  }

  async destroy() {
    var _this$_transport;

    this.destroyed = true;
    await ((_this$_transport = this._transport) === null || _this$_transport === void 0 ? void 0 : _this$_transport.destroy());
    this._transport = null;

    if (this._worker) {
      this._worker.destroy();

      this._worker = null;
    }
  }

}

exports.PDFDocumentLoadingTask = PDFDocumentLoadingTask;
var _docId = {
  writable: true,
  value: 0
};

class PDFDataRangeTransport {
  constructor(length, initialData) {
    let progressiveDone = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
    let contentDispositionFilename = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;
    this.length = length;
    this.initialData = initialData;
    this.progressiveDone = progressiveDone;
    this.contentDispositionFilename = contentDispositionFilename;
    this._rangeListeners = [];
    this._progressListeners = [];
    this._progressiveReadListeners = [];
    this._progressiveDoneListeners = [];
    this._readyCapability = (0, _util.createPromiseCapability)();
  }

  addRangeListener(listener) {
    this._rangeListeners.push(listener);
  }

  addProgressListener(listener) {
    this._progressListeners.push(listener);
  }

  addProgressiveReadListener(listener) {
    this._progressiveReadListeners.push(listener);
  }

  addProgressiveDoneListener(listener) {
    this._progressiveDoneListeners.push(listener);
  }

  onDataRange(begin, chunk) {
    for (const listener of this._rangeListeners) {
      listener(begin, chunk);
    }
  }

  onDataProgress(loaded, total) {
    this._readyCapability.promise.then(() => {
      for (const listener of this._progressListeners) {
        listener(loaded, total);
      }
    });
  }

  onDataProgressiveRead(chunk) {
    this._readyCapability.promise.then(() => {
      for (const listener of this._progressiveReadListeners) {
        listener(chunk);
      }
    });
  }

  onDataProgressiveDone() {
    this._readyCapability.promise.then(() => {
      for (const listener of this._progressiveDoneListeners) {
        listener();
      }
    });
  }

  transportReady() {
    this._readyCapability.resolve();
  }

  requestDataRange(begin, end) {
    (0, _util.unreachable)("Abstract method PDFDataRangeTransport.requestDataRange");
  }

  abort() {}

}

exports.PDFDataRangeTransport = PDFDataRangeTransport;

class PDFDocumentProxy {
  constructor(pdfInfo, transport) {
    this._pdfInfo = pdfInfo;
    this._transport = transport;
    Object.defineProperty(this, "fingerprint", {
      get() {
        (0, _display_utils.deprecated)("`PDFDocumentProxy.fingerprint`, " + "please use `PDFDocumentProxy.fingerprints` instead.");
        return this.fingerprints[0];
      }

    });
    Object.defineProperty(this, "getStats", {
      value: async () => {
        (0, _display_utils.deprecated)("`PDFDocumentProxy.getStats`, " + "please use the `PDFDocumentProxy.stats`-getter instead.");
        return this.stats || {
          streamTypes: {},
          fontTypes: {}
        };
      }
    });
  }

  get annotationStorage() {
    return this._transport.annotationStorage;
  }

  get numPages() {
    return this._pdfInfo.numPages;
  }

  get fingerprints() {
    return this._pdfInfo.fingerprints;
  }

  get stats() {
    return this._transport.stats;
  }

  get isPureXfa() {
    return !!this._transport._htmlForXfa;
  }

  get allXfaHtml() {
    return this._transport._htmlForXfa;
  }

  getPage(pageNumber) {
    return this._transport.getPage(pageNumber);
  }

  getPageIndex(ref) {
    return this._transport.getPageIndex(ref);
  }

  getDestinations() {
    return this._transport.getDestinations();
  }

  getDestination(id) {
    return this._transport.getDestination(id);
  }

  getPageLabels() {
    return this._transport.getPageLabels();
  }

  getPageLayout() {
    return this._transport.getPageLayout();
  }

  getPageMode() {
    return this._transport.getPageMode();
  }

  getViewerPreferences() {
    return this._transport.getViewerPreferences();
  }

  getOpenAction() {
    return this._transport.getOpenAction();
  }

  getAttachments() {
    return this._transport.getAttachments();
  }

  getJavaScript() {
    return this._transport.getJavaScript();
  }

  getJSActions() {
    return this._transport.getDocJSActions();
  }

  getOutline() {
    return this._transport.getOutline();
  }

  getOptionalContentConfig() {
    return this._transport.getOptionalContentConfig();
  }

  getPermissions() {
    return this._transport.getPermissions();
  }

  getMetadata() {
    return this._transport.getMetadata();
  }

  getMarkInfo() {
    return this._transport.getMarkInfo();
  }

  getData() {
    return this._transport.getData();
  }

  getDownloadInfo() {
    return this._transport.downloadInfoCapability.promise;
  }

  cleanup() {
    let keepLoadedFonts = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;
    return this._transport.startCleanup(keepLoadedFonts || this.isPureXfa);
  }

  destroy() {
    return this.loadingTask.destroy();
  }

  get loadingParams() {
    return this._transport.loadingParams;
  }

  get loadingTask() {
    return this._transport.loadingTask;
  }

  saveDocument() {
    if (this._transport.annotationStorage.size <= 0) {
      (0, _display_utils.deprecated)("saveDocument called while `annotationStorage` is empty, " + "please use the getData-method instead.");
    }

    return this._transport.saveDocument();
  }

  getFieldObjects() {
    return this._transport.getFieldObjects();
  }

  hasJSActions() {
    return this._transport.hasJSActions();
  }

  getCalculationOrderIds() {
    return this._transport.getCalculationOrderIds();
  }

}

exports.PDFDocumentProxy = PDFDocumentProxy;

class PDFPageProxy {
  constructor(pageIndex, pageInfo, transport, ownerDocument) {
    let pdfBug = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : false;
    this._pageIndex = pageIndex;
    this._pageInfo = pageInfo;
    this._ownerDocument = ownerDocument;
    this._transport = transport;
    this._stats = pdfBug ? new _display_utils.StatTimer() : null;
    this._pdfBug = pdfBug;
    this.commonObjs = transport.commonObjs;
    this.objs = new PDFObjects();
    this._bitmaps = new Set();
    this.cleanupAfterRender = false;
    this.pendingCleanup = false;
    this._intentStates = new Map();
    this._annotationPromises = new Map();
    this.destroyed = false;
  }

  get pageNumber() {
    return this._pageIndex + 1;
  }

  get rotate() {
    return this._pageInfo.rotate;
  }

  get ref() {
    return this._pageInfo.ref;
  }

  get userUnit() {
    return this._pageInfo.userUnit;
  }

  get view() {
    return this._pageInfo.view;
  }

  getViewport() {
    let {
      scale,
      rotation = this.rotate,
      offsetX = 0,
      offsetY = 0,
      dontFlip = false
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    return new _display_utils.PageViewport({
      viewBox: this.view,
      scale,
      rotation,
      offsetX,
      offsetY,
      dontFlip
    });
  }

  getAnnotations() {
    let {
      intent = "display"
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

    const intentArgs = this._transport.getRenderingIntent(intent);

    let promise = this._annotationPromises.get(intentArgs.cacheKey);

    if (!promise) {
      promise = this._transport.getAnnotations(this._pageIndex, intentArgs.renderingIntent);

      this._annotationPromises.set(intentArgs.cacheKey, promise);

      promise = promise.then(annotations => {
        for (const annotation of annotations) {
          if (annotation.titleObj !== undefined) {
            Object.defineProperty(annotation, "title", {
              get() {
                (0, _display_utils.deprecated)("`title`-property on annotation, please use `titleObj` instead.");
                return annotation.titleObj.str;
              }

            });
          }

          if (annotation.contentsObj !== undefined) {
            Object.defineProperty(annotation, "contents", {
              get() {
                (0, _display_utils.deprecated)("`contents`-property on annotation, please use `contentsObj` instead.");
                return annotation.contentsObj.str;
              }

            });
          }
        }

        return annotations;
      });
    }

    return promise;
  }

  getJSActions() {
    return this._jsActionsPromise || (this._jsActionsPromise = this._transport.getPageJSActions(this._pageIndex));
  }

  async getXfa() {
    var _this$_transport$_htm;

    return ((_this$_transport$_htm = this._transport._htmlForXfa) === null || _this$_transport$_htm === void 0 ? void 0 : _this$_transport$_htm.children[this._pageIndex]) || null;
  }

  render(_ref2) {
    var _arguments$, _arguments$2, _intentState;

    let {
      canvasContext,
      viewport,
      intent = "display",
      annotationMode = _util.AnnotationMode.ENABLE,
      transform = null,
      imageLayer = null,
      canvasFactory = null,
      background = null,
      optionalContentConfigPromise = null,
      annotationCanvasMap = null,
      pageColors = null,
      printAnnotationStorage = null
    } = _ref2;

    if (((_arguments$ = arguments[0]) === null || _arguments$ === void 0 ? void 0 : _arguments$.renderInteractiveForms) !== undefined) {
      (0, _display_utils.deprecated)("render no longer accepts the `renderInteractiveForms`-option, " + "please use the `annotationMode`-option instead.");

      if (arguments[0].renderInteractiveForms === true && annotationMode === _util.AnnotationMode.ENABLE) {
        annotationMode = _util.AnnotationMode.ENABLE_FORMS;
      }
    }

    if (((_arguments$2 = arguments[0]) === null || _arguments$2 === void 0 ? void 0 : _arguments$2.includeAnnotationStorage) !== undefined) {
      (0, _display_utils.deprecated)("render no longer accepts the `includeAnnotationStorage`-option, " + "please use the `annotationMode`-option instead.");

      if (arguments[0].includeAnnotationStorage === true && annotationMode === _util.AnnotationMode.ENABLE) {
        annotationMode = _util.AnnotationMode.ENABLE_STORAGE;
      }
    }

    if (this._stats) {
      this._stats.time("Overall");
    }

    const intentArgs = this._transport.getRenderingIntent(intent, annotationMode, printAnnotationStorage);

    this.pendingCleanup = false;

    if (!optionalContentConfigPromise) {
      optionalContentConfigPromise = this._transport.getOptionalContentConfig();
    }

    let intentState = this._intentStates.get(intentArgs.cacheKey);

    if (!intentState) {
      intentState = Object.create(null);

      this._intentStates.set(intentArgs.cacheKey, intentState);
    }

    if (intentState.streamReaderCancelTimeout) {
      clearTimeout(intentState.streamReaderCancelTimeout);
      intentState.streamReaderCancelTimeout = null;
    }

    const canvasFactoryInstance = canvasFactory || new DefaultCanvasFactory({
      ownerDocument: this._ownerDocument
    });
    const intentPrint = !!(intentArgs.renderingIntent & _util.RenderingIntentFlag.PRINT);

    if (!intentState.displayReadyCapability) {
      intentState.displayReadyCapability = (0, _util.createPromiseCapability)();
      intentState.operatorList = {
        fnArray: [],
        argsArray: [],
        lastChunk: false,
        separateAnnots: null
      };

      if (this._stats) {
        this._stats.time("Page Request");
      }

      this._pumpOperatorList(intentArgs);
    }

    const complete = error => {
      intentState.renderTasks.delete(internalRenderTask);

      if (this.cleanupAfterRender || intentPrint) {
        this.pendingCleanup = true;
      }

      this._tryCleanup();

      if (error) {
        internalRenderTask.capability.reject(error);

        this._abortOperatorList({
          intentState,
          reason: error instanceof Error ? error : new Error(error)
        });
      } else {
        internalRenderTask.capability.resolve();
      }

      if (this._stats) {
        this._stats.timeEnd("Rendering");

        this._stats.timeEnd("Overall");
      }
    };

    const internalRenderTask = new InternalRenderTask({
      callback: complete,
      params: {
        canvasContext,
        viewport,
        transform,
        imageLayer,
        background
      },
      objs: this.objs,
      commonObjs: this.commonObjs,
      annotationCanvasMap,
      operatorList: intentState.operatorList,
      pageIndex: this._pageIndex,
      canvasFactory: canvasFactoryInstance,
      useRequestAnimationFrame: !intentPrint,
      pdfBug: this._pdfBug,
      pageColors
    });
    ((_intentState = intentState).renderTasks || (_intentState.renderTasks = new Set())).add(internalRenderTask);
    const renderTask = internalRenderTask.task;
    Promise.all([intentState.displayReadyCapability.promise, optionalContentConfigPromise]).then(_ref3 => {
      let [transparency, optionalContentConfig] = _ref3;

      if (this.pendingCleanup) {
        complete();
        return;
      }

      if (this._stats) {
        this._stats.time("Rendering");
      }

      internalRenderTask.initializeGraphics({
        transparency,
        optionalContentConfig
      });
      internalRenderTask.operatorListChanged();
    }).catch(complete);
    return renderTask;
  }

  getOperatorList() {
    let {
      intent = "display",
      annotationMode = _util.AnnotationMode.ENABLE,
      printAnnotationStorage = null
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

    function operatorListChanged() {
      if (intentState.operatorList.lastChunk) {
        intentState.opListReadCapability.resolve(intentState.operatorList);
        intentState.renderTasks.delete(opListTask);
      }
    }

    const intentArgs = this._transport.getRenderingIntent(intent, annotationMode, printAnnotationStorage, true);

    let intentState = this._intentStates.get(intentArgs.cacheKey);

    if (!intentState) {
      intentState = Object.create(null);

      this._intentStates.set(intentArgs.cacheKey, intentState);
    }

    let opListTask;

    if (!intentState.opListReadCapability) {
      var _intentState2;

      opListTask = Object.create(null);
      opListTask.operatorListChanged = operatorListChanged;
      intentState.opListReadCapability = (0, _util.createPromiseCapability)();
      ((_intentState2 = intentState).renderTasks || (_intentState2.renderTasks = new Set())).add(opListTask);
      intentState.operatorList = {
        fnArray: [],
        argsArray: [],
        lastChunk: false,
        separateAnnots: null
      };

      if (this._stats) {
        this._stats.time("Page Request");
      }

      this._pumpOperatorList(intentArgs);
    }

    return intentState.opListReadCapability.promise;
  }

  streamTextContent() {
    let {
      disableCombineTextItems = false,
      includeMarkedContent = false
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    const TEXT_CONTENT_CHUNK_SIZE = 100;
    return this._transport.messageHandler.sendWithStream("GetTextContent", {
      pageIndex: this._pageIndex,
      combineTextItems: disableCombineTextItems !== true,
      includeMarkedContent: includeMarkedContent === true
    }, {
      highWaterMark: TEXT_CONTENT_CHUNK_SIZE,

      size(textContent) {
        return textContent.items.length;
      }

    });
  }

  getTextContent() {
    let params = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

    if (this._transport._htmlForXfa) {
      return this.getXfa().then(xfa => {
        return _xfa_text.XfaText.textContent(xfa);
      });
    }

    const readableStream = this.streamTextContent(params);
    return new Promise(function (resolve, reject) {
      function pump() {
        reader.read().then(function (_ref4) {
          let {
            value,
            done
          } = _ref4;

          if (done) {
            resolve(textContent);
            return;
          }

          Object.assign(textContent.styles, value.styles);
          textContent.items.push(...value.items);
          pump();
        }, reject);
      }

      const reader = readableStream.getReader();
      const textContent = {
        items: [],
        styles: Object.create(null)
      };
      pump();
    });
  }

  getStructTree() {
    return this._structTreePromise || (this._structTreePromise = this._transport.getStructTree(this._pageIndex));
  }

  _destroy() {
    this.destroyed = true;
    const waitOn = [];

    for (const intentState of this._intentStates.values()) {
      this._abortOperatorList({
        intentState,
        reason: new Error("Page was destroyed."),
        force: true
      });

      if (intentState.opListReadCapability) {
        continue;
      }

      for (const internalRenderTask of intentState.renderTasks) {
        waitOn.push(internalRenderTask.completed);
        internalRenderTask.cancel();
      }
    }

    this.objs.clear();

    for (const bitmap of this._bitmaps) {
      bitmap.close();
    }

    this._bitmaps.clear();

    this._annotationPromises.clear();

    this._jsActionsPromise = null;
    this._structTreePromise = null;
    this.pendingCleanup = false;
    return Promise.all(waitOn);
  }

  cleanup() {
    let resetStats = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;
    this.pendingCleanup = true;
    return this._tryCleanup(resetStats);
  }

  _tryCleanup() {
    let resetStats = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

    if (!this.pendingCleanup) {
      return false;
    }

    for (const {
      renderTasks,
      operatorList
    } of this._intentStates.values()) {
      if (renderTasks.size > 0 || !operatorList.lastChunk) {
        return false;
      }
    }

    this._intentStates.clear();

    this.objs.clear();

    this._annotationPromises.clear();

    this._jsActionsPromise = null;
    this._structTreePromise = null;

    if (resetStats && this._stats) {
      this._stats = new _display_utils.StatTimer();
    }

    for (const bitmap of this._bitmaps) {
      bitmap.close();
    }

    this._bitmaps.clear();

    this.pendingCleanup = false;
    return true;
  }

  _startRenderPage(transparency, cacheKey) {
    const intentState = this._intentStates.get(cacheKey);

    if (!intentState) {
      return;
    }

    if (this._stats) {
      this._stats.timeEnd("Page Request");
    }

    if (intentState.displayReadyCapability) {
      intentState.displayReadyCapability.resolve(transparency);
    }
  }

  _renderPageChunk(operatorListChunk, intentState) {
    for (let i = 0, ii = operatorListChunk.length; i < ii; i++) {
      intentState.operatorList.fnArray.push(operatorListChunk.fnArray[i]);
      intentState.operatorList.argsArray.push(operatorListChunk.argsArray[i]);
    }

    intentState.operatorList.lastChunk = operatorListChunk.lastChunk;
    intentState.operatorList.separateAnnots = operatorListChunk.separateAnnots;

    for (const internalRenderTask of intentState.renderTasks) {
      internalRenderTask.operatorListChanged();
    }

    if (operatorListChunk.lastChunk) {
      this._tryCleanup();
    }
  }

  _pumpOperatorList(_ref5) {
    let {
      renderingIntent,
      cacheKey,
      annotationStorageMap
    } = _ref5;

    const readableStream = this._transport.messageHandler.sendWithStream("GetOperatorList", {
      pageIndex: this._pageIndex,
      intent: renderingIntent,
      cacheKey,
      annotationStorage: annotationStorageMap
    });

    const reader = readableStream.getReader();

    const intentState = this._intentStates.get(cacheKey);

    intentState.streamReader = reader;

    const pump = () => {
      reader.read().then(_ref6 => {
        let {
          value,
          done
        } = _ref6;

        if (done) {
          intentState.streamReader = null;
          return;
        }

        if (this._transport.destroyed) {
          return;
        }

        this._renderPageChunk(value, intentState);

        pump();
      }, reason => {
        intentState.streamReader = null;

        if (this._transport.destroyed) {
          return;
        }

        if (intentState.operatorList) {
          intentState.operatorList.lastChunk = true;

          for (const internalRenderTask of intentState.renderTasks) {
            internalRenderTask.operatorListChanged();
          }

          this._tryCleanup();
        }

        if (intentState.displayReadyCapability) {
          intentState.displayReadyCapability.reject(reason);
        } else if (intentState.opListReadCapability) {
          intentState.opListReadCapability.reject(reason);
        } else {
          throw reason;
        }
      });
    };

    pump();
  }

  _abortOperatorList(_ref7) {
    let {
      intentState,
      reason,
      force = false
    } = _ref7;

    if (!intentState.streamReader) {
      return;
    }

    if (!force) {
      if (intentState.renderTasks.size > 0) {
        return;
      }

      if (reason instanceof _display_utils.RenderingCancelledException) {
        intentState.streamReaderCancelTimeout = setTimeout(() => {
          this._abortOperatorList({
            intentState,
            reason,
            force: true
          });

          intentState.streamReaderCancelTimeout = null;
        }, RENDERING_CANCELLED_TIMEOUT);
        return;
      }
    }

    intentState.streamReader.cancel(new _util.AbortException(reason.message)).catch(() => {});
    intentState.streamReader = null;

    if (this._transport.destroyed) {
      return;
    }

    for (const [curCacheKey, curIntentState] of this._intentStates) {
      if (curIntentState === intentState) {
        this._intentStates.delete(curCacheKey);

        break;
      }
    }

    this.cleanup();
  }

  get stats() {
    return this._stats;
  }

}

exports.PDFPageProxy = PDFPageProxy;

class LoopbackPort {
  constructor() {
    this._listeners = [];
    this._deferred = Promise.resolve();
  }

  postMessage(obj, transfers) {
    const event = {
      data: structuredClone(obj, transfers)
    };

    this._deferred.then(() => {
      for (const listener of this._listeners) {
        listener.call(this, event);
      }
    });
  }

  addEventListener(name, listener) {
    this._listeners.push(listener);
  }

  removeEventListener(name, listener) {
    const i = this._listeners.indexOf(listener);

    this._listeners.splice(i, 1);
  }

  terminate() {
    this._listeners.length = 0;
  }

}

exports.LoopbackPort = LoopbackPort;
const PDFWorkerUtil = {
  isWorkerDisabled: false,
  fallbackWorkerSrc: null,
  fakeWorkerId: 0
};
exports.PDFWorkerUtil = PDFWorkerUtil;
{
  if (_is_node.isNodeJS && typeof require === "function") {
    PDFWorkerUtil.isWorkerDisabled = true;
    PDFWorkerUtil.fallbackWorkerSrc = "./pdf.worker.js";
  } else if (typeof document === "object") {
    var _document, _document$currentScri;

    const pdfjsFilePath = (_document = document) === null || _document === void 0 ? void 0 : (_document$currentScri = _document.currentScript) === null || _document$currentScri === void 0 ? void 0 : _document$currentScri.src;

    if (pdfjsFilePath) {
      PDFWorkerUtil.fallbackWorkerSrc = pdfjsFilePath.replace(/(\.(?:min\.)?js)(\?.*)?$/i, ".worker$1$2");
    }
  }

  PDFWorkerUtil.isSameOrigin = function (baseUrl, otherUrl) {
    let base;

    try {
      base = new URL(baseUrl);

      if (!base.origin || base.origin === "null") {
        return false;
      }
    } catch (e) {
      return false;
    }

    const other = new URL(otherUrl, base);
    return base.origin === other.origin;
  };

  PDFWorkerUtil.createCDNWrapper = function (url) {
    const wrapper = `importScripts("${url}");`;
    return URL.createObjectURL(new Blob([wrapper]));
  };
}

class PDFWorker {
  constructor() {
    let {
      name = null,
      port = null,
      verbosity = (0, _util.getVerbosityLevel)()
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

    if (port && _classStaticPrivateFieldSpecGet(PDFWorker, PDFWorker, _workerPorts).has(port)) {
      throw new Error("Cannot use more than one PDFWorker per port.");
    }

    this.name = name;
    this.destroyed = false;
    this.verbosity = verbosity;
    this._readyCapability = (0, _util.createPromiseCapability)();
    this._port = null;
    this._webWorker = null;
    this._messageHandler = null;

    if (port) {
      _classStaticPrivateFieldSpecGet(PDFWorker, PDFWorker, _workerPorts).set(port, this);

      this._initializeFromPort(port);

      return;
    }

    this._initialize();
  }

  get promise() {
    return this._readyCapability.promise;
  }

  get port() {
    return this._port;
  }

  get messageHandler() {
    return this._messageHandler;
  }

  _initializeFromPort(port) {
    this._port = port;
    this._messageHandler = new _message_handler.MessageHandler("main", "worker", port);

    this._messageHandler.on("ready", function () {});

    this._readyCapability.resolve();
  }

  _initialize() {
    if (!PDFWorkerUtil.isWorkerDisabled && !PDFWorker._mainThreadWorkerMessageHandler) {
      let {
        workerSrc
      } = PDFWorker;

      try {
        if (!PDFWorkerUtil.isSameOrigin(window.location.href, workerSrc)) {
          workerSrc = PDFWorkerUtil.createCDNWrapper(new URL(workerSrc, window.location).href);
        }

        const worker = new Worker(workerSrc);
        const messageHandler = new _message_handler.MessageHandler("main", "worker", worker);

        const terminateEarly = () => {
          worker.removeEventListener("error", onWorkerError);
          messageHandler.destroy();
          worker.terminate();

          if (this.destroyed) {
            this._readyCapability.reject(new Error("Worker was destroyed"));
          } else {
            this._setupFakeWorker();
          }
        };

        const onWorkerError = () => {
          if (!this._webWorker) {
            terminateEarly();
          }
        };

        worker.addEventListener("error", onWorkerError);
        messageHandler.on("test", data => {
          worker.removeEventListener("error", onWorkerError);

          if (this.destroyed) {
            terminateEarly();
            return;
          }

          if (data) {
            this._messageHandler = messageHandler;
            this._port = worker;
            this._webWorker = worker;

            this._readyCapability.resolve();

            messageHandler.send("configure", {
              verbosity: this.verbosity
            });
          } else {
            this._setupFakeWorker();

            messageHandler.destroy();
            worker.terminate();
          }
        });
        messageHandler.on("ready", data => {
          worker.removeEventListener("error", onWorkerError);

          if (this.destroyed) {
            terminateEarly();
            return;
          }

          try {
            sendTest();
          } catch (e) {
            this._setupFakeWorker();
          }
        });

        const sendTest = () => {
          const testObj = new Uint8Array();
          messageHandler.send("test", testObj, [testObj.buffer]);
        };

        sendTest();
        return;
      } catch (e) {
        (0, _util.info)("The worker has been disabled.");
      }
    }

    this._setupFakeWorker();
  }

  _setupFakeWorker() {
    if (!PDFWorkerUtil.isWorkerDisabled) {
      (0, _util.warn)("Setting up fake worker.");
      PDFWorkerUtil.isWorkerDisabled = true;
    }

    PDFWorker._setupFakeWorkerGlobal.then(WorkerMessageHandler => {
      if (this.destroyed) {
        this._readyCapability.reject(new Error("Worker was destroyed"));

        return;
      }

      const port = new LoopbackPort();
      this._port = port;
      const id = `fake${PDFWorkerUtil.fakeWorkerId++}`;
      const workerHandler = new _message_handler.MessageHandler(id + "_worker", id, port);
      WorkerMessageHandler.setup(workerHandler, port);
      const messageHandler = new _message_handler.MessageHandler(id, id + "_worker", port);
      this._messageHandler = messageHandler;

      this._readyCapability.resolve();

      messageHandler.send("configure", {
        verbosity: this.verbosity
      });
    }).catch(reason => {
      this._readyCapability.reject(new Error(`Setting up fake worker failed: "${reason.message}".`));
    });
  }

  destroy() {
    this.destroyed = true;

    if (this._webWorker) {
      this._webWorker.terminate();

      this._webWorker = null;
    }

    _classStaticPrivateFieldSpecGet(PDFWorker, PDFWorker, _workerPorts).delete(this._port);

    this._port = null;

    if (this._messageHandler) {
      this._messageHandler.destroy();

      this._messageHandler = null;
    }
  }

  static fromPort(params) {
    if (!(params !== null && params !== void 0 && params.port)) {
      throw new Error("PDFWorker.fromPort - invalid method signature.");
    }

    if (_classStaticPrivateFieldSpecGet(this, PDFWorker, _workerPorts).has(params.port)) {
      return _classStaticPrivateFieldSpecGet(this, PDFWorker, _workerPorts).get(params.port);
    }

    return new PDFWorker(params);
  }

  static get workerSrc() {
    if (_worker_options.GlobalWorkerOptions.workerSrc) {
      return _worker_options.GlobalWorkerOptions.workerSrc;
    }

    if (PDFWorkerUtil.fallbackWorkerSrc !== null) {
      if (!_is_node.isNodeJS) {
        (0, _display_utils.deprecated)('No "GlobalWorkerOptions.workerSrc" specified.');
      }

      return PDFWorkerUtil.fallbackWorkerSrc;
    }

    throw new Error('No "GlobalWorkerOptions.workerSrc" specified.');
  }

  static get _mainThreadWorkerMessageHandler() {
    try {
      var _globalThis$pdfjsWork;

      return ((_globalThis$pdfjsWork = globalThis.pdfjsWorker) === null || _globalThis$pdfjsWork === void 0 ? void 0 : _globalThis$pdfjsWork.WorkerMessageHandler) || null;
    } catch (ex) {
      return null;
    }
  }

  static get _setupFakeWorkerGlobal() {
    const loader = async () => {
      const mainWorkerMessageHandler = this._mainThreadWorkerMessageHandler;

      if (mainWorkerMessageHandler) {
        return mainWorkerMessageHandler;
      }

      if (_is_node.isNodeJS && typeof require === "function") {
        const worker = eval("require")(this.workerSrc);
        return worker.WorkerMessageHandler;
      }

      await (0, _display_utils.loadScript)(this.workerSrc);
      return window.pdfjsWorker.WorkerMessageHandler;
    };

    return (0, _util.shadow)(this, "_setupFakeWorkerGlobal", loader());
  }

}

exports.PDFWorker = PDFWorker;
var _workerPorts = {
  writable: true,
  value: new WeakMap()
};
{
  PDFWorker.getWorkerSrc = function () {
    (0, _display_utils.deprecated)("`PDFWorker.getWorkerSrc()`, please use `PDFWorker.workerSrc` instead.");
    return this.workerSrc;
  };
}

var _docStats = /*#__PURE__*/new WeakMap();

var _pageCache = /*#__PURE__*/new WeakMap();

var _pagePromises = /*#__PURE__*/new WeakMap();

var _metadataPromise = /*#__PURE__*/new WeakMap();

class WorkerTransport {
  constructor(messageHandler, loadingTask, networkStream, params) {
    _classPrivateFieldInitSpec(this, _docStats, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _pageCache, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _pagePromises, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _metadataPromise, {
      writable: true,
      value: null
    });

    this.messageHandler = messageHandler;
    this.loadingTask = loadingTask;
    this.commonObjs = new PDFObjects();
    this.fontLoader = new _font_loader.FontLoader({
      docId: loadingTask.docId,
      onUnsupportedFeature: this._onUnsupportedFeature.bind(this),
      ownerDocument: params.ownerDocument,
      styleElement: params.styleElement
    });
    this._params = params;

    if (!params.useWorkerFetch) {
      this.CMapReaderFactory = new params.CMapReaderFactory({
        baseUrl: params.cMapUrl,
        isCompressed: params.cMapPacked
      });
      this.StandardFontDataFactory = new params.StandardFontDataFactory({
        baseUrl: params.standardFontDataUrl
      });
    }

    this.destroyed = false;
    this.destroyCapability = null;
    this._passwordCapability = null;
    this._networkStream = networkStream;
    this._fullReader = null;
    this._lastProgress = null;
    this.downloadInfoCapability = (0, _util.createPromiseCapability)();
    this.setupMessageHandler();
  }

  get annotationStorage() {
    return (0, _util.shadow)(this, "annotationStorage", new _annotation_storage.AnnotationStorage());
  }

  get stats() {
    return _classPrivateFieldGet(this, _docStats);
  }

  getRenderingIntent(intent) {
    let annotationMode = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : _util.AnnotationMode.ENABLE;
    let printAnnotationStorage = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
    let isOpList = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : false;
    let renderingIntent = _util.RenderingIntentFlag.DISPLAY;
    let annotationMap = null;

    switch (intent) {
      case "any":
        renderingIntent = _util.RenderingIntentFlag.ANY;
        break;

      case "display":
        break;

      case "print":
        renderingIntent = _util.RenderingIntentFlag.PRINT;
        break;

      default:
        (0, _util.warn)(`getRenderingIntent - invalid intent: ${intent}`);
    }

    switch (annotationMode) {
      case _util.AnnotationMode.DISABLE:
        renderingIntent += _util.RenderingIntentFlag.ANNOTATIONS_DISABLE;
        break;

      case _util.AnnotationMode.ENABLE:
        break;

      case _util.AnnotationMode.ENABLE_FORMS:
        renderingIntent += _util.RenderingIntentFlag.ANNOTATIONS_FORMS;
        break;

      case _util.AnnotationMode.ENABLE_STORAGE:
        renderingIntent += _util.RenderingIntentFlag.ANNOTATIONS_STORAGE;
        const annotationStorage = renderingIntent & _util.RenderingIntentFlag.PRINT && printAnnotationStorage instanceof _annotation_storage.PrintAnnotationStorage ? printAnnotationStorage : this.annotationStorage;
        annotationMap = annotationStorage.serializable;
        break;

      default:
        (0, _util.warn)(`getRenderingIntent - invalid annotationMode: ${annotationMode}`);
    }

    if (isOpList) {
      renderingIntent += _util.RenderingIntentFlag.OPLIST;
    }

    return {
      renderingIntent,
      cacheKey: `${renderingIntent}_${_annotation_storage.AnnotationStorage.getHash(annotationMap)}`,
      annotationStorageMap: annotationMap
    };
  }

  destroy() {
    if (this.destroyCapability) {
      return this.destroyCapability.promise;
    }

    this.destroyed = true;
    this.destroyCapability = (0, _util.createPromiseCapability)();

    if (this._passwordCapability) {
      this._passwordCapability.reject(new Error("Worker was destroyed during onPassword callback"));
    }

    const waitOn = [];

    for (const page of _classPrivateFieldGet(this, _pageCache).values()) {
      waitOn.push(page._destroy());
    }

    _classPrivateFieldGet(this, _pageCache).clear();

    _classPrivateFieldGet(this, _pagePromises).clear();

    if (this.hasOwnProperty("annotationStorage")) {
      this.annotationStorage.resetModified();
    }

    const terminated = this.messageHandler.sendWithPromise("Terminate", null);
    waitOn.push(terminated);
    Promise.all(waitOn).then(() => {
      this.commonObjs.clear();
      this.fontLoader.clear();

      _classPrivateFieldSet(this, _metadataPromise, null);

      this._getFieldObjectsPromise = null;
      this._hasJSActionsPromise = null;

      if (this._networkStream) {
        this._networkStream.cancelAllRequests(new _util.AbortException("Worker was terminated."));
      }

      if (this.messageHandler) {
        this.messageHandler.destroy();
        this.messageHandler = null;
      }

      this.destroyCapability.resolve();
    }, this.destroyCapability.reject);
    return this.destroyCapability.promise;
  }

  setupMessageHandler() {
    const {
      messageHandler,
      loadingTask
    } = this;
    messageHandler.on("GetReader", (data, sink) => {
      (0, _util.assert)(this._networkStream, "GetReader - no `IPDFStream` instance available.");
      this._fullReader = this._networkStream.getFullReader();

      this._fullReader.onProgress = evt => {
        this._lastProgress = {
          loaded: evt.loaded,
          total: evt.total
        };
      };

      sink.onPull = () => {
        this._fullReader.read().then(function (_ref8) {
          let {
            value,
            done
          } = _ref8;

          if (done) {
            sink.close();
            return;
          }

          (0, _util.assert)((0, _util.isArrayBuffer)(value), "GetReader - expected an ArrayBuffer.");
          sink.enqueue(new Uint8Array(value), 1, [value]);
        }).catch(reason => {
          sink.error(reason);
        });
      };

      sink.onCancel = reason => {
        this._fullReader.cancel(reason);

        sink.ready.catch(readyReason => {
          if (this.destroyed) {
            return;
          }

          throw readyReason;
        });
      };
    });
    messageHandler.on("ReaderHeadersReady", data => {
      const headersCapability = (0, _util.createPromiseCapability)();
      const fullReader = this._fullReader;
      fullReader.headersReady.then(() => {
        if (!fullReader.isStreamingSupported || !fullReader.isRangeSupported) {
          if (this._lastProgress) {
            var _loadingTask$onProgre;

            (_loadingTask$onProgre = loadingTask.onProgress) === null || _loadingTask$onProgre === void 0 ? void 0 : _loadingTask$onProgre.call(loadingTask, this._lastProgress);
          }

          fullReader.onProgress = evt => {
            var _loadingTask$onProgre2;

            (_loadingTask$onProgre2 = loadingTask.onProgress) === null || _loadingTask$onProgre2 === void 0 ? void 0 : _loadingTask$onProgre2.call(loadingTask, {
              loaded: evt.loaded,
              total: evt.total
            });
          };
        }

        headersCapability.resolve({
          isStreamingSupported: fullReader.isStreamingSupported,
          isRangeSupported: fullReader.isRangeSupported,
          contentLength: fullReader.contentLength
        });
      }, headersCapability.reject);
      return headersCapability.promise;
    });
    messageHandler.on("GetRangeReader", (data, sink) => {
      (0, _util.assert)(this._networkStream, "GetRangeReader - no `IPDFStream` instance available.");

      const rangeReader = this._networkStream.getRangeReader(data.begin, data.end);

      if (!rangeReader) {
        sink.close();
        return;
      }

      sink.onPull = () => {
        rangeReader.read().then(function (_ref9) {
          let {
            value,
            done
          } = _ref9;

          if (done) {
            sink.close();
            return;
          }

          (0, _util.assert)((0, _util.isArrayBuffer)(value), "GetRangeReader - expected an ArrayBuffer.");
          sink.enqueue(new Uint8Array(value), 1, [value]);
        }).catch(reason => {
          sink.error(reason);
        });
      };

      sink.onCancel = reason => {
        rangeReader.cancel(reason);
        sink.ready.catch(readyReason => {
          if (this.destroyed) {
            return;
          }

          throw readyReason;
        });
      };
    });
    messageHandler.on("GetDoc", _ref10 => {
      let {
        pdfInfo
      } = _ref10;
      this._numPages = pdfInfo.numPages;
      this._htmlForXfa = pdfInfo.htmlForXfa;
      delete pdfInfo.htmlForXfa;

      loadingTask._capability.resolve(new PDFDocumentProxy(pdfInfo, this));
    });
    messageHandler.on("DocException", function (ex) {
      let reason;

      switch (ex.name) {
        case "PasswordException":
          reason = new _util.PasswordException(ex.message, ex.code);
          break;

        case "InvalidPDFException":
          reason = new _util.InvalidPDFException(ex.message);
          break;

        case "MissingPDFException":
          reason = new _util.MissingPDFException(ex.message);
          break;

        case "UnexpectedResponseException":
          reason = new _util.UnexpectedResponseException(ex.message, ex.status);
          break;

        case "UnknownErrorException":
          reason = new _util.UnknownErrorException(ex.message, ex.details);
          break;

        default:
          (0, _util.unreachable)("DocException - expected a valid Error.");
      }

      loadingTask._capability.reject(reason);
    });
    messageHandler.on("PasswordRequest", exception => {
      this._passwordCapability = (0, _util.createPromiseCapability)();

      if (loadingTask.onPassword) {
        const updatePassword = password => {
          if (password instanceof Error) {
            this._passwordCapability.reject(password);
          } else {
            this._passwordCapability.resolve({
              password
            });
          }
        };

        try {
          loadingTask.onPassword(updatePassword, exception.code);
        } catch (ex) {
          this._passwordCapability.reject(ex);
        }
      } else {
        this._passwordCapability.reject(new _util.PasswordException(exception.message, exception.code));
      }

      return this._passwordCapability.promise;
    });
    messageHandler.on("DataLoaded", data => {
      var _loadingTask$onProgre3;

      (_loadingTask$onProgre3 = loadingTask.onProgress) === null || _loadingTask$onProgre3 === void 0 ? void 0 : _loadingTask$onProgre3.call(loadingTask, {
        loaded: data.length,
        total: data.length
      });
      this.downloadInfoCapability.resolve(data);
    });
    messageHandler.on("StartRenderPage", data => {
      if (this.destroyed) {
        return;
      }

      const page = _classPrivateFieldGet(this, _pageCache).get(data.pageIndex);

      page._startRenderPage(data.transparency, data.cacheKey);
    });
    messageHandler.on("commonobj", _ref11 => {
      var _globalThis$FontInspe;

      let [id, type, exportedData] = _ref11;

      if (this.destroyed) {
        return;
      }

      if (this.commonObjs.has(id)) {
        return;
      }

      switch (type) {
        case "Font":
          const params = this._params;

          if ("error" in exportedData) {
            const exportedError = exportedData.error;
            (0, _util.warn)(`Error during font loading: ${exportedError}`);
            this.commonObjs.resolve(id, exportedError);
            break;
          }

          let fontRegistry = null;

          if (params.pdfBug && (_globalThis$FontInspe = globalThis.FontInspector) !== null && _globalThis$FontInspe !== void 0 && _globalThis$FontInspe.enabled) {
            fontRegistry = {
              registerFont(font, url) {
                globalThis.FontInspector.fontAdded(font, url);
              }

            };
          }

          const font = new _font_loader.FontFaceObject(exportedData, {
            isEvalSupported: params.isEvalSupported,
            disableFontFace: params.disableFontFace,
            ignoreErrors: params.ignoreErrors,
            onUnsupportedFeature: this._onUnsupportedFeature.bind(this),
            fontRegistry
          });
          this.fontLoader.bind(font).catch(reason => {
            return messageHandler.sendWithPromise("FontFallback", {
              id
            });
          }).finally(() => {
            if (!params.fontExtraProperties && font.data) {
              font.data = null;
            }

            this.commonObjs.resolve(id, font);
          });
          break;

        case "FontPath":
        case "Image":
          this.commonObjs.resolve(id, exportedData);
          break;

        default:
          throw new Error(`Got unknown common object type ${type}`);
      }
    });
    messageHandler.on("obj", _ref12 => {
      let [id, pageIndex, type, imageData] = _ref12;

      if (this.destroyed) {
        return;
      }

      const pageProxy = _classPrivateFieldGet(this, _pageCache).get(pageIndex);

      if (pageProxy.objs.has(id)) {
        return;
      }

      switch (type) {
        case "Image":
          pageProxy.objs.resolve(id, imageData);
          const MAX_IMAGE_SIZE_TO_STORE = 8000000;

          if (imageData) {
            let length;

            if (imageData.bitmap) {
              const {
                bitmap,
                width,
                height
              } = imageData;
              length = width * height * 4;

              pageProxy._bitmaps.add(bitmap);
            } else {
              var _imageData$data;

              length = ((_imageData$data = imageData.data) === null || _imageData$data === void 0 ? void 0 : _imageData$data.length) || 0;
            }

            if (length > MAX_IMAGE_SIZE_TO_STORE) {
              pageProxy.cleanupAfterRender = true;
            }
          }

          break;

        case "Pattern":
          pageProxy.objs.resolve(id, imageData);
          break;

        default:
          throw new Error(`Got unknown object type ${type}`);
      }
    });
    messageHandler.on("DocProgress", data => {
      var _loadingTask$onProgre4;

      if (this.destroyed) {
        return;
      }

      (_loadingTask$onProgre4 = loadingTask.onProgress) === null || _loadingTask$onProgre4 === void 0 ? void 0 : _loadingTask$onProgre4.call(loadingTask, {
        loaded: data.loaded,
        total: data.total
      });
    });
    messageHandler.on("DocStats", data => {
      if (this.destroyed) {
        return;
      }

      _classPrivateFieldSet(this, _docStats, Object.freeze({
        streamTypes: Object.freeze(data.streamTypes),
        fontTypes: Object.freeze(data.fontTypes)
      }));
    });
    messageHandler.on("UnsupportedFeature", this._onUnsupportedFeature.bind(this));
    messageHandler.on("FetchBuiltInCMap", data => {
      if (this.destroyed) {
        return Promise.reject(new Error("Worker was destroyed."));
      }

      if (!this.CMapReaderFactory) {
        return Promise.reject(new Error("CMapReaderFactory not initialized, see the `useWorkerFetch` parameter."));
      }

      return this.CMapReaderFactory.fetch(data);
    });
    messageHandler.on("FetchStandardFontData", data => {
      if (this.destroyed) {
        return Promise.reject(new Error("Worker was destroyed."));
      }

      if (!this.StandardFontDataFactory) {
        return Promise.reject(new Error("StandardFontDataFactory not initialized, see the `useWorkerFetch` parameter."));
      }

      return this.StandardFontDataFactory.fetch(data);
    });
  }

  _onUnsupportedFeature(_ref13) {
    var _this$loadingTask$onU, _this$loadingTask;

    let {
      featureId
    } = _ref13;

    if (this.destroyed) {
      return;
    }

    (_this$loadingTask$onU = (_this$loadingTask = this.loadingTask).onUnsupportedFeature) === null || _this$loadingTask$onU === void 0 ? void 0 : _this$loadingTask$onU.call(_this$loadingTask, featureId);
  }

  getData() {
    return this.messageHandler.sendWithPromise("GetData", null);
  }

  getPage(pageNumber) {
    if (!Number.isInteger(pageNumber) || pageNumber <= 0 || pageNumber > this._numPages) {
      return Promise.reject(new Error("Invalid page request."));
    }

    const pageIndex = pageNumber - 1,
          cachedPromise = _classPrivateFieldGet(this, _pagePromises).get(pageIndex);

    if (cachedPromise) {
      return cachedPromise;
    }

    const promise = this.messageHandler.sendWithPromise("GetPage", {
      pageIndex
    }).then(pageInfo => {
      if (this.destroyed) {
        throw new Error("Transport destroyed");
      }

      const page = new PDFPageProxy(pageIndex, pageInfo, this, this._params.ownerDocument, this._params.pdfBug);

      _classPrivateFieldGet(this, _pageCache).set(pageIndex, page);

      return page;
    });

    _classPrivateFieldGet(this, _pagePromises).set(pageIndex, promise);

    return promise;
  }

  getPageIndex(ref) {
    if (typeof ref !== "object" || ref === null || !Number.isInteger(ref.num) || ref.num < 0 || !Number.isInteger(ref.gen) || ref.gen < 0) {
      return Promise.reject(new Error("Invalid pageIndex request."));
    }

    return this.messageHandler.sendWithPromise("GetPageIndex", {
      num: ref.num,
      gen: ref.gen
    });
  }

  getAnnotations(pageIndex, intent) {
    return this.messageHandler.sendWithPromise("GetAnnotations", {
      pageIndex,
      intent
    });
  }

  saveDocument() {
    var _this$_fullReader$fil, _this$_fullReader;

    return this.messageHandler.sendWithPromise("SaveDocument", {
      isPureXfa: !!this._htmlForXfa,
      numPages: this._numPages,
      annotationStorage: this.annotationStorage.serializable,
      filename: (_this$_fullReader$fil = (_this$_fullReader = this._fullReader) === null || _this$_fullReader === void 0 ? void 0 : _this$_fullReader.filename) !== null && _this$_fullReader$fil !== void 0 ? _this$_fullReader$fil : null
    }).finally(() => {
      this.annotationStorage.resetModified();
    });
  }

  getFieldObjects() {
    return this._getFieldObjectsPromise || (this._getFieldObjectsPromise = this.messageHandler.sendWithPromise("GetFieldObjects", null));
  }

  hasJSActions() {
    return this._hasJSActionsPromise || (this._hasJSActionsPromise = this.messageHandler.sendWithPromise("HasJSActions", null));
  }

  getCalculationOrderIds() {
    return this.messageHandler.sendWithPromise("GetCalculationOrderIds", null);
  }

  getDestinations() {
    return this.messageHandler.sendWithPromise("GetDestinations", null);
  }

  getDestination(id) {
    if (typeof id !== "string") {
      return Promise.reject(new Error("Invalid destination request."));
    }

    return this.messageHandler.sendWithPromise("GetDestination", {
      id
    });
  }

  getPageLabels() {
    return this.messageHandler.sendWithPromise("GetPageLabels", null);
  }

  getPageLayout() {
    return this.messageHandler.sendWithPromise("GetPageLayout", null);
  }

  getPageMode() {
    return this.messageHandler.sendWithPromise("GetPageMode", null);
  }

  getViewerPreferences() {
    return this.messageHandler.sendWithPromise("GetViewerPreferences", null);
  }

  getOpenAction() {
    return this.messageHandler.sendWithPromise("GetOpenAction", null);
  }

  getAttachments() {
    return this.messageHandler.sendWithPromise("GetAttachments", null);
  }

  getJavaScript() {
    return this.messageHandler.sendWithPromise("GetJavaScript", null);
  }

  getDocJSActions() {
    return this.messageHandler.sendWithPromise("GetDocJSActions", null);
  }

  getPageJSActions(pageIndex) {
    return this.messageHandler.sendWithPromise("GetPageJSActions", {
      pageIndex
    });
  }

  getStructTree(pageIndex) {
    return this.messageHandler.sendWithPromise("GetStructTree", {
      pageIndex
    });
  }

  getOutline() {
    return this.messageHandler.sendWithPromise("GetOutline", null);
  }

  getOptionalContentConfig() {
    return this.messageHandler.sendWithPromise("GetOptionalContentConfig", null).then(results => {
      return new _optional_content_config.OptionalContentConfig(results);
    });
  }

  getPermissions() {
    return this.messageHandler.sendWithPromise("GetPermissions", null);
  }

  getMetadata() {
    return _classPrivateFieldGet(this, _metadataPromise) || _classPrivateFieldSet(this, _metadataPromise, this.messageHandler.sendWithPromise("GetMetadata", null).then(results => {
      var _this$_fullReader$fil2, _this$_fullReader2, _this$_fullReader$con, _this$_fullReader3;

      return {
        info: results[0],
        metadata: results[1] ? new _metadata.Metadata(results[1]) : null,
        contentDispositionFilename: (_this$_fullReader$fil2 = (_this$_fullReader2 = this._fullReader) === null || _this$_fullReader2 === void 0 ? void 0 : _this$_fullReader2.filename) !== null && _this$_fullReader$fil2 !== void 0 ? _this$_fullReader$fil2 : null,
        contentLength: (_this$_fullReader$con = (_this$_fullReader3 = this._fullReader) === null || _this$_fullReader3 === void 0 ? void 0 : _this$_fullReader3.contentLength) !== null && _this$_fullReader$con !== void 0 ? _this$_fullReader$con : null
      };
    }));
  }

  getMarkInfo() {
    return this.messageHandler.sendWithPromise("GetMarkInfo", null);
  }

  async startCleanup() {
    let keepLoadedFonts = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;
    await this.messageHandler.sendWithPromise("Cleanup", null);

    if (this.destroyed) {
      return;
    }

    for (const page of _classPrivateFieldGet(this, _pageCache).values()) {
      const cleanupSuccessful = page.cleanup();

      if (!cleanupSuccessful) {
        throw new Error(`startCleanup: Page ${page.pageNumber} is currently rendering.`);
      }
    }

    this.commonObjs.clear();

    if (!keepLoadedFonts) {
      this.fontLoader.clear();
    }

    _classPrivateFieldSet(this, _metadataPromise, null);

    this._getFieldObjectsPromise = null;
    this._hasJSActionsPromise = null;
  }

  get loadingParams() {
    const params = this._params;
    return (0, _util.shadow)(this, "loadingParams", {
      disableAutoFetch: params.disableAutoFetch,
      enableXfa: params.enableXfa
    });
  }

}

var _objs = /*#__PURE__*/new WeakMap();

var _ensureObj = /*#__PURE__*/new WeakSet();

class PDFObjects {
  constructor() {
    _classPrivateMethodInitSpec(this, _ensureObj);

    _classPrivateFieldInitSpec(this, _objs, {
      writable: true,
      value: Object.create(null)
    });
  }

  get(objId) {
    let callback = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

    if (callback) {
      const obj = _classPrivateMethodGet(this, _ensureObj, _ensureObj2).call(this, objId);

      obj.capability.promise.then(() => callback(obj.data));
      return null;
    }

    const obj = _classPrivateFieldGet(this, _objs)[objId];

    if (!(obj !== null && obj !== void 0 && obj.capability.settled)) {
      throw new Error(`Requesting object that isn't resolved yet ${objId}.`);
    }

    return obj.data;
  }

  has(objId) {
    const obj = _classPrivateFieldGet(this, _objs)[objId];

    return (obj === null || obj === void 0 ? void 0 : obj.capability.settled) || false;
  }

  resolve(objId) {
    let data = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

    const obj = _classPrivateMethodGet(this, _ensureObj, _ensureObj2).call(this, objId);

    obj.data = data;
    obj.capability.resolve();
  }

  clear() {
    _classPrivateFieldSet(this, _objs, Object.create(null));
  }

}

function _ensureObj2(objId) {
  const obj = _classPrivateFieldGet(this, _objs)[objId];

  if (obj) {
    return obj;
  }

  return _classPrivateFieldGet(this, _objs)[objId] = {
    capability: (0, _util.createPromiseCapability)(),
    data: null
  };
}

var _internalRenderTask = /*#__PURE__*/new WeakMap();

class RenderTask {
  constructor(internalRenderTask) {
    _classPrivateFieldInitSpec(this, _internalRenderTask, {
      writable: true,
      value: null
    });

    _classPrivateFieldSet(this, _internalRenderTask, internalRenderTask);

    this.onContinue = null;
  }

  get promise() {
    return _classPrivateFieldGet(this, _internalRenderTask).capability.promise;
  }

  cancel() {
    _classPrivateFieldGet(this, _internalRenderTask).cancel();
  }

  get separateAnnots() {
    const {
      separateAnnots
    } = _classPrivateFieldGet(this, _internalRenderTask).operatorList;

    if (!separateAnnots) {
      return false;
    }

    const {
      annotationCanvasMap
    } = _classPrivateFieldGet(this, _internalRenderTask);

    return separateAnnots.form || separateAnnots.canvas && (annotationCanvasMap === null || annotationCanvasMap === void 0 ? void 0 : annotationCanvasMap.size) > 0;
  }

}

exports.RenderTask = RenderTask;

class InternalRenderTask {
  constructor(_ref14) {
    let {
      callback,
      params,
      objs,
      commonObjs,
      annotationCanvasMap,
      operatorList,
      pageIndex,
      canvasFactory,
      useRequestAnimationFrame = false,
      pdfBug = false,
      pageColors = null
    } = _ref14;
    this.callback = callback;
    this.params = params;
    this.objs = objs;
    this.commonObjs = commonObjs;
    this.annotationCanvasMap = annotationCanvasMap;
    this.operatorListIdx = null;
    this.operatorList = operatorList;
    this._pageIndex = pageIndex;
    this.canvasFactory = canvasFactory;
    this._pdfBug = pdfBug;
    this.pageColors = pageColors;
    this.running = false;
    this.graphicsReadyCallback = null;
    this.graphicsReady = false;
    this._useRequestAnimationFrame = useRequestAnimationFrame === true && typeof window !== "undefined";
    this.cancelled = false;
    this.capability = (0, _util.createPromiseCapability)();
    this.task = new RenderTask(this);
    this._cancelBound = this.cancel.bind(this);
    this._continueBound = this._continue.bind(this);
    this._scheduleNextBound = this._scheduleNext.bind(this);
    this._nextBound = this._next.bind(this);
    this._canvas = params.canvasContext.canvas;
  }

  get completed() {
    return this.capability.promise.catch(function () {});
  }

  initializeGraphics(_ref15) {
    var _globalThis$StepperMa;

    let {
      transparency = false,
      optionalContentConfig
    } = _ref15;

    if (this.cancelled) {
      return;
    }

    if (this._canvas) {
      if (_classStaticPrivateFieldSpecGet(InternalRenderTask, InternalRenderTask, _canvasInUse).has(this._canvas)) {
        throw new Error("Cannot use the same canvas during multiple render() operations. " + "Use different canvas or ensure previous operations were " + "cancelled or completed.");
      }

      _classStaticPrivateFieldSpecGet(InternalRenderTask, InternalRenderTask, _canvasInUse).add(this._canvas);
    }

    if (this._pdfBug && (_globalThis$StepperMa = globalThis.StepperManager) !== null && _globalThis$StepperMa !== void 0 && _globalThis$StepperMa.enabled) {
      this.stepper = globalThis.StepperManager.create(this._pageIndex);
      this.stepper.init(this.operatorList);
      this.stepper.nextBreakPoint = this.stepper.getNextBreakPoint();
    }

    const {
      canvasContext,
      viewport,
      transform,
      imageLayer,
      background
    } = this.params;
    this.gfx = new _canvas.CanvasGraphics(canvasContext, this.commonObjs, this.objs, this.canvasFactory, imageLayer, optionalContentConfig, this.annotationCanvasMap, this.pageColors);
    this.gfx.beginDrawing({
      transform,
      viewport,
      transparency,
      background
    });
    this.operatorListIdx = 0;
    this.graphicsReady = true;

    if (this.graphicsReadyCallback) {
      this.graphicsReadyCallback();
    }
  }

  cancel() {
    let error = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
    this.running = false;
    this.cancelled = true;

    if (this.gfx) {
      this.gfx.endDrawing();
    }

    if (this._canvas) {
      _classStaticPrivateFieldSpecGet(InternalRenderTask, InternalRenderTask, _canvasInUse).delete(this._canvas);
    }

    this.callback(error || new _display_utils.RenderingCancelledException(`Rendering cancelled, page ${this._pageIndex + 1}`, "canvas"));
  }

  operatorListChanged() {
    if (!this.graphicsReady) {
      if (!this.graphicsReadyCallback) {
        this.graphicsReadyCallback = this._continueBound;
      }

      return;
    }

    if (this.stepper) {
      this.stepper.updateOperatorList(this.operatorList);
    }

    if (this.running) {
      return;
    }

    this._continue();
  }

  _continue() {
    this.running = true;

    if (this.cancelled) {
      return;
    }

    if (this.task.onContinue) {
      this.task.onContinue(this._scheduleNextBound);
    } else {
      this._scheduleNext();
    }
  }

  _scheduleNext() {
    if (this._useRequestAnimationFrame) {
      window.requestAnimationFrame(() => {
        this._nextBound().catch(this._cancelBound);
      });
    } else {
      Promise.resolve().then(this._nextBound).catch(this._cancelBound);
    }
  }

  async _next() {
    if (this.cancelled) {
      return;
    }

    this.operatorListIdx = this.gfx.executeOperatorList(this.operatorList, this.operatorListIdx, this._continueBound, this.stepper);

    if (this.operatorListIdx === this.operatorList.argsArray.length) {
      this.running = false;

      if (this.operatorList.lastChunk) {
        this.gfx.endDrawing();

        if (this._canvas) {
          _classStaticPrivateFieldSpecGet(InternalRenderTask, InternalRenderTask, _canvasInUse).delete(this._canvas);
        }

        this.callback();
      }
    }
  }

}

var _canvasInUse = {
  writable: true,
  value: new WeakSet()
};
const version = '2.16.105';
exports.version = version;
const build = '172ccdbe5';
exports.build = build;

/***/ }),
/* 130 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.PrintAnnotationStorage = exports.AnnotationStorage = void 0;

var _util = __w_pdfjs_require__(1);

var _editor = __w_pdfjs_require__(131);

var _murmurhash = __w_pdfjs_require__(135);

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

var _setModified = /*#__PURE__*/new WeakSet();

class AnnotationStorage {
  constructor() {
    _classPrivateMethodInitSpec(this, _setModified);

    this._storage = new Map();
    this._modified = false;
    this.onSetModified = null;
    this.onResetModified = null;
    this.onAnnotationEditor = null;
  }

  getValue(key, defaultValue) {
    const value = this._storage.get(key);

    if (value === undefined) {
      return defaultValue;
    }

    return Object.assign(defaultValue, value);
  }

  getRawValue(key) {
    return this._storage.get(key);
  }

  remove(key) {
    this._storage.delete(key);

    if (this._storage.size === 0) {
      this.resetModified();
    }

    if (typeof this.onAnnotationEditor === "function") {
      for (const value of this._storage.values()) {
        if (value instanceof _editor.AnnotationEditor) {
          return;
        }
      }

      this.onAnnotationEditor(null);
    }
  }

  setValue(key, value) {
    const obj = this._storage.get(key);

    let modified = false;

    if (obj !== undefined) {
      for (const [entry, val] of Object.entries(value)) {
        if (obj[entry] !== val) {
          modified = true;
          obj[entry] = val;
        }
      }
    } else {
      modified = true;

      this._storage.set(key, value);
    }

    if (modified) {
      _classPrivateMethodGet(this, _setModified, _setModified2).call(this);
    }

    if (value instanceof _editor.AnnotationEditor && typeof this.onAnnotationEditor === "function") {
      this.onAnnotationEditor(value.constructor._type);
    }
  }

  has(key) {
    return this._storage.has(key);
  }

  getAll() {
    return this._storage.size > 0 ? (0, _util.objectFromMap)(this._storage) : null;
  }

  get size() {
    return this._storage.size;
  }

  resetModified() {
    if (this._modified) {
      this._modified = false;

      if (typeof this.onResetModified === "function") {
        this.onResetModified();
      }
    }
  }

  get print() {
    return new PrintAnnotationStorage(this);
  }

  get serializable() {
    if (this._storage.size === 0) {
      return null;
    }

    const clone = new Map();

    for (const [key, val] of this._storage) {
      const serialized = val instanceof _editor.AnnotationEditor ? val.serialize() : val;

      if (serialized) {
        clone.set(key, serialized);
      }
    }

    return clone;
  }

  static getHash(map) {
    if (!map) {
      return "";
    }

    const hash = new _murmurhash.MurmurHash3_64();

    for (const [key, val] of map) {
      hash.update(`${key}:${JSON.stringify(val)}`);
    }

    return hash.hexdigest();
  }

}

exports.AnnotationStorage = AnnotationStorage;

function _setModified2() {
  if (!this._modified) {
    this._modified = true;

    if (typeof this.onSetModified === "function") {
      this.onSetModified();
    }
  }
}

var _serializable = /*#__PURE__*/new WeakMap();

class PrintAnnotationStorage extends AnnotationStorage {
  constructor(parent) {
    super();

    _classPrivateFieldInitSpec(this, _serializable, {
      writable: true,
      value: null
    });

    _classPrivateFieldSet(this, _serializable, structuredClone(parent.serializable));
  }

  get print() {
    (0, _util.unreachable)("Should not call PrintAnnotationStorage.print");
  }

  get serializable() {
    return _classPrivateFieldGet(this, _serializable);
  }

}

exports.PrintAnnotationStorage = PrintAnnotationStorage;

/***/ }),
/* 131 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.AnnotationEditor = void 0;

var _tools = __w_pdfjs_require__(132);

var _util = __w_pdfjs_require__(1);

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

var _boundFocusin = /*#__PURE__*/new WeakMap();

var _boundFocusout = /*#__PURE__*/new WeakMap();

var _hasBeenSelected = /*#__PURE__*/new WeakMap();

var _isEditing = /*#__PURE__*/new WeakMap();

var _isInEditMode = /*#__PURE__*/new WeakMap();

var _zIndex = /*#__PURE__*/new WeakMap();

class AnnotationEditor {
  constructor(parameters) {
    _classPrivateFieldInitSpec(this, _boundFocusin, {
      writable: true,
      value: this.focusin.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundFocusout, {
      writable: true,
      value: this.focusout.bind(this)
    });

    _classPrivateFieldInitSpec(this, _hasBeenSelected, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _isEditing, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _isInEditMode, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _zIndex, {
      writable: true,
      value: AnnotationEditor._zIndex++
    });

    if (this.constructor === AnnotationEditor) {
      (0, _util.unreachable)("Cannot initialize AnnotationEditor.");
    }

    this.parent = parameters.parent;
    this.id = parameters.id;
    this.width = this.height = null;
    this.pageIndex = parameters.parent.pageIndex;
    this.name = parameters.name;
    this.div = null;
    const [width, height] = this.parent.viewportBaseDimensions;
    this.x = parameters.x / width;
    this.y = parameters.y / height;
    this.rotation = this.parent.viewport.rotation;
    this.isAttachedToDOM = false;
  }

  static get _defaultLineColor() {
    return (0, _util.shadow)(this, "_defaultLineColor", this._colorManager.getHexCode("CanvasText"));
  }

  setInBackground() {
    this.div.style.zIndex = 0;
  }

  setInForeground() {
    this.div.style.zIndex = _classPrivateFieldGet(this, _zIndex);
  }

  focusin(event) {
    if (!_classPrivateFieldGet(this, _hasBeenSelected)) {
      this.parent.setSelected(this);
    } else {
      _classPrivateFieldSet(this, _hasBeenSelected, false);
    }
  }

  focusout(event) {
    if (!this.isAttachedToDOM) {
      return;
    }

    const target = event.relatedTarget;

    if (target !== null && target !== void 0 && target.closest(`#${this.id}`)) {
      return;
    }

    event.preventDefault();

    if (!this.parent.isMultipleSelection) {
      this.commitOrRemove();
    }
  }

  commitOrRemove() {
    if (this.isEmpty()) {
      this.remove();
    } else {
      this.commit();
    }
  }

  commit() {
    this.parent.addToAnnotationStorage(this);
  }

  dragstart(event) {
    const rect = this.parent.div.getBoundingClientRect();
    this.startX = event.clientX - rect.x;
    this.startY = event.clientY - rect.y;
    event.dataTransfer.setData("text/plain", this.id);
    event.dataTransfer.effectAllowed = "move";
  }

  setAt(x, y, tx, ty) {
    const [width, height] = this.parent.viewportBaseDimensions;
    [tx, ty] = this.screenToPageTranslation(tx, ty);
    this.x = (x + tx) / width;
    this.y = (y + ty) / height;
    this.div.style.left = `${100 * this.x}%`;
    this.div.style.top = `${100 * this.y}%`;
  }

  translate(x, y) {
    const [width, height] = this.parent.viewportBaseDimensions;
    [x, y] = this.screenToPageTranslation(x, y);
    this.x += x / width;
    this.y += y / height;
    this.div.style.left = `${100 * this.x}%`;
    this.div.style.top = `${100 * this.y}%`;
  }

  screenToPageTranslation(x, y) {
    const {
      rotation
    } = this.parent.viewport;

    switch (rotation) {
      case 90:
        return [y, -x];

      case 180:
        return [-x, -y];

      case 270:
        return [-y, x];

      default:
        return [x, y];
    }
  }

  setDims(width, height) {
    const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
    this.div.style.width = `${100 * width / parentWidth}%`;
    this.div.style.height = `${100 * height / parentHeight}%`;
  }

  getInitialTranslation() {
    return [0, 0];
  }

  render() {
    this.div = document.createElement("div");
    this.div.setAttribute("data-editor-rotation", (360 - this.rotation) % 360);
    this.div.className = this.name;
    this.div.setAttribute("id", this.id);
    this.div.setAttribute("tabIndex", 0);
    this.setInForeground();
    this.div.addEventListener("focusin", _classPrivateFieldGet(this, _boundFocusin));
    this.div.addEventListener("focusout", _classPrivateFieldGet(this, _boundFocusout));
    const [tx, ty] = this.getInitialTranslation();
    this.translate(tx, ty);
    (0, _tools.bindEvents)(this, this.div, ["dragstart", "pointerdown"]);
    return this.div;
  }

  pointerdown(event) {
    const isMac = _tools.KeyboardManager.platform.isMac;

    if (event.button !== 0 || event.ctrlKey && isMac) {
      event.preventDefault();
      return;
    }

    if (event.ctrlKey && !isMac || event.shiftKey || event.metaKey && isMac) {
      this.parent.toggleSelected(this);
    } else {
      this.parent.setSelected(this);
    }

    _classPrivateFieldSet(this, _hasBeenSelected, true);
  }

  getRect(tx, ty) {
    const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
    const [pageWidth, pageHeight] = this.parent.pageDimensions;
    const shiftX = pageWidth * tx / parentWidth;
    const shiftY = pageHeight * ty / parentHeight;
    const x = this.x * pageWidth;
    const y = this.y * pageHeight;
    const width = this.width * pageWidth;
    const height = this.height * pageHeight;

    switch (this.rotation) {
      case 0:
        return [x + shiftX, pageHeight - y - shiftY - height, x + shiftX + width, pageHeight - y - shiftY];

      case 90:
        return [x + shiftY, pageHeight - y + shiftX, x + shiftY + height, pageHeight - y + shiftX + width];

      case 180:
        return [x - shiftX - width, pageHeight - y + shiftY, x - shiftX, pageHeight - y + shiftY + height];

      case 270:
        return [x - shiftY - height, pageHeight - y - shiftX - width, x - shiftY, pageHeight - y - shiftX];

      default:
        throw new Error("Invalid rotation");
    }
  }

  getRectInCurrentCoords(rect, pageHeight) {
    const [x1, y1, x2, y2] = rect;
    const width = x2 - x1;
    const height = y2 - y1;

    switch (this.rotation) {
      case 0:
        return [x1, pageHeight - y2, width, height];

      case 90:
        return [x1, pageHeight - y1, height, width];

      case 180:
        return [x2, pageHeight - y1, width, height];

      case 270:
        return [x2, pageHeight - y2, height, width];

      default:
        throw new Error("Invalid rotation");
    }
  }

  onceAdded() {}

  isEmpty() {
    return false;
  }

  enableEditMode() {
    _classPrivateFieldSet(this, _isInEditMode, true);
  }

  disableEditMode() {
    _classPrivateFieldSet(this, _isInEditMode, false);
  }

  isInEditMode() {
    return _classPrivateFieldGet(this, _isInEditMode);
  }

  shouldGetKeyboardEvents() {
    return false;
  }

  needsToBeRebuilt() {
    return this.div && !this.isAttachedToDOM;
  }

  rebuild() {
    var _this$div;

    (_this$div = this.div) === null || _this$div === void 0 ? void 0 : _this$div.addEventListener("focusin", _classPrivateFieldGet(this, _boundFocusin));
  }

  serialize() {
    (0, _util.unreachable)("An editor must be serializable");
  }

  static deserialize(data, parent) {
    const editor = new this.prototype.constructor({
      parent,
      id: parent.getNextId()
    });
    editor.rotation = data.rotation;
    const [pageWidth, pageHeight] = parent.pageDimensions;
    const [x, y, width, height] = editor.getRectInCurrentCoords(data.rect, pageHeight);
    editor.x = x / pageWidth;
    editor.y = y / pageHeight;
    editor.width = width / pageWidth;
    editor.height = height / pageHeight;
    return editor;
  }

  remove() {
    this.div.removeEventListener("focusin", _classPrivateFieldGet(this, _boundFocusin));
    this.div.removeEventListener("focusout", _classPrivateFieldGet(this, _boundFocusout));

    if (!this.isEmpty()) {
      this.commit();
    }

    this.parent.remove(this);
  }

  select() {
    var _this$div2;

    (_this$div2 = this.div) === null || _this$div2 === void 0 ? void 0 : _this$div2.classList.add("selectedEditor");
  }

  unselect() {
    var _this$div3;

    (_this$div3 = this.div) === null || _this$div3 === void 0 ? void 0 : _this$div3.classList.remove("selectedEditor");
  }

  updateParams(type, value) {}

  disableEditing() {}

  enableEditing() {}

  get propertiesToUpdate() {
    return {};
  }

  get contentDiv() {
    return this.div;
  }

  get isEditing() {
    return _classPrivateFieldGet(this, _isEditing);
  }

  set isEditing(value) {
    _classPrivateFieldSet(this, _isEditing, value);

    if (value) {
      this.parent.setSelected(this);
      this.parent.setActiveEditor(this);
    } else {
      this.parent.setActiveEditor(null);
    }
  }

}

exports.AnnotationEditor = AnnotationEditor;

_defineProperty(AnnotationEditor, "_colorManager", new _tools.ColorManager());

_defineProperty(AnnotationEditor, "_zIndex", 1);

/***/ }),
/* 132 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.KeyboardManager = exports.CommandManager = exports.ColorManager = exports.AnnotationEditorUIManager = void 0;
exports.bindEvents = bindEvents;
exports.opacityToHex = opacityToHex;

var _util = __w_pdfjs_require__(1);

var _display_utils = __w_pdfjs_require__(133);

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function bindEvents(obj, element, names) {
  for (const name of names) {
    element.addEventListener(name, obj[name].bind(obj));
  }
}

function opacityToHex(opacity) {
  return Math.round(Math.min(255, Math.max(1, 255 * opacity))).toString(16).padStart(2, "0");
}

var _id = /*#__PURE__*/new WeakMap();

class IdManager {
  constructor() {
    _classPrivateFieldInitSpec(this, _id, {
      writable: true,
      value: 0
    });
  }

  getId() {
    var _this$id, _this$id2;

    return `${_util.AnnotationEditorPrefix}${(_classPrivateFieldSet(this, _id, (_this$id = _classPrivateFieldGet(this, _id), _this$id2 = _this$id++, _this$id)), _this$id2)}`;
  }

}

var _commands = /*#__PURE__*/new WeakMap();

var _locked = /*#__PURE__*/new WeakMap();

var _maxSize = /*#__PURE__*/new WeakMap();

var _position = /*#__PURE__*/new WeakMap();

class CommandManager {
  constructor() {
    let maxSize = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 128;

    _classPrivateFieldInitSpec(this, _commands, {
      writable: true,
      value: []
    });

    _classPrivateFieldInitSpec(this, _locked, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _maxSize, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldInitSpec(this, _position, {
      writable: true,
      value: -1
    });

    _classPrivateFieldSet(this, _maxSize, maxSize);
  }

  add(_ref) {
    let {
      cmd,
      undo,
      mustExec,
      type = NaN,
      overwriteIfSameType = false,
      keepUndo = false
    } = _ref;

    if (mustExec) {
      cmd();
    }

    if (_classPrivateFieldGet(this, _locked)) {
      return;
    }

    const save = {
      cmd,
      undo,
      type
    };

    if (_classPrivateFieldGet(this, _position) === -1) {
      if (_classPrivateFieldGet(this, _commands).length > 0) {
        _classPrivateFieldGet(this, _commands).length = 0;
      }

      _classPrivateFieldSet(this, _position, 0);

      _classPrivateFieldGet(this, _commands).push(save);

      return;
    }

    if (overwriteIfSameType && _classPrivateFieldGet(this, _commands)[_classPrivateFieldGet(this, _position)].type === type) {
      if (keepUndo) {
        save.undo = _classPrivateFieldGet(this, _commands)[_classPrivateFieldGet(this, _position)].undo;
      }

      _classPrivateFieldGet(this, _commands)[_classPrivateFieldGet(this, _position)] = save;
      return;
    }

    const next = _classPrivateFieldGet(this, _position) + 1;

    if (next === _classPrivateFieldGet(this, _maxSize)) {
      _classPrivateFieldGet(this, _commands).splice(0, 1);
    } else {
      _classPrivateFieldSet(this, _position, next);

      if (next < _classPrivateFieldGet(this, _commands).length) {
        _classPrivateFieldGet(this, _commands).splice(next);
      }
    }

    _classPrivateFieldGet(this, _commands).push(save);
  }

  undo() {
    if (_classPrivateFieldGet(this, _position) === -1) {
      return;
    }

    _classPrivateFieldSet(this, _locked, true);

    _classPrivateFieldGet(this, _commands)[_classPrivateFieldGet(this, _position)].undo();

    _classPrivateFieldSet(this, _locked, false);

    _classPrivateFieldSet(this, _position, _classPrivateFieldGet(this, _position) - 1);
  }

  redo() {
    if (_classPrivateFieldGet(this, _position) < _classPrivateFieldGet(this, _commands).length - 1) {
      _classPrivateFieldSet(this, _position, _classPrivateFieldGet(this, _position) + 1);

      _classPrivateFieldSet(this, _locked, true);

      _classPrivateFieldGet(this, _commands)[_classPrivateFieldGet(this, _position)].cmd();

      _classPrivateFieldSet(this, _locked, false);
    }
  }

  hasSomethingToUndo() {
    return _classPrivateFieldGet(this, _position) !== -1;
  }

  hasSomethingToRedo() {
    return _classPrivateFieldGet(this, _position) < _classPrivateFieldGet(this, _commands).length - 1;
  }

  destroy() {
    _classPrivateFieldSet(this, _commands, null);
  }

}

exports.CommandManager = CommandManager;

var _serialize = /*#__PURE__*/new WeakSet();

class KeyboardManager {
  constructor(callbacks) {
    _classPrivateMethodInitSpec(this, _serialize);

    this.buffer = [];
    this.callbacks = new Map();
    this.allKeys = new Set();
    const isMac = KeyboardManager.platform.isMac;

    for (const [keys, callback] of callbacks) {
      for (const key of keys) {
        const isMacKey = key.startsWith("mac+");

        if (isMac && isMacKey) {
          this.callbacks.set(key.slice(4), callback);
          this.allKeys.add(key.split("+").at(-1));
        } else if (!isMac && !isMacKey) {
          this.callbacks.set(key, callback);
          this.allKeys.add(key.split("+").at(-1));
        }
      }
    }
  }

  static get platform() {
    const platform = typeof navigator !== "undefined" ? navigator.platform : "";
    return (0, _util.shadow)(this, "platform", {
      isWin: platform.includes("Win"),
      isMac: platform.includes("Mac")
    });
  }

  exec(self, event) {
    if (!this.allKeys.has(event.key)) {
      return;
    }

    const callback = this.callbacks.get(_classPrivateMethodGet(this, _serialize, _serialize2).call(this, event));

    if (!callback) {
      return;
    }

    callback.bind(self)();
    event.stopPropagation();
    event.preventDefault();
  }

}

exports.KeyboardManager = KeyboardManager;

function _serialize2(event) {
  if (event.altKey) {
    this.buffer.push("alt");
  }

  if (event.ctrlKey) {
    this.buffer.push("ctrl");
  }

  if (event.metaKey) {
    this.buffer.push("meta");
  }

  if (event.shiftKey) {
    this.buffer.push("shift");
  }

  this.buffer.push(event.key);
  const str = this.buffer.join("+");
  this.buffer.length = 0;
  return str;
}

var _elements = /*#__PURE__*/new WeakMap();

class ClipboardManager {
  constructor() {
    _classPrivateFieldInitSpec(this, _elements, {
      writable: true,
      value: null
    });
  }

  copy(element) {
    if (!element) {
      return;
    }

    if (Array.isArray(element)) {
      _classPrivateFieldSet(this, _elements, element.map(el => el.serialize()));
    } else {
      _classPrivateFieldSet(this, _elements, [element.serialize()]);
    }

    _classPrivateFieldSet(this, _elements, _classPrivateFieldGet(this, _elements).filter(el => !!el));

    if (_classPrivateFieldGet(this, _elements).length === 0) {
      _classPrivateFieldSet(this, _elements, null);
    }
  }

  paste() {
    return _classPrivateFieldGet(this, _elements);
  }

  isEmpty() {
    return _classPrivateFieldGet(this, _elements) === null;
  }

  destroy() {
    _classPrivateFieldSet(this, _elements, null);
  }

}

class ColorManager {
  get _colors() {
    const colors = new Map([["CanvasText", null], ["Canvas", null]]);
    (0, _display_utils.getColorValues)(colors);
    return (0, _util.shadow)(this, "_colors", colors);
  }

  convert(color) {
    const rgb = (0, _display_utils.getRGB)(color);

    if (!window.matchMedia("(forced-colors: active)").matches) {
      return rgb;
    }

    for (const [name, RGB] of this._colors) {
      if (RGB.every((x, i) => x === rgb[i])) {
        return ColorManager._colorsMapping.get(name);
      }
    }

    return rgb;
  }

  getHexCode(name) {
    const rgb = this._colors.get(name);

    if (!rgb) {
      return name;
    }

    return _util.Util.makeHexColor(...rgb);
  }

}

exports.ColorManager = ColorManager;

_defineProperty(ColorManager, "_colorsMapping", new Map([["CanvasText", [0, 0, 0]], ["Canvas", [255, 255, 255]]]));

var _activeEditor = /*#__PURE__*/new WeakMap();

var _allEditors = /*#__PURE__*/new WeakMap();

var _allLayers = /*#__PURE__*/new WeakMap();

var _clipboardManager = /*#__PURE__*/new WeakMap();

var _commandManager = /*#__PURE__*/new WeakMap();

var _currentPageIndex = /*#__PURE__*/new WeakMap();

var _editorTypes = /*#__PURE__*/new WeakMap();

var _eventBus = /*#__PURE__*/new WeakMap();

var _idManager = /*#__PURE__*/new WeakMap();

var _isEnabled = /*#__PURE__*/new WeakMap();

var _mode = /*#__PURE__*/new WeakMap();

var _selectedEditors = /*#__PURE__*/new WeakMap();

var _boundKeydown = /*#__PURE__*/new WeakMap();

var _boundOnEditingAction = /*#__PURE__*/new WeakMap();

var _boundOnPageChanging = /*#__PURE__*/new WeakMap();

var _previousStates = /*#__PURE__*/new WeakMap();

var _container = /*#__PURE__*/new WeakMap();

var _addKeyboardManager = /*#__PURE__*/new WeakSet();

var _removeKeyboardManager = /*#__PURE__*/new WeakSet();

var _dispatchUpdateStates = /*#__PURE__*/new WeakSet();

var _dispatchUpdateUI = /*#__PURE__*/new WeakSet();

var _enableAll = /*#__PURE__*/new WeakSet();

var _disableAll = /*#__PURE__*/new WeakSet();

var _addEditorToLayer = /*#__PURE__*/new WeakSet();

var _isEmpty = /*#__PURE__*/new WeakSet();

var _selectEditors = /*#__PURE__*/new WeakSet();

class AnnotationEditorUIManager {
  constructor(container, eventBus) {
    _classPrivateMethodInitSpec(this, _selectEditors);

    _classPrivateMethodInitSpec(this, _isEmpty);

    _classPrivateMethodInitSpec(this, _addEditorToLayer);

    _classPrivateMethodInitSpec(this, _disableAll);

    _classPrivateMethodInitSpec(this, _enableAll);

    _classPrivateMethodInitSpec(this, _dispatchUpdateUI);

    _classPrivateMethodInitSpec(this, _dispatchUpdateStates);

    _classPrivateMethodInitSpec(this, _removeKeyboardManager);

    _classPrivateMethodInitSpec(this, _addKeyboardManager);

    _classPrivateFieldInitSpec(this, _activeEditor, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _allEditors, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _allLayers, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _clipboardManager, {
      writable: true,
      value: new ClipboardManager()
    });

    _classPrivateFieldInitSpec(this, _commandManager, {
      writable: true,
      value: new CommandManager()
    });

    _classPrivateFieldInitSpec(this, _currentPageIndex, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _editorTypes, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _eventBus, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _idManager, {
      writable: true,
      value: new IdManager()
    });

    _classPrivateFieldInitSpec(this, _isEnabled, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _mode, {
      writable: true,
      value: _util.AnnotationEditorType.NONE
    });

    _classPrivateFieldInitSpec(this, _selectedEditors, {
      writable: true,
      value: new Set()
    });

    _classPrivateFieldInitSpec(this, _boundKeydown, {
      writable: true,
      value: this.keydown.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundOnEditingAction, {
      writable: true,
      value: this.onEditingAction.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundOnPageChanging, {
      writable: true,
      value: this.onPageChanging.bind(this)
    });

    _classPrivateFieldInitSpec(this, _previousStates, {
      writable: true,
      value: {
        isEditing: false,
        isEmpty: true,
        hasEmptyClipboard: true,
        hasSomethingToUndo: false,
        hasSomethingToRedo: false,
        hasSelectedEditor: false
      }
    });

    _classPrivateFieldInitSpec(this, _container, {
      writable: true,
      value: null
    });

    _classPrivateFieldSet(this, _container, container);

    _classPrivateFieldSet(this, _eventBus, eventBus);

    _classPrivateFieldGet(this, _eventBus)._on("editingaction", _classPrivateFieldGet(this, _boundOnEditingAction));

    _classPrivateFieldGet(this, _eventBus)._on("pagechanging", _classPrivateFieldGet(this, _boundOnPageChanging));
  }

  destroy() {
    _classPrivateMethodGet(this, _removeKeyboardManager, _removeKeyboardManager2).call(this);

    _classPrivateFieldGet(this, _eventBus)._off("editingaction", _classPrivateFieldGet(this, _boundOnEditingAction));

    _classPrivateFieldGet(this, _eventBus)._off("pagechanging", _classPrivateFieldGet(this, _boundOnPageChanging));

    for (const layer of _classPrivateFieldGet(this, _allLayers).values()) {
      layer.destroy();
    }

    _classPrivateFieldGet(this, _allLayers).clear();

    _classPrivateFieldGet(this, _allEditors).clear();

    _classPrivateFieldSet(this, _activeEditor, null);

    _classPrivateFieldGet(this, _selectedEditors).clear();

    _classPrivateFieldGet(this, _clipboardManager).destroy();

    _classPrivateFieldGet(this, _commandManager).destroy();
  }

  onPageChanging(_ref2) {
    let {
      pageNumber
    } = _ref2;

    _classPrivateFieldSet(this, _currentPageIndex, pageNumber - 1);
  }

  focusMainContainer() {
    _classPrivateFieldGet(this, _container).focus();
  }

  keydown(event) {
    var _this$getActive;

    if (!((_this$getActive = this.getActive()) !== null && _this$getActive !== void 0 && _this$getActive.shouldGetKeyboardEvents())) {
      AnnotationEditorUIManager._keyboardManager.exec(this, event);
    }
  }

  onEditingAction(details) {
    if (["undo", "redo", "cut", "copy", "paste", "delete", "selectAll"].includes(details.name)) {
      this[details.name]();
    }
  }

  setEditingState(isEditing) {
    if (isEditing) {
      _classPrivateMethodGet(this, _addKeyboardManager, _addKeyboardManager2).call(this);

      _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
        isEditing: _classPrivateFieldGet(this, _mode) !== _util.AnnotationEditorType.NONE,
        isEmpty: _classPrivateMethodGet(this, _isEmpty, _isEmpty2).call(this),
        hasSomethingToUndo: _classPrivateFieldGet(this, _commandManager).hasSomethingToUndo(),
        hasSomethingToRedo: _classPrivateFieldGet(this, _commandManager).hasSomethingToRedo(),
        hasSelectedEditor: false,
        hasEmptyClipboard: _classPrivateFieldGet(this, _clipboardManager).isEmpty()
      });
    } else {
      _classPrivateMethodGet(this, _removeKeyboardManager, _removeKeyboardManager2).call(this);

      _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
        isEditing: false
      });
    }
  }

  registerEditorTypes(types) {
    _classPrivateFieldSet(this, _editorTypes, types);

    for (const editorType of _classPrivateFieldGet(this, _editorTypes)) {
      _classPrivateMethodGet(this, _dispatchUpdateUI, _dispatchUpdateUI2).call(this, editorType.defaultPropertiesToUpdate);
    }
  }

  getId() {
    return _classPrivateFieldGet(this, _idManager).getId();
  }

  addLayer(layer) {
    _classPrivateFieldGet(this, _allLayers).set(layer.pageIndex, layer);

    if (_classPrivateFieldGet(this, _isEnabled)) {
      layer.enable();
    } else {
      layer.disable();
    }
  }

  removeLayer(layer) {
    _classPrivateFieldGet(this, _allLayers).delete(layer.pageIndex);
  }

  updateMode(mode) {
    _classPrivateFieldSet(this, _mode, mode);

    if (mode === _util.AnnotationEditorType.NONE) {
      this.setEditingState(false);

      _classPrivateMethodGet(this, _disableAll, _disableAll2).call(this);
    } else {
      this.setEditingState(true);

      _classPrivateMethodGet(this, _enableAll, _enableAll2).call(this);

      for (const layer of _classPrivateFieldGet(this, _allLayers).values()) {
        layer.updateMode(mode);
      }
    }
  }

  updateToolbar(mode) {
    if (mode === _classPrivateFieldGet(this, _mode)) {
      return;
    }

    _classPrivateFieldGet(this, _eventBus).dispatch("switchannotationeditormode", {
      source: this,
      mode
    });
  }

  updateParams(type, value) {
    for (const editor of _classPrivateFieldGet(this, _selectedEditors)) {
      editor.updateParams(type, value);
    }

    for (const editorType of _classPrivateFieldGet(this, _editorTypes)) {
      editorType.updateDefaultParams(type, value);
    }
  }

  getEditors(pageIndex) {
    const editors = [];

    for (const editor of _classPrivateFieldGet(this, _allEditors).values()) {
      if (editor.pageIndex === pageIndex) {
        editors.push(editor);
      }
    }

    return editors;
  }

  getEditor(id) {
    return _classPrivateFieldGet(this, _allEditors).get(id);
  }

  addEditor(editor) {
    _classPrivateFieldGet(this, _allEditors).set(editor.id, editor);
  }

  removeEditor(editor) {
    _classPrivateFieldGet(this, _allEditors).delete(editor.id);

    this.unselect(editor);
  }

  setActiveEditor(editor) {
    if (_classPrivateFieldGet(this, _activeEditor) === editor) {
      return;
    }

    _classPrivateFieldSet(this, _activeEditor, editor);

    if (editor) {
      _classPrivateMethodGet(this, _dispatchUpdateUI, _dispatchUpdateUI2).call(this, editor.propertiesToUpdate);
    }
  }

  toggleSelected(editor) {
    if (_classPrivateFieldGet(this, _selectedEditors).has(editor)) {
      _classPrivateFieldGet(this, _selectedEditors).delete(editor);

      editor.unselect();

      _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
        hasSelectedEditor: this.hasSelection
      });

      return;
    }

    _classPrivateFieldGet(this, _selectedEditors).add(editor);

    editor.select();

    _classPrivateMethodGet(this, _dispatchUpdateUI, _dispatchUpdateUI2).call(this, editor.propertiesToUpdate);

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSelectedEditor: true
    });
  }

  setSelected(editor) {
    for (const ed of _classPrivateFieldGet(this, _selectedEditors)) {
      if (ed !== editor) {
        ed.unselect();
      }
    }

    _classPrivateFieldGet(this, _selectedEditors).clear();

    _classPrivateFieldGet(this, _selectedEditors).add(editor);

    editor.select();

    _classPrivateMethodGet(this, _dispatchUpdateUI, _dispatchUpdateUI2).call(this, editor.propertiesToUpdate);

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSelectedEditor: true
    });
  }

  isSelected(editor) {
    return _classPrivateFieldGet(this, _selectedEditors).has(editor);
  }

  unselect(editor) {
    editor.unselect();

    _classPrivateFieldGet(this, _selectedEditors).delete(editor);

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSelectedEditor: this.hasSelection
    });
  }

  get hasSelection() {
    return _classPrivateFieldGet(this, _selectedEditors).size !== 0;
  }

  undo() {
    _classPrivateFieldGet(this, _commandManager).undo();

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSomethingToUndo: _classPrivateFieldGet(this, _commandManager).hasSomethingToUndo(),
      hasSomethingToRedo: true,
      isEmpty: _classPrivateMethodGet(this, _isEmpty, _isEmpty2).call(this)
    });
  }

  redo() {
    _classPrivateFieldGet(this, _commandManager).redo();

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSomethingToUndo: true,
      hasSomethingToRedo: _classPrivateFieldGet(this, _commandManager).hasSomethingToRedo(),
      isEmpty: _classPrivateMethodGet(this, _isEmpty, _isEmpty2).call(this)
    });
  }

  addCommands(params) {
    _classPrivateFieldGet(this, _commandManager).add(params);

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSomethingToUndo: true,
      hasSomethingToRedo: false,
      isEmpty: _classPrivateMethodGet(this, _isEmpty, _isEmpty2).call(this)
    });
  }

  delete() {
    if (_classPrivateFieldGet(this, _activeEditor)) {
      _classPrivateFieldGet(this, _activeEditor).commitOrRemove();
    }

    if (!this.hasSelection) {
      return;
    }

    const editors = [..._classPrivateFieldGet(this, _selectedEditors)];

    const cmd = () => {
      for (const editor of editors) {
        editor.remove();
      }
    };

    const undo = () => {
      for (const editor of editors) {
        _classPrivateMethodGet(this, _addEditorToLayer, _addEditorToLayer2).call(this, editor);
      }
    };

    this.addCommands({
      cmd,
      undo,
      mustExec: true
    });
  }

  copy() {
    if (_classPrivateFieldGet(this, _activeEditor)) {
      _classPrivateFieldGet(this, _activeEditor).commitOrRemove();
    }

    if (this.hasSelection) {
      const editors = [];

      for (const editor of _classPrivateFieldGet(this, _selectedEditors)) {
        if (!editor.isEmpty()) {
          editors.push(editor);
        }
      }

      if (editors.length === 0) {
        return;
      }

      _classPrivateFieldGet(this, _clipboardManager).copy(editors);

      _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
        hasEmptyClipboard: false
      });
    }
  }

  cut() {
    this.copy();
    this.delete();
  }

  paste() {
    if (_classPrivateFieldGet(this, _clipboardManager).isEmpty()) {
      return;
    }

    this.unselectAll();

    const layer = _classPrivateFieldGet(this, _allLayers).get(_classPrivateFieldGet(this, _currentPageIndex));

    const newEditors = _classPrivateFieldGet(this, _clipboardManager).paste().map(data => layer.deserialize(data));

    const cmd = () => {
      for (const editor of newEditors) {
        _classPrivateMethodGet(this, _addEditorToLayer, _addEditorToLayer2).call(this, editor);
      }

      _classPrivateMethodGet(this, _selectEditors, _selectEditors2).call(this, newEditors);
    };

    const undo = () => {
      for (const editor of newEditors) {
        editor.remove();
      }
    };

    this.addCommands({
      cmd,
      undo,
      mustExec: true
    });
  }

  selectAll() {
    for (const editor of _classPrivateFieldGet(this, _selectedEditors)) {
      editor.commit();
    }

    _classPrivateMethodGet(this, _selectEditors, _selectEditors2).call(this, _classPrivateFieldGet(this, _allEditors).values());
  }

  unselectAll() {
    if (_classPrivateFieldGet(this, _activeEditor)) {
      _classPrivateFieldGet(this, _activeEditor).commitOrRemove();

      return;
    }

    if (_classPrivateMethodGet(this, _selectEditors, _selectEditors2).size === 0) {
      return;
    }

    for (const editor of _classPrivateFieldGet(this, _selectedEditors)) {
      editor.unselect();
    }

    _classPrivateFieldGet(this, _selectedEditors).clear();

    _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
      hasSelectedEditor: false
    });
  }

  isActive(editor) {
    return _classPrivateFieldGet(this, _activeEditor) === editor;
  }

  getActive() {
    return _classPrivateFieldGet(this, _activeEditor);
  }

  getMode() {
    return _classPrivateFieldGet(this, _mode);
  }

}

exports.AnnotationEditorUIManager = AnnotationEditorUIManager;

function _addKeyboardManager2() {
  _classPrivateFieldGet(this, _container).addEventListener("keydown", _classPrivateFieldGet(this, _boundKeydown));
}

function _removeKeyboardManager2() {
  _classPrivateFieldGet(this, _container).removeEventListener("keydown", _classPrivateFieldGet(this, _boundKeydown));
}

function _dispatchUpdateStates2(details) {
  const hasChanged = Object.entries(details).some(_ref3 => {
    let [key, value] = _ref3;
    return _classPrivateFieldGet(this, _previousStates)[key] !== value;
  });

  if (hasChanged) {
    _classPrivateFieldGet(this, _eventBus).dispatch("annotationeditorstateschanged", {
      source: this,
      details: Object.assign(_classPrivateFieldGet(this, _previousStates), details)
    });
  }
}

function _dispatchUpdateUI2(details) {
  _classPrivateFieldGet(this, _eventBus).dispatch("annotationeditorparamschanged", {
    source: this,
    details
  });
}

function _enableAll2() {
  if (!_classPrivateFieldGet(this, _isEnabled)) {
    _classPrivateFieldSet(this, _isEnabled, true);

    for (const layer of _classPrivateFieldGet(this, _allLayers).values()) {
      layer.enable();
    }
  }
}

function _disableAll2() {
  this.unselectAll();

  if (_classPrivateFieldGet(this, _isEnabled)) {
    _classPrivateFieldSet(this, _isEnabled, false);

    for (const layer of _classPrivateFieldGet(this, _allLayers).values()) {
      layer.disable();
    }
  }
}

function _addEditorToLayer2(editor) {
  const layer = _classPrivateFieldGet(this, _allLayers).get(editor.pageIndex);

  if (layer) {
    layer.addOrRebuild(editor);
  } else {
    this.addEditor(editor);
  }
}

function _isEmpty2() {
  if (_classPrivateFieldGet(this, _allEditors).size === 0) {
    return true;
  }

  if (_classPrivateFieldGet(this, _allEditors).size === 1) {
    for (const editor of _classPrivateFieldGet(this, _allEditors).values()) {
      return editor.isEmpty();
    }
  }

  return false;
}

function _selectEditors2(editors) {
  _classPrivateFieldGet(this, _selectedEditors).clear();

  for (const editor of editors) {
    if (editor.isEmpty()) {
      continue;
    }

    _classPrivateFieldGet(this, _selectedEditors).add(editor);

    editor.select();
  }

  _classPrivateMethodGet(this, _dispatchUpdateStates, _dispatchUpdateStates2).call(this, {
    hasSelectedEditor: true
  });
}

_defineProperty(AnnotationEditorUIManager, "_keyboardManager", new KeyboardManager([[["ctrl+a", "mac+meta+a"], AnnotationEditorUIManager.prototype.selectAll], [["ctrl+c", "mac+meta+c"], AnnotationEditorUIManager.prototype.copy], [["ctrl+v", "mac+meta+v"], AnnotationEditorUIManager.prototype.paste], [["ctrl+x", "mac+meta+x"], AnnotationEditorUIManager.prototype.cut], [["ctrl+z", "mac+meta+z"], AnnotationEditorUIManager.prototype.undo], [["ctrl+y", "ctrl+shift+Z", "mac+meta+shift+Z"], AnnotationEditorUIManager.prototype.redo], [["Backspace", "alt+Backspace", "ctrl+Backspace", "shift+Backspace", "mac+Backspace", "mac+alt+Backspace", "mac+ctrl+Backspace", "Delete", "ctrl+Delete", "shift+Delete"], AnnotationEditorUIManager.prototype.delete], [["Escape", "mac+Escape"], AnnotationEditorUIManager.prototype.unselectAll]]));

/***/ }),
/* 133 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.StatTimer = exports.RenderingCancelledException = exports.PixelsPerInch = exports.PageViewport = exports.PDFDateString = exports.DOMStandardFontDataFactory = exports.DOMSVGFactory = exports.DOMCanvasFactory = exports.DOMCMapReaderFactory = exports.AnnotationPrefix = void 0;
exports.deprecated = deprecated;
exports.getColorValues = getColorValues;
exports.getCurrentTransform = getCurrentTransform;
exports.getCurrentTransformInverse = getCurrentTransformInverse;
exports.getFilenameFromUrl = getFilenameFromUrl;
exports.getPdfFilenameFromUrl = getPdfFilenameFromUrl;
exports.getRGB = getRGB;
exports.getXfaPageViewport = getXfaPageViewport;
exports.isDataScheme = isDataScheme;
exports.isPdfFile = isPdfFile;
exports.isValidFetchUrl = isValidFetchUrl;
exports.loadScript = loadScript;

var _base_factory = __w_pdfjs_require__(134);

var _util = __w_pdfjs_require__(1);

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

const SVG_NS = "http://www.w3.org/2000/svg";
const AnnotationPrefix = "pdfjs_internal_id_";
exports.AnnotationPrefix = AnnotationPrefix;

class PixelsPerInch {}

exports.PixelsPerInch = PixelsPerInch;

_defineProperty(PixelsPerInch, "CSS", 96.0);

_defineProperty(PixelsPerInch, "PDF", 72.0);

_defineProperty(PixelsPerInch, "PDF_TO_CSS_UNITS", PixelsPerInch.CSS / PixelsPerInch.PDF);

class DOMCanvasFactory extends _base_factory.BaseCanvasFactory {
  constructor() {
    let {
      ownerDocument = globalThis.document
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    super();
    this._document = ownerDocument;
  }

  _createCanvas(width, height) {
    const canvas = this._document.createElement("canvas");

    canvas.width = width;
    canvas.height = height;
    return canvas;
  }

}

exports.DOMCanvasFactory = DOMCanvasFactory;

async function fetchData(url) {
  let asTypedArray = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

  if (isValidFetchUrl(url, document.baseURI)) {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(response.statusText);
    }

    return asTypedArray ? new Uint8Array(await response.arrayBuffer()) : (0, _util.stringToBytes)(await response.text());
  }

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("GET", url, true);

    if (asTypedArray) {
      request.responseType = "arraybuffer";
    }

    request.onreadystatechange = () => {
      if (request.readyState !== XMLHttpRequest.DONE) {
        return;
      }

      if (request.status === 200 || request.status === 0) {
        let data;

        if (asTypedArray && request.response) {
          data = new Uint8Array(request.response);
        } else if (!asTypedArray && request.responseText) {
          data = (0, _util.stringToBytes)(request.responseText);
        }

        if (data) {
          resolve(data);
          return;
        }
      }

      reject(new Error(request.statusText));
    };

    request.send(null);
  });
}

class DOMCMapReaderFactory extends _base_factory.BaseCMapReaderFactory {
  _fetchData(url, compressionType) {
    return fetchData(url, this.isCompressed).then(data => {
      return {
        cMapData: data,
        compressionType
      };
    });
  }

}

exports.DOMCMapReaderFactory = DOMCMapReaderFactory;

class DOMStandardFontDataFactory extends _base_factory.BaseStandardFontDataFactory {
  _fetchData(url) {
    return fetchData(url, true);
  }

}

exports.DOMStandardFontDataFactory = DOMStandardFontDataFactory;

class DOMSVGFactory extends _base_factory.BaseSVGFactory {
  _createSVG(type) {
    return document.createElementNS(SVG_NS, type);
  }

}

exports.DOMSVGFactory = DOMSVGFactory;

class PageViewport {
  constructor(_ref) {
    let {
      viewBox,
      scale,
      rotation,
      offsetX = 0,
      offsetY = 0,
      dontFlip = false
    } = _ref;
    this.viewBox = viewBox;
    this.scale = scale;
    this.rotation = rotation;
    this.offsetX = offsetX;
    this.offsetY = offsetY;
    const centerX = (viewBox[2] + viewBox[0]) / 2;
    const centerY = (viewBox[3] + viewBox[1]) / 2;
    let rotateA, rotateB, rotateC, rotateD;
    rotation %= 360;

    if (rotation < 0) {
      rotation += 360;
    }

    switch (rotation) {
      case 180:
        rotateA = -1;
        rotateB = 0;
        rotateC = 0;
        rotateD = 1;
        break;

      case 90:
        rotateA = 0;
        rotateB = 1;
        rotateC = 1;
        rotateD = 0;
        break;

      case 270:
        rotateA = 0;
        rotateB = -1;
        rotateC = -1;
        rotateD = 0;
        break;

      case 0:
        rotateA = 1;
        rotateB = 0;
        rotateC = 0;
        rotateD = -1;
        break;

      default:
        throw new Error("PageViewport: Invalid rotation, must be a multiple of 90 degrees.");
    }

    if (dontFlip) {
      rotateC = -rotateC;
      rotateD = -rotateD;
    }

    let offsetCanvasX, offsetCanvasY;
    let width, height;

    if (rotateA === 0) {
      offsetCanvasX = Math.abs(centerY - viewBox[1]) * scale + offsetX;
      offsetCanvasY = Math.abs(centerX - viewBox[0]) * scale + offsetY;
      width = Math.abs(viewBox[3] - viewBox[1]) * scale;
      height = Math.abs(viewBox[2] - viewBox[0]) * scale;
    } else {
      offsetCanvasX = Math.abs(centerX - viewBox[0]) * scale + offsetX;
      offsetCanvasY = Math.abs(centerY - viewBox[1]) * scale + offsetY;
      width = Math.abs(viewBox[2] - viewBox[0]) * scale;
      height = Math.abs(viewBox[3] - viewBox[1]) * scale;
    }

    this.transform = [rotateA * scale, rotateB * scale, rotateC * scale, rotateD * scale, offsetCanvasX - rotateA * scale * centerX - rotateC * scale * centerY, offsetCanvasY - rotateB * scale * centerX - rotateD * scale * centerY];
    this.width = width;
    this.height = height;
  }

  clone() {
    let {
      scale = this.scale,
      rotation = this.rotation,
      offsetX = this.offsetX,
      offsetY = this.offsetY,
      dontFlip = false
    } = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    return new PageViewport({
      viewBox: this.viewBox.slice(),
      scale,
      rotation,
      offsetX,
      offsetY,
      dontFlip
    });
  }

  convertToViewportPoint(x, y) {
    return _util.Util.applyTransform([x, y], this.transform);
  }

  convertToViewportRectangle(rect) {
    const topLeft = _util.Util.applyTransform([rect[0], rect[1]], this.transform);

    const bottomRight = _util.Util.applyTransform([rect[2], rect[3]], this.transform);

    return [topLeft[0], topLeft[1], bottomRight[0], bottomRight[1]];
  }

  convertToPdfPoint(x, y) {
    return _util.Util.applyInverseTransform([x, y], this.transform);
  }

}

exports.PageViewport = PageViewport;

class RenderingCancelledException extends _util.BaseException {
  constructor(msg, type) {
    super(msg, "RenderingCancelledException");
    this.type = type;
  }

}

exports.RenderingCancelledException = RenderingCancelledException;

function isDataScheme(url) {
  const ii = url.length;
  let i = 0;

  while (i < ii && url[i].trim() === "") {
    i++;
  }

  return url.substring(i, i + 5).toLowerCase() === "data:";
}

function isPdfFile(filename) {
  return typeof filename === "string" && /\.pdf$/i.test(filename);
}

function getFilenameFromUrl(url) {
  const anchor = url.indexOf("#");
  const query = url.indexOf("?");
  const end = Math.min(anchor > 0 ? anchor : url.length, query > 0 ? query : url.length);
  return url.substring(url.lastIndexOf("/", end) + 1, end);
}

function getPdfFilenameFromUrl(url) {
  let defaultFilename = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "document.pdf";

  if (typeof url !== "string") {
    return defaultFilename;
  }

  if (isDataScheme(url)) {
    (0, _util.warn)('getPdfFilenameFromUrl: ignore "data:"-URL for performance reasons.');
    return defaultFilename;
  }

  const reURI = /^(?:(?:[^:]+:)?\/\/[^/]+)?([^?#]*)(\?[^#]*)?(#.*)?$/;
  const reFilename = /[^/?#=]+\.pdf\b(?!.*\.pdf\b)/i;
  const splitURI = reURI.exec(url);
  let suggestedFilename = reFilename.exec(splitURI[1]) || reFilename.exec(splitURI[2]) || reFilename.exec(splitURI[3]);

  if (suggestedFilename) {
    suggestedFilename = suggestedFilename[0];

    if (suggestedFilename.includes("%")) {
      try {
        suggestedFilename = reFilename.exec(decodeURIComponent(suggestedFilename))[0];
      } catch (ex) {}
    }
  }

  return suggestedFilename || defaultFilename;
}

class StatTimer {
  constructor() {
    this.started = Object.create(null);
    this.times = [];
  }

  time(name) {
    if (name in this.started) {
      (0, _util.warn)(`Timer is already running for ${name}`);
    }

    this.started[name] = Date.now();
  }

  timeEnd(name) {
    if (!(name in this.started)) {
      (0, _util.warn)(`Timer has not been started for ${name}`);
    }

    this.times.push({
      name,
      start: this.started[name],
      end: Date.now()
    });
    delete this.started[name];
  }

  toString() {
    const outBuf = [];
    let longest = 0;

    for (const time of this.times) {
      const name = time.name;

      if (name.length > longest) {
        longest = name.length;
      }
    }

    for (const time of this.times) {
      const duration = time.end - time.start;
      outBuf.push(`${time.name.padEnd(longest)} ${duration}ms\n`);
    }

    return outBuf.join("");
  }

}

exports.StatTimer = StatTimer;

function isValidFetchUrl(url, baseUrl) {
  try {
    const {
      protocol
    } = baseUrl ? new URL(url, baseUrl) : new URL(url);
    return protocol === "http:" || protocol === "https:";
  } catch (ex) {
    return false;
  }
}

function loadScript(src) {
  let removeScriptElement = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;

    script.onload = function (evt) {
      if (removeScriptElement) {
        script.remove();
      }

      resolve(evt);
    };

    script.onerror = function () {
      reject(new Error(`Cannot load script at: ${script.src}`));
    };

    (document.head || document.documentElement).append(script);
  });
}

function deprecated(details) {
  console.log("Deprecated API usage: " + details);
}

let pdfDateStringRegex;

class PDFDateString {
  static toDateObject(input) {
    if (!input || typeof input !== "string") {
      return null;
    }

    if (!pdfDateStringRegex) {
      pdfDateStringRegex = new RegExp("^D:" + "(\\d{4})" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "([Z|+|-])?" + "(\\d{2})?" + "'?" + "(\\d{2})?" + "'?");
    }

    const matches = pdfDateStringRegex.exec(input);

    if (!matches) {
      return null;
    }

    const year = parseInt(matches[1], 10);
    let month = parseInt(matches[2], 10);
    month = month >= 1 && month <= 12 ? month - 1 : 0;
    let day = parseInt(matches[3], 10);
    day = day >= 1 && day <= 31 ? day : 1;
    let hour = parseInt(matches[4], 10);
    hour = hour >= 0 && hour <= 23 ? hour : 0;
    let minute = parseInt(matches[5], 10);
    minute = minute >= 0 && minute <= 59 ? minute : 0;
    let second = parseInt(matches[6], 10);
    second = second >= 0 && second <= 59 ? second : 0;
    const universalTimeRelation = matches[7] || "Z";
    let offsetHour = parseInt(matches[8], 10);
    offsetHour = offsetHour >= 0 && offsetHour <= 23 ? offsetHour : 0;
    let offsetMinute = parseInt(matches[9], 10) || 0;
    offsetMinute = offsetMinute >= 0 && offsetMinute <= 59 ? offsetMinute : 0;

    if (universalTimeRelation === "-") {
      hour += offsetHour;
      minute += offsetMinute;
    } else if (universalTimeRelation === "+") {
      hour -= offsetHour;
      minute -= offsetMinute;
    }

    return new Date(Date.UTC(year, month, day, hour, minute, second));
  }

}

exports.PDFDateString = PDFDateString;

function getXfaPageViewport(xfaPage, _ref2) {
  let {
    scale = 1,
    rotation = 0
  } = _ref2;
  const {
    width,
    height
  } = xfaPage.attributes.style;
  const viewBox = [0, 0, parseInt(width), parseInt(height)];
  return new PageViewport({
    viewBox,
    scale,
    rotation
  });
}

function getRGB(color) {
  if (color.startsWith("#")) {
    const colorRGB = parseInt(color.slice(1), 16);
    return [(colorRGB & 0xff0000) >> 16, (colorRGB & 0x00ff00) >> 8, colorRGB & 0x0000ff];
  }

  if (color.startsWith("rgb(")) {
    return color.slice(4, -1).split(",").map(x => parseInt(x));
  }

  if (color.startsWith("rgba(")) {
    return color.slice(5, -1).split(",").map(x => parseInt(x)).slice(0, 3);
  }

  (0, _util.warn)(`Not a valid color format: "${color}"`);
  return [0, 0, 0];
}

function getColorValues(colors) {
  const span = document.createElement("span");
  span.style.visibility = "hidden";
  document.body.append(span);

  for (const name of colors.keys()) {
    span.style.color = name;
    const computedColor = window.getComputedStyle(span).color;
    colors.set(name, getRGB(computedColor));
  }

  span.remove();
}

function getCurrentTransform(ctx) {
  const {
    a,
    b,
    c,
    d,
    e,
    f
  } = ctx.getTransform();
  return [a, b, c, d, e, f];
}

function getCurrentTransformInverse(ctx) {
  const {
    a,
    b,
    c,
    d,
    e,
    f
  } = ctx.getTransform().invertSelf();
  return [a, b, c, d, e, f];
}

/***/ }),
/* 134 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.BaseStandardFontDataFactory = exports.BaseSVGFactory = exports.BaseCanvasFactory = exports.BaseCMapReaderFactory = void 0;

var _util = __w_pdfjs_require__(1);

class BaseCanvasFactory {
  constructor() {
    if (this.constructor === BaseCanvasFactory) {
      (0, _util.unreachable)("Cannot initialize BaseCanvasFactory.");
    }
  }

  create(width, height) {
    if (width <= 0 || height <= 0) {
      throw new Error("Invalid canvas size");
    }

    const canvas = this._createCanvas(width, height);

    return {
      canvas,
      context: canvas.getContext("2d")
    };
  }

  reset(canvasAndContext, width, height) {
    if (!canvasAndContext.canvas) {
      throw new Error("Canvas is not specified");
    }

    if (width <= 0 || height <= 0) {
      throw new Error("Invalid canvas size");
    }

    canvasAndContext.canvas.width = width;
    canvasAndContext.canvas.height = height;
  }

  destroy(canvasAndContext) {
    if (!canvasAndContext.canvas) {
      throw new Error("Canvas is not specified");
    }

    canvasAndContext.canvas.width = 0;
    canvasAndContext.canvas.height = 0;
    canvasAndContext.canvas = null;
    canvasAndContext.context = null;
  }

  _createCanvas(width, height) {
    (0, _util.unreachable)("Abstract method `_createCanvas` called.");
  }

}

exports.BaseCanvasFactory = BaseCanvasFactory;

class BaseCMapReaderFactory {
  constructor(_ref) {
    let {
      baseUrl = null,
      isCompressed = false
    } = _ref;

    if (this.constructor === BaseCMapReaderFactory) {
      (0, _util.unreachable)("Cannot initialize BaseCMapReaderFactory.");
    }

    this.baseUrl = baseUrl;
    this.isCompressed = isCompressed;
  }

  async fetch(_ref2) {
    let {
      name
    } = _ref2;

    if (!this.baseUrl) {
      throw new Error('The CMap "baseUrl" parameter must be specified, ensure that ' + 'the "cMapUrl" and "cMapPacked" API parameters are provided.');
    }

    if (!name) {
      throw new Error("CMap name must be specified.");
    }

    const url = this.baseUrl + name + (this.isCompressed ? ".bcmap" : "");
    const compressionType = this.isCompressed ? _util.CMapCompressionType.BINARY : _util.CMapCompressionType.NONE;
    return this._fetchData(url, compressionType).catch(reason => {
      throw new Error(`Unable to load ${this.isCompressed ? "binary " : ""}CMap at: ${url}`);
    });
  }

  _fetchData(url, compressionType) {
    (0, _util.unreachable)("Abstract method `_fetchData` called.");
  }

}

exports.BaseCMapReaderFactory = BaseCMapReaderFactory;

class BaseStandardFontDataFactory {
  constructor(_ref3) {
    let {
      baseUrl = null
    } = _ref3;

    if (this.constructor === BaseStandardFontDataFactory) {
      (0, _util.unreachable)("Cannot initialize BaseStandardFontDataFactory.");
    }

    this.baseUrl = baseUrl;
  }

  async fetch(_ref4) {
    let {
      filename
    } = _ref4;

    if (!this.baseUrl) {
      throw new Error('The standard font "baseUrl" parameter must be specified, ensure that ' + 'the "standardFontDataUrl" API parameter is provided.');
    }

    if (!filename) {
      throw new Error("Font filename must be specified.");
    }

    const url = `${this.baseUrl}${filename}`;
    return this._fetchData(url).catch(reason => {
      throw new Error(`Unable to load font data at: ${url}`);
    });
  }

  _fetchData(url) {
    (0, _util.unreachable)("Abstract method `_fetchData` called.");
  }

}

exports.BaseStandardFontDataFactory = BaseStandardFontDataFactory;

class BaseSVGFactory {
  constructor() {
    if (this.constructor === BaseSVGFactory) {
      (0, _util.unreachable)("Cannot initialize BaseSVGFactory.");
    }
  }

  create(width, height) {
    let skipDimensions = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;

    if (width <= 0 || height <= 0) {
      throw new Error("Invalid SVG dimensions");
    }

    const svg = this._createSVG("svg:svg");

    svg.setAttribute("version", "1.1");

    if (!skipDimensions) {
      svg.setAttribute("width", `${width}px`);
      svg.setAttribute("height", `${height}px`);
    }

    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    return svg;
  }

  createElement(type) {
    if (typeof type !== "string") {
      throw new Error("Invalid SVG element type");
    }

    return this._createSVG(type);
  }

  _createSVG(type) {
    (0, _util.unreachable)("Abstract method `_createSVG` called.");
  }

}

exports.BaseSVGFactory = BaseSVGFactory;

/***/ }),
/* 135 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.MurmurHash3_64 = void 0;

var _util = __w_pdfjs_require__(1);

const SEED = 0xc3d2e1f0;
const MASK_HIGH = 0xffff0000;
const MASK_LOW = 0xffff;

class MurmurHash3_64 {
  constructor(seed) {
    this.h1 = seed ? seed & 0xffffffff : SEED;
    this.h2 = seed ? seed & 0xffffffff : SEED;
  }

  update(input) {
    let data, length;

    if (typeof input === "string") {
      data = new Uint8Array(input.length * 2);
      length = 0;

      for (let i = 0, ii = input.length; i < ii; i++) {
        const code = input.charCodeAt(i);

        if (code <= 0xff) {
          data[length++] = code;
        } else {
          data[length++] = code >>> 8;
          data[length++] = code & 0xff;
        }
      }
    } else if ((0, _util.isArrayBuffer)(input)) {
      data = input.slice();
      length = data.byteLength;
    } else {
      throw new Error("Wrong data format in MurmurHash3_64_update. " + "Input must be a string or array.");
    }

    const blockCounts = length >> 2;
    const tailLength = length - blockCounts * 4;
    const dataUint32 = new Uint32Array(data.buffer, 0, blockCounts);
    let k1 = 0,
        k2 = 0;
    let h1 = this.h1,
        h2 = this.h2;
    const C1 = 0xcc9e2d51,
          C2 = 0x1b873593;
    const C1_LOW = C1 & MASK_LOW,
          C2_LOW = C2 & MASK_LOW;

    for (let i = 0; i < blockCounts; i++) {
      if (i & 1) {
        k1 = dataUint32[i];
        k1 = k1 * C1 & MASK_HIGH | k1 * C1_LOW & MASK_LOW;
        k1 = k1 << 15 | k1 >>> 17;
        k1 = k1 * C2 & MASK_HIGH | k1 * C2_LOW & MASK_LOW;
        h1 ^= k1;
        h1 = h1 << 13 | h1 >>> 19;
        h1 = h1 * 5 + 0xe6546b64;
      } else {
        k2 = dataUint32[i];
        k2 = k2 * C1 & MASK_HIGH | k2 * C1_LOW & MASK_LOW;
        k2 = k2 << 15 | k2 >>> 17;
        k2 = k2 * C2 & MASK_HIGH | k2 * C2_LOW & MASK_LOW;
        h2 ^= k2;
        h2 = h2 << 13 | h2 >>> 19;
        h2 = h2 * 5 + 0xe6546b64;
      }
    }

    k1 = 0;

    switch (tailLength) {
      case 3:
        k1 ^= data[blockCounts * 4 + 2] << 16;

      case 2:
        k1 ^= data[blockCounts * 4 + 1] << 8;

      case 1:
        k1 ^= data[blockCounts * 4];
        k1 = k1 * C1 & MASK_HIGH | k1 * C1_LOW & MASK_LOW;
        k1 = k1 << 15 | k1 >>> 17;
        k1 = k1 * C2 & MASK_HIGH | k1 * C2_LOW & MASK_LOW;

        if (blockCounts & 1) {
          h1 ^= k1;
        } else {
          h2 ^= k1;
        }

    }

    this.h1 = h1;
    this.h2 = h2;
  }

  hexdigest() {
    let h1 = this.h1,
        h2 = this.h2;
    h1 ^= h2 >>> 1;
    h1 = h1 * 0xed558ccd & MASK_HIGH | h1 * 0x8ccd & MASK_LOW;
    h2 = h2 * 0xff51afd7 & MASK_HIGH | ((h2 << 16 | h1 >>> 16) * 0xafd7ed55 & MASK_HIGH) >>> 16;
    h1 ^= h2 >>> 1;
    h1 = h1 * 0x1a85ec53 & MASK_HIGH | h1 * 0xec53 & MASK_LOW;
    h2 = h2 * 0xc4ceb9fe & MASK_HIGH | ((h2 << 16 | h1 >>> 16) * 0xb9fe1a85 & MASK_HIGH) >>> 16;
    h1 ^= h2 >>> 1;
    const hex1 = (h1 >>> 0).toString(16),
          hex2 = (h2 >>> 0).toString(16);
    return hex1.padStart(8, "0") + hex2.padStart(8, "0");
  }

}

exports.MurmurHash3_64 = MurmurHash3_64;

/***/ }),
/* 136 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.FontLoader = exports.FontFaceObject = void 0;

var _util = __w_pdfjs_require__(1);

class BaseFontLoader {
  constructor(_ref) {
    let {
      docId,
      onUnsupportedFeature,
      ownerDocument = globalThis.document,
      styleElement = null
    } = _ref;

    if (this.constructor === BaseFontLoader) {
      (0, _util.unreachable)("Cannot initialize BaseFontLoader.");
    }

    this.docId = docId;
    this._onUnsupportedFeature = onUnsupportedFeature;
    this._document = ownerDocument;
    this.nativeFontFaces = [];
    this.styleElement = null;
  }

  addNativeFontFace(nativeFontFace) {
    this.nativeFontFaces.push(nativeFontFace);

    this._document.fonts.add(nativeFontFace);
  }

  insertRule(rule) {
    let styleElement = this.styleElement;

    if (!styleElement) {
      styleElement = this.styleElement = this._document.createElement("style");
      styleElement.id = `PDFJS_FONT_STYLE_TAG_${this.docId}`;

      this._document.documentElement.getElementsByTagName("head")[0].append(styleElement);
    }

    const styleSheet = styleElement.sheet;
    styleSheet.insertRule(rule, styleSheet.cssRules.length);
  }

  clear() {
    for (const nativeFontFace of this.nativeFontFaces) {
      this._document.fonts.delete(nativeFontFace);
    }

    this.nativeFontFaces.length = 0;

    if (this.styleElement) {
      this.styleElement.remove();
      this.styleElement = null;
    }
  }

  async bind(font) {
    if (font.attached || font.missingFile) {
      return;
    }

    font.attached = true;

    if (this.isFontLoadingAPISupported) {
      const nativeFontFace = font.createNativeFontFace();

      if (nativeFontFace) {
        this.addNativeFontFace(nativeFontFace);

        try {
          await nativeFontFace.loaded;
        } catch (ex) {
          this._onUnsupportedFeature({
            featureId: _util.UNSUPPORTED_FEATURES.errorFontLoadNative
          });

          (0, _util.warn)(`Failed to load font '${nativeFontFace.family}': '${ex}'.`);
          font.disableFontFace = true;
          throw ex;
        }
      }

      return;
    }

    const rule = font.createFontFaceRule();

    if (rule) {
      this.insertRule(rule);

      if (this.isSyncFontLoadingSupported) {
        return;
      }

      await new Promise(resolve => {
        const request = this._queueLoadingCallback(resolve);

        this._prepareFontLoadEvent([rule], [font], request);
      });
    }
  }

  _queueLoadingCallback(callback) {
    (0, _util.unreachable)("Abstract method `_queueLoadingCallback`.");
  }

  get isFontLoadingAPISupported() {
    var _this$_document;

    const hasFonts = !!((_this$_document = this._document) !== null && _this$_document !== void 0 && _this$_document.fonts);
    return (0, _util.shadow)(this, "isFontLoadingAPISupported", hasFonts);
  }

  get isSyncFontLoadingSupported() {
    (0, _util.unreachable)("Abstract method `isSyncFontLoadingSupported`.");
  }

  get _loadTestFont() {
    (0, _util.unreachable)("Abstract method `_loadTestFont`.");
  }

  _prepareFontLoadEvent(rules, fontsToLoad, request) {
    (0, _util.unreachable)("Abstract method `_prepareFontLoadEvent`.");
  }

}

let FontLoader;
exports.FontLoader = FontLoader;
{
  exports.FontLoader = FontLoader = class GenericFontLoader extends BaseFontLoader {
    constructor(params) {
      super(params);
      this.loadingContext = {
        requests: [],
        nextRequestId: 0
      };
      this.loadTestFontId = 0;
    }

    get isSyncFontLoadingSupported() {
      let supported = false;

      if (typeof navigator === "undefined") {
        supported = true;
      } else {
        const m = /Mozilla\/5.0.*?rv:(\d+).*? Gecko/.exec(navigator.userAgent);

        if ((m === null || m === void 0 ? void 0 : m[1]) >= 14) {
          supported = true;
        }
      }

      return (0, _util.shadow)(this, "isSyncFontLoadingSupported", supported);
    }

    _queueLoadingCallback(callback) {
      function completeRequest() {
        (0, _util.assert)(!request.done, "completeRequest() cannot be called twice.");
        request.done = true;

        while (context.requests.length > 0 && context.requests[0].done) {
          const otherRequest = context.requests.shift();
          setTimeout(otherRequest.callback, 0);
        }
      }

      const context = this.loadingContext;
      const request = {
        id: `pdfjs-font-loading-${context.nextRequestId++}`,
        done: false,
        complete: completeRequest,
        callback
      };
      context.requests.push(request);
      return request;
    }

    get _loadTestFont() {
      const getLoadTestFont = function () {
        return atob("T1RUTwALAIAAAwAwQ0ZGIDHtZg4AAAOYAAAAgUZGVE1lkzZwAAAEHAAAABxHREVGABQA" + "FQAABDgAAAAeT1MvMlYNYwkAAAEgAAAAYGNtYXABDQLUAAACNAAAAUJoZWFk/xVFDQAA" + "ALwAAAA2aGhlYQdkA+oAAAD0AAAAJGhtdHgD6AAAAAAEWAAAAAZtYXhwAAJQAAAAARgA" + "AAAGbmFtZVjmdH4AAAGAAAAAsXBvc3T/hgAzAAADeAAAACAAAQAAAAEAALZRFsRfDzz1" + "AAsD6AAAAADOBOTLAAAAAM4KHDwAAAAAA+gDIQAAAAgAAgAAAAAAAAABAAADIQAAAFoD" + "6AAAAAAD6AABAAAAAAAAAAAAAAAAAAAAAQAAUAAAAgAAAAQD6AH0AAUAAAKKArwAAACM" + "AooCvAAAAeAAMQECAAACAAYJAAAAAAAAAAAAAQAAAAAAAAAAAAAAAFBmRWQAwAAuAC4D" + "IP84AFoDIQAAAAAAAQAAAAAAAAAAACAAIAABAAAADgCuAAEAAAAAAAAAAQAAAAEAAAAA" + "AAEAAQAAAAEAAAAAAAIAAQAAAAEAAAAAAAMAAQAAAAEAAAAAAAQAAQAAAAEAAAAAAAUA" + "AQAAAAEAAAAAAAYAAQAAAAMAAQQJAAAAAgABAAMAAQQJAAEAAgABAAMAAQQJAAIAAgAB" + "AAMAAQQJAAMAAgABAAMAAQQJAAQAAgABAAMAAQQJAAUAAgABAAMAAQQJAAYAAgABWABY" + "AAAAAAAAAwAAAAMAAAAcAAEAAAAAADwAAwABAAAAHAAEACAAAAAEAAQAAQAAAC7//wAA" + "AC7////TAAEAAAAAAAABBgAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAD/gwAyAAAAAQAAAAAAAAAAAAAAAAAA" + "AAABAAQEAAEBAQJYAAEBASH4DwD4GwHEAvgcA/gXBIwMAYuL+nz5tQXkD5j3CBLnEQAC" + "AQEBIVhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYAAABAQAADwACAQEEE/t3" + "Dov6fAH6fAT+fPp8+nwHDosMCvm1Cvm1DAz6fBQAAAAAAAABAAAAAMmJbzEAAAAAzgTj" + "FQAAAADOBOQpAAEAAAAAAAAADAAUAAQAAAABAAAAAgABAAAAAAAAAAAD6AAAAAAAAA==");
      };

      return (0, _util.shadow)(this, "_loadTestFont", getLoadTestFont());
    }

    _prepareFontLoadEvent(rules, fonts, request) {
      function int32(data, offset) {
        return data.charCodeAt(offset) << 24 | data.charCodeAt(offset + 1) << 16 | data.charCodeAt(offset + 2) << 8 | data.charCodeAt(offset + 3) & 0xff;
      }

      function spliceString(s, offset, remove, insert) {
        const chunk1 = s.substring(0, offset);
        const chunk2 = s.substring(offset + remove);
        return chunk1 + insert + chunk2;
      }

      let i, ii;

      const canvas = this._document.createElement("canvas");

      canvas.width = 1;
      canvas.height = 1;
      const ctx = canvas.getContext("2d");
      let called = 0;

      function isFontReady(name, callback) {
        called++;

        if (called > 30) {
          (0, _util.warn)("Load test font never loaded.");
          callback();
          return;
        }

        ctx.font = "30px " + name;
        ctx.fillText(".", 0, 20);
        const imageData = ctx.getImageData(0, 0, 1, 1);

        if (imageData.data[3] > 0) {
          callback();
          return;
        }

        setTimeout(isFontReady.bind(null, name, callback));
      }

      const loadTestFontId = `lt${Date.now()}${this.loadTestFontId++}`;
      let data = this._loadTestFont;
      const COMMENT_OFFSET = 976;
      data = spliceString(data, COMMENT_OFFSET, loadTestFontId.length, loadTestFontId);
      const CFF_CHECKSUM_OFFSET = 16;
      const XXXX_VALUE = 0x58585858;
      let checksum = int32(data, CFF_CHECKSUM_OFFSET);

      for (i = 0, ii = loadTestFontId.length - 3; i < ii; i += 4) {
        checksum = checksum - XXXX_VALUE + int32(loadTestFontId, i) | 0;
      }

      if (i < loadTestFontId.length) {
        checksum = checksum - XXXX_VALUE + int32(loadTestFontId + "XXX", i) | 0;
      }

      data = spliceString(data, CFF_CHECKSUM_OFFSET, 4, (0, _util.string32)(checksum));
      const url = `url(data:font/opentype;base64,${btoa(data)});`;
      const rule = `@font-face {font-family:"${loadTestFontId}";src:${url}}`;
      this.insertRule(rule);
      const names = [];

      for (const font of fonts) {
        names.push(font.loadedName);
      }

      names.push(loadTestFontId);

      const div = this._document.createElement("div");

      div.style.visibility = "hidden";
      div.style.width = div.style.height = "10px";
      div.style.position = "absolute";
      div.style.top = div.style.left = "0px";

      for (const name of names) {
        const span = this._document.createElement("span");

        span.textContent = "Hi";
        span.style.fontFamily = name;
        div.append(span);
      }

      this._document.body.append(div);

      isFontReady(loadTestFontId, () => {
        div.remove();
        request.complete();
      });
    }

  };
}

class FontFaceObject {
  constructor(translatedData, _ref2) {
    let {
      isEvalSupported = true,
      disableFontFace = false,
      ignoreErrors = false,
      onUnsupportedFeature,
      fontRegistry = null
    } = _ref2;
    this.compiledGlyphs = Object.create(null);

    for (const i in translatedData) {
      this[i] = translatedData[i];
    }

    this.isEvalSupported = isEvalSupported !== false;
    this.disableFontFace = disableFontFace === true;
    this.ignoreErrors = ignoreErrors === true;
    this._onUnsupportedFeature = onUnsupportedFeature;
    this.fontRegistry = fontRegistry;
  }

  createNativeFontFace() {
    if (!this.data || this.disableFontFace) {
      return null;
    }

    let nativeFontFace;

    if (!this.cssFontInfo) {
      nativeFontFace = new FontFace(this.loadedName, this.data, {});
    } else {
      const css = {
        weight: this.cssFontInfo.fontWeight
      };

      if (this.cssFontInfo.italicAngle) {
        css.style = `oblique ${this.cssFontInfo.italicAngle}deg`;
      }

      nativeFontFace = new FontFace(this.cssFontInfo.fontFamily, this.data, css);
    }

    if (this.fontRegistry) {
      this.fontRegistry.registerFont(this);
    }

    return nativeFontFace;
  }

  createFontFaceRule() {
    if (!this.data || this.disableFontFace) {
      return null;
    }

    const data = (0, _util.bytesToString)(this.data);
    const url = `url(data:${this.mimetype};base64,${btoa(data)});`;
    let rule;

    if (!this.cssFontInfo) {
      rule = `@font-face {font-family:"${this.loadedName}";src:${url}}`;
    } else {
      let css = `font-weight: ${this.cssFontInfo.fontWeight};`;

      if (this.cssFontInfo.italicAngle) {
        css += `font-style: oblique ${this.cssFontInfo.italicAngle}deg;`;
      }

      rule = `@font-face {font-family:"${this.cssFontInfo.fontFamily}";${css}src:${url}}`;
    }

    if (this.fontRegistry) {
      this.fontRegistry.registerFont(this, url);
    }

    return rule;
  }

  getPathGenerator(objs, character) {
    if (this.compiledGlyphs[character] !== undefined) {
      return this.compiledGlyphs[character];
    }

    let cmds;

    try {
      cmds = objs.get(this.loadedName + "_path_" + character);
    } catch (ex) {
      if (!this.ignoreErrors) {
        throw ex;
      }

      this._onUnsupportedFeature({
        featureId: _util.UNSUPPORTED_FEATURES.errorFontGetPath
      });

      (0, _util.warn)(`getPathGenerator - ignoring character: "${ex}".`);
      return this.compiledGlyphs[character] = function (c, size) {};
    }

    if (this.isEvalSupported && _util.FeatureTest.isEvalSupported) {
      const jsBuf = [];

      for (const current of cmds) {
        const args = current.args !== undefined ? current.args.join(",") : "";
        jsBuf.push("c.", current.cmd, "(", args, ");\n");
      }

      return this.compiledGlyphs[character] = new Function("c", "size", jsBuf.join(""));
    }

    return this.compiledGlyphs[character] = function (c, size) {
      for (const current of cmds) {
        if (current.cmd === "scale") {
          current.args = [size, -size];
        }

        c[current.cmd].apply(c, current.args);
      }
    };
  }

}

exports.FontFaceObject = FontFaceObject;

/***/ }),
/* 137 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.CanvasGraphics = void 0;

var _display_utils = __w_pdfjs_require__(133);

var _util = __w_pdfjs_require__(1);

var _pattern_helper = __w_pdfjs_require__(138);

var _image_utils = __w_pdfjs_require__(139);

var _is_node = __w_pdfjs_require__(3);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

const MIN_FONT_SIZE = 16;
const MAX_FONT_SIZE = 100;
const MAX_GROUP_SIZE = 4096;
const EXECUTION_TIME = 15;
const EXECUTION_STEPS = 10;
const MAX_SIZE_TO_COMPILE = _is_node.isNodeJS && typeof Path2D === "undefined" ? -1 : 1000;
const FULL_CHUNK_HEIGHT = 16;

function mirrorContextOperations(ctx, destCtx) {
  if (ctx._removeMirroring) {
    throw new Error("Context is already forwarding operations.");
  }

  ctx.__originalSave = ctx.save;
  ctx.__originalRestore = ctx.restore;
  ctx.__originalRotate = ctx.rotate;
  ctx.__originalScale = ctx.scale;
  ctx.__originalTranslate = ctx.translate;
  ctx.__originalTransform = ctx.transform;
  ctx.__originalSetTransform = ctx.setTransform;
  ctx.__originalResetTransform = ctx.resetTransform;
  ctx.__originalClip = ctx.clip;
  ctx.__originalMoveTo = ctx.moveTo;
  ctx.__originalLineTo = ctx.lineTo;
  ctx.__originalBezierCurveTo = ctx.bezierCurveTo;
  ctx.__originalRect = ctx.rect;
  ctx.__originalClosePath = ctx.closePath;
  ctx.__originalBeginPath = ctx.beginPath;

  ctx._removeMirroring = () => {
    ctx.save = ctx.__originalSave;
    ctx.restore = ctx.__originalRestore;
    ctx.rotate = ctx.__originalRotate;
    ctx.scale = ctx.__originalScale;
    ctx.translate = ctx.__originalTranslate;
    ctx.transform = ctx.__originalTransform;
    ctx.setTransform = ctx.__originalSetTransform;
    ctx.resetTransform = ctx.__originalResetTransform;
    ctx.clip = ctx.__originalClip;
    ctx.moveTo = ctx.__originalMoveTo;
    ctx.lineTo = ctx.__originalLineTo;
    ctx.bezierCurveTo = ctx.__originalBezierCurveTo;
    ctx.rect = ctx.__originalRect;
    ctx.closePath = ctx.__originalClosePath;
    ctx.beginPath = ctx.__originalBeginPath;
    delete ctx._removeMirroring;
  };

  ctx.save = function ctxSave() {
    destCtx.save();

    this.__originalSave();
  };

  ctx.restore = function ctxRestore() {
    destCtx.restore();

    this.__originalRestore();
  };

  ctx.translate = function ctxTranslate(x, y) {
    destCtx.translate(x, y);

    this.__originalTranslate(x, y);
  };

  ctx.scale = function ctxScale(x, y) {
    destCtx.scale(x, y);

    this.__originalScale(x, y);
  };

  ctx.transform = function ctxTransform(a, b, c, d, e, f) {
    destCtx.transform(a, b, c, d, e, f);

    this.__originalTransform(a, b, c, d, e, f);
  };

  ctx.setTransform = function ctxSetTransform(a, b, c, d, e, f) {
    destCtx.setTransform(a, b, c, d, e, f);

    this.__originalSetTransform(a, b, c, d, e, f);
  };

  ctx.resetTransform = function ctxResetTransform() {
    destCtx.resetTransform();

    this.__originalResetTransform();
  };

  ctx.rotate = function ctxRotate(angle) {
    destCtx.rotate(angle);

    this.__originalRotate(angle);
  };

  ctx.clip = function ctxRotate(rule) {
    destCtx.clip(rule);

    this.__originalClip(rule);
  };

  ctx.moveTo = function (x, y) {
    destCtx.moveTo(x, y);

    this.__originalMoveTo(x, y);
  };

  ctx.lineTo = function (x, y) {
    destCtx.lineTo(x, y);

    this.__originalLineTo(x, y);
  };

  ctx.bezierCurveTo = function (cp1x, cp1y, cp2x, cp2y, x, y) {
    destCtx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, x, y);

    this.__originalBezierCurveTo(cp1x, cp1y, cp2x, cp2y, x, y);
  };

  ctx.rect = function (x, y, width, height) {
    destCtx.rect(x, y, width, height);

    this.__originalRect(x, y, width, height);
  };

  ctx.closePath = function () {
    destCtx.closePath();

    this.__originalClosePath();
  };

  ctx.beginPath = function () {
    destCtx.beginPath();

    this.__originalBeginPath();
  };
}

class CachedCanvases {
  constructor(canvasFactory) {
    this.canvasFactory = canvasFactory;
    this.cache = Object.create(null);
  }

  getCanvas(id, width, height) {
    let canvasEntry;

    if (this.cache[id] !== undefined) {
      canvasEntry = this.cache[id];
      this.canvasFactory.reset(canvasEntry, width, height);
    } else {
      canvasEntry = this.canvasFactory.create(width, height);
      this.cache[id] = canvasEntry;
    }

    return canvasEntry;
  }

  delete(id) {
    delete this.cache[id];
  }

  clear() {
    for (const id in this.cache) {
      const canvasEntry = this.cache[id];
      this.canvasFactory.destroy(canvasEntry);
      delete this.cache[id];
    }
  }

}

function drawImageAtIntegerCoords(ctx, srcImg, srcX, srcY, srcW, srcH, destX, destY, destW, destH) {
  const [a, b, c, d, tx, ty] = (0, _display_utils.getCurrentTransform)(ctx);

  if (b === 0 && c === 0) {
    const tlX = destX * a + tx;
    const rTlX = Math.round(tlX);
    const tlY = destY * d + ty;
    const rTlY = Math.round(tlY);
    const brX = (destX + destW) * a + tx;
    const rWidth = Math.abs(Math.round(brX) - rTlX) || 1;
    const brY = (destY + destH) * d + ty;
    const rHeight = Math.abs(Math.round(brY) - rTlY) || 1;
    ctx.setTransform(Math.sign(a), 0, 0, Math.sign(d), rTlX, rTlY);
    ctx.drawImage(srcImg, srcX, srcY, srcW, srcH, 0, 0, rWidth, rHeight);
    ctx.setTransform(a, b, c, d, tx, ty);
    return [rWidth, rHeight];
  }

  if (a === 0 && d === 0) {
    const tlX = destY * c + tx;
    const rTlX = Math.round(tlX);
    const tlY = destX * b + ty;
    const rTlY = Math.round(tlY);
    const brX = (destY + destH) * c + tx;
    const rWidth = Math.abs(Math.round(brX) - rTlX) || 1;
    const brY = (destX + destW) * b + ty;
    const rHeight = Math.abs(Math.round(brY) - rTlY) || 1;
    ctx.setTransform(0, Math.sign(b), Math.sign(c), 0, rTlX, rTlY);
    ctx.drawImage(srcImg, srcX, srcY, srcW, srcH, 0, 0, rHeight, rWidth);
    ctx.setTransform(a, b, c, d, tx, ty);
    return [rHeight, rWidth];
  }

  ctx.drawImage(srcImg, srcX, srcY, srcW, srcH, destX, destY, destW, destH);
  const scaleX = Math.hypot(a, b);
  const scaleY = Math.hypot(c, d);
  return [scaleX * destW, scaleY * destH];
}

function compileType3Glyph(imgData) {
  const {
    width,
    height
  } = imgData;

  if (width > MAX_SIZE_TO_COMPILE || height > MAX_SIZE_TO_COMPILE) {
    return null;
  }

  const POINT_TO_PROCESS_LIMIT = 1000;
  const POINT_TYPES = new Uint8Array([0, 2, 4, 0, 1, 0, 5, 4, 8, 10, 0, 8, 0, 2, 1, 0]);
  const width1 = width + 1;
  let points = new Uint8Array(width1 * (height + 1));
  let i, j, j0;
  const lineSize = width + 7 & ~7;
  let data = new Uint8Array(lineSize * height),
      pos = 0;

  for (const elem of imgData.data) {
    let mask = 128;

    while (mask > 0) {
      data[pos++] = elem & mask ? 0 : 255;
      mask >>= 1;
    }
  }

  let count = 0;
  pos = 0;

  if (data[pos] !== 0) {
    points[0] = 1;
    ++count;
  }

  for (j = 1; j < width; j++) {
    if (data[pos] !== data[pos + 1]) {
      points[j] = data[pos] ? 2 : 1;
      ++count;
    }

    pos++;
  }

  if (data[pos] !== 0) {
    points[j] = 2;
    ++count;
  }

  for (i = 1; i < height; i++) {
    pos = i * lineSize;
    j0 = i * width1;

    if (data[pos - lineSize] !== data[pos]) {
      points[j0] = data[pos] ? 1 : 8;
      ++count;
    }

    let sum = (data[pos] ? 4 : 0) + (data[pos - lineSize] ? 8 : 0);

    for (j = 1; j < width; j++) {
      sum = (sum >> 2) + (data[pos + 1] ? 4 : 0) + (data[pos - lineSize + 1] ? 8 : 0);

      if (POINT_TYPES[sum]) {
        points[j0 + j] = POINT_TYPES[sum];
        ++count;
      }

      pos++;
    }

    if (data[pos - lineSize] !== data[pos]) {
      points[j0 + j] = data[pos] ? 2 : 4;
      ++count;
    }

    if (count > POINT_TO_PROCESS_LIMIT) {
      return null;
    }
  }

  pos = lineSize * (height - 1);
  j0 = i * width1;

  if (data[pos] !== 0) {
    points[j0] = 8;
    ++count;
  }

  for (j = 1; j < width; j++) {
    if (data[pos] !== data[pos + 1]) {
      points[j0 + j] = data[pos] ? 4 : 8;
      ++count;
    }

    pos++;
  }

  if (data[pos] !== 0) {
    points[j0 + j] = 4;
    ++count;
  }

  if (count > POINT_TO_PROCESS_LIMIT) {
    return null;
  }

  const steps = new Int32Array([0, width1, -1, 0, -width1, 0, 0, 0, 1]);
  const path = new Path2D();

  for (i = 0; count && i <= height; i++) {
    let p = i * width1;
    const end = p + width;

    while (p < end && !points[p]) {
      p++;
    }

    if (p === end) {
      continue;
    }

    path.moveTo(p % width1, i);
    const p0 = p;
    let type = points[p];

    do {
      const step = steps[type];

      do {
        p += step;
      } while (!points[p]);

      const pp = points[p];

      if (pp !== 5 && pp !== 10) {
        type = pp;
        points[p] = 0;
      } else {
        type = pp & 0x33 * type >> 4;
        points[p] &= type >> 2 | type << 2;
      }

      path.lineTo(p % width1, p / width1 | 0);

      if (!points[p]) {
        --count;
      }
    } while (p0 !== p);

    --i;
  }

  data = null;
  points = null;

  const drawOutline = function (c) {
    c.save();
    c.scale(1 / width, -1 / height);
    c.translate(0, -height);
    c.fill(path);
    c.beginPath();
    c.restore();
  };

  return drawOutline;
}

class CanvasExtraState {
  constructor(width, height) {
    this.alphaIsShape = false;
    this.fontSize = 0;
    this.fontSizeScale = 1;
    this.textMatrix = _util.IDENTITY_MATRIX;
    this.textMatrixScale = 1;
    this.fontMatrix = _util.FONT_IDENTITY_MATRIX;
    this.leading = 0;
    this.x = 0;
    this.y = 0;
    this.lineX = 0;
    this.lineY = 0;
    this.charSpacing = 0;
    this.wordSpacing = 0;
    this.textHScale = 1;
    this.textRenderingMode = _util.TextRenderingMode.FILL;
    this.textRise = 0;
    this.fillColor = "#000000";
    this.strokeColor = "#000000";
    this.patternFill = false;
    this.fillAlpha = 1;
    this.strokeAlpha = 1;
    this.lineWidth = 1;
    this.activeSMask = null;
    this.transferMaps = null;
    this.startNewPathAndClipBox([0, 0, width, height]);
  }

  clone() {
    const clone = Object.create(this);
    clone.clipBox = this.clipBox.slice();
    return clone;
  }

  setCurrentPoint(x, y) {
    this.x = x;
    this.y = y;
  }

  updatePathMinMax(transform, x, y) {
    [x, y] = _util.Util.applyTransform([x, y], transform);
    this.minX = Math.min(this.minX, x);
    this.minY = Math.min(this.minY, y);
    this.maxX = Math.max(this.maxX, x);
    this.maxY = Math.max(this.maxY, y);
  }

  updateRectMinMax(transform, rect) {
    const p1 = _util.Util.applyTransform(rect, transform);

    const p2 = _util.Util.applyTransform(rect.slice(2), transform);

    this.minX = Math.min(this.minX, p1[0], p2[0]);
    this.minY = Math.min(this.minY, p1[1], p2[1]);
    this.maxX = Math.max(this.maxX, p1[0], p2[0]);
    this.maxY = Math.max(this.maxY, p1[1], p2[1]);
  }

  updateScalingPathMinMax(transform, minMax) {
    _util.Util.scaleMinMax(transform, minMax);

    this.minX = Math.min(this.minX, minMax[0]);
    this.maxX = Math.max(this.maxX, minMax[1]);
    this.minY = Math.min(this.minY, minMax[2]);
    this.maxY = Math.max(this.maxY, minMax[3]);
  }

  updateCurvePathMinMax(transform, x0, y0, x1, y1, x2, y2, x3, y3, minMax) {
    const box = _util.Util.bezierBoundingBox(x0, y0, x1, y1, x2, y2, x3, y3);

    if (minMax) {
      minMax[0] = Math.min(minMax[0], box[0], box[2]);
      minMax[1] = Math.max(minMax[1], box[0], box[2]);
      minMax[2] = Math.min(minMax[2], box[1], box[3]);
      minMax[3] = Math.max(minMax[3], box[1], box[3]);
      return;
    }

    this.updateRectMinMax(transform, box);
  }

  getPathBoundingBox() {
    let pathType = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : _pattern_helper.PathType.FILL;
    let transform = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
    const box = [this.minX, this.minY, this.maxX, this.maxY];

    if (pathType === _pattern_helper.PathType.STROKE) {
      if (!transform) {
        (0, _util.unreachable)("Stroke bounding box must include transform.");
      }

      const scale = _util.Util.singularValueDecompose2dScale(transform);

      const xStrokePad = scale[0] * this.lineWidth / 2;
      const yStrokePad = scale[1] * this.lineWidth / 2;
      box[0] -= xStrokePad;
      box[1] -= yStrokePad;
      box[2] += xStrokePad;
      box[3] += yStrokePad;
    }

    return box;
  }

  updateClipFromPath() {
    const intersect = _util.Util.intersect(this.clipBox, this.getPathBoundingBox());

    this.startNewPathAndClipBox(intersect || [0, 0, 0, 0]);
  }

  isEmptyClip() {
    return this.minX === Infinity;
  }

  startNewPathAndClipBox(box) {
    this.clipBox = box;
    this.minX = Infinity;
    this.minY = Infinity;
    this.maxX = 0;
    this.maxY = 0;
  }

  getClippedPathBoundingBox() {
    let pathType = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : _pattern_helper.PathType.FILL;
    let transform = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
    return _util.Util.intersect(this.clipBox, this.getPathBoundingBox(pathType, transform));
  }

}

function putBinaryImageData(ctx, imgData) {
  let transferMaps = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;

  if (typeof ImageData !== "undefined" && imgData instanceof ImageData) {
    ctx.putImageData(imgData, 0, 0);
    return;
  }

  const height = imgData.height,
        width = imgData.width;
  const partialChunkHeight = height % FULL_CHUNK_HEIGHT;
  const fullChunks = (height - partialChunkHeight) / FULL_CHUNK_HEIGHT;
  const totalChunks = partialChunkHeight === 0 ? fullChunks : fullChunks + 1;
  const chunkImgData = ctx.createImageData(width, FULL_CHUNK_HEIGHT);
  let srcPos = 0,
      destPos;
  const src = imgData.data;
  const dest = chunkImgData.data;
  let i, j, thisChunkHeight, elemsInThisChunk;
  let transferMapRed, transferMapGreen, transferMapBlue, transferMapGray;

  if (transferMaps) {
    switch (transferMaps.length) {
      case 1:
        transferMapRed = transferMaps[0];
        transferMapGreen = transferMaps[0];
        transferMapBlue = transferMaps[0];
        transferMapGray = transferMaps[0];
        break;

      case 4:
        transferMapRed = transferMaps[0];
        transferMapGreen = transferMaps[1];
        transferMapBlue = transferMaps[2];
        transferMapGray = transferMaps[3];
        break;
    }
  }

  if (imgData.kind === _util.ImageKind.GRAYSCALE_1BPP) {
    const srcLength = src.byteLength;
    const dest32 = new Uint32Array(dest.buffer, 0, dest.byteLength >> 2);
    const dest32DataLength = dest32.length;
    const fullSrcDiff = width + 7 >> 3;
    let white = 0xffffffff;
    let black = _util.FeatureTest.isLittleEndian ? 0xff000000 : 0x000000ff;

    if (transferMapGray) {
      if (transferMapGray[0] === 0xff && transferMapGray[0xff] === 0) {
        [white, black] = [black, white];
      }
    }

    for (i = 0; i < totalChunks; i++) {
      thisChunkHeight = i < fullChunks ? FULL_CHUNK_HEIGHT : partialChunkHeight;
      destPos = 0;

      for (j = 0; j < thisChunkHeight; j++) {
        const srcDiff = srcLength - srcPos;
        let k = 0;
        const kEnd = srcDiff > fullSrcDiff ? width : srcDiff * 8 - 7;
        const kEndUnrolled = kEnd & ~7;
        let mask = 0;
        let srcByte = 0;

        for (; k < kEndUnrolled; k += 8) {
          srcByte = src[srcPos++];
          dest32[destPos++] = srcByte & 128 ? white : black;
          dest32[destPos++] = srcByte & 64 ? white : black;
          dest32[destPos++] = srcByte & 32 ? white : black;
          dest32[destPos++] = srcByte & 16 ? white : black;
          dest32[destPos++] = srcByte & 8 ? white : black;
          dest32[destPos++] = srcByte & 4 ? white : black;
          dest32[destPos++] = srcByte & 2 ? white : black;
          dest32[destPos++] = srcByte & 1 ? white : black;
        }

        for (; k < kEnd; k++) {
          if (mask === 0) {
            srcByte = src[srcPos++];
            mask = 128;
          }

          dest32[destPos++] = srcByte & mask ? white : black;
          mask >>= 1;
        }
      }

      while (destPos < dest32DataLength) {
        dest32[destPos++] = 0;
      }

      ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
    }
  } else if (imgData.kind === _util.ImageKind.RGBA_32BPP) {
    const hasTransferMaps = !!(transferMapRed || transferMapGreen || transferMapBlue);
    j = 0;
    elemsInThisChunk = width * FULL_CHUNK_HEIGHT * 4;

    for (i = 0; i < fullChunks; i++) {
      dest.set(src.subarray(srcPos, srcPos + elemsInThisChunk));
      srcPos += elemsInThisChunk;

      if (hasTransferMaps) {
        for (let k = 0; k < elemsInThisChunk; k += 4) {
          if (transferMapRed) {
            dest[k + 0] = transferMapRed[dest[k + 0]];
          }

          if (transferMapGreen) {
            dest[k + 1] = transferMapGreen[dest[k + 1]];
          }

          if (transferMapBlue) {
            dest[k + 2] = transferMapBlue[dest[k + 2]];
          }
        }
      }

      ctx.putImageData(chunkImgData, 0, j);
      j += FULL_CHUNK_HEIGHT;
    }

    if (i < totalChunks) {
      elemsInThisChunk = width * partialChunkHeight * 4;
      dest.set(src.subarray(srcPos, srcPos + elemsInThisChunk));

      if (hasTransferMaps) {
        for (let k = 0; k < elemsInThisChunk; k += 4) {
          if (transferMapRed) {
            dest[k + 0] = transferMapRed[dest[k + 0]];
          }

          if (transferMapGreen) {
            dest[k + 1] = transferMapGreen[dest[k + 1]];
          }

          if (transferMapBlue) {
            dest[k + 2] = transferMapBlue[dest[k + 2]];
          }
        }
      }

      ctx.putImageData(chunkImgData, 0, j);
    }
  } else if (imgData.kind === _util.ImageKind.RGB_24BPP) {
    const hasTransferMaps = !!(transferMapRed || transferMapGreen || transferMapBlue);
    thisChunkHeight = FULL_CHUNK_HEIGHT;
    elemsInThisChunk = width * thisChunkHeight;

    for (i = 0; i < totalChunks; i++) {
      if (i >= fullChunks) {
        thisChunkHeight = partialChunkHeight;
        elemsInThisChunk = width * thisChunkHeight;
      }

      destPos = 0;

      for (j = elemsInThisChunk; j--;) {
        dest[destPos++] = src[srcPos++];
        dest[destPos++] = src[srcPos++];
        dest[destPos++] = src[srcPos++];
        dest[destPos++] = 255;
      }

      if (hasTransferMaps) {
        for (let k = 0; k < destPos; k += 4) {
          if (transferMapRed) {
            dest[k + 0] = transferMapRed[dest[k + 0]];
          }

          if (transferMapGreen) {
            dest[k + 1] = transferMapGreen[dest[k + 1]];
          }

          if (transferMapBlue) {
            dest[k + 2] = transferMapBlue[dest[k + 2]];
          }
        }
      }

      ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
    }
  } else {
    throw new Error(`bad image kind: ${imgData.kind}`);
  }
}

function putBinaryImageMask(ctx, imgData) {
  if (imgData.bitmap) {
    ctx.drawImage(imgData.bitmap, 0, 0);
    return;
  }

  const height = imgData.height,
        width = imgData.width;
  const partialChunkHeight = height % FULL_CHUNK_HEIGHT;
  const fullChunks = (height - partialChunkHeight) / FULL_CHUNK_HEIGHT;
  const totalChunks = partialChunkHeight === 0 ? fullChunks : fullChunks + 1;
  const chunkImgData = ctx.createImageData(width, FULL_CHUNK_HEIGHT);
  let srcPos = 0;
  const src = imgData.data;
  const dest = chunkImgData.data;

  for (let i = 0; i < totalChunks; i++) {
    const thisChunkHeight = i < fullChunks ? FULL_CHUNK_HEIGHT : partialChunkHeight;
    ({
      srcPos
    } = (0, _image_utils.applyMaskImageData)({
      src,
      srcPos,
      dest,
      width,
      height: thisChunkHeight
    }));
    ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
  }
}

function copyCtxState(sourceCtx, destCtx) {
  const properties = ["strokeStyle", "fillStyle", "fillRule", "globalAlpha", "lineWidth", "lineCap", "lineJoin", "miterLimit", "globalCompositeOperation", "font"];

  for (let i = 0, ii = properties.length; i < ii; i++) {
    const property = properties[i];

    if (sourceCtx[property] !== undefined) {
      destCtx[property] = sourceCtx[property];
    }
  }

  if (sourceCtx.setLineDash !== undefined) {
    destCtx.setLineDash(sourceCtx.getLineDash());
    destCtx.lineDashOffset = sourceCtx.lineDashOffset;
  }
}

function resetCtxToDefault(ctx, foregroundColor) {
  ctx.strokeStyle = ctx.fillStyle = foregroundColor || "#000000";
  ctx.fillRule = "nonzero";
  ctx.globalAlpha = 1;
  ctx.lineWidth = 1;
  ctx.lineCap = "butt";
  ctx.lineJoin = "miter";
  ctx.miterLimit = 10;
  ctx.globalCompositeOperation = "source-over";
  ctx.font = "10px sans-serif";

  if (ctx.setLineDash !== undefined) {
    ctx.setLineDash([]);
    ctx.lineDashOffset = 0;
  }
}

function composeSMaskBackdrop(bytes, r0, g0, b0) {
  const length = bytes.length;

  for (let i = 3; i < length; i += 4) {
    const alpha = bytes[i];

    if (alpha === 0) {
      bytes[i - 3] = r0;
      bytes[i - 2] = g0;
      bytes[i - 1] = b0;
    } else if (alpha < 255) {
      const alpha_ = 255 - alpha;
      bytes[i - 3] = bytes[i - 3] * alpha + r0 * alpha_ >> 8;
      bytes[i - 2] = bytes[i - 2] * alpha + g0 * alpha_ >> 8;
      bytes[i - 1] = bytes[i - 1] * alpha + b0 * alpha_ >> 8;
    }
  }
}

function composeSMaskAlpha(maskData, layerData, transferMap) {
  const length = maskData.length;
  const scale = 1 / 255;

  for (let i = 3; i < length; i += 4) {
    const alpha = transferMap ? transferMap[maskData[i]] : maskData[i];
    layerData[i] = layerData[i] * alpha * scale | 0;
  }
}

function composeSMaskLuminosity(maskData, layerData, transferMap) {
  const length = maskData.length;

  for (let i = 3; i < length; i += 4) {
    const y = maskData[i - 3] * 77 + maskData[i - 2] * 152 + maskData[i - 1] * 28;
    layerData[i] = transferMap ? layerData[i] * transferMap[y >> 8] >> 8 : layerData[i] * y >> 16;
  }
}

function genericComposeSMask(maskCtx, layerCtx, width, height, subtype, backdrop, transferMap, layerOffsetX, layerOffsetY, maskOffsetX, maskOffsetY) {
  const hasBackdrop = !!backdrop;
  const r0 = hasBackdrop ? backdrop[0] : 0;
  const g0 = hasBackdrop ? backdrop[1] : 0;
  const b0 = hasBackdrop ? backdrop[2] : 0;
  let composeFn;

  if (subtype === "Luminosity") {
    composeFn = composeSMaskLuminosity;
  } else {
    composeFn = composeSMaskAlpha;
  }

  const PIXELS_TO_PROCESS = 1048576;
  const chunkSize = Math.min(height, Math.ceil(PIXELS_TO_PROCESS / width));

  for (let row = 0; row < height; row += chunkSize) {
    const chunkHeight = Math.min(chunkSize, height - row);
    const maskData = maskCtx.getImageData(layerOffsetX - maskOffsetX, row + (layerOffsetY - maskOffsetY), width, chunkHeight);
    const layerData = layerCtx.getImageData(layerOffsetX, row + layerOffsetY, width, chunkHeight);

    if (hasBackdrop) {
      composeSMaskBackdrop(maskData.data, r0, g0, b0);
    }

    composeFn(maskData.data, layerData.data, transferMap);
    layerCtx.putImageData(layerData, layerOffsetX, row + layerOffsetY);
  }
}

function composeSMask(ctx, smask, layerCtx, layerBox) {
  const layerOffsetX = layerBox[0];
  const layerOffsetY = layerBox[1];
  const layerWidth = layerBox[2] - layerOffsetX;
  const layerHeight = layerBox[3] - layerOffsetY;

  if (layerWidth === 0 || layerHeight === 0) {
    return;
  }

  genericComposeSMask(smask.context, layerCtx, layerWidth, layerHeight, smask.subtype, smask.backdrop, smask.transferMap, layerOffsetX, layerOffsetY, smask.offsetX, smask.offsetY);
  ctx.save();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(layerCtx.canvas, 0, 0);
  ctx.restore();
}

function getImageSmoothingEnabled(transform, interpolate) {
  const scale = _util.Util.singularValueDecompose2dScale(transform);

  scale[0] = Math.fround(scale[0]);
  scale[1] = Math.fround(scale[1]);
  const actualScale = Math.fround((globalThis.devicePixelRatio || 1) * _display_utils.PixelsPerInch.PDF_TO_CSS_UNITS);

  if (interpolate !== undefined) {
    return interpolate;
  } else if (scale[0] <= actualScale || scale[1] <= actualScale) {
    return true;
  }

  return false;
}

const LINE_CAP_STYLES = ["butt", "round", "square"];
const LINE_JOIN_STYLES = ["miter", "round", "bevel"];
const NORMAL_CLIP = {};
const EO_CLIP = {};

var _restoreInitialState = /*#__PURE__*/new WeakSet();

class CanvasGraphics {
  constructor(canvasCtx, commonObjs, objs, canvasFactory, imageLayer, optionalContentConfig, annotationCanvasMap, pageColors) {
    _classPrivateMethodInitSpec(this, _restoreInitialState);

    this.ctx = canvasCtx;
    this.current = new CanvasExtraState(this.ctx.canvas.width, this.ctx.canvas.height);
    this.stateStack = [];
    this.pendingClip = null;
    this.pendingEOFill = false;
    this.res = null;
    this.xobjs = null;
    this.commonObjs = commonObjs;
    this.objs = objs;
    this.canvasFactory = canvasFactory;
    this.imageLayer = imageLayer;
    this.groupStack = [];
    this.processingType3 = null;
    this.baseTransform = null;
    this.baseTransformStack = [];
    this.groupLevel = 0;
    this.smaskStack = [];
    this.smaskCounter = 0;
    this.tempSMask = null;
    this.suspendedCtx = null;
    this.contentVisible = true;
    this.markedContentStack = [];
    this.optionalContentConfig = optionalContentConfig;
    this.cachedCanvases = new CachedCanvases(this.canvasFactory);
    this.cachedPatterns = new Map();
    this.annotationCanvasMap = annotationCanvasMap;
    this.viewportScale = 1;
    this.outputScaleX = 1;
    this.outputScaleY = 1;
    this.backgroundColor = (pageColors === null || pageColors === void 0 ? void 0 : pageColors.background) || null;
    this.foregroundColor = (pageColors === null || pageColors === void 0 ? void 0 : pageColors.foreground) || null;
    this._cachedScaleForStroking = null;
    this._cachedGetSinglePixelWidth = null;
    this._cachedBitmapsMap = new Map();
  }

  getObject(data) {
    let fallback = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

    if (typeof data === "string") {
      return data.startsWith("g_") ? this.commonObjs.get(data) : this.objs.get(data);
    }

    return fallback;
  }

  beginDrawing(_ref) {
    let {
      transform,
      viewport,
      transparency = false,
      background = null
    } = _ref;
    const width = this.ctx.canvas.width;
    const height = this.ctx.canvas.height;
    const defaultBackgroundColor = background || "#ffffff";
    this.ctx.save();

    if (this.foregroundColor && this.backgroundColor) {
      this.ctx.fillStyle = this.foregroundColor;
      const fg = this.foregroundColor = this.ctx.fillStyle;
      this.ctx.fillStyle = this.backgroundColor;
      const bg = this.backgroundColor = this.ctx.fillStyle;
      let isValidDefaultBg = true;
      let defaultBg = defaultBackgroundColor;
      this.ctx.fillStyle = defaultBackgroundColor;
      defaultBg = this.ctx.fillStyle;
      isValidDefaultBg = typeof defaultBg === "string" && /^#[0-9A-Fa-f]{6}$/.test(defaultBg);

      if (fg === "#000000" && bg === "#ffffff" || fg === bg || !isValidDefaultBg) {
        this.foregroundColor = this.backgroundColor = null;
      } else {
        const [rB, gB, bB] = (0, _display_utils.getRGB)(defaultBg);

        const newComp = x => {
          x /= 255;
          return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
        };

        const lumB = Math.round(0.2126 * newComp(rB) + 0.7152 * newComp(gB) + 0.0722 * newComp(bB));

        this.selectColor = (r, g, b) => {
          const lumC = 0.2126 * newComp(r) + 0.7152 * newComp(g) + 0.0722 * newComp(b);
          return Math.round(lumC) === lumB ? bg : fg;
        };
      }
    }

    this.ctx.fillStyle = this.backgroundColor || defaultBackgroundColor;
    this.ctx.fillRect(0, 0, width, height);
    this.ctx.restore();

    if (transparency) {
      const transparentCanvas = this.cachedCanvases.getCanvas("transparent", width, height);
      this.compositeCtx = this.ctx;
      this.transparentCanvas = transparentCanvas.canvas;
      this.ctx = transparentCanvas.context;
      this.ctx.save();
      this.ctx.transform(...(0, _display_utils.getCurrentTransform)(this.compositeCtx));
    }

    this.ctx.save();
    resetCtxToDefault(this.ctx, this.foregroundColor);

    if (transform) {
      this.ctx.transform(...transform);
      this.outputScaleX = transform[0];
      this.outputScaleY = transform[0];
    }

    this.ctx.transform(...viewport.transform);
    this.viewportScale = viewport.scale;
    this.baseTransform = (0, _display_utils.getCurrentTransform)(this.ctx);

    if (this.imageLayer) {
      (0, _display_utils.deprecated)("The `imageLayer` functionality will be removed in the future.");
      this.imageLayer.beginLayout();
    }
  }

  executeOperatorList(operatorList, executionStartIdx, continueCallback, stepper) {
    const argsArray = operatorList.argsArray;
    const fnArray = operatorList.fnArray;
    let i = executionStartIdx || 0;
    const argsArrayLen = argsArray.length;

    if (argsArrayLen === i) {
      return i;
    }

    const chunkOperations = argsArrayLen - i > EXECUTION_STEPS && typeof continueCallback === "function";
    const endTime = chunkOperations ? Date.now() + EXECUTION_TIME : 0;
    let steps = 0;
    const commonObjs = this.commonObjs;
    const objs = this.objs;
    let fnId;

    while (true) {
      if (stepper !== undefined && i === stepper.nextBreakPoint) {
        stepper.breakIt(i, continueCallback);
        return i;
      }

      fnId = fnArray[i];

      if (fnId !== _util.OPS.dependency) {
        this[fnId].apply(this, argsArray[i]);
      } else {
        for (const depObjId of argsArray[i]) {
          const objsPool = depObjId.startsWith("g_") ? commonObjs : objs;

          if (!objsPool.has(depObjId)) {
            objsPool.get(depObjId, continueCallback);
            return i;
          }
        }
      }

      i++;

      if (i === argsArrayLen) {
        return i;
      }

      if (chunkOperations && ++steps > EXECUTION_STEPS) {
        if (Date.now() > endTime) {
          continueCallback();
          return i;
        }

        steps = 0;
      }
    }
  }

  endDrawing() {
    _classPrivateMethodGet(this, _restoreInitialState, _restoreInitialState2).call(this);

    this.cachedCanvases.clear();
    this.cachedPatterns.clear();

    for (const cache of this._cachedBitmapsMap.values()) {
      for (const canvas of cache.values()) {
        if (typeof HTMLCanvasElement !== "undefined" && canvas instanceof HTMLCanvasElement) {
          canvas.width = canvas.height = 0;
        }
      }

      cache.clear();
    }

    this._cachedBitmapsMap.clear();

    if (this.imageLayer) {
      this.imageLayer.endLayout();
    }
  }

  _scaleImage(img, inverseTransform) {
    const width = img.width;
    const height = img.height;
    let widthScale = Math.max(Math.hypot(inverseTransform[0], inverseTransform[1]), 1);
    let heightScale = Math.max(Math.hypot(inverseTransform[2], inverseTransform[3]), 1);
    let paintWidth = width,
        paintHeight = height;
    let tmpCanvasId = "prescale1";
    let tmpCanvas, tmpCtx;

    while (widthScale > 2 && paintWidth > 1 || heightScale > 2 && paintHeight > 1) {
      let newWidth = paintWidth,
          newHeight = paintHeight;

      if (widthScale > 2 && paintWidth > 1) {
        newWidth = Math.ceil(paintWidth / 2);
        widthScale /= paintWidth / newWidth;
      }

      if (heightScale > 2 && paintHeight > 1) {
        newHeight = Math.ceil(paintHeight / 2);
        heightScale /= paintHeight / newHeight;
      }

      tmpCanvas = this.cachedCanvases.getCanvas(tmpCanvasId, newWidth, newHeight);
      tmpCtx = tmpCanvas.context;
      tmpCtx.clearRect(0, 0, newWidth, newHeight);
      tmpCtx.drawImage(img, 0, 0, paintWidth, paintHeight, 0, 0, newWidth, newHeight);
      img = tmpCanvas.canvas;
      paintWidth = newWidth;
      paintHeight = newHeight;
      tmpCanvasId = tmpCanvasId === "prescale1" ? "prescale2" : "prescale1";
    }

    return {
      img,
      paintWidth,
      paintHeight
    };
  }

  _createMaskCanvas(img) {
    const ctx = this.ctx;
    const {
      width,
      height
    } = img;
    const fillColor = this.current.fillColor;
    const isPatternFill = this.current.patternFill;
    const currentTransform = (0, _display_utils.getCurrentTransform)(ctx);
    let cache, cacheKey, scaled, maskCanvas;

    if ((img.bitmap || img.data) && img.count > 1) {
      const mainKey = img.bitmap || img.data.buffer;
      const withoutTranslation = currentTransform.slice(0, 4);
      cacheKey = JSON.stringify(isPatternFill ? withoutTranslation : [withoutTranslation, fillColor]);
      cache = this._cachedBitmapsMap.get(mainKey);

      if (!cache) {
        cache = new Map();

        this._cachedBitmapsMap.set(mainKey, cache);
      }

      const cachedImage = cache.get(cacheKey);

      if (cachedImage && !isPatternFill) {
        const offsetX = Math.round(Math.min(currentTransform[0], currentTransform[2]) + currentTransform[4]);
        const offsetY = Math.round(Math.min(currentTransform[1], currentTransform[3]) + currentTransform[5]);
        return {
          canvas: cachedImage,
          offsetX,
          offsetY
        };
      }

      scaled = cachedImage;
    }

    if (!scaled) {
      maskCanvas = this.cachedCanvases.getCanvas("maskCanvas", width, height);
      putBinaryImageMask(maskCanvas.context, img);
    }

    let maskToCanvas = _util.Util.transform(currentTransform, [1 / width, 0, 0, -1 / height, 0, 0]);

    maskToCanvas = _util.Util.transform(maskToCanvas, [1, 0, 0, 1, 0, -height]);

    const cord1 = _util.Util.applyTransform([0, 0], maskToCanvas);

    const cord2 = _util.Util.applyTransform([width, height], maskToCanvas);

    const rect = _util.Util.normalizeRect([cord1[0], cord1[1], cord2[0], cord2[1]]);

    const drawnWidth = Math.round(rect[2] - rect[0]) || 1;
    const drawnHeight = Math.round(rect[3] - rect[1]) || 1;
    const fillCanvas = this.cachedCanvases.getCanvas("fillCanvas", drawnWidth, drawnHeight);
    const fillCtx = fillCanvas.context;
    const offsetX = Math.min(cord1[0], cord2[0]);
    const offsetY = Math.min(cord1[1], cord2[1]);
    fillCtx.translate(-offsetX, -offsetY);
    fillCtx.transform(...maskToCanvas);

    if (!scaled) {
      scaled = this._scaleImage(maskCanvas.canvas, (0, _display_utils.getCurrentTransformInverse)(fillCtx));
      scaled = scaled.img;

      if (cache && isPatternFill) {
        cache.set(cacheKey, scaled);
      }
    }

    fillCtx.imageSmoothingEnabled = getImageSmoothingEnabled((0, _display_utils.getCurrentTransform)(fillCtx), img.interpolate);
    drawImageAtIntegerCoords(fillCtx, scaled, 0, 0, scaled.width, scaled.height, 0, 0, width, height);
    fillCtx.globalCompositeOperation = "source-in";

    const inverse = _util.Util.transform((0, _display_utils.getCurrentTransformInverse)(fillCtx), [1, 0, 0, 1, -offsetX, -offsetY]);

    fillCtx.fillStyle = isPatternFill ? fillColor.getPattern(ctx, this, inverse, _pattern_helper.PathType.FILL) : fillColor;
    fillCtx.fillRect(0, 0, width, height);

    if (cache && !isPatternFill) {
      this.cachedCanvases.delete("fillCanvas");
      cache.set(cacheKey, fillCanvas.canvas);
    }

    return {
      canvas: fillCanvas.canvas,
      offsetX: Math.round(offsetX),
      offsetY: Math.round(offsetY)
    };
  }

  setLineWidth(width) {
    if (width !== this.current.lineWidth) {
      this._cachedScaleForStroking = null;
    }

    this.current.lineWidth = width;
    this.ctx.lineWidth = width;
  }

  setLineCap(style) {
    this.ctx.lineCap = LINE_CAP_STYLES[style];
  }

  setLineJoin(style) {
    this.ctx.lineJoin = LINE_JOIN_STYLES[style];
  }

  setMiterLimit(limit) {
    this.ctx.miterLimit = limit;
  }

  setDash(dashArray, dashPhase) {
    const ctx = this.ctx;

    if (ctx.setLineDash !== undefined) {
      ctx.setLineDash(dashArray);
      ctx.lineDashOffset = dashPhase;
    }
  }

  setRenderingIntent(intent) {}

  setFlatness(flatness) {}

  setGState(states) {
    for (let i = 0, ii = states.length; i < ii; i++) {
      const state = states[i];
      const key = state[0];
      const value = state[1];

      switch (key) {
        case "LW":
          this.setLineWidth(value);
          break;

        case "LC":
          this.setLineCap(value);
          break;

        case "LJ":
          this.setLineJoin(value);
          break;

        case "ML":
          this.setMiterLimit(value);
          break;

        case "D":
          this.setDash(value[0], value[1]);
          break;

        case "RI":
          this.setRenderingIntent(value);
          break;

        case "FL":
          this.setFlatness(value);
          break;

        case "Font":
          this.setFont(value[0], value[1]);
          break;

        case "CA":
          this.current.strokeAlpha = state[1];
          break;

        case "ca":
          this.current.fillAlpha = state[1];
          this.ctx.globalAlpha = state[1];
          break;

        case "BM":
          this.ctx.globalCompositeOperation = value;
          break;

        case "SMask":
          this.current.activeSMask = value ? this.tempSMask : null;
          this.tempSMask = null;
          this.checkSMaskState();
          break;

        case "TR":
          this.current.transferMaps = value;
      }
    }
  }

  get inSMaskMode() {
    return !!this.suspendedCtx;
  }

  checkSMaskState() {
    const inSMaskMode = this.inSMaskMode;

    if (this.current.activeSMask && !inSMaskMode) {
      this.beginSMaskMode();
    } else if (!this.current.activeSMask && inSMaskMode) {
      this.endSMaskMode();
    }
  }

  beginSMaskMode() {
    if (this.inSMaskMode) {
      throw new Error("beginSMaskMode called while already in smask mode");
    }

    const drawnWidth = this.ctx.canvas.width;
    const drawnHeight = this.ctx.canvas.height;
    const cacheId = "smaskGroupAt" + this.groupLevel;
    const scratchCanvas = this.cachedCanvases.getCanvas(cacheId, drawnWidth, drawnHeight);
    this.suspendedCtx = this.ctx;
    this.ctx = scratchCanvas.context;
    const ctx = this.ctx;
    ctx.setTransform(...(0, _display_utils.getCurrentTransform)(this.suspendedCtx));
    copyCtxState(this.suspendedCtx, ctx);
    mirrorContextOperations(ctx, this.suspendedCtx);
    this.setGState([["BM", "source-over"], ["ca", 1], ["CA", 1]]);
  }

  endSMaskMode() {
    if (!this.inSMaskMode) {
      throw new Error("endSMaskMode called while not in smask mode");
    }

    this.ctx._removeMirroring();

    copyCtxState(this.ctx, this.suspendedCtx);
    this.ctx = this.suspendedCtx;
    this.suspendedCtx = null;
  }

  compose(dirtyBox) {
    if (!this.current.activeSMask) {
      return;
    }

    if (!dirtyBox) {
      dirtyBox = [0, 0, this.ctx.canvas.width, this.ctx.canvas.height];
    } else {
      dirtyBox[0] = Math.floor(dirtyBox[0]);
      dirtyBox[1] = Math.floor(dirtyBox[1]);
      dirtyBox[2] = Math.ceil(dirtyBox[2]);
      dirtyBox[3] = Math.ceil(dirtyBox[3]);
    }

    const smask = this.current.activeSMask;
    const suspendedCtx = this.suspendedCtx;
    composeSMask(suspendedCtx, smask, this.ctx, dirtyBox);
    this.ctx.save();
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
    this.ctx.restore();
  }

  save() {
    if (this.inSMaskMode) {
      copyCtxState(this.ctx, this.suspendedCtx);
      this.suspendedCtx.save();
    } else {
      this.ctx.save();
    }

    const old = this.current;
    this.stateStack.push(old);
    this.current = old.clone();
  }

  restore() {
    if (this.stateStack.length === 0 && this.inSMaskMode) {
      this.endSMaskMode();
    }

    if (this.stateStack.length !== 0) {
      this.current = this.stateStack.pop();

      if (this.inSMaskMode) {
        this.suspendedCtx.restore();
        copyCtxState(this.suspendedCtx, this.ctx);
      } else {
        this.ctx.restore();
      }

      this.checkSMaskState();
      this.pendingClip = null;
      this._cachedScaleForStroking = null;
      this._cachedGetSinglePixelWidth = null;
    }
  }

  transform(a, b, c, d, e, f) {
    this.ctx.transform(a, b, c, d, e, f);
    this._cachedScaleForStroking = null;
    this._cachedGetSinglePixelWidth = null;
  }

  constructPath(ops, args, minMax) {
    const ctx = this.ctx;
    const current = this.current;
    let x = current.x,
        y = current.y;
    let startX, startY;
    const currentTransform = (0, _display_utils.getCurrentTransform)(ctx);
    const isScalingMatrix = currentTransform[0] === 0 && currentTransform[3] === 0 || currentTransform[1] === 0 && currentTransform[2] === 0;
    const minMaxForBezier = isScalingMatrix ? minMax.slice(0) : null;

    for (let i = 0, j = 0, ii = ops.length; i < ii; i++) {
      switch (ops[i] | 0) {
        case _util.OPS.rectangle:
          x = args[j++];
          y = args[j++];
          const width = args[j++];
          const height = args[j++];
          const xw = x + width;
          const yh = y + height;
          ctx.moveTo(x, y);

          if (width === 0 || height === 0) {
            ctx.lineTo(xw, yh);
          } else {
            ctx.lineTo(xw, y);
            ctx.lineTo(xw, yh);
            ctx.lineTo(x, yh);
          }

          if (!isScalingMatrix) {
            current.updateRectMinMax(currentTransform, [x, y, xw, yh]);
          }

          ctx.closePath();
          break;

        case _util.OPS.moveTo:
          x = args[j++];
          y = args[j++];
          ctx.moveTo(x, y);

          if (!isScalingMatrix) {
            current.updatePathMinMax(currentTransform, x, y);
          }

          break;

        case _util.OPS.lineTo:
          x = args[j++];
          y = args[j++];
          ctx.lineTo(x, y);

          if (!isScalingMatrix) {
            current.updatePathMinMax(currentTransform, x, y);
          }

          break;

        case _util.OPS.curveTo:
          startX = x;
          startY = y;
          x = args[j + 4];
          y = args[j + 5];
          ctx.bezierCurveTo(args[j], args[j + 1], args[j + 2], args[j + 3], x, y);
          current.updateCurvePathMinMax(currentTransform, startX, startY, args[j], args[j + 1], args[j + 2], args[j + 3], x, y, minMaxForBezier);
          j += 6;
          break;

        case _util.OPS.curveTo2:
          startX = x;
          startY = y;
          ctx.bezierCurveTo(x, y, args[j], args[j + 1], args[j + 2], args[j + 3]);
          current.updateCurvePathMinMax(currentTransform, startX, startY, x, y, args[j], args[j + 1], args[j + 2], args[j + 3], minMaxForBezier);
          x = args[j + 2];
          y = args[j + 3];
          j += 4;
          break;

        case _util.OPS.curveTo3:
          startX = x;
          startY = y;
          x = args[j + 2];
          y = args[j + 3];
          ctx.bezierCurveTo(args[j], args[j + 1], x, y, x, y);
          current.updateCurvePathMinMax(currentTransform, startX, startY, args[j], args[j + 1], x, y, x, y, minMaxForBezier);
          j += 4;
          break;

        case _util.OPS.closePath:
          ctx.closePath();
          break;
      }
    }

    if (isScalingMatrix) {
      current.updateScalingPathMinMax(currentTransform, minMaxForBezier);
    }

    current.setCurrentPoint(x, y);
  }

  closePath() {
    this.ctx.closePath();
  }

  stroke(consumePath) {
    consumePath = typeof consumePath !== "undefined" ? consumePath : true;
    const ctx = this.ctx;
    const strokeColor = this.current.strokeColor;
    ctx.globalAlpha = this.current.strokeAlpha;

    if (this.contentVisible) {
      if (typeof strokeColor === "object" && strokeColor !== null && strokeColor !== void 0 && strokeColor.getPattern) {
        ctx.save();
        ctx.strokeStyle = strokeColor.getPattern(ctx, this, (0, _display_utils.getCurrentTransformInverse)(ctx), _pattern_helper.PathType.STROKE);
        this.rescaleAndStroke(false);
        ctx.restore();
      } else {
        this.rescaleAndStroke(true);
      }
    }

    if (consumePath) {
      this.consumePath(this.current.getClippedPathBoundingBox());
    }

    ctx.globalAlpha = this.current.fillAlpha;
  }

  closeStroke() {
    this.closePath();
    this.stroke();
  }

  fill(consumePath) {
    consumePath = typeof consumePath !== "undefined" ? consumePath : true;
    const ctx = this.ctx;
    const fillColor = this.current.fillColor;
    const isPatternFill = this.current.patternFill;
    let needRestore = false;

    if (isPatternFill) {
      ctx.save();
      ctx.fillStyle = fillColor.getPattern(ctx, this, (0, _display_utils.getCurrentTransformInverse)(ctx), _pattern_helper.PathType.FILL);
      needRestore = true;
    }

    const intersect = this.current.getClippedPathBoundingBox();

    if (this.contentVisible && intersect !== null) {
      if (this.pendingEOFill) {
        ctx.fill("evenodd");
        this.pendingEOFill = false;
      } else {
        ctx.fill();
      }
    }

    if (needRestore) {
      ctx.restore();
    }

    if (consumePath) {
      this.consumePath(intersect);
    }
  }

  eoFill() {
    this.pendingEOFill = true;
    this.fill();
  }

  fillStroke() {
    this.fill(false);
    this.stroke(false);
    this.consumePath();
  }

  eoFillStroke() {
    this.pendingEOFill = true;
    this.fillStroke();
  }

  closeFillStroke() {
    this.closePath();
    this.fillStroke();
  }

  closeEOFillStroke() {
    this.pendingEOFill = true;
    this.closePath();
    this.fillStroke();
  }

  endPath() {
    this.consumePath();
  }

  clip() {
    this.pendingClip = NORMAL_CLIP;
  }

  eoClip() {
    this.pendingClip = EO_CLIP;
  }

  beginText() {
    this.current.textMatrix = _util.IDENTITY_MATRIX;
    this.current.textMatrixScale = 1;
    this.current.x = this.current.lineX = 0;
    this.current.y = this.current.lineY = 0;
  }

  endText() {
    const paths = this.pendingTextPaths;
    const ctx = this.ctx;

    if (paths === undefined) {
      ctx.beginPath();
      return;
    }

    ctx.save();
    ctx.beginPath();

    for (const path of paths) {
      ctx.setTransform(...path.transform);
      ctx.translate(path.x, path.y);
      path.addToPath(ctx, path.fontSize);
    }

    ctx.restore();
    ctx.clip();
    ctx.beginPath();
    delete this.pendingTextPaths;
  }

  setCharSpacing(spacing) {
    this.current.charSpacing = spacing;
  }

  setWordSpacing(spacing) {
    this.current.wordSpacing = spacing;
  }

  setHScale(scale) {
    this.current.textHScale = scale / 100;
  }

  setLeading(leading) {
    this.current.leading = -leading;
  }

  setFont(fontRefName, size) {
    const fontObj = this.commonObjs.get(fontRefName);
    const current = this.current;

    if (!fontObj) {
      throw new Error(`Can't find font for ${fontRefName}`);
    }

    current.fontMatrix = fontObj.fontMatrix || _util.FONT_IDENTITY_MATRIX;

    if (current.fontMatrix[0] === 0 || current.fontMatrix[3] === 0) {
      (0, _util.warn)("Invalid font matrix for font " + fontRefName);
    }

    if (size < 0) {
      size = -size;
      current.fontDirection = -1;
    } else {
      current.fontDirection = 1;
    }

    this.current.font = fontObj;
    this.current.fontSize = size;

    if (fontObj.isType3Font) {
      return;
    }

    const name = fontObj.loadedName || "sans-serif";
    let bold = "normal";

    if (fontObj.black) {
      bold = "900";
    } else if (fontObj.bold) {
      bold = "bold";
    }

    const italic = fontObj.italic ? "italic" : "normal";
    const typeface = `"${name}", ${fontObj.fallbackName}`;
    let browserFontSize = size;

    if (size < MIN_FONT_SIZE) {
      browserFontSize = MIN_FONT_SIZE;
    } else if (size > MAX_FONT_SIZE) {
      browserFontSize = MAX_FONT_SIZE;
    }

    this.current.fontSizeScale = size / browserFontSize;
    this.ctx.font = `${italic} ${bold} ${browserFontSize}px ${typeface}`;
  }

  setTextRenderingMode(mode) {
    this.current.textRenderingMode = mode;
  }

  setTextRise(rise) {
    this.current.textRise = rise;
  }

  moveText(x, y) {
    this.current.x = this.current.lineX += x;
    this.current.y = this.current.lineY += y;
  }

  setLeadingMoveText(x, y) {
    this.setLeading(-y);
    this.moveText(x, y);
  }

  setTextMatrix(a, b, c, d, e, f) {
    this.current.textMatrix = [a, b, c, d, e, f];
    this.current.textMatrixScale = Math.hypot(a, b);
    this.current.x = this.current.lineX = 0;
    this.current.y = this.current.lineY = 0;
  }

  nextLine() {
    this.moveText(0, this.current.leading);
  }

  paintChar(character, x, y, patternTransform) {
    const ctx = this.ctx;
    const current = this.current;
    const font = current.font;
    const textRenderingMode = current.textRenderingMode;
    const fontSize = current.fontSize / current.fontSizeScale;
    const fillStrokeMode = textRenderingMode & _util.TextRenderingMode.FILL_STROKE_MASK;
    const isAddToPathSet = !!(textRenderingMode & _util.TextRenderingMode.ADD_TO_PATH_FLAG);
    const patternFill = current.patternFill && !font.missingFile;
    let addToPath;

    if (font.disableFontFace || isAddToPathSet || patternFill) {
      addToPath = font.getPathGenerator(this.commonObjs, character);
    }

    if (font.disableFontFace || patternFill) {
      ctx.save();
      ctx.translate(x, y);
      ctx.beginPath();
      addToPath(ctx, fontSize);

      if (patternTransform) {
        ctx.setTransform(...patternTransform);
      }

      if (fillStrokeMode === _util.TextRenderingMode.FILL || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        ctx.fill();
      }

      if (fillStrokeMode === _util.TextRenderingMode.STROKE || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        ctx.stroke();
      }

      ctx.restore();
    } else {
      if (fillStrokeMode === _util.TextRenderingMode.FILL || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        ctx.fillText(character, x, y);
      }

      if (fillStrokeMode === _util.TextRenderingMode.STROKE || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        ctx.strokeText(character, x, y);
      }
    }

    if (isAddToPathSet) {
      const paths = this.pendingTextPaths || (this.pendingTextPaths = []);
      paths.push({
        transform: (0, _display_utils.getCurrentTransform)(ctx),
        x,
        y,
        fontSize,
        addToPath
      });
    }
  }

  get isFontSubpixelAAEnabled() {
    const {
      context: ctx
    } = this.cachedCanvases.getCanvas("isFontSubpixelAAEnabled", 10, 10);
    ctx.scale(1.5, 1);
    ctx.fillText("I", 0, 10);
    const data = ctx.getImageData(0, 0, 10, 10).data;
    let enabled = false;

    for (let i = 3; i < data.length; i += 4) {
      if (data[i] > 0 && data[i] < 255) {
        enabled = true;
        break;
      }
    }

    return (0, _util.shadow)(this, "isFontSubpixelAAEnabled", enabled);
  }

  showText(glyphs) {
    const current = this.current;
    const font = current.font;

    if (font.isType3Font) {
      return this.showType3Text(glyphs);
    }

    const fontSize = current.fontSize;

    if (fontSize === 0) {
      return undefined;
    }

    const ctx = this.ctx;
    const fontSizeScale = current.fontSizeScale;
    const charSpacing = current.charSpacing;
    const wordSpacing = current.wordSpacing;
    const fontDirection = current.fontDirection;
    const textHScale = current.textHScale * fontDirection;
    const glyphsLength = glyphs.length;
    const vertical = font.vertical;
    const spacingDir = vertical ? 1 : -1;
    const defaultVMetrics = font.defaultVMetrics;
    const widthAdvanceScale = fontSize * current.fontMatrix[0];
    const simpleFillText = current.textRenderingMode === _util.TextRenderingMode.FILL && !font.disableFontFace && !current.patternFill;
    ctx.save();
    ctx.transform(...current.textMatrix);
    ctx.translate(current.x, current.y + current.textRise);

    if (fontDirection > 0) {
      ctx.scale(textHScale, -1);
    } else {
      ctx.scale(textHScale, 1);
    }

    let patternTransform;

    if (current.patternFill) {
      ctx.save();
      const pattern = current.fillColor.getPattern(ctx, this, (0, _display_utils.getCurrentTransformInverse)(ctx), _pattern_helper.PathType.FILL);
      patternTransform = (0, _display_utils.getCurrentTransform)(ctx);
      ctx.restore();
      ctx.fillStyle = pattern;
    }

    let lineWidth = current.lineWidth;
    const scale = current.textMatrixScale;

    if (scale === 0 || lineWidth === 0) {
      const fillStrokeMode = current.textRenderingMode & _util.TextRenderingMode.FILL_STROKE_MASK;

      if (fillStrokeMode === _util.TextRenderingMode.STROKE || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        lineWidth = this.getSinglePixelWidth();
      }
    } else {
      lineWidth /= scale;
    }

    if (fontSizeScale !== 1.0) {
      ctx.scale(fontSizeScale, fontSizeScale);
      lineWidth /= fontSizeScale;
    }

    ctx.lineWidth = lineWidth;
    let x = 0,
        i;

    for (i = 0; i < glyphsLength; ++i) {
      const glyph = glyphs[i];

      if (typeof glyph === "number") {
        x += spacingDir * glyph * fontSize / 1000;
        continue;
      }

      let restoreNeeded = false;
      const spacing = (glyph.isSpace ? wordSpacing : 0) + charSpacing;
      const character = glyph.fontChar;
      const accent = glyph.accent;
      let scaledX, scaledY;
      let width = glyph.width;

      if (vertical) {
        const vmetric = glyph.vmetric || defaultVMetrics;
        const vx = -(glyph.vmetric ? vmetric[1] : width * 0.5) * widthAdvanceScale;
        const vy = vmetric[2] * widthAdvanceScale;
        width = vmetric ? -vmetric[0] : width;
        scaledX = vx / fontSizeScale;
        scaledY = (x + vy) / fontSizeScale;
      } else {
        scaledX = x / fontSizeScale;
        scaledY = 0;
      }

      if (font.remeasure && width > 0) {
        const measuredWidth = ctx.measureText(character).width * 1000 / fontSize * fontSizeScale;

        if (width < measuredWidth && this.isFontSubpixelAAEnabled) {
          const characterScaleX = width / measuredWidth;
          restoreNeeded = true;
          ctx.save();
          ctx.scale(characterScaleX, 1);
          scaledX /= characterScaleX;
        } else if (width !== measuredWidth) {
          scaledX += (width - measuredWidth) / 2000 * fontSize / fontSizeScale;
        }
      }

      if (this.contentVisible && (glyph.isInFont || font.missingFile)) {
        if (simpleFillText && !accent) {
          ctx.fillText(character, scaledX, scaledY);
        } else {
          this.paintChar(character, scaledX, scaledY, patternTransform);

          if (accent) {
            const scaledAccentX = scaledX + fontSize * accent.offset.x / fontSizeScale;
            const scaledAccentY = scaledY - fontSize * accent.offset.y / fontSizeScale;
            this.paintChar(accent.fontChar, scaledAccentX, scaledAccentY, patternTransform);
          }
        }
      }

      let charWidth;

      if (vertical) {
        charWidth = width * widthAdvanceScale - spacing * fontDirection;
      } else {
        charWidth = width * widthAdvanceScale + spacing * fontDirection;
      }

      x += charWidth;

      if (restoreNeeded) {
        ctx.restore();
      }
    }

    if (vertical) {
      current.y -= x;
    } else {
      current.x += x * textHScale;
    }

    ctx.restore();
    this.compose();
    return undefined;
  }

  showType3Text(glyphs) {
    const ctx = this.ctx;
    const current = this.current;
    const font = current.font;
    const fontSize = current.fontSize;
    const fontDirection = current.fontDirection;
    const spacingDir = font.vertical ? 1 : -1;
    const charSpacing = current.charSpacing;
    const wordSpacing = current.wordSpacing;
    const textHScale = current.textHScale * fontDirection;
    const fontMatrix = current.fontMatrix || _util.FONT_IDENTITY_MATRIX;
    const glyphsLength = glyphs.length;
    const isTextInvisible = current.textRenderingMode === _util.TextRenderingMode.INVISIBLE;
    let i, glyph, width, spacingLength;

    if (isTextInvisible || fontSize === 0) {
      return;
    }

    this._cachedScaleForStroking = null;
    this._cachedGetSinglePixelWidth = null;
    ctx.save();
    ctx.transform(...current.textMatrix);
    ctx.translate(current.x, current.y);
    ctx.scale(textHScale, fontDirection);

    for (i = 0; i < glyphsLength; ++i) {
      glyph = glyphs[i];

      if (typeof glyph === "number") {
        spacingLength = spacingDir * glyph * fontSize / 1000;
        this.ctx.translate(spacingLength, 0);
        current.x += spacingLength * textHScale;
        continue;
      }

      const spacing = (glyph.isSpace ? wordSpacing : 0) + charSpacing;
      const operatorList = font.charProcOperatorList[glyph.operatorListId];

      if (!operatorList) {
        (0, _util.warn)(`Type3 character "${glyph.operatorListId}" is not available.`);
        continue;
      }

      if (this.contentVisible) {
        this.processingType3 = glyph;
        this.save();
        ctx.scale(fontSize, fontSize);
        ctx.transform(...fontMatrix);
        this.executeOperatorList(operatorList);
        this.restore();
      }

      const transformed = _util.Util.applyTransform([glyph.width, 0], fontMatrix);

      width = transformed[0] * fontSize + spacing;
      ctx.translate(width, 0);
      current.x += width * textHScale;
    }

    ctx.restore();
    this.processingType3 = null;
  }

  setCharWidth(xWidth, yWidth) {}

  setCharWidthAndBounds(xWidth, yWidth, llx, lly, urx, ury) {
    this.ctx.rect(llx, lly, urx - llx, ury - lly);
    this.ctx.clip();
    this.endPath();
  }

  getColorN_Pattern(IR) {
    let pattern;

    if (IR[0] === "TilingPattern") {
      const color = IR[1];
      const baseTransform = this.baseTransform || (0, _display_utils.getCurrentTransform)(this.ctx);
      const canvasGraphicsFactory = {
        createCanvasGraphics: ctx => {
          return new CanvasGraphics(ctx, this.commonObjs, this.objs, this.canvasFactory);
        }
      };
      pattern = new _pattern_helper.TilingPattern(IR, color, this.ctx, canvasGraphicsFactory, baseTransform);
    } else {
      pattern = this._getPattern(IR[1], IR[2]);
    }

    return pattern;
  }

  setStrokeColorN() {
    this.current.strokeColor = this.getColorN_Pattern(arguments);
  }

  setFillColorN() {
    this.current.fillColor = this.getColorN_Pattern(arguments);
    this.current.patternFill = true;
  }

  setStrokeRGBColor(r, g, b) {
    var _this$selectColor;

    const color = ((_this$selectColor = this.selectColor) === null || _this$selectColor === void 0 ? void 0 : _this$selectColor.call(this, r, g, b)) || _util.Util.makeHexColor(r, g, b);

    this.ctx.strokeStyle = color;
    this.current.strokeColor = color;
  }

  setFillRGBColor(r, g, b) {
    var _this$selectColor2;

    const color = ((_this$selectColor2 = this.selectColor) === null || _this$selectColor2 === void 0 ? void 0 : _this$selectColor2.call(this, r, g, b)) || _util.Util.makeHexColor(r, g, b);

    this.ctx.fillStyle = color;
    this.current.fillColor = color;
    this.current.patternFill = false;
  }

  _getPattern(objId) {
    let matrix = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
    let pattern;

    if (this.cachedPatterns.has(objId)) {
      pattern = this.cachedPatterns.get(objId);
    } else {
      pattern = (0, _pattern_helper.getShadingPattern)(this.objs.get(objId));
      this.cachedPatterns.set(objId, pattern);
    }

    if (matrix) {
      pattern.matrix = matrix;
    }

    return pattern;
  }

  shadingFill(objId) {
    if (!this.contentVisible) {
      return;
    }

    const ctx = this.ctx;
    this.save();

    const pattern = this._getPattern(objId);

    ctx.fillStyle = pattern.getPattern(ctx, this, (0, _display_utils.getCurrentTransformInverse)(ctx), _pattern_helper.PathType.SHADING);
    const inv = (0, _display_utils.getCurrentTransformInverse)(ctx);

    if (inv) {
      const canvas = ctx.canvas;
      const width = canvas.width;
      const height = canvas.height;

      const bl = _util.Util.applyTransform([0, 0], inv);

      const br = _util.Util.applyTransform([0, height], inv);

      const ul = _util.Util.applyTransform([width, 0], inv);

      const ur = _util.Util.applyTransform([width, height], inv);

      const x0 = Math.min(bl[0], br[0], ul[0], ur[0]);
      const y0 = Math.min(bl[1], br[1], ul[1], ur[1]);
      const x1 = Math.max(bl[0], br[0], ul[0], ur[0]);
      const y1 = Math.max(bl[1], br[1], ul[1], ur[1]);
      this.ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    } else {
      this.ctx.fillRect(-1e10, -1e10, 2e10, 2e10);
    }

    this.compose(this.current.getClippedPathBoundingBox());
    this.restore();
  }

  beginInlineImage() {
    (0, _util.unreachable)("Should not call beginInlineImage");
  }

  beginImageData() {
    (0, _util.unreachable)("Should not call beginImageData");
  }

  paintFormXObjectBegin(matrix, bbox) {
    if (!this.contentVisible) {
      return;
    }

    this.save();
    this.baseTransformStack.push(this.baseTransform);

    if (Array.isArray(matrix) && matrix.length === 6) {
      this.transform(...matrix);
    }

    this.baseTransform = (0, _display_utils.getCurrentTransform)(this.ctx);

    if (bbox) {
      const width = bbox[2] - bbox[0];
      const height = bbox[3] - bbox[1];
      this.ctx.rect(bbox[0], bbox[1], width, height);
      this.current.updateRectMinMax((0, _display_utils.getCurrentTransform)(this.ctx), bbox);
      this.clip();
      this.endPath();
    }
  }

  paintFormXObjectEnd() {
    if (!this.contentVisible) {
      return;
    }

    this.restore();
    this.baseTransform = this.baseTransformStack.pop();
  }

  beginGroup(group) {
    if (!this.contentVisible) {
      return;
    }

    this.save();

    if (this.inSMaskMode) {
      this.endSMaskMode();
      this.current.activeSMask = null;
    }

    const currentCtx = this.ctx;

    if (!group.isolated) {
      (0, _util.info)("TODO: Support non-isolated groups.");
    }

    if (group.knockout) {
      (0, _util.warn)("Knockout groups not supported.");
    }

    const currentTransform = (0, _display_utils.getCurrentTransform)(currentCtx);

    if (group.matrix) {
      currentCtx.transform(...group.matrix);
    }

    if (!group.bbox) {
      throw new Error("Bounding box is required.");
    }

    let bounds = _util.Util.getAxialAlignedBoundingBox(group.bbox, (0, _display_utils.getCurrentTransform)(currentCtx));

    const canvasBounds = [0, 0, currentCtx.canvas.width, currentCtx.canvas.height];
    bounds = _util.Util.intersect(bounds, canvasBounds) || [0, 0, 0, 0];
    const offsetX = Math.floor(bounds[0]);
    const offsetY = Math.floor(bounds[1]);
    let drawnWidth = Math.max(Math.ceil(bounds[2]) - offsetX, 1);
    let drawnHeight = Math.max(Math.ceil(bounds[3]) - offsetY, 1);
    let scaleX = 1,
        scaleY = 1;

    if (drawnWidth > MAX_GROUP_SIZE) {
      scaleX = drawnWidth / MAX_GROUP_SIZE;
      drawnWidth = MAX_GROUP_SIZE;
    }

    if (drawnHeight > MAX_GROUP_SIZE) {
      scaleY = drawnHeight / MAX_GROUP_SIZE;
      drawnHeight = MAX_GROUP_SIZE;
    }

    this.current.startNewPathAndClipBox([0, 0, drawnWidth, drawnHeight]);
    let cacheId = "groupAt" + this.groupLevel;

    if (group.smask) {
      cacheId += "_smask_" + this.smaskCounter++ % 2;
    }

    const scratchCanvas = this.cachedCanvases.getCanvas(cacheId, drawnWidth, drawnHeight);
    const groupCtx = scratchCanvas.context;
    groupCtx.scale(1 / scaleX, 1 / scaleY);
    groupCtx.translate(-offsetX, -offsetY);
    groupCtx.transform(...currentTransform);

    if (group.smask) {
      this.smaskStack.push({
        canvas: scratchCanvas.canvas,
        context: groupCtx,
        offsetX,
        offsetY,
        scaleX,
        scaleY,
        subtype: group.smask.subtype,
        backdrop: group.smask.backdrop,
        transferMap: group.smask.transferMap || null,
        startTransformInverse: null
      });
    } else {
      currentCtx.setTransform(1, 0, 0, 1, 0, 0);
      currentCtx.translate(offsetX, offsetY);
      currentCtx.scale(scaleX, scaleY);
      currentCtx.save();
    }

    copyCtxState(currentCtx, groupCtx);
    this.ctx = groupCtx;
    this.setGState([["BM", "source-over"], ["ca", 1], ["CA", 1]]);
    this.groupStack.push(currentCtx);
    this.groupLevel++;
  }

  endGroup(group) {
    if (!this.contentVisible) {
      return;
    }

    this.groupLevel--;
    const groupCtx = this.ctx;
    const ctx = this.groupStack.pop();
    this.ctx = ctx;
    this.ctx.imageSmoothingEnabled = false;

    if (group.smask) {
      this.tempSMask = this.smaskStack.pop();
      this.restore();
    } else {
      this.ctx.restore();
      const currentMtx = (0, _display_utils.getCurrentTransform)(this.ctx);
      this.restore();
      this.ctx.save();
      this.ctx.setTransform(...currentMtx);

      const dirtyBox = _util.Util.getAxialAlignedBoundingBox([0, 0, groupCtx.canvas.width, groupCtx.canvas.height], currentMtx);

      this.ctx.drawImage(groupCtx.canvas, 0, 0);
      this.ctx.restore();
      this.compose(dirtyBox);
    }
  }

  beginAnnotation(id, rect, transform, matrix, hasOwnCanvas) {
    _classPrivateMethodGet(this, _restoreInitialState, _restoreInitialState2).call(this);

    resetCtxToDefault(this.ctx, this.foregroundColor);
    this.ctx.save();
    this.save();

    if (this.baseTransform) {
      this.ctx.setTransform(...this.baseTransform);
    }

    if (Array.isArray(rect) && rect.length === 4) {
      const width = rect[2] - rect[0];
      const height = rect[3] - rect[1];

      if (hasOwnCanvas && this.annotationCanvasMap) {
        transform = transform.slice();
        transform[4] -= rect[0];
        transform[5] -= rect[1];
        rect = rect.slice();
        rect[0] = rect[1] = 0;
        rect[2] = width;
        rect[3] = height;

        const [scaleX, scaleY] = _util.Util.singularValueDecompose2dScale((0, _display_utils.getCurrentTransform)(this.ctx));

        const {
          viewportScale
        } = this;
        const canvasWidth = Math.ceil(width * this.outputScaleX * viewportScale);
        const canvasHeight = Math.ceil(height * this.outputScaleY * viewportScale);
        this.annotationCanvas = this.canvasFactory.create(canvasWidth, canvasHeight);
        const {
          canvas,
          context
        } = this.annotationCanvas;
        this.annotationCanvasMap.set(id, canvas);
        this.annotationCanvas.savedCtx = this.ctx;
        this.ctx = context;
        this.ctx.setTransform(scaleX, 0, 0, -scaleY, 0, height * scaleY);
        resetCtxToDefault(this.ctx, this.foregroundColor);
      } else {
        resetCtxToDefault(this.ctx, this.foregroundColor);
        this.ctx.rect(rect[0], rect[1], width, height);
        this.ctx.clip();
        this.endPath();
      }
    }

    this.current = new CanvasExtraState(this.ctx.canvas.width, this.ctx.canvas.height);
    this.transform(...transform);
    this.transform(...matrix);
  }

  endAnnotation() {
    if (this.annotationCanvas) {
      this.ctx = this.annotationCanvas.savedCtx;
      delete this.annotationCanvas.savedCtx;
      delete this.annotationCanvas;
    }
  }

  paintImageMaskXObject(img) {
    if (!this.contentVisible) {
      return;
    }

    const count = img.count;
    img = this.getObject(img.data, img);
    img.count = count;
    const ctx = this.ctx;
    const glyph = this.processingType3;

    if (glyph) {
      if (glyph.compiled === undefined) {
        glyph.compiled = compileType3Glyph(img);
      }

      if (glyph.compiled) {
        glyph.compiled(ctx);
        return;
      }
    }

    const mask = this._createMaskCanvas(img);

    const maskCanvas = mask.canvas;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(maskCanvas, mask.offsetX, mask.offsetY);
    ctx.restore();
    this.compose();
  }

  paintImageMaskXObjectRepeat(img, scaleX) {
    let skewX = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 0;
    let skewY = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : 0;
    let scaleY = arguments.length > 4 ? arguments[4] : undefined;
    let positions = arguments.length > 5 ? arguments[5] : undefined;

    if (!this.contentVisible) {
      return;
    }

    img = this.getObject(img.data, img);
    const ctx = this.ctx;
    ctx.save();
    const currentTransform = (0, _display_utils.getCurrentTransform)(ctx);
    ctx.transform(scaleX, skewX, skewY, scaleY, 0, 0);

    const mask = this._createMaskCanvas(img);

    ctx.setTransform(1, 0, 0, 1, 0, 0);

    for (let i = 0, ii = positions.length; i < ii; i += 2) {
      const trans = _util.Util.transform(currentTransform, [scaleX, skewX, skewY, scaleY, positions[i], positions[i + 1]]);

      const [x, y] = _util.Util.applyTransform([0, 0], trans);

      ctx.drawImage(mask.canvas, x, y);
    }

    ctx.restore();
    this.compose();
  }

  paintImageMaskXObjectGroup(images) {
    if (!this.contentVisible) {
      return;
    }

    const ctx = this.ctx;
    const fillColor = this.current.fillColor;
    const isPatternFill = this.current.patternFill;

    for (const image of images) {
      const {
        data,
        width,
        height,
        transform
      } = image;
      const maskCanvas = this.cachedCanvases.getCanvas("maskCanvas", width, height);
      const maskCtx = maskCanvas.context;
      maskCtx.save();
      const img = this.getObject(data, image);
      putBinaryImageMask(maskCtx, img);
      maskCtx.globalCompositeOperation = "source-in";
      maskCtx.fillStyle = isPatternFill ? fillColor.getPattern(maskCtx, this, (0, _display_utils.getCurrentTransformInverse)(ctx), _pattern_helper.PathType.FILL) : fillColor;
      maskCtx.fillRect(0, 0, width, height);
      maskCtx.restore();
      ctx.save();
      ctx.transform(...transform);
      ctx.scale(1, -1);
      drawImageAtIntegerCoords(ctx, maskCanvas.canvas, 0, 0, width, height, 0, -1, 1, 1);
      ctx.restore();
    }

    this.compose();
  }

  paintImageXObject(objId) {
    if (!this.contentVisible) {
      return;
    }

    const imgData = this.getObject(objId);

    if (!imgData) {
      (0, _util.warn)("Dependent image isn't ready yet");
      return;
    }

    this.paintInlineImageXObject(imgData);
  }

  paintImageXObjectRepeat(objId, scaleX, scaleY, positions) {
    if (!this.contentVisible) {
      return;
    }

    const imgData = this.getObject(objId);

    if (!imgData) {
      (0, _util.warn)("Dependent image isn't ready yet");
      return;
    }

    const width = imgData.width;
    const height = imgData.height;
    const map = [];

    for (let i = 0, ii = positions.length; i < ii; i += 2) {
      map.push({
        transform: [scaleX, 0, 0, scaleY, positions[i], positions[i + 1]],
        x: 0,
        y: 0,
        w: width,
        h: height
      });
    }

    this.paintInlineImageXObjectGroup(imgData, map);
  }

  paintInlineImageXObject(imgData) {
    if (!this.contentVisible) {
      return;
    }

    const width = imgData.width;
    const height = imgData.height;
    const ctx = this.ctx;
    this.save();
    ctx.scale(1 / width, -1 / height);
    let imgToPaint;

    if (typeof HTMLElement === "function" && imgData instanceof HTMLElement || !imgData.data) {
      imgToPaint = imgData;
    } else {
      const tmpCanvas = this.cachedCanvases.getCanvas("inlineImage", width, height);
      const tmpCtx = tmpCanvas.context;
      putBinaryImageData(tmpCtx, imgData, this.current.transferMaps);
      imgToPaint = tmpCanvas.canvas;
    }

    const scaled = this._scaleImage(imgToPaint, (0, _display_utils.getCurrentTransformInverse)(ctx));

    ctx.imageSmoothingEnabled = getImageSmoothingEnabled((0, _display_utils.getCurrentTransform)(ctx), imgData.interpolate);
    const [rWidth, rHeight] = drawImageAtIntegerCoords(ctx, scaled.img, 0, 0, scaled.paintWidth, scaled.paintHeight, 0, -height, width, height);

    if (this.imageLayer) {
      const [left, top] = _util.Util.applyTransform([0, -height], (0, _display_utils.getCurrentTransform)(this.ctx));

      this.imageLayer.appendImage({
        imgData,
        left,
        top,
        width: rWidth,
        height: rHeight
      });
    }

    this.compose();
    this.restore();
  }

  paintInlineImageXObjectGroup(imgData, map) {
    if (!this.contentVisible) {
      return;
    }

    const ctx = this.ctx;
    const w = imgData.width;
    const h = imgData.height;
    const tmpCanvas = this.cachedCanvases.getCanvas("inlineImage", w, h);
    const tmpCtx = tmpCanvas.context;
    putBinaryImageData(tmpCtx, imgData, this.current.transferMaps);

    for (const entry of map) {
      ctx.save();
      ctx.transform(...entry.transform);
      ctx.scale(1, -1);
      drawImageAtIntegerCoords(ctx, tmpCanvas.canvas, entry.x, entry.y, entry.w, entry.h, 0, -1, 1, 1);

      if (this.imageLayer) {
        const [left, top] = _util.Util.applyTransform([entry.x, entry.y], (0, _display_utils.getCurrentTransform)(this.ctx));

        this.imageLayer.appendImage({
          imgData,
          left,
          top,
          width: w,
          height: h
        });
      }

      ctx.restore();
    }

    this.compose();
  }

  paintSolidColorImageMask() {
    if (!this.contentVisible) {
      return;
    }

    this.ctx.fillRect(0, 0, 1, 1);
    this.compose();
  }

  markPoint(tag) {}

  markPointProps(tag, properties) {}

  beginMarkedContent(tag) {
    this.markedContentStack.push({
      visible: true
    });
  }

  beginMarkedContentProps(tag, properties) {
    if (tag === "OC") {
      this.markedContentStack.push({
        visible: this.optionalContentConfig.isVisible(properties)
      });
    } else {
      this.markedContentStack.push({
        visible: true
      });
    }

    this.contentVisible = this.isContentVisible();
  }

  endMarkedContent() {
    this.markedContentStack.pop();
    this.contentVisible = this.isContentVisible();
  }

  beginCompat() {}

  endCompat() {}

  consumePath(clipBox) {
    const isEmpty = this.current.isEmptyClip();

    if (this.pendingClip) {
      this.current.updateClipFromPath();
    }

    if (!this.pendingClip) {
      this.compose(clipBox);
    }

    const ctx = this.ctx;

    if (this.pendingClip) {
      if (!isEmpty) {
        if (this.pendingClip === EO_CLIP) {
          ctx.clip("evenodd");
        } else {
          ctx.clip();
        }
      }

      this.pendingClip = null;
    }

    this.current.startNewPathAndClipBox(this.current.clipBox);
    ctx.beginPath();
  }

  getSinglePixelWidth() {
    if (!this._cachedGetSinglePixelWidth) {
      const m = (0, _display_utils.getCurrentTransform)(this.ctx);

      if (m[1] === 0 && m[2] === 0) {
        this._cachedGetSinglePixelWidth = 1 / Math.min(Math.abs(m[0]), Math.abs(m[3]));
      } else {
        const absDet = Math.abs(m[0] * m[3] - m[2] * m[1]);
        const normX = Math.hypot(m[0], m[2]);
        const normY = Math.hypot(m[1], m[3]);
        this._cachedGetSinglePixelWidth = Math.max(normX, normY) / absDet;
      }
    }

    return this._cachedGetSinglePixelWidth;
  }

  getScaleForStroking() {
    if (!this._cachedScaleForStroking) {
      const {
        lineWidth
      } = this.current;
      const m = (0, _display_utils.getCurrentTransform)(this.ctx);
      let scaleX, scaleY;

      if (m[1] === 0 && m[2] === 0) {
        const normX = Math.abs(m[0]);
        const normY = Math.abs(m[3]);

        if (lineWidth === 0) {
          scaleX = 1 / normX;
          scaleY = 1 / normY;
        } else {
          const scaledXLineWidth = normX * lineWidth;
          const scaledYLineWidth = normY * lineWidth;
          scaleX = scaledXLineWidth < 1 ? 1 / scaledXLineWidth : 1;
          scaleY = scaledYLineWidth < 1 ? 1 / scaledYLineWidth : 1;
        }
      } else {
        const absDet = Math.abs(m[0] * m[3] - m[2] * m[1]);
        const normX = Math.hypot(m[0], m[1]);
        const normY = Math.hypot(m[2], m[3]);

        if (lineWidth === 0) {
          scaleX = normY / absDet;
          scaleY = normX / absDet;
        } else {
          const baseArea = lineWidth * absDet;
          scaleX = normY > baseArea ? normY / baseArea : 1;
          scaleY = normX > baseArea ? normX / baseArea : 1;
        }
      }

      this._cachedScaleForStroking = [scaleX, scaleY];
    }

    return this._cachedScaleForStroking;
  }

  rescaleAndStroke(saveRestore) {
    const {
      ctx
    } = this;
    const {
      lineWidth
    } = this.current;
    const [scaleX, scaleY] = this.getScaleForStroking();
    ctx.lineWidth = lineWidth || 1;

    if (scaleX === 1 && scaleY === 1) {
      ctx.stroke();
      return;
    }

    let savedMatrix, savedDashes, savedDashOffset;

    if (saveRestore) {
      savedMatrix = (0, _display_utils.getCurrentTransform)(ctx);
      savedDashes = ctx.getLineDash().slice();
      savedDashOffset = ctx.lineDashOffset;
    }

    ctx.scale(scaleX, scaleY);
    const scale = Math.max(scaleX, scaleY);
    ctx.setLineDash(ctx.getLineDash().map(x => x / scale));
    ctx.lineDashOffset /= scale;
    ctx.stroke();

    if (saveRestore) {
      ctx.setTransform(...savedMatrix);
      ctx.setLineDash(savedDashes);
      ctx.lineDashOffset = savedDashOffset;
    }
  }

  isContentVisible() {
    for (let i = this.markedContentStack.length - 1; i >= 0; i--) {
      if (!this.markedContentStack[i].visible) {
        return false;
      }
    }

    return true;
  }

}

exports.CanvasGraphics = CanvasGraphics;

function _restoreInitialState2() {
  while (this.stateStack.length || this.inSMaskMode) {
    this.restore();
  }

  this.ctx.restore();

  if (this.transparentCanvas) {
    this.ctx = this.compositeCtx;
    this.ctx.save();
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.drawImage(this.transparentCanvas, 0, 0);
    this.ctx.restore();
    this.transparentCanvas = null;
  }
}

for (const op in _util.OPS) {
  if (CanvasGraphics.prototype[op] !== undefined) {
    CanvasGraphics.prototype[_util.OPS[op]] = CanvasGraphics.prototype[op];
  }
}

/***/ }),
/* 138 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.TilingPattern = exports.PathType = void 0;
exports.getShadingPattern = getShadingPattern;

var _util = __w_pdfjs_require__(1);

var _display_utils = __w_pdfjs_require__(133);

var _is_node = __w_pdfjs_require__(3);

const PathType = {
  FILL: "Fill",
  STROKE: "Stroke",
  SHADING: "Shading"
};
exports.PathType = PathType;

function applyBoundingBox(ctx, bbox) {
  if (!bbox || _is_node.isNodeJS) {
    return;
  }

  const width = bbox[2] - bbox[0];
  const height = bbox[3] - bbox[1];
  const region = new Path2D();
  region.rect(bbox[0], bbox[1], width, height);
  ctx.clip(region);
}

class BaseShadingPattern {
  constructor() {
    if (this.constructor === BaseShadingPattern) {
      (0, _util.unreachable)("Cannot initialize BaseShadingPattern.");
    }
  }

  getPattern() {
    (0, _util.unreachable)("Abstract method `getPattern` called.");
  }

}

class RadialAxialShadingPattern extends BaseShadingPattern {
  constructor(IR) {
    super();
    this._type = IR[1];
    this._bbox = IR[2];
    this._colorStops = IR[3];
    this._p0 = IR[4];
    this._p1 = IR[5];
    this._r0 = IR[6];
    this._r1 = IR[7];
    this.matrix = null;
  }

  _createGradient(ctx) {
    let grad;

    if (this._type === "axial") {
      grad = ctx.createLinearGradient(this._p0[0], this._p0[1], this._p1[0], this._p1[1]);
    } else if (this._type === "radial") {
      grad = ctx.createRadialGradient(this._p0[0], this._p0[1], this._r0, this._p1[0], this._p1[1], this._r1);
    }

    for (const colorStop of this._colorStops) {
      grad.addColorStop(colorStop[0], colorStop[1]);
    }

    return grad;
  }

  getPattern(ctx, owner, inverse, pathType) {
    let pattern;

    if (pathType === PathType.STROKE || pathType === PathType.FILL) {
      const ownerBBox = owner.current.getClippedPathBoundingBox(pathType, (0, _display_utils.getCurrentTransform)(ctx)) || [0, 0, 0, 0];
      const width = Math.ceil(ownerBBox[2] - ownerBBox[0]) || 1;
      const height = Math.ceil(ownerBBox[3] - ownerBBox[1]) || 1;
      const tmpCanvas = owner.cachedCanvases.getCanvas("pattern", width, height, true);
      const tmpCtx = tmpCanvas.context;
      tmpCtx.clearRect(0, 0, tmpCtx.canvas.width, tmpCtx.canvas.height);
      tmpCtx.beginPath();
      tmpCtx.rect(0, 0, tmpCtx.canvas.width, tmpCtx.canvas.height);
      tmpCtx.translate(-ownerBBox[0], -ownerBBox[1]);
      inverse = _util.Util.transform(inverse, [1, 0, 0, 1, ownerBBox[0], ownerBBox[1]]);
      tmpCtx.transform(...owner.baseTransform);

      if (this.matrix) {
        tmpCtx.transform(...this.matrix);
      }

      applyBoundingBox(tmpCtx, this._bbox);
      tmpCtx.fillStyle = this._createGradient(tmpCtx);
      tmpCtx.fill();
      pattern = ctx.createPattern(tmpCanvas.canvas, "no-repeat");
      const domMatrix = new DOMMatrix(inverse);

      try {
        pattern.setTransform(domMatrix);
      } catch (ex) {
        (0, _util.warn)(`RadialAxialShadingPattern.getPattern: "${ex === null || ex === void 0 ? void 0 : ex.message}".`);
      }
    } else {
      applyBoundingBox(ctx, this._bbox);
      pattern = this._createGradient(ctx);
    }

    return pattern;
  }

}

function drawTriangle(data, context, p1, p2, p3, c1, c2, c3) {
  const coords = context.coords,
        colors = context.colors;
  const bytes = data.data,
        rowSize = data.width * 4;
  let tmp;

  if (coords[p1 + 1] > coords[p2 + 1]) {
    tmp = p1;
    p1 = p2;
    p2 = tmp;
    tmp = c1;
    c1 = c2;
    c2 = tmp;
  }

  if (coords[p2 + 1] > coords[p3 + 1]) {
    tmp = p2;
    p2 = p3;
    p3 = tmp;
    tmp = c2;
    c2 = c3;
    c3 = tmp;
  }

  if (coords[p1 + 1] > coords[p2 + 1]) {
    tmp = p1;
    p1 = p2;
    p2 = tmp;
    tmp = c1;
    c1 = c2;
    c2 = tmp;
  }

  const x1 = (coords[p1] + context.offsetX) * context.scaleX;
  const y1 = (coords[p1 + 1] + context.offsetY) * context.scaleY;
  const x2 = (coords[p2] + context.offsetX) * context.scaleX;
  const y2 = (coords[p2 + 1] + context.offsetY) * context.scaleY;
  const x3 = (coords[p3] + context.offsetX) * context.scaleX;
  const y3 = (coords[p3 + 1] + context.offsetY) * context.scaleY;

  if (y1 >= y3) {
    return;
  }

  const c1r = colors[c1],
        c1g = colors[c1 + 1],
        c1b = colors[c1 + 2];
  const c2r = colors[c2],
        c2g = colors[c2 + 1],
        c2b = colors[c2 + 2];
  const c3r = colors[c3],
        c3g = colors[c3 + 1],
        c3b = colors[c3 + 2];
  const minY = Math.round(y1),
        maxY = Math.round(y3);
  let xa, car, cag, cab;
  let xb, cbr, cbg, cbb;

  for (let y = minY; y <= maxY; y++) {
    if (y < y2) {
      let k;

      if (y < y1) {
        k = 0;
      } else {
        k = (y1 - y) / (y1 - y2);
      }

      xa = x1 - (x1 - x2) * k;
      car = c1r - (c1r - c2r) * k;
      cag = c1g - (c1g - c2g) * k;
      cab = c1b - (c1b - c2b) * k;
    } else {
      let k;

      if (y > y3) {
        k = 1;
      } else if (y2 === y3) {
        k = 0;
      } else {
        k = (y2 - y) / (y2 - y3);
      }

      xa = x2 - (x2 - x3) * k;
      car = c2r - (c2r - c3r) * k;
      cag = c2g - (c2g - c3g) * k;
      cab = c2b - (c2b - c3b) * k;
    }

    let k;

    if (y < y1) {
      k = 0;
    } else if (y > y3) {
      k = 1;
    } else {
      k = (y1 - y) / (y1 - y3);
    }

    xb = x1 - (x1 - x3) * k;
    cbr = c1r - (c1r - c3r) * k;
    cbg = c1g - (c1g - c3g) * k;
    cbb = c1b - (c1b - c3b) * k;
    const x1_ = Math.round(Math.min(xa, xb));
    const x2_ = Math.round(Math.max(xa, xb));
    let j = rowSize * y + x1_ * 4;

    for (let x = x1_; x <= x2_; x++) {
      k = (xa - x) / (xa - xb);

      if (k < 0) {
        k = 0;
      } else if (k > 1) {
        k = 1;
      }

      bytes[j++] = car - (car - cbr) * k | 0;
      bytes[j++] = cag - (cag - cbg) * k | 0;
      bytes[j++] = cab - (cab - cbb) * k | 0;
      bytes[j++] = 255;
    }
  }
}

function drawFigure(data, figure, context) {
  const ps = figure.coords;
  const cs = figure.colors;
  let i, ii;

  switch (figure.type) {
    case "lattice":
      const verticesPerRow = figure.verticesPerRow;
      const rows = Math.floor(ps.length / verticesPerRow) - 1;
      const cols = verticesPerRow - 1;

      for (i = 0; i < rows; i++) {
        let q = i * verticesPerRow;

        for (let j = 0; j < cols; j++, q++) {
          drawTriangle(data, context, ps[q], ps[q + 1], ps[q + verticesPerRow], cs[q], cs[q + 1], cs[q + verticesPerRow]);
          drawTriangle(data, context, ps[q + verticesPerRow + 1], ps[q + 1], ps[q + verticesPerRow], cs[q + verticesPerRow + 1], cs[q + 1], cs[q + verticesPerRow]);
        }
      }

      break;

    case "triangles":
      for (i = 0, ii = ps.length; i < ii; i += 3) {
        drawTriangle(data, context, ps[i], ps[i + 1], ps[i + 2], cs[i], cs[i + 1], cs[i + 2]);
      }

      break;

    default:
      throw new Error("illegal figure");
  }
}

class MeshShadingPattern extends BaseShadingPattern {
  constructor(IR) {
    super();
    this._coords = IR[2];
    this._colors = IR[3];
    this._figures = IR[4];
    this._bounds = IR[5];
    this._bbox = IR[7];
    this._background = IR[8];
    this.matrix = null;
  }

  _createMeshCanvas(combinedScale, backgroundColor, cachedCanvases) {
    const EXPECTED_SCALE = 1.1;
    const MAX_PATTERN_SIZE = 3000;
    const BORDER_SIZE = 2;
    const offsetX = Math.floor(this._bounds[0]);
    const offsetY = Math.floor(this._bounds[1]);
    const boundsWidth = Math.ceil(this._bounds[2]) - offsetX;
    const boundsHeight = Math.ceil(this._bounds[3]) - offsetY;
    const width = Math.min(Math.ceil(Math.abs(boundsWidth * combinedScale[0] * EXPECTED_SCALE)), MAX_PATTERN_SIZE);
    const height = Math.min(Math.ceil(Math.abs(boundsHeight * combinedScale[1] * EXPECTED_SCALE)), MAX_PATTERN_SIZE);
    const scaleX = boundsWidth / width;
    const scaleY = boundsHeight / height;
    const context = {
      coords: this._coords,
      colors: this._colors,
      offsetX: -offsetX,
      offsetY: -offsetY,
      scaleX: 1 / scaleX,
      scaleY: 1 / scaleY
    };
    const paddedWidth = width + BORDER_SIZE * 2;
    const paddedHeight = height + BORDER_SIZE * 2;
    const tmpCanvas = cachedCanvases.getCanvas("mesh", paddedWidth, paddedHeight, false);
    const tmpCtx = tmpCanvas.context;
    const data = tmpCtx.createImageData(width, height);

    if (backgroundColor) {
      const bytes = data.data;

      for (let i = 0, ii = bytes.length; i < ii; i += 4) {
        bytes[i] = backgroundColor[0];
        bytes[i + 1] = backgroundColor[1];
        bytes[i + 2] = backgroundColor[2];
        bytes[i + 3] = 255;
      }
    }

    for (const figure of this._figures) {
      drawFigure(data, figure, context);
    }

    tmpCtx.putImageData(data, BORDER_SIZE, BORDER_SIZE);
    const canvas = tmpCanvas.canvas;
    return {
      canvas,
      offsetX: offsetX - BORDER_SIZE * scaleX,
      offsetY: offsetY - BORDER_SIZE * scaleY,
      scaleX,
      scaleY
    };
  }

  getPattern(ctx, owner, inverse, pathType) {
    applyBoundingBox(ctx, this._bbox);
    let scale;

    if (pathType === PathType.SHADING) {
      scale = _util.Util.singularValueDecompose2dScale((0, _display_utils.getCurrentTransform)(ctx));
    } else {
      scale = _util.Util.singularValueDecompose2dScale(owner.baseTransform);

      if (this.matrix) {
        const matrixScale = _util.Util.singularValueDecompose2dScale(this.matrix);

        scale = [scale[0] * matrixScale[0], scale[1] * matrixScale[1]];
      }
    }

    const temporaryPatternCanvas = this._createMeshCanvas(scale, pathType === PathType.SHADING ? null : this._background, owner.cachedCanvases);

    if (pathType !== PathType.SHADING) {
      ctx.setTransform(...owner.baseTransform);

      if (this.matrix) {
        ctx.transform(...this.matrix);
      }
    }

    ctx.translate(temporaryPatternCanvas.offsetX, temporaryPatternCanvas.offsetY);
    ctx.scale(temporaryPatternCanvas.scaleX, temporaryPatternCanvas.scaleY);
    return ctx.createPattern(temporaryPatternCanvas.canvas, "no-repeat");
  }

}

class DummyShadingPattern extends BaseShadingPattern {
  getPattern() {
    return "hotpink";
  }

}

function getShadingPattern(IR) {
  switch (IR[0]) {
    case "RadialAxial":
      return new RadialAxialShadingPattern(IR);

    case "Mesh":
      return new MeshShadingPattern(IR);

    case "Dummy":
      return new DummyShadingPattern();
  }

  throw new Error(`Unknown IR type: ${IR[0]}`);
}

const PaintType = {
  COLORED: 1,
  UNCOLORED: 2
};

class TilingPattern {
  static get MAX_PATTERN_SIZE() {
    return (0, _util.shadow)(this, "MAX_PATTERN_SIZE", 3000);
  }

  constructor(IR, color, ctx, canvasGraphicsFactory, baseTransform) {
    this.operatorList = IR[2];
    this.matrix = IR[3] || [1, 0, 0, 1, 0, 0];
    this.bbox = IR[4];
    this.xstep = IR[5];
    this.ystep = IR[6];
    this.paintType = IR[7];
    this.tilingType = IR[8];
    this.color = color;
    this.ctx = ctx;
    this.canvasGraphicsFactory = canvasGraphicsFactory;
    this.baseTransform = baseTransform;
  }

  createPatternCanvas(owner) {
    const operatorList = this.operatorList;
    const bbox = this.bbox;
    const xstep = this.xstep;
    const ystep = this.ystep;
    const paintType = this.paintType;
    const tilingType = this.tilingType;
    const color = this.color;
    const canvasGraphicsFactory = this.canvasGraphicsFactory;
    (0, _util.info)("TilingType: " + tilingType);
    const x0 = bbox[0],
          y0 = bbox[1],
          x1 = bbox[2],
          y1 = bbox[3];

    const matrixScale = _util.Util.singularValueDecompose2dScale(this.matrix);

    const curMatrixScale = _util.Util.singularValueDecompose2dScale(this.baseTransform);

    const combinedScale = [matrixScale[0] * curMatrixScale[0], matrixScale[1] * curMatrixScale[1]];
    const dimx = this.getSizeAndScale(xstep, this.ctx.canvas.width, combinedScale[0]);
    const dimy = this.getSizeAndScale(ystep, this.ctx.canvas.height, combinedScale[1]);
    const tmpCanvas = owner.cachedCanvases.getCanvas("pattern", dimx.size, dimy.size, true);
    const tmpCtx = tmpCanvas.context;
    const graphics = canvasGraphicsFactory.createCanvasGraphics(tmpCtx);
    graphics.groupLevel = owner.groupLevel;
    this.setFillAndStrokeStyleToContext(graphics, paintType, color);
    let adjustedX0 = x0;
    let adjustedY0 = y0;
    let adjustedX1 = x1;
    let adjustedY1 = y1;

    if (x0 < 0) {
      adjustedX0 = 0;
      adjustedX1 += Math.abs(x0);
    }

    if (y0 < 0) {
      adjustedY0 = 0;
      adjustedY1 += Math.abs(y0);
    }

    tmpCtx.translate(-(dimx.scale * adjustedX0), -(dimy.scale * adjustedY0));
    graphics.transform(dimx.scale, 0, 0, dimy.scale, 0, 0);
    tmpCtx.save();
    this.clipBbox(graphics, adjustedX0, adjustedY0, adjustedX1, adjustedY1);
    graphics.baseTransform = (0, _display_utils.getCurrentTransform)(graphics.ctx);
    graphics.executeOperatorList(operatorList);
    graphics.endDrawing();
    return {
      canvas: tmpCanvas.canvas,
      scaleX: dimx.scale,
      scaleY: dimy.scale,
      offsetX: adjustedX0,
      offsetY: adjustedY0
    };
  }

  getSizeAndScale(step, realOutputSize, scale) {
    step = Math.abs(step);
    const maxSize = Math.max(TilingPattern.MAX_PATTERN_SIZE, realOutputSize);
    let size = Math.ceil(step * scale);

    if (size >= maxSize) {
      size = maxSize;
    } else {
      scale = size / step;
    }

    return {
      scale,
      size
    };
  }

  clipBbox(graphics, x0, y0, x1, y1) {
    const bboxWidth = x1 - x0;
    const bboxHeight = y1 - y0;
    graphics.ctx.rect(x0, y0, bboxWidth, bboxHeight);
    graphics.current.updateRectMinMax((0, _display_utils.getCurrentTransform)(graphics.ctx), [x0, y0, x1, y1]);
    graphics.clip();
    graphics.endPath();
  }

  setFillAndStrokeStyleToContext(graphics, paintType, color) {
    const context = graphics.ctx,
          current = graphics.current;

    switch (paintType) {
      case PaintType.COLORED:
        const ctx = this.ctx;
        context.fillStyle = ctx.fillStyle;
        context.strokeStyle = ctx.strokeStyle;
        current.fillColor = ctx.fillStyle;
        current.strokeColor = ctx.strokeStyle;
        break;

      case PaintType.UNCOLORED:
        const cssColor = _util.Util.makeHexColor(color[0], color[1], color[2]);

        context.fillStyle = cssColor;
        context.strokeStyle = cssColor;
        current.fillColor = cssColor;
        current.strokeColor = cssColor;
        break;

      default:
        throw new _util.FormatError(`Unsupported paint type: ${paintType}`);
    }
  }

  getPattern(ctx, owner, inverse, pathType) {
    let matrix = inverse;

    if (pathType !== PathType.SHADING) {
      matrix = _util.Util.transform(matrix, owner.baseTransform);

      if (this.matrix) {
        matrix = _util.Util.transform(matrix, this.matrix);
      }
    }

    const temporaryPatternCanvas = this.createPatternCanvas(owner);
    let domMatrix = new DOMMatrix(matrix);
    domMatrix = domMatrix.translate(temporaryPatternCanvas.offsetX, temporaryPatternCanvas.offsetY);
    domMatrix = domMatrix.scale(1 / temporaryPatternCanvas.scaleX, 1 / temporaryPatternCanvas.scaleY);
    const pattern = ctx.createPattern(temporaryPatternCanvas.canvas, "repeat");

    try {
      pattern.setTransform(domMatrix);
    } catch (ex) {
      (0, _util.warn)(`TilingPattern.getPattern: "${ex === null || ex === void 0 ? void 0 : ex.message}".`);
    }

    return pattern;
  }

}

exports.TilingPattern = TilingPattern;

/***/ }),
/* 139 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.applyMaskImageData = applyMaskImageData;

var _util = __w_pdfjs_require__(1);

function applyMaskImageData(_ref) {
  let {
    src,
    srcPos = 0,
    dest,
    destPos = 0,
    width,
    height,
    inverseDecode = false
  } = _ref;
  const opaque = _util.FeatureTest.isLittleEndian ? 0xff000000 : 0x000000ff;
  const [zeroMapping, oneMapping] = !inverseDecode ? [opaque, 0] : [0, opaque];
  const widthInSource = width >> 3;
  const widthRemainder = width & 7;
  const srcLength = src.length;
  dest = new Uint32Array(dest.buffer);

  for (let i = 0; i < height; i++) {
    for (const max = srcPos + widthInSource; srcPos < max; srcPos++) {
      const elem = srcPos < srcLength ? src[srcPos] : 255;
      dest[destPos++] = elem & 0b10000000 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b1000000 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b100000 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b10000 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b1000 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b100 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b10 ? oneMapping : zeroMapping;
      dest[destPos++] = elem & 0b1 ? oneMapping : zeroMapping;
    }

    if (widthRemainder === 0) {
      continue;
    }

    const elem = srcPos < srcLength ? src[srcPos++] : 255;

    for (let j = 0; j < widthRemainder; j++) {
      dest[destPos++] = elem & 1 << 7 - j ? oneMapping : zeroMapping;
    }
  }

  return {
    srcPos,
    destPos
  };
}

/***/ }),
/* 140 */
/***/ ((__unused_webpack_module, exports) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.GlobalWorkerOptions = void 0;
const GlobalWorkerOptions = Object.create(null);
exports.GlobalWorkerOptions = GlobalWorkerOptions;
GlobalWorkerOptions.workerPort = GlobalWorkerOptions.workerPort === undefined ? null : GlobalWorkerOptions.workerPort;
GlobalWorkerOptions.workerSrc = GlobalWorkerOptions.workerSrc === undefined ? "" : GlobalWorkerOptions.workerSrc;

/***/ }),
/* 141 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.MessageHandler = void 0;

var _util = __w_pdfjs_require__(1);

const CallbackKind = {
  UNKNOWN: 0,
  DATA: 1,
  ERROR: 2
};
const StreamKind = {
  UNKNOWN: 0,
  CANCEL: 1,
  CANCEL_COMPLETE: 2,
  CLOSE: 3,
  ENQUEUE: 4,
  ERROR: 5,
  PULL: 6,
  PULL_COMPLETE: 7,
  START_COMPLETE: 8
};

function wrapReason(reason) {
  if (!(reason instanceof Error || typeof reason === "object" && reason !== null)) {
    (0, _util.unreachable)('wrapReason: Expected "reason" to be a (possibly cloned) Error.');
  }

  switch (reason.name) {
    case "AbortException":
      return new _util.AbortException(reason.message);

    case "MissingPDFException":
      return new _util.MissingPDFException(reason.message);

    case "PasswordException":
      return new _util.PasswordException(reason.message, reason.code);

    case "UnexpectedResponseException":
      return new _util.UnexpectedResponseException(reason.message, reason.status);

    case "UnknownErrorException":
      return new _util.UnknownErrorException(reason.message, reason.details);

    default:
      return new _util.UnknownErrorException(reason.message, reason.toString());
  }
}

class MessageHandler {
  constructor(sourceName, targetName, comObj) {
    this.sourceName = sourceName;
    this.targetName = targetName;
    this.comObj = comObj;
    this.callbackId = 1;
    this.streamId = 1;
    this.streamSinks = Object.create(null);
    this.streamControllers = Object.create(null);
    this.callbackCapabilities = Object.create(null);
    this.actionHandler = Object.create(null);

    this._onComObjOnMessage = event => {
      const data = event.data;

      if (data.targetName !== this.sourceName) {
        return;
      }

      if (data.stream) {
        this._processStreamMessage(data);

        return;
      }

      if (data.callback) {
        const callbackId = data.callbackId;
        const capability = this.callbackCapabilities[callbackId];

        if (!capability) {
          throw new Error(`Cannot resolve callback ${callbackId}`);
        }

        delete this.callbackCapabilities[callbackId];

        if (data.callback === CallbackKind.DATA) {
          capability.resolve(data.data);
        } else if (data.callback === CallbackKind.ERROR) {
          capability.reject(wrapReason(data.reason));
        } else {
          throw new Error("Unexpected callback case");
        }

        return;
      }

      const action = this.actionHandler[data.action];

      if (!action) {
        throw new Error(`Unknown action from worker: ${data.action}`);
      }

      if (data.callbackId) {
        const cbSourceName = this.sourceName;
        const cbTargetName = data.sourceName;
        new Promise(function (resolve) {
          resolve(action(data.data));
        }).then(function (result) {
          comObj.postMessage({
            sourceName: cbSourceName,
            targetName: cbTargetName,
            callback: CallbackKind.DATA,
            callbackId: data.callbackId,
            data: result
          });
        }, function (reason) {
          comObj.postMessage({
            sourceName: cbSourceName,
            targetName: cbTargetName,
            callback: CallbackKind.ERROR,
            callbackId: data.callbackId,
            reason: wrapReason(reason)
          });
        });
        return;
      }

      if (data.streamId) {
        this._createStreamSink(data);

        return;
      }

      action(data.data);
    };

    comObj.addEventListener("message", this._onComObjOnMessage);
  }

  on(actionName, handler) {
    const ah = this.actionHandler;

    if (ah[actionName]) {
      throw new Error(`There is already an actionName called "${actionName}"`);
    }

    ah[actionName] = handler;
  }

  send(actionName, data, transfers) {
    this.comObj.postMessage({
      sourceName: this.sourceName,
      targetName: this.targetName,
      action: actionName,
      data
    }, transfers);
  }

  sendWithPromise(actionName, data, transfers) {
    const callbackId = this.callbackId++;
    const capability = (0, _util.createPromiseCapability)();
    this.callbackCapabilities[callbackId] = capability;

    try {
      this.comObj.postMessage({
        sourceName: this.sourceName,
        targetName: this.targetName,
        action: actionName,
        callbackId,
        data
      }, transfers);
    } catch (ex) {
      capability.reject(ex);
    }

    return capability.promise;
  }

  sendWithStream(actionName, data, queueingStrategy, transfers) {
    const streamId = this.streamId++,
          sourceName = this.sourceName,
          targetName = this.targetName,
          comObj = this.comObj;
    return new ReadableStream({
      start: controller => {
        const startCapability = (0, _util.createPromiseCapability)();
        this.streamControllers[streamId] = {
          controller,
          startCall: startCapability,
          pullCall: null,
          cancelCall: null,
          isClosed: false
        };
        comObj.postMessage({
          sourceName,
          targetName,
          action: actionName,
          streamId,
          data,
          desiredSize: controller.desiredSize
        }, transfers);
        return startCapability.promise;
      },
      pull: controller => {
        const pullCapability = (0, _util.createPromiseCapability)();
        this.streamControllers[streamId].pullCall = pullCapability;
        comObj.postMessage({
          sourceName,
          targetName,
          stream: StreamKind.PULL,
          streamId,
          desiredSize: controller.desiredSize
        });
        return pullCapability.promise;
      },
      cancel: reason => {
        (0, _util.assert)(reason instanceof Error, "cancel must have a valid reason");
        const cancelCapability = (0, _util.createPromiseCapability)();
        this.streamControllers[streamId].cancelCall = cancelCapability;
        this.streamControllers[streamId].isClosed = true;
        comObj.postMessage({
          sourceName,
          targetName,
          stream: StreamKind.CANCEL,
          streamId,
          reason: wrapReason(reason)
        });
        return cancelCapability.promise;
      }
    }, queueingStrategy);
  }

  _createStreamSink(data) {
    const streamId = data.streamId,
          sourceName = this.sourceName,
          targetName = data.sourceName,
          comObj = this.comObj;
    const self = this,
          action = this.actionHandler[data.action];
    const streamSink = {
      enqueue(chunk) {
        let size = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 1;
        let transfers = arguments.length > 2 ? arguments[2] : undefined;

        if (this.isCancelled) {
          return;
        }

        const lastDesiredSize = this.desiredSize;
        this.desiredSize -= size;

        if (lastDesiredSize > 0 && this.desiredSize <= 0) {
          this.sinkCapability = (0, _util.createPromiseCapability)();
          this.ready = this.sinkCapability.promise;
        }

        comObj.postMessage({
          sourceName,
          targetName,
          stream: StreamKind.ENQUEUE,
          streamId,
          chunk
        }, transfers);
      },

      close() {
        if (this.isCancelled) {
          return;
        }

        this.isCancelled = true;
        comObj.postMessage({
          sourceName,
          targetName,
          stream: StreamKind.CLOSE,
          streamId
        });
        delete self.streamSinks[streamId];
      },

      error(reason) {
        (0, _util.assert)(reason instanceof Error, "error must have a valid reason");

        if (this.isCancelled) {
          return;
        }

        this.isCancelled = true;
        comObj.postMessage({
          sourceName,
          targetName,
          stream: StreamKind.ERROR,
          streamId,
          reason: wrapReason(reason)
        });
      },

      sinkCapability: (0, _util.createPromiseCapability)(),
      onPull: null,
      onCancel: null,
      isCancelled: false,
      desiredSize: data.desiredSize,
      ready: null
    };
    streamSink.sinkCapability.resolve();
    streamSink.ready = streamSink.sinkCapability.promise;
    this.streamSinks[streamId] = streamSink;
    new Promise(function (resolve) {
      resolve(action(data.data, streamSink));
    }).then(function () {
      comObj.postMessage({
        sourceName,
        targetName,
        stream: StreamKind.START_COMPLETE,
        streamId,
        success: true
      });
    }, function (reason) {
      comObj.postMessage({
        sourceName,
        targetName,
        stream: StreamKind.START_COMPLETE,
        streamId,
        reason: wrapReason(reason)
      });
    });
  }

  _processStreamMessage(data) {
    const streamId = data.streamId,
          sourceName = this.sourceName,
          targetName = data.sourceName,
          comObj = this.comObj;
    const streamController = this.streamControllers[streamId],
          streamSink = this.streamSinks[streamId];

    switch (data.stream) {
      case StreamKind.START_COMPLETE:
        if (data.success) {
          streamController.startCall.resolve();
        } else {
          streamController.startCall.reject(wrapReason(data.reason));
        }

        break;

      case StreamKind.PULL_COMPLETE:
        if (data.success) {
          streamController.pullCall.resolve();
        } else {
          streamController.pullCall.reject(wrapReason(data.reason));
        }

        break;

      case StreamKind.PULL:
        if (!streamSink) {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.PULL_COMPLETE,
            streamId,
            success: true
          });
          break;
        }

        if (streamSink.desiredSize <= 0 && data.desiredSize > 0) {
          streamSink.sinkCapability.resolve();
        }

        streamSink.desiredSize = data.desiredSize;
        new Promise(function (resolve) {
          resolve(streamSink.onPull && streamSink.onPull());
        }).then(function () {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.PULL_COMPLETE,
            streamId,
            success: true
          });
        }, function (reason) {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.PULL_COMPLETE,
            streamId,
            reason: wrapReason(reason)
          });
        });
        break;

      case StreamKind.ENQUEUE:
        (0, _util.assert)(streamController, "enqueue should have stream controller");

        if (streamController.isClosed) {
          break;
        }

        streamController.controller.enqueue(data.chunk);
        break;

      case StreamKind.CLOSE:
        (0, _util.assert)(streamController, "close should have stream controller");

        if (streamController.isClosed) {
          break;
        }

        streamController.isClosed = true;
        streamController.controller.close();

        this._deleteStreamController(streamController, streamId);

        break;

      case StreamKind.ERROR:
        (0, _util.assert)(streamController, "error should have stream controller");
        streamController.controller.error(wrapReason(data.reason));

        this._deleteStreamController(streamController, streamId);

        break;

      case StreamKind.CANCEL_COMPLETE:
        if (data.success) {
          streamController.cancelCall.resolve();
        } else {
          streamController.cancelCall.reject(wrapReason(data.reason));
        }

        this._deleteStreamController(streamController, streamId);

        break;

      case StreamKind.CANCEL:
        if (!streamSink) {
          break;
        }

        new Promise(function (resolve) {
          resolve(streamSink.onCancel && streamSink.onCancel(wrapReason(data.reason)));
        }).then(function () {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.CANCEL_COMPLETE,
            streamId,
            success: true
          });
        }, function (reason) {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.CANCEL_COMPLETE,
            streamId,
            reason: wrapReason(reason)
          });
        });
        streamSink.sinkCapability.reject(wrapReason(data.reason));
        streamSink.isCancelled = true;
        delete this.streamSinks[streamId];
        break;

      default:
        throw new Error("Unexpected stream case");
    }
  }

  async _deleteStreamController(streamController, streamId) {
    await Promise.allSettled([streamController.startCall && streamController.startCall.promise, streamController.pullCall && streamController.pullCall.promise, streamController.cancelCall && streamController.cancelCall.promise]);
    delete this.streamControllers[streamId];
  }

  destroy() {
    this.comObj.removeEventListener("message", this._onComObjOnMessage);
  }

}

exports.MessageHandler = MessageHandler;

/***/ }),
/* 142 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.Metadata = void 0;

var _util = __w_pdfjs_require__(1);

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

var _metadataMap = /*#__PURE__*/new WeakMap();

var _data = /*#__PURE__*/new WeakMap();

class Metadata {
  constructor(_ref) {
    let {
      parsedData,
      rawData
    } = _ref;

    _classPrivateFieldInitSpec(this, _metadataMap, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldInitSpec(this, _data, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldSet(this, _metadataMap, parsedData);

    _classPrivateFieldSet(this, _data, rawData);
  }

  getRaw() {
    return _classPrivateFieldGet(this, _data);
  }

  get(name) {
    var _classPrivateFieldGet2;

    return (_classPrivateFieldGet2 = _classPrivateFieldGet(this, _metadataMap).get(name)) !== null && _classPrivateFieldGet2 !== void 0 ? _classPrivateFieldGet2 : null;
  }

  getAll() {
    return (0, _util.objectFromMap)(_classPrivateFieldGet(this, _metadataMap));
  }

  has(name) {
    return _classPrivateFieldGet(this, _metadataMap).has(name);
  }

}

exports.Metadata = Metadata;

/***/ }),
/* 143 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.OptionalContentConfig = void 0;

var _util = __w_pdfjs_require__(1);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

const INTERNAL = Symbol("INTERNAL");

var _visible = /*#__PURE__*/new WeakMap();

class OptionalContentGroup {
  constructor(name, intent) {
    _classPrivateFieldInitSpec(this, _visible, {
      writable: true,
      value: true
    });

    this.name = name;
    this.intent = intent;
  }

  get visible() {
    return _classPrivateFieldGet(this, _visible);
  }

  _setVisible(internal, visible) {
    if (internal !== INTERNAL) {
      (0, _util.unreachable)("Internal method `_setVisible` called.");
    }

    _classPrivateFieldSet(this, _visible, visible);
  }

}

var _cachedHasInitialVisibility = /*#__PURE__*/new WeakMap();

var _groups = /*#__PURE__*/new WeakMap();

var _initialVisibility = /*#__PURE__*/new WeakMap();

var _order = /*#__PURE__*/new WeakMap();

var _evaluateVisibilityExpression = /*#__PURE__*/new WeakSet();

class OptionalContentConfig {
  constructor(data) {
    _classPrivateMethodInitSpec(this, _evaluateVisibilityExpression);

    _classPrivateFieldInitSpec(this, _cachedHasInitialVisibility, {
      writable: true,
      value: true
    });

    _classPrivateFieldInitSpec(this, _groups, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _initialVisibility, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _order, {
      writable: true,
      value: null
    });

    this.name = null;
    this.creator = null;

    if (data === null) {
      return;
    }

    this.name = data.name;
    this.creator = data.creator;

    _classPrivateFieldSet(this, _order, data.order);

    for (const group of data.groups) {
      _classPrivateFieldGet(this, _groups).set(group.id, new OptionalContentGroup(group.name, group.intent));
    }

    if (data.baseState === "OFF") {
      for (const group of _classPrivateFieldGet(this, _groups).values()) {
        group._setVisible(INTERNAL, false);
      }
    }

    for (const on of data.on) {
      _classPrivateFieldGet(this, _groups).get(on)._setVisible(INTERNAL, true);
    }

    for (const off of data.off) {
      _classPrivateFieldGet(this, _groups).get(off)._setVisible(INTERNAL, false);
    }

    _classPrivateFieldSet(this, _initialVisibility, new Map());

    for (const [id, group] of _classPrivateFieldGet(this, _groups)) {
      _classPrivateFieldGet(this, _initialVisibility).set(id, group.visible);
    }
  }

  isVisible(group) {
    if (_classPrivateFieldGet(this, _groups).size === 0) {
      return true;
    }

    if (!group) {
      (0, _util.warn)("Optional content group not defined.");
      return true;
    }

    if (group.type === "OCG") {
      if (!_classPrivateFieldGet(this, _groups).has(group.id)) {
        (0, _util.warn)(`Optional content group not found: ${group.id}`);
        return true;
      }

      return _classPrivateFieldGet(this, _groups).get(group.id).visible;
    } else if (group.type === "OCMD") {
      if (group.expression) {
        return _classPrivateMethodGet(this, _evaluateVisibilityExpression, _evaluateVisibilityExpression2).call(this, group.expression);
      }

      if (!group.policy || group.policy === "AnyOn") {
        for (const id of group.ids) {
          if (!_classPrivateFieldGet(this, _groups).has(id)) {
            (0, _util.warn)(`Optional content group not found: ${id}`);
            return true;
          }

          if (_classPrivateFieldGet(this, _groups).get(id).visible) {
            return true;
          }
        }

        return false;
      } else if (group.policy === "AllOn") {
        for (const id of group.ids) {
          if (!_classPrivateFieldGet(this, _groups).has(id)) {
            (0, _util.warn)(`Optional content group not found: ${id}`);
            return true;
          }

          if (!_classPrivateFieldGet(this, _groups).get(id).visible) {
            return false;
          }
        }

        return true;
      } else if (group.policy === "AnyOff") {
        for (const id of group.ids) {
          if (!_classPrivateFieldGet(this, _groups).has(id)) {
            (0, _util.warn)(`Optional content group not found: ${id}`);
            return true;
          }

          if (!_classPrivateFieldGet(this, _groups).get(id).visible) {
            return true;
          }
        }

        return false;
      } else if (group.policy === "AllOff") {
        for (const id of group.ids) {
          if (!_classPrivateFieldGet(this, _groups).has(id)) {
            (0, _util.warn)(`Optional content group not found: ${id}`);
            return true;
          }

          if (_classPrivateFieldGet(this, _groups).get(id).visible) {
            return false;
          }
        }

        return true;
      }

      (0, _util.warn)(`Unknown optional content policy ${group.policy}.`);
      return true;
    }

    (0, _util.warn)(`Unknown group type ${group.type}.`);
    return true;
  }

  setVisibility(id) {
    let visible = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : true;

    if (!_classPrivateFieldGet(this, _groups).has(id)) {
      (0, _util.warn)(`Optional content group not found: ${id}`);
      return;
    }

    _classPrivateFieldGet(this, _groups).get(id)._setVisible(INTERNAL, !!visible);

    _classPrivateFieldSet(this, _cachedHasInitialVisibility, null);
  }

  get hasInitialVisibility() {
    if (_classPrivateFieldGet(this, _cachedHasInitialVisibility) !== null) {
      return _classPrivateFieldGet(this, _cachedHasInitialVisibility);
    }

    for (const [id, group] of _classPrivateFieldGet(this, _groups)) {
      const visible = _classPrivateFieldGet(this, _initialVisibility).get(id);

      if (group.visible !== visible) {
        return _classPrivateFieldSet(this, _cachedHasInitialVisibility, false);
      }
    }

    return _classPrivateFieldSet(this, _cachedHasInitialVisibility, true);
  }

  getOrder() {
    if (!_classPrivateFieldGet(this, _groups).size) {
      return null;
    }

    if (_classPrivateFieldGet(this, _order)) {
      return _classPrivateFieldGet(this, _order).slice();
    }

    return [..._classPrivateFieldGet(this, _groups).keys()];
  }

  getGroups() {
    return _classPrivateFieldGet(this, _groups).size > 0 ? (0, _util.objectFromMap)(_classPrivateFieldGet(this, _groups)) : null;
  }

  getGroup(id) {
    return _classPrivateFieldGet(this, _groups).get(id) || null;
  }

}

exports.OptionalContentConfig = OptionalContentConfig;

function _evaluateVisibilityExpression2(array) {
  const length = array.length;

  if (length < 2) {
    return true;
  }

  const operator = array[0];

  for (let i = 1; i < length; i++) {
    const element = array[i];
    let state;

    if (Array.isArray(element)) {
      state = _classPrivateMethodGet(this, _evaluateVisibilityExpression, _evaluateVisibilityExpression2).call(this, element);
    } else if (_classPrivateFieldGet(this, _groups).has(element)) {
      state = _classPrivateFieldGet(this, _groups).get(element).visible;
    } else {
      (0, _util.warn)(`Optional content group not found: ${element}`);
      return true;
    }

    switch (operator) {
      case "And":
        if (!state) {
          return false;
        }

        break;

      case "Or":
        if (state) {
          return true;
        }

        break;

      case "Not":
        return !state;

      default:
        return true;
    }
  }

  return operator === "And";
}

/***/ }),
/* 144 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.PDFDataTransportStream = void 0;

var _util = __w_pdfjs_require__(1);

var _display_utils = __w_pdfjs_require__(133);

class PDFDataTransportStream {
  constructor(params, pdfDataRangeTransport) {
    (0, _util.assert)(pdfDataRangeTransport, 'PDFDataTransportStream - missing required "pdfDataRangeTransport" argument.');
    this._queuedChunks = [];
    this._progressiveDone = params.progressiveDone || false;
    this._contentDispositionFilename = params.contentDispositionFilename || null;
    const initialData = params.initialData;

    if ((initialData === null || initialData === void 0 ? void 0 : initialData.length) > 0) {
      const buffer = new Uint8Array(initialData).buffer;

      this._queuedChunks.push(buffer);
    }

    this._pdfDataRangeTransport = pdfDataRangeTransport;
    this._isStreamingSupported = !params.disableStream;
    this._isRangeSupported = !params.disableRange;
    this._contentLength = params.length;
    this._fullRequestReader = null;
    this._rangeReaders = [];

    this._pdfDataRangeTransport.addRangeListener((begin, chunk) => {
      this._onReceiveData({
        begin,
        chunk
      });
    });

    this._pdfDataRangeTransport.addProgressListener((loaded, total) => {
      this._onProgress({
        loaded,
        total
      });
    });

    this._pdfDataRangeTransport.addProgressiveReadListener(chunk => {
      this._onReceiveData({
        chunk
      });
    });

    this._pdfDataRangeTransport.addProgressiveDoneListener(() => {
      this._onProgressiveDone();
    });

    this._pdfDataRangeTransport.transportReady();
  }

  _onReceiveData(args) {
    const buffer = new Uint8Array(args.chunk).buffer;

    if (args.begin === undefined) {
      if (this._fullRequestReader) {
        this._fullRequestReader._enqueue(buffer);
      } else {
        this._queuedChunks.push(buffer);
      }
    } else {
      const found = this._rangeReaders.some(function (rangeReader) {
        if (rangeReader._begin !== args.begin) {
          return false;
        }

        rangeReader._enqueue(buffer);

        return true;
      });

      (0, _util.assert)(found, "_onReceiveData - no `PDFDataTransportStreamRangeReader` instance found.");
    }
  }

  get _progressiveDataLength() {
    var _this$_fullRequestRea, _this$_fullRequestRea2;

    return (_this$_fullRequestRea = (_this$_fullRequestRea2 = this._fullRequestReader) === null || _this$_fullRequestRea2 === void 0 ? void 0 : _this$_fullRequestRea2._loaded) !== null && _this$_fullRequestRea !== void 0 ? _this$_fullRequestRea : 0;
  }

  _onProgress(evt) {
    if (evt.total === undefined) {
      const firstReader = this._rangeReaders[0];

      if (firstReader !== null && firstReader !== void 0 && firstReader.onProgress) {
        firstReader.onProgress({
          loaded: evt.loaded
        });
      }
    } else {
      const fullReader = this._fullRequestReader;

      if (fullReader !== null && fullReader !== void 0 && fullReader.onProgress) {
        fullReader.onProgress({
          loaded: evt.loaded,
          total: evt.total
        });
      }
    }
  }

  _onProgressiveDone() {
    if (this._fullRequestReader) {
      this._fullRequestReader.progressiveDone();
    }

    this._progressiveDone = true;
  }

  _removeRangeReader(reader) {
    const i = this._rangeReaders.indexOf(reader);

    if (i >= 0) {
      this._rangeReaders.splice(i, 1);
    }
  }

  getFullReader() {
    (0, _util.assert)(!this._fullRequestReader, "PDFDataTransportStream.getFullReader can only be called once.");
    const queuedChunks = this._queuedChunks;
    this._queuedChunks = null;
    return new PDFDataTransportStreamReader(this, queuedChunks, this._progressiveDone, this._contentDispositionFilename);
  }

  getRangeReader(begin, end) {
    if (end <= this._progressiveDataLength) {
      return null;
    }

    const reader = new PDFDataTransportStreamRangeReader(this, begin, end);

    this._pdfDataRangeTransport.requestDataRange(begin, end);

    this._rangeReaders.push(reader);

    return reader;
  }

  cancelAllRequests(reason) {
    if (this._fullRequestReader) {
      this._fullRequestReader.cancel(reason);
    }

    for (const reader of this._rangeReaders.slice(0)) {
      reader.cancel(reason);
    }

    this._pdfDataRangeTransport.abort();
  }

}

exports.PDFDataTransportStream = PDFDataTransportStream;

class PDFDataTransportStreamReader {
  constructor(stream, queuedChunks) {
    let progressiveDone = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
    let contentDispositionFilename = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;
    this._stream = stream;
    this._done = progressiveDone || false;
    this._filename = (0, _display_utils.isPdfFile)(contentDispositionFilename) ? contentDispositionFilename : null;
    this._queuedChunks = queuedChunks || [];
    this._loaded = 0;

    for (const chunk of this._queuedChunks) {
      this._loaded += chunk.byteLength;
    }

    this._requests = [];
    this._headersReady = Promise.resolve();
    stream._fullRequestReader = this;
    this.onProgress = null;
  }

  _enqueue(chunk) {
    if (this._done) {
      return;
    }

    if (this._requests.length > 0) {
      const requestCapability = this._requests.shift();

      requestCapability.resolve({
        value: chunk,
        done: false
      });
    } else {
      this._queuedChunks.push(chunk);
    }

    this._loaded += chunk.byteLength;
  }

  get headersReady() {
    return this._headersReady;
  }

  get filename() {
    return this._filename;
  }

  get isRangeSupported() {
    return this._stream._isRangeSupported;
  }

  get isStreamingSupported() {
    return this._stream._isStreamingSupported;
  }

  get contentLength() {
    return this._stream._contentLength;
  }

  async read() {
    if (this._queuedChunks.length > 0) {
      const chunk = this._queuedChunks.shift();

      return {
        value: chunk,
        done: false
      };
    }

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    const requestCapability = (0, _util.createPromiseCapability)();

    this._requests.push(requestCapability);

    return requestCapability.promise;
  }

  cancel(reason) {
    this._done = true;

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;
  }

  progressiveDone() {
    if (this._done) {
      return;
    }

    this._done = true;
  }

}

class PDFDataTransportStreamRangeReader {
  constructor(stream, begin, end) {
    this._stream = stream;
    this._begin = begin;
    this._end = end;
    this._queuedChunk = null;
    this._requests = [];
    this._done = false;
    this.onProgress = null;
  }

  _enqueue(chunk) {
    if (this._done) {
      return;
    }

    if (this._requests.length === 0) {
      this._queuedChunk = chunk;
    } else {
      const requestsCapability = this._requests.shift();

      requestsCapability.resolve({
        value: chunk,
        done: false
      });

      for (const requestCapability of this._requests) {
        requestCapability.resolve({
          value: undefined,
          done: true
        });
      }

      this._requests.length = 0;
    }

    this._done = true;

    this._stream._removeRangeReader(this);
  }

  get isStreamingSupported() {
    return false;
  }

  async read() {
    if (this._queuedChunk) {
      const chunk = this._queuedChunk;
      this._queuedChunk = null;
      return {
        value: chunk,
        done: false
      };
    }

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    const requestCapability = (0, _util.createPromiseCapability)();

    this._requests.push(requestCapability);

    return requestCapability.promise;
  }

  cancel(reason) {
    this._done = true;

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;

    this._stream._removeRangeReader(this);
  }

}

/***/ }),
/* 145 */
/***/ ((__unused_webpack_module, exports) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.XfaText = void 0;

class XfaText {
  static textContent(xfa) {
    const items = [];
    const output = {
      items,
      styles: Object.create(null)
    };

    function walk(node) {
      var _node$attributes;

      if (!node) {
        return;
      }

      let str = null;
      const name = node.name;

      if (name === "#text") {
        str = node.value;
      } else if (!XfaText.shouldBuildText(name)) {
        return;
      } else if (node !== null && node !== void 0 && (_node$attributes = node.attributes) !== null && _node$attributes !== void 0 && _node$attributes.textContent) {
        str = node.attributes.textContent;
      } else if (node.value) {
        str = node.value;
      }

      if (str !== null) {
        items.push({
          str
        });
      }

      if (!node.children) {
        return;
      }

      for (const child of node.children) {
        walk(child);
      }
    }

    walk(xfa);
    return output;
  }

  static shouldBuildText(name) {
    return !(name === "textarea" || name === "input" || name === "option" || name === "select");
  }

}

exports.XfaText = XfaText;

/***/ }),
/* 146 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.NodeStandardFontDataFactory = exports.NodeCanvasFactory = exports.NodeCMapReaderFactory = void 0;

var _base_factory = __w_pdfjs_require__(134);

;

const fetchData = function (url) {
  return new Promise((resolve, reject) => {
    const fs = require("fs");

    fs.readFile(url, (error, data) => {
      if (error || !data) {
        reject(new Error(error));
        return;
      }

      resolve(new Uint8Array(data));
    });
  });
};

class NodeCanvasFactory extends _base_factory.BaseCanvasFactory {
  _createCanvas(width, height) {
    const Canvas = require("canvas");

    return Canvas.createCanvas(width, height);
  }

}

exports.NodeCanvasFactory = NodeCanvasFactory;

class NodeCMapReaderFactory extends _base_factory.BaseCMapReaderFactory {
  _fetchData(url, compressionType) {
    return fetchData(url).then(data => {
      return {
        cMapData: data,
        compressionType
      };
    });
  }

}

exports.NodeCMapReaderFactory = NodeCMapReaderFactory;

class NodeStandardFontDataFactory extends _base_factory.BaseStandardFontDataFactory {
  _fetchData(url) {
    return fetchData(url);
  }

}

exports.NodeStandardFontDataFactory = NodeStandardFontDataFactory;

/***/ }),
/* 147 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.AnnotationEditorLayer = void 0;

var _tools = __w_pdfjs_require__(132);

var _util = __w_pdfjs_require__(1);

var _freetext = __w_pdfjs_require__(148);

var _ink = __w_pdfjs_require__(149);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

var _accessibilityManager = /*#__PURE__*/new WeakMap();

var _allowClick = /*#__PURE__*/new WeakMap();

var _boundPointerup = /*#__PURE__*/new WeakMap();

var _boundPointerdown = /*#__PURE__*/new WeakMap();

var _editors = /*#__PURE__*/new WeakMap();

var _hadPointerDown = /*#__PURE__*/new WeakMap();

var _isCleaningUp = /*#__PURE__*/new WeakMap();

var _uiManager = /*#__PURE__*/new WeakMap();

var _changeParent = /*#__PURE__*/new WeakSet();

var _createNewEditor = /*#__PURE__*/new WeakSet();

var _createAndAddNewEditor = /*#__PURE__*/new WeakSet();

var _cleanup = /*#__PURE__*/new WeakSet();

class AnnotationEditorLayer {
  constructor(options) {
    _classPrivateMethodInitSpec(this, _cleanup);

    _classPrivateMethodInitSpec(this, _createAndAddNewEditor);

    _classPrivateMethodInitSpec(this, _createNewEditor);

    _classPrivateMethodInitSpec(this, _changeParent);

    _classPrivateFieldInitSpec(this, _accessibilityManager, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldInitSpec(this, _allowClick, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _boundPointerup, {
      writable: true,
      value: this.pointerup.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundPointerdown, {
      writable: true,
      value: this.pointerdown.bind(this)
    });

    _classPrivateFieldInitSpec(this, _editors, {
      writable: true,
      value: new Map()
    });

    _classPrivateFieldInitSpec(this, _hadPointerDown, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _isCleaningUp, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _uiManager, {
      writable: true,
      value: void 0
    });

    if (!AnnotationEditorLayer._initialized) {
      AnnotationEditorLayer._initialized = true;

      _freetext.FreeTextEditor.initialize(options.l10n);

      _ink.InkEditor.initialize(options.l10n);

      options.uiManager.registerEditorTypes([_freetext.FreeTextEditor, _ink.InkEditor]);
    }

    _classPrivateFieldSet(this, _uiManager, options.uiManager);

    this.annotationStorage = options.annotationStorage;
    this.pageIndex = options.pageIndex;
    this.div = options.div;

    _classPrivateFieldSet(this, _accessibilityManager, options.accessibilityManager);

    _classPrivateFieldGet(this, _uiManager).addLayer(this);
  }

  updateToolbar(mode) {
    _classPrivateFieldGet(this, _uiManager).updateToolbar(mode);
  }

  updateMode() {
    let mode = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : _classPrivateFieldGet(this, _uiManager).getMode();

    _classPrivateMethodGet(this, _cleanup, _cleanup2).call(this);

    if (mode === _util.AnnotationEditorType.INK) {
      this.addInkEditorIfNeeded(false);
      this.disableClick();
    } else {
      this.enableClick();
    }

    _classPrivateFieldGet(this, _uiManager).unselectAll();
  }

  addInkEditorIfNeeded(isCommitting) {
    if (!isCommitting && _classPrivateFieldGet(this, _uiManager).getMode() !== _util.AnnotationEditorType.INK) {
      return;
    }

    if (!isCommitting) {
      for (const editor of _classPrivateFieldGet(this, _editors).values()) {
        if (editor.isEmpty()) {
          editor.setInBackground();
          return;
        }
      }
    }

    const editor = _classPrivateMethodGet(this, _createAndAddNewEditor, _createAndAddNewEditor2).call(this, {
      offsetX: 0,
      offsetY: 0
    });

    editor.setInBackground();
  }

  setEditingState(isEditing) {
    _classPrivateFieldGet(this, _uiManager).setEditingState(isEditing);
  }

  addCommands(params) {
    _classPrivateFieldGet(this, _uiManager).addCommands(params);
  }

  enable() {
    this.div.style.pointerEvents = "auto";

    for (const editor of _classPrivateFieldGet(this, _editors).values()) {
      editor.enableEditing();
    }
  }

  disable() {
    this.div.style.pointerEvents = "none";

    for (const editor of _classPrivateFieldGet(this, _editors).values()) {
      editor.disableEditing();
    }
  }

  setActiveEditor(editor) {
    const currentActive = _classPrivateFieldGet(this, _uiManager).getActive();

    if (currentActive === editor) {
      return;
    }

    _classPrivateFieldGet(this, _uiManager).setActiveEditor(editor);
  }

  enableClick() {
    this.div.addEventListener("pointerdown", _classPrivateFieldGet(this, _boundPointerdown));
    this.div.addEventListener("pointerup", _classPrivateFieldGet(this, _boundPointerup));
  }

  disableClick() {
    this.div.removeEventListener("pointerdown", _classPrivateFieldGet(this, _boundPointerdown));
    this.div.removeEventListener("pointerup", _classPrivateFieldGet(this, _boundPointerup));
  }

  attach(editor) {
    _classPrivateFieldGet(this, _editors).set(editor.id, editor);
  }

  detach(editor) {
    var _classPrivateFieldGet2;

    _classPrivateFieldGet(this, _editors).delete(editor.id);

    (_classPrivateFieldGet2 = _classPrivateFieldGet(this, _accessibilityManager)) === null || _classPrivateFieldGet2 === void 0 ? void 0 : _classPrivateFieldGet2.removePointerInTextLayer(editor.contentDiv);
  }

  remove(editor) {
    _classPrivateFieldGet(this, _uiManager).removeEditor(editor);

    this.detach(editor);
    this.annotationStorage.remove(editor.id);
    editor.div.style.display = "none";
    setTimeout(() => {
      editor.div.style.display = "";
      editor.div.remove();
      editor.isAttachedToDOM = false;

      if (document.activeElement === document.body) {
        _classPrivateFieldGet(this, _uiManager).focusMainContainer();
      }
    }, 0);

    if (!_classPrivateFieldGet(this, _isCleaningUp)) {
      this.addInkEditorIfNeeded(false);
    }
  }

  add(editor) {
    _classPrivateMethodGet(this, _changeParent, _changeParent2).call(this, editor);

    _classPrivateFieldGet(this, _uiManager).addEditor(editor);

    this.attach(editor);

    if (!editor.isAttachedToDOM) {
      const div = editor.render();
      this.div.append(div);
      editor.isAttachedToDOM = true;
    }

    this.moveEditorInDOM(editor);
    editor.onceAdded();
    this.addToAnnotationStorage(editor);
  }

  moveEditorInDOM(editor) {
    var _classPrivateFieldGet3;

    (_classPrivateFieldGet3 = _classPrivateFieldGet(this, _accessibilityManager)) === null || _classPrivateFieldGet3 === void 0 ? void 0 : _classPrivateFieldGet3.moveElementInDOM(this.div, editor.div, editor.contentDiv, true);
  }

  addToAnnotationStorage(editor) {
    if (!editor.isEmpty() && !this.annotationStorage.has(editor.id)) {
      this.annotationStorage.setValue(editor.id, editor);
    }
  }

  addOrRebuild(editor) {
    if (editor.needsToBeRebuilt()) {
      editor.rebuild();
    } else {
      this.add(editor);
    }
  }

  addANewEditor(editor) {
    const cmd = () => {
      this.addOrRebuild(editor);
    };

    const undo = () => {
      editor.remove();
    };

    this.addCommands({
      cmd,
      undo,
      mustExec: true
    });
  }

  addUndoableEditor(editor) {
    const cmd = () => {
      this.addOrRebuild(editor);
    };

    const undo = () => {
      editor.remove();
    };

    this.addCommands({
      cmd,
      undo,
      mustExec: false
    });
  }

  getNextId() {
    return _classPrivateFieldGet(this, _uiManager).getId();
  }

  deserialize(data) {
    switch (data.annotationType) {
      case _util.AnnotationEditorType.FREETEXT:
        return _freetext.FreeTextEditor.deserialize(data, this);

      case _util.AnnotationEditorType.INK:
        return _ink.InkEditor.deserialize(data, this);
    }

    return null;
  }

  setSelected(editor) {
    _classPrivateFieldGet(this, _uiManager).setSelected(editor);
  }

  toggleSelected(editor) {
    _classPrivateFieldGet(this, _uiManager).toggleSelected(editor);
  }

  isSelected(editor) {
    return _classPrivateFieldGet(this, _uiManager).isSelected(editor);
  }

  unselect(editor) {
    _classPrivateFieldGet(this, _uiManager).unselect(editor);
  }

  pointerup(event) {
    const isMac = _tools.KeyboardManager.platform.isMac;

    if (event.button !== 0 || event.ctrlKey && isMac) {
      return;
    }

    if (event.target !== this.div) {
      return;
    }

    if (!_classPrivateFieldGet(this, _hadPointerDown)) {
      return;
    }

    _classPrivateFieldSet(this, _hadPointerDown, false);

    if (!_classPrivateFieldGet(this, _allowClick)) {
      _classPrivateFieldSet(this, _allowClick, true);

      return;
    }

    _classPrivateMethodGet(this, _createAndAddNewEditor, _createAndAddNewEditor2).call(this, event);
  }

  pointerdown(event) {
    const isMac = _tools.KeyboardManager.platform.isMac;

    if (event.button !== 0 || event.ctrlKey && isMac) {
      return;
    }

    if (event.target !== this.div) {
      return;
    }

    _classPrivateFieldSet(this, _hadPointerDown, true);

    const editor = _classPrivateFieldGet(this, _uiManager).getActive();

    _classPrivateFieldSet(this, _allowClick, !editor || editor.isEmpty());
  }

  drop(event) {
    const id = event.dataTransfer.getData("text/plain");

    const editor = _classPrivateFieldGet(this, _uiManager).getEditor(id);

    if (!editor) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    _classPrivateMethodGet(this, _changeParent, _changeParent2).call(this, editor);

    const rect = this.div.getBoundingClientRect();
    const endX = event.clientX - rect.x;
    const endY = event.clientY - rect.y;
    editor.translate(endX - editor.startX, endY - editor.startY);
    this.moveEditorInDOM(editor);
    editor.div.focus();
  }

  dragover(event) {
    event.preventDefault();
  }

  destroy() {
    var _classPrivateFieldGet4;

    if (((_classPrivateFieldGet4 = _classPrivateFieldGet(this, _uiManager).getActive()) === null || _classPrivateFieldGet4 === void 0 ? void 0 : _classPrivateFieldGet4.parent) === this) {
      _classPrivateFieldGet(this, _uiManager).setActiveEditor(null);
    }

    for (const editor of _classPrivateFieldGet(this, _editors).values()) {
      var _classPrivateFieldGet5;

      (_classPrivateFieldGet5 = _classPrivateFieldGet(this, _accessibilityManager)) === null || _classPrivateFieldGet5 === void 0 ? void 0 : _classPrivateFieldGet5.removePointerInTextLayer(editor.contentDiv);
      editor.isAttachedToDOM = false;
      editor.div.remove();
      editor.parent = null;
    }

    this.div = null;

    _classPrivateFieldGet(this, _editors).clear();

    _classPrivateFieldGet(this, _uiManager).removeLayer(this);
  }

  render(parameters) {
    this.viewport = parameters.viewport;
    (0, _tools.bindEvents)(this, this.div, ["dragover", "drop"]);
    this.setDimensions();

    for (const editor of _classPrivateFieldGet(this, _uiManager).getEditors(this.pageIndex)) {
      this.add(editor);
    }

    this.updateMode();
  }

  update(parameters) {
    this.viewport = parameters.viewport;
    this.setDimensions();
    this.updateMode();
  }

  get scaleFactor() {
    return this.viewport.scale;
  }

  get pageDimensions() {
    const [pageLLx, pageLLy, pageURx, pageURy] = this.viewport.viewBox;
    const width = pageURx - pageLLx;
    const height = pageURy - pageLLy;
    return [width, height];
  }

  get viewportBaseDimensions() {
    const {
      width,
      height,
      rotation
    } = this.viewport;
    return rotation % 180 === 0 ? [width, height] : [height, width];
  }

  setDimensions() {
    const {
      width,
      height,
      rotation
    } = this.viewport;
    const flipOrientation = rotation % 180 !== 0,
          widthStr = Math.floor(width) + "px",
          heightStr = Math.floor(height) + "px";
    this.div.style.width = flipOrientation ? heightStr : widthStr;
    this.div.style.height = flipOrientation ? widthStr : heightStr;
    this.div.setAttribute("data-main-rotation", rotation);
  }

}

exports.AnnotationEditorLayer = AnnotationEditorLayer;

function _changeParent2(editor) {
  var _editor$parent;

  if (editor.parent === this) {
    return;
  }

  this.attach(editor);
  editor.pageIndex = this.pageIndex;
  (_editor$parent = editor.parent) === null || _editor$parent === void 0 ? void 0 : _editor$parent.detach(editor);
  editor.parent = this;

  if (editor.div && editor.isAttachedToDOM) {
    editor.div.remove();
    this.div.append(editor.div);
  }
}

function _createNewEditor2(params) {
  switch (_classPrivateFieldGet(this, _uiManager).getMode()) {
    case _util.AnnotationEditorType.FREETEXT:
      return new _freetext.FreeTextEditor(params);

    case _util.AnnotationEditorType.INK:
      return new _ink.InkEditor(params);
  }

  return null;
}

function _createAndAddNewEditor2(event) {
  const id = this.getNextId();

  const editor = _classPrivateMethodGet(this, _createNewEditor, _createNewEditor2).call(this, {
    parent: this,
    id,
    x: event.offsetX,
    y: event.offsetY
  });

  if (editor) {
    this.add(editor);
  }

  return editor;
}

function _cleanup2() {
  _classPrivateFieldSet(this, _isCleaningUp, true);

  for (const editor of _classPrivateFieldGet(this, _editors).values()) {
    if (editor.isEmpty()) {
      editor.remove();
    }
  }

  _classPrivateFieldSet(this, _isCleaningUp, false);
}

_defineProperty(AnnotationEditorLayer, "_initialized", false);

/***/ }),
/* 148 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.FreeTextEditor = void 0;

var _util = __w_pdfjs_require__(1);

var _tools = __w_pdfjs_require__(132);

var _editor = __w_pdfjs_require__(131);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

var _boundEditorDivBlur = /*#__PURE__*/new WeakMap();

var _boundEditorDivFocus = /*#__PURE__*/new WeakMap();

var _boundEditorDivKeydown = /*#__PURE__*/new WeakMap();

var _color = /*#__PURE__*/new WeakMap();

var _content = /*#__PURE__*/new WeakMap();

var _hasAlreadyBeenCommitted = /*#__PURE__*/new WeakMap();

var _fontSize = /*#__PURE__*/new WeakMap();

var _updateFontSize = /*#__PURE__*/new WeakSet();

var _updateColor = /*#__PURE__*/new WeakSet();

var _extractText = /*#__PURE__*/new WeakSet();

var _setEditorDimensions = /*#__PURE__*/new WeakSet();

class FreeTextEditor extends _editor.AnnotationEditor {
  constructor(params) {
    super({ ...params,
      name: "freeTextEditor"
    });

    _classPrivateMethodInitSpec(this, _setEditorDimensions);

    _classPrivateMethodInitSpec(this, _extractText);

    _classPrivateMethodInitSpec(this, _updateColor);

    _classPrivateMethodInitSpec(this, _updateFontSize);

    _classPrivateFieldInitSpec(this, _boundEditorDivBlur, {
      writable: true,
      value: this.editorDivBlur.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundEditorDivFocus, {
      writable: true,
      value: this.editorDivFocus.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundEditorDivKeydown, {
      writable: true,
      value: this.editorDivKeydown.bind(this)
    });

    _classPrivateFieldInitSpec(this, _color, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldInitSpec(this, _content, {
      writable: true,
      value: ""
    });

    _classPrivateFieldInitSpec(this, _hasAlreadyBeenCommitted, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _fontSize, {
      writable: true,
      value: void 0
    });

    _classPrivateFieldSet(this, _color, params.color || FreeTextEditor._defaultColor || _editor.AnnotationEditor._defaultLineColor);

    _classPrivateFieldSet(this, _fontSize, params.fontSize || FreeTextEditor._defaultFontSize);
  }

  static initialize(l10n) {
    this._l10nPromise = new Map(["free_text_default_content", "editor_free_text_aria_label"].map(str => [str, l10n.get(str)]));
    const style = getComputedStyle(document.documentElement);
    this._internalPadding = parseFloat(style.getPropertyValue("--freetext-padding"));
  }

  static updateDefaultParams(type, value) {
    switch (type) {
      case _util.AnnotationEditorParamsType.FREETEXT_SIZE:
        FreeTextEditor._defaultFontSize = value;
        break;

      case _util.AnnotationEditorParamsType.FREETEXT_COLOR:
        FreeTextEditor._defaultColor = value;
        break;
    }
  }

  updateParams(type, value) {
    switch (type) {
      case _util.AnnotationEditorParamsType.FREETEXT_SIZE:
        _classPrivateMethodGet(this, _updateFontSize, _updateFontSize2).call(this, value);

        break;

      case _util.AnnotationEditorParamsType.FREETEXT_COLOR:
        _classPrivateMethodGet(this, _updateColor, _updateColor2).call(this, value);

        break;
    }
  }

  static get defaultPropertiesToUpdate() {
    return [[_util.AnnotationEditorParamsType.FREETEXT_SIZE, FreeTextEditor._defaultFontSize], [_util.AnnotationEditorParamsType.FREETEXT_COLOR, FreeTextEditor._defaultColor || _editor.AnnotationEditor._defaultLineColor]];
  }

  get propertiesToUpdate() {
    return [[_util.AnnotationEditorParamsType.FREETEXT_SIZE, _classPrivateFieldGet(this, _fontSize)], [_util.AnnotationEditorParamsType.FREETEXT_COLOR, _classPrivateFieldGet(this, _color)]];
  }

  getInitialTranslation() {
    return [-FreeTextEditor._internalPadding * this.parent.scaleFactor, -(FreeTextEditor._internalPadding + _classPrivateFieldGet(this, _fontSize)) * this.parent.scaleFactor];
  }

  rebuild() {
    super.rebuild();

    if (this.div === null) {
      return;
    }

    if (!this.isAttachedToDOM) {
      this.parent.add(this);
    }
  }

  enableEditMode() {
    if (this.isInEditMode()) {
      return;
    }

    this.parent.setEditingState(false);
    this.parent.updateToolbar(_util.AnnotationEditorType.FREETEXT);
    super.enableEditMode();
    this.enableEditing();
    this.overlayDiv.classList.remove("enabled");
    this.editorDiv.contentEditable = true;
    this.div.draggable = false;
    this.editorDiv.addEventListener("keydown", _classPrivateFieldGet(this, _boundEditorDivKeydown));
    this.editorDiv.addEventListener("focus", _classPrivateFieldGet(this, _boundEditorDivFocus));
    this.editorDiv.addEventListener("blur", _classPrivateFieldGet(this, _boundEditorDivBlur));
  }

  disableEditMode() {
    if (!this.isInEditMode()) {
      return;
    }

    this.parent.setEditingState(true);
    super.disableEditMode();
    this.disableEditing();
    this.overlayDiv.classList.add("enabled");
    this.editorDiv.contentEditable = false;
    this.div.draggable = true;
    this.editorDiv.removeEventListener("keydown", _classPrivateFieldGet(this, _boundEditorDivKeydown));
    this.editorDiv.removeEventListener("focus", _classPrivateFieldGet(this, _boundEditorDivFocus));
    this.editorDiv.removeEventListener("blur", _classPrivateFieldGet(this, _boundEditorDivBlur));
    this.div.focus();
    this.isEditing = false;
  }

  focusin(event) {
    super.focusin(event);

    if (event.target !== this.editorDiv) {
      this.editorDiv.focus();
    }
  }

  onceAdded() {
    if (this.width) {
      return;
    }

    this.enableEditMode();
    this.editorDiv.focus();
  }

  isEmpty() {
    return !this.editorDiv || this.editorDiv.innerText.trim() === "";
  }

  remove() {
    this.isEditing = false;
    this.parent.setEditingState(true);
    super.remove();
  }

  commit() {
    super.commit();

    if (!_classPrivateFieldGet(this, _hasAlreadyBeenCommitted)) {
      _classPrivateFieldSet(this, _hasAlreadyBeenCommitted, true);

      this.parent.addUndoableEditor(this);
    }

    this.disableEditMode();

    _classPrivateFieldSet(this, _content, _classPrivateMethodGet(this, _extractText, _extractText2).call(this).trimEnd());

    _classPrivateMethodGet(this, _setEditorDimensions, _setEditorDimensions2).call(this);
  }

  shouldGetKeyboardEvents() {
    return this.isInEditMode();
  }

  dblclick(event) {
    this.enableEditMode();
    this.editorDiv.focus();
  }

  keydown(event) {
    if (event.target === this.div && event.key === "Enter") {
      this.enableEditMode();
      this.editorDiv.focus();
    }
  }

  editorDivKeydown(event) {
    FreeTextEditor._keyboardManager.exec(this, event);
  }

  editorDivFocus(event) {
    this.isEditing = true;
  }

  editorDivBlur(event) {
    this.isEditing = false;
  }

  disableEditing() {
    this.editorDiv.setAttribute("role", "comment");
    this.editorDiv.removeAttribute("aria-multiline");
  }

  enableEditing() {
    this.editorDiv.setAttribute("role", "textbox");
    this.editorDiv.setAttribute("aria-multiline", true);
  }

  render() {
    if (this.div) {
      return this.div;
    }

    let baseX, baseY;

    if (this.width) {
      baseX = this.x;
      baseY = this.y;
    }

    super.render();
    this.editorDiv = document.createElement("div");
    this.editorDiv.className = "internal";
    this.editorDiv.setAttribute("id", `${this.id}-editor`);
    this.enableEditing();

    FreeTextEditor._l10nPromise.get("editor_free_text_aria_label").then(msg => {
      var _this$editorDiv;

      return (_this$editorDiv = this.editorDiv) === null || _this$editorDiv === void 0 ? void 0 : _this$editorDiv.setAttribute("aria-label", msg);
    });

    FreeTextEditor._l10nPromise.get("free_text_default_content").then(msg => {
      var _this$editorDiv2;

      return (_this$editorDiv2 = this.editorDiv) === null || _this$editorDiv2 === void 0 ? void 0 : _this$editorDiv2.setAttribute("default-content", msg);
    });

    this.editorDiv.contentEditable = true;
    const {
      style
    } = this.editorDiv;
    style.fontSize = `calc(${_classPrivateFieldGet(this, _fontSize)}px * var(--scale-factor))`;
    style.color = _classPrivateFieldGet(this, _color);
    this.div.append(this.editorDiv);
    this.overlayDiv = document.createElement("div");
    this.overlayDiv.classList.add("overlay", "enabled");
    this.div.append(this.overlayDiv);
    (0, _tools.bindEvents)(this, this.div, ["dblclick", "keydown"]);

    if (this.width) {
      const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
      this.setAt(baseX * parentWidth, baseY * parentHeight, this.width * parentWidth, this.height * parentHeight);

      for (const line of _classPrivateFieldGet(this, _content).split("\n")) {
        const div = document.createElement("div");
        div.append(line ? document.createTextNode(line) : document.createElement("br"));
        this.editorDiv.append(div);
      }

      this.div.draggable = true;
      this.editorDiv.contentEditable = false;
    } else {
      this.div.draggable = false;
      this.editorDiv.contentEditable = true;
    }

    return this.div;
  }

  get contentDiv() {
    return this.editorDiv;
  }

  static deserialize(data, parent) {
    const editor = super.deserialize(data, parent);

    _classPrivateFieldSet(editor, _fontSize, data.fontSize);

    _classPrivateFieldSet(editor, _color, _util.Util.makeHexColor(...data.color));

    _classPrivateFieldSet(editor, _content, data.value);

    return editor;
  }

  serialize() {
    if (this.isEmpty()) {
      return null;
    }

    const padding = FreeTextEditor._internalPadding * this.parent.scaleFactor;
    const rect = this.getRect(padding, padding);

    const color = _editor.AnnotationEditor._colorManager.convert(getComputedStyle(this.editorDiv).color);

    return {
      annotationType: _util.AnnotationEditorType.FREETEXT,
      color,
      fontSize: _classPrivateFieldGet(this, _fontSize),
      value: _classPrivateFieldGet(this, _content),
      pageIndex: this.parent.pageIndex,
      rect,
      rotation: this.rotation
    };
  }

}

exports.FreeTextEditor = FreeTextEditor;

function _updateFontSize2(fontSize) {
  const setFontsize = size => {
    this.editorDiv.style.fontSize = `calc(${size}px * var(--scale-factor))`;
    this.translate(0, -(size - _classPrivateFieldGet(this, _fontSize)) * this.parent.scaleFactor);

    _classPrivateFieldSet(this, _fontSize, size);

    _classPrivateMethodGet(this, _setEditorDimensions, _setEditorDimensions2).call(this);
  };

  const savedFontsize = _classPrivateFieldGet(this, _fontSize);

  this.parent.addCommands({
    cmd: () => {
      setFontsize(fontSize);
    },
    undo: () => {
      setFontsize(savedFontsize);
    },
    mustExec: true,
    type: _util.AnnotationEditorParamsType.FREETEXT_SIZE,
    overwriteIfSameType: true,
    keepUndo: true
  });
}

function _updateColor2(color) {
  const savedColor = _classPrivateFieldGet(this, _color);

  this.parent.addCommands({
    cmd: () => {
      _classPrivateFieldSet(this, _color, color);

      this.editorDiv.style.color = color;
    },
    undo: () => {
      _classPrivateFieldSet(this, _color, savedColor);

      this.editorDiv.style.color = savedColor;
    },
    mustExec: true,
    type: _util.AnnotationEditorParamsType.FREETEXT_COLOR,
    overwriteIfSameType: true,
    keepUndo: true
  });
}

function _extractText2() {
  const divs = this.editorDiv.getElementsByTagName("div");

  if (divs.length === 0) {
    return this.editorDiv.innerText;
  }

  const buffer = [];

  for (let i = 0, ii = divs.length; i < ii; i++) {
    const div = divs[i];
    const first = div.firstChild;

    if ((first === null || first === void 0 ? void 0 : first.nodeName) === "#text") {
      buffer.push(first.data);
    } else {
      buffer.push("");
    }
  }

  return buffer.join("\n");
}

function _setEditorDimensions2() {
  const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
  const rect = this.div.getBoundingClientRect();
  this.width = rect.width / parentWidth;
  this.height = rect.height / parentHeight;
}

_defineProperty(FreeTextEditor, "_freeTextDefaultContent", "");

_defineProperty(FreeTextEditor, "_l10nPromise", void 0);

_defineProperty(FreeTextEditor, "_internalPadding", 0);

_defineProperty(FreeTextEditor, "_defaultColor", null);

_defineProperty(FreeTextEditor, "_defaultFontSize", 10);

_defineProperty(FreeTextEditor, "_keyboardManager", new _tools.KeyboardManager([[["ctrl+Enter", "mac+meta+Enter", "Escape", "mac+Escape"], FreeTextEditor.prototype.commitOrRemove]]));

_defineProperty(FreeTextEditor, "_type", "freetext");

/***/ }),
/* 149 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.InkEditor = void 0;
Object.defineProperty(exports, "fitCurve", ({
  enumerable: true,
  get: function () {
    return _pdfjsFitCurve.fitCurve;
  }
}));

var _util = __w_pdfjs_require__(1);

var _editor = __w_pdfjs_require__(131);

var _pdfjsFitCurve = __w_pdfjs_require__(150);

var _tools = __w_pdfjs_require__(132);

function _classPrivateMethodInitSpec(obj, privateSet) { _checkPrivateRedeclaration(obj, privateSet); privateSet.add(obj); }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classPrivateFieldInitSpec(obj, privateMap, value) { _checkPrivateRedeclaration(obj, privateMap); privateMap.set(obj, value); }

function _checkPrivateRedeclaration(obj, privateCollection) { if (privateCollection.has(obj)) { throw new TypeError("Cannot initialize the same private elements twice on an object"); } }

function _classStaticPrivateMethodGet(receiver, classConstructor, method) { _classCheckPrivateStaticAccess(receiver, classConstructor); return method; }

function _classCheckPrivateStaticAccess(receiver, classConstructor) { if (receiver !== classConstructor) { throw new TypeError("Private static access of wrong provenance"); } }

function _classPrivateFieldSet(receiver, privateMap, value) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "set"); _classApplyDescriptorSet(receiver, descriptor, value); return value; }

function _classApplyDescriptorSet(receiver, descriptor, value) { if (descriptor.set) { descriptor.set.call(receiver, value); } else { if (!descriptor.writable) { throw new TypeError("attempted to set read only private field"); } descriptor.value = value; } }

function _classPrivateFieldGet(receiver, privateMap) { var descriptor = _classExtractFieldDescriptor(receiver, privateMap, "get"); return _classApplyDescriptorGet(receiver, descriptor); }

function _classExtractFieldDescriptor(receiver, privateMap, action) { if (!privateMap.has(receiver)) { throw new TypeError("attempted to " + action + " private field on non-instance"); } return privateMap.get(receiver); }

function _classApplyDescriptorGet(receiver, descriptor) { if (descriptor.get) { return descriptor.get.call(receiver); } return descriptor.value; }

function _classPrivateMethodGet(receiver, privateSet, fn) { if (!privateSet.has(receiver)) { throw new TypeError("attempted to get private field on non-instance"); } return fn; }

const RESIZER_SIZE = 16;

var _aspectRatio = /*#__PURE__*/new WeakMap();

var _baseHeight = /*#__PURE__*/new WeakMap();

var _baseWidth = /*#__PURE__*/new WeakMap();

var _boundCanvasPointermove = /*#__PURE__*/new WeakMap();

var _boundCanvasPointerleave = /*#__PURE__*/new WeakMap();

var _boundCanvasPointerup = /*#__PURE__*/new WeakMap();

var _boundCanvasPointerdown = /*#__PURE__*/new WeakMap();

var _disableEditing = /*#__PURE__*/new WeakMap();

var _isCanvasInitialized = /*#__PURE__*/new WeakMap();

var _lastPoint = /*#__PURE__*/new WeakMap();

var _observer = /*#__PURE__*/new WeakMap();

var _realWidth = /*#__PURE__*/new WeakMap();

var _realHeight = /*#__PURE__*/new WeakMap();

var _requestFrameCallback = /*#__PURE__*/new WeakMap();

var _updateThickness = /*#__PURE__*/new WeakSet();

var _updateColor = /*#__PURE__*/new WeakSet();

var _updateOpacity = /*#__PURE__*/new WeakSet();

var _getInitialBBox = /*#__PURE__*/new WeakSet();

var _setStroke = /*#__PURE__*/new WeakSet();

var _startDrawing = /*#__PURE__*/new WeakSet();

var _draw = /*#__PURE__*/new WeakSet();

var _stopDrawing = /*#__PURE__*/new WeakSet();

var _redraw = /*#__PURE__*/new WeakSet();

var _endDrawing = /*#__PURE__*/new WeakSet();

var _createCanvas = /*#__PURE__*/new WeakSet();

var _createObserver = /*#__PURE__*/new WeakSet();

var _setCanvasDims = /*#__PURE__*/new WeakSet();

var _setScaleFactor = /*#__PURE__*/new WeakSet();

var _updateTransform = /*#__PURE__*/new WeakSet();

var _serializePaths = /*#__PURE__*/new WeakSet();

var _extractPointsOnBezier = /*#__PURE__*/new WeakSet();

var _isAlmostFlat = /*#__PURE__*/new WeakSet();

var _getBbox = /*#__PURE__*/new WeakSet();

var _getPadding = /*#__PURE__*/new WeakSet();

var _fitToContent = /*#__PURE__*/new WeakSet();

var _setMinDims = /*#__PURE__*/new WeakSet();

class InkEditor extends _editor.AnnotationEditor {
  constructor(params) {
    super({ ...params,
      name: "inkEditor"
    });

    _classPrivateMethodInitSpec(this, _setMinDims);

    _classPrivateMethodInitSpec(this, _fitToContent);

    _classPrivateMethodInitSpec(this, _getPadding);

    _classPrivateMethodInitSpec(this, _getBbox);

    _classPrivateMethodInitSpec(this, _isAlmostFlat);

    _classPrivateMethodInitSpec(this, _extractPointsOnBezier);

    _classPrivateMethodInitSpec(this, _serializePaths);

    _classPrivateMethodInitSpec(this, _updateTransform);

    _classPrivateMethodInitSpec(this, _setScaleFactor);

    _classPrivateMethodInitSpec(this, _setCanvasDims);

    _classPrivateMethodInitSpec(this, _createObserver);

    _classPrivateMethodInitSpec(this, _createCanvas);

    _classPrivateMethodInitSpec(this, _endDrawing);

    _classPrivateMethodInitSpec(this, _redraw);

    _classPrivateMethodInitSpec(this, _stopDrawing);

    _classPrivateMethodInitSpec(this, _draw);

    _classPrivateMethodInitSpec(this, _startDrawing);

    _classPrivateMethodInitSpec(this, _setStroke);

    _classPrivateMethodInitSpec(this, _getInitialBBox);

    _classPrivateMethodInitSpec(this, _updateOpacity);

    _classPrivateMethodInitSpec(this, _updateColor);

    _classPrivateMethodInitSpec(this, _updateThickness);

    _classPrivateFieldInitSpec(this, _aspectRatio, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _baseHeight, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _baseWidth, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _boundCanvasPointermove, {
      writable: true,
      value: this.canvasPointermove.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundCanvasPointerleave, {
      writable: true,
      value: this.canvasPointerleave.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundCanvasPointerup, {
      writable: true,
      value: this.canvasPointerup.bind(this)
    });

    _classPrivateFieldInitSpec(this, _boundCanvasPointerdown, {
      writable: true,
      value: this.canvasPointerdown.bind(this)
    });

    _classPrivateFieldInitSpec(this, _disableEditing, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _isCanvasInitialized, {
      writable: true,
      value: false
    });

    _classPrivateFieldInitSpec(this, _lastPoint, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _observer, {
      writable: true,
      value: null
    });

    _classPrivateFieldInitSpec(this, _realWidth, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _realHeight, {
      writable: true,
      value: 0
    });

    _classPrivateFieldInitSpec(this, _requestFrameCallback, {
      writable: true,
      value: null
    });

    this.color = params.color || null;
    this.thickness = params.thickness || null;
    this.opacity = params.opacity || null;
    this.paths = [];
    this.bezierPath2D = [];
    this.currentPath = [];
    this.scaleFactor = 1;
    this.translationX = this.translationY = 0;
    this.x = 0;
    this.y = 0;
  }

  static initialize(l10n) {
    this._l10nPromise = new Map(["editor_ink_canvas_aria_label", "editor_ink_aria_label"].map(str => [str, l10n.get(str)]));
  }

  static updateDefaultParams(type, value) {
    switch (type) {
      case _util.AnnotationEditorParamsType.INK_THICKNESS:
        InkEditor._defaultThickness = value;
        break;

      case _util.AnnotationEditorParamsType.INK_COLOR:
        InkEditor._defaultColor = value;
        break;

      case _util.AnnotationEditorParamsType.INK_OPACITY:
        InkEditor._defaultOpacity = value / 100;
        break;
    }
  }

  updateParams(type, value) {
    switch (type) {
      case _util.AnnotationEditorParamsType.INK_THICKNESS:
        _classPrivateMethodGet(this, _updateThickness, _updateThickness2).call(this, value);

        break;

      case _util.AnnotationEditorParamsType.INK_COLOR:
        _classPrivateMethodGet(this, _updateColor, _updateColor2).call(this, value);

        break;

      case _util.AnnotationEditorParamsType.INK_OPACITY:
        _classPrivateMethodGet(this, _updateOpacity, _updateOpacity2).call(this, value);

        break;
    }
  }

  static get defaultPropertiesToUpdate() {
    return [[_util.AnnotationEditorParamsType.INK_THICKNESS, InkEditor._defaultThickness], [_util.AnnotationEditorParamsType.INK_COLOR, InkEditor._defaultColor || _editor.AnnotationEditor._defaultLineColor], [_util.AnnotationEditorParamsType.INK_OPACITY, Math.round(InkEditor._defaultOpacity * 100)]];
  }

  get propertiesToUpdate() {
    var _this$opacity;

    return [[_util.AnnotationEditorParamsType.INK_THICKNESS, this.thickness || InkEditor._defaultThickness], [_util.AnnotationEditorParamsType.INK_COLOR, this.color || InkEditor._defaultColor || _editor.AnnotationEditor._defaultLineColor], [_util.AnnotationEditorParamsType.INK_OPACITY, Math.round(100 * ((_this$opacity = this.opacity) !== null && _this$opacity !== void 0 ? _this$opacity : InkEditor._defaultOpacity))]];
  }

  rebuild() {
    super.rebuild();

    if (this.div === null) {
      return;
    }

    if (!this.canvas) {
      _classPrivateMethodGet(this, _createCanvas, _createCanvas2).call(this);

      _classPrivateMethodGet(this, _createObserver, _createObserver2).call(this);
    }

    if (!this.isAttachedToDOM) {
      this.parent.add(this);

      _classPrivateMethodGet(this, _setCanvasDims, _setCanvasDims2).call(this);
    }

    _classPrivateMethodGet(this, _fitToContent, _fitToContent2).call(this);
  }

  remove() {
    if (this.canvas === null) {
      return;
    }

    if (!this.isEmpty()) {
      this.commit();
    }

    this.canvas.width = this.canvas.height = 0;
    this.canvas.remove();
    this.canvas = null;

    _classPrivateFieldGet(this, _observer).disconnect();

    _classPrivateFieldSet(this, _observer, null);

    super.remove();
  }

  enableEditMode() {
    if (_classPrivateFieldGet(this, _disableEditing) || this.canvas === null) {
      return;
    }

    super.enableEditMode();
    this.div.draggable = false;
    this.canvas.addEventListener("pointerdown", _classPrivateFieldGet(this, _boundCanvasPointerdown));
    this.canvas.addEventListener("pointerup", _classPrivateFieldGet(this, _boundCanvasPointerup));
  }

  disableEditMode() {
    if (!this.isInEditMode() || this.canvas === null) {
      return;
    }

    super.disableEditMode();
    this.div.draggable = !this.isEmpty();
    this.div.classList.remove("editing");
    this.canvas.removeEventListener("pointerdown", _classPrivateFieldGet(this, _boundCanvasPointerdown));
    this.canvas.removeEventListener("pointerup", _classPrivateFieldGet(this, _boundCanvasPointerup));
  }

  onceAdded() {
    this.div.draggable = !this.isEmpty();
  }

  isEmpty() {
    return this.paths.length === 0 || this.paths.length === 1 && this.paths[0].length === 0;
  }

  commit() {
    if (_classPrivateFieldGet(this, _disableEditing)) {
      return;
    }

    super.commit();
    this.isEditing = false;
    this.disableEditMode();
    this.setInForeground();

    _classPrivateFieldSet(this, _disableEditing, true);

    this.div.classList.add("disabled");

    _classPrivateMethodGet(this, _fitToContent, _fitToContent2).call(this, true);

    this.parent.addInkEditorIfNeeded(true);
    this.parent.moveEditorInDOM(this);
    this.div.focus();
  }

  focusin(event) {
    super.focusin(event);
    this.enableEditMode();
  }

  canvasPointerdown(event) {
    if (event.button !== 0 || !this.isInEditMode() || _classPrivateFieldGet(this, _disableEditing)) {
      return;
    }

    this.setInForeground();

    if (event.type !== "mouse") {
      this.div.focus();
    }

    event.stopPropagation();
    this.canvas.addEventListener("pointerleave", _classPrivateFieldGet(this, _boundCanvasPointerleave));
    this.canvas.addEventListener("pointermove", _classPrivateFieldGet(this, _boundCanvasPointermove));

    _classPrivateMethodGet(this, _startDrawing, _startDrawing2).call(this, event.offsetX, event.offsetY);
  }

  canvasPointermove(event) {
    event.stopPropagation();

    _classPrivateMethodGet(this, _draw, _draw2).call(this, event.offsetX, event.offsetY);
  }

  canvasPointerup(event) {
    if (event.button !== 0) {
      return;
    }

    if (this.isInEditMode() && this.currentPath.length !== 0) {
      event.stopPropagation();

      _classPrivateMethodGet(this, _endDrawing, _endDrawing2).call(this, event);

      this.setInBackground();
    }
  }

  canvasPointerleave(event) {
    _classPrivateMethodGet(this, _endDrawing, _endDrawing2).call(this, event);

    this.setInBackground();
  }

  render() {
    if (this.div) {
      return this.div;
    }

    let baseX, baseY;

    if (this.width) {
      baseX = this.x;
      baseY = this.y;
    }

    super.render();

    InkEditor._l10nPromise.get("editor_ink_aria_label").then(msg => {
      var _this$div;

      return (_this$div = this.div) === null || _this$div === void 0 ? void 0 : _this$div.setAttribute("aria-label", msg);
    });

    const [x, y, w, h] = _classPrivateMethodGet(this, _getInitialBBox, _getInitialBBox2).call(this);

    this.setAt(x, y, 0, 0);
    this.setDims(w, h);

    _classPrivateMethodGet(this, _createCanvas, _createCanvas2).call(this);

    if (this.width) {
      const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
      this.setAt(baseX * parentWidth, baseY * parentHeight, this.width * parentWidth, this.height * parentHeight);

      _classPrivateFieldSet(this, _isCanvasInitialized, true);

      _classPrivateMethodGet(this, _setCanvasDims, _setCanvasDims2).call(this);

      this.setDims(this.width * parentWidth, this.height * parentHeight);

      _classPrivateMethodGet(this, _redraw, _redraw2).call(this);

      _classPrivateMethodGet(this, _setMinDims, _setMinDims2).call(this);

      this.div.classList.add("disabled");
    } else {
      this.div.classList.add("editing");
      this.enableEditMode();
    }

    _classPrivateMethodGet(this, _createObserver, _createObserver2).call(this);

    return this.div;
  }

  setDimensions(width, height) {
    const roundedWidth = Math.round(width);
    const roundedHeight = Math.round(height);

    if (_classPrivateFieldGet(this, _realWidth) === roundedWidth && _classPrivateFieldGet(this, _realHeight) === roundedHeight) {
      return;
    }

    _classPrivateFieldSet(this, _realWidth, roundedWidth);

    _classPrivateFieldSet(this, _realHeight, roundedHeight);

    this.canvas.style.visibility = "hidden";

    if (_classPrivateFieldGet(this, _aspectRatio) && Math.abs(_classPrivateFieldGet(this, _aspectRatio) - width / height) > 1e-2) {
      height = Math.ceil(width / _classPrivateFieldGet(this, _aspectRatio));
      this.setDims(width, height);
    }

    const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
    this.width = width / parentWidth;
    this.height = height / parentHeight;

    if (_classPrivateFieldGet(this, _disableEditing)) {
      _classPrivateMethodGet(this, _setScaleFactor, _setScaleFactor2).call(this, width, height);
    }

    _classPrivateMethodGet(this, _setCanvasDims, _setCanvasDims2).call(this);

    _classPrivateMethodGet(this, _redraw, _redraw2).call(this);

    this.canvas.style.visibility = "visible";
  }

  static deserialize(data, parent) {
    const editor = super.deserialize(data, parent);
    editor.thickness = data.thickness;
    editor.color = _util.Util.makeHexColor(...data.color);
    editor.opacity = data.opacity;
    const [pageWidth, pageHeight] = parent.pageDimensions;
    const width = editor.width * pageWidth;
    const height = editor.height * pageHeight;
    const scaleFactor = parent.scaleFactor;
    const padding = data.thickness / 2;

    _classPrivateFieldSet(editor, _aspectRatio, width / height);

    _classPrivateFieldSet(editor, _disableEditing, true);

    _classPrivateFieldSet(editor, _realWidth, Math.round(width));

    _classPrivateFieldSet(editor, _realHeight, Math.round(height));

    for (const {
      bezier
    } of data.paths) {
      const path = [];
      editor.paths.push(path);
      let p0 = scaleFactor * (bezier[0] - padding);
      let p1 = scaleFactor * (height - bezier[1] - padding);

      for (let i = 2, ii = bezier.length; i < ii; i += 6) {
        const p10 = scaleFactor * (bezier[i] - padding);
        const p11 = scaleFactor * (height - bezier[i + 1] - padding);
        const p20 = scaleFactor * (bezier[i + 2] - padding);
        const p21 = scaleFactor * (height - bezier[i + 3] - padding);
        const p30 = scaleFactor * (bezier[i + 4] - padding);
        const p31 = scaleFactor * (height - bezier[i + 5] - padding);
        path.push([[p0, p1], [p10, p11], [p20, p21], [p30, p31]]);
        p0 = p30;
        p1 = p31;
      }

      const path2D = _classStaticPrivateMethodGet(this, InkEditor, _buildPath2D).call(this, path);

      editor.bezierPath2D.push(path2D);
    }

    const bbox = _classPrivateMethodGet(editor, _getBbox, _getBbox2).call(editor);

    _classPrivateFieldSet(editor, _baseWidth, Math.max(RESIZER_SIZE, bbox[2] - bbox[0]));

    _classPrivateFieldSet(editor, _baseHeight, Math.max(RESIZER_SIZE, bbox[3] - bbox[1]));

    _classPrivateMethodGet(editor, _setScaleFactor, _setScaleFactor2).call(editor, width, height);

    return editor;
  }

  serialize() {
    if (this.isEmpty()) {
      return null;
    }

    const rect = this.getRect(0, 0);
    const height = this.rotation % 180 === 0 ? rect[3] - rect[1] : rect[2] - rect[0];

    const color = _editor.AnnotationEditor._colorManager.convert(this.ctx.strokeStyle);

    return {
      annotationType: _util.AnnotationEditorType.INK,
      color,
      thickness: this.thickness,
      opacity: this.opacity,
      paths: _classPrivateMethodGet(this, _serializePaths, _serializePaths2).call(this, this.scaleFactor / this.parent.scaleFactor, this.translationX, this.translationY, height),
      pageIndex: this.parent.pageIndex,
      rect,
      rotation: this.rotation
    };
  }

}

exports.InkEditor = InkEditor;

function _updateThickness2(thickness) {
  const savedThickness = this.thickness;
  this.parent.addCommands({
    cmd: () => {
      this.thickness = thickness;

      _classPrivateMethodGet(this, _fitToContent, _fitToContent2).call(this);
    },
    undo: () => {
      this.thickness = savedThickness;

      _classPrivateMethodGet(this, _fitToContent, _fitToContent2).call(this);
    },
    mustExec: true,
    type: _util.AnnotationEditorParamsType.INK_THICKNESS,
    overwriteIfSameType: true,
    keepUndo: true
  });
}

function _updateColor2(color) {
  const savedColor = this.color;
  this.parent.addCommands({
    cmd: () => {
      this.color = color;

      _classPrivateMethodGet(this, _redraw, _redraw2).call(this);
    },
    undo: () => {
      this.color = savedColor;

      _classPrivateMethodGet(this, _redraw, _redraw2).call(this);
    },
    mustExec: true,
    type: _util.AnnotationEditorParamsType.INK_COLOR,
    overwriteIfSameType: true,
    keepUndo: true
  });
}

function _updateOpacity2(opacity) {
  opacity /= 100;
  const savedOpacity = this.opacity;
  this.parent.addCommands({
    cmd: () => {
      this.opacity = opacity;

      _classPrivateMethodGet(this, _redraw, _redraw2).call(this);
    },
    undo: () => {
      this.opacity = savedOpacity;

      _classPrivateMethodGet(this, _redraw, _redraw2).call(this);
    },
    mustExec: true,
    type: _util.AnnotationEditorParamsType.INK_OPACITY,
    overwriteIfSameType: true,
    keepUndo: true
  });
}

function _getInitialBBox2() {
  const {
    width,
    height,
    rotation
  } = this.parent.viewport;

  switch (rotation) {
    case 90:
      return [0, width, width, height];

    case 180:
      return [width, height, width, height];

    case 270:
      return [height, 0, width, height];

    default:
      return [0, 0, width, height];
  }
}

function _setStroke2() {
  this.ctx.lineWidth = this.thickness * this.parent.scaleFactor / this.scaleFactor;
  this.ctx.lineCap = "round";
  this.ctx.lineJoin = "round";
  this.ctx.miterLimit = 10;
  this.ctx.strokeStyle = `${this.color}${(0, _tools.opacityToHex)(this.opacity)}`;
}

function _startDrawing2(x, y) {
  this.isEditing = true;

  if (!_classPrivateFieldGet(this, _isCanvasInitialized)) {
    var _this$opacity2;

    _classPrivateFieldSet(this, _isCanvasInitialized, true);

    _classPrivateMethodGet(this, _setCanvasDims, _setCanvasDims2).call(this);

    this.thickness || (this.thickness = InkEditor._defaultThickness);
    this.color || (this.color = InkEditor._defaultColor || _editor.AnnotationEditor._defaultLineColor);
    (_this$opacity2 = this.opacity) !== null && _this$opacity2 !== void 0 ? _this$opacity2 : this.opacity = InkEditor._defaultOpacity;
  }

  this.currentPath.push([x, y]);

  _classPrivateFieldSet(this, _lastPoint, null);

  _classPrivateMethodGet(this, _setStroke, _setStroke2).call(this);

  this.ctx.beginPath();
  this.ctx.moveTo(x, y);

  _classPrivateFieldSet(this, _requestFrameCallback, () => {
    if (!_classPrivateFieldGet(this, _requestFrameCallback)) {
      return;
    }

    if (_classPrivateFieldGet(this, _lastPoint)) {
      if (this.isEmpty()) {
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      } else {
        _classPrivateMethodGet(this, _redraw, _redraw2).call(this);
      }

      this.ctx.lineTo(..._classPrivateFieldGet(this, _lastPoint));

      _classPrivateFieldSet(this, _lastPoint, null);

      this.ctx.stroke();
    }

    window.requestAnimationFrame(_classPrivateFieldGet(this, _requestFrameCallback));
  });

  window.requestAnimationFrame(_classPrivateFieldGet(this, _requestFrameCallback));
}

function _draw2(x, y) {
  const [lastX, lastY] = this.currentPath.at(-1);

  if (x === lastX && y === lastY) {
    return;
  }

  this.currentPath.push([x, y]);

  _classPrivateFieldSet(this, _lastPoint, [x, y]);
}

function _stopDrawing2(x, y) {
  this.ctx.closePath();

  _classPrivateFieldSet(this, _requestFrameCallback, null);

  x = Math.min(Math.max(x, 0), this.canvas.width);
  y = Math.min(Math.max(y, 0), this.canvas.height);
  const [lastX, lastY] = this.currentPath.at(-1);

  if (x !== lastX || y !== lastY) {
    this.currentPath.push([x, y]);
  }

  let bezier;

  if (this.currentPath.length !== 1) {
    bezier = (0, _pdfjsFitCurve.fitCurve)(this.currentPath, 30, null);
  } else {
    const xy = [x, y];
    bezier = [[xy, xy.slice(), xy.slice(), xy]];
  }

  const path2D = _classStaticPrivateMethodGet(InkEditor, InkEditor, _buildPath2D).call(InkEditor, bezier);

  this.currentPath.length = 0;

  const cmd = () => {
    this.paths.push(bezier);
    this.bezierPath2D.push(path2D);
    this.rebuild();
  };

  const undo = () => {
    this.paths.pop();
    this.bezierPath2D.pop();

    if (this.paths.length === 0) {
      this.remove();
    } else {
      if (!this.canvas) {
        _classPrivateMethodGet(this, _createCanvas, _createCanvas2).call(this);

        _classPrivateMethodGet(this, _createObserver, _createObserver2).call(this);
      }

      _classPrivateMethodGet(this, _fitToContent, _fitToContent2).call(this);
    }
  };

  this.parent.addCommands({
    cmd,
    undo,
    mustExec: true
  });
}

function _redraw2() {
  if (this.isEmpty()) {
    _classPrivateMethodGet(this, _updateTransform, _updateTransform2).call(this);

    return;
  }

  _classPrivateMethodGet(this, _setStroke, _setStroke2).call(this);

  const {
    canvas,
    ctx
  } = this;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  _classPrivateMethodGet(this, _updateTransform, _updateTransform2).call(this);

  for (const path of this.bezierPath2D) {
    ctx.stroke(path);
  }
}

function _endDrawing2(event) {
  _classPrivateMethodGet(this, _stopDrawing, _stopDrawing2).call(this, event.offsetX, event.offsetY);

  this.canvas.removeEventListener("pointerleave", _classPrivateFieldGet(this, _boundCanvasPointerleave));
  this.canvas.removeEventListener("pointermove", _classPrivateFieldGet(this, _boundCanvasPointermove));
  this.parent.addToAnnotationStorage(this);
}

function _createCanvas2() {
  this.canvas = document.createElement("canvas");
  this.canvas.width = this.canvas.height = 0;
  this.canvas.className = "inkEditorCanvas";

  InkEditor._l10nPromise.get("editor_ink_canvas_aria_label").then(msg => {
    var _this$canvas;

    return (_this$canvas = this.canvas) === null || _this$canvas === void 0 ? void 0 : _this$canvas.setAttribute("aria-label", msg);
  });

  this.div.append(this.canvas);
  this.ctx = this.canvas.getContext("2d");
}

function _createObserver2() {
  _classPrivateFieldSet(this, _observer, new ResizeObserver(entries => {
    const rect = entries[0].contentRect;

    if (rect.width && rect.height) {
      this.setDimensions(rect.width, rect.height);
    }
  }));

  _classPrivateFieldGet(this, _observer).observe(this.div);
}

function _setCanvasDims2() {
  if (!_classPrivateFieldGet(this, _isCanvasInitialized)) {
    return;
  }

  const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
  this.canvas.width = Math.ceil(this.width * parentWidth);
  this.canvas.height = Math.ceil(this.height * parentHeight);

  _classPrivateMethodGet(this, _updateTransform, _updateTransform2).call(this);
}

function _setScaleFactor2(width, height) {
  const padding = _classPrivateMethodGet(this, _getPadding, _getPadding2).call(this);

  const scaleFactorW = (width - padding) / _classPrivateFieldGet(this, _baseWidth);

  const scaleFactorH = (height - padding) / _classPrivateFieldGet(this, _baseHeight);

  this.scaleFactor = Math.min(scaleFactorW, scaleFactorH);
}

function _updateTransform2() {
  const padding = _classPrivateMethodGet(this, _getPadding, _getPadding2).call(this) / 2;
  this.ctx.setTransform(this.scaleFactor, 0, 0, this.scaleFactor, this.translationX * this.scaleFactor + padding, this.translationY * this.scaleFactor + padding);
}

function _buildPath2D(bezier) {
  const path2D = new Path2D();

  for (let i = 0, ii = bezier.length; i < ii; i++) {
    const [first, control1, control2, second] = bezier[i];

    if (i === 0) {
      path2D.moveTo(...first);
    }

    path2D.bezierCurveTo(control1[0], control1[1], control2[0], control2[1], second[0], second[1]);
  }

  return path2D;
}

function _serializePaths2(s, tx, ty, h) {
  const NUMBER_OF_POINTS_ON_BEZIER_CURVE = 4;
  const paths = [];
  const padding = this.thickness / 2;
  let buffer, points;

  for (const bezier of this.paths) {
    buffer = [];
    points = [];

    for (let i = 0, ii = bezier.length; i < ii; i++) {
      const [first, control1, control2, second] = bezier[i];
      const p10 = s * (first[0] + tx) + padding;
      const p11 = h - s * (first[1] + ty) - padding;
      const p20 = s * (control1[0] + tx) + padding;
      const p21 = h - s * (control1[1] + ty) - padding;
      const p30 = s * (control2[0] + tx) + padding;
      const p31 = h - s * (control2[1] + ty) - padding;
      const p40 = s * (second[0] + tx) + padding;
      const p41 = h - s * (second[1] + ty) - padding;

      if (i === 0) {
        buffer.push(p10, p11);
        points.push(p10, p11);
      }

      buffer.push(p20, p21, p30, p31, p40, p41);

      _classPrivateMethodGet(this, _extractPointsOnBezier, _extractPointsOnBezier2).call(this, p10, p11, p20, p21, p30, p31, p40, p41, NUMBER_OF_POINTS_ON_BEZIER_CURVE, points);
    }

    paths.push({
      bezier: buffer,
      points
    });
  }

  return paths;
}

function _extractPointsOnBezier2(p10, p11, p20, p21, p30, p31, p40, p41, n, points) {
  if (_classPrivateMethodGet(this, _isAlmostFlat, _isAlmostFlat2).call(this, p10, p11, p20, p21, p30, p31, p40, p41)) {
    points.push(p40, p41);
    return;
  }

  for (let i = 1; i < n - 1; i++) {
    const t = i / n;
    const mt = 1 - t;
    let q10 = t * p10 + mt * p20;
    let q11 = t * p11 + mt * p21;
    let q20 = t * p20 + mt * p30;
    let q21 = t * p21 + mt * p31;
    const q30 = t * p30 + mt * p40;
    const q31 = t * p31 + mt * p41;
    q10 = t * q10 + mt * q20;
    q11 = t * q11 + mt * q21;
    q20 = t * q20 + mt * q30;
    q21 = t * q21 + mt * q31;
    q10 = t * q10 + mt * q20;
    q11 = t * q11 + mt * q21;
    points.push(q10, q11);
  }

  points.push(p40, p41);
}

function _isAlmostFlat2(p10, p11, p20, p21, p30, p31, p40, p41) {
  const tol = 10;
  const ax = (3 * p20 - 2 * p10 - p40) ** 2;
  const ay = (3 * p21 - 2 * p11 - p41) ** 2;
  const bx = (3 * p30 - p10 - 2 * p40) ** 2;
  const by = (3 * p31 - p11 - 2 * p41) ** 2;
  return Math.max(ax, bx) + Math.max(ay, by) <= tol;
}

function _getBbox2() {
  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;

  for (const path of this.paths) {
    for (const [first, control1, control2, second] of path) {
      const bbox = _util.Util.bezierBoundingBox(...first, ...control1, ...control2, ...second);

      xMin = Math.min(xMin, bbox[0]);
      yMin = Math.min(yMin, bbox[1]);
      xMax = Math.max(xMax, bbox[2]);
      yMax = Math.max(yMax, bbox[3]);
    }
  }

  return [xMin, yMin, xMax, yMax];
}

function _getPadding2() {
  return _classPrivateFieldGet(this, _disableEditing) ? Math.ceil(this.thickness * this.parent.scaleFactor) : 0;
}

function _fitToContent2() {
  let firstTime = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

  if (this.isEmpty()) {
    return;
  }

  if (!_classPrivateFieldGet(this, _disableEditing)) {
    _classPrivateMethodGet(this, _redraw, _redraw2).call(this);

    return;
  }

  const bbox = _classPrivateMethodGet(this, _getBbox, _getBbox2).call(this);

  const padding = _classPrivateMethodGet(this, _getPadding, _getPadding2).call(this);

  _classPrivateFieldSet(this, _baseWidth, Math.max(RESIZER_SIZE, bbox[2] - bbox[0]));

  _classPrivateFieldSet(this, _baseHeight, Math.max(RESIZER_SIZE, bbox[3] - bbox[1]));

  const width = Math.ceil(padding + _classPrivateFieldGet(this, _baseWidth) * this.scaleFactor);
  const height = Math.ceil(padding + _classPrivateFieldGet(this, _baseHeight) * this.scaleFactor);
  const [parentWidth, parentHeight] = this.parent.viewportBaseDimensions;
  this.width = width / parentWidth;
  this.height = height / parentHeight;

  _classPrivateFieldSet(this, _aspectRatio, width / height);

  _classPrivateMethodGet(this, _setMinDims, _setMinDims2).call(this);

  const prevTranslationX = this.translationX;
  const prevTranslationY = this.translationY;
  this.translationX = -bbox[0];
  this.translationY = -bbox[1];

  _classPrivateMethodGet(this, _setCanvasDims, _setCanvasDims2).call(this);

  _classPrivateMethodGet(this, _redraw, _redraw2).call(this);

  _classPrivateFieldSet(this, _realWidth, width);

  _classPrivateFieldSet(this, _realHeight, height);

  this.setDims(width, height);
  const unscaledPadding = firstTime ? padding / this.scaleFactor / 2 : 0;
  this.translate(prevTranslationX - this.translationX - unscaledPadding, prevTranslationY - this.translationY - unscaledPadding);
}

function _setMinDims2() {
  const {
    style
  } = this.div;

  if (_classPrivateFieldGet(this, _aspectRatio) >= 1) {
    style.minHeight = `${RESIZER_SIZE}px`;
    style.minWidth = `${Math.round(_classPrivateFieldGet(this, _aspectRatio) * RESIZER_SIZE)}px`;
  } else {
    style.minWidth = `${RESIZER_SIZE}px`;
    style.minHeight = `${Math.round(RESIZER_SIZE / _classPrivateFieldGet(this, _aspectRatio))}px`;
  }
}

_defineProperty(InkEditor, "_defaultColor", null);

_defineProperty(InkEditor, "_defaultOpacity", 1);

_defineProperty(InkEditor, "_defaultThickness", 1);

_defineProperty(InkEditor, "_l10nPromise", void 0);

_defineProperty(InkEditor, "_type", "ink");

/***/ }),
/* 150 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.fitCurve = void 0;

const fitCurve = __w_pdfjs_require__(151);

exports.fitCurve = fitCurve;

/***/ }),
/* 151 */
/***/ ((module) => {

"use strict";


function fitCurve(points, maxError, progressCallback) {
  if (!Array.isArray(points)) {
    throw new TypeError("First argument should be an array");
  }

  points.forEach(point => {
    if (!Array.isArray(point) || point.some(item => typeof item !== 'number') || point.length !== points[0].length) {
      throw Error("Each point should be an array of numbers. Each point should have the same amount of numbers.");
    }
  });
  points = points.filter((point, i) => i === 0 || !point.every((val, j) => val === points[i - 1][j]));

  if (points.length < 2) {
    return [];
  }

  const len = points.length;
  const leftTangent = createTangent(points[1], points[0]);
  const rightTangent = createTangent(points[len - 2], points[len - 1]);
  return fitCubic(points, leftTangent, rightTangent, maxError, progressCallback);
}

function fitCubic(points, leftTangent, rightTangent, error, progressCallback) {
  const MaxIterations = 20;
  var bezCurve, u, uPrime, maxError, prevErr, splitPoint, prevSplit, centerVector, toCenterTangent, fromCenterTangent, beziers, dist, i;

  if (points.length === 2) {
    dist = maths.vectorLen(maths.subtract(points[0], points[1])) / 3.0;
    bezCurve = [points[0], maths.addArrays(points[0], maths.mulItems(leftTangent, dist)), maths.addArrays(points[1], maths.mulItems(rightTangent, dist)), points[1]];
    return [bezCurve];
  }

  u = chordLengthParameterize(points);
  [bezCurve, maxError, splitPoint] = generateAndReport(points, u, u, leftTangent, rightTangent, progressCallback);

  if (maxError === 0 || maxError < error) {
    return [bezCurve];
  }

  if (maxError < error * error) {
    uPrime = u;
    prevErr = maxError;
    prevSplit = splitPoint;

    for (i = 0; i < MaxIterations; i++) {
      uPrime = reparameterize(bezCurve, points, uPrime);
      [bezCurve, maxError, splitPoint] = generateAndReport(points, u, uPrime, leftTangent, rightTangent, progressCallback);

      if (maxError < error) {
        return [bezCurve];
      } else if (splitPoint === prevSplit) {
        let errChange = maxError / prevErr;

        if (errChange > .9999 && errChange < 1.0001) {
          break;
        }
      }

      prevErr = maxError;
      prevSplit = splitPoint;
    }
  }

  beziers = [];
  centerVector = maths.subtract(points[splitPoint - 1], points[splitPoint + 1]);

  if (centerVector.every(val => val === 0)) {
    centerVector = maths.subtract(points[splitPoint - 1], points[splitPoint]);
    [centerVector[0], centerVector[1]] = [-centerVector[1], centerVector[0]];
  }

  toCenterTangent = maths.normalize(centerVector);
  fromCenterTangent = maths.mulItems(toCenterTangent, -1);
  beziers = beziers.concat(fitCubic(points.slice(0, splitPoint + 1), leftTangent, toCenterTangent, error, progressCallback));
  beziers = beziers.concat(fitCubic(points.slice(splitPoint), fromCenterTangent, rightTangent, error, progressCallback));
  return beziers;
}

;

function generateAndReport(points, paramsOrig, paramsPrime, leftTangent, rightTangent, progressCallback) {
  var bezCurve, maxError, splitPoint;
  bezCurve = generateBezier(points, paramsPrime, leftTangent, rightTangent, progressCallback);
  [maxError, splitPoint] = computeMaxError(points, bezCurve, paramsOrig);

  if (progressCallback) {
    progressCallback({
      bez: bezCurve,
      points: points,
      params: paramsOrig,
      maxErr: maxError,
      maxPoint: splitPoint
    });
  }

  return [bezCurve, maxError, splitPoint];
}

function generateBezier(points, parameters, leftTangent, rightTangent) {
  var bezCurve,
      A,
      a,
      C,
      X,
      det_C0_C1,
      det_C0_X,
      det_X_C1,
      alpha_l,
      alpha_r,
      epsilon,
      segLength,
      i,
      len,
      tmp,
      u,
      ux,
      firstPoint = points[0],
      lastPoint = points[points.length - 1];
  bezCurve = [firstPoint, null, null, lastPoint];
  A = maths.zeros_Xx2x2(parameters.length);

  for (i = 0, len = parameters.length; i < len; i++) {
    u = parameters[i];
    ux = 1 - u;
    a = A[i];
    a[0] = maths.mulItems(leftTangent, 3 * u * (ux * ux));
    a[1] = maths.mulItems(rightTangent, 3 * ux * (u * u));
  }

  C = [[0, 0], [0, 0]];
  X = [0, 0];

  for (i = 0, len = points.length; i < len; i++) {
    u = parameters[i];
    a = A[i];
    C[0][0] += maths.dot(a[0], a[0]);
    C[0][1] += maths.dot(a[0], a[1]);
    C[1][0] += maths.dot(a[0], a[1]);
    C[1][1] += maths.dot(a[1], a[1]);
    tmp = maths.subtract(points[i], bezier.q([firstPoint, firstPoint, lastPoint, lastPoint], u));
    X[0] += maths.dot(a[0], tmp);
    X[1] += maths.dot(a[1], tmp);
  }

  det_C0_C1 = C[0][0] * C[1][1] - C[1][0] * C[0][1];
  det_C0_X = C[0][0] * X[1] - C[1][0] * X[0];
  det_X_C1 = X[0] * C[1][1] - X[1] * C[0][1];
  alpha_l = det_C0_C1 === 0 ? 0 : det_X_C1 / det_C0_C1;
  alpha_r = det_C0_C1 === 0 ? 0 : det_C0_X / det_C0_C1;
  segLength = maths.vectorLen(maths.subtract(firstPoint, lastPoint));
  epsilon = 1.0e-6 * segLength;

  if (alpha_l < epsilon || alpha_r < epsilon) {
    bezCurve[1] = maths.addArrays(firstPoint, maths.mulItems(leftTangent, segLength / 3.0));
    bezCurve[2] = maths.addArrays(lastPoint, maths.mulItems(rightTangent, segLength / 3.0));
  } else {
    bezCurve[1] = maths.addArrays(firstPoint, maths.mulItems(leftTangent, alpha_l));
    bezCurve[2] = maths.addArrays(lastPoint, maths.mulItems(rightTangent, alpha_r));
  }

  return bezCurve;
}

;

function reparameterize(bezier, points, parameters) {
  return parameters.map((p, i) => newtonRaphsonRootFind(bezier, points[i], p));
}

;

function newtonRaphsonRootFind(bez, point, u) {
  var d = maths.subtract(bezier.q(bez, u), point),
      qprime = bezier.qprime(bez, u),
      numerator = maths.mulMatrix(d, qprime),
      denominator = maths.sum(maths.squareItems(qprime)) + 2 * maths.mulMatrix(d, bezier.qprimeprime(bez, u));

  if (denominator === 0) {
    return u;
  } else {
    return u - numerator / denominator;
  }
}

;

function chordLengthParameterize(points) {
  var u = [],
      currU,
      prevU,
      prevP;
  points.forEach((p, i) => {
    currU = i ? prevU + maths.vectorLen(maths.subtract(p, prevP)) : 0;
    u.push(currU);
    prevU = currU;
    prevP = p;
  });
  u = u.map(x => x / prevU);
  return u;
}

;

function computeMaxError(points, bez, parameters) {
  var dist, maxDist, splitPoint, v, i, count, point, t;
  maxDist = 0;
  splitPoint = Math.floor(points.length / 2);
  const t_distMap = mapTtoRelativeDistances(bez, 10);

  for (i = 0, count = points.length; i < count; i++) {
    point = points[i];
    t = find_t(bez, parameters[i], t_distMap, 10);
    v = maths.subtract(bezier.q(bez, t), point);
    dist = v[0] * v[0] + v[1] * v[1];

    if (dist > maxDist) {
      maxDist = dist;
      splitPoint = i;
    }
  }

  return [maxDist, splitPoint];
}

;

var mapTtoRelativeDistances = function (bez, B_parts) {
  var B_t_curr;
  var B_t_dist = [0];
  var B_t_prev = bez[0];
  var sumLen = 0;

  for (var i = 1; i <= B_parts; i++) {
    B_t_curr = bezier.q(bez, i / B_parts);
    sumLen += maths.vectorLen(maths.subtract(B_t_curr, B_t_prev));
    B_t_dist.push(sumLen);
    B_t_prev = B_t_curr;
  }

  B_t_dist = B_t_dist.map(x => x / sumLen);
  return B_t_dist;
};

function find_t(bez, param, t_distMap, B_parts) {
  if (param < 0) {
    return 0;
  }

  if (param > 1) {
    return 1;
  }

  var lenMax, lenMin, tMax, tMin, t;

  for (var i = 1; i <= B_parts; i++) {
    if (param <= t_distMap[i]) {
      tMin = (i - 1) / B_parts;
      tMax = i / B_parts;
      lenMin = t_distMap[i - 1];
      lenMax = t_distMap[i];
      t = (param - lenMin) / (lenMax - lenMin) * (tMax - tMin) + tMin;
      break;
    }
  }

  return t;
}

function createTangent(pointA, pointB) {
  return maths.normalize(maths.subtract(pointA, pointB));
}

class maths {
  static zeros_Xx2x2(x) {
    var zs = [];

    while (x--) {
      zs.push([0, 0]);
    }

    return zs;
  }

  static mulItems(items, multiplier) {
    return items.map(x => x * multiplier);
  }

  static mulMatrix(m1, m2) {
    return m1.reduce((sum, x1, i) => sum + x1 * m2[i], 0);
  }

  static subtract(arr1, arr2) {
    return arr1.map((x1, i) => x1 - arr2[i]);
  }

  static addArrays(arr1, arr2) {
    return arr1.map((x1, i) => x1 + arr2[i]);
  }

  static addItems(items, addition) {
    return items.map(x => x + addition);
  }

  static sum(items) {
    return items.reduce((sum, x) => sum + x);
  }

  static dot(m1, m2) {
    return maths.mulMatrix(m1, m2);
  }

  static vectorLen(v) {
    return Math.hypot(...v);
  }

  static divItems(items, divisor) {
    return items.map(x => x / divisor);
  }

  static squareItems(items) {
    return items.map(x => x * x);
  }

  static normalize(v) {
    return this.divItems(v, this.vectorLen(v));
  }

}

class bezier {
  static q(ctrlPoly, t) {
    var tx = 1.0 - t;
    var pA = maths.mulItems(ctrlPoly[0], tx * tx * tx),
        pB = maths.mulItems(ctrlPoly[1], 3 * tx * tx * t),
        pC = maths.mulItems(ctrlPoly[2], 3 * tx * t * t),
        pD = maths.mulItems(ctrlPoly[3], t * t * t);
    return maths.addArrays(maths.addArrays(pA, pB), maths.addArrays(pC, pD));
  }

  static qprime(ctrlPoly, t) {
    var tx = 1.0 - t;
    var pA = maths.mulItems(maths.subtract(ctrlPoly[1], ctrlPoly[0]), 3 * tx * tx),
        pB = maths.mulItems(maths.subtract(ctrlPoly[2], ctrlPoly[1]), 6 * tx * t),
        pC = maths.mulItems(maths.subtract(ctrlPoly[3], ctrlPoly[2]), 3 * t * t);
    return maths.addArrays(maths.addArrays(pA, pB), pC);
  }

  static qprimeprime(ctrlPoly, t) {
    return maths.addArrays(maths.mulItems(maths.addArrays(maths.subtract(ctrlPoly[2], maths.mulItems(ctrlPoly[1], 2)), ctrlPoly[0]), 6 * (1.0 - t)), maths.mulItems(maths.addArrays(maths.subtract(ctrlPoly[3], maths.mulItems(ctrlPoly[2], 2)), ctrlPoly[1]), 6 * t));
  }

}

module.exports = fitCurve;
module.exports.fitCubic = fitCubic;
module.exports.createTangent = createTangent;

/***/ }),
/* 152 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.AnnotationLayer = void 0;

var _util = __w_pdfjs_require__(1);

var _display_utils = __w_pdfjs_require__(133);

var _annotation_storage = __w_pdfjs_require__(130);

var _scripting_utils = __w_pdfjs_require__(153);

var _xfa_layer = __w_pdfjs_require__(154);

function _classStaticPrivateMethodGet(receiver, classConstructor, method) { _classCheckPrivateStaticAccess(receiver, classConstructor); return method; }

function _classCheckPrivateStaticAccess(receiver, classConstructor) { if (receiver !== classConstructor) { throw new TypeError("Private static access of wrong provenance"); } }

const DEFAULT_TAB_INDEX = 1000;
const DEFAULT_FONT_SIZE = 9;
const GetElementsByNameSet = new WeakSet();

function getRectDims(rect) {
  return {
    width: rect[2] - rect[0],
    height: rect[3] - rect[1]
  };
}

class AnnotationElementFactory {
  static create(parameters) {
    const subtype = parameters.data.annotationType;

    switch (subtype) {
      case _util.AnnotationType.LINK:
        return new LinkAnnotationElement(parameters);

      case _util.AnnotationType.TEXT:
        return new TextAnnotationElement(parameters);

      case _util.AnnotationType.WIDGET:
        const fieldType = parameters.data.fieldType;

        switch (fieldType) {
          case "Tx":
            return new TextWidgetAnnotationElement(parameters);

          case "Btn":
            if (parameters.data.radioButton) {
              return new RadioButtonWidgetAnnotationElement(parameters);
            } else if (parameters.data.checkBox) {
              return new CheckboxWidgetAnnotationElement(parameters);
            }

            return new PushButtonWidgetAnnotationElement(parameters);

          case "Ch":
            return new ChoiceWidgetAnnotationElement(parameters);
        }

        return new WidgetAnnotationElement(parameters);

      case _util.AnnotationType.POPUP:
        return new PopupAnnotationElement(parameters);

      case _util.AnnotationType.FREETEXT:
        return new FreeTextAnnotationElement(parameters);

      case _util.AnnotationType.LINE:
        return new LineAnnotationElement(parameters);

      case _util.AnnotationType.SQUARE:
        return new SquareAnnotationElement(parameters);

      case _util.AnnotationType.CIRCLE:
        return new CircleAnnotationElement(parameters);

      case _util.AnnotationType.POLYLINE:
        return new PolylineAnnotationElement(parameters);

      case _util.AnnotationType.CARET:
        return new CaretAnnotationElement(parameters);

      case _util.AnnotationType.INK:
        return new InkAnnotationElement(parameters);

      case _util.AnnotationType.POLYGON:
        return new PolygonAnnotationElement(parameters);

      case _util.AnnotationType.HIGHLIGHT:
        return new HighlightAnnotationElement(parameters);

      case _util.AnnotationType.UNDERLINE:
        return new UnderlineAnnotationElement(parameters);

      case _util.AnnotationType.SQUIGGLY:
        return new SquigglyAnnotationElement(parameters);

      case _util.AnnotationType.STRIKEOUT:
        return new StrikeOutAnnotationElement(parameters);

      case _util.AnnotationType.STAMP:
        return new StampAnnotationElement(parameters);

      case _util.AnnotationType.FILEATTACHMENT:
        return new FileAttachmentAnnotationElement(parameters);

      default:
        return new AnnotationElement(parameters);
    }
  }

}

class AnnotationElement {
  constructor(parameters) {
    let {
      isRenderable = false,
      ignoreBorder = false,
      createQuadrilaterals = false
    } = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
    this.isRenderable = isRenderable;
    this.data = parameters.data;
    this.layer = parameters.layer;
    this.page = parameters.page;
    this.viewport = parameters.viewport;
    this.linkService = parameters.linkService;
    this.downloadManager = parameters.downloadManager;
    this.imageResourcesPath = parameters.imageResourcesPath;
    this.renderForms = parameters.renderForms;
    this.svgFactory = parameters.svgFactory;
    this.annotationStorage = parameters.annotationStorage;
    this.enableScripting = parameters.enableScripting;
    this.hasJSActions = parameters.hasJSActions;
    this._fieldObjects = parameters.fieldObjects;
    this._mouseState = parameters.mouseState;

    if (isRenderable) {
      this.container = this._createContainer(ignoreBorder);
    }

    if (createQuadrilaterals) {
      this.quadrilaterals = this._createQuadrilaterals(ignoreBorder);
    }
  }

  _createContainer() {
    let ignoreBorder = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;
    const data = this.data,
          page = this.page,
          viewport = this.viewport;
    const container = document.createElement("section");
    const {
      width,
      height
    } = getRectDims(data.rect);
    const [pageLLx, pageLLy, pageURx, pageURy] = viewport.viewBox;
    const pageWidth = pageURx - pageLLx;
    const pageHeight = pageURy - pageLLy;
    container.setAttribute("data-annotation-id", data.id);

    const rect = _util.Util.normalizeRect([data.rect[0], page.view[3] - data.rect[1] + page.view[1], data.rect[2], page.view[3] - data.rect[3] + page.view[1]]);

    if (!ignoreBorder && data.borderStyle.width > 0) {
      container.style.borderWidth = `${data.borderStyle.width}px`;
      const horizontalRadius = data.borderStyle.horizontalCornerRadius;
      const verticalRadius = data.borderStyle.verticalCornerRadius;

      if (horizontalRadius > 0 || verticalRadius > 0) {
        const radius = `calc(${horizontalRadius}px * var(--scale-factor)) / calc(${verticalRadius}px * var(--scale-factor))`;
        container.style.borderRadius = radius;
      } else if (this instanceof RadioButtonWidgetAnnotationElement) {
        const radius = `calc(${width}px * var(--scale-factor)) / calc(${height}px * var(--scale-factor))`;
        container.style.borderRadius = radius;
      }

      switch (data.borderStyle.style) {
        case _util.AnnotationBorderStyleType.SOLID:
          container.style.borderStyle = "solid";
          break;

        case _util.AnnotationBorderStyleType.DASHED:
          container.style.borderStyle = "dashed";
          break;

        case _util.AnnotationBorderStyleType.BEVELED:
          (0, _util.warn)("Unimplemented border style: beveled");
          break;

        case _util.AnnotationBorderStyleType.INSET:
          (0, _util.warn)("Unimplemented border style: inset");
          break;

        case _util.AnnotationBorderStyleType.UNDERLINE:
          container.style.borderBottomStyle = "solid";
          break;

        default:
          break;
      }

      const borderColor = data.borderColor || null;

      if (borderColor) {
        container.style.borderColor = _util.Util.makeHexColor(borderColor[0] | 0, borderColor[1] | 0, borderColor[2] | 0);
      } else {
        container.style.borderWidth = 0;
      }
    }

    container.style.left = `${100 * (rect[0] - pageLLx) / pageWidth}%`;
    container.style.top = `${100 * (rect[1] - pageLLy) / pageHeight}%`;
    const {
      rotation
    } = data;

    if (data.hasOwnCanvas || rotation === 0) {
      container.style.width = `${100 * width / pageWidth}%`;
      container.style.height = `${100 * height / pageHeight}%`;
    } else {
      this.setRotation(rotation, container);
    }

    return container;
  }

  setRotation(angle) {
    let container = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : this.container;
    const [pageLLx, pageLLy, pageURx, pageURy] = this.viewport.viewBox;
    const pageWidth = pageURx - pageLLx;
    const pageHeight = pageURy - pageLLy;
    const {
      width,
      height
    } = getRectDims(this.data.rect);
    let elementWidth, elementHeight;

    if (angle % 180 === 0) {
      elementWidth = 100 * width / pageWidth;
      elementHeight = 100 * height / pageHeight;
    } else {
      elementWidth = 100 * height / pageWidth;
      elementHeight = 100 * width / pageHeight;
    }

    container.style.width = `${elementWidth}%`;
    container.style.height = `${elementHeight}%`;
    container.setAttribute("data-main-rotation", (360 - angle) % 360);
  }

  get _commonActions() {
    const setColor = (jsName, styleName, event) => {
      const color = event.detail[jsName];
      event.target.style[styleName] = _scripting_utils.ColorConverters[`${color[0]}_HTML`](color.slice(1));
    };

    return (0, _util.shadow)(this, "_commonActions", {
      display: event => {
        const hidden = event.detail.display % 2 === 1;
        this.container.style.visibility = hidden ? "hidden" : "visible";
        this.annotationStorage.setValue(this.data.id, {
          hidden,
          print: event.detail.display === 0 || event.detail.display === 3
        });
      },
      print: event => {
        this.annotationStorage.setValue(this.data.id, {
          print: event.detail.print
        });
      },
      hidden: event => {
        this.container.style.visibility = event.detail.hidden ? "hidden" : "visible";
        this.annotationStorage.setValue(this.data.id, {
          hidden: event.detail.hidden
        });
      },
      focus: event => {
        setTimeout(() => event.target.focus({
          preventScroll: false
        }), 0);
      },
      userName: event => {
        event.target.title = event.detail.userName;
      },
      readonly: event => {
        if (event.detail.readonly) {
          event.target.setAttribute("readonly", "");
        } else {
          event.target.removeAttribute("readonly");
        }
      },
      required: event => {
        this._setRequired(event.target, event.detail.required);
      },
      bgColor: event => {
        setColor("bgColor", "backgroundColor", event);
      },
      fillColor: event => {
        setColor("fillColor", "backgroundColor", event);
      },
      fgColor: event => {
        setColor("fgColor", "color", event);
      },
      textColor: event => {
        setColor("textColor", "color", event);
      },
      borderColor: event => {
        setColor("borderColor", "borderColor", event);
      },
      strokeColor: event => {
        setColor("strokeColor", "borderColor", event);
      },
      rotation: event => {
        const angle = event.detail.rotation;
        this.setRotation(angle);
        this.annotationStorage.setValue(this.data.id, {
          rotation: angle
        });
      }
    });
  }

  _dispatchEventFromSandbox(actions, jsEvent) {
    const commonActions = this._commonActions;

    for (const name of Object.keys(jsEvent.detail)) {
      const action = actions[name] || commonActions[name];

      if (action) {
        action(jsEvent);
      }
    }
  }

  _setDefaultPropertiesFromJS(element) {
    if (!this.enableScripting) {
      return;
    }

    const storedData = this.annotationStorage.getRawValue(this.data.id);

    if (!storedData) {
      return;
    }

    const commonActions = this._commonActions;

    for (const [actionName, detail] of Object.entries(storedData)) {
      const action = commonActions[actionName];

      if (action) {
        const eventProxy = {
          detail: {
            [actionName]: detail
          },
          target: element
        };
        action(eventProxy);
        delete storedData[actionName];
      }
    }
  }

  _createQuadrilaterals() {
    let ignoreBorder = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

    if (!this.data.quadPoints) {
      return null;
    }

    const quadrilaterals = [];
    const savedRect = this.data.rect;

    for (const quadPoint of this.data.quadPoints) {
      this.data.rect = [quadPoint[2].x, quadPoint[2].y, quadPoint[1].x, quadPoint[1].y];
      quadrilaterals.push(this._createContainer(ignoreBorder));
    }

    this.data.rect = savedRect;
    return quadrilaterals;
  }

  _createPopup(trigger, data) {
    let container = this.container;

    if (this.quadrilaterals) {
      trigger = trigger || this.quadrilaterals;
      container = this.quadrilaterals[0];
    }

    if (!trigger) {
      trigger = document.createElement("div");
      trigger.className = "popupTriggerArea";
      container.append(trigger);
    }

    const popupElement = new PopupElement({
      container,
      trigger,
      color: data.color,
      titleObj: data.titleObj,
      modificationDate: data.modificationDate,
      contentsObj: data.contentsObj,
      richText: data.richText,
      hideWrapper: true
    });
    const popup = popupElement.render();
    popup.style.left = "100%";
    container.append(popup);
  }

  _renderQuadrilaterals(className) {
    for (const quadrilateral of this.quadrilaterals) {
      quadrilateral.className = className;
    }

    return this.quadrilaterals;
  }

  render() {
    (0, _util.unreachable)("Abstract method `AnnotationElement.render` called");
  }

  _getElementsByName(name) {
    let skipId = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
    const fields = [];

    if (this._fieldObjects) {
      const fieldObj = this._fieldObjects[name];

      if (fieldObj) {
        for (const {
          page,
          id,
          exportValues
        } of fieldObj) {
          if (page === -1) {
            continue;
          }

          if (id === skipId) {
            continue;
          }

          const exportValue = typeof exportValues === "string" ? exportValues : null;
          const domElement = document.querySelector(`[data-element-id="${id}"]`);

          if (domElement && !GetElementsByNameSet.has(domElement)) {
            (0, _util.warn)(`_getElementsByName - element not allowed: ${id}`);
            continue;
          }

          fields.push({
            id,
            exportValue,
            domElement
          });
        }
      }

      return fields;
    }

    for (const domElement of document.getElementsByName(name)) {
      const {
        id,
        exportValue
      } = domElement;

      if (id === skipId) {
        continue;
      }

      if (!GetElementsByNameSet.has(domElement)) {
        continue;
      }

      fields.push({
        id,
        exportValue,
        domElement
      });
    }

    return fields;
  }

  static get platform() {
    const platform = typeof navigator !== "undefined" ? navigator.platform : "";
    return (0, _util.shadow)(this, "platform", {
      isWin: platform.includes("Win"),
      isMac: platform.includes("Mac")
    });
  }

}

class LinkAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    let options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
    super(parameters, {
      isRenderable: true,
      ignoreBorder: !!(options !== null && options !== void 0 && options.ignoreBorder),
      createQuadrilaterals: true
    });
    this.isTooltipOnly = parameters.data.isTooltipOnly;
  }

  render() {
    const {
      data,
      linkService
    } = this;
    const link = document.createElement("a");
    link.setAttribute("data-element-id", data.id);
    let isBound = false;

    if (data.url) {
      linkService.addLinkAttributes(link, data.url, data.newWindow);
      isBound = true;
    } else if (data.action) {
      this._bindNamedAction(link, data.action);

      isBound = true;
    } else if (data.dest) {
      this._bindLink(link, data.dest);

      isBound = true;
    } else {
      if (data.actions && (data.actions.Action || data.actions["Mouse Up"] || data.actions["Mouse Down"]) && this.enableScripting && this.hasJSActions) {
        this._bindJSAction(link, data);

        isBound = true;
      }

      if (data.resetForm) {
        this._bindResetFormAction(link, data.resetForm);

        isBound = true;
      } else if (this.isTooltipOnly && !isBound) {
        this._bindLink(link, "");

        isBound = true;
      }
    }

    if (this.quadrilaterals) {
      return this._renderQuadrilaterals("linkAnnotation").map((quadrilateral, index) => {
        const linkElement = index === 0 ? link : link.cloneNode();
        quadrilateral.append(linkElement);
        return quadrilateral;
      });
    }

    this.container.className = "linkAnnotation";

    if (isBound) {
      this.container.append(link);
    }

    return this.container;
  }

  _bindLink(link, destination) {
    link.href = this.linkService.getDestinationHash(destination);

    link.onclick = () => {
      if (destination) {
        this.linkService.goToDestination(destination);
      }

      return false;
    };

    if (destination || destination === "") {
      link.className = "internalLink";
    }
  }

  _bindNamedAction(link, action) {
    link.href = this.linkService.getAnchorUrl("");

    link.onclick = () => {
      this.linkService.executeNamedAction(action);
      return false;
    };

    link.className = "internalLink";
  }

  _bindJSAction(link, data) {
    link.href = this.linkService.getAnchorUrl("");
    const map = new Map([["Action", "onclick"], ["Mouse Up", "onmouseup"], ["Mouse Down", "onmousedown"]]);

    for (const name of Object.keys(data.actions)) {
      const jsName = map.get(name);

      if (!jsName) {
        continue;
      }

      link[jsName] = () => {
        var _this$linkService$eve;

        (_this$linkService$eve = this.linkService.eventBus) === null || _this$linkService$eve === void 0 ? void 0 : _this$linkService$eve.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id: data.id,
            name
          }
        });
        return false;
      };
    }

    if (!link.onclick) {
      link.onclick = () => false;
    }

    link.className = "internalLink";
  }

  _bindResetFormAction(link, resetForm) {
    const otherClickAction = link.onclick;

    if (!otherClickAction) {
      link.href = this.linkService.getAnchorUrl("");
    }

    link.className = "internalLink";

    if (!this._fieldObjects) {
      (0, _util.warn)(`_bindResetFormAction - "resetForm" action not supported, ` + "ensure that the `fieldObjects` parameter is provided.");

      if (!otherClickAction) {
        link.onclick = () => false;
      }

      return;
    }

    link.onclick = () => {
      if (otherClickAction) {
        otherClickAction();
      }

      const {
        fields: resetFormFields,
        refs: resetFormRefs,
        include
      } = resetForm;
      const allFields = [];

      if (resetFormFields.length !== 0 || resetFormRefs.length !== 0) {
        const fieldIds = new Set(resetFormRefs);

        for (const fieldName of resetFormFields) {
          const fields = this._fieldObjects[fieldName] || [];

          for (const {
            id
          } of fields) {
            fieldIds.add(id);
          }
        }

        for (const fields of Object.values(this._fieldObjects)) {
          for (const field of fields) {
            if (fieldIds.has(field.id) === include) {
              allFields.push(field);
            }
          }
        }
      } else {
        for (const fields of Object.values(this._fieldObjects)) {
          allFields.push(...fields);
        }
      }

      const storage = this.annotationStorage;
      const allIds = [];

      for (const field of allFields) {
        const {
          id
        } = field;
        allIds.push(id);

        switch (field.type) {
          case "text":
            {
              const value = field.defaultValue || "";
              storage.setValue(id, {
                value
              });
              break;
            }

          case "checkbox":
          case "radiobutton":
            {
              const value = field.defaultValue === field.exportValues;
              storage.setValue(id, {
                value
              });
              break;
            }

          case "combobox":
          case "listbox":
            {
              const value = field.defaultValue || "";
              storage.setValue(id, {
                value
              });
              break;
            }

          default:
            continue;
        }

        const domElement = document.querySelector(`[data-element-id="${id}"]`);

        if (!domElement) {
          continue;
        } else if (!GetElementsByNameSet.has(domElement)) {
          (0, _util.warn)(`_bindResetFormAction - element not allowed: ${id}`);
          continue;
        }

        domElement.dispatchEvent(new Event("resetform"));
      }

      if (this.enableScripting) {
        var _this$linkService$eve2;

        (_this$linkService$eve2 = this.linkService.eventBus) === null || _this$linkService$eve2 === void 0 ? void 0 : _this$linkService$eve2.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id: "app",
            ids: allIds,
            name: "ResetForm"
          }
        });
      }

      return false;
    };
  }

}

class TextAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl, _parameters$data$cont, _parameters$data$rich;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl = parameters.data.titleObj) !== null && _parameters$data$titl !== void 0 && _parameters$data$titl.str || (_parameters$data$cont = parameters.data.contentsObj) !== null && _parameters$data$cont !== void 0 && _parameters$data$cont.str || (_parameters$data$rich = parameters.data.richText) !== null && _parameters$data$rich !== void 0 && _parameters$data$rich.str);
    super(parameters, {
      isRenderable
    });
  }

  render() {
    this.container.className = "textAnnotation";
    const image = document.createElement("img");
    image.src = this.imageResourcesPath + "annotation-" + this.data.name.toLowerCase() + ".svg";
    image.alt = "[{{type}} Annotation]";
    image.dataset.l10nId = "text_annotation_type";
    image.dataset.l10nArgs = JSON.stringify({
      type: this.data.name
    });

    if (!this.data.hasPopup) {
      this._createPopup(image, this.data);
    }

    this.container.append(image);
    return this.container;
  }

}

class WidgetAnnotationElement extends AnnotationElement {
  render() {
    if (this.data.alternativeText) {
      this.container.title = this.data.alternativeText;
    }

    return this.container;
  }

  _getKeyModifier(event) {
    const {
      isWin,
      isMac
    } = AnnotationElement.platform;
    return isWin && event.ctrlKey || isMac && event.metaKey;
  }

  _setEventListener(element, baseName, eventName, valueGetter) {
    if (baseName.includes("mouse")) {
      element.addEventListener(baseName, event => {
        var _this$linkService$eve3;

        (_this$linkService$eve3 = this.linkService.eventBus) === null || _this$linkService$eve3 === void 0 ? void 0 : _this$linkService$eve3.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id: this.data.id,
            name: eventName,
            value: valueGetter(event),
            shift: event.shiftKey,
            modifier: this._getKeyModifier(event)
          }
        });
      });
    } else {
      element.addEventListener(baseName, event => {
        var _this$linkService$eve4;

        (_this$linkService$eve4 = this.linkService.eventBus) === null || _this$linkService$eve4 === void 0 ? void 0 : _this$linkService$eve4.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id: this.data.id,
            name: eventName,
            value: valueGetter(event)
          }
        });
      });
    }
  }

  _setEventListeners(element, names, getter) {
    for (const [baseName, eventName] of names) {
      var _this$data$actions;

      if (eventName === "Action" || (_this$data$actions = this.data.actions) !== null && _this$data$actions !== void 0 && _this$data$actions[eventName]) {
        this._setEventListener(element, baseName, eventName, getter);
      }
    }
  }

  _setBackgroundColor(element) {
    const color = this.data.backgroundColor || null;
    element.style.backgroundColor = color === null ? "transparent" : _util.Util.makeHexColor(color[0], color[1], color[2]);
  }

  _setTextStyle(element) {
    const TEXT_ALIGNMENT = ["left", "center", "right"];
    const {
      fontColor
    } = this.data.defaultAppearanceData;
    const fontSize = this.data.defaultAppearanceData.fontSize || DEFAULT_FONT_SIZE;
    const style = element.style;
    let computedFontSize;

    if (this.data.multiLine) {
      const height = Math.abs(this.data.rect[3] - this.data.rect[1]);
      const numberOfLines = Math.round(height / (_util.LINE_FACTOR * fontSize)) || 1;
      const lineHeight = height / numberOfLines;
      computedFontSize = Math.min(fontSize, Math.round(lineHeight / _util.LINE_FACTOR));
    } else {
      const height = Math.abs(this.data.rect[3] - this.data.rect[1]);
      computedFontSize = Math.min(fontSize, Math.round(height / _util.LINE_FACTOR));
    }

    style.fontSize = `calc(${computedFontSize}px * var(--scale-factor))`;
    style.color = _util.Util.makeHexColor(fontColor[0], fontColor[1], fontColor[2]);

    if (this.data.textAlignment !== null) {
      style.textAlign = TEXT_ALIGNMENT[this.data.textAlignment];
    }
  }

  _setRequired(element, isRequired) {
    if (isRequired) {
      element.setAttribute("required", true);
    } else {
      element.removeAttribute("required");
    }

    element.setAttribute("aria-required", isRequired);
  }

}

class TextWidgetAnnotationElement extends WidgetAnnotationElement {
  constructor(parameters) {
    const isRenderable = parameters.renderForms || !parameters.data.hasAppearance && !!parameters.data.fieldValue;
    super(parameters, {
      isRenderable
    });
  }

  setPropertyOnSiblings(base, key, value, keyInStorage) {
    const storage = this.annotationStorage;

    for (const element of this._getElementsByName(base.name, base.id)) {
      if (element.domElement) {
        element.domElement[key] = value;
      }

      storage.setValue(element.id, {
        [keyInStorage]: value
      });
    }
  }

  render() {
    const storage = this.annotationStorage;
    const id = this.data.id;
    this.container.className = "textWidgetAnnotation";
    let element = null;

    if (this.renderForms) {
      const storedData = storage.getValue(id, {
        value: this.data.fieldValue
      });
      let textContent = storedData.formattedValue || storedData.value || "";
      const maxLen = storage.getValue(id, {
        charLimit: this.data.maxLen
      }).charLimit;

      if (maxLen && textContent.length > maxLen) {
        textContent = textContent.slice(0, maxLen);
      }

      const elementData = {
        userValue: textContent,
        formattedValue: null,
        valueOnFocus: ""
      };

      if (this.data.multiLine) {
        element = document.createElement("textarea");
        element.textContent = textContent;

        if (this.data.doNotScroll) {
          element.style.overflowY = "hidden";
        }
      } else {
        element = document.createElement("input");
        element.type = "text";
        element.setAttribute("value", textContent);

        if (this.data.doNotScroll) {
          element.style.overflowX = "hidden";
        }
      }

      GetElementsByNameSet.add(element);
      element.setAttribute("data-element-id", id);
      element.disabled = this.data.readOnly;
      element.name = this.data.fieldName;
      element.tabIndex = DEFAULT_TAB_INDEX;

      this._setRequired(element, this.data.required);

      if (maxLen) {
        element.maxLength = maxLen;
      }

      element.addEventListener("input", event => {
        storage.setValue(id, {
          value: event.target.value
        });
        this.setPropertyOnSiblings(element, "value", event.target.value, "value");
      });
      element.addEventListener("resetform", event => {
        var _this$data$defaultFie;

        const defaultValue = (_this$data$defaultFie = this.data.defaultFieldValue) !== null && _this$data$defaultFie !== void 0 ? _this$data$defaultFie : "";
        element.value = elementData.userValue = defaultValue;
        elementData.formattedValue = null;
      });

      let blurListener = event => {
        const {
          formattedValue
        } = elementData;

        if (formattedValue !== null && formattedValue !== undefined) {
          event.target.value = formattedValue;
        }

        event.target.scrollLeft = 0;
      };

      if (this.enableScripting && this.hasJSActions) {
        var _this$data$actions2;

        element.addEventListener("focus", event => {
          if (elementData.userValue) {
            event.target.value = elementData.userValue;
          }

          elementData.valueOnFocus = event.target.value;
        });
        element.addEventListener("updatefromsandbox", jsEvent => {
          const actions = {
            value(event) {
              var _event$detail$value;

              elementData.userValue = (_event$detail$value = event.detail.value) !== null && _event$detail$value !== void 0 ? _event$detail$value : "";
              storage.setValue(id, {
                value: elementData.userValue.toString()
              });
              event.target.value = elementData.userValue;
            },

            formattedValue(event) {
              const {
                formattedValue
              } = event.detail;
              elementData.formattedValue = formattedValue;

              if (formattedValue !== null && formattedValue !== undefined && event.target !== document.activeElement) {
                event.target.value = formattedValue;
              }

              storage.setValue(id, {
                formattedValue
              });
            },

            selRange(event) {
              event.target.setSelectionRange(...event.detail.selRange);
            },

            charLimit: event => {
              var _this$linkService$eve5;

              const {
                charLimit
              } = event.detail;
              const {
                target
              } = event;

              if (charLimit === 0) {
                target.removeAttribute("maxLength");
                return;
              }

              target.setAttribute("maxLength", charLimit);
              let value = elementData.userValue;

              if (!value || value.length <= charLimit) {
                return;
              }

              value = value.slice(0, charLimit);
              target.value = elementData.userValue = value;
              storage.setValue(id, {
                value
              });
              (_this$linkService$eve5 = this.linkService.eventBus) === null || _this$linkService$eve5 === void 0 ? void 0 : _this$linkService$eve5.dispatch("dispatcheventinsandbox", {
                source: this,
                detail: {
                  id,
                  name: "Keystroke",
                  value,
                  willCommit: true,
                  commitKey: 1,
                  selStart: target.selectionStart,
                  selEnd: target.selectionEnd
                }
              });
            }
          };

          this._dispatchEventFromSandbox(actions, jsEvent);
        });
        element.addEventListener("keydown", event => {
          var _this$linkService$eve6;

          let commitKey = -1;

          if (event.key === "Escape") {
            commitKey = 0;
          } else if (event.key === "Enter") {
            commitKey = 2;
          } else if (event.key === "Tab") {
            commitKey = 3;
          }

          if (commitKey === -1) {
            return;
          }

          const {
            value
          } = event.target;

          if (elementData.valueOnFocus === value) {
            return;
          }

          elementData.userValue = value;
          (_this$linkService$eve6 = this.linkService.eventBus) === null || _this$linkService$eve6 === void 0 ? void 0 : _this$linkService$eve6.dispatch("dispatcheventinsandbox", {
            source: this,
            detail: {
              id,
              name: "Keystroke",
              value,
              willCommit: true,
              commitKey,
              selStart: event.target.selectionStart,
              selEnd: event.target.selectionEnd
            }
          });
        });
        const _blurListener = blurListener;
        blurListener = null;
        element.addEventListener("blur", event => {
          const {
            value
          } = event.target;
          elementData.userValue = value;

          if (this._mouseState.isDown && elementData.valueOnFocus !== value) {
            var _this$linkService$eve7;

            (_this$linkService$eve7 = this.linkService.eventBus) === null || _this$linkService$eve7 === void 0 ? void 0 : _this$linkService$eve7.dispatch("dispatcheventinsandbox", {
              source: this,
              detail: {
                id,
                name: "Keystroke",
                value,
                willCommit: true,
                commitKey: 1,
                selStart: event.target.selectionStart,
                selEnd: event.target.selectionEnd
              }
            });
          }

          _blurListener(event);
        });

        if ((_this$data$actions2 = this.data.actions) !== null && _this$data$actions2 !== void 0 && _this$data$actions2.Keystroke) {
          element.addEventListener("beforeinput", event => {
            var _this$linkService$eve8;

            const {
              data,
              target
            } = event;
            const {
              value,
              selectionStart,
              selectionEnd
            } = target;
            let selStart = selectionStart,
                selEnd = selectionEnd;

            switch (event.inputType) {
              case "deleteWordBackward":
                {
                  const match = value.substring(0, selectionStart).match(/\w*[^\w]*$/);

                  if (match) {
                    selStart -= match[0].length;
                  }

                  break;
                }

              case "deleteWordForward":
                {
                  const match = value.substring(selectionStart).match(/^[^\w]*\w*/);

                  if (match) {
                    selEnd += match[0].length;
                  }

                  break;
                }

              case "deleteContentBackward":
                if (selectionStart === selectionEnd) {
                  selStart -= 1;
                }

                break;

              case "deleteContentForward":
                if (selectionStart === selectionEnd) {
                  selEnd += 1;
                }

                break;
            }

            event.preventDefault();
            (_this$linkService$eve8 = this.linkService.eventBus) === null || _this$linkService$eve8 === void 0 ? void 0 : _this$linkService$eve8.dispatch("dispatcheventinsandbox", {
              source: this,
              detail: {
                id,
                name: "Keystroke",
                value,
                change: data || "",
                willCommit: false,
                selStart,
                selEnd
              }
            });
          });
        }

        this._setEventListeners(element, [["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.value);
      }

      if (blurListener) {
        element.addEventListener("blur", blurListener);
      }

      if (this.data.comb) {
        const fieldWidth = this.data.rect[2] - this.data.rect[0];
        const combWidth = fieldWidth / maxLen;
        element.classList.add("comb");
        element.style.letterSpacing = `calc(${combWidth}px * var(--scale-factor) - 1ch)`;
      }
    } else {
      element = document.createElement("div");
      element.textContent = this.data.fieldValue;
      element.style.verticalAlign = "middle";
      element.style.display = "table-cell";
    }

    this._setTextStyle(element);

    this._setBackgroundColor(element);

    this._setDefaultPropertiesFromJS(element);

    this.container.append(element);
    return this.container;
  }

}

class CheckboxWidgetAnnotationElement extends WidgetAnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: parameters.renderForms
    });
  }

  render() {
    const storage = this.annotationStorage;
    const data = this.data;
    const id = data.id;
    let value = storage.getValue(id, {
      value: data.exportValue === data.fieldValue
    }).value;

    if (typeof value === "string") {
      value = value !== "Off";
      storage.setValue(id, {
        value
      });
    }

    this.container.className = "buttonWidgetAnnotation checkBox";
    const element = document.createElement("input");
    GetElementsByNameSet.add(element);
    element.setAttribute("data-element-id", id);
    element.disabled = data.readOnly;

    this._setRequired(element, this.data.required);

    element.type = "checkbox";
    element.name = data.fieldName;

    if (value) {
      element.setAttribute("checked", true);
    }

    element.setAttribute("exportValue", data.exportValue);
    element.tabIndex = DEFAULT_TAB_INDEX;
    element.addEventListener("change", event => {
      const {
        name,
        checked
      } = event.target;

      for (const checkbox of this._getElementsByName(name, id)) {
        const curChecked = checked && checkbox.exportValue === data.exportValue;

        if (checkbox.domElement) {
          checkbox.domElement.checked = curChecked;
        }

        storage.setValue(checkbox.id, {
          value: curChecked
        });
      }

      storage.setValue(id, {
        value: checked
      });
    });
    element.addEventListener("resetform", event => {
      const defaultValue = data.defaultFieldValue || "Off";
      event.target.checked = defaultValue === data.exportValue;
    });

    if (this.enableScripting && this.hasJSActions) {
      element.addEventListener("updatefromsandbox", jsEvent => {
        const actions = {
          value(event) {
            event.target.checked = event.detail.value !== "Off";
            storage.setValue(id, {
              value: event.target.checked
            });
          }

        };

        this._dispatchEventFromSandbox(actions, jsEvent);
      });

      this._setEventListeners(element, [["change", "Validate"], ["change", "Action"], ["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.checked);
    }

    this._setBackgroundColor(element);

    this._setDefaultPropertiesFromJS(element);

    this.container.append(element);
    return this.container;
  }

}

class RadioButtonWidgetAnnotationElement extends WidgetAnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: parameters.renderForms
    });
  }

  render() {
    this.container.className = "buttonWidgetAnnotation radioButton";
    const storage = this.annotationStorage;
    const data = this.data;
    const id = data.id;
    let value = storage.getValue(id, {
      value: data.fieldValue === data.buttonValue
    }).value;

    if (typeof value === "string") {
      value = value !== data.buttonValue;
      storage.setValue(id, {
        value
      });
    }

    const element = document.createElement("input");
    GetElementsByNameSet.add(element);
    element.setAttribute("data-element-id", id);
    element.disabled = data.readOnly;

    this._setRequired(element, this.data.required);

    element.type = "radio";
    element.name = data.fieldName;

    if (value) {
      element.setAttribute("checked", true);
    }

    element.tabIndex = DEFAULT_TAB_INDEX;
    element.addEventListener("change", event => {
      const {
        name,
        checked
      } = event.target;

      for (const radio of this._getElementsByName(name, id)) {
        storage.setValue(radio.id, {
          value: false
        });
      }

      storage.setValue(id, {
        value: checked
      });
    });
    element.addEventListener("resetform", event => {
      const defaultValue = data.defaultFieldValue;
      event.target.checked = defaultValue !== null && defaultValue !== undefined && defaultValue === data.buttonValue;
    });

    if (this.enableScripting && this.hasJSActions) {
      const pdfButtonValue = data.buttonValue;
      element.addEventListener("updatefromsandbox", jsEvent => {
        const actions = {
          value: event => {
            const checked = pdfButtonValue === event.detail.value;

            for (const radio of this._getElementsByName(event.target.name)) {
              const curChecked = checked && radio.id === id;

              if (radio.domElement) {
                radio.domElement.checked = curChecked;
              }

              storage.setValue(radio.id, {
                value: curChecked
              });
            }
          }
        };

        this._dispatchEventFromSandbox(actions, jsEvent);
      });

      this._setEventListeners(element, [["change", "Validate"], ["change", "Action"], ["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.checked);
    }

    this._setBackgroundColor(element);

    this._setDefaultPropertiesFromJS(element);

    this.container.append(element);
    return this.container;
  }

}

class PushButtonWidgetAnnotationElement extends LinkAnnotationElement {
  constructor(parameters) {
    super(parameters, {
      ignoreBorder: parameters.data.hasAppearance
    });
  }

  render() {
    const container = super.render();
    container.className = "buttonWidgetAnnotation pushButton";

    if (this.data.alternativeText) {
      container.title = this.data.alternativeText;
    }

    const linkElement = container.lastChild;

    if (this.enableScripting && this.hasJSActions && linkElement) {
      this._setDefaultPropertiesFromJS(linkElement);

      linkElement.addEventListener("updatefromsandbox", jsEvent => {
        this._dispatchEventFromSandbox({}, jsEvent);
      });
    }

    return container;
  }

}

class ChoiceWidgetAnnotationElement extends WidgetAnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: parameters.renderForms
    });
  }

  render() {
    this.container.className = "choiceWidgetAnnotation";
    const storage = this.annotationStorage;
    const id = this.data.id;
    const storedData = storage.getValue(id, {
      value: this.data.fieldValue
    });
    const selectElement = document.createElement("select");
    GetElementsByNameSet.add(selectElement);
    selectElement.setAttribute("data-element-id", id);
    selectElement.disabled = this.data.readOnly;

    this._setRequired(selectElement, this.data.required);

    selectElement.name = this.data.fieldName;
    selectElement.tabIndex = DEFAULT_TAB_INDEX;
    let addAnEmptyEntry = this.data.combo && this.data.options.length > 0;

    if (!this.data.combo) {
      selectElement.size = this.data.options.length;

      if (this.data.multiSelect) {
        selectElement.multiple = true;
      }
    }

    selectElement.addEventListener("resetform", event => {
      const defaultValue = this.data.defaultFieldValue;

      for (const option of selectElement.options) {
        option.selected = option.value === defaultValue;
      }
    });

    for (const option of this.data.options) {
      const optionElement = document.createElement("option");
      optionElement.textContent = option.displayValue;
      optionElement.value = option.exportValue;

      if (storedData.value.includes(option.exportValue)) {
        optionElement.setAttribute("selected", true);
        addAnEmptyEntry = false;
      }

      selectElement.append(optionElement);
    }

    let removeEmptyEntry = null;

    if (addAnEmptyEntry) {
      const noneOptionElement = document.createElement("option");
      noneOptionElement.value = " ";
      noneOptionElement.setAttribute("hidden", true);
      noneOptionElement.setAttribute("selected", true);
      selectElement.prepend(noneOptionElement);

      removeEmptyEntry = () => {
        noneOptionElement.remove();
        selectElement.removeEventListener("input", removeEmptyEntry);
        removeEmptyEntry = null;
      };

      selectElement.addEventListener("input", removeEmptyEntry);
    }

    const getValue = (event, isExport) => {
      const name = isExport ? "value" : "textContent";
      const options = event.target.options;

      if (!event.target.multiple) {
        return options.selectedIndex === -1 ? null : options[options.selectedIndex][name];
      }

      return Array.prototype.filter.call(options, option => option.selected).map(option => option[name]);
    };

    const getItems = event => {
      const options = event.target.options;
      return Array.prototype.map.call(options, option => {
        return {
          displayValue: option.textContent,
          exportValue: option.value
        };
      });
    };

    if (this.enableScripting && this.hasJSActions) {
      selectElement.addEventListener("updatefromsandbox", jsEvent => {
        const actions = {
          value(event) {
            var _removeEmptyEntry;

            (_removeEmptyEntry = removeEmptyEntry) === null || _removeEmptyEntry === void 0 ? void 0 : _removeEmptyEntry();
            const value = event.detail.value;
            const values = new Set(Array.isArray(value) ? value : [value]);

            for (const option of selectElement.options) {
              option.selected = values.has(option.value);
            }

            storage.setValue(id, {
              value: getValue(event, true)
            });
          },

          multipleSelection(event) {
            selectElement.multiple = true;
          },

          remove(event) {
            const options = selectElement.options;
            const index = event.detail.remove;
            options[index].selected = false;
            selectElement.remove(index);

            if (options.length > 0) {
              const i = Array.prototype.findIndex.call(options, option => option.selected);

              if (i === -1) {
                options[0].selected = true;
              }
            }

            storage.setValue(id, {
              value: getValue(event, true),
              items: getItems(event)
            });
          },

          clear(event) {
            while (selectElement.length !== 0) {
              selectElement.remove(0);
            }

            storage.setValue(id, {
              value: null,
              items: []
            });
          },

          insert(event) {
            const {
              index,
              displayValue,
              exportValue
            } = event.detail.insert;
            const selectChild = selectElement.children[index];
            const optionElement = document.createElement("option");
            optionElement.textContent = displayValue;
            optionElement.value = exportValue;

            if (selectChild) {
              selectChild.before(optionElement);
            } else {
              selectElement.append(optionElement);
            }

            storage.setValue(id, {
              value: getValue(event, true),
              items: getItems(event)
            });
          },

          items(event) {
            const {
              items
            } = event.detail;

            while (selectElement.length !== 0) {
              selectElement.remove(0);
            }

            for (const item of items) {
              const {
                displayValue,
                exportValue
              } = item;
              const optionElement = document.createElement("option");
              optionElement.textContent = displayValue;
              optionElement.value = exportValue;
              selectElement.append(optionElement);
            }

            if (selectElement.options.length > 0) {
              selectElement.options[0].selected = true;
            }

            storage.setValue(id, {
              value: getValue(event, true),
              items: getItems(event)
            });
          },

          indices(event) {
            const indices = new Set(event.detail.indices);

            for (const option of event.target.options) {
              option.selected = indices.has(option.index);
            }

            storage.setValue(id, {
              value: getValue(event, true)
            });
          },

          editable(event) {
            event.target.disabled = !event.detail.editable;
          }

        };

        this._dispatchEventFromSandbox(actions, jsEvent);
      });
      selectElement.addEventListener("input", event => {
        var _this$linkService$eve9;

        const exportValue = getValue(event, true);
        const value = getValue(event, false);
        storage.setValue(id, {
          value: exportValue
        });
        (_this$linkService$eve9 = this.linkService.eventBus) === null || _this$linkService$eve9 === void 0 ? void 0 : _this$linkService$eve9.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id,
            name: "Keystroke",
            value,
            changeEx: exportValue,
            willCommit: true,
            commitKey: 1,
            keyDown: false
          }
        });
      });

      this._setEventListeners(selectElement, [["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"], ["input", "Action"]], event => event.target.checked);
    } else {
      selectElement.addEventListener("input", function (event) {
        storage.setValue(id, {
          value: getValue(event, true)
        });
      });
    }

    if (this.data.combo) {
      this._setTextStyle(selectElement);
    } else {}

    this._setBackgroundColor(selectElement);

    this._setDefaultPropertiesFromJS(selectElement);

    this.container.append(selectElement);
    return this.container;
  }

}

class PopupAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl2, _parameters$data$cont2, _parameters$data$rich2;

    const isRenderable = !!((_parameters$data$titl2 = parameters.data.titleObj) !== null && _parameters$data$titl2 !== void 0 && _parameters$data$titl2.str || (_parameters$data$cont2 = parameters.data.contentsObj) !== null && _parameters$data$cont2 !== void 0 && _parameters$data$cont2.str || (_parameters$data$rich2 = parameters.data.richText) !== null && _parameters$data$rich2 !== void 0 && _parameters$data$rich2.str);
    super(parameters, {
      isRenderable
    });
  }

  render() {
    const IGNORE_TYPES = ["Line", "Square", "Circle", "PolyLine", "Polygon", "Ink"];
    this.container.className = "popupAnnotation";

    if (IGNORE_TYPES.includes(this.data.parentType)) {
      return this.container;
    }

    const selector = `[data-annotation-id="${this.data.parentId}"]`;
    const parentElements = this.layer.querySelectorAll(selector);

    if (parentElements.length === 0) {
      return this.container;
    }

    const popup = new PopupElement({
      container: this.container,
      trigger: Array.from(parentElements),
      color: this.data.color,
      titleObj: this.data.titleObj,
      modificationDate: this.data.modificationDate,
      contentsObj: this.data.contentsObj,
      richText: this.data.richText
    });
    const page = this.page;

    const rect = _util.Util.normalizeRect([this.data.parentRect[0], page.view[3] - this.data.parentRect[1] + page.view[1], this.data.parentRect[2], page.view[3] - this.data.parentRect[3] + page.view[1]]);

    const popupLeft = rect[0] + this.data.parentRect[2] - this.data.parentRect[0];
    const popupTop = rect[1];
    const [pageLLx, pageLLy, pageURx, pageURy] = this.viewport.viewBox;
    const pageWidth = pageURx - pageLLx;
    const pageHeight = pageURy - pageLLy;
    this.container.style.left = `${100 * (popupLeft - pageLLx) / pageWidth}%`;
    this.container.style.top = `${100 * (popupTop - pageLLy) / pageHeight}%`;
    this.container.append(popup.render());
    return this.container;
  }

}

class PopupElement {
  constructor(parameters) {
    this.container = parameters.container;
    this.trigger = parameters.trigger;
    this.color = parameters.color;
    this.titleObj = parameters.titleObj;
    this.modificationDate = parameters.modificationDate;
    this.contentsObj = parameters.contentsObj;
    this.richText = parameters.richText;
    this.hideWrapper = parameters.hideWrapper || false;
    this.pinned = false;
  }

  render() {
    var _this$richText, _this$contentsObj;

    const BACKGROUND_ENLIGHT = 0.7;
    const wrapper = document.createElement("div");
    wrapper.className = "popupWrapper";
    this.hideElement = this.hideWrapper ? wrapper : this.container;
    this.hideElement.hidden = true;
    const popup = document.createElement("div");
    popup.className = "popup";
    const color = this.color;

    if (color) {
      const r = BACKGROUND_ENLIGHT * (255 - color[0]) + color[0];
      const g = BACKGROUND_ENLIGHT * (255 - color[1]) + color[1];
      const b = BACKGROUND_ENLIGHT * (255 - color[2]) + color[2];
      popup.style.backgroundColor = _util.Util.makeHexColor(r | 0, g | 0, b | 0);
    }

    const title = document.createElement("h1");
    title.dir = this.titleObj.dir;
    title.textContent = this.titleObj.str;
    popup.append(title);

    const dateObject = _display_utils.PDFDateString.toDateObject(this.modificationDate);

    if (dateObject) {
      const modificationDate = document.createElement("span");
      modificationDate.className = "popupDate";
      modificationDate.textContent = "{{date}}, {{time}}";
      modificationDate.dataset.l10nId = "annotation_date_string";
      modificationDate.dataset.l10nArgs = JSON.stringify({
        date: dateObject.toLocaleDateString(),
        time: dateObject.toLocaleTimeString()
      });
      popup.append(modificationDate);
    }

    if ((_this$richText = this.richText) !== null && _this$richText !== void 0 && _this$richText.str && (!((_this$contentsObj = this.contentsObj) !== null && _this$contentsObj !== void 0 && _this$contentsObj.str) || this.contentsObj.str === this.richText.str)) {
      _xfa_layer.XfaLayer.render({
        xfaHtml: this.richText.html,
        intent: "richText",
        div: popup
      });

      popup.lastChild.className = "richText popupContent";
    } else {
      const contents = this._formatContents(this.contentsObj);

      popup.append(contents);
    }

    if (!Array.isArray(this.trigger)) {
      this.trigger = [this.trigger];
    }

    for (const element of this.trigger) {
      element.addEventListener("click", this._toggle.bind(this));
      element.addEventListener("mouseover", this._show.bind(this, false));
      element.addEventListener("mouseout", this._hide.bind(this, false));
    }

    popup.addEventListener("click", this._hide.bind(this, true));
    wrapper.append(popup);
    return wrapper;
  }

  _formatContents(_ref) {
    let {
      str,
      dir
    } = _ref;
    const p = document.createElement("p");
    p.className = "popupContent";
    p.dir = dir;
    const lines = str.split(/(?:\r\n?|\n)/);

    for (let i = 0, ii = lines.length; i < ii; ++i) {
      const line = lines[i];
      p.append(document.createTextNode(line));

      if (i < ii - 1) {
        p.append(document.createElement("br"));
      }
    }

    return p;
  }

  _toggle() {
    if (this.pinned) {
      this._hide(true);
    } else {
      this._show(true);
    }
  }

  _show() {
    let pin = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

    if (pin) {
      this.pinned = true;
    }

    if (this.hideElement.hidden) {
      this.hideElement.hidden = false;
      this.container.style.zIndex = parseInt(this.container.style.zIndex) + 1000;
    }
  }

  _hide() {
    let unpin = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : true;

    if (unpin) {
      this.pinned = false;
    }

    if (!this.hideElement.hidden && !this.pinned) {
      this.hideElement.hidden = true;
      this.container.style.zIndex = parseInt(this.container.style.zIndex) - 1000;
    }
  }

}

class FreeTextAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl3, _parameters$data$cont3, _parameters$data$rich3;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl3 = parameters.data.titleObj) !== null && _parameters$data$titl3 !== void 0 && _parameters$data$titl3.str || (_parameters$data$cont3 = parameters.data.contentsObj) !== null && _parameters$data$cont3 !== void 0 && _parameters$data$cont3.str || (_parameters$data$rich3 = parameters.data.richText) !== null && _parameters$data$rich3 !== void 0 && _parameters$data$rich3.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
    this.textContent = parameters.data.textContent;
  }

  render() {
    this.container.className = "freeTextAnnotation";

    if (this.textContent) {
      const content = document.createElement("div");
      content.className = "annotationTextContent";
      content.setAttribute("role", "comment");

      for (const line of this.textContent) {
        const lineSpan = document.createElement("span");
        lineSpan.textContent = line;
        content.append(lineSpan);
      }

      this.container.append(content);
    }

    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    return this.container;
  }

}

class LineAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl4, _parameters$data$cont4, _parameters$data$rich4;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl4 = parameters.data.titleObj) !== null && _parameters$data$titl4 !== void 0 && _parameters$data$titl4.str || (_parameters$data$cont4 = parameters.data.contentsObj) !== null && _parameters$data$cont4 !== void 0 && _parameters$data$cont4.str || (_parameters$data$rich4 = parameters.data.richText) !== null && _parameters$data$rich4 !== void 0 && _parameters$data$rich4.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
  }

  render() {
    this.container.className = "lineAnnotation";
    const data = this.data;
    const {
      width,
      height
    } = getRectDims(data.rect);
    const svg = this.svgFactory.create(width, height, true);
    const line = this.svgFactory.createElement("svg:line");
    line.setAttribute("x1", data.rect[2] - data.lineCoordinates[0]);
    line.setAttribute("y1", data.rect[3] - data.lineCoordinates[1]);
    line.setAttribute("x2", data.rect[2] - data.lineCoordinates[2]);
    line.setAttribute("y2", data.rect[3] - data.lineCoordinates[3]);
    line.setAttribute("stroke-width", data.borderStyle.width || 1);
    line.setAttribute("stroke", "transparent");
    line.setAttribute("fill", "transparent");
    svg.append(line);
    this.container.append(svg);

    this._createPopup(line, data);

    return this.container;
  }

}

class SquareAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl5, _parameters$data$cont5, _parameters$data$rich5;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl5 = parameters.data.titleObj) !== null && _parameters$data$titl5 !== void 0 && _parameters$data$titl5.str || (_parameters$data$cont5 = parameters.data.contentsObj) !== null && _parameters$data$cont5 !== void 0 && _parameters$data$cont5.str || (_parameters$data$rich5 = parameters.data.richText) !== null && _parameters$data$rich5 !== void 0 && _parameters$data$rich5.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
  }

  render() {
    this.container.className = "squareAnnotation";
    const data = this.data;
    const {
      width,
      height
    } = getRectDims(data.rect);
    const svg = this.svgFactory.create(width, height, true);
    const borderWidth = data.borderStyle.width;
    const square = this.svgFactory.createElement("svg:rect");
    square.setAttribute("x", borderWidth / 2);
    square.setAttribute("y", borderWidth / 2);
    square.setAttribute("width", width - borderWidth);
    square.setAttribute("height", height - borderWidth);
    square.setAttribute("stroke-width", borderWidth || 1);
    square.setAttribute("stroke", "transparent");
    square.setAttribute("fill", "transparent");
    svg.append(square);
    this.container.append(svg);

    this._createPopup(square, data);

    return this.container;
  }

}

class CircleAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl6, _parameters$data$cont6, _parameters$data$rich6;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl6 = parameters.data.titleObj) !== null && _parameters$data$titl6 !== void 0 && _parameters$data$titl6.str || (_parameters$data$cont6 = parameters.data.contentsObj) !== null && _parameters$data$cont6 !== void 0 && _parameters$data$cont6.str || (_parameters$data$rich6 = parameters.data.richText) !== null && _parameters$data$rich6 !== void 0 && _parameters$data$rich6.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
  }

  render() {
    this.container.className = "circleAnnotation";
    const data = this.data;
    const {
      width,
      height
    } = getRectDims(data.rect);
    const svg = this.svgFactory.create(width, height, true);
    const borderWidth = data.borderStyle.width;
    const circle = this.svgFactory.createElement("svg:ellipse");
    circle.setAttribute("cx", width / 2);
    circle.setAttribute("cy", height / 2);
    circle.setAttribute("rx", width / 2 - borderWidth / 2);
    circle.setAttribute("ry", height / 2 - borderWidth / 2);
    circle.setAttribute("stroke-width", borderWidth || 1);
    circle.setAttribute("stroke", "transparent");
    circle.setAttribute("fill", "transparent");
    svg.append(circle);
    this.container.append(svg);

    this._createPopup(circle, data);

    return this.container;
  }

}

class PolylineAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl7, _parameters$data$cont7, _parameters$data$rich7;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl7 = parameters.data.titleObj) !== null && _parameters$data$titl7 !== void 0 && _parameters$data$titl7.str || (_parameters$data$cont7 = parameters.data.contentsObj) !== null && _parameters$data$cont7 !== void 0 && _parameters$data$cont7.str || (_parameters$data$rich7 = parameters.data.richText) !== null && _parameters$data$rich7 !== void 0 && _parameters$data$rich7.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
    this.containerClassName = "polylineAnnotation";
    this.svgElementName = "svg:polyline";
  }

  render() {
    this.container.className = this.containerClassName;
    const data = this.data;
    const {
      width,
      height
    } = getRectDims(data.rect);
    const svg = this.svgFactory.create(width, height, true);
    let points = [];

    for (const coordinate of data.vertices) {
      const x = coordinate.x - data.rect[0];
      const y = data.rect[3] - coordinate.y;
      points.push(x + "," + y);
    }

    points = points.join(" ");
    const polyline = this.svgFactory.createElement(this.svgElementName);
    polyline.setAttribute("points", points);
    polyline.setAttribute("stroke-width", data.borderStyle.width || 1);
    polyline.setAttribute("stroke", "transparent");
    polyline.setAttribute("fill", "transparent");
    svg.append(polyline);
    this.container.append(svg);

    this._createPopup(polyline, data);

    return this.container;
  }

}

class PolygonAnnotationElement extends PolylineAnnotationElement {
  constructor(parameters) {
    super(parameters);
    this.containerClassName = "polygonAnnotation";
    this.svgElementName = "svg:polygon";
  }

}

class CaretAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl8, _parameters$data$cont8, _parameters$data$rich8;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl8 = parameters.data.titleObj) !== null && _parameters$data$titl8 !== void 0 && _parameters$data$titl8.str || (_parameters$data$cont8 = parameters.data.contentsObj) !== null && _parameters$data$cont8 !== void 0 && _parameters$data$cont8.str || (_parameters$data$rich8 = parameters.data.richText) !== null && _parameters$data$rich8 !== void 0 && _parameters$data$rich8.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
  }

  render() {
    this.container.className = "caretAnnotation";

    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    return this.container;
  }

}

class InkAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl9, _parameters$data$cont9, _parameters$data$rich9;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl9 = parameters.data.titleObj) !== null && _parameters$data$titl9 !== void 0 && _parameters$data$titl9.str || (_parameters$data$cont9 = parameters.data.contentsObj) !== null && _parameters$data$cont9 !== void 0 && _parameters$data$cont9.str || (_parameters$data$rich9 = parameters.data.richText) !== null && _parameters$data$rich9 !== void 0 && _parameters$data$rich9.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
    this.containerClassName = "inkAnnotation";
    this.svgElementName = "svg:polyline";
  }

  render() {
    this.container.className = this.containerClassName;
    const data = this.data;
    const {
      width,
      height
    } = getRectDims(data.rect);
    const svg = this.svgFactory.create(width, height, true);

    for (const inkList of data.inkLists) {
      let points = [];

      for (const coordinate of inkList) {
        const x = coordinate.x - data.rect[0];
        const y = data.rect[3] - coordinate.y;
        points.push(`${x},${y}`);
      }

      points = points.join(" ");
      const polyline = this.svgFactory.createElement(this.svgElementName);
      polyline.setAttribute("points", points);
      polyline.setAttribute("stroke-width", data.borderStyle.width || 1);
      polyline.setAttribute("stroke", "transparent");
      polyline.setAttribute("fill", "transparent");

      this._createPopup(polyline, data);

      svg.append(polyline);
    }

    this.container.append(svg);
    return this.container;
  }

}

class HighlightAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl10, _parameters$data$cont10, _parameters$data$rich10;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl10 = parameters.data.titleObj) !== null && _parameters$data$titl10 !== void 0 && _parameters$data$titl10.str || (_parameters$data$cont10 = parameters.data.contentsObj) !== null && _parameters$data$cont10 !== void 0 && _parameters$data$cont10.str || (_parameters$data$rich10 = parameters.data.richText) !== null && _parameters$data$rich10 !== void 0 && _parameters$data$rich10.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }

  render() {
    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    if (this.quadrilaterals) {
      return this._renderQuadrilaterals("highlightAnnotation");
    }

    this.container.className = "highlightAnnotation";
    return this.container;
  }

}

class UnderlineAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl11, _parameters$data$cont11, _parameters$data$rich11;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl11 = parameters.data.titleObj) !== null && _parameters$data$titl11 !== void 0 && _parameters$data$titl11.str || (_parameters$data$cont11 = parameters.data.contentsObj) !== null && _parameters$data$cont11 !== void 0 && _parameters$data$cont11.str || (_parameters$data$rich11 = parameters.data.richText) !== null && _parameters$data$rich11 !== void 0 && _parameters$data$rich11.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }

  render() {
    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    if (this.quadrilaterals) {
      return this._renderQuadrilaterals("underlineAnnotation");
    }

    this.container.className = "underlineAnnotation";
    return this.container;
  }

}

class SquigglyAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl12, _parameters$data$cont12, _parameters$data$rich12;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl12 = parameters.data.titleObj) !== null && _parameters$data$titl12 !== void 0 && _parameters$data$titl12.str || (_parameters$data$cont12 = parameters.data.contentsObj) !== null && _parameters$data$cont12 !== void 0 && _parameters$data$cont12.str || (_parameters$data$rich12 = parameters.data.richText) !== null && _parameters$data$rich12 !== void 0 && _parameters$data$rich12.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }

  render() {
    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    if (this.quadrilaterals) {
      return this._renderQuadrilaterals("squigglyAnnotation");
    }

    this.container.className = "squigglyAnnotation";
    return this.container;
  }

}

class StrikeOutAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl13, _parameters$data$cont13, _parameters$data$rich13;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl13 = parameters.data.titleObj) !== null && _parameters$data$titl13 !== void 0 && _parameters$data$titl13.str || (_parameters$data$cont13 = parameters.data.contentsObj) !== null && _parameters$data$cont13 !== void 0 && _parameters$data$cont13.str || (_parameters$data$rich13 = parameters.data.richText) !== null && _parameters$data$rich13 !== void 0 && _parameters$data$rich13.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }

  render() {
    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    if (this.quadrilaterals) {
      return this._renderQuadrilaterals("strikeoutAnnotation");
    }

    this.container.className = "strikeoutAnnotation";
    return this.container;
  }

}

class StampAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _parameters$data$titl14, _parameters$data$cont14, _parameters$data$rich14;

    const isRenderable = !!(parameters.data.hasPopup || (_parameters$data$titl14 = parameters.data.titleObj) !== null && _parameters$data$titl14 !== void 0 && _parameters$data$titl14.str || (_parameters$data$cont14 = parameters.data.contentsObj) !== null && _parameters$data$cont14 !== void 0 && _parameters$data$cont14.str || (_parameters$data$rich14 = parameters.data.richText) !== null && _parameters$data$rich14 !== void 0 && _parameters$data$rich14.str);
    super(parameters, {
      isRenderable,
      ignoreBorder: true
    });
  }

  render() {
    this.container.className = "stampAnnotation";

    if (!this.data.hasPopup) {
      this._createPopup(null, this.data);
    }

    return this.container;
  }

}

class FileAttachmentAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    var _this$linkService$eve10;

    super(parameters, {
      isRenderable: true
    });
    const {
      filename,
      content
    } = this.data.file;
    this.filename = (0, _display_utils.getFilenameFromUrl)(filename);
    this.content = content;
    (_this$linkService$eve10 = this.linkService.eventBus) === null || _this$linkService$eve10 === void 0 ? void 0 : _this$linkService$eve10.dispatch("fileattachmentannotation", {
      source: this,
      filename,
      content
    });
  }

  render() {
    var _this$data$titleObj, _this$data$contentsOb;

    this.container.className = "fileAttachmentAnnotation";
    const trigger = document.createElement("div");
    trigger.className = "popupTriggerArea";
    trigger.addEventListener("dblclick", this._download.bind(this));

    if (!this.data.hasPopup && ((_this$data$titleObj = this.data.titleObj) !== null && _this$data$titleObj !== void 0 && _this$data$titleObj.str || (_this$data$contentsOb = this.data.contentsObj) !== null && _this$data$contentsOb !== void 0 && _this$data$contentsOb.str || this.data.richText)) {
      this._createPopup(trigger, this.data);
    }

    this.container.append(trigger);
    return this.container;
  }

  _download() {
    var _this$downloadManager;

    (_this$downloadManager = this.downloadManager) === null || _this$downloadManager === void 0 ? void 0 : _this$downloadManager.openOrDownloadData(this.container, this.content, this.filename);
  }

}

class AnnotationLayer {
  static render(parameters) {
    const {
      annotations,
      div,
      viewport,
      accessibilityManager
    } = parameters;

    _classStaticPrivateMethodGet(this, AnnotationLayer, _setDimensions).call(this, div, viewport);

    let zIndex = 0;

    for (const data of annotations) {
      if (data.annotationType !== _util.AnnotationType.POPUP) {
        const {
          width,
          height
        } = getRectDims(data.rect);

        if (width <= 0 || height <= 0) {
          continue;
        }
      }

      const element = AnnotationElementFactory.create({
        data,
        layer: div,
        page: parameters.page,
        viewport,
        linkService: parameters.linkService,
        downloadManager: parameters.downloadManager,
        imageResourcesPath: parameters.imageResourcesPath || "",
        renderForms: parameters.renderForms !== false,
        svgFactory: new _display_utils.DOMSVGFactory(),
        annotationStorage: parameters.annotationStorage || new _annotation_storage.AnnotationStorage(),
        enableScripting: parameters.enableScripting,
        hasJSActions: parameters.hasJSActions,
        fieldObjects: parameters.fieldObjects,
        mouseState: parameters.mouseState || {
          isDown: false
        }
      });

      if (element.isRenderable) {
        const rendered = element.render();

        if (data.hidden) {
          rendered.style.visibility = "hidden";
        }

        if (Array.isArray(rendered)) {
          for (const renderedElement of rendered) {
            renderedElement.style.zIndex = zIndex++;

            _classStaticPrivateMethodGet(AnnotationLayer, AnnotationLayer, _appendElement).call(AnnotationLayer, renderedElement, data.id, div, accessibilityManager);
          }
        } else {
          rendered.style.zIndex = zIndex++;

          if (element instanceof PopupAnnotationElement) {
            div.prepend(rendered);
          } else {
            _classStaticPrivateMethodGet(AnnotationLayer, AnnotationLayer, _appendElement).call(AnnotationLayer, rendered, data.id, div, accessibilityManager);
          }
        }
      }
    }

    _classStaticPrivateMethodGet(this, AnnotationLayer, _setAnnotationCanvasMap).call(this, div, parameters.annotationCanvasMap);
  }

  static update(parameters) {
    const {
      annotationCanvasMap,
      div,
      viewport
    } = parameters;

    _classStaticPrivateMethodGet(this, AnnotationLayer, _setDimensions).call(this, div, viewport);

    _classStaticPrivateMethodGet(this, AnnotationLayer, _setAnnotationCanvasMap).call(this, div, annotationCanvasMap);

    div.hidden = false;
  }

}

exports.AnnotationLayer = AnnotationLayer;

function _appendElement(element, id, div, accessibilityManager) {
  const contentElement = element.firstChild || element;
  contentElement.id = `${_display_utils.AnnotationPrefix}${id}`;
  div.append(element);
  accessibilityManager === null || accessibilityManager === void 0 ? void 0 : accessibilityManager.moveElementInDOM(div, element, contentElement, false);
}

function _setDimensions(div, _ref2) {
  let {
    width,
    height,
    rotation
  } = _ref2;
  const {
    style
  } = div;
  const flipOrientation = rotation % 180 !== 0,
        widthStr = Math.floor(width) + "px",
        heightStr = Math.floor(height) + "px";
  style.width = flipOrientation ? heightStr : widthStr;
  style.height = flipOrientation ? widthStr : heightStr;
  div.setAttribute("data-main-rotation", rotation);
}

function _setAnnotationCanvasMap(div, annotationCanvasMap) {
  if (!annotationCanvasMap) {
    return;
  }

  for (const [id, canvas] of annotationCanvasMap) {
    const element = div.querySelector(`[data-annotation-id="${id}"]`);

    if (!element) {
      continue;
    }

    const {
      firstChild
    } = element;

    if (!firstChild) {
      element.append(canvas);
    } else if (firstChild.nodeName === "CANVAS") {
      firstChild.replaceWith(canvas);
    } else {
      firstChild.before(canvas);
    }
  }

  annotationCanvasMap.clear();
}

/***/ }),
/* 153 */
/***/ ((__unused_webpack_module, exports) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.ColorConverters = void 0;

function makeColorComp(n) {
  return Math.floor(Math.max(0, Math.min(1, n)) * 255).toString(16).padStart(2, "0");
}

class ColorConverters {
  static CMYK_G(_ref) {
    let [c, y, m, k] = _ref;
    return ["G", 1 - Math.min(1, 0.3 * c + 0.59 * m + 0.11 * y + k)];
  }

  static G_CMYK(_ref2) {
    let [g] = _ref2;
    return ["CMYK", 0, 0, 0, 1 - g];
  }

  static G_RGB(_ref3) {
    let [g] = _ref3;
    return ["RGB", g, g, g];
  }

  static G_HTML(_ref4) {
    let [g] = _ref4;
    const G = makeColorComp(g);
    return `#${G}${G}${G}`;
  }

  static RGB_G(_ref5) {
    let [r, g, b] = _ref5;
    return ["G", 0.3 * r + 0.59 * g + 0.11 * b];
  }

  static RGB_HTML(_ref6) {
    let [r, g, b] = _ref6;
    const R = makeColorComp(r);
    const G = makeColorComp(g);
    const B = makeColorComp(b);
    return `#${R}${G}${B}`;
  }

  static T_HTML() {
    return "#00000000";
  }

  static CMYK_RGB(_ref7) {
    let [c, y, m, k] = _ref7;
    return ["RGB", 1 - Math.min(1, c + k), 1 - Math.min(1, m + k), 1 - Math.min(1, y + k)];
  }

  static CMYK_HTML(components) {
    const rgb = this.CMYK_RGB(components).slice(1);
    return this.RGB_HTML(rgb);
  }

  static RGB_CMYK(_ref8) {
    let [r, g, b] = _ref8;
    const c = 1 - r;
    const m = 1 - g;
    const y = 1 - b;
    const k = Math.min(c, m, y);
    return ["CMYK", c, m, y, k];
  }

}

exports.ColorConverters = ColorConverters;

/***/ }),
/* 154 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.XfaLayer = void 0;

var _xfa_text = __w_pdfjs_require__(145);

class XfaLayer {
  static setupStorage(html, id, element, storage, intent) {
    const storedData = storage.getValue(id, {
      value: null
    });

    switch (element.name) {
      case "textarea":
        if (storedData.value !== null) {
          html.textContent = storedData.value;
        }

        if (intent === "print") {
          break;
        }

        html.addEventListener("input", event => {
          storage.setValue(id, {
            value: event.target.value
          });
        });
        break;

      case "input":
        if (element.attributes.type === "radio" || element.attributes.type === "checkbox") {
          if (storedData.value === element.attributes.xfaOn) {
            html.setAttribute("checked", true);
          } else if (storedData.value === element.attributes.xfaOff) {
            html.removeAttribute("checked");
          }

          if (intent === "print") {
            break;
          }

          html.addEventListener("change", event => {
            storage.setValue(id, {
              value: event.target.checked ? event.target.getAttribute("xfaOn") : event.target.getAttribute("xfaOff")
            });
          });
        } else {
          if (storedData.value !== null) {
            html.setAttribute("value", storedData.value);
          }

          if (intent === "print") {
            break;
          }

          html.addEventListener("input", event => {
            storage.setValue(id, {
              value: event.target.value
            });
          });
        }

        break;

      case "select":
        if (storedData.value !== null) {
          for (const option of element.children) {
            if (option.attributes.value === storedData.value) {
              option.attributes.selected = true;
            }
          }
        }

        html.addEventListener("input", event => {
          const options = event.target.options;
          const value = options.selectedIndex === -1 ? "" : options[options.selectedIndex].value;
          storage.setValue(id, {
            value
          });
        });
        break;
    }
  }

  static setAttributes(_ref) {
    let {
      html,
      element,
      storage = null,
      intent,
      linkService
    } = _ref;
    const {
      attributes
    } = element;
    const isHTMLAnchorElement = html instanceof HTMLAnchorElement;

    if (attributes.type === "radio") {
      attributes.name = `${attributes.name}-${intent}`;
    }

    for (const [key, value] of Object.entries(attributes)) {
      if (value === null || value === undefined) {
        continue;
      }

      switch (key) {
        case "class":
          if (value.length) {
            html.setAttribute(key, value.join(" "));
          }

          break;

        case "dataId":
          break;

        case "id":
          html.setAttribute("data-element-id", value);
          break;

        case "style":
          Object.assign(html.style, value);
          break;

        case "textContent":
          html.textContent = value;
          break;

        default:
          if (!isHTMLAnchorElement || key !== "href" && key !== "newWindow") {
            html.setAttribute(key, value);
          }

      }
    }

    if (isHTMLAnchorElement) {
      linkService.addLinkAttributes(html, attributes.href, attributes.newWindow);
    }

    if (storage && attributes.dataId) {
      this.setupStorage(html, attributes.dataId, element, storage);
    }
  }

  static render(parameters) {
    const storage = parameters.annotationStorage;
    const linkService = parameters.linkService;
    const root = parameters.xfaHtml;
    const intent = parameters.intent || "display";
    const rootHtml = document.createElement(root.name);

    if (root.attributes) {
      this.setAttributes({
        html: rootHtml,
        element: root,
        intent,
        linkService
      });
    }

    const stack = [[root, -1, rootHtml]];
    const rootDiv = parameters.div;
    rootDiv.append(rootHtml);

    if (parameters.viewport) {
      const transform = `matrix(${parameters.viewport.transform.join(",")})`;
      rootDiv.style.transform = transform;
    }

    if (intent !== "richText") {
      rootDiv.setAttribute("class", "xfaLayer xfaFont");
    }

    const textDivs = [];

    while (stack.length > 0) {
      var _child$attributes;

      const [parent, i, html] = stack.at(-1);

      if (i + 1 === parent.children.length) {
        stack.pop();
        continue;
      }

      const child = parent.children[++stack.at(-1)[1]];

      if (child === null) {
        continue;
      }

      const {
        name
      } = child;

      if (name === "#text") {
        const node = document.createTextNode(child.value);
        textDivs.push(node);
        html.append(node);
        continue;
      }

      let childHtml;

      if (child !== null && child !== void 0 && (_child$attributes = child.attributes) !== null && _child$attributes !== void 0 && _child$attributes.xmlns) {
        childHtml = document.createElementNS(child.attributes.xmlns, name);
      } else {
        childHtml = document.createElement(name);
      }

      html.append(childHtml);

      if (child.attributes) {
        this.setAttributes({
          html: childHtml,
          element: child,
          storage,
          intent,
          linkService
        });
      }

      if (child.children && child.children.length > 0) {
        stack.push([child, -1, childHtml]);
      } else if (child.value) {
        const node = document.createTextNode(child.value);

        if (_xfa_text.XfaText.shouldBuildText(name)) {
          textDivs.push(node);
        }

        childHtml.append(node);
      }
    }

    for (const el of rootDiv.querySelectorAll(".xfaNonInteractive input, .xfaNonInteractive textarea")) {
      el.setAttribute("readOnly", true);
    }

    return {
      textDivs
    };
  }

  static update(parameters) {
    const transform = `matrix(${parameters.viewport.transform.join(",")})`;
    parameters.div.style.transform = transform;
    parameters.div.hidden = false;
  }

}

exports.XfaLayer = XfaLayer;

/***/ }),
/* 155 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.TextLayerRenderTask = void 0;
exports.renderTextLayer = renderTextLayer;

var _util = __w_pdfjs_require__(1);

var _display_utils = __w_pdfjs_require__(133);

const MAX_TEXT_DIVS_TO_RENDER = 100000;
const DEFAULT_FONT_SIZE = 30;
const DEFAULT_FONT_ASCENT = 0.8;
const ascentCache = new Map();
const AllWhitespaceRegexp = /^\s+$/g;

function getAscent(fontFamily, ctx) {
  const cachedAscent = ascentCache.get(fontFamily);

  if (cachedAscent) {
    return cachedAscent;
  }

  ctx.save();
  ctx.font = `${DEFAULT_FONT_SIZE}px ${fontFamily}`;
  const metrics = ctx.measureText("");
  let ascent = metrics.fontBoundingBoxAscent;
  let descent = Math.abs(metrics.fontBoundingBoxDescent);

  if (ascent) {
    ctx.restore();
    const ratio = ascent / (ascent + descent);
    ascentCache.set(fontFamily, ratio);
    return ratio;
  }

  ctx.strokeStyle = "red";
  ctx.clearRect(0, 0, DEFAULT_FONT_SIZE, DEFAULT_FONT_SIZE);
  ctx.strokeText("g", 0, 0);
  let pixels = ctx.getImageData(0, 0, DEFAULT_FONT_SIZE, DEFAULT_FONT_SIZE).data;
  descent = 0;

  for (let i = pixels.length - 1 - 3; i >= 0; i -= 4) {
    if (pixels[i] > 0) {
      descent = Math.ceil(i / 4 / DEFAULT_FONT_SIZE);
      break;
    }
  }

  ctx.clearRect(0, 0, DEFAULT_FONT_SIZE, DEFAULT_FONT_SIZE);
  ctx.strokeText("A", 0, DEFAULT_FONT_SIZE);
  pixels = ctx.getImageData(0, 0, DEFAULT_FONT_SIZE, DEFAULT_FONT_SIZE).data;
  ascent = 0;

  for (let i = 0, ii = pixels.length; i < ii; i += 4) {
    if (pixels[i] > 0) {
      ascent = DEFAULT_FONT_SIZE - Math.floor(i / 4 / DEFAULT_FONT_SIZE);
      break;
    }
  }

  ctx.restore();

  if (ascent) {
    const ratio = ascent / (ascent + descent);
    ascentCache.set(fontFamily, ratio);
    return ratio;
  }

  ascentCache.set(fontFamily, DEFAULT_FONT_ASCENT);
  return DEFAULT_FONT_ASCENT;
}

function appendText(task, geom, styles, ctx) {
  const textDiv = document.createElement("span");
  const textDivProperties = task._enhanceTextSelection ? {
    angle: 0,
    canvasWidth: 0,
    hasText: geom.str !== "",
    hasEOL: geom.hasEOL,
    originalTransform: null,
    paddingBottom: 0,
    paddingLeft: 0,
    paddingRight: 0,
    paddingTop: 0,
    scale: 1,
    fontSize: 0
  } : {
    angle: 0,
    canvasWidth: 0,
    hasText: geom.str !== "",
    hasEOL: geom.hasEOL,
    fontSize: 0
  };

  task._textDivs.push(textDiv);

  const tx = _util.Util.transform(task._viewport.transform, geom.transform);

  let angle = Math.atan2(tx[1], tx[0]);
  const style = styles[geom.fontName];

  if (style.vertical) {
    angle += Math.PI / 2;
  }

  const fontHeight = Math.hypot(tx[2], tx[3]);
  const fontAscent = fontHeight * getAscent(style.fontFamily, ctx);
  let left, top;

  if (angle === 0) {
    left = tx[4];
    top = tx[5] - fontAscent;
  } else {
    left = tx[4] + fontAscent * Math.sin(angle);
    top = tx[5] - fontAscent * Math.cos(angle);
  }

  textDiv.style.left = `${left}px`;
  textDiv.style.top = `${top}px`;
  textDiv.style.fontSize = `${fontHeight}px`;
  textDiv.style.fontFamily = style.fontFamily;
  textDivProperties.fontSize = fontHeight;
  textDiv.setAttribute("role", "presentation");
  textDiv.textContent = geom.str;
  textDiv.dir = geom.dir;

  if (task._fontInspectorEnabled) {
    textDiv.dataset.fontName = geom.fontName;
  }

  if (angle !== 0) {
    textDivProperties.angle = angle * (180 / Math.PI);
  }

  let shouldScaleText = false;

  if (geom.str.length > 1 || task._enhanceTextSelection && AllWhitespaceRegexp.test(geom.str)) {
    shouldScaleText = true;
  } else if (geom.str !== " " && geom.transform[0] !== geom.transform[3]) {
    const absScaleX = Math.abs(geom.transform[0]),
          absScaleY = Math.abs(geom.transform[3]);

    if (absScaleX !== absScaleY && Math.max(absScaleX, absScaleY) / Math.min(absScaleX, absScaleY) > 1.5) {
      shouldScaleText = true;
    }
  }

  if (shouldScaleText) {
    if (style.vertical) {
      textDivProperties.canvasWidth = geom.height * task._viewport.scale;
    } else {
      textDivProperties.canvasWidth = geom.width * task._viewport.scale;
    }
  }

  task._textDivProperties.set(textDiv, textDivProperties);

  if (task._textContentStream) {
    task._layoutText(textDiv);
  }

  if (task._enhanceTextSelection && textDivProperties.hasText) {
    let angleCos = 1,
        angleSin = 0;

    if (angle !== 0) {
      angleCos = Math.cos(angle);
      angleSin = Math.sin(angle);
    }

    const divWidth = (style.vertical ? geom.height : geom.width) * task._viewport.scale;
    const divHeight = fontHeight;
    let m, b;

    if (angle !== 0) {
      m = [angleCos, angleSin, -angleSin, angleCos, left, top];
      b = _util.Util.getAxialAlignedBoundingBox([0, 0, divWidth, divHeight], m);
    } else {
      b = [left, top, left + divWidth, top + divHeight];
    }

    task._bounds.push({
      left: b[0],
      top: b[1],
      right: b[2],
      bottom: b[3],
      div: textDiv,
      size: [divWidth, divHeight],
      m
    });
  }
}

function render(task) {
  if (task._canceled) {
    return;
  }

  const textDivs = task._textDivs;
  const capability = task._capability;
  const textDivsLength = textDivs.length;

  if (textDivsLength > MAX_TEXT_DIVS_TO_RENDER) {
    task._renderingDone = true;
    capability.resolve();
    return;
  }

  if (!task._textContentStream) {
    for (let i = 0; i < textDivsLength; i++) {
      task._layoutText(textDivs[i]);
    }
  }

  task._renderingDone = true;
  capability.resolve();
}

function findPositiveMin(ts, offset, count) {
  let result = 0;

  for (let i = 0; i < count; i++) {
    const t = ts[offset++];

    if (t > 0) {
      result = result ? Math.min(t, result) : t;
    }
  }

  return result;
}

function expand(task) {
  const bounds = task._bounds;
  const viewport = task._viewport;
  const expanded = expandBounds(viewport.width, viewport.height, bounds);

  for (let i = 0; i < expanded.length; i++) {
    const div = bounds[i].div;

    const divProperties = task._textDivProperties.get(div);

    if (divProperties.angle === 0) {
      divProperties.paddingLeft = bounds[i].left - expanded[i].left;
      divProperties.paddingTop = bounds[i].top - expanded[i].top;
      divProperties.paddingRight = expanded[i].right - bounds[i].right;
      divProperties.paddingBottom = expanded[i].bottom - bounds[i].bottom;

      task._textDivProperties.set(div, divProperties);

      continue;
    }

    const e = expanded[i],
          b = bounds[i];
    const m = b.m,
          c = m[0],
          s = m[1];
    const points = [[0, 0], [0, b.size[1]], [b.size[0], 0], b.size];
    const ts = new Float64Array(64);

    for (let j = 0, jj = points.length; j < jj; j++) {
      const t = _util.Util.applyTransform(points[j], m);

      ts[j + 0] = c && (e.left - t[0]) / c;
      ts[j + 4] = s && (e.top - t[1]) / s;
      ts[j + 8] = c && (e.right - t[0]) / c;
      ts[j + 12] = s && (e.bottom - t[1]) / s;
      ts[j + 16] = s && (e.left - t[0]) / -s;
      ts[j + 20] = c && (e.top - t[1]) / c;
      ts[j + 24] = s && (e.right - t[0]) / -s;
      ts[j + 28] = c && (e.bottom - t[1]) / c;
      ts[j + 32] = c && (e.left - t[0]) / -c;
      ts[j + 36] = s && (e.top - t[1]) / -s;
      ts[j + 40] = c && (e.right - t[0]) / -c;
      ts[j + 44] = s && (e.bottom - t[1]) / -s;
      ts[j + 48] = s && (e.left - t[0]) / s;
      ts[j + 52] = c && (e.top - t[1]) / -c;
      ts[j + 56] = s && (e.right - t[0]) / s;
      ts[j + 60] = c && (e.bottom - t[1]) / -c;
    }

    const boxScale = 1 + Math.min(Math.abs(c), Math.abs(s));
    divProperties.paddingLeft = findPositiveMin(ts, 32, 16) / boxScale;
    divProperties.paddingTop = findPositiveMin(ts, 48, 16) / boxScale;
    divProperties.paddingRight = findPositiveMin(ts, 0, 16) / boxScale;
    divProperties.paddingBottom = findPositiveMin(ts, 16, 16) / boxScale;

    task._textDivProperties.set(div, divProperties);
  }
}

function expandBounds(width, height, boxes) {
  const bounds = boxes.map(function (box, i) {
    return {
      x1: box.left,
      y1: box.top,
      x2: box.right,
      y2: box.bottom,
      index: i,
      x1New: undefined,
      x2New: undefined
    };
  });
  expandBoundsLTR(width, bounds);
  const expanded = new Array(boxes.length);

  for (const b of bounds) {
    const i = b.index;
    expanded[i] = {
      left: b.x1New,
      top: 0,
      right: b.x2New,
      bottom: 0
    };
  }

  boxes.map(function (box, i) {
    const e = expanded[i],
          b = bounds[i];
    b.x1 = box.top;
    b.y1 = width - e.right;
    b.x2 = box.bottom;
    b.y2 = width - e.left;
    b.index = i;
    b.x1New = undefined;
    b.x2New = undefined;
  });
  expandBoundsLTR(height, bounds);

  for (const b of bounds) {
    const i = b.index;
    expanded[i].top = b.x1New;
    expanded[i].bottom = b.x2New;
  }

  return expanded;
}

function expandBoundsLTR(width, bounds) {
  bounds.sort(function (a, b) {
    return a.x1 - b.x1 || a.index - b.index;
  });
  const fakeBoundary = {
    x1: -Infinity,
    y1: -Infinity,
    x2: 0,
    y2: Infinity,
    index: -1,
    x1New: 0,
    x2New: 0
  };
  const horizon = [{
    start: -Infinity,
    end: Infinity,
    boundary: fakeBoundary
  }];

  for (const boundary of bounds) {
    let i = 0;

    while (i < horizon.length && horizon[i].end <= boundary.y1) {
      i++;
    }

    let j = horizon.length - 1;

    while (j >= 0 && horizon[j].start >= boundary.y2) {
      j--;
    }

    let horizonPart, affectedBoundary;
    let q,
        k,
        maxXNew = -Infinity;

    for (q = i; q <= j; q++) {
      horizonPart = horizon[q];
      affectedBoundary = horizonPart.boundary;
      let xNew;

      if (affectedBoundary.x2 > boundary.x1) {
        xNew = affectedBoundary.index > boundary.index ? affectedBoundary.x1New : boundary.x1;
      } else if (affectedBoundary.x2New === undefined) {
        xNew = (affectedBoundary.x2 + boundary.x1) / 2;
      } else {
        xNew = affectedBoundary.x2New;
      }

      if (xNew > maxXNew) {
        maxXNew = xNew;
      }
    }

    boundary.x1New = maxXNew;

    for (q = i; q <= j; q++) {
      horizonPart = horizon[q];
      affectedBoundary = horizonPart.boundary;

      if (affectedBoundary.x2New === undefined) {
        if (affectedBoundary.x2 > boundary.x1) {
          if (affectedBoundary.index > boundary.index) {
            affectedBoundary.x2New = affectedBoundary.x2;
          }
        } else {
          affectedBoundary.x2New = maxXNew;
        }
      } else if (affectedBoundary.x2New > maxXNew) {
        affectedBoundary.x2New = Math.max(maxXNew, affectedBoundary.x2);
      }
    }

    const changedHorizon = [];
    let lastBoundary = null;

    for (q = i; q <= j; q++) {
      horizonPart = horizon[q];
      affectedBoundary = horizonPart.boundary;
      const useBoundary = affectedBoundary.x2 > boundary.x2 ? affectedBoundary : boundary;

      if (lastBoundary === useBoundary) {
        changedHorizon.at(-1).end = horizonPart.end;
      } else {
        changedHorizon.push({
          start: horizonPart.start,
          end: horizonPart.end,
          boundary: useBoundary
        });
        lastBoundary = useBoundary;
      }
    }

    if (horizon[i].start < boundary.y1) {
      changedHorizon[0].start = boundary.y1;
      changedHorizon.unshift({
        start: horizon[i].start,
        end: boundary.y1,
        boundary: horizon[i].boundary
      });
    }

    if (boundary.y2 < horizon[j].end) {
      changedHorizon.at(-1).end = boundary.y2;
      changedHorizon.push({
        start: boundary.y2,
        end: horizon[j].end,
        boundary: horizon[j].boundary
      });
    }

    for (q = i; q <= j; q++) {
      horizonPart = horizon[q];
      affectedBoundary = horizonPart.boundary;

      if (affectedBoundary.x2New !== undefined) {
        continue;
      }

      let used = false;

      for (k = i - 1; !used && k >= 0 && horizon[k].start >= affectedBoundary.y1; k--) {
        used = horizon[k].boundary === affectedBoundary;
      }

      for (k = j + 1; !used && k < horizon.length && horizon[k].end <= affectedBoundary.y2; k++) {
        used = horizon[k].boundary === affectedBoundary;
      }

      for (k = 0; !used && k < changedHorizon.length; k++) {
        used = changedHorizon[k].boundary === affectedBoundary;
      }

      if (!used) {
        affectedBoundary.x2New = maxXNew;
      }
    }

    Array.prototype.splice.apply(horizon, [i, j - i + 1, ...changedHorizon]);
  }

  for (const horizonPart of horizon) {
    const affectedBoundary = horizonPart.boundary;

    if (affectedBoundary.x2New === undefined) {
      affectedBoundary.x2New = Math.max(width, affectedBoundary.x2);
    }
  }
}

class TextLayerRenderTask {
  constructor(_ref) {
    var _globalThis$FontInspe;

    let {
      textContent,
      textContentStream,
      container,
      viewport,
      textDivs,
      textContentItemsStr,
      enhanceTextSelection
    } = _ref;

    if (enhanceTextSelection) {
      (0, _display_utils.deprecated)("The `enhanceTextSelection` functionality will be removed in the future.");
    }

    this._textContent = textContent;
    this._textContentStream = textContentStream;
    this._container = container;
    this._document = container.ownerDocument;
    this._viewport = viewport;
    this._textDivs = textDivs || [];
    this._textContentItemsStr = textContentItemsStr || [];
    this._enhanceTextSelection = !!enhanceTextSelection;
    this._fontInspectorEnabled = !!((_globalThis$FontInspe = globalThis.FontInspector) !== null && _globalThis$FontInspe !== void 0 && _globalThis$FontInspe.enabled);
    this._reader = null;
    this._layoutTextLastFontSize = null;
    this._layoutTextLastFontFamily = null;
    this._layoutTextCtx = null;
    this._textDivProperties = new WeakMap();
    this._renderingDone = false;
    this._canceled = false;
    this._capability = (0, _util.createPromiseCapability)();
    this._renderTimer = null;
    this._bounds = [];
    this._devicePixelRatio = globalThis.devicePixelRatio || 1;

    this._capability.promise.finally(() => {
      if (!this._enhanceTextSelection) {
        this._textDivProperties = null;
      }

      if (this._layoutTextCtx) {
        this._layoutTextCtx.canvas.width = 0;
        this._layoutTextCtx.canvas.height = 0;
        this._layoutTextCtx = null;
      }
    }).catch(() => {});
  }

  get promise() {
    return this._capability.promise;
  }

  cancel() {
    this._canceled = true;

    if (this._reader) {
      this._reader.cancel(new _util.AbortException("TextLayer task cancelled.")).catch(() => {});

      this._reader = null;
    }

    if (this._renderTimer !== null) {
      clearTimeout(this._renderTimer);
      this._renderTimer = null;
    }

    this._capability.reject(new Error("TextLayer task cancelled."));
  }

  _processItems(items, styleCache) {
    for (let i = 0, len = items.length; i < len; i++) {
      if (items[i].str === undefined) {
        if (items[i].type === "beginMarkedContentProps" || items[i].type === "beginMarkedContent") {
          const parent = this._container;
          this._container = document.createElement("span");

          this._container.classList.add("markedContent");

          if (items[i].id !== null) {
            this._container.setAttribute("id", `${items[i].id}`);
          }

          parent.append(this._container);
        } else if (items[i].type === "endMarkedContent") {
          this._container = this._container.parentNode;
        }

        continue;
      }

      this._textContentItemsStr.push(items[i].str);

      appendText(this, items[i], styleCache, this._layoutTextCtx);
    }
  }

  _layoutText(textDiv) {
    const textDivProperties = this._textDivProperties.get(textDiv);

    let transform = "";

    if (textDivProperties.canvasWidth !== 0 && textDivProperties.hasText) {
      const {
        fontFamily
      } = textDiv.style;
      const {
        fontSize
      } = textDivProperties;

      if (fontSize !== this._layoutTextLastFontSize || fontFamily !== this._layoutTextLastFontFamily) {
        this._layoutTextCtx.font = `${fontSize * this._devicePixelRatio}px ${fontFamily}`;
        this._layoutTextLastFontSize = fontSize;
        this._layoutTextLastFontFamily = fontFamily;
      }

      const {
        width
      } = this._layoutTextCtx.measureText(textDiv.textContent);

      if (width > 0) {
        const scale = this._devicePixelRatio * textDivProperties.canvasWidth / width;

        if (this._enhanceTextSelection) {
          textDivProperties.scale = scale;
        }

        transform = `scaleX(${scale})`;
      }
    }

    if (textDivProperties.angle !== 0) {
      transform = `rotate(${textDivProperties.angle}deg) ${transform}`;
    }

    if (transform.length > 0) {
      if (this._enhanceTextSelection) {
        textDivProperties.originalTransform = transform;
      }

      textDiv.style.transform = transform;
    }

    if (textDivProperties.hasText) {
      this._container.append(textDiv);
    }

    if (textDivProperties.hasEOL) {
      const br = document.createElement("br");
      br.setAttribute("role", "presentation");

      this._container.append(br);
    }
  }

  _render() {
    let timeout = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
    const capability = (0, _util.createPromiseCapability)();
    let styleCache = Object.create(null);

    const canvas = this._document.createElement("canvas");

    canvas.height = canvas.width = DEFAULT_FONT_SIZE;
    this._layoutTextCtx = canvas.getContext("2d", {
      alpha: false
    });

    if (this._textContent) {
      const textItems = this._textContent.items;
      const textStyles = this._textContent.styles;

      this._processItems(textItems, textStyles);

      capability.resolve();
    } else if (this._textContentStream) {
      const pump = () => {
        this._reader.read().then(_ref2 => {
          let {
            value,
            done
          } = _ref2;

          if (done) {
            capability.resolve();
            return;
          }

          Object.assign(styleCache, value.styles);

          this._processItems(value.items, styleCache);

          pump();
        }, capability.reject);
      };

      this._reader = this._textContentStream.getReader();
      pump();
    } else {
      throw new Error('Neither "textContent" nor "textContentStream" parameters specified.');
    }

    capability.promise.then(() => {
      styleCache = null;

      if (!timeout) {
        render(this);
      } else {
        this._renderTimer = setTimeout(() => {
          render(this);
          this._renderTimer = null;
        }, timeout);
      }
    }, this._capability.reject);
  }

  expandTextDivs() {
    let expandDivs = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

    if (!this._enhanceTextSelection || !this._renderingDone) {
      return;
    }

    if (this._bounds !== null) {
      expand(this);
      this._bounds = null;
    }

    const transformBuf = [],
          paddingBuf = [];

    for (let i = 0, ii = this._textDivs.length; i < ii; i++) {
      const div = this._textDivs[i];

      const divProps = this._textDivProperties.get(div);

      if (!divProps.hasText) {
        continue;
      }

      if (expandDivs) {
        transformBuf.length = 0;
        paddingBuf.length = 0;

        if (divProps.originalTransform) {
          transformBuf.push(divProps.originalTransform);
        }

        if (divProps.paddingTop > 0) {
          paddingBuf.push(`${divProps.paddingTop}px`);
          transformBuf.push(`translateY(${-divProps.paddingTop}px)`);
        } else {
          paddingBuf.push(0);
        }

        if (divProps.paddingRight > 0) {
          paddingBuf.push(`${divProps.paddingRight / divProps.scale}px`);
        } else {
          paddingBuf.push(0);
        }

        if (divProps.paddingBottom > 0) {
          paddingBuf.push(`${divProps.paddingBottom}px`);
        } else {
          paddingBuf.push(0);
        }

        if (divProps.paddingLeft > 0) {
          paddingBuf.push(`${divProps.paddingLeft / divProps.scale}px`);
          transformBuf.push(`translateX(${-divProps.paddingLeft / divProps.scale}px)`);
        } else {
          paddingBuf.push(0);
        }

        div.style.padding = paddingBuf.join(" ");

        if (transformBuf.length) {
          div.style.transform = transformBuf.join(" ");
        }
      } else {
        div.style.padding = null;
        div.style.transform = divProps.originalTransform;
      }
    }
  }

}

exports.TextLayerRenderTask = TextLayerRenderTask;

function renderTextLayer(renderParameters) {
  const task = new TextLayerRenderTask({
    textContent: renderParameters.textContent,
    textContentStream: renderParameters.textContentStream,
    container: renderParameters.container,
    viewport: renderParameters.viewport,
    textDivs: renderParameters.textDivs,
    textContentItemsStr: renderParameters.textContentItemsStr,
    enhanceTextSelection: renderParameters.enhanceTextSelection
  });

  task._render(renderParameters.timeout);

  return task;
}

/***/ }),
/* 156 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.SVGGraphics = void 0;

var _display_utils = __w_pdfjs_require__(133);

var _util = __w_pdfjs_require__(1);

var _is_node = __w_pdfjs_require__(3);

let SVGGraphics = class {
  constructor() {
    (0, _util.unreachable)("Not implemented: SVGGraphics");
  }

};
exports.SVGGraphics = SVGGraphics;
{
  const SVG_DEFAULTS = {
    fontStyle: "normal",
    fontWeight: "normal",
    fillColor: "#000000"
  };
  const XML_NS = "http://www.w3.org/XML/1998/namespace";
  const XLINK_NS = "http://www.w3.org/1999/xlink";
  const LINE_CAP_STYLES = ["butt", "round", "square"];
  const LINE_JOIN_STYLES = ["miter", "round", "bevel"];

  const createObjectURL = function (data) {
    let contentType = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    let forceDataSchema = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;

    if (URL.createObjectURL && typeof Blob !== "undefined" && !forceDataSchema) {
      return URL.createObjectURL(new Blob([data], {
        type: contentType
      }));
    }

    const digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
    let buffer = `data:${contentType};base64,`;

    for (let i = 0, ii = data.length; i < ii; i += 3) {
      const b1 = data[i] & 0xff;
      const b2 = data[i + 1] & 0xff;
      const b3 = data[i + 2] & 0xff;
      const d1 = b1 >> 2,
            d2 = (b1 & 3) << 4 | b2 >> 4;
      const d3 = i + 1 < ii ? (b2 & 0xf) << 2 | b3 >> 6 : 64;
      const d4 = i + 2 < ii ? b3 & 0x3f : 64;
      buffer += digits[d1] + digits[d2] + digits[d3] + digits[d4];
    }

    return buffer;
  };

  const convertImgDataToPng = function () {
    const PNG_HEADER = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    const CHUNK_WRAPPER_SIZE = 12;
    const crcTable = new Int32Array(256);

    for (let i = 0; i < 256; i++) {
      let c = i;

      for (let h = 0; h < 8; h++) {
        if (c & 1) {
          c = 0xedb88320 ^ c >> 1 & 0x7fffffff;
        } else {
          c = c >> 1 & 0x7fffffff;
        }
      }

      crcTable[i] = c;
    }

    function crc32(data, start, end) {
      let crc = -1;

      for (let i = start; i < end; i++) {
        const a = (crc ^ data[i]) & 0xff;
        const b = crcTable[a];
        crc = crc >>> 8 ^ b;
      }

      return crc ^ -1;
    }

    function writePngChunk(type, body, data, offset) {
      let p = offset;
      const len = body.length;
      data[p] = len >> 24 & 0xff;
      data[p + 1] = len >> 16 & 0xff;
      data[p + 2] = len >> 8 & 0xff;
      data[p + 3] = len & 0xff;
      p += 4;
      data[p] = type.charCodeAt(0) & 0xff;
      data[p + 1] = type.charCodeAt(1) & 0xff;
      data[p + 2] = type.charCodeAt(2) & 0xff;
      data[p + 3] = type.charCodeAt(3) & 0xff;
      p += 4;
      data.set(body, p);
      p += body.length;
      const crc = crc32(data, offset + 4, p);
      data[p] = crc >> 24 & 0xff;
      data[p + 1] = crc >> 16 & 0xff;
      data[p + 2] = crc >> 8 & 0xff;
      data[p + 3] = crc & 0xff;
    }

    function adler32(data, start, end) {
      let a = 1;
      let b = 0;

      for (let i = start; i < end; ++i) {
        a = (a + (data[i] & 0xff)) % 65521;
        b = (b + a) % 65521;
      }

      return b << 16 | a;
    }

    function deflateSync(literals) {
      if (!_is_node.isNodeJS) {
        return deflateSyncUncompressed(literals);
      }

      try {
        let input;

        if (parseInt(process.versions.node) >= 8) {
          input = literals;
        } else {
          input = Buffer.from(literals);
        }

        const output = require("zlib").deflateSync(input, {
          level: 9
        });

        return output instanceof Uint8Array ? output : new Uint8Array(output);
      } catch (e) {
        (0, _util.warn)("Not compressing PNG because zlib.deflateSync is unavailable: " + e);
      }

      return deflateSyncUncompressed(literals);
    }

    function deflateSyncUncompressed(literals) {
      let len = literals.length;
      const maxBlockLength = 0xffff;
      const deflateBlocks = Math.ceil(len / maxBlockLength);
      const idat = new Uint8Array(2 + len + deflateBlocks * 5 + 4);
      let pi = 0;
      idat[pi++] = 0x78;
      idat[pi++] = 0x9c;
      let pos = 0;

      while (len > maxBlockLength) {
        idat[pi++] = 0x00;
        idat[pi++] = 0xff;
        idat[pi++] = 0xff;
        idat[pi++] = 0x00;
        idat[pi++] = 0x00;
        idat.set(literals.subarray(pos, pos + maxBlockLength), pi);
        pi += maxBlockLength;
        pos += maxBlockLength;
        len -= maxBlockLength;
      }

      idat[pi++] = 0x01;
      idat[pi++] = len & 0xff;
      idat[pi++] = len >> 8 & 0xff;
      idat[pi++] = ~len & 0xffff & 0xff;
      idat[pi++] = (~len & 0xffff) >> 8 & 0xff;
      idat.set(literals.subarray(pos), pi);
      pi += literals.length - pos;
      const adler = adler32(literals, 0, literals.length);
      idat[pi++] = adler >> 24 & 0xff;
      idat[pi++] = adler >> 16 & 0xff;
      idat[pi++] = adler >> 8 & 0xff;
      idat[pi++] = adler & 0xff;
      return idat;
    }

    function encode(imgData, kind, forceDataSchema, isMask) {
      const width = imgData.width;
      const height = imgData.height;
      let bitDepth, colorType, lineSize;
      const bytes = imgData.data;

      switch (kind) {
        case _util.ImageKind.GRAYSCALE_1BPP:
          colorType = 0;
          bitDepth = 1;
          lineSize = width + 7 >> 3;
          break;

        case _util.ImageKind.RGB_24BPP:
          colorType = 2;
          bitDepth = 8;
          lineSize = width * 3;
          break;

        case _util.ImageKind.RGBA_32BPP:
          colorType = 6;
          bitDepth = 8;
          lineSize = width * 4;
          break;

        default:
          throw new Error("invalid format");
      }

      const literals = new Uint8Array((1 + lineSize) * height);
      let offsetLiterals = 0,
          offsetBytes = 0;

      for (let y = 0; y < height; ++y) {
        literals[offsetLiterals++] = 0;
        literals.set(bytes.subarray(offsetBytes, offsetBytes + lineSize), offsetLiterals);
        offsetBytes += lineSize;
        offsetLiterals += lineSize;
      }

      if (kind === _util.ImageKind.GRAYSCALE_1BPP && isMask) {
        offsetLiterals = 0;

        for (let y = 0; y < height; y++) {
          offsetLiterals++;

          for (let i = 0; i < lineSize; i++) {
            literals[offsetLiterals++] ^= 0xff;
          }
        }
      }

      const ihdr = new Uint8Array([width >> 24 & 0xff, width >> 16 & 0xff, width >> 8 & 0xff, width & 0xff, height >> 24 & 0xff, height >> 16 & 0xff, height >> 8 & 0xff, height & 0xff, bitDepth, colorType, 0x00, 0x00, 0x00]);
      const idat = deflateSync(literals);
      const pngLength = PNG_HEADER.length + CHUNK_WRAPPER_SIZE * 3 + ihdr.length + idat.length;
      const data = new Uint8Array(pngLength);
      let offset = 0;
      data.set(PNG_HEADER, offset);
      offset += PNG_HEADER.length;
      writePngChunk("IHDR", ihdr, data, offset);
      offset += CHUNK_WRAPPER_SIZE + ihdr.length;
      writePngChunk("IDATA", idat, data, offset);
      offset += CHUNK_WRAPPER_SIZE + idat.length;
      writePngChunk("IEND", new Uint8Array(0), data, offset);
      return createObjectURL(data, "image/png", forceDataSchema);
    }

    return function convertImgDataToPng(imgData, forceDataSchema, isMask) {
      const kind = imgData.kind === undefined ? _util.ImageKind.GRAYSCALE_1BPP : imgData.kind;
      return encode(imgData, kind, forceDataSchema, isMask);
    };
  }();

  class SVGExtraState {
    constructor() {
      this.fontSizeScale = 1;
      this.fontWeight = SVG_DEFAULTS.fontWeight;
      this.fontSize = 0;
      this.textMatrix = _util.IDENTITY_MATRIX;
      this.fontMatrix = _util.FONT_IDENTITY_MATRIX;
      this.leading = 0;
      this.textRenderingMode = _util.TextRenderingMode.FILL;
      this.textMatrixScale = 1;
      this.x = 0;
      this.y = 0;
      this.lineX = 0;
      this.lineY = 0;
      this.charSpacing = 0;
      this.wordSpacing = 0;
      this.textHScale = 1;
      this.textRise = 0;
      this.fillColor = SVG_DEFAULTS.fillColor;
      this.strokeColor = "#000000";
      this.fillAlpha = 1;
      this.strokeAlpha = 1;
      this.lineWidth = 1;
      this.lineJoin = "";
      this.lineCap = "";
      this.miterLimit = 0;
      this.dashArray = [];
      this.dashPhase = 0;
      this.dependencies = [];
      this.activeClipUrl = null;
      this.clipGroup = null;
      this.maskId = "";
    }

    clone() {
      return Object.create(this);
    }

    setCurrentPoint(x, y) {
      this.x = x;
      this.y = y;
    }

  }

  function opListToTree(opList) {
    let opTree = [];
    const tmp = [];

    for (const opListElement of opList) {
      if (opListElement.fn === "save") {
        opTree.push({
          fnId: 92,
          fn: "group",
          items: []
        });
        tmp.push(opTree);
        opTree = opTree.at(-1).items;
        continue;
      }

      if (opListElement.fn === "restore") {
        opTree = tmp.pop();
      } else {
        opTree.push(opListElement);
      }
    }

    return opTree;
  }

  function pf(value) {
    if (Number.isInteger(value)) {
      return value.toString();
    }

    const s = value.toFixed(10);
    let i = s.length - 1;

    if (s[i] !== "0") {
      return s;
    }

    do {
      i--;
    } while (s[i] === "0");

    return s.substring(0, s[i] === "." ? i : i + 1);
  }

  function pm(m) {
    if (m[4] === 0 && m[5] === 0) {
      if (m[1] === 0 && m[2] === 0) {
        if (m[0] === 1 && m[3] === 1) {
          return "";
        }

        return `scale(${pf(m[0])} ${pf(m[3])})`;
      }

      if (m[0] === m[3] && m[1] === -m[2]) {
        const a = Math.acos(m[0]) * 180 / Math.PI;
        return `rotate(${pf(a)})`;
      }
    } else {
      if (m[0] === 1 && m[1] === 0 && m[2] === 0 && m[3] === 1) {
        return `translate(${pf(m[4])} ${pf(m[5])})`;
      }
    }

    return `matrix(${pf(m[0])} ${pf(m[1])} ${pf(m[2])} ${pf(m[3])} ${pf(m[4])} ` + `${pf(m[5])})`;
  }

  let clipCount = 0;
  let maskCount = 0;
  let shadingCount = 0;
  exports.SVGGraphics = SVGGraphics = class {
    constructor(commonObjs, objs) {
      let forceDataSchema = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
      (0, _display_utils.deprecated)("The SVG back-end is no longer maintained and *may* be removed in the future.");
      this.svgFactory = new _display_utils.DOMSVGFactory();
      this.current = new SVGExtraState();
      this.transformMatrix = _util.IDENTITY_MATRIX;
      this.transformStack = [];
      this.extraStack = [];
      this.commonObjs = commonObjs;
      this.objs = objs;
      this.pendingClip = null;
      this.pendingEOFill = false;
      this.embedFonts = false;
      this.embeddedFonts = Object.create(null);
      this.cssStyle = null;
      this.forceDataSchema = !!forceDataSchema;
      this._operatorIdMapping = [];

      for (const op in _util.OPS) {
        this._operatorIdMapping[_util.OPS[op]] = op;
      }
    }

    save() {
      this.transformStack.push(this.transformMatrix);
      const old = this.current;
      this.extraStack.push(old);
      this.current = old.clone();
    }

    restore() {
      this.transformMatrix = this.transformStack.pop();
      this.current = this.extraStack.pop();
      this.pendingClip = null;
      this.tgrp = null;
    }

    group(items) {
      this.save();
      this.executeOpTree(items);
      this.restore();
    }

    loadDependencies(operatorList) {
      const fnArray = operatorList.fnArray;
      const argsArray = operatorList.argsArray;

      for (let i = 0, ii = fnArray.length; i < ii; i++) {
        if (fnArray[i] !== _util.OPS.dependency) {
          continue;
        }

        for (const obj of argsArray[i]) {
          const objsPool = obj.startsWith("g_") ? this.commonObjs : this.objs;
          const promise = new Promise(resolve => {
            objsPool.get(obj, resolve);
          });
          this.current.dependencies.push(promise);
        }
      }

      return Promise.all(this.current.dependencies);
    }

    transform(a, b, c, d, e, f) {
      const transformMatrix = [a, b, c, d, e, f];
      this.transformMatrix = _util.Util.transform(this.transformMatrix, transformMatrix);
      this.tgrp = null;
    }

    getSVG(operatorList, viewport) {
      this.viewport = viewport;

      const svgElement = this._initialize(viewport);

      return this.loadDependencies(operatorList).then(() => {
        this.transformMatrix = _util.IDENTITY_MATRIX;
        this.executeOpTree(this.convertOpList(operatorList));
        return svgElement;
      });
    }

    convertOpList(operatorList) {
      const operatorIdMapping = this._operatorIdMapping;
      const argsArray = operatorList.argsArray;
      const fnArray = operatorList.fnArray;
      const opList = [];

      for (let i = 0, ii = fnArray.length; i < ii; i++) {
        const fnId = fnArray[i];
        opList.push({
          fnId,
          fn: operatorIdMapping[fnId],
          args: argsArray[i]
        });
      }

      return opListToTree(opList);
    }

    executeOpTree(opTree) {
      for (const opTreeElement of opTree) {
        const fn = opTreeElement.fn;
        const fnId = opTreeElement.fnId;
        const args = opTreeElement.args;

        switch (fnId | 0) {
          case _util.OPS.beginText:
            this.beginText();
            break;

          case _util.OPS.dependency:
            break;

          case _util.OPS.setLeading:
            this.setLeading(args);
            break;

          case _util.OPS.setLeadingMoveText:
            this.setLeadingMoveText(args[0], args[1]);
            break;

          case _util.OPS.setFont:
            this.setFont(args);
            break;

          case _util.OPS.showText:
            this.showText(args[0]);
            break;

          case _util.OPS.showSpacedText:
            this.showText(args[0]);
            break;

          case _util.OPS.endText:
            this.endText();
            break;

          case _util.OPS.moveText:
            this.moveText(args[0], args[1]);
            break;

          case _util.OPS.setCharSpacing:
            this.setCharSpacing(args[0]);
            break;

          case _util.OPS.setWordSpacing:
            this.setWordSpacing(args[0]);
            break;

          case _util.OPS.setHScale:
            this.setHScale(args[0]);
            break;

          case _util.OPS.setTextMatrix:
            this.setTextMatrix(args[0], args[1], args[2], args[3], args[4], args[5]);
            break;

          case _util.OPS.setTextRise:
            this.setTextRise(args[0]);
            break;

          case _util.OPS.setTextRenderingMode:
            this.setTextRenderingMode(args[0]);
            break;

          case _util.OPS.setLineWidth:
            this.setLineWidth(args[0]);
            break;

          case _util.OPS.setLineJoin:
            this.setLineJoin(args[0]);
            break;

          case _util.OPS.setLineCap:
            this.setLineCap(args[0]);
            break;

          case _util.OPS.setMiterLimit:
            this.setMiterLimit(args[0]);
            break;

          case _util.OPS.setFillRGBColor:
            this.setFillRGBColor(args[0], args[1], args[2]);
            break;

          case _util.OPS.setStrokeRGBColor:
            this.setStrokeRGBColor(args[0], args[1], args[2]);
            break;

          case _util.OPS.setStrokeColorN:
            this.setStrokeColorN(args);
            break;

          case _util.OPS.setFillColorN:
            this.setFillColorN(args);
            break;

          case _util.OPS.shadingFill:
            this.shadingFill(args[0]);
            break;

          case _util.OPS.setDash:
            this.setDash(args[0], args[1]);
            break;

          case _util.OPS.setRenderingIntent:
            this.setRenderingIntent(args[0]);
            break;

          case _util.OPS.setFlatness:
            this.setFlatness(args[0]);
            break;

          case _util.OPS.setGState:
            this.setGState(args[0]);
            break;

          case _util.OPS.fill:
            this.fill();
            break;

          case _util.OPS.eoFill:
            this.eoFill();
            break;

          case _util.OPS.stroke:
            this.stroke();
            break;

          case _util.OPS.fillStroke:
            this.fillStroke();
            break;

          case _util.OPS.eoFillStroke:
            this.eoFillStroke();
            break;

          case _util.OPS.clip:
            this.clip("nonzero");
            break;

          case _util.OPS.eoClip:
            this.clip("evenodd");
            break;

          case _util.OPS.paintSolidColorImageMask:
            this.paintSolidColorImageMask();
            break;

          case _util.OPS.paintImageXObject:
            this.paintImageXObject(args[0]);
            break;

          case _util.OPS.paintInlineImageXObject:
            this.paintInlineImageXObject(args[0]);
            break;

          case _util.OPS.paintImageMaskXObject:
            this.paintImageMaskXObject(args[0]);
            break;

          case _util.OPS.paintFormXObjectBegin:
            this.paintFormXObjectBegin(args[0], args[1]);
            break;

          case _util.OPS.paintFormXObjectEnd:
            this.paintFormXObjectEnd();
            break;

          case _util.OPS.closePath:
            this.closePath();
            break;

          case _util.OPS.closeStroke:
            this.closeStroke();
            break;

          case _util.OPS.closeFillStroke:
            this.closeFillStroke();
            break;

          case _util.OPS.closeEOFillStroke:
            this.closeEOFillStroke();
            break;

          case _util.OPS.nextLine:
            this.nextLine();
            break;

          case _util.OPS.transform:
            this.transform(args[0], args[1], args[2], args[3], args[4], args[5]);
            break;

          case _util.OPS.constructPath:
            this.constructPath(args[0], args[1]);
            break;

          case _util.OPS.endPath:
            this.endPath();
            break;

          case 92:
            this.group(opTreeElement.items);
            break;

          default:
            (0, _util.warn)(`Unimplemented operator ${fn}`);
            break;
        }
      }
    }

    setWordSpacing(wordSpacing) {
      this.current.wordSpacing = wordSpacing;
    }

    setCharSpacing(charSpacing) {
      this.current.charSpacing = charSpacing;
    }

    nextLine() {
      this.moveText(0, this.current.leading);
    }

    setTextMatrix(a, b, c, d, e, f) {
      const current = this.current;
      current.textMatrix = current.lineMatrix = [a, b, c, d, e, f];
      current.textMatrixScale = Math.hypot(a, b);
      current.x = current.lineX = 0;
      current.y = current.lineY = 0;
      current.xcoords = [];
      current.ycoords = [];
      current.tspan = this.svgFactory.createElement("svg:tspan");
      current.tspan.setAttributeNS(null, "font-family", current.fontFamily);
      current.tspan.setAttributeNS(null, "font-size", `${pf(current.fontSize)}px`);
      current.tspan.setAttributeNS(null, "y", pf(-current.y));
      current.txtElement = this.svgFactory.createElement("svg:text");
      current.txtElement.append(current.tspan);
    }

    beginText() {
      const current = this.current;
      current.x = current.lineX = 0;
      current.y = current.lineY = 0;
      current.textMatrix = _util.IDENTITY_MATRIX;
      current.lineMatrix = _util.IDENTITY_MATRIX;
      current.textMatrixScale = 1;
      current.tspan = this.svgFactory.createElement("svg:tspan");
      current.txtElement = this.svgFactory.createElement("svg:text");
      current.txtgrp = this.svgFactory.createElement("svg:g");
      current.xcoords = [];
      current.ycoords = [];
    }

    moveText(x, y) {
      const current = this.current;
      current.x = current.lineX += x;
      current.y = current.lineY += y;
      current.xcoords = [];
      current.ycoords = [];
      current.tspan = this.svgFactory.createElement("svg:tspan");
      current.tspan.setAttributeNS(null, "font-family", current.fontFamily);
      current.tspan.setAttributeNS(null, "font-size", `${pf(current.fontSize)}px`);
      current.tspan.setAttributeNS(null, "y", pf(-current.y));
    }

    showText(glyphs) {
      const current = this.current;
      const font = current.font;
      const fontSize = current.fontSize;

      if (fontSize === 0) {
        return;
      }

      const fontSizeScale = current.fontSizeScale;
      const charSpacing = current.charSpacing;
      const wordSpacing = current.wordSpacing;
      const fontDirection = current.fontDirection;
      const textHScale = current.textHScale * fontDirection;
      const vertical = font.vertical;
      const spacingDir = vertical ? 1 : -1;
      const defaultVMetrics = font.defaultVMetrics;
      const widthAdvanceScale = fontSize * current.fontMatrix[0];
      let x = 0;

      for (const glyph of glyphs) {
        if (glyph === null) {
          x += fontDirection * wordSpacing;
          continue;
        } else if (typeof glyph === "number") {
          x += spacingDir * glyph * fontSize / 1000;
          continue;
        }

        const spacing = (glyph.isSpace ? wordSpacing : 0) + charSpacing;
        const character = glyph.fontChar;
        let scaledX, scaledY;
        let width = glyph.width;

        if (vertical) {
          let vx;
          const vmetric = glyph.vmetric || defaultVMetrics;
          vx = glyph.vmetric ? vmetric[1] : width * 0.5;
          vx = -vx * widthAdvanceScale;
          const vy = vmetric[2] * widthAdvanceScale;
          width = vmetric ? -vmetric[0] : width;
          scaledX = vx / fontSizeScale;
          scaledY = (x + vy) / fontSizeScale;
        } else {
          scaledX = x / fontSizeScale;
          scaledY = 0;
        }

        if (glyph.isInFont || font.missingFile) {
          current.xcoords.push(current.x + scaledX);

          if (vertical) {
            current.ycoords.push(-current.y + scaledY);
          }

          current.tspan.textContent += character;
        } else {}

        let charWidth;

        if (vertical) {
          charWidth = width * widthAdvanceScale - spacing * fontDirection;
        } else {
          charWidth = width * widthAdvanceScale + spacing * fontDirection;
        }

        x += charWidth;
      }

      current.tspan.setAttributeNS(null, "x", current.xcoords.map(pf).join(" "));

      if (vertical) {
        current.tspan.setAttributeNS(null, "y", current.ycoords.map(pf).join(" "));
      } else {
        current.tspan.setAttributeNS(null, "y", pf(-current.y));
      }

      if (vertical) {
        current.y -= x;
      } else {
        current.x += x * textHScale;
      }

      current.tspan.setAttributeNS(null, "font-family", current.fontFamily);
      current.tspan.setAttributeNS(null, "font-size", `${pf(current.fontSize)}px`);

      if (current.fontStyle !== SVG_DEFAULTS.fontStyle) {
        current.tspan.setAttributeNS(null, "font-style", current.fontStyle);
      }

      if (current.fontWeight !== SVG_DEFAULTS.fontWeight) {
        current.tspan.setAttributeNS(null, "font-weight", current.fontWeight);
      }

      const fillStrokeMode = current.textRenderingMode & _util.TextRenderingMode.FILL_STROKE_MASK;

      if (fillStrokeMode === _util.TextRenderingMode.FILL || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        if (current.fillColor !== SVG_DEFAULTS.fillColor) {
          current.tspan.setAttributeNS(null, "fill", current.fillColor);
        }

        if (current.fillAlpha < 1) {
          current.tspan.setAttributeNS(null, "fill-opacity", current.fillAlpha);
        }
      } else if (current.textRenderingMode === _util.TextRenderingMode.ADD_TO_PATH) {
        current.tspan.setAttributeNS(null, "fill", "transparent");
      } else {
        current.tspan.setAttributeNS(null, "fill", "none");
      }

      if (fillStrokeMode === _util.TextRenderingMode.STROKE || fillStrokeMode === _util.TextRenderingMode.FILL_STROKE) {
        const lineWidthScale = 1 / (current.textMatrixScale || 1);

        this._setStrokeAttributes(current.tspan, lineWidthScale);
      }

      let textMatrix = current.textMatrix;

      if (current.textRise !== 0) {
        textMatrix = textMatrix.slice();
        textMatrix[5] += current.textRise;
      }

      current.txtElement.setAttributeNS(null, "transform", `${pm(textMatrix)} scale(${pf(textHScale)}, -1)`);
      current.txtElement.setAttributeNS(XML_NS, "xml:space", "preserve");
      current.txtElement.append(current.tspan);
      current.txtgrp.append(current.txtElement);

      this._ensureTransformGroup().append(current.txtElement);
    }

    setLeadingMoveText(x, y) {
      this.setLeading(-y);
      this.moveText(x, y);
    }

    addFontStyle(fontObj) {
      if (!fontObj.data) {
        throw new Error("addFontStyle: No font data available, " + 'ensure that the "fontExtraProperties" API parameter is set.');
      }

      if (!this.cssStyle) {
        this.cssStyle = this.svgFactory.createElement("svg:style");
        this.cssStyle.setAttributeNS(null, "type", "text/css");
        this.defs.append(this.cssStyle);
      }

      const url = createObjectURL(fontObj.data, fontObj.mimetype, this.forceDataSchema);
      this.cssStyle.textContent += `@font-face { font-family: "${fontObj.loadedName}";` + ` src: url(${url}); }\n`;
    }

    setFont(details) {
      const current = this.current;
      const fontObj = this.commonObjs.get(details[0]);
      let size = details[1];
      current.font = fontObj;

      if (this.embedFonts && !fontObj.missingFile && !this.embeddedFonts[fontObj.loadedName]) {
        this.addFontStyle(fontObj);
        this.embeddedFonts[fontObj.loadedName] = fontObj;
      }

      current.fontMatrix = fontObj.fontMatrix || _util.FONT_IDENTITY_MATRIX;
      let bold = "normal";

      if (fontObj.black) {
        bold = "900";
      } else if (fontObj.bold) {
        bold = "bold";
      }

      const italic = fontObj.italic ? "italic" : "normal";

      if (size < 0) {
        size = -size;
        current.fontDirection = -1;
      } else {
        current.fontDirection = 1;
      }

      current.fontSize = size;
      current.fontFamily = fontObj.loadedName;
      current.fontWeight = bold;
      current.fontStyle = italic;
      current.tspan = this.svgFactory.createElement("svg:tspan");
      current.tspan.setAttributeNS(null, "y", pf(-current.y));
      current.xcoords = [];
      current.ycoords = [];
    }

    endText() {
      var _current$txtElement;

      const current = this.current;

      if (current.textRenderingMode & _util.TextRenderingMode.ADD_TO_PATH_FLAG && (_current$txtElement = current.txtElement) !== null && _current$txtElement !== void 0 && _current$txtElement.hasChildNodes()) {
        current.element = current.txtElement;
        this.clip("nonzero");
        this.endPath();
      }
    }

    setLineWidth(width) {
      if (width > 0) {
        this.current.lineWidth = width;
      }
    }

    setLineCap(style) {
      this.current.lineCap = LINE_CAP_STYLES[style];
    }

    setLineJoin(style) {
      this.current.lineJoin = LINE_JOIN_STYLES[style];
    }

    setMiterLimit(limit) {
      this.current.miterLimit = limit;
    }

    setStrokeAlpha(strokeAlpha) {
      this.current.strokeAlpha = strokeAlpha;
    }

    setStrokeRGBColor(r, g, b) {
      this.current.strokeColor = _util.Util.makeHexColor(r, g, b);
    }

    setFillAlpha(fillAlpha) {
      this.current.fillAlpha = fillAlpha;
    }

    setFillRGBColor(r, g, b) {
      this.current.fillColor = _util.Util.makeHexColor(r, g, b);
      this.current.tspan = this.svgFactory.createElement("svg:tspan");
      this.current.xcoords = [];
      this.current.ycoords = [];
    }

    setStrokeColorN(args) {
      this.current.strokeColor = this._makeColorN_Pattern(args);
    }

    setFillColorN(args) {
      this.current.fillColor = this._makeColorN_Pattern(args);
    }

    shadingFill(args) {
      const width = this.viewport.width;
      const height = this.viewport.height;

      const inv = _util.Util.inverseTransform(this.transformMatrix);

      const bl = _util.Util.applyTransform([0, 0], inv);

      const br = _util.Util.applyTransform([0, height], inv);

      const ul = _util.Util.applyTransform([width, 0], inv);

      const ur = _util.Util.applyTransform([width, height], inv);

      const x0 = Math.min(bl[0], br[0], ul[0], ur[0]);
      const y0 = Math.min(bl[1], br[1], ul[1], ur[1]);
      const x1 = Math.max(bl[0], br[0], ul[0], ur[0]);
      const y1 = Math.max(bl[1], br[1], ul[1], ur[1]);
      const rect = this.svgFactory.createElement("svg:rect");
      rect.setAttributeNS(null, "x", x0);
      rect.setAttributeNS(null, "y", y0);
      rect.setAttributeNS(null, "width", x1 - x0);
      rect.setAttributeNS(null, "height", y1 - y0);
      rect.setAttributeNS(null, "fill", this._makeShadingPattern(args));

      if (this.current.fillAlpha < 1) {
        rect.setAttributeNS(null, "fill-opacity", this.current.fillAlpha);
      }

      this._ensureTransformGroup().append(rect);
    }

    _makeColorN_Pattern(args) {
      if (args[0] === "TilingPattern") {
        return this._makeTilingPattern(args);
      }

      return this._makeShadingPattern(args);
    }

    _makeTilingPattern(args) {
      const color = args[1];
      const operatorList = args[2];
      const matrix = args[3] || _util.IDENTITY_MATRIX;
      const [x0, y0, x1, y1] = args[4];
      const xstep = args[5];
      const ystep = args[6];
      const paintType = args[7];
      const tilingId = `shading${shadingCount++}`;

      const [tx0, ty0, tx1, ty1] = _util.Util.normalizeRect([..._util.Util.applyTransform([x0, y0], matrix), ..._util.Util.applyTransform([x1, y1], matrix)]);

      const [xscale, yscale] = _util.Util.singularValueDecompose2dScale(matrix);

      const txstep = xstep * xscale;
      const tystep = ystep * yscale;
      const tiling = this.svgFactory.createElement("svg:pattern");
      tiling.setAttributeNS(null, "id", tilingId);
      tiling.setAttributeNS(null, "patternUnits", "userSpaceOnUse");
      tiling.setAttributeNS(null, "width", txstep);
      tiling.setAttributeNS(null, "height", tystep);
      tiling.setAttributeNS(null, "x", `${tx0}`);
      tiling.setAttributeNS(null, "y", `${ty0}`);
      const svg = this.svg;
      const transformMatrix = this.transformMatrix;
      const fillColor = this.current.fillColor;
      const strokeColor = this.current.strokeColor;
      const bbox = this.svgFactory.create(tx1 - tx0, ty1 - ty0);
      this.svg = bbox;
      this.transformMatrix = matrix;

      if (paintType === 2) {
        const cssColor = _util.Util.makeHexColor(...color);

        this.current.fillColor = cssColor;
        this.current.strokeColor = cssColor;
      }

      this.executeOpTree(this.convertOpList(operatorList));
      this.svg = svg;
      this.transformMatrix = transformMatrix;
      this.current.fillColor = fillColor;
      this.current.strokeColor = strokeColor;
      tiling.append(bbox.childNodes[0]);
      this.defs.append(tiling);
      return `url(#${tilingId})`;
    }

    _makeShadingPattern(args) {
      if (typeof args === "string") {
        args = this.objs.get(args);
      }

      switch (args[0]) {
        case "RadialAxial":
          const shadingId = `shading${shadingCount++}`;
          const colorStops = args[3];
          let gradient;

          switch (args[1]) {
            case "axial":
              const point0 = args[4];
              const point1 = args[5];
              gradient = this.svgFactory.createElement("svg:linearGradient");
              gradient.setAttributeNS(null, "id", shadingId);
              gradient.setAttributeNS(null, "gradientUnits", "userSpaceOnUse");
              gradient.setAttributeNS(null, "x1", point0[0]);
              gradient.setAttributeNS(null, "y1", point0[1]);
              gradient.setAttributeNS(null, "x2", point1[0]);
              gradient.setAttributeNS(null, "y2", point1[1]);
              break;

            case "radial":
              const focalPoint = args[4];
              const circlePoint = args[5];
              const focalRadius = args[6];
              const circleRadius = args[7];
              gradient = this.svgFactory.createElement("svg:radialGradient");
              gradient.setAttributeNS(null, "id", shadingId);
              gradient.setAttributeNS(null, "gradientUnits", "userSpaceOnUse");
              gradient.setAttributeNS(null, "cx", circlePoint[0]);
              gradient.setAttributeNS(null, "cy", circlePoint[1]);
              gradient.setAttributeNS(null, "r", circleRadius);
              gradient.setAttributeNS(null, "fx", focalPoint[0]);
              gradient.setAttributeNS(null, "fy", focalPoint[1]);
              gradient.setAttributeNS(null, "fr", focalRadius);
              break;

            default:
              throw new Error(`Unknown RadialAxial type: ${args[1]}`);
          }

          for (const colorStop of colorStops) {
            const stop = this.svgFactory.createElement("svg:stop");
            stop.setAttributeNS(null, "offset", colorStop[0]);
            stop.setAttributeNS(null, "stop-color", colorStop[1]);
            gradient.append(stop);
          }

          this.defs.append(gradient);
          return `url(#${shadingId})`;

        case "Mesh":
          (0, _util.warn)("Unimplemented pattern Mesh");
          return null;

        case "Dummy":
          return "hotpink";

        default:
          throw new Error(`Unknown IR type: ${args[0]}`);
      }
    }

    setDash(dashArray, dashPhase) {
      this.current.dashArray = dashArray;
      this.current.dashPhase = dashPhase;
    }

    constructPath(ops, args) {
      const current = this.current;
      let x = current.x,
          y = current.y;
      let d = [];
      let j = 0;

      for (const op of ops) {
        switch (op | 0) {
          case _util.OPS.rectangle:
            x = args[j++];
            y = args[j++];
            const width = args[j++];
            const height = args[j++];
            const xw = x + width;
            const yh = y + height;
            d.push("M", pf(x), pf(y), "L", pf(xw), pf(y), "L", pf(xw), pf(yh), "L", pf(x), pf(yh), "Z");
            break;

          case _util.OPS.moveTo:
            x = args[j++];
            y = args[j++];
            d.push("M", pf(x), pf(y));
            break;

          case _util.OPS.lineTo:
            x = args[j++];
            y = args[j++];
            d.push("L", pf(x), pf(y));
            break;

          case _util.OPS.curveTo:
            x = args[j + 4];
            y = args[j + 5];
            d.push("C", pf(args[j]), pf(args[j + 1]), pf(args[j + 2]), pf(args[j + 3]), pf(x), pf(y));
            j += 6;
            break;

          case _util.OPS.curveTo2:
            d.push("C", pf(x), pf(y), pf(args[j]), pf(args[j + 1]), pf(args[j + 2]), pf(args[j + 3]));
            x = args[j + 2];
            y = args[j + 3];
            j += 4;
            break;

          case _util.OPS.curveTo3:
            x = args[j + 2];
            y = args[j + 3];
            d.push("C", pf(args[j]), pf(args[j + 1]), pf(x), pf(y), pf(x), pf(y));
            j += 4;
            break;

          case _util.OPS.closePath:
            d.push("Z");
            break;
        }
      }

      d = d.join(" ");

      if (current.path && ops.length > 0 && ops[0] !== _util.OPS.rectangle && ops[0] !== _util.OPS.moveTo) {
        d = current.path.getAttributeNS(null, "d") + d;
      } else {
        current.path = this.svgFactory.createElement("svg:path");

        this._ensureTransformGroup().append(current.path);
      }

      current.path.setAttributeNS(null, "d", d);
      current.path.setAttributeNS(null, "fill", "none");
      current.element = current.path;
      current.setCurrentPoint(x, y);
    }

    endPath() {
      const current = this.current;
      current.path = null;

      if (!this.pendingClip) {
        return;
      }

      if (!current.element) {
        this.pendingClip = null;
        return;
      }

      const clipId = `clippath${clipCount++}`;
      const clipPath = this.svgFactory.createElement("svg:clipPath");
      clipPath.setAttributeNS(null, "id", clipId);
      clipPath.setAttributeNS(null, "transform", pm(this.transformMatrix));
      const clipElement = current.element.cloneNode(true);

      if (this.pendingClip === "evenodd") {
        clipElement.setAttributeNS(null, "clip-rule", "evenodd");
      } else {
        clipElement.setAttributeNS(null, "clip-rule", "nonzero");
      }

      this.pendingClip = null;
      clipPath.append(clipElement);
      this.defs.append(clipPath);

      if (current.activeClipUrl) {
        current.clipGroup = null;

        for (const prev of this.extraStack) {
          prev.clipGroup = null;
        }

        clipPath.setAttributeNS(null, "clip-path", current.activeClipUrl);
      }

      current.activeClipUrl = `url(#${clipId})`;
      this.tgrp = null;
    }

    clip(type) {
      this.pendingClip = type;
    }

    closePath() {
      const current = this.current;

      if (current.path) {
        const d = `${current.path.getAttributeNS(null, "d")}Z`;
        current.path.setAttributeNS(null, "d", d);
      }
    }

    setLeading(leading) {
      this.current.leading = -leading;
    }

    setTextRise(textRise) {
      this.current.textRise = textRise;
    }

    setTextRenderingMode(textRenderingMode) {
      this.current.textRenderingMode = textRenderingMode;
    }

    setHScale(scale) {
      this.current.textHScale = scale / 100;
    }

    setRenderingIntent(intent) {}

    setFlatness(flatness) {}

    setGState(states) {
      for (const [key, value] of states) {
        switch (key) {
          case "LW":
            this.setLineWidth(value);
            break;

          case "LC":
            this.setLineCap(value);
            break;

          case "LJ":
            this.setLineJoin(value);
            break;

          case "ML":
            this.setMiterLimit(value);
            break;

          case "D":
            this.setDash(value[0], value[1]);
            break;

          case "RI":
            this.setRenderingIntent(value);
            break;

          case "FL":
            this.setFlatness(value);
            break;

          case "Font":
            this.setFont(value);
            break;

          case "CA":
            this.setStrokeAlpha(value);
            break;

          case "ca":
            this.setFillAlpha(value);
            break;

          default:
            (0, _util.warn)(`Unimplemented graphic state operator ${key}`);
            break;
        }
      }
    }

    fill() {
      const current = this.current;

      if (current.element) {
        current.element.setAttributeNS(null, "fill", current.fillColor);
        current.element.setAttributeNS(null, "fill-opacity", current.fillAlpha);
        this.endPath();
      }
    }

    stroke() {
      const current = this.current;

      if (current.element) {
        this._setStrokeAttributes(current.element);

        current.element.setAttributeNS(null, "fill", "none");
        this.endPath();
      }
    }

    _setStrokeAttributes(element) {
      let lineWidthScale = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 1;
      const current = this.current;
      let dashArray = current.dashArray;

      if (lineWidthScale !== 1 && dashArray.length > 0) {
        dashArray = dashArray.map(function (value) {
          return lineWidthScale * value;
        });
      }

      element.setAttributeNS(null, "stroke", current.strokeColor);
      element.setAttributeNS(null, "stroke-opacity", current.strokeAlpha);
      element.setAttributeNS(null, "stroke-miterlimit", pf(current.miterLimit));
      element.setAttributeNS(null, "stroke-linecap", current.lineCap);
      element.setAttributeNS(null, "stroke-linejoin", current.lineJoin);
      element.setAttributeNS(null, "stroke-width", pf(lineWidthScale * current.lineWidth) + "px");
      element.setAttributeNS(null, "stroke-dasharray", dashArray.map(pf).join(" "));
      element.setAttributeNS(null, "stroke-dashoffset", pf(lineWidthScale * current.dashPhase) + "px");
    }

    eoFill() {
      if (this.current.element) {
        this.current.element.setAttributeNS(null, "fill-rule", "evenodd");
      }

      this.fill();
    }

    fillStroke() {
      this.stroke();
      this.fill();
    }

    eoFillStroke() {
      if (this.current.element) {
        this.current.element.setAttributeNS(null, "fill-rule", "evenodd");
      }

      this.fillStroke();
    }

    closeStroke() {
      this.closePath();
      this.stroke();
    }

    closeFillStroke() {
      this.closePath();
      this.fillStroke();
    }

    closeEOFillStroke() {
      this.closePath();
      this.eoFillStroke();
    }

    paintSolidColorImageMask() {
      const rect = this.svgFactory.createElement("svg:rect");
      rect.setAttributeNS(null, "x", "0");
      rect.setAttributeNS(null, "y", "0");
      rect.setAttributeNS(null, "width", "1px");
      rect.setAttributeNS(null, "height", "1px");
      rect.setAttributeNS(null, "fill", this.current.fillColor);

      this._ensureTransformGroup().append(rect);
    }

    paintImageXObject(objId) {
      const imgData = objId.startsWith("g_") ? this.commonObjs.get(objId) : this.objs.get(objId);

      if (!imgData) {
        (0, _util.warn)(`Dependent image with object ID ${objId} is not ready yet`);
        return;
      }

      this.paintInlineImageXObject(imgData);
    }

    paintInlineImageXObject(imgData, mask) {
      const width = imgData.width;
      const height = imgData.height;
      const imgSrc = convertImgDataToPng(imgData, this.forceDataSchema, !!mask);
      const cliprect = this.svgFactory.createElement("svg:rect");
      cliprect.setAttributeNS(null, "x", "0");
      cliprect.setAttributeNS(null, "y", "0");
      cliprect.setAttributeNS(null, "width", pf(width));
      cliprect.setAttributeNS(null, "height", pf(height));
      this.current.element = cliprect;
      this.clip("nonzero");
      const imgEl = this.svgFactory.createElement("svg:image");
      imgEl.setAttributeNS(XLINK_NS, "xlink:href", imgSrc);
      imgEl.setAttributeNS(null, "x", "0");
      imgEl.setAttributeNS(null, "y", pf(-height));
      imgEl.setAttributeNS(null, "width", pf(width) + "px");
      imgEl.setAttributeNS(null, "height", pf(height) + "px");
      imgEl.setAttributeNS(null, "transform", `scale(${pf(1 / width)} ${pf(-1 / height)})`);

      if (mask) {
        mask.append(imgEl);
      } else {
        this._ensureTransformGroup().append(imgEl);
      }
    }

    paintImageMaskXObject(imgData) {
      const current = this.current;
      const width = imgData.width;
      const height = imgData.height;
      const fillColor = current.fillColor;
      current.maskId = `mask${maskCount++}`;
      const mask = this.svgFactory.createElement("svg:mask");
      mask.setAttributeNS(null, "id", current.maskId);
      const rect = this.svgFactory.createElement("svg:rect");
      rect.setAttributeNS(null, "x", "0");
      rect.setAttributeNS(null, "y", "0");
      rect.setAttributeNS(null, "width", pf(width));
      rect.setAttributeNS(null, "height", pf(height));
      rect.setAttributeNS(null, "fill", fillColor);
      rect.setAttributeNS(null, "mask", `url(#${current.maskId})`);
      this.defs.append(mask);

      this._ensureTransformGroup().append(rect);

      this.paintInlineImageXObject(imgData, mask);
    }

    paintFormXObjectBegin(matrix, bbox) {
      if (Array.isArray(matrix) && matrix.length === 6) {
        this.transform(matrix[0], matrix[1], matrix[2], matrix[3], matrix[4], matrix[5]);
      }

      if (bbox) {
        const width = bbox[2] - bbox[0];
        const height = bbox[3] - bbox[1];
        const cliprect = this.svgFactory.createElement("svg:rect");
        cliprect.setAttributeNS(null, "x", bbox[0]);
        cliprect.setAttributeNS(null, "y", bbox[1]);
        cliprect.setAttributeNS(null, "width", pf(width));
        cliprect.setAttributeNS(null, "height", pf(height));
        this.current.element = cliprect;
        this.clip("nonzero");
        this.endPath();
      }
    }

    paintFormXObjectEnd() {}

    _initialize(viewport) {
      const svg = this.svgFactory.create(viewport.width, viewport.height);
      const definitions = this.svgFactory.createElement("svg:defs");
      svg.append(definitions);
      this.defs = definitions;
      const rootGroup = this.svgFactory.createElement("svg:g");
      rootGroup.setAttributeNS(null, "transform", pm(viewport.transform));
      svg.append(rootGroup);
      this.svg = rootGroup;
      return svg;
    }

    _ensureClipGroup() {
      if (!this.current.clipGroup) {
        const clipGroup = this.svgFactory.createElement("svg:g");
        clipGroup.setAttributeNS(null, "clip-path", this.current.activeClipUrl);
        this.svg.append(clipGroup);
        this.current.clipGroup = clipGroup;
      }

      return this.current.clipGroup;
    }

    _ensureTransformGroup() {
      if (!this.tgrp) {
        this.tgrp = this.svgFactory.createElement("svg:g");
        this.tgrp.setAttributeNS(null, "transform", pm(this.transformMatrix));

        if (this.current.activeClipUrl) {
          this._ensureClipGroup().append(this.tgrp);
        } else {
          this.svg.append(this.tgrp);
        }
      }

      return this.tgrp;
    }

  };
}

/***/ }),
/* 157 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.PDFNodeStream = void 0;

var _util = __w_pdfjs_require__(1);

var _network_utils = __w_pdfjs_require__(158);

;

const fs = require("fs");

const http = require("http");

const https = require("https");

const url = require("url");

const fileUriRegex = /^file:\/\/\/[a-zA-Z]:\//;

function parseUrl(sourceUrl) {
  const parsedUrl = url.parse(sourceUrl);

  if (parsedUrl.protocol === "file:" || parsedUrl.host) {
    return parsedUrl;
  }

  if (/^[a-z]:[/\\]/i.test(sourceUrl)) {
    return url.parse(`file:///${sourceUrl}`);
  }

  if (!parsedUrl.host) {
    parsedUrl.protocol = "file:";
  }

  return parsedUrl;
}

class PDFNodeStream {
  constructor(source) {
    this.source = source;
    this.url = parseUrl(source.url);
    this.isHttp = this.url.protocol === "http:" || this.url.protocol === "https:";
    this.isFsUrl = this.url.protocol === "file:";
    this.httpHeaders = this.isHttp && source.httpHeaders || {};
    this._fullRequestReader = null;
    this._rangeRequestReaders = [];
  }

  get _progressiveDataLength() {
    var _this$_fullRequestRea, _this$_fullRequestRea2;

    return (_this$_fullRequestRea = (_this$_fullRequestRea2 = this._fullRequestReader) === null || _this$_fullRequestRea2 === void 0 ? void 0 : _this$_fullRequestRea2._loaded) !== null && _this$_fullRequestRea !== void 0 ? _this$_fullRequestRea : 0;
  }

  getFullReader() {
    (0, _util.assert)(!this._fullRequestReader, "PDFNodeStream.getFullReader can only be called once.");
    this._fullRequestReader = this.isFsUrl ? new PDFNodeStreamFsFullReader(this) : new PDFNodeStreamFullReader(this);
    return this._fullRequestReader;
  }

  getRangeReader(start, end) {
    if (end <= this._progressiveDataLength) {
      return null;
    }

    const rangeReader = this.isFsUrl ? new PDFNodeStreamFsRangeReader(this, start, end) : new PDFNodeStreamRangeReader(this, start, end);

    this._rangeRequestReaders.push(rangeReader);

    return rangeReader;
  }

  cancelAllRequests(reason) {
    if (this._fullRequestReader) {
      this._fullRequestReader.cancel(reason);
    }

    for (const reader of this._rangeRequestReaders.slice(0)) {
      reader.cancel(reason);
    }
  }

}

exports.PDFNodeStream = PDFNodeStream;

class BaseFullReader {
  constructor(stream) {
    this._url = stream.url;
    this._done = false;
    this._storedError = null;
    this.onProgress = null;
    const source = stream.source;
    this._contentLength = source.length;
    this._loaded = 0;
    this._filename = null;
    this._disableRange = source.disableRange || false;
    this._rangeChunkSize = source.rangeChunkSize;

    if (!this._rangeChunkSize && !this._disableRange) {
      this._disableRange = true;
    }

    this._isStreamingSupported = !source.disableStream;
    this._isRangeSupported = !source.disableRange;
    this._readableStream = null;
    this._readCapability = (0, _util.createPromiseCapability)();
    this._headersCapability = (0, _util.createPromiseCapability)();
  }

  get headersReady() {
    return this._headersCapability.promise;
  }

  get filename() {
    return this._filename;
  }

  get contentLength() {
    return this._contentLength;
  }

  get isRangeSupported() {
    return this._isRangeSupported;
  }

  get isStreamingSupported() {
    return this._isStreamingSupported;
  }

  async read() {
    await this._readCapability.promise;

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    if (this._storedError) {
      throw this._storedError;
    }

    const chunk = this._readableStream.read();

    if (chunk === null) {
      this._readCapability = (0, _util.createPromiseCapability)();
      return this.read();
    }

    this._loaded += chunk.length;

    if (this.onProgress) {
      this.onProgress({
        loaded: this._loaded,
        total: this._contentLength
      });
    }

    const buffer = new Uint8Array(chunk).buffer;
    return {
      value: buffer,
      done: false
    };
  }

  cancel(reason) {
    if (!this._readableStream) {
      this._error(reason);

      return;
    }

    this._readableStream.destroy(reason);
  }

  _error(reason) {
    this._storedError = reason;

    this._readCapability.resolve();
  }

  _setReadableStream(readableStream) {
    this._readableStream = readableStream;
    readableStream.on("readable", () => {
      this._readCapability.resolve();
    });
    readableStream.on("end", () => {
      readableStream.destroy();
      this._done = true;

      this._readCapability.resolve();
    });
    readableStream.on("error", reason => {
      this._error(reason);
    });

    if (!this._isStreamingSupported && this._isRangeSupported) {
      this._error(new _util.AbortException("streaming is disabled"));
    }

    if (this._storedError) {
      this._readableStream.destroy(this._storedError);
    }
  }

}

class BaseRangeReader {
  constructor(stream) {
    this._url = stream.url;
    this._done = false;
    this._storedError = null;
    this.onProgress = null;
    this._loaded = 0;
    this._readableStream = null;
    this._readCapability = (0, _util.createPromiseCapability)();
    const source = stream.source;
    this._isStreamingSupported = !source.disableStream;
  }

  get isStreamingSupported() {
    return this._isStreamingSupported;
  }

  async read() {
    await this._readCapability.promise;

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    if (this._storedError) {
      throw this._storedError;
    }

    const chunk = this._readableStream.read();

    if (chunk === null) {
      this._readCapability = (0, _util.createPromiseCapability)();
      return this.read();
    }

    this._loaded += chunk.length;

    if (this.onProgress) {
      this.onProgress({
        loaded: this._loaded
      });
    }

    const buffer = new Uint8Array(chunk).buffer;
    return {
      value: buffer,
      done: false
    };
  }

  cancel(reason) {
    if (!this._readableStream) {
      this._error(reason);

      return;
    }

    this._readableStream.destroy(reason);
  }

  _error(reason) {
    this._storedError = reason;

    this._readCapability.resolve();
  }

  _setReadableStream(readableStream) {
    this._readableStream = readableStream;
    readableStream.on("readable", () => {
      this._readCapability.resolve();
    });
    readableStream.on("end", () => {
      readableStream.destroy();
      this._done = true;

      this._readCapability.resolve();
    });
    readableStream.on("error", reason => {
      this._error(reason);
    });

    if (this._storedError) {
      this._readableStream.destroy(this._storedError);
    }
  }

}

function createRequestOptions(parsedUrl, headers) {
  return {
    protocol: parsedUrl.protocol,
    auth: parsedUrl.auth,
    host: parsedUrl.hostname,
    port: parsedUrl.port,
    path: parsedUrl.path,
    method: "GET",
    headers
  };
}

class PDFNodeStreamFullReader extends BaseFullReader {
  constructor(stream) {
    super(stream);

    const handleResponse = response => {
      if (response.statusCode === 404) {
        const error = new _util.MissingPDFException(`Missing PDF "${this._url}".`);
        this._storedError = error;

        this._headersCapability.reject(error);

        return;
      }

      this._headersCapability.resolve();

      this._setReadableStream(response);

      const getResponseHeader = name => {
        return this._readableStream.headers[name.toLowerCase()];
      };

      const {
        allowRangeRequests,
        suggestedLength
      } = (0, _network_utils.validateRangeRequestCapabilities)({
        getResponseHeader,
        isHttp: stream.isHttp,
        rangeChunkSize: this._rangeChunkSize,
        disableRange: this._disableRange
      });
      this._isRangeSupported = allowRangeRequests;
      this._contentLength = suggestedLength || this._contentLength;
      this._filename = (0, _network_utils.extractFilenameFromHeader)(getResponseHeader);
    };

    this._request = null;

    if (this._url.protocol === "http:") {
      this._request = http.request(createRequestOptions(this._url, stream.httpHeaders), handleResponse);
    } else {
      this._request = https.request(createRequestOptions(this._url, stream.httpHeaders), handleResponse);
    }

    this._request.on("error", reason => {
      this._storedError = reason;

      this._headersCapability.reject(reason);
    });

    this._request.end();
  }

}

class PDFNodeStreamRangeReader extends BaseRangeReader {
  constructor(stream, start, end) {
    super(stream);
    this._httpHeaders = {};

    for (const property in stream.httpHeaders) {
      const value = stream.httpHeaders[property];

      if (typeof value === "undefined") {
        continue;
      }

      this._httpHeaders[property] = value;
    }

    this._httpHeaders.Range = `bytes=${start}-${end - 1}`;

    const handleResponse = response => {
      if (response.statusCode === 404) {
        const error = new _util.MissingPDFException(`Missing PDF "${this._url}".`);
        this._storedError = error;
        return;
      }

      this._setReadableStream(response);
    };

    this._request = null;

    if (this._url.protocol === "http:") {
      this._request = http.request(createRequestOptions(this._url, this._httpHeaders), handleResponse);
    } else {
      this._request = https.request(createRequestOptions(this._url, this._httpHeaders), handleResponse);
    }

    this._request.on("error", reason => {
      this._storedError = reason;
    });

    this._request.end();
  }

}

class PDFNodeStreamFsFullReader extends BaseFullReader {
  constructor(stream) {
    super(stream);
    let path = decodeURIComponent(this._url.path);

    if (fileUriRegex.test(this._url.href)) {
      path = path.replace(/^\//, "");
    }

    fs.lstat(path, (error, stat) => {
      if (error) {
        if (error.code === "ENOENT") {
          error = new _util.MissingPDFException(`Missing PDF "${path}".`);
        }

        this._storedError = error;

        this._headersCapability.reject(error);

        return;
      }

      this._contentLength = stat.size;

      this._setReadableStream(fs.createReadStream(path));

      this._headersCapability.resolve();
    });
  }

}

class PDFNodeStreamFsRangeReader extends BaseRangeReader {
  constructor(stream, start, end) {
    super(stream);
    let path = decodeURIComponent(this._url.path);

    if (fileUriRegex.test(this._url.href)) {
      path = path.replace(/^\//, "");
    }

    this._setReadableStream(fs.createReadStream(path, {
      start,
      end: end - 1
    }));
  }

}

/***/ }),
/* 158 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.createResponseStatusError = createResponseStatusError;
exports.extractFilenameFromHeader = extractFilenameFromHeader;
exports.validateRangeRequestCapabilities = validateRangeRequestCapabilities;
exports.validateResponseStatus = validateResponseStatus;

var _util = __w_pdfjs_require__(1);

var _content_disposition = __w_pdfjs_require__(159);

var _display_utils = __w_pdfjs_require__(133);

function validateRangeRequestCapabilities(_ref) {
  let {
    getResponseHeader,
    isHttp,
    rangeChunkSize,
    disableRange
  } = _ref;
  const returnValues = {
    allowRangeRequests: false,
    suggestedLength: undefined
  };
  const length = parseInt(getResponseHeader("Content-Length"), 10);

  if (!Number.isInteger(length)) {
    return returnValues;
  }

  returnValues.suggestedLength = length;

  if (length <= 2 * rangeChunkSize) {
    return returnValues;
  }

  if (disableRange || !isHttp) {
    return returnValues;
  }

  if (getResponseHeader("Accept-Ranges") !== "bytes") {
    return returnValues;
  }

  const contentEncoding = getResponseHeader("Content-Encoding") || "identity";

  if (contentEncoding !== "identity") {
    return returnValues;
  }

  returnValues.allowRangeRequests = true;
  return returnValues;
}

function extractFilenameFromHeader(getResponseHeader) {
  const contentDisposition = getResponseHeader("Content-Disposition");

  if (contentDisposition) {
    let filename = (0, _content_disposition.getFilenameFromContentDispositionHeader)(contentDisposition);

    if (filename.includes("%")) {
      try {
        filename = decodeURIComponent(filename);
      } catch (ex) {}
    }

    if ((0, _display_utils.isPdfFile)(filename)) {
      return filename;
    }
  }

  return null;
}

function createResponseStatusError(status, url) {
  if (status === 404 || status === 0 && url.startsWith("file:")) {
    return new _util.MissingPDFException('Missing PDF "' + url + '".');
  }

  return new _util.UnexpectedResponseException(`Unexpected server response (${status}) while retrieving PDF "${url}".`, status);
}

function validateResponseStatus(status) {
  return status === 200 || status === 206;
}

/***/ }),
/* 159 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.getFilenameFromContentDispositionHeader = getFilenameFromContentDispositionHeader;

var _util = __w_pdfjs_require__(1);

function getFilenameFromContentDispositionHeader(contentDisposition) {
  let needsEncodingFixup = true;
  let tmp = toParamRegExp("filename\\*", "i").exec(contentDisposition);

  if (tmp) {
    tmp = tmp[1];
    let filename = rfc2616unquote(tmp);
    filename = unescape(filename);
    filename = rfc5987decode(filename);
    filename = rfc2047decode(filename);
    return fixupEncoding(filename);
  }

  tmp = rfc2231getparam(contentDisposition);

  if (tmp) {
    const filename = rfc2047decode(tmp);
    return fixupEncoding(filename);
  }

  tmp = toParamRegExp("filename", "i").exec(contentDisposition);

  if (tmp) {
    tmp = tmp[1];
    let filename = rfc2616unquote(tmp);
    filename = rfc2047decode(filename);
    return fixupEncoding(filename);
  }

  function toParamRegExp(attributePattern, flags) {
    return new RegExp("(?:^|;)\\s*" + attributePattern + "\\s*=\\s*" + "(" + '[^";\\s][^;\\s]*' + "|" + '"(?:[^"\\\\]|\\\\"?)+"?' + ")", flags);
  }

  function textdecode(encoding, value) {
    if (encoding) {
      if (!/^[\x00-\xFF]+$/.test(value)) {
        return value;
      }

      try {
        const decoder = new TextDecoder(encoding, {
          fatal: true
        });
        const buffer = (0, _util.stringToBytes)(value);
        value = decoder.decode(buffer);
        needsEncodingFixup = false;
      } catch (e) {}
    }

    return value;
  }

  function fixupEncoding(value) {
    if (needsEncodingFixup && /[\x80-\xff]/.test(value)) {
      value = textdecode("utf-8", value);

      if (needsEncodingFixup) {
        value = textdecode("iso-8859-1", value);
      }
    }

    return value;
  }

  function rfc2231getparam(contentDispositionStr) {
    const matches = [];
    let match;
    const iter = toParamRegExp("filename\\*((?!0\\d)\\d+)(\\*?)", "ig");

    while ((match = iter.exec(contentDispositionStr)) !== null) {
      let [, n, quot, part] = match;
      n = parseInt(n, 10);

      if (n in matches) {
        if (n === 0) {
          break;
        }

        continue;
      }

      matches[n] = [quot, part];
    }

    const parts = [];

    for (let n = 0; n < matches.length; ++n) {
      if (!(n in matches)) {
        break;
      }

      let [quot, part] = matches[n];
      part = rfc2616unquote(part);

      if (quot) {
        part = unescape(part);

        if (n === 0) {
          part = rfc5987decode(part);
        }
      }

      parts.push(part);
    }

    return parts.join("");
  }

  function rfc2616unquote(value) {
    if (value.startsWith('"')) {
      const parts = value.slice(1).split('\\"');

      for (let i = 0; i < parts.length; ++i) {
        const quotindex = parts[i].indexOf('"');

        if (quotindex !== -1) {
          parts[i] = parts[i].slice(0, quotindex);
          parts.length = i + 1;
        }

        parts[i] = parts[i].replace(/\\(.)/g, "$1");
      }

      value = parts.join('"');
    }

    return value;
  }

  function rfc5987decode(extvalue) {
    const encodingend = extvalue.indexOf("'");

    if (encodingend === -1) {
      return extvalue;
    }

    const encoding = extvalue.slice(0, encodingend);
    const langvalue = extvalue.slice(encodingend + 1);
    const value = langvalue.replace(/^[^']*'/, "");
    return textdecode(encoding, value);
  }

  function rfc2047decode(value) {
    if (!value.startsWith("=?") || /[\x00-\x19\x80-\xff]/.test(value)) {
      return value;
    }

    return value.replace(/=\?([\w-]*)\?([QqBb])\?((?:[^?]|\?(?!=))*)\?=/g, function (matches, charset, encoding, text) {
      if (encoding === "q" || encoding === "Q") {
        text = text.replace(/_/g, " ");
        text = text.replace(/=([0-9a-fA-F]{2})/g, function (match, hex) {
          return String.fromCharCode(parseInt(hex, 16));
        });
        return textdecode(charset, text);
      }

      try {
        text = atob(text);
      } catch (e) {}

      return textdecode(charset, text);
    });
  }

  return "";
}

/***/ }),
/* 160 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.PDFNetworkStream = void 0;

var _util = __w_pdfjs_require__(1);

var _network_utils = __w_pdfjs_require__(158);

;
const OK_RESPONSE = 200;
const PARTIAL_CONTENT_RESPONSE = 206;

function getArrayBuffer(xhr) {
  const data = xhr.response;

  if (typeof data !== "string") {
    return data;
  }

  const array = (0, _util.stringToBytes)(data);
  return array.buffer;
}

class NetworkManager {
  constructor(url) {
    let args = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
    this.url = url;
    this.isHttp = /^https?:/i.test(url);
    this.httpHeaders = this.isHttp && args.httpHeaders || Object.create(null);
    this.withCredentials = args.withCredentials || false;

    this.getXhr = args.getXhr || function NetworkManager_getXhr() {
      return new XMLHttpRequest();
    };

    this.currXhrId = 0;
    this.pendingRequests = Object.create(null);
  }

  requestRange(begin, end, listeners) {
    const args = {
      begin,
      end
    };

    for (const prop in listeners) {
      args[prop] = listeners[prop];
    }

    return this.request(args);
  }

  requestFull(listeners) {
    return this.request(listeners);
  }

  request(args) {
    const xhr = this.getXhr();
    const xhrId = this.currXhrId++;
    const pendingRequest = this.pendingRequests[xhrId] = {
      xhr
    };
    xhr.open("GET", this.url);
    xhr.withCredentials = this.withCredentials;

    for (const property in this.httpHeaders) {
      const value = this.httpHeaders[property];

      if (typeof value === "undefined") {
        continue;
      }

      xhr.setRequestHeader(property, value);
    }

    if (this.isHttp && "begin" in args && "end" in args) {
      xhr.setRequestHeader("Range", `bytes=${args.begin}-${args.end - 1}`);
      pendingRequest.expectedStatus = PARTIAL_CONTENT_RESPONSE;
    } else {
      pendingRequest.expectedStatus = OK_RESPONSE;
    }

    xhr.responseType = "arraybuffer";

    if (args.onError) {
      xhr.onerror = function (evt) {
        args.onError(xhr.status);
      };
    }

    xhr.onreadystatechange = this.onStateChange.bind(this, xhrId);
    xhr.onprogress = this.onProgress.bind(this, xhrId);
    pendingRequest.onHeadersReceived = args.onHeadersReceived;
    pendingRequest.onDone = args.onDone;
    pendingRequest.onError = args.onError;
    pendingRequest.onProgress = args.onProgress;
    xhr.send(null);
    return xhrId;
  }

  onProgress(xhrId, evt) {
    var _pendingRequest$onPro;

    const pendingRequest = this.pendingRequests[xhrId];

    if (!pendingRequest) {
      return;
    }

    (_pendingRequest$onPro = pendingRequest.onProgress) === null || _pendingRequest$onPro === void 0 ? void 0 : _pendingRequest$onPro.call(pendingRequest, evt);
  }

  onStateChange(xhrId, evt) {
    const pendingRequest = this.pendingRequests[xhrId];

    if (!pendingRequest) {
      return;
    }

    const xhr = pendingRequest.xhr;

    if (xhr.readyState >= 2 && pendingRequest.onHeadersReceived) {
      pendingRequest.onHeadersReceived();
      delete pendingRequest.onHeadersReceived;
    }

    if (xhr.readyState !== 4) {
      return;
    }

    if (!(xhrId in this.pendingRequests)) {
      return;
    }

    delete this.pendingRequests[xhrId];

    if (xhr.status === 0 && this.isHttp) {
      var _pendingRequest$onErr;

      (_pendingRequest$onErr = pendingRequest.onError) === null || _pendingRequest$onErr === void 0 ? void 0 : _pendingRequest$onErr.call(pendingRequest, xhr.status);
      return;
    }

    const xhrStatus = xhr.status || OK_RESPONSE;
    const ok_response_on_range_request = xhrStatus === OK_RESPONSE && pendingRequest.expectedStatus === PARTIAL_CONTENT_RESPONSE;

    if (!ok_response_on_range_request && xhrStatus !== pendingRequest.expectedStatus) {
      var _pendingRequest$onErr2;

      (_pendingRequest$onErr2 = pendingRequest.onError) === null || _pendingRequest$onErr2 === void 0 ? void 0 : _pendingRequest$onErr2.call(pendingRequest, xhr.status);
      return;
    }

    const chunk = getArrayBuffer(xhr);

    if (xhrStatus === PARTIAL_CONTENT_RESPONSE) {
      const rangeHeader = xhr.getResponseHeader("Content-Range");
      const matches = /bytes (\d+)-(\d+)\/(\d+)/.exec(rangeHeader);
      pendingRequest.onDone({
        begin: parseInt(matches[1], 10),
        chunk
      });
    } else if (chunk) {
      pendingRequest.onDone({
        begin: 0,
        chunk
      });
    } else {
      var _pendingRequest$onErr3;

      (_pendingRequest$onErr3 = pendingRequest.onError) === null || _pendingRequest$onErr3 === void 0 ? void 0 : _pendingRequest$onErr3.call(pendingRequest, xhr.status);
    }
  }

  getRequestXhr(xhrId) {
    return this.pendingRequests[xhrId].xhr;
  }

  isPendingRequest(xhrId) {
    return xhrId in this.pendingRequests;
  }

  abortRequest(xhrId) {
    const xhr = this.pendingRequests[xhrId].xhr;
    delete this.pendingRequests[xhrId];
    xhr.abort();
  }

}

class PDFNetworkStream {
  constructor(source) {
    this._source = source;
    this._manager = new NetworkManager(source.url, {
      httpHeaders: source.httpHeaders,
      withCredentials: source.withCredentials
    });
    this._rangeChunkSize = source.rangeChunkSize;
    this._fullRequestReader = null;
    this._rangeRequestReaders = [];
  }

  _onRangeRequestReaderClosed(reader) {
    const i = this._rangeRequestReaders.indexOf(reader);

    if (i >= 0) {
      this._rangeRequestReaders.splice(i, 1);
    }
  }

  getFullReader() {
    (0, _util.assert)(!this._fullRequestReader, "PDFNetworkStream.getFullReader can only be called once.");
    this._fullRequestReader = new PDFNetworkStreamFullRequestReader(this._manager, this._source);
    return this._fullRequestReader;
  }

  getRangeReader(begin, end) {
    const reader = new PDFNetworkStreamRangeRequestReader(this._manager, begin, end);
    reader.onClosed = this._onRangeRequestReaderClosed.bind(this);

    this._rangeRequestReaders.push(reader);

    return reader;
  }

  cancelAllRequests(reason) {
    var _this$_fullRequestRea;

    (_this$_fullRequestRea = this._fullRequestReader) === null || _this$_fullRequestRea === void 0 ? void 0 : _this$_fullRequestRea.cancel(reason);

    for (const reader of this._rangeRequestReaders.slice(0)) {
      reader.cancel(reason);
    }
  }

}

exports.PDFNetworkStream = PDFNetworkStream;

class PDFNetworkStreamFullRequestReader {
  constructor(manager, source) {
    this._manager = manager;
    const args = {
      onHeadersReceived: this._onHeadersReceived.bind(this),
      onDone: this._onDone.bind(this),
      onError: this._onError.bind(this),
      onProgress: this._onProgress.bind(this)
    };
    this._url = source.url;
    this._fullRequestId = manager.requestFull(args);
    this._headersReceivedCapability = (0, _util.createPromiseCapability)();
    this._disableRange = source.disableRange || false;
    this._contentLength = source.length;
    this._rangeChunkSize = source.rangeChunkSize;

    if (!this._rangeChunkSize && !this._disableRange) {
      this._disableRange = true;
    }

    this._isStreamingSupported = false;
    this._isRangeSupported = false;
    this._cachedChunks = [];
    this._requests = [];
    this._done = false;
    this._storedError = undefined;
    this._filename = null;
    this.onProgress = null;
  }

  _onHeadersReceived() {
    const fullRequestXhrId = this._fullRequestId;

    const fullRequestXhr = this._manager.getRequestXhr(fullRequestXhrId);

    const getResponseHeader = name => {
      return fullRequestXhr.getResponseHeader(name);
    };

    const {
      allowRangeRequests,
      suggestedLength
    } = (0, _network_utils.validateRangeRequestCapabilities)({
      getResponseHeader,
      isHttp: this._manager.isHttp,
      rangeChunkSize: this._rangeChunkSize,
      disableRange: this._disableRange
    });

    if (allowRangeRequests) {
      this._isRangeSupported = true;
    }

    this._contentLength = suggestedLength || this._contentLength;
    this._filename = (0, _network_utils.extractFilenameFromHeader)(getResponseHeader);

    if (this._isRangeSupported) {
      this._manager.abortRequest(fullRequestXhrId);
    }

    this._headersReceivedCapability.resolve();
  }

  _onDone(data) {
    if (data) {
      if (this._requests.length > 0) {
        const requestCapability = this._requests.shift();

        requestCapability.resolve({
          value: data.chunk,
          done: false
        });
      } else {
        this._cachedChunks.push(data.chunk);
      }
    }

    this._done = true;

    if (this._cachedChunks.length > 0) {
      return;
    }

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;
  }

  _onError(status) {
    this._storedError = (0, _network_utils.createResponseStatusError)(status, this._url);

    this._headersReceivedCapability.reject(this._storedError);

    for (const requestCapability of this._requests) {
      requestCapability.reject(this._storedError);
    }

    this._requests.length = 0;
    this._cachedChunks.length = 0;
  }

  _onProgress(evt) {
    var _this$onProgress;

    (_this$onProgress = this.onProgress) === null || _this$onProgress === void 0 ? void 0 : _this$onProgress.call(this, {
      loaded: evt.loaded,
      total: evt.lengthComputable ? evt.total : this._contentLength
    });
  }

  get filename() {
    return this._filename;
  }

  get isRangeSupported() {
    return this._isRangeSupported;
  }

  get isStreamingSupported() {
    return this._isStreamingSupported;
  }

  get contentLength() {
    return this._contentLength;
  }

  get headersReady() {
    return this._headersReceivedCapability.promise;
  }

  async read() {
    if (this._storedError) {
      throw this._storedError;
    }

    if (this._cachedChunks.length > 0) {
      const chunk = this._cachedChunks.shift();

      return {
        value: chunk,
        done: false
      };
    }

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    const requestCapability = (0, _util.createPromiseCapability)();

    this._requests.push(requestCapability);

    return requestCapability.promise;
  }

  cancel(reason) {
    this._done = true;

    this._headersReceivedCapability.reject(reason);

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;

    if (this._manager.isPendingRequest(this._fullRequestId)) {
      this._manager.abortRequest(this._fullRequestId);
    }

    this._fullRequestReader = null;
  }

}

class PDFNetworkStreamRangeRequestReader {
  constructor(manager, begin, end) {
    this._manager = manager;
    const args = {
      onDone: this._onDone.bind(this),
      onError: this._onError.bind(this),
      onProgress: this._onProgress.bind(this)
    };
    this._url = manager.url;
    this._requestId = manager.requestRange(begin, end, args);
    this._requests = [];
    this._queuedChunk = null;
    this._done = false;
    this._storedError = undefined;
    this.onProgress = null;
    this.onClosed = null;
  }

  _close() {
    var _this$onClosed;

    (_this$onClosed = this.onClosed) === null || _this$onClosed === void 0 ? void 0 : _this$onClosed.call(this, this);
  }

  _onDone(data) {
    const chunk = data.chunk;

    if (this._requests.length > 0) {
      const requestCapability = this._requests.shift();

      requestCapability.resolve({
        value: chunk,
        done: false
      });
    } else {
      this._queuedChunk = chunk;
    }

    this._done = true;

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;

    this._close();
  }

  _onError(status) {
    this._storedError = (0, _network_utils.createResponseStatusError)(status, this._url);

    for (const requestCapability of this._requests) {
      requestCapability.reject(this._storedError);
    }

    this._requests.length = 0;
    this._queuedChunk = null;
  }

  _onProgress(evt) {
    if (!this.isStreamingSupported) {
      var _this$onProgress2;

      (_this$onProgress2 = this.onProgress) === null || _this$onProgress2 === void 0 ? void 0 : _this$onProgress2.call(this, {
        loaded: evt.loaded
      });
    }
  }

  get isStreamingSupported() {
    return false;
  }

  async read() {
    if (this._storedError) {
      throw this._storedError;
    }

    if (this._queuedChunk !== null) {
      const chunk = this._queuedChunk;
      this._queuedChunk = null;
      return {
        value: chunk,
        done: false
      };
    }

    if (this._done) {
      return {
        value: undefined,
        done: true
      };
    }

    const requestCapability = (0, _util.createPromiseCapability)();

    this._requests.push(requestCapability);

    return requestCapability.promise;
  }

  cancel(reason) {
    this._done = true;

    for (const requestCapability of this._requests) {
      requestCapability.resolve({
        value: undefined,
        done: true
      });
    }

    this._requests.length = 0;

    if (this._manager.isPendingRequest(this._requestId)) {
      this._manager.abortRequest(this._requestId);
    }

    this._close();
  }

}

/***/ }),
/* 161 */
/***/ ((__unused_webpack_module, exports, __w_pdfjs_require__) => {

"use strict";


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
exports.PDFFetchStream = void 0;

var _util = __w_pdfjs_require__(1);

var _network_utils = __w_pdfjs_require__(158);

;

function createFetchOptions(headers, withCredentials, abortController) {
  return {
    method: "GET",
    headers,
    signal: abortController.signal,
    mode: "cors",
    credentials: withCredentials ? "include" : "same-origin",
    redirect: "follow"
  };
}

function createHeaders(httpHeaders) {
  const headers = new Headers();

  for (const property in httpHeaders) {
    const value = httpHeaders[property];

    if (typeof value === "undefined") {
      continue;
    }

    headers.append(property, value);
  }

  return headers;
}

class PDFFetchStream {
  constructor(source) {
    this.source = source;
    this.isHttp = /^https?:/i.test(source.url);
    this.httpHeaders = this.isHttp && source.httpHeaders || {};
    this._fullRequestReader = null;
    this._rangeRequestReaders = [];
  }

  get _progressiveDataLength() {
    var _this$_fullRequestRea, _this$_fullRequestRea2;

    return (_this$_fullRequestRea = (_this$_fullRequestRea2 = this._fullRequestReader) === null || _this$_fullRequestRea2 === void 0 ? void 0 : _this$_fullRequestRea2._loaded) !== null && _this$_fullRequestRea !== void 0 ? _this$_fullRequestRea : 0;
  }

  getFullReader() {
    (0, _util.assert)(!this._fullRequestReader, "PDFFetchStream.getFullReader can only be called once.");
    this._fullRequestReader = new PDFFetchStreamReader(this);
    return this._fullRequestReader;
  }

  getRangeReader(begin, end) {
    if (end <= this._progressiveDataLength) {
      return null;
    }

    const reader = new PDFFetchStreamRangeReader(this, begin, end);

    this._rangeRequestReaders.push(reader);

    return reader;
  }

  cancelAllRequests(reason) {
    if (this._fullRequestReader) {
      this._fullRequestReader.cancel(reason);
    }

    for (const reader of this._rangeRequestReaders.slice(0)) {
      reader.cancel(reason);
    }
  }

}

exports.PDFFetchStream = PDFFetchStream;

class PDFFetchStreamReader {
  constructor(stream) {
    this._stream = stream;
    this._reader = null;
    this._loaded = 0;
    this._filename = null;
    const source = stream.source;
    this._withCredentials = source.withCredentials || false;
    this._contentLength = source.length;
    this._headersCapability = (0, _util.createPromiseCapability)();
    this._disableRange = source.disableRange || false;
    this._rangeChunkSize = source.rangeChunkSize;

    if (!this._rangeChunkSize && !this._disableRange) {
      this._disableRange = true;
    }

    this._abortController = new AbortController();
    this._isStreamingSupported = !source.disableStream;
    this._isRangeSupported = !source.disableRange;
    this._headers = createHeaders(this._stream.httpHeaders);
    const url = source.url;
    fetch(url, createFetchOptions(this._headers, this._withCredentials, this._abortController)).then(response => {
      if (!(0, _network_utils.validateResponseStatus)(response.status)) {
        throw (0, _network_utils.createResponseStatusError)(response.status, url);
      }

      this._reader = response.body.getReader();

      this._headersCapability.resolve();

      const getResponseHeader = name => {
        return response.headers.get(name);
      };

      const {
        allowRangeRequests,
        suggestedLength
      } = (0, _network_utils.validateRangeRequestCapabilities)({
        getResponseHeader,
        isHttp: this._stream.isHttp,
        rangeChunkSize: this._rangeChunkSize,
        disableRange: this._disableRange
      });
      this._isRangeSupported = allowRangeRequests;
      this._contentLength = suggestedLength || this._contentLength;
      this._filename = (0, _network_utils.extractFilenameFromHeader)(getResponseHeader);

      if (!this._isStreamingSupported && this._isRangeSupported) {
        this.cancel(new _util.AbortException("Streaming is disabled."));
      }
    }).catch(this._headersCapability.reject);
    this.onProgress = null;
  }

  get headersReady() {
    return this._headersCapability.promise;
  }

  get filename() {
    return this._filename;
  }

  get contentLength() {
    return this._contentLength;
  }

  get isRangeSupported() {
    return this._isRangeSupported;
  }

  get isStreamingSupported() {
    return this._isStreamingSupported;
  }

  async read() {
    await this._headersCapability.promise;
    const {
      value,
      done
    } = await this._reader.read();

    if (done) {
      return {
        value,
        done
      };
    }

    this._loaded += value.byteLength;

    if (this.onProgress) {
      this.onProgress({
        loaded: this._loaded,
        total: this._contentLength
      });
    }

    const buffer = new Uint8Array(value).buffer;
    return {
      value: buffer,
      done: false
    };
  }

  cancel(reason) {
    if (this._reader) {
      this._reader.cancel(reason);
    }

    this._abortController.abort();
  }

}

class PDFFetchStreamRangeReader {
  constructor(stream, begin, end) {
    this._stream = stream;
    this._reader = null;
    this._loaded = 0;
    const source = stream.source;
    this._withCredentials = source.withCredentials || false;
    this._readCapability = (0, _util.createPromiseCapability)();
    this._isStreamingSupported = !source.disableStream;
    this._abortController = new AbortController();
    this._headers = createHeaders(this._stream.httpHeaders);

    this._headers.append("Range", `bytes=${begin}-${end - 1}`);

    const url = source.url;
    fetch(url, createFetchOptions(this._headers, this._withCredentials, this._abortController)).then(response => {
      if (!(0, _network_utils.validateResponseStatus)(response.status)) {
        throw (0, _network_utils.createResponseStatusError)(response.status, url);
      }

      this._readCapability.resolve();

      this._reader = response.body.getReader();
    }).catch(this._readCapability.reject);
    this.onProgress = null;
  }

  get isStreamingSupported() {
    return this._isStreamingSupported;
  }

  async read() {
    await this._readCapability.promise;
    const {
      value,
      done
    } = await this._reader.read();

    if (done) {
      return {
        value,
        done
      };
    }

    this._loaded += value.byteLength;

    if (this.onProgress) {
      this.onProgress({
        loaded: this._loaded
      });
    }

    const buffer = new Uint8Array(value).buffer;
    return {
      value: buffer,
      done: false
    };
  }

  cancel(reason) {
    if (this._reader) {
      this._reader.cancel(reason);
    }

    this._abortController.abort();
  }

}

/***/ })
/******/ 	]);
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __w_pdfjs_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __w_pdfjs_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry need to be wrapped in an IIFE because it need to be in strict mode.
(() => {
"use strict";
var exports = __webpack_exports__;


Object.defineProperty(exports, "__esModule", ({
  value: true
}));
Object.defineProperty(exports, "AnnotationEditorLayer", ({
  enumerable: true,
  get: function () {
    return _annotation_editor_layer.AnnotationEditorLayer;
  }
}));
Object.defineProperty(exports, "AnnotationEditorParamsType", ({
  enumerable: true,
  get: function () {
    return _util.AnnotationEditorParamsType;
  }
}));
Object.defineProperty(exports, "AnnotationEditorType", ({
  enumerable: true,
  get: function () {
    return _util.AnnotationEditorType;
  }
}));
Object.defineProperty(exports, "AnnotationEditorUIManager", ({
  enumerable: true,
  get: function () {
    return _tools.AnnotationEditorUIManager;
  }
}));
Object.defineProperty(exports, "AnnotationLayer", ({
  enumerable: true,
  get: function () {
    return _annotation_layer.AnnotationLayer;
  }
}));
Object.defineProperty(exports, "AnnotationMode", ({
  enumerable: true,
  get: function () {
    return _util.AnnotationMode;
  }
}));
Object.defineProperty(exports, "CMapCompressionType", ({
  enumerable: true,
  get: function () {
    return _util.CMapCompressionType;
  }
}));
Object.defineProperty(exports, "GlobalWorkerOptions", ({
  enumerable: true,
  get: function () {
    return _worker_options.GlobalWorkerOptions;
  }
}));
Object.defineProperty(exports, "InvalidPDFException", ({
  enumerable: true,
  get: function () {
    return _util.InvalidPDFException;
  }
}));
Object.defineProperty(exports, "LoopbackPort", ({
  enumerable: true,
  get: function () {
    return _api.LoopbackPort;
  }
}));
Object.defineProperty(exports, "MissingPDFException", ({
  enumerable: true,
  get: function () {
    return _util.MissingPDFException;
  }
}));
Object.defineProperty(exports, "OPS", ({
  enumerable: true,
  get: function () {
    return _util.OPS;
  }
}));
Object.defineProperty(exports, "PDFDataRangeTransport", ({
  enumerable: true,
  get: function () {
    return _api.PDFDataRangeTransport;
  }
}));
Object.defineProperty(exports, "PDFDateString", ({
  enumerable: true,
  get: function () {
    return _display_utils.PDFDateString;
  }
}));
Object.defineProperty(exports, "PDFWorker", ({
  enumerable: true,
  get: function () {
    return _api.PDFWorker;
  }
}));
Object.defineProperty(exports, "PasswordResponses", ({
  enumerable: true,
  get: function () {
    return _util.PasswordResponses;
  }
}));
Object.defineProperty(exports, "PermissionFlag", ({
  enumerable: true,
  get: function () {
    return _util.PermissionFlag;
  }
}));
Object.defineProperty(exports, "PixelsPerInch", ({
  enumerable: true,
  get: function () {
    return _display_utils.PixelsPerInch;
  }
}));
Object.defineProperty(exports, "RenderingCancelledException", ({
  enumerable: true,
  get: function () {
    return _display_utils.RenderingCancelledException;
  }
}));
Object.defineProperty(exports, "SVGGraphics", ({
  enumerable: true,
  get: function () {
    return _svg.SVGGraphics;
  }
}));
Object.defineProperty(exports, "UNSUPPORTED_FEATURES", ({
  enumerable: true,
  get: function () {
    return _util.UNSUPPORTED_FEATURES;
  }
}));
Object.defineProperty(exports, "UnexpectedResponseException", ({
  enumerable: true,
  get: function () {
    return _util.UnexpectedResponseException;
  }
}));
Object.defineProperty(exports, "Util", ({
  enumerable: true,
  get: function () {
    return _util.Util;
  }
}));
Object.defineProperty(exports, "VerbosityLevel", ({
  enumerable: true,
  get: function () {
    return _util.VerbosityLevel;
  }
}));
Object.defineProperty(exports, "XfaLayer", ({
  enumerable: true,
  get: function () {
    return _xfa_layer.XfaLayer;
  }
}));
Object.defineProperty(exports, "build", ({
  enumerable: true,
  get: function () {
    return _api.build;
  }
}));
Object.defineProperty(exports, "createPromiseCapability", ({
  enumerable: true,
  get: function () {
    return _util.createPromiseCapability;
  }
}));
Object.defineProperty(exports, "createValidAbsoluteUrl", ({
  enumerable: true,
  get: function () {
    return _util.createValidAbsoluteUrl;
  }
}));
Object.defineProperty(exports, "getDocument", ({
  enumerable: true,
  get: function () {
    return _api.getDocument;
  }
}));
Object.defineProperty(exports, "getFilenameFromUrl", ({
  enumerable: true,
  get: function () {
    return _display_utils.getFilenameFromUrl;
  }
}));
Object.defineProperty(exports, "getPdfFilenameFromUrl", ({
  enumerable: true,
  get: function () {
    return _display_utils.getPdfFilenameFromUrl;
  }
}));
Object.defineProperty(exports, "getXfaPageViewport", ({
  enumerable: true,
  get: function () {
    return _display_utils.getXfaPageViewport;
  }
}));
Object.defineProperty(exports, "isPdfFile", ({
  enumerable: true,
  get: function () {
    return _display_utils.isPdfFile;
  }
}));
Object.defineProperty(exports, "loadScript", ({
  enumerable: true,
  get: function () {
    return _display_utils.loadScript;
  }
}));
Object.defineProperty(exports, "renderTextLayer", ({
  enumerable: true,
  get: function () {
    return _text_layer.renderTextLayer;
  }
}));
Object.defineProperty(exports, "shadow", ({
  enumerable: true,
  get: function () {
    return _util.shadow;
  }
}));
Object.defineProperty(exports, "version", ({
  enumerable: true,
  get: function () {
    return _api.version;
  }
}));

var _util = __w_pdfjs_require__(1);

var _api = __w_pdfjs_require__(129);

var _display_utils = __w_pdfjs_require__(133);

var _annotation_editor_layer = __w_pdfjs_require__(147);

var _tools = __w_pdfjs_require__(132);

var _annotation_layer = __w_pdfjs_require__(152);

var _worker_options = __w_pdfjs_require__(140);

var _is_node = __w_pdfjs_require__(3);

var _text_layer = __w_pdfjs_require__(155);

var _svg = __w_pdfjs_require__(156);

var _xfa_layer = __w_pdfjs_require__(154);

const pdfjsVersion = '2.16.105';
const pdfjsBuild = '172ccdbe5';
{
  if (_is_node.isNodeJS) {
    const {
      PDFNodeStream
    } = __w_pdfjs_require__(157);

    (0, _api.setPDFNetworkStreamFactory)(params => {
      return new PDFNodeStream(params);
    });
  } else {
    const {
      PDFNetworkStream
    } = __w_pdfjs_require__(160);

    const {
      PDFFetchStream
    } = __w_pdfjs_require__(161);

    (0, _api.setPDFNetworkStreamFactory)(params => {
      if ((0, _display_utils.isValidFetchUrl)(params.url)) {
        return new PDFFetchStream(params);
      }

      return new PDFNetworkStream(params);
    });
  }
}
})();

/******/ 	return __webpack_exports__;
/******/ })()
;
});
